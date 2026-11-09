from repositories import admin_repository, auth_repository
from utils import decorators
from utils.passwords import hash_password


def test_aluno_troca_senha_provisoria_antes_de_acessar_portal(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-not-used-in-production")
    from app import create_app

    app = create_app({"RATELIMIT_ENABLED": False})
    from flask_wtf.csrf import generate_csrf
    app.add_url_rule("/csrf-teste", view_func=generate_csrf)
    client = app.test_client()

    provisoria = "senha-provisoria-teste"
    nova = "nova-senha-do-aluno"
    usuario = {
        "id": 7, "tipo": "aluno", "status_conta": "pendente", "senha": hash_password(provisoria),
        "nome": "Aluno", "login": "aluno", "matricula": "123", "id_corporativo": None,
        "email_institucional": "aluno@example.org", "permissoes": [],
    }
    monkeypatch.setattr(auth_repository, "buscar_usuario_por_identificador", lambda _: usuario)
    monkeypatch.setattr(auth_repository, "buscar_usuario_por_id", lambda _: usuario)
    monkeypatch.setattr(decorators, "buscar_estado_sessao", lambda _: usuario)
    monkeypatch.setattr(admin_repository, "listar_todos_cursos", lambda: [{"id": 1, "nome_curso": "Curso"}])
    monkeypatch.setattr(auth_repository, "buscar_cursos_usuario", lambda _: [1])
    monkeypatch.setattr(auth_repository, "identificador_em_uso", lambda *_: False)

    def concluir(usuario_id, nome, email, login, senha, senha_anterior_hash, curso):
        assert curso is None
        assert senha == nova
        assert senha_anterior_hash == usuario["senha"]
        usuario.update(senha=hash_password(senha), status_conta="ativa")
        return usuario["senha"]

    monkeypatch.setattr(auth_repository, "salvar_conclusao_cadastro", concluir)

    assert client.get("/recuperar").status_code == 200
    assert client.post("/recuperar").status_code == 405
    csrf = client.get("/csrf-teste").get_data(as_text=True)
    login = {"matricula": "123", "senha": provisoria, "csrf_token": csrf}
    assert client.post("/login", data=login).location == "/concluir-cadastro"
    assert client.get("/aluno/dashboard").location == "/concluir-cadastro"

    pagina = client.get("/concluir-cadastro").get_data(as_text=True)
    assert 'name="pergunta"' not in pagina
    assert 'name="resposta"' not in pagina
    assert 'name="confirmar_senha"' in pagina

    csrf = client.get("/csrf-teste").get_data(as_text=True)
    cadastro = {"nome": "Aluno", "login": "aluno", "csrf_token": csrf}
    for senha, confirmacao in [(provisoria, provisoria), (nova, provisoria)]:
        resposta = client.post("/concluir-cadastro", data={
            **cadastro, "senha": senha, "confirmar_senha": confirmacao,
        })
        assert resposta.status_code == 200
        assert usuario["status_conta"] == "pendente"

    resposta = client.post("/concluir-cadastro", data={
        **cadastro, "senha": nova, "confirmar_senha": nova,
    })
    assert resposta.location == "/"
    assert client.get("/").location == "/aluno/dashboard"
    assert client.get("/concluir-cadastro").location == "/"

    outro_cliente = app.test_client()
    login["csrf_token"] = outro_cliente.get("/csrf-teste").get_data(as_text=True)
    assert outro_cliente.post("/login", data=login).status_code == 200
    assert outro_cliente.post("/login", data={**login, "senha": nova}).location == "/"
