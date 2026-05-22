from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import check_password_hash
from itsdangerous import URLSafeTimedSerializer
from utils.decorators import requer_autenticacao
from repositories import auth_repository, admin_repository

auth_bp = Blueprint('auth', __name__)

def obter_serializador():
    return URLSafeTimedSerializer(current_app.secret_key)

@auth_bp.route('/')
@requer_autenticacao
def index():
    tipo_usuario = session.get('tipo')
    if tipo_usuario == 'admin': 
        return redirect(url_for('admin.admin_painel'))
    elif tipo_usuario == 'professor': 
        return redirect(url_for('professor.professor_dashboard'))
    elif tipo_usuario == 'aluno': 
        return redirect(url_for('aluno.aluno_dashboard'))
    
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'usuario_id' in session:
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        identificador = request.form.get('matricula', '').strip().lower().replace(" ", "")
        senha = request.form.get('senha', '')
        usuario = auth_repository.buscar_usuario_por_identificador(identificador)

        if usuario and check_password_hash(usuario['senha'], senha):
            session['usuario_id'] = usuario['id']
            session['nome'] = usuario['nome']
            session['tipo'] = usuario['tipo']
            session['status_conta'] = usuario['status_conta']

            if usuario['status_conta'] == 'pendente':
                return redirect(url_for('auth.concluir_cadastro'))
            return redirect(url_for('auth.index'))
        
        flash("Identificador ou senha incorretos.", "erro")
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/primeiro-acesso', methods=['GET', 'POST'])
def primeiro_acesso():
    if 'usuario_id' in session: 
        return redirect(url_for('auth.index'))
        
    cursos = admin_repository.listar_todos_cursos()

    if request.method == 'POST':
        form_data = request.form
        matricula = form_data.get('matricula', '').strip()
        login_form = form_data.get('login', '').strip().lower().replace(" ", "")
        email = form_data.get('email', '').strip()
        senha_real = form_data.get('senha', '') 
        id_curso = form_data.get('curso') # 🚀 ALTERADO: Captura um único curso selecionado no dropdown

        if len(senha_real) < 6:
            flash("Erro de Segurança: A senha deve conter no mínimo 6 caracteres.", "erro")
            return render_template('primeiro_acesso.html', cursos=cursos, form_data=form_data, erro_campo="senha")
        
        if not matricula.isdigit() or len(matricula) != 10:
            flash("Erro de Validação: O RA/Matrícula deve conter exatamente 10 dígitos numéricos.", "erro")
            return render_template('primeiro_acesso.html', cursos=cursos, form_data=form_data, erro_campo="matricula")

        if not id_curso:
            flash("Erro de Validação: Você deve selecionar um curso.", "erro")
            return render_template('primeiro_acesso.html', cursos=cursos, form_data=form_data, erro_campo="curso")

        conflito = auth_repository.verificar_duplicidade_cadastro(matricula, login_form, email)
        if conflito:
            flash(f"Este {conflito} já consta registrado no sistema!", "erro")
            return render_template('primeiro_acesso.html', cursos=cursos, form_data=form_data, erro_campo=conflito)

        # 🚀 ALTERADO: Enviando int(id_curso) em vez de request.form.getlist('curso')
        auth_repository.cadastrar_primeiro_acesso_aluno(
            matricula, login_form, form_data.get('nome', '').strip(), email,
            senha_real, form_data.get('pergunta'), form_data.get('resposta', '').strip().lower(),
            int(id_curso)
        )
        
        flash("Cadastro realizado com sucesso! Faça login.", "sucesso")
        return redirect(url_for('auth.login'))

    return render_template('primeiro_acesso.html', cursos=cursos, form_data=request.form)

