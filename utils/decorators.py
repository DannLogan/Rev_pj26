from functools import wraps
from hmac import compare_digest
from time import time

from repositories.auth_repository import buscar_estado_sessao
from utils.security import marca_sessao
from flask import abort, current_app, flash, g, redirect, request, session, url_for

def requer_autenticacao(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash("Por favor, faça login para acessar o sistema.", "erro")
            return redirect(url_for('auth.login'))

        usuario = buscar_estado_sessao(session['usuario_id'])
        duracao = current_app.config[
            'ADMIN_SESSION_LIFETIME' if session.get('tipo') == 'admin' else 'COMMON_SESSION_LIFETIME'
        ].total_seconds()
        if (
            not usuario
            or usuario['tipo'] != session.get('tipo')
            or time() - session.get('ultimo_acesso', 0) >= duracao
            or not compare_digest(session.get('marca_sessao', ''), marca_sessao(usuario['senha']))
        ):
            session.clear()
            return redirect(url_for('auth.login'))

        session['ultimo_acesso'] = int(time())
        session['status_conta'] = usuario['status_conta']
        g.permissoes = frozenset(usuario["permissoes"])

        if session.get('status_conta') == 'pendente' and request.endpoint not in ['auth.concluir_cadastro', 'auth.logout']:
            flash("Ação obrigatória: Conclua a configuração da sua conta.", "aviso")
            return redirect(url_for('auth.concluir_cadastro'))

        return f(*args, **kwargs)
    return decorated_function

def requer_perfil(perfil_exigido):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('tipo') != perfil_exigido:
                flash(f"Acesso negado. Área restrita para {perfil_exigido}.", "erro")
                tipo = session.get('tipo')
                if tipo == 'admin': return redirect(url_for('admin.admin_painel'))
                elif tipo == 'professor': return redirect(url_for('professor.professor_dashboard'))
                elif tipo == 'aluno': return redirect(url_for('aluno.aluno_dashboard'))
                return redirect(url_for('auth.login'))
            operacao = "read" if request.method in {"GET", "HEAD", "OPTIONS"} else "write"
            if f"{request.endpoint}.{operacao}" not in g.get("permissoes", ()):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
