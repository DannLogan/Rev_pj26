from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from testcontainers.postgres import PostgresContainer

from db import obter_conexao
from init_db import inicializar_novo_banco_normalizado
from repositories.admin_repository import atualizar_edicao_ativa
from repositories.aluno_repository import cancelar_inscricao_pendente, realizar_inscricao_manual
from repositories.professor_repository import listar_chamadas_supervisor, registrar_presenca_aluno


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
            cursor.execute("INSERT INTO professores (id_usuario) VALUES (%s)", (ids["professor"],))
            cursor.execute("INSERT INTO alunos (id_usuario, matricula) VALUES (%s, '0001')", (ids["aluno"],))
            cursor.execute("INSERT INTO cursos (nome_curso) VALUES ('Curso A'), ('Curso B') RETURNING id")
            curso, outro_curso = (row['id'] for row in cursor.fetchall())
            cursor.execute("INSERT INTO usuarios_cursos VALUES (%s, %s)", (ids["aluno"], curso))
            cursor.execute("INSERT INTO supervisores_projeto_curso VALUES (%s, %s, %s)", (ids["professor"], projeto, curso))
            cursor.execute("""
                INSERT INTO inscricoes (id_aluno, id_projeto, id_edicao)
                VALUES (%s, %s, %s)
            """, (ids["aluno"], projeto, edicao))

        with pytest.raises(PermissionError):
            registrar_presenca_aluno(ids["aluno"], projeto, edicao, ids["aluno"], curso)

        with pytest.raises(PermissionError):
            registrar_presenca_aluno(ids["aluno"], projeto, edicao, ids["professor"], outro_curso)
        with obter_conexao() as cursor:
            cursor.execute("UPDATE usuarios_cursos SET id_curso = %s WHERE id_aluno = %s", (outro_curso, ids["aluno"]))
        assert listar_chamadas_supervisor(ids["professor"], edicao) == []
        assert registrar_presenca_aluno(ids["aluno"], projeto, edicao, ids["professor"], curso) == "fora_do_escopo"
        with obter_conexao() as cursor:
            cursor.execute("UPDATE usuarios_cursos SET id_curso = %s WHERE id_aluno = %s", (curso, ids["aluno"]))
        assert [row["matricula"] for row in listar_chamadas_supervisor(ids["professor"], edicao)] == ["0001"]

        barrier = Barrier(2)

        def registrar():
            barrier.wait(timeout=5)
            return registrar_presenca_aluno(ids["aluno"], projeto, edicao, ids["professor"], curso)

        with ThreadPoolExecutor(max_workers=2) as executor:
            requests = [executor.submit(registrar) for _ in range(2)]
            assert sorted(item.result(timeout=10) for item in requests) == ["ja_presente", "sucesso"]

        with obter_conexao() as cursor:
            cursor.execute("SELECT presenca FROM inscricoes")
            assert cursor.fetchall() == [{"presenca": 1}]


        assert realizar_inscricao_manual(ids["aluno"], projeto) == "ja_inscrito"
        with obter_conexao() as cursor:
            cursor.execute("UPDATE projetos SET ativo = 0 WHERE id = %s", (projeto,))
            cursor.execute("DELETE FROM configuracoes WHERE chave = 'edicao_ativa'")
        assert realizar_inscricao_manual(ids["aluno"], projeto) == "indisponivel"

        barrier = Barrier(2)

        def abrir_edicao():
            barrier.wait(timeout=5)
            return atualizar_edicao_ativa("2026.2")

        with ThreadPoolExecutor(max_workers=2) as executor:
            requests = [executor.submit(abrir_edicao) for _ in range(2)]
            assert sorted(item.result(timeout=10) for item in requests) == ["ja_ativa", "sucesso"]

        assert realizar_inscricao_manual(ids["aluno"], projeto) == "indisponivel"
        with obter_conexao() as cursor:
            cursor.execute("UPDATE projetos SET ativo = 1 WHERE id = %s", (projeto,))
        assert realizar_inscricao_manual(ids["aluno"], projeto) == "sucesso"
        assert realizar_inscricao_manual(ids["aluno"], projeto) == "ja_inscrito"
        assert cancelar_inscricao_pendente(ids["aluno"], projeto, edicao) == 0
        assert registrar_presenca_aluno(
            ids["aluno"], projeto, edicao, ids["professor"], curso
        ) == "edicao_indisponivel"
