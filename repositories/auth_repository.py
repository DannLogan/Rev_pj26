import uuid
from db import obter_conexao
from werkzeug.security import generate_password_hash

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


def salvar_conclusao_cadastro(usuario_id: int, nome: str, email: str, login: str, senha_bruta: str, pergunta: str, resposta_bruta: str, cursos_ids: any) -> None:
    with obter_conexao() as cursor:
        senha_hash = generate_password_hash(senha_bruta)
        resposta_hash = generate_password_hash(resposta_bruta)
        
        cursor.execute("""
            UPDATE usuarios 
            SET nome = %s, email_institucional = %s, login = %s, senha = %s, 
                pergunta_seguranca = %s, resposta_seguranca = %s, status_conta = 'ativa' 
            WHERE id = %s
        """, (nome, email, login, senha_hash, pergunta, resposta_hash, usuario_id))
        
        cursor.execute("SELECT tipo FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        
        if usuario and usuario['tipo'] == 'aluno':
            # Segurança adicional: Garante que contas antigas ou importadas ganhem um qr_token caso não possuam
            cursor.execute("SELECT qr_token FROM alunos WHERE id_usuario = %s", (usuario_id,))
            reg_aluno = cursor.fetchone()
            if reg_aluno and not reg_aluno['qr_token']:
                cursor.execute("UPDATE alunos SET qr_token = %s WHERE id_usuario = %s", (str(uuid.uuid4()), usuario_id))

            cursor.execute("DELETE FROM usuarios_cursos WHERE id_aluno = %s", (usuario_id,))
            
            # 🚀 BLINDAGEM DO TIPO: Se vier apenas um ID inteiro, transforma em lista
            if isinstance(cursos_ids, int):
                cursos_ids = [cursos_ids]
            elif cursos_ids is None:
                cursos_ids = []
                
            # Remove duplicatas com segurança e roda o laço sem erros
            for c_id in list(set(cursos_ids)):
                if c_id:
                    cursor.execute("INSERT INTO usuarios_cursos (id_aluno, id_curso) VALUES (%s, %s)", (usuario_id, int(c_id)))
                    
def atualizar_perfil_usuario(usuario_id: int, nome: str, email: str, login: str = None, nova_senha_bruta: str = None, cursos_ids: list = None) -> None:
    with obter_conexao() as cursor:
        campos = ["nome = %s", "email_institucional = %s"]
        valores = [nome, email]
        
        if login:
            campos.append("login = %s")
            valores.append(login)
        if nova_senha_bruta:
            campos.append("senha = %s")
            valores.append(generate_password_hash(nova_senha_bruta))
            
        valores.append(usuario_id)
        sql = f"UPDATE usuarios SET {', '.join(campos)} WHERE id = %s"
        cursor.execute(sql, tuple(valores))
            
        cursor.execute("SELECT tipo FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        
        if usuario and usuario['tipo'] == 'aluno' and cursos_ids is not None:
            cursor.execute("DELETE FROM usuarios_cursos WHERE id_aluno = %s", (usuario_id,))
            for c_id in cursos_ids:
                cursor.execute("INSERT INTO usuarios_cursos (id_aluno, id_curso) VALUES (%s, %s)", (usuario_id, c_id))

def buscar_cursos_usuario(usuario_id: int) -> list:
    with obter_conexao() as cursor:
        cursor.execute("SELECT id_curso FROM usuarios_cursos WHERE id_aluno = %s", (usuario_id,))
        return [row['id_curso'] for row in cursor.fetchall()]

def atualizar_senha_recuperada(usuario_id: int, nova_senha_bruta: str) -> None:
    sql = "UPDATE usuarios SET senha = %s WHERE id = %s"
    with obter_conexao() as cursor:
        cursor.execute(sql, (generate_password_hash(nova_senha_bruta), usuario_id))

def buscar_estado_sessao(usuario_id: int) -> dict | None:
    with obter_conexao() as cursor:
        cursor.execute(
            "SELECT tipo, status_conta, senha FROM usuarios WHERE id = %s AND ativo = 1",
            (usuario_id,),
        )
        return cursor.fetchone()
