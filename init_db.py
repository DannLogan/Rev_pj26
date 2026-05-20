import os
import psycopg2
import uuid
from werkzeug.security import generate_password_hash

# ==============================================================================
# DADOS DE CONEXÃO SEPARADOS (Extraídos direto do seu projeto Supabase)
# ==============================================================================
DB_HOST = "db.kkdtsaostzhqfmzvohmz.supabase.co"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "@Fr3qu3nc14.S1mp0s10" # Identificada através do log do seu terminal

def inicializar_novo_banco_normalizado():
    print("--- Iniciando Criação do Banco de Dados Normalizado no Supabase ---")
    
    try:
        # Conexão explícita por parâmetros - Imune a erros de quebra de texto (URI)
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        cursor = conn.cursor()

        # 1. CRIAÇÃO DAS TABELAS NORMALIZADAS
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS edicoes (
            id SERIAL PRIMARY KEY,
            nome_edicao TEXT UNIQUE NOT NULL
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
            email_institucional TEXT UNIQUE,
            login TEXT UNIQUE,
            senha TEXT NOT NULL,
            tipo TEXT CHECK( tipo IN ('aluno','professor','admin') ) NOT NULL,
            status_conta TEXT DEFAULT 'pendente',
            pergunta_seguranca TEXT,
            resposta_seguranca TEXT,
            chave_acesso TEXT UNIQUE,
            ativo INTEGER DEFAULT 1,
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS alunos (
            id_usuario INTEGER PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
            matricula TEXT UNIQUE NOT NULL,
            origem_cadastro TEXT DEFAULT 'manual'
        );

        CREATE TABLE IF NOT EXISTS professores (
            id_usuario INTEGER PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS usuarios_cursos (
            id_aluno INTEGER REFERENCES alunos(id_usuario) ON DELETE CASCADE,
            id_curso INTEGER REFERENCES cursos(id) ON DELETE CASCADE,
            PRIMARY KEY (id_aluno, id_curso)
        );

        CREATE TABLE IF NOT EXISTS supervisores_projeto (
            id_professor INTEGER REFERENCES professores(id_usuario) ON DELETE CASCADE,
            id_projeto INTEGER REFERENCES projetos(id) ON DELETE CASCADE,
            PRIMARY KEY (id_professor, id_projeto)
        );

        CREATE TABLE IF NOT EXISTS inscricoes (
            id_aluno INTEGER REFERENCES alunos(id_usuario) ON DELETE CASCADE,
            id_projeto INTEGER REFERENCES projetos(id) ON DELETE CASCADE,
            id_edicao INTEGER REFERENCES edicoes(id) ON DELETE CASCADE,
            presenca INTEGER DEFAULT 0,
            data_inscricao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id_aluno, id_projeto, id_edicao)
        );
        ''')
        print("✔️ Tabelas e restrições criadas com sucesso.")

        # 2. INSERÇÃO DA PRIMEIRA EDIÇÃO E CONFIGURAÇÃO GLOBAL
        cursor.execute("INSERT INTO edicoes (nome_edicao) VALUES (%s) ON CONFLICT DO NOTHING RETURNING id", ('2026.1',))
        resultado_edicao = cursor.fetchone()
        
        if resultado_edicao:
            id_edicao = resultado_edicao[0]
        else:
            cursor.execute("SELECT id FROM edicoes WHERE nome_edicao = %s", ('2026.1',))
            id_edicao = cursor.fetchone()[0]

        cursor.execute('''
            INSERT INTO configuracoes (chave, valor) 
            VALUES (%s, %s) 
            ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor
        ''', ('edicao_ativa', str(id_edicao)))
        print(f"✔️ Edição '2026.1' (ID: {id_edicao}) definida como ativa.")

        # 3. CRIAÇÃO DO ADMINISTRADOR MESTRE
        cursor.execute("SELECT id FROM usuarios WHERE login = %s", ('admin',))
        if not cursor.fetchone():
            admin_uuid = str(uuid.uuid4())
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
        print("\n--- Banco de Dados Normalizado e PRONTO para o Flask! ---")

    except Exception as e:
        print(f"\n❌ ERRO ao configurar o Supabase: {e}")

if __name__ == '__main__':
    inicializar_novo_banco_normalizado()