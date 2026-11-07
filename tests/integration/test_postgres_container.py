from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from testcontainers.postgres import PostgresContainer

from db import obter_conexao
from init_db import inicializar_novo_banco_normalizado
from repositories.professor_repository import registrar_presenca_aluno


def test_apenas_uma_leitura_concorrente_confirma_presenca(monkeypatch):
    with PostgresContainer("postgres:16") as postgres:
        url = postgres.get_connection_url().replace("postgresql+psycopg2://", "postgresql://", 1)
        monkeypatch.setenv("DATABASE_URL", url)
        monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "senha-exclusiva-de-teste-postgres")
        inicializar_novo_banco_normalizado()

        with obter_conexao() as cursor:
            cursor.execute("""
                INSERT INTO usuarios (nome, senha, tipo)
                VALUES ('Aluno', 'fixture', 'aluno'), ('Professor', 'fixture', 'professor')
                RETURNING id, tipo
            """)
            ids = {row["tipo"]: row["id"] for row in cursor.fetchall()}
            cursor.execute("INSERT INTO projetos (nome_projeto) VALUES ('Teste') RETURNING id")
            projeto = cursor.fetchone()["id"]
            cursor.execute("SELECT id FROM edicoes WHERE nome_edicao = '2026.1'")
            edicao = str(cursor.fetchone()["id"])
            cursor.execute("INSERT INTO supervisores_projeto VALUES (%s, %s)", (ids["professor"], projeto))
            cursor.execute("""
                INSERT INTO inscricoes (id_aluno, id_projeto, id_edicao)
                VALUES (%s, %s, %s)
            """, (ids["aluno"], projeto, edicao))

        with pytest.raises(PermissionError):
            registrar_presenca_aluno(ids["aluno"], projeto, edicao, ids["aluno"])

        barrier = Barrier(2)

        def registrar():
            barrier.wait(timeout=5)
            return registrar_presenca_aluno(ids["aluno"], projeto, edicao, ids["professor"])

        with ThreadPoolExecutor(max_workers=2) as executor:
            requests = [executor.submit(registrar) for _ in range(2)]
            assert sorted(item.result(timeout=10) for item in requests) == ["ja_presente", "sucesso"]

        with obter_conexao() as cursor:
            cursor.execute("SELECT presenca FROM inscricoes")
            assert cursor.fetchall() == [{"presenca": 1}]
