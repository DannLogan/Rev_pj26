import pytest

from repositories import professor_repository


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-not-used-in-production")
    from app import create_app

    app = create_app({"RATELIMIT_ENABLED": False})
    client = app.test_client()
    with client.session_transaction() as session:
        session.update(usuario_id=12, tipo="professor", status_conta="ativa")
    return client


@pytest.mark.parametrize("suffix", ["", "/scanner", "/exportar"])
def test_professor_sem_vinculo_nao_le_projeto(client, monkeypatch, suffix):
    def buscar(projeto_id, professor_id):
        assert (projeto_id, professor_id) == (3, 12)
        return None

    monkeypatch.setattr(professor_repository, "obter_projeto_por_id_e_professor", buscar)
    assert client.get(f"/professor/projeto/3{suffix}").status_code == 404


def test_registro_exige_post_e_csrf(client):
    assert client.get("/professor/projeto/3/registrar").status_code == 405
    assert client.post(
        "/professor/projeto/3/registrar", data={"qr_token": "qr-1"}
    ).status_code == 400


def test_professor_sem_vinculo_nao_registra_presenca(client, monkeypatch):
    from flask_wtf.csrf import generate_csrf

    monkeypatch.setattr(
        professor_repository, "obter_projeto_por_id_e_professor", lambda *_: None
    )

    def nao_deve_buscar_qr(*_):
        pytest.fail("QR consultado antes de autorizar o projeto")

    monkeypatch.setattr(
        professor_repository, "buscar_aluno_por_qr_token", nao_deve_buscar_qr
    )
    app = client.application
    app.add_url_rule("/csrf-teste", view_func=generate_csrf)
    token = client.get("/csrf-teste").get_data(as_text=True)
    assert client.post(
        "/professor/projeto/3/registrar",
        data={"csrf_token": token, "qr_token": "qr-1"},
    ).status_code == 404
