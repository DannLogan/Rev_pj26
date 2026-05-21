from db import obter_conexao

def _obter_id_edicao_por_nome(cursor, nome_edicao: str) -> int:
    """Função utilitária interna robusta para obter o ID numérico a partir do nome ou do próprio ID."""
    if not nome_edicao:
        return None
        
    nome_edicao_limpo = str(nome_edicao).strip()
    
    # Cenário A: Se o valor recebido já for puramente numérico (o ID salvo nas configurações)
    if nome_edicao_limpo.isdigit():
        cursor.execute("SELECT id FROM edicoes WHERE id = %s", (int(nome_edicao_limpo),))
        res = cursor.fetchone()
        if res:
            return res['id']
            
    # Cenário B: Caso receba o nome textual da edição (fallback seguro)
    cursor.execute("SELECT id FROM edicoes WHERE nome_edicao = %s", (nome_edicao_limpo,))
    res = cursor.fetchone()
    return res['id'] if res else None

def obter_dashboard_aluno(usuario_id: int, id_edicao_ativa: str) -> dict:
    with obter_conexao() as cursor:
        id_real_edicao = _obter_id_edicao_por_nome(cursor, id_edicao_ativa)

        # Ajustado para trazer o qr_token essencial para a renderização do QR Code
        cursor.execute("""
            SELECT a.matricula, a.qr_token, u.chave_acesso 
            FROM usuarios u 
            JOIN alunos a ON u.id = a.id_usuario 
            WHERE u.id = %s
        """, (usuario_id,))
        dados_aluno = cursor.fetchone()

        sql_inscricoes = """
            SELECT p.id as projeto_id, p.nome_projeto, i.presenca, 
                   TO_CHAR(i.data_inscricao, 'DD/MM/YYYY') as data_formatada
            FROM inscricoes i 
            JOIN projetos p ON i.id_projeto = p.id
            WHERE i.id_aluno = %s AND i.id_edicao = %s 
            ORDER BY i.data_inscricao DESC
        """
        cursor.execute(sql_inscricoes, (usuario_id, id_real_edicao))
        inscricoes = cursor.fetchall()

        sql_projetos = """
            SELECT id, nome_projeto 
            FROM projetos 
            WHERE ativo = 1 AND id NOT IN (
                SELECT id_projeto FROM inscricoes WHERE id_aluno = %s AND id_edicao = %s
            ) 
            ORDER BY nome_projeto
        """
        cursor.execute(sql_projetos, (usuario_id, id_real_edicao))
        projetos_disponiveis = cursor.fetchall()

        return {
            "aluno": dados_aluno, 
            "inscricoes": inscricoes, 
            "projetos_disponiveis": projetos_disponiveis
        }

def obter_historico_aluno(usuario_id: int, id_edicao_ativa: str) -> list:
    sql = """
        SELECT p.nome_projeto, e.nome_edicao as edicao_simposio
        FROM inscricoes i
        JOIN projetos p ON i.id_projeto = p.id
        JOIN edicoes e ON i.id_edicao = e.id
        WHERE i.id_aluno = %s AND i.presenca = 1 AND i.id_edicao != %s
        ORDER BY e.nome_edicao DESC, p.nome_projeto ASC
    """
    with obter_conexao() as cursor:
        id_real_edicao = _obter_id_edicao_por_nome(cursor, id_edicao_ativa)
        cursor.execute(sql, (usuario_id, id_real_edicao))
        return cursor.fetchall()

def verificar_inscricao_existente(id_aluno: int, id_projeto: int, id_edicao: str) -> dict:
    sql = "SELECT 1 FROM inscricoes WHERE id_aluno = %s AND id_projeto = %s AND id_edicao = %s"
    with obter_conexao() as cursor:
        id_real_edicao = _obter_id_edicao_por_nome(cursor, id_edicao)
        cursor.execute(sql, (id_aluno, id_projeto, id_real_edicao))
        return cursor.fetchone()

def realizar_inscricao_manual(id_aluno: int, id_projeto: int, id_edicao: str) -> None:
    sql = "INSERT INTO inscricoes (id_aluno, id_projeto, id_edicao, presenca) VALUES (%s, %s, %s, 0)"
    with obter_conexao() as cursor:
        id_real_edicao = _obter_id_edicao_por_nome(cursor, id_edicao)
        cursor.execute(sql, (id_aluno, id_projeto, id_real_edicao))

def registrar_auto_presenca(id_aluno: int, id_projeto: int, id_edicao: str) -> None:
    sql = """
        INSERT INTO inscricoes (id_aluno, id_projeto, id_edicao, presenca) 
        VALUES (%s, %s, %s, 1)
        ON CONFLICT (id_aluno, id_projeto, id_edicao) DO UPDATE SET presenca = 1
    """
    with obter_conexao() as cursor:
        id_real_edicao = _obter_id_edicao_por_nome(cursor, id_edicao)
        cursor.execute(sql, (id_aluno, id_projeto, id_real_edicao))

def cancelar_inscricao_pendente(id_aluno: int, id_projeto: int, id_edicao: str) -> int:
    sql = "DELETE FROM inscricoes WHERE id_aluno = %s AND id_projeto = %s AND id_edicao = %s AND presenca = 0"
    with obter_conexao() as cursor:
        id_real_edicao = _obter_id_edicao_por_nome(cursor, id_edicao)
        cursor.execute(sql, (id_aluno, id_projeto, id_real_edicao))
        return cursor.rowcount