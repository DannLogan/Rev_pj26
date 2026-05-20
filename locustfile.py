from locust import HttpUser, task, between

class SimuladorEstresseBanco(HttpUser):
    # Simula cliques rápidos para forçar o estresse do banco
    wait_time = between(0.1, 0.5) 

    @task
    def testar_escrita_concorrente(self):
        # Dispara direto contra a rota de teste de carga
        self.client.post("/teste-carga-presenca", json={
            "aluno_id": 1,
            "projeto_id": 1
        })