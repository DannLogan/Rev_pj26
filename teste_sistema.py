# Exemplo de arquivo de teste: test_sistema.py
import pytest
from app import create_app

@pytest.fixture
def client():
    # Cria o aplicativo em modo de teste estrito
    app = create_app({'TESTING': True})
    with app.test_client() as client:
        yield client

def test_dashboard_aluno_abre_sem_login(client):
    # O decorador vai ver a flag TESTING=True e vai deixar passar direto!
    resposta = client.get('/aluno/dashboard')
    assert resposta.status_code == 200