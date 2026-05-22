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

        # 1. CRIAÇÃO DAS TABELAS CONFORME EXTRAÇÃO DO SEU BANCO ORIGINAL
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT NOT NULL,
            valor TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS edicoes (
            id INTEGER NOT NULL,
            nome_edicao TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS cursos (
            id INTEGER NOT NULL,
            nome_curso TEXT NOT NULL,
            ativo INTEGER
        );

        CREATE TABLE IF NOT EXISTS projetos (
            id INTEGER NOT NULL,
            nome_projeto TEXT NOT NULL,
            ativo INTEGER
        );

        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            email_institucional TEXT,
            login TEXT,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL,
            status_conta TEXT,
            pergunta_seguranca TEXT,
            resposta_seguranca TEXT,
            chave_acesso TEXT,
            ativo INTEGER,
            data_cadastro TIMESTAMP WITHOUT TIME ZONE
        );

        -- 🚀 Alunos atualizado com o campo qr_token que causava o erro!
        CREATE TABLE IF NOT EXISTS alunos (
            id_usuario INTEGER NOT NULL,
            matricula TEXT NOT NULL,
            origem_cadastro TEXT,
            qr_token CHARACTER VARYING(255)
        );

        -- 🚀 Professores atualizado com o id_corporativo do banco original
        CREATE TABLE IF NOT EXISTS professores (
            id_usuario INTEGER NOT NULL,
            id_corporativo TEXT
        );

        CREATE TABLE IF NOT EXISTS usuarios_cursos (
            id_aluno INTEGER NOT NULL,
            id_curso INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS supervisores_projeto (
            id_professor INTEGER NOT NULL,
            id_projeto INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS inscricoes (
            id_aluno INTEGER NOT NULL,
            id_projeto INTEGER NOT NULL,
            id_edicao INTEGER NOT NULL,
            presenca INTEGER,
            data_inscricao TIMESTAMP WITHOUT TIME ZONE
        );
        ''')
        print("✔️ Tabelas criadas no modelo idêntico ao original.")

        # 2. INSERÇÃO DA PRIMEIRA EDIÇÃO E CONFIGURAÇÃO GLOBAL
        # Como removemos o SERIAL para bater com o histórico do seu banco, inserimos o ID 1 manualmente para a primeira edição
        cursor.execute("SELECT id FROM edicoes WHERE nome_edicao = %s", ('2026.1',))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO edicoes (id, nome_edicao) VALUES (%s, %s)", (1, '2026.1'))
            id_edicao = 1
        else:
            cursor.execute("SELECT id FROM edicoes WHERE nome_edicao = %s", ('2026.1',))
            id_edicao = cursor.fetchone()[0]

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
            # Inserindo o ID 1 explicitamente para o primeiro admin
            cursor.execute('''
                INSERT INTO usuarios (id, nome, login, senha, tipo, status_conta, ativo, chave_acesso)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (1, 'Administrador Sistema', 'admin', generate_password_hash('admin123'), 'admin', 'ativo', 1, admin_uuid))
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