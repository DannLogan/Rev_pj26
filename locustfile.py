import os
from html.parser import HTMLParser

from locust import HttpUser, between, task
from locust.exception import StopUser


class CsrfToken(HTMLParser):
    value = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "input" and attributes.get("name") == "csrf_token":
            self.value = attributes.get("value")


def csrf_token(response):
    parser = CsrfToken()
    parser.feed(response.text)
    if not parser.value:
        raise StopUser("Formulário sem token CSRF")
    return parser.value


class Professor(HttpUser):
    wait_time = between(2, 5)

    def on_start(self):
        if os.getenv("LOAD_TEST_ALLOW_WRITES") != "1":
            raise StopUser("Habilite escritas apenas no ambiente de teste")
        self.project = f"/professor/projeto/{int(os.environ['LOAD_TEST_PROJECT_ID'])}"
        self.qr_token = os.environ["LOAD_TEST_QR_TOKEN"]
        login = self.client.get("/login")
        with self.client.post("/login", data={
            "csrf_token": csrf_token(login),
            "matricula": os.environ["LOAD_TEST_LOGIN"],
            "senha": os.environ["LOAD_TEST_PASSWORD"],
        }, allow_redirects=False, catch_response=True) as response:
            if response.status_code != 302 or response.headers.get("Location") != "/":
                response.failure("Login de professor recusado")
                raise StopUser()
        scanner = self.client.get(f"{self.project}/scanner", name="/professor/projeto/:id/scanner")
        self.csrf = csrf_token(scanner)

    @task(4)
    def dashboard(self):
        self.client.get("/professor/dashboard", allow_redirects=False)

    @task(2)
    def registrar_presenca(self):
        with self.client.post(f"{self.project}/registrar", name="/professor/projeto/:id/registrar",
                              data={"csrf_token": self.csrf, "qr_token": self.qr_token},
                              allow_redirects=False, catch_response=True) as response:
            if response.status_code != 302 or response.headers.get("Location") != self.project:
                response.failure("Registro rejeitado")

    @task
    def exportar(self):
        self.client.get(f"{self.project}/exportar", name="/professor/projeto/:id/exportar",
                        allow_redirects=False)