@auth_bp.route('/concluir-cadastro', methods=['GET', 'POST'])
@requer_autenticacao
def concluir_cadastro():
    usuario = auth_repository.buscar_usuario_por_id(session['usuario_id'])
    cursos = admin_repository.listar_todos_cursos()
    
    cursos_usuario = auth_repository.buscar_cursos_usuario(session['usuario_id'])
    curso_atual_id = str(cursos_usuario[0]) if cursos_usuario else ""

    if request.method == 'POST':
        form_data = request.form
        senha_form = form_data.get('senha', '')
        id_curso = form_data.get('curso')
        
        if len(senha_form) < 6:
            flash("Erro de Segurança: A senha deve conter no mínimo 6 caracteres.", "erro")
            return render_template(
                'concluir_cadastro.html', 
                cursos=cursos, 
                usuario=usuario, 
                form_data=form_data, 
                curso_atual_id=curso_atual_id,
                erro_campo="senha"
            )
            
        login_form = form_data.get('login', '').strip().lower().replace(" ", "")
        
        if usuario['status_conta'] == 'pendente' and login_form != usuario['login']:
            if auth_repository.buscar_usuario_por_identificador(login_form):
                flash("Este login único já está em uso.", "erro")
                return render_template('concluir_cadastro.html', cursos=cursos, usuario=usuario, form_data=form_data, curso_atual_id=curso_atual_id)
            login_final = login_form
        else:
            login_final = usuario['login']

        if usuario['tipo'] == 'aluno' and not id_curso:
            flash("Erro de Validação: Você deve selecionar um curso.", "erro")
            return render_template('concluir_cadastro.html', cursos=cursos, usuario=usuario, form_data=form_data, curso_atual_id=curso_atual_id)

        curso_final = int(id_curso) if (usuario['tipo'] == 'aluno' and id_curso) else None

        auth_repository.salvar_conclusao_cadastro(
            session['usuario_id'], form_data.get('nome', '').strip(), form_data.get('email', '').strip(),
            login_final, senha_form, form_data.get('pergunta'), 
            form_data.get('resposta', '').strip().lower(), curso_final
        )
        
        session['status_conta'] = 'ativa'
        session['nome'] = form_data.get('nome', '').strip()
        flash("Cadastro concluído com sucesso!", "sucesso")
        return redirect(url_for('auth.index'))

    return render_template('concluir_cadastro.html', cursos=cursos, usuario=usuario, form_data=request.form, curso_atual_id=curso_atual_id)

@auth_bp.route('/recuperar', methods=['GET', 'POST'])
def recuperar_senha():
    if 'usuario_id' in session: 
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        form_data = request.form
        matricula_form = form_data.get('matricula', '').strip()
        nova_senha = form_data.get('nova_senha', '') 

        usuario = auth_repository.buscar_usuario_por_identificador(matricula_form)
        
        if not usuario:
            flash("Matrícula ou Login não encontrados.", "erro")
            return render_template('recuperar.html', form_data=form_data, erro_campo='matricula')

        if len(nova_senha) < 6:
            flash("Erro de Segurança: A nova senha deve conter no mínimo 6 caracteres.", "erro")
            return render_template('recuperar.html', form_data=form_data, erro_campo='nova_senha')

        if usuario['pergunta_seguranca'] == form_data.get('pergunta') and check_password_hash(usuario['resposta_seguranca'], form_data.get('resposta', '').strip().lower()):
            auth_repository.atualizar_senha_recuperada(usuario['id'], nova_senha)
            flash("Senha alterada! Acesse com a nova credencial.", "sucesso")
            return redirect(url_for('auth.login'))
        else:
            flash("Dados de validação incorretos.", "erro")
            return render_template('recuperar.html', form_data=form_data, erro_campo='resposta')

    return render_template('recuperar.html', form_data=request.form)

@auth_bp.route('/editar-perfil', methods=['GET', 'POST'])
@requer_autenticacao
def editar_perfil():
    usuario = auth_repository.buscar_usuario_por_id(session['usuario_id'])

    if request.method == 'POST':
        form_data = request.form
        login_form = form_data.get('matricula', '').strip().lower().replace(" ", "")
        id_curso = form_data.get('curso') # 🚀 ALTERADO: Campo único para curso

        if usuario['status_conta'] == 'pendente' and login_form != usuario['login']:
            if auth_repository.buscar_usuario_por_identificador(login_form):
                flash("Este login único já está em uso.", "erro")
                return redirect(request.form.get('voltar_url') or url_for('auth.index'))
            login_final = login_form
        else:
            login_final = usuario['login']

        # 🚀 ALTERADO: Passando int(id_curso) se houver
        curso_final = int(id_curso) if id_curso else None
        auth_repository.atualizar_perfil_usuario(
            session['usuario_id'], form_data.get('nome').strip(), form_data.get('email').strip(),
            login_final, form_data.get('nova_senha') or None, curso_final
        )
        
        session['nome'] = form_data.get('nome').strip()
        flash("Perfil updated!", "sucesso")
        return redirect(form_data.get('voltar_url') or url_for('auth.index'))

    cursos = admin_repository.listar_todos_cursos()
    cursos_usuario = auth_repository.buscar_cursos_usuario(session['usuario_id']) if session.get('tipo') == 'aluno' else []
    curso_usuario_id = cursos_usuario[0] if cursos_usuario else None
    
    referer = request.referrer or ''
    voltar_url = url_for('professor.professor_dashboard') if '/professor' in referer else url_for('admin.admin_painel') if '/admin' in referer else url_for('aluno.aluno_dashboard')

    return render_template('editar_perfil.html', usuario=usuario, cursos=cursos, curso_usuario_id=curso_usuario_id, voltar_url=voltar_url)