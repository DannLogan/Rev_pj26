from db import obter_conexao

def _obter_id_edicao_por_nome(cursor, nome_edicao: str) -> int:
    """Função utilitária interna robusta que aceita tanto o ID numérico quanto o Nome textual."""
    if not nome_edicao:
        return None
        
    nome_edicao_limpo = str(nome_edicao).strip()
    
    # Se o valor recebido for puramente numérico (o ID '7' vindo do banco), retorna ele mesmo
    if nome_edicao_limpo.isdigit():
        cursor.execute("SELECT id FROM edicoes WHERE id = %s", (int(nome_edicao_limpo),))
        res = cursor.fetchone()
        if res:
            return res['id']
            
    # Caso receba o nome textual (fallback de segurança), busca o ID correspondente
    cursor.execute("SELECT id FROM edicoes WHERE nome_edicao = %s", (nome_edicao_limpo,))
    res = cursor.fetchone()
    return res['id'] if res else None

def buscar_aluno_por_qr_token(qr_token: str) -> dict:
    sql = """
        SELECT u.id, u.nome, a.matricula
        FROM usuarios u
        JOIN alunos a ON u.id = a.id_usuario
        WHERE a.qr_token = %s AND u.tipo = 'aluno' AND u.ativo = 1
    """
    with obter_conexao() as cursor:
        cursor.execute(sql, (qr_token,))
        return cursor.fetchone()
    
def obter_projetos_supervisor(id_professor: int, id_edicao_ativa: str) -> list:
    sql = """
        SELECT p.id, p.nome_projeto, 
               COUNT(i.id_aluno) AS total_inscritos, 
               COALESCE(SUM(i.presenca), 0) AS total_presentes
        FROM projetos p 
        JOIN supervisores_projeto sp ON p.id = sp.id_projeto
        LEFT JOIN inscricoes i ON p.id = i.id_projeto AND i.id_edicao = %s
        WHERE sp.id_professor = %s AND p.ativo = 1 
        GROUP BY p.id, p.nome_projeto
    """
    with obter_conexao() as cursor:
        id_real_edicao = _obter_id_edicao_por_nome(cursor, id_edicao_ativa)
        cursor.execute(sql, (id_real_edicao, id_professor))
        return cursor.fetchall()

def obter_projeto_por_id_e_professor(id_projeto: int, id_professor: int) -> dict:
    sql = """
        SELECT p.id, p.nome_projeto 
        FROM projetos p 
        JOIN supervisores_projeto sp ON p.id = sp.id_projeto 
        WHERE p.id = %s AND sp.id_professor = %s
    """
    with obter_conexao() as cursor:
        cursor.execute(sql, (id_projeto, id_professor))
        return cursor.fetchone()

def obter_projeto_por_id(id_projeto: int) -> dict:
    sql = "SELECT id, nome_projeto FROM projetos WHERE id = %s"
    with obter_conexao() as cursor:
        cursor.execute(sql, (id_projeto,))
        return cursor.fetchone()

def buscar_aluno_por_chave_acesso(chave_acesso: str) -> dict:
    sql = """
        SELECT u.id, u.nome 
        FROM usuarios u 
        JOIN alunos a ON u.id = a.id_usuario 
        WHERE u.chave_acesso = %s AND u.tipo = 'aluno'
    """
    with obter_conexao() as cursor:
        cursor.execute(sql, (chave_acesso,))
        return cursor.fetchone()

def obter_inscricao_aluno(id_aluno: int, id_projeto: int, id_edicao: str) -> dict:
    sql = "SELECT presenca FROM inscricoes WHERE id_aluno = %s AND id_projeto = %s AND id_edicao = %s"
    with obter_conexao() as cursor:
        id_real_edicao = _obter_id_edicao_por_nome(cursor, id_edicao)
        cursor.execute(sql, (id_aluno, id_projeto, id_real_edicao))
        return cursor.fetchone()

def registrar_presenca_aluno(id_aluno: int, id_projeto: int, id_edicao: str) -> str:
    """
    Tenta registrar a presença do aluno convertendo o nome da edição para ID.
    Retorna:
        'sucesso' - Se a presença foi computada agora.
        'ja_presente' - Se o aluno já havia recebido presença antes.
        'nao_inscrito' - Se o aluno não está cadastrado neste projeto/edição.
    """
    with obter_conexao() as cursor:
        id_real_edicao = _obter_id_edicao_por_nome(cursor, id_edicao)
        
        # 1. Verifica se a inscrição existe e qual o estado atual dela
        cursor.execute("""
            SELECT presenca FROM inscricoes 
            WHERE id_aluno = %s AND id_projeto = %s AND id_edicao = %s
        """, (id_aluno, id_projeto, id_real_edicao))
        
        inscricao = cursor.fetchone()
        
        if not inscricao:
            return 'nao_inscrito'
            
        if inscricao['presenca'] == 1:
            return 'ja_presente'
            
        # 2. Se chegou aqui, está inscrito e com presença pendente. Atualiza!
        cursor.execute("""
            UPDATE inscricoes SET presenca = 1 
            WHERE id_aluno = %s AND id_projeto = %s AND id_edicao = %s
        """, (id_aluno, id_projeto, id_real_edicao))
        return 'sucesso'

def forçar_inscricao_com_presenca(id_aluno: int, id_projeto: int, id_edicao: str) -> None:
    sql = "INSERT INTO inscricoes (id_aluno, id_projeto, id_edicao, presenca) VALUES (%s, %s, %s, 1)"
    with obter_conexao() as cursor:
        id_real_edicao = _obter_id_edicao_por_nome(cursor, id_edicao)
        cursor.execute(sql, (id_aluno, id_projeto, id_real_edicao))

def listar_alunos_inscritos_no_projeto(id_projeto: int, id_edicao: str) -> list:
    sql = """
        SELECT 
            u.nome, 
            a.matricula, 
            i.presenca,
            COALESCE(c.nome_curso, 'Não Informado') AS nome_curso,
            e.nome_edicao
        FROM usuarios u 
        JOIN alunos a ON u.id = a.id_usuario
        JOIN inscricoes i ON u.id = i.id_aluno
        JOIN edicoes e ON i.id_edicao = e.id
        LEFT JOIN usuarios_cursos uc ON a.id_usuario = uc.id_aluno
        LEFT JOIN cursos c ON uc.id_curso = c.id
        WHERE i.id_projeto = %s AND i.id_edicao = %s 
        ORDER BY u.nome
    """
    with obter_conexao() as cursor:
        id_real_edicao = _obter_id_edicao_por_nome(cursor, id_edicao)
        cursor.execute(sql, (id_projeto, id_real_edicao))
        return cursor.fetchall()