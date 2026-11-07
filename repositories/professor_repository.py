from db import bloquear_edicao_ativa, obter_conexao, resolver_id_edicao


def buscar_aluno_por_qr_token(qr_token: str) -> dict | None:
    with obter_conexao() as cursor:
        cursor.execute("""
            SELECT u.id, u.nome, a.matricula
            FROM usuarios u JOIN alunos a ON u.id = a.id_usuario
            WHERE a.qr_token = %s AND u.tipo = 'aluno' AND u.ativo = 1
            LIMIT 2
        """, (qr_token,))
        alunos = cursor.fetchall()
        return alunos[0] if len(alunos) == 1 else None


def obter_projetos_supervisor(id_professor: int, edicao: str) -> list:
    with obter_conexao() as cursor:
        cursor.execute("""
            SELECT p.id, p.nome_projeto, c.id AS id_curso, c.nome_curso,
                   COUNT(uc.id_aluno) AS total_inscritos,
                   COUNT(uc.id_aluno) FILTER (WHERE i.presenca = 1) AS total_presentes
            FROM supervisores_projeto_curso sp
            JOIN projetos p ON p.id = sp.id_projeto AND p.ativo = 1
            JOIN cursos c ON c.id = sp.id_curso
            LEFT JOIN inscricoes i ON i.id_projeto = p.id AND i.id_edicao = %s
            LEFT JOIN usuarios_cursos uc ON uc.id_aluno = i.id_aluno AND uc.id_curso = c.id
            WHERE sp.id_professor = %s
            GROUP BY p.id, p.nome_projeto, c.id, c.nome_curso
            ORDER BY p.nome_projeto, c.nome_curso
        """, (resolver_id_edicao(cursor, edicao), id_professor))
        return cursor.fetchall()


def obter_projeto_por_id_e_professor(id_projeto: int, id_professor: int, id_curso: int) -> dict | None:
    with obter_conexao() as cursor:
        cursor.execute("""
            SELECT p.id, p.nome_projeto, c.id AS id_curso, c.nome_curso
            FROM supervisores_projeto_curso sp
            JOIN projetos p ON p.id = sp.id_projeto AND p.ativo = 1
            JOIN cursos c ON c.id = sp.id_curso
            WHERE sp.id_professor = %s AND sp.id_projeto = %s AND sp.id_curso = %s
        """, (id_professor, id_projeto, id_curso))
        return cursor.fetchone()


def obter_nome_edicao(edicao: str) -> str:
    with obter_conexao() as cursor:
        cursor.execute("SELECT nome_edicao FROM edicoes WHERE id = %s", (resolver_id_edicao(cursor, edicao),))
        resultado = cursor.fetchone()
        return resultado['nome_edicao'] if resultado else "Não configurado"


def registrar_presenca_aluno(
    id_aluno: int, id_projeto: int, id_edicao: str, id_professor: int, id_curso: int
) -> str:
    with obter_conexao() as cursor:
        edicao_ativa = bloquear_edicao_ativa(cursor)
        if edicao_ativa is None or edicao_ativa != id_edicao:
            return 'edicao_indisponivel'

        cursor.execute("""
            SELECT 1 FROM supervisores_projeto_curso sp
            JOIN projetos p ON p.id = sp.id_projeto AND p.ativo = 1
            WHERE sp.id_professor = %s AND sp.id_projeto = %s AND sp.id_curso = %s
            FOR SHARE OF sp, p
        """, (id_professor, id_projeto, id_curso))
        if cursor.fetchone() is None:
            raise PermissionError("Projeto ou curso indisponível para o professor")

        cursor.execute("""
            SELECT 1 FROM usuarios_cursos uc
            JOIN usuarios u ON u.id = uc.id_aluno AND u.tipo = 'aluno' AND u.ativo = 1
            WHERE uc.id_aluno = %s AND uc.id_curso = %s
            FOR SHARE OF uc, u
        """, (id_aluno, id_curso))
        if cursor.fetchone() is None:
            return 'fora_do_escopo'

        id_real_edicao = resolver_id_edicao(cursor, id_edicao)
        if id_real_edicao is None:
            return 'edicao_indisponivel'
        chave = (id_aluno, id_projeto, id_real_edicao)
        cursor.execute("""
            UPDATE inscricoes SET presenca = 1
            WHERE id_aluno = %s AND id_projeto = %s AND id_edicao = %s
              AND presenca IS DISTINCT FROM 1
            RETURNING 1
        """, chave)
        if cursor.fetchone() is not None:
            return 'sucesso'

        cursor.execute("""
            SELECT 1 FROM inscricoes
            WHERE id_aluno = %s AND id_projeto = %s AND id_edicao = %s AND presenca = 1
        """, chave)
        return 'ja_presente' if cursor.fetchone() is not None else 'nao_inscrito'


def listar_chamadas_supervisor(id_professor: int, edicao: str, id_projeto=None, id_curso=None) -> list:
    if (id_projeto is None) != (id_curso is None):
        raise ValueError("Informe projeto e curso juntos.")

    filtros = ""
    parametros = [id_professor]
    if id_projeto is not None and id_curso is not None:
        filtros = "AND sp.id_projeto = %s AND sp.id_curso = %s"
        parametros.extend((id_projeto, id_curso))

    with obter_conexao() as cursor:
        parametros.insert(0, resolver_id_edicao(cursor, edicao))
        cursor.execute(f"""
            SELECT p.nome_projeto, c.nome_curso, u.nome, a.matricula, i.presenca, e.nome_edicao
            FROM supervisores_projeto_curso sp
            JOIN projetos p ON p.id = sp.id_projeto AND p.ativo = 1
            JOIN cursos c ON c.id = sp.id_curso
            JOIN inscricoes i ON i.id_projeto = p.id AND i.id_edicao = %s
            JOIN usuarios_cursos uc ON uc.id_aluno = i.id_aluno AND uc.id_curso = c.id
            JOIN usuarios u ON u.id = i.id_aluno
            JOIN alunos a ON a.id_usuario = u.id
            JOIN edicoes e ON e.id = i.id_edicao
            WHERE sp.id_professor = %s {filtros}
            ORDER BY p.nome_projeto, c.nome_curso, u.nome, u.id
        """, parametros)
        return cursor.fetchall()
