import os
from html.parser import HTMLParser

from locust import HttpUser, between, task
from locust.exception import StopUser


class FormFields(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fields = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "input" and attributes.get("type") == "hidden" and "name" in attributes:
            self.fields[attributes["name"]] = attributes.get("value")


def form_fields(response, *names):
    parser = FormFields()
    parser.feed(response.text)
    if any(not parser.fields.get(name) for name in names):
        raise StopUser("Formulário incompleto")
    return {name: parser.fields[name] for name in names}


class Professor(HttpUser):
    wait_time = between(2, 5)

    def on_start(self):
        if os.getenv("LOAD_TEST_ALLOW_WRITES") != "1":
            raise StopUser("Habilite escritas apenas no ambiente de teste")
        self.project = f"/professor/projeto/{int(os.environ['LOAD_TEST_PROJECT_ID'])}"
        self.qr_token = os.environ["LOAD_TEST_QR_TOKEN"]
        login = self.client.get("/login")
        with self.client.post("/login", data={
            **form_fields(login, "csrf_token"),
            "matricula": os.environ["LOAD_TEST_LOGIN"],
            "senha": os.environ["LOAD_TEST_PASSWORD"],
        }, allow_redirects=False, catch_response=True) as response:
            if response.status_code != 302 or response.headers.get("Location") != "/":
                response.failure("Login de professor recusado")
                raise StopUser()
        scanner = self.client.get(f"{self.project}/scanner", name="/professor/projeto/:id/scanner")
        self.scanner_fields = form_fields(scanner, "csrf_token", "edicao")

    @task(4)
    def dashboard(self):
        self.client.get("/professor/dashboard", allow_redirects=False)

    @task(2)
    def registrar_presenca(self):
        with self.client.post(f"{self.project}/registrar", name="/professor/projeto/:id/registrar",
                              data={**self.scanner_fields, "qr_token": self.qr_token},
                              catch_response=True) as response:
            if response.status_code != 200 or not any(
                mensagem in response.text
                for mensagem in ("computada com sucesso!", "já havia sido registrada anteriormente.")
            ):
                response.failure("Registro rejeitado")

    @task
    def exportar(self):
        self.client.get(f"{self.project}/exportar", name="/professor/projeto/:id/exportar",
                        allow_redirects=False)
