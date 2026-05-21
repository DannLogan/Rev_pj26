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
        senha_real = form_data.get('senha', '') # 🚀 Captura o valor real digitado pelo usuário

        # 🚀 CORREÇÃO: Mede o tamanho da variável real digitada na tela
        if len(senha_real) < 6:
            flash("Erro de Segurança: A senha deve conter no mínimo 6 caracteres.", "erro")
            return render_template('primeiro_acesso.html', cursos=cursos, form_data=form_data, erro_campo="senha")

        conflito = auth_repository.verificar_duplicidade_cadastro(matricula, login_form, email)
        if conflito:
            flash(f"Este {conflito} já consta registrado no sistema!", "erro")
            return render_template('primeiro_acesso.html', cursos=cursos, form_data=form_data, erro_campo=conflito)

        auth_repository.cadastrar_primeiro_acesso_aluno(
            matricula, login_form, form_data.get('nome', '').strip(), email,
            senha_real, form_data.get('pergunta'), form_data.get('resposta', '').strip().lower(),
            request.form.getlist('curso')
        )
        
        flash("Cadastro realizado com sucesso! Faça login.", "sucesso")
        return redirect(url_for('auth.login'))

    return render_template('primeiro_acesso.html', cursos=cursos, form_data=request.form)

@auth_bp.route('/concluir-cadastro', methods=['GET', 'POST'])
@requer_autenticacao
def concluir_cadastro():
    usuario = auth_repository.buscar_usuario_por_id(session['usuario_id'])
    cursos = admin_repository.listar_todos_cursos()
    cursos_atuais_ids = [str(cid) for cid in auth_repository.buscar_cursos_usuario(session['usuario_id'])]

    if request.method == 'POST':
        form_data = request.form
        senha_form = form_data.get('senha', '')
        
        # 🚀 TRAVA DE SEGURANÇA: Bloqueia senhas menores que 6 caracteres
        if len(senha_form) < 6:
            flash("Erro de Segurança: A senha deve conter no mínimo 6 caracteres.", "erro")
            return render_template(
                'concluir_cadastro.html', 
                cursos=cursos, 
                usuario=usuario, 
                form_data=form_data, 
                cursos_atuais_ids=cursos_atuais_ids,
                erro_campo="senha"
            )
            
        login_form = form_data.get('login', '').strip().lower().replace(" ", "")
        
        if usuario['status_conta'] == 'pendente' and login_form != usuario['login']:
            if auth_repository.buscar_usuario_por_identificador(login_form):
                flash("Este login único já está em uso.", "erro")
                return render_template('concluir_cadastro.html', cursos=cursos, usuario=usuario, form_data=form_data, cursos_atuais_ids=cursos_atuais_ids)
            login_final = login_form
        else:
            login_final = usuario['login']

        auth_repository.salvar_conclusao_cadastro(
            session['usuario_id'], form_data.get('nome', '').strip(), form_data.get('email', '').strip(),
            login_final, senha_form, form_data.get('pergunta'), 
            form_data.get('resposta', '').strip().lower(), request.form.getlist('curso')
        )
        
        session['status_conta'] = 'ativa'
        session['nome'] = form_data.get('nome', '').strip()
        flash("Cadastro concluído com sucesso!", "sucesso")
        return redirect(url_for('auth.index'))

    return render_template('concluir_cadastro.html', cursos=cursos, usuario=usuario, form_data=request.form, cursos_atuais_ids=cursos_atuais_ids)

@auth_bp.route('/recuperar', methods=['GET', 'POST'])
def recuperar_senha():
    if 'usuario_id' in session: 
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        form_data = request.form
        matricula_form = form_data.get('matricula', '').strip()
        nova_senha = form_data.get('nova_senha', '') # 🚀 Captura a nova senha enviada

        usuario = auth_repository.buscar_usuario_por_identificador(matricula_form)
        
        if not usuario:
            flash("Matrícula ou Login não encontrados.", "erro")
            return render_template('recuperar.html', form_data=form_data, erro_campo='matricula')

        # 🚀 TRAVA DE SEGURANÇA BACKEND: Verifica o tamanho da nova senha informada
        if len(nova_senha) < 6:
            flash("Erro de Segurança: A nova senha deve conter no mínimo 6 caracteres.", "erro")
            return render_template('recuperar.html', form_data=form_data, erro_campo='nova_senha')

        # Se o tamanho da senha estiver correto, prossegue para validar a pergunta/resposta
        if usuario['pergunta_seguranca'] == form_data.get('pergunta') and check_password_hash(usuario['resposta_seguranca'], form_data.get('resposta', '').strip().lower()):
            
            # Executa a atualização segura no banco de dados
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
        
        if usuario['status_conta'] == 'pendente' and login_form != usuario['login']:
            if auth_repository.buscar_usuario_por_identificador(login_form):
                flash("Este login único já está em uso.", "erro")
                return redirect(request.form.get('voltar_url') or url_for('auth.index'))
            login_final = login_form
        else:
            login_final = usuario['login']

        auth_repository.atualizar_perfil_usuario(
            session['usuario_id'], form_data.get('nome').strip(), form_data.get('email').strip(),
            login_final, form_data.get('nova_senha') or None, form_data.getlist('cursos')
        )
        
        session['nome'] = form_data.get('nome').strip()
        flash("Perfil atualizado!", "sucesso")
        return redirect(form_data.get('voltar_url') or url_for('auth.index'))

    cursos = admin_repository.listar_todos_cursos()
    cursos_usuario = auth_repository.buscar_cursos_usuario(session['usuario_id']) if session.get('tipo') == 'aluno' else []
    
    referer = request.referrer or ''
    voltar_url = url_for('professor.professor_dashboard') if '/professor' in referer else url_for('admin.admin_painel') if '/admin' in referer else url_for('aluno.aluno_dashboard')

    return render_template('editar_perfil.html', usuario=usuario, cursos=cursos, cursos_usuario=cursos_usuario, voltar_url=voltar_url)