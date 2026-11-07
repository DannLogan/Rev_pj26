import uuid
import secrets
from db import obter_conexao, resolver_id_edicao
from psycopg2 import IntegrityError
from werkzeug.security import generate_password_hash

def obter_nome_edicao_ativa() -> str:
    """Busca o nome textual (ex: '2026.1') da edição que está ativa no momento."""
    with obter_conexao() as cursor:
        cursor.execute("SELECT valor FROM configuracoes WHERE chave = 'edicao_ativa'")
        res_config = cursor.fetchone()
        if not res_config:
            return "Sem_Edicao"
            
        valor_bruto = res_config['valor'].strip()

        if valor_bruto.isdigit():
            cursor.execute("SELECT nome_edicao FROM edicoes WHERE id = %s", (int(valor_bruto),))
        else:
            cursor.execute("SELECT nome_edicao FROM edicoes WHERE nome_edicao = %s", (valor_bruto,))
            
        res_edicao = cursor.fetchone()
        
        return res_edicao['nome_edicao'].strip() if res_edicao else valor_bruto

def obter_projetos_vinculados_admin(id_admin: int) -> list:
    sql = """
        SELECT p.id, p.nome_projeto 
        FROM supervisores_projeto sp 
        JOIN projetos p ON sp.id_projeto = p.id 
        WHERE sp.id_professor = %s
    """
    with obter_conexao() as cursor:
        cursor.execute(sql, (id_admin,))
        return cursor.fetchall()
    
def obter_cursos_ids_do_usuario(id_usuario: int) -> list:
    sql = "SELECT id_curso FROM usuarios_cursos WHERE id_aluno = %s"
    with obter_conexao() as cursor:
        cursor.execute(sql, (id_usuario,))
        return [row['id_curso'] for row in cursor.fetchall()]

def obter_inscricoes_ids_do_usuario(id_usuario: int) -> list:
    sql = "SELECT id_projeto FROM inscricoes WHERE id_aluno = %s"
    with obter_conexao() as cursor:
        cursor.execute(sql, (id_usuario,))
        return [row['id_projeto'] for row in cursor.fetchall()]

def obter_projetos_ids_do_usuario(id_usuario: int) -> list:
    sql = "SELECT id_projeto FROM supervisores_projeto WHERE id_professor = %s"
    with obter_conexao() as cursor:
        cursor.execute(sql, (id_usuario,))
        return [row['id_projeto'] for row in cursor.fetchall()]

def verificar_vinculos_alunos(tipo: str, target_id: int) -> list:
    if tipo == 'curso':
        sql = "SELECT u.nome FROM usuarios u JOIN usuarios_cursos uc ON u.id = uc.id_aluno WHERE uc.id_curso = %s"
    else:
        sql = "SELECT u.nome FROM usuarios u JOIN inscricoes i ON u.id = i.id_aluno WHERE i.id_projeto = %s"
    with obter_conexao() as cursor:
        cursor.execute(sql, (target_id,))
        return [row['nome'] for row in cursor.fetchall()]

def listar_todos_cursos() -> list:
    sql = "SELECT * FROM cursos ORDER BY ativo DESC, nome_curso ASC"
    with obter_conexao() as cursor:
        cursor.execute(sql)
        return cursor.fetchall()

def salvar_curso(nome: str, curso_id: int = None) -> None:
    with obter_conexao() as cursor:
        if curso_id:
            cursor.execute("UPDATE cursos SET nome_curso = %s WHERE id = %s", (nome, curso_id))
        else:
            cursor.execute("INSERT INTO cursos (nome_curso, ativo) VALUES (%s, 1)", (nome,))

def alternar_status_curso(id_curso: int) -> str:
    with obter_conexao() as cursor:
        cursor.execute("SELECT nome_curso, ativo FROM cursos WHERE id = %s", (id_curso,))
        curso = cursor.fetchone()
        if curso:
            novo_status = 0 if curso['ativo'] == 1 else 1
            cursor.execute("UPDATE cursos SET ativo = %s WHERE id = %s", (novo_status, id_curso))
            return curso['nome_curso']
    return None

def listar_todos_projetos() -> list:
    sql = "SELECT * FROM projetos ORDER BY ativo DESC, nome_projeto ASC"
    with obter_conexao() as cursor:
        cursor.execute(sql)
        return cursor.fetchall()

def salvar_projeto(nome: str, projeto_id: int = None) -> None:
    with obter_conexao() as cursor:
        if projeto_id:
            cursor.execute("UPDATE projetos SET nome_projeto = %s WHERE id = %s", (nome, projeto_id))
        else:
            cursor.execute("INSERT INTO projetos (nome_projeto, ativo) VALUES (%s, 1)", (nome,))

