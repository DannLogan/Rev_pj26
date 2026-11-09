import uuid
from db import obter_conexao
from utils.passwords import hash_password

def buscar_usuario_por_identificador(identificador: str) -> dict:
    sql = """
        SELECT u.*, a.matricula, p.id_corporativo
        FROM usuarios u 
        LEFT JOIN alunos a ON u.id = a.id_usuario 
        LEFT JOIN professores p ON u.id = p.id_usuario
        WHERE (u.login = %s OR lower(replace(u.email_institucional, ' ', '')) = %s
               OR a.matricula = %s OR p.id_corporativo = %s)
          AND u.ativo = 1
        LIMIT 2
    """
    with obter_conexao() as cursor:
        cursor.execute(sql, (identificador, identificador, identificador, identificador))
        usuarios = cursor.fetchall()
        return usuarios[0] if len(usuarios) == 1 else None

def buscar_usuario_por_id(usuario_id: int) -> dict:
    sql = """
        SELECT u.*, a.matricula, p.id_corporativo
        FROM usuarios u 
        LEFT JOIN alunos a ON u.id = a.id_usuario 
        LEFT JOIN professores p ON u.id = p.id_usuario
        WHERE u.id = %s
    """
    with obter_conexao() as cursor:
        cursor.execute(sql, (usuario_id,))
        return cursor.fetchone()

def identificador_em_uso_no_cursor(cursor, identificador: str, usuario_id: int = 0) -> bool:
    if not identificador:
        return False
    cursor.execute("""
        SELECT 1 FROM usuarios u
        LEFT JOIN alunos a ON a.id_usuario = u.id
        LEFT JOIN professores p ON p.id_usuario = u.id
        WHERE u.id <> %s AND %s IN (u.login, u.email_institucional, a.matricula, p.id_corporativo)
        LIMIT 1
    """, (usuario_id, identificador))
    return cursor.fetchone() is not None


def identificador_em_uso(identificador: str, usuario_id: int) -> bool:
    with obter_conexao() as cursor:
        return identificador_em_uso_no_cursor(cursor, identificador, usuario_id)


def salvar_conclusao_cadastro(
    usuario_id: int, nome: str, email: str, login: str, senha_bruta: str,
    senha_anterior_hash: str, curso_id: int | None,
) -> str | None:
    senha_hash = hash_password(senha_bruta)
    with obter_conexao() as cursor:
        cursor.execute("""
            UPDATE usuarios
            SET nome = %s, email_institucional = %s, login = %s, senha = %s,
                status_conta = 'ativa'
            WHERE id = %s AND senha = %s AND status_conta = 'pendente' AND ativo = 1
            RETURNING tipo
        """, (nome, email, login, senha_hash, usuario_id, senha_anterior_hash))
        usuario = cursor.fetchone()
        if usuario is None:
            return None

        if usuario['tipo'] == 'aluno':
            # Segurança adicional: Garante que contas antigas ou importadas ganhem um qr_token caso não possuam
            cursor.execute("SELECT qr_token FROM alunos WHERE id_usuario = %s", (usuario_id,))
            reg_aluno = cursor.fetchone()
            if reg_aluno and not reg_aluno['qr_token']:
                cursor.execute("UPDATE alunos SET qr_token = %s WHERE id_usuario = %s", (str(uuid.uuid4()), usuario_id))

            if curso_id is not None:
                cursor.execute(
                    "INSERT INTO usuarios_cursos (id_aluno, id_curso) VALUES (%s, %s) "
                    "ON CONFLICT DO NOTHING",
                    (usuario_id, curso_id),
                )

    return senha_hash


def atualizar_perfil_usuario(usuario_id: int, nome: str, email: str, login: str = None, nova_senha_bruta: str = None) -> None:
    with obter_conexao() as cursor:
        campos = ["nome = %s", "email_institucional = %s"]
        valores = [nome, email]
        
        if login:
            campos.append("login = %s")
            valores.append(login)
        if nova_senha_bruta:
            campos.append("senha = %s")
            valores.append(hash_password(nova_senha_bruta))
            
        valores.append(usuario_id)
        sql = f"UPDATE usuarios SET {', '.join(campos)} WHERE id = %s"
        cursor.execute(sql, tuple(valores))
            

def buscar_cursos_usuario(usuario_id: int) -> list:
    with obter_conexao() as cursor:
        cursor.execute("SELECT id_curso FROM usuarios_cursos WHERE id_aluno = %s", (usuario_id,))
        return [row['id_curso'] for row in cursor.fetchall()]

def buscar_estado_sessao(usuario_id: int) -> dict | None:
    with obter_conexao() as cursor:
        cursor.execute(
            """
            SELECT u.tipo, u.status_conta, u.senha,
                   ARRAY(
                       SELECT p.codigo
                       FROM rbac_permissoes p
                       LEFT JOIN rbac_papel_permissoes rp ON rp.papel = u.tipo AND rp.permissao = p.codigo
                       LEFT JOIN rbac_usuario_permissoes up ON up.id_usuario = u.id AND up.permissao = p.codigo
                       WHERE COALESCE(up.permitido, rp.permissao IS NOT NULL)
                   ) AS permissoes
            FROM usuarios u WHERE u.id = %s AND u.ativo = 1
            """,
            (usuario_id,),
        )
        return cursor.fetchone()
