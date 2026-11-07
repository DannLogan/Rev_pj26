import os
from contextlib import contextmanager
import psycopg2
import psycopg2.extras

# Configurações de acesso ao Supabase (Padrão para desenvolvimento local)
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS")

@contextmanager
def obter_conexao():
    """Gerenciador de contexto adaptável para produção (Render) e local."""
    # 1. Tenta pegar a URL de conexão do Pooler configurada no Render
    url_producao = os.environ.get('DATABASE_URL')
    
    if url_producao:
        # Se estiver no Render, conecta usando a URL robusta do Pooler (porta 6543)
        conn = psycopg2.connect(url_producao, connect_timeout=5)
    else:
        if not all((DB_HOST, DB_PASS)):
            raise RuntimeError("DATABASE_URL ou DB_HOST/DB_PASS devem ser configurados")
        # Se estiver local (Termux/PC), usa os dados separados padrões
        conn = psycopg2.connect(
            host=DB_HOST, 
            port=DB_PORT, 
            database=DB_NAME, 
            user=DB_USER, 
            connect_timeout=5,
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


def bloquear_edicao_ativa(cursor) -> str | None:
    """Lê a configuração e impede a troca da edição até o fim da transação."""
    cursor.execute("""
        SELECT valor FROM configuracoes
        WHERE chave = 'edicao_ativa' FOR SHARE
    """)
    configuracao = cursor.fetchone()
    return configuracao['valor'] if configuracao else None