def alternar_status_projeto(id_projeto: int) -> str:
    with obter_conexao() as cursor:
        cursor.execute("SELECT nome_projeto, ativo FROM projetos WHERE id = %s", (id_projeto,))
        proj = cursor.fetchone()
        if proj:
            novo_status = 0 if proj['ativo'] == 1 else 1
            cursor.execute("UPDATE projetos SET ativo = %s WHERE id = %s", (novo_status, id_projeto))
            return proj['nome_projeto']
    return None

def listar_projetos_ativos_por_edicao(id_edicao: any = None) -> list:
    """Retorna os projetos ativos globais protegendo contra parâmetros nulos ou sobressalentes."""
    sql = "SELECT id, nome_projeto FROM projetos WHERE ativo = 1 ORDER BY nome_projeto ASC"
    with obter_conexao() as cursor:
        cursor.execute(sql)
        return cursor.fetchall()

def listar_usuarios_painel_paginado(busca_matricula: str, tipo_filtro: str, letra_filtro: str, pagina: int, limite: int = 50) -> tuple:
    offset = (pagina - 1) * limite
    condicoes = []
    parametros = []
    
    if busca_matricula:
        condicoes.append("(a.matricula LIKE %s OR p.id_corporativo LIKE %s)")
        parametros.extend([f"%{busca_matricula}%", f"%{busca_matricula}%"])
    if tipo_filtro:
        condicoes.append("u.tipo = %s")
        parametros.append(tipo_filtro)
        
    if letra_filtro:
        condicoes.append("u.nome ILIKE %s")
        parametros.append(f"{letra_filtro}%")
        
    where_clause = " WHERE " + " AND ".join(condicoes) if condicoes else ""
    
    sql_dados = f"""
        SELECT u.id, u.nome, COALESCE(a.matricula, p.id_corporativo) AS matricula, u.tipo, u.status_conta, u.ativo 
        FROM usuarios u 
        LEFT JOIN alunos a ON u.id = a.id_usuario 
        LEFT JOIN professores p ON u.id = p.id_usuario
        {where_clause}
        ORDER BY u.nome ASC
        LIMIT %s OFFSET %s
    """
    
    sql_count = f"""
        SELECT COUNT(*) as total 
        FROM usuarios u 
        LEFT JOIN alunos a ON u.id = a.id_usuario 
        LEFT JOIN professores p ON u.id = p.id_usuario
        {where_clause}
    """
    
    with obter_conexao() as cursor:
        cursor.execute(sql_count, parametros)
        total = cursor.fetchone()['total']
        
        cursor.execute(sql_dados, parametros + [limite, offset])
        usuarios = cursor.fetchall()
        
    return usuarios, total

