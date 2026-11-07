from db import bloquear_edicao_ativa, obter_conexao, resolver_id_edicao

def obter_dashboard_aluno(usuario_id: int, id_edicao_ativa: str) -> dict:
    with obter_conexao() as cursor:
        id_real_edicao = resolver_id_edicao(cursor, id_edicao_ativa)

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
        id_real_edicao = resolver_id_edicao(cursor, id_edicao_ativa)
        cursor.execute(sql, (usuario_id, id_real_edicao))
        return cursor.fetchall()

def realizar_inscricao_manual(id_aluno: int, id_projeto: int) -> str:
    with obter_conexao() as cursor:
        id_edicao = resolver_id_edicao(cursor, bloquear_edicao_ativa(cursor))
        if id_edicao is None:
            return 'indisponivel'

        cursor.execute("""
            SELECT id FROM projetos WHERE id = %s AND ativo = 1 FOR SHARE
        """, (id_projeto,))
        if cursor.fetchone() is None:
            return 'indisponivel'

        cursor.execute("""
            INSERT INTO inscricoes (id_aluno, id_projeto, id_edicao, presenca)
            VALUES (%s, %s, %s, 0)
            ON CONFLICT (id_aluno, id_projeto, id_edicao) DO NOTHING
            RETURNING 1
        """, (id_aluno, id_projeto, id_edicao))
        return 'sucesso' if cursor.fetchone() is not None else 'ja_inscrito'


def cancelar_inscricao_pendente(id_aluno: int, id_projeto: int, id_edicao: str) -> int:
    sql = "DELETE FROM inscricoes WHERE id_aluno = %s AND id_projeto = %s AND id_edicao = %s AND presenca = 0"
    with obter_conexao() as cursor:
        edicao_ativa = bloquear_edicao_ativa(cursor)
        if edicao_ativa is None or edicao_ativa != id_edicao:
            return 0
        id_real_edicao = resolver_id_edicao(cursor, edicao_ativa)
        cursor.execute(sql, (id_aluno, id_projeto, id_real_edicao))
        return cursor.rowcount

def obter_token_qr(id_aluno: int) -> str | None:
    with obter_conexao() as cursor:
        cursor.execute("""
            SELECT a.qr_token FROM alunos a
            JOIN usuarios u ON u.id = a.id_usuario
            WHERE a.id_usuario = %s AND u.ativo = 1
        """, (id_aluno,))
        aluno = cursor.fetchone()
        return aluno['qr_token'] if aluno else None
