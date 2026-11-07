from time import time
from utils.security import marca_sessao
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import check_password_hash
from itsdangerous import URLSafeTimedSerializer
from extensions import limiter
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
@limiter.limit("15 per minute", methods=["POST"], key_func=lambda: request.remote_addr or "unknown")
def login():
    if 'usuario_id' in session:
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        identificador = request.form.get('matricula', '').strip().lower().replace(" ", "")
        senha = request.form.get('senha', '')
        usuario = auth_repository.buscar_usuario_por_identificador(identificador)

        if usuario and check_password_hash(usuario['senha'], senha):
            identificadores = (usuario['login'], usuario['matricula'], usuario['id_corporativo'])
            if (usuario['status_conta'] == 'pendente' and senha in identificadores) or (
                usuario['tipo'] == 'admin' and usuario['login'] == 'admin' and senha == 'admin123'
            ):
                flash("Solicite uma nova credencial à administração.", "erro")
                return render_template('login.html')
            session.clear()
            session['usuario_id'] = usuario['id']
            session['ultimo_acesso'] = int(time())
            session['marca_sessao'] = marca_sessao(usuario['senha'])
            session['nome'] = usuario['nome']
            session['tipo'] = usuario['tipo']
            session['status_conta'] = usuario['status_conta']

            if usuario['status_conta'] == 'pendente':
                return redirect(url_for('auth.concluir_cadastro'))
            return redirect(url_for('auth.index'))
        
        flash("Identificador ou senha incorretos.", "erro")
    return render_template('login.html')

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/primeiro-acesso', methods=['GET', 'POST'])
def primeiro_acesso():
    if 'usuario_id' in session: 
        return redirect(url_for('auth.index'))
        
    return render_template('primeiro_acesso.html')


@auth_bp.route('/concluir-cadastro', methods=['GET', 'POST'])
@requer_autenticacao
def concluir_cadastro():
    usuario = auth_repository.buscar_usuario_por_id(session['usuario_id'])
    cursos = admin_repository.listar_todos_cursos()
    
    cursos_usuario = auth_repository.buscar_cursos_usuario(session['usuario_id'])
    curso_atual_id = str(cursos_usuario[0]) if cursos_usuario else ""

    if request.method == 'POST':
        form_data = request.form
        if auth_repository.identificador_em_uso(form_data.get('email', '').strip(), usuario['id']):
            flash("Este e-mail já está em uso.", "erro")
            return redirect(request.path)

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

        if usuario['status_conta'] == 'pendente' and usuario['tipo'] in ('professor', 'admin') and senha_form == usuario['login']:
            flash("Por segurança, a nova senha deve ser diferente do ID corporativo e da senha provisória.", "erro")
            return render_template(
                'concluir_cadastro.html', cursos=cursos, usuario=usuario,
                form_data=form_data, curso_atual_id=curso_atual_id,
                erro_campo="senha"
            )
            
        login_form = form_data.get('login', '').strip().lower().replace(" ", "")
        
        if usuario['status_conta'] == 'pendente' and login_form != usuario['login']:
            if auth_repository.identificador_em_uso(login_form, usuario['id']):
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
        
        estado = auth_repository.buscar_estado_sessao(session['usuario_id'])
        if estado is None:
            session.clear()
            return redirect(url_for('auth.login'))
        session['marca_sessao'] = marca_sessao(estado['senha'])
        session['status_conta'] = 'ativa'
        session['nome'] = form_data.get('nome', '').strip()
        flash("Cadastro concluído com sucesso!", "sucesso")
        return redirect(url_for('auth.index'))

    return render_template('concluir_cadastro.html', cursos=cursos, usuario=usuario, form_data=request.form, curso_atual_id=curso_atual_id)

@auth_bp.route('/recuperar', methods=['GET', 'POST'])
def recuperar_senha():
    if 'usuario_id' in session: 
        return redirect(url_for('auth.index'))

    return render_template('recuperar.html')


@auth_bp.route('/editar-perfil', methods=['GET', 'POST'])
@requer_autenticacao
def editar_perfil():
    usuario = auth_repository.buscar_usuario_por_id(session['usuario_id'])
    
    cursos = admin_repository.listar_todos_cursos()
    cursos_usuario = auth_repository.buscar_cursos_usuario(session['usuario_id']) if usuario['tipo'] == 'aluno' else []
    curso_usuario_id = cursos_usuario[0] if cursos_usuario else None
    
    voltar_url = url_for({
        'professor': 'professor.professor_dashboard',
        'admin': 'admin.admin_painel',
        'aluno': 'aluno.aluno_dashboard',
    }.get(usuario['tipo'], 'auth.index'))

    if request.method == 'POST':
        form_data = request.form
        if auth_repository.identificador_em_uso(form_data.get('email', '').strip(), usuario['id']):
            flash("Este e-mail já está em uso.", "erro")
            return redirect(request.path)

        login_form = form_data.get('matricula', '').strip().lower().replace(" ", "")
        id_curso = form_data.get('curso') 
        
        voltar_url_post = voltar_url

        if usuario['status_conta'] == 'pendente' and login_form != usuario['login']:
            if auth_repository.identificador_em_uso(login_form, usuario['id']):
                flash("Este login único já está em uso.", "erro")
                return render_template('editar_perfil.html', usuario=usuario, cursos=cursos, curso_usuario_id=curso_usuario_id, voltar_url=voltar_url_post, form_data=form_data)
            login_final = login_form
        else:
            login_final = usuario['login']

        curso_final = int(id_curso) if (usuario['tipo'] == 'aluno' and id_curso and str(id_curso).isdigit()) else None
        
        try:
            auth_repository.atualizar_perfil_usuario(
                session['usuario_id'], form_data.get('nome').strip(), form_data.get('email').strip(),
                login_final, form_data.get('nova_senha') or None, curso_final
            )
            
            session['nome'] = form_data.get('nome').strip()
            flash("Perfil atualizado com sucesso!", "sucesso")
            return redirect(voltar_url_post)
            
        except Exception:
            current_app.logger.exception("profile_update_failed")
            flash("Não foi possível salvar as alterações.", "erro")
            return render_template('editar_perfil.html', usuario=usuario, cursos=cursos, curso_usuario_id=curso_usuario_id, voltar_url=voltar_url_post, form_data=form_data)

    return render_template('editar_perfil.html', usuario=usuario, cursos=cursos, curso_usuario_id=curso_usuario_id, voltar_url=voltar_url, form_data={})
