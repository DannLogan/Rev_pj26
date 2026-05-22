import os
import psycopg2
import uuid
from werkzeug.security import generate_password_hash

# ==============================================================================
# 🚀 DADOS DE CONEXÃO DO NOVO SUPABASE (VIRGÍNIA)
# ==============================================================================
DB_HOST = "db.fzvzosmsgqmapkidboqo.supabase.co"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "@Fr3qu3nc14.S1mp0s10"

def inicializar_novo_banco_normalizado():
    print("--- Iniciando Criação do Banco de Dados Atualizado na Virgínia ---")
    
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        cursor = conn.cursor()

        # 1. CRIAÇÃO DAS TABELAS COM AS TRAVAS E REGRAS DA VIRGÍNIA
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT NOT NULL PRIMARY KEY,
            valor TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS edicoes (
            id SERIAL PRIMARY KEY,
            nome_edicao TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS cursos (
            id SERIAL PRIMARY KEY,
            nome_curso TEXT NOT NULL,
            ativo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS projetos (
            id SERIAL PRIMARY KEY,
            nome_projeto TEXT NOT NULL,
            ativo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            email_institucional TEXT,
            login TEXT UNIQUE,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL,
            status_conta TEXT,
            pergunta_seguranca TEXT,
            resposta_seguranca TEXT,
            chave_acesso TEXT,
            ativo INTEGER DEFAULT 1,
            data_cadastro TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS alunos (
            id_usuario INTEGER NOT NULL PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
            matricula TEXT NOT NULL UNIQUE,
            origem_cadastro TEXT,
            qr_token CHARACTER VARYING(255)
        );

        CREATE TABLE IF NOT EXISTS professores (
            id_usuario INTEGER NOT NULL PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
            id_corporativo TEXT UNIQUE
        );

        -- 🚀 TRAVA UNIQUE AQUI: Garante o modelo de Curso Único por Aluno
        CREATE TABLE IF NOT EXISTS usuarios_cursos (
            id_aluno INTEGER NOT NULL PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
            id_curso INTEGER NOT NULL REFERENCES cursos(id) ON DELETE CASCADE,
            CONSTRAINT unique_aluno_curso UNIQUE (id_aluno)
        );

        CREATE TABLE IF NOT EXISTS supervisores_projeto (
            id_professor INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            id_projeto INTEGER NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
            PRIMARY KEY (id_professor, id_projeto)
        );

        -- 🚀 TIMESTAMP DEFAULT: O banco calcula a data de inscrição automaticamente
        CREATE TABLE IF NOT EXISTS inscricoes (
            id_aluno INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            id_projeto INTEGER NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
            id_edicao INTEGER NOT NULL REFERENCES edicoes(id) ON DELETE CASCADE,
            presenca INTEGER DEFAULT 0,
            data_inscricao TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id_aluno, id_projeto, id_edicao)
        );
        ''')
        print("✔️ Tabelas criadas e normalizadas com Chaves Primárias, Auto-incrementos e Defaults.")

        # 2. INSERÇÃO DA PRIMEIRA EDIÇÃO E CONFIGURAÇÃO GLOBAL
        cursor.execute("SELECT id FROM edicoes WHERE nome_edicao = %s", ('2026.1',))
        res_edicao = cursor.fetchone()
        if not res_edicao:
            cursor.execute("INSERT INTO edicoes (nome_edicao) VALUES (%s) RETURNING id", ('2026.1',))
            id_edicao = cursor.fetchone()[0]
        else:
            id_edicao = res_edicao[0]

        cursor.execute("SELECT chave FROM configuracoes WHERE chave = %s", ('edicao_ativa',))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO configuracoes (chave, valor) VALUES (%s, %s)", ('edicao_ativa', str(id_edicao)))
        else:
            cursor.execute("UPDATE configuracoes SET valor = %s WHERE chave = %s", (str(id_edicao), 'edicao_ativa'))
            
        print(f"✔️ Edição '2026.1' (ID: {id_edicao}) definida como ativa.")

        # 3. CRIAÇÃO DO ADMINISTRADOR MESTRE
        cursor.execute("SELECT id FROM usuarios WHERE login = %s", ('admin',))
        if not cursor.fetchone():
            admin_uuid = str(uuid.uuid4())
            # Deixamos o SERIAL gerar o ID do Admin naturalmente para manter a integridade das sequências
            cursor.execute('''
                INSERT INTO usuarios (nome, login, senha, tipo, status_conta, ativo, chave_acesso)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', ('Administrador Sistema', 'admin', generate_password_hash('admin123'), 'admin', 'ativo', 1, admin_uuid))
            print("✔️ Usuário Administrador Mestre criado.")
        else:
            print("ℹ️ Administrador Mestre já existia no sistema.")

        conn.commit()
        cursor.close()
        conn.close()
        print("\n--- NOVO BANCO DA VIRGÍNIA PRONTO PARA RODAR! ---")

    except Exception as e:
        print(f"\n❌ ERRO ao configurar o Supabase: {e}")

if __name__ == '__main__':
    inicializar_novo_banco_normalizado()