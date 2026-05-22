import os
from contextlib import contextmanager
import psycopg2
import psycopg2.extras

# Configurações de acesso ao Supabase (Padrão para desenvolvimento local)
DB_HOST = "db.fzvzosmsgqmapkidboqo.supabase.co"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "@Fr3qu3nc14.S1mp0s10"

@contextmanager
def obter_conexao():
    """Gerenciador de contexto adaptável para produção (Render) e local."""
    # 1. Tenta pegar a URL de conexão do Pooler configurada no Render
    url_producao = os.environ.get('DATABASE_URL')
    
    if url_producao:
        # Se estiver no Render, conecta usando a URL robusta do Pooler (porta 6543)
        conn = psycopg2.connect(url_producao)
    else:
        # Se estiver local (Termux/PC), usa os dados separados padrões
        conn = psycopg2.connect(
            host=DB_HOST, 
            port=DB_PORT, 
            database=DB_NAME, 
            user=DB_USER, 
            password=DB_PASS
        )
        
    try:
        # RealDictCursor faz o Postgres retornar os dados como dicionário
        yield conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        conn.commit()
    except Exception as erro:
        conn.rollback()
        raise erro
    finally:
        conn.close()

def obter_configuracao_global(chave: str) -> str:
    """Busca um valor da tabela de configurações globais."""
    with obter_conexao() as cursor:
        cursor.execute("SELECT valor FROM configuracoes WHERE chave = %s", (chave,))
        resultado = cursor.fetchone()
        return resultado['valor'] if resultado else None