def cadastrar_usuario_manual(nome: str, identificador: str, tipo: str, senha_hash: str, chave_unica: str, cursos: any, projetos: list, inscricoes: list, id_edicao: str) -> str:
    with obter_conexao() as cursor:
        id_real_edicao = resolver_id_edicao(cursor, id_edicao)
        
        # =====================================================================
        # FLUXO 1: CADASTRO DE ALUNO (Mantém a consistência original do RA)
        # =====================================================================
        if tipo == 'aluno':
            # Cria o hash da própria matrícula informada
            senha_aluno_hash = senha_hash
            
            cursor.execute("""
                INSERT INTO usuarios (nome, login, senha, tipo, status_conta, chave_acesso, ativo)
                VALUES (%s, %s, %s, %s, 'pendente', %s, 1) RETURNING id
            """, (nome, identificador, senha_aluno_hash, tipo, chave_unica))
            novo_id = cursor.fetchone()['id']

            qr_token = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO alunos (id_usuario, matricula, origem_cadastro, qr_token) 
                VALUES (%s, %s, 'manual', %s)
            """, (novo_id, identificador, qr_token))
            
            if isinstance(cursos, int):
                cursos = [cursos]
            elif cursos is None:
                cursos = []

            for c_id in list(set(cursos)):
                if c_id:
                    cursor.execute("INSERT INTO usuarios_cursos (id_aluno, id_curso) VALUES (%s, %s)", (novo_id, int(c_id)))
                    
            for p_id in list(set(inscricoes)):
                if p_id:
                    cursor.execute("INSERT INTO inscricoes (id_aluno, id_projeto, id_edicao, presenca) VALUES (%s, %s, %s, 0)", (novo_id, p_id, id_real_edicao))
            
            return identificador

        # =====================================================================
        # FLUXO 2: CADASTRO DE PROFESSOR OU ADMIN (Gerador Sequencial com Máscara)
        # =====================================================================
        elif tipo in ['professor', 'admin']:
            # 1. Usa as sequências mantidas pelo schema, preservando o comportamento original.
            if tipo == 'professor':
                cursor.execute("SELECT nextval('public.seq_id_professor') AS numero;")
                num = cursor.fetchone()['numero']
                id_corporativo_gerado = str(num).zfill(5)
            else:
                cursor.execute("SELECT nextval('public.seq_id_admin') AS numero;")
                num = cursor.fetchone()['numero']
                id_corporativo_gerado = str(num).zfill(4)

            senha_colaborador_hash = senha_hash

            # 3. Insere o registro na tabela principal 'usuarios' usando o ID como login
            cursor.execute("""
                INSERT INTO usuarios (nome, login, senha, tipo, status_conta, chave_acesso, ativo)
                VALUES (%s, %s, %s, %s, 'pendente', %s, 1) RETURNING id
            """, (nome, id_corporativo_gerado, senha_colaborador_hash, tipo, chave_unica))
            novo_id = cursor.fetchone()['id']
            
            # 4. Vincula o usuário na tabela 'professores' injetando o id_corporativo padronizado
            cursor.execute("""
                INSERT INTO professores (id_usuario, id_corporativo) 
                VALUES (%s, %s)
                ON CONFLICT (id_usuario) DO UPDATE SET id_corporativo = EXCLUDED.id_corporativo
            """, (novo_id, id_corporativo_gerado))
            
            # 5. Salva os vínculos de projetos do professor coordenador/supervisor
            for p_id in list(set(projetos)):
                if p_id:
                    cursor.execute("INSERT INTO supervisores_projeto (id_professor, id_projeto) VALUES (%s, %s)", (novo_id, p_id))
            
            # Retorna o ID gerado para que a Blueprint do Admin exiba na mensagem flash
            return id_corporativo_gerado
                            
def obter_lista_inscricoes_aluno(id_aluno: int, id_edicao: str) -> list:
    with obter_conexao() as cursor:
        id_real_edicao = resolver_id_edicao(cursor, id_edicao)
        sql = "SELECT id_projeto FROM inscricoes WHERE id_aluno = %s AND id_edicao = %s"
        cursor.execute(sql, (id_aluno, id_real_edicao))
        return [row['id_projeto'] for row in cursor.fetchall()]

def atualizar_usuario_admin(id_usuario: int, nome: str, tipo: str, cursos_ids: any, projetos_ids: list, inscricoes_ids: list, id_edicao: str, senha_provisoria_hash: str | None, identificador: str) -> None:
    with obter_conexao() as cursor:
        id_real_edicao = resolver_id_edicao(cursor, id_edicao)
        
        cursor.execute("UPDATE usuarios SET nome = %s, tipo = %s WHERE id = %s", (nome, tipo, id_usuario))
        cursor.execute("DELETE FROM usuarios_cursos WHERE id_aluno = %s", (id_usuario,))
        cursor.execute("DELETE FROM supervisores_projeto WHERE id_professor = %s", (id_usuario,))
        
        if tipo == 'aluno':
            cursor.execute("""
                INSERT INTO alunos (id_usuario, matricula, origem_cadastro, qr_token)
                VALUES (%s, %s, 'manual', %s)
                ON CONFLICT (id_usuario) DO UPDATE SET matricula = EXCLUDED.matricula
            """, (id_usuario, identificador, str(uuid.uuid4())))

            # 🚀 CORREÇÃO CURSO ÚNICO: Normaliza o inteiro para lista, blindando contra o erro 'int' object is not iterable
            if isinstance(cursos_ids, int):
                cursos_ids = [cursos_ids]
            elif cursos_ids is None:
                cursos_ids = []

            for c_id in cursos_ids:
                if c_id:
                    cursor.execute("INSERT INTO usuarios_cursos (id_aluno, id_curso) VALUES (%s, %s)", (id_usuario, int(c_id)))
            
            cursor.execute("SELECT id_projeto, presenca FROM inscricoes WHERE id_aluno = %s AND id_edicao = %s", (id_usuario, id_real_edicao))
            atuais = cursor.fetchall()
            atuais_dict = {row['id_projeto']: row['presenca'] for row in atuais}
            
            selecionados = [int(x) for x in inscricoes_ids] if inscricoes_ids else []
            
            for p_id, presenca in atuais_dict.items():
                if p_id not in selecionados and presenca == 0:
                    cursor.execute("DELETE FROM inscricoes WHERE id_aluno = %s AND id_projeto = %s AND id_edicao = %s AND presenca = 0", (id_usuario, p_id, id_real_edicao))
            
            for p_id in selecionados:
                if p_id not in atuais_dict:
                    cursor.execute("INSERT INTO inscricoes (id_aluno, id_projeto, id_edicao, presenca) VALUES (%s, %s, %s, 0)", (id_usuario, p_id, id_real_edicao))
        
        elif tipo in ['professor', 'admin']:
            cursor.execute("""
                INSERT INTO professores (id_usuario, id_corporativo) 
                VALUES (%s, %s) 
                ON CONFLICT (id_usuario) DO UPDATE SET id_corporativo = EXCLUDED.id_corporativo
            """, (id_usuario, identificador))
            
            if projetos_ids:
                for p_id in projetos_ids:
                    if p_id:
                        cursor.execute("INSERT INTO supervisores_projeto (id_professor, id_projeto) VALUES (%s, %s)", (id_usuario, p_id))
                
        if senha_provisoria_hash:
            cursor.execute("UPDATE usuarios SET senha = %s, status_conta = 'pendente' WHERE id = %s", (senha_provisoria_hash, id_usuario))
                        
def alternar_status_usuario(id_usuario: int) -> dict:
    with obter_conexao() as cursor:
        cursor.execute("SELECT ativo, nome FROM usuarios WHERE id = %s", (id_usuario,))
        usuario = cursor.fetchone()
        if usuario:
            novo_estado = 0 if usuario['ativo'] == 1 else 1
            cursor.execute("UPDATE usuarios SET ativo = %s WHERE id = %s", (novo_estado, id_usuario))
            return {"nome": usuario['nome'], "novo_estado": novo_estado}
    return None

def preparar_novo_ciclo_limpeza(cursor):
    """Apaga os vínculos temporários (supervisores) e garante que todos os alunos tenham um QR Code."""
    cursor.execute("DELETE FROM supervisores_projeto;")

    cursor.execute("""
        UPDATE alunos 
        SET qr_token = gen_random_uuid()::text 
        WHERE qr_token IS NULL;
    """)

def atualizar_edicao_ativa(nova_edicao: str) -> str:
    nova_edicao = str(nova_edicao).strip()
    
    with obter_conexao() as cursor:
        cursor.execute("""
            INSERT INTO configuracoes (chave, valor) VALUES ('edicao_ativa', '')
            ON CONFLICT (chave) DO NOTHING
        """)
        cursor.execute("SELECT valor FROM configuracoes WHERE chave = 'edicao_ativa' FOR UPDATE")
        config_atual = cursor.fetchone()
        
        if config_atual:
            id_atual = config_atual['valor']
            if str(id_atual).isdigit():
                cursor.execute("SELECT nome_edicao FROM edicoes WHERE id = %s", (int(id_atual),))
                nome_atual = cursor.fetchone()
                if nome_atual and nome_atual['nome_edicao'] == nova_edicao:
                    return 'ja_ativa'

        cursor.execute("SELECT 1 FROM edicoes WHERE nome_edicao = %s", (nova_edicao,))
        if cursor.fetchone():
            return 'ja_existe'
            
        cursor.execute("""
            INSERT INTO edicoes (nome_edicao) 
            VALUES (%s) 
            RETURNING id
        """, (nova_edicao,))
        id_final = cursor.fetchone()['id']
        
        # 🚀 PASSO 4 AQUI: Limpa os vínculos do ciclo anterior ANTES de ativar o novo
        preparar_novo_ciclo_limpeza(cursor)
            
        cursor.execute("""
            UPDATE configuracoes 
            SET valor = %s 
            WHERE chave = 'edicao_ativa'
        """, (str(id_final),))
        
        return 'sucesso'

def verificar_vinculos_projeto(id_projeto: int, id_edicao_ativa: str) -> bool:
    """Retorna True se o projeto tiver qualquer aluno inscrito ou professor supervisor neste ciclo."""
    with obter_conexao() as cursor:
        id_real_edicao = resolver_id_edicao(cursor, id_edicao_ativa)
        
        sql = """
            SELECT EXISTS (
                -- Cenário A: Verifica se existem alunos inscritos neste projeto para a edição atual
                SELECT 1 FROM inscricoes 
                WHERE id_projeto = %s AND id_edicao = %s
                
                UNION ALL
                
                -- Cenário B: Verifica se existem professores orientando este projeto
                SELECT 1 FROM supervisores_projeto 
                WHERE id_projeto = %s
            ) AS possui_vinculo;
        """
        
        cursor.execute(sql, (id_projeto, id_real_edicao, id_projeto))
        resultado = cursor.fetchone()
        return resultado['possui_vinculo'] if resultado else False    
    
def processar_importacao_csv(linhas: list, id_edicao: str) -> tuple:
    credenciais = []
    erros = 0
    
    with obter_conexao() as cursor:
        for linha in linhas:
            if not linha or len(linha) < 2:
                erros += 1
                continue
                
            matricula = str(linha[0]).strip()
            nome = str(linha[1]).strip()
            email = str(linha[2]).strip() if len(linha) > 2 else f"{matricula}@substituir.edu.br"
            
            if not matricula.isdigit() or len(matricula) != 10:
                erros += 1
                continue

            cursor.execute("SELECT 1 FROM usuarios WHERE login = %s", (matricula,))
            if cursor.fetchone():
                erros += 1
                continue

            cursor.execute("SAVEPOINT importacao_linha")
            try:
                senha_provisoria = secrets.token_urlsafe(18)
                senha_padrao_hash = generate_password_hash(senha_provisoria)
                chave_unica = str(uuid.uuid4())
                qr_token_novo = str(uuid.uuid4())

                cursor.execute("""
                    INSERT INTO usuarios (nome, login, email_institucional, senha, tipo, status_conta, chave_acesso)
                    VALUES (%s, %s, %s, %s, 'aluno', 'pendente', %s)
                    RETURNING id
                """, (nome, matricula, email, senha_padrao_hash, chave_unica))
                
                novo_id_usuario = cursor.fetchone()['id']

                cursor.execute("""
                    INSERT INTO alunos (id_usuario, matricula, origem_cadastro, qr_token)
                    VALUES (%s, %s, 'csv', %s)
                """, (novo_id_usuario, matricula, qr_token_novo))

                credenciais.append((matricula, senha_provisoria))

            except IntegrityError:
                cursor.execute("ROLLBACK TO SAVEPOINT importacao_linha")
                erros += 1
            cursor.execute("RELEASE SAVEPOINT importacao_linha")

    return credenciais, erros

def obter_relatorio_geral_presencas(id_edicao: str) -> list:
    with obter_conexao() as cursor:
        id_real_edicao = resolver_id_edicao(cursor, id_edicao)
        sql = """
            SELECT u.nome, a.matricula, c.nome_curso, p.nome_projeto, e.nome_edicao,
                CASE WHEN i.presenca = 1 THEN 'Presente' ELSE 'Faltou' END as status
            FROM usuarios u
            JOIN alunos a ON u.id = a.id_usuario
            JOIN inscricoes i ON u.id = i.id_aluno
            JOIN projetos p ON i.id_projeto = p.id
            JOIN edicoes e ON i.id_edicao = e.id
            LEFT JOIN usuarios_cursos uc ON a.id_usuario = uc.id_aluno
            LEFT JOIN cursos c ON uc.id_curso = c.id
            WHERE i.id_edicao = %s 
            ORDER BY u.nome ASC
        """
        cursor.execute(sql, (id_real_edicao,))
        return cursor.fetchall()

def projeto_esta_ativo(id_projeto: int) -> bool:
    with obter_conexao() as cursor:
        cursor.execute("SELECT ativo FROM projetos WHERE id = %s", (id_projeto,))
        projeto = cursor.fetchone()
        return bool(projeto and projeto['ativo'] == 1)

def buscar_usuario_por_login(login: str) -> dict:
    with obter_conexao() as cursor:
        cursor.execute("SELECT id FROM usuarios WHERE login = %s", (login,))
        return cursor.fetchone()

def obter_usuario_admin(id_usuario: int) -> dict:
    with obter_conexao() as cursor:
        cursor.execute("SELECT id, nome, login, email_institucional, tipo, status_conta FROM usuarios WHERE id = %s", (id_usuario,))
        return cursor.fetchone()

def obter_identificador_usuario(id_usuario: int, tipo: str) -> str:
    tabela, coluna = ('alunos', 'matricula') if tipo == 'aluno' else ('professores', 'id_corporativo')
    with obter_conexao() as cursor:
        cursor.execute(f"SELECT {coluna} FROM {tabela} WHERE id_usuario = %s", (id_usuario,))
        resultado = cursor.fetchone()
        return resultado[coluna] if resultado else ""

def obter_nome_edicao(id_edicao: str) -> str:
    with obter_conexao() as cursor:
        valor = str(id_edicao).strip()
        cursor.execute("SELECT nome_edicao FROM edicoes WHERE id = %s" if valor.isdigit() else "SELECT nome_edicao FROM edicoes WHERE nome_edicao = %s", (int(valor) if valor.isdigit() else valor,))
        resultado = cursor.fetchone()
        return resultado['nome_edicao'] if resultado else "Não configurado"
