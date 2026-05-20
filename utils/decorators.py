from functools import wraps
from flask import session, flash, redirect, url_for, request, current_app

def requer_autenticacao(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # TRAVA DE TESTE: Ignora completamente a autenticação em ambiente de testes
        if current_app.config.get('TESTING'):
            return f(*args, **kwargs)

        if 'usuario_id' not in session:
            flash("Por favor, faça login para acessar o sistema.", "erro")
            return redirect(url_for('auth.login'))

        if session.get('status_conta') == 'pendente' and request.endpoint not in ['auth.concluir_cadastro', 'auth.logout']:
            flash("Ação obrigatória: Conclua a configuração da sua conta.", "aviso")
            return redirect(url_for('auth.concluir_cadastro'))

        return f(*args, **kwargs)
    return decorated_function

def requer_perfil(perfil_exigido):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # TRAVA DE TESTE: Ignora o bloqueio de perfil em ambiente de testes
            if current_app.config.get('TESTING'):
                return f(*args, **kwargs)

            if session.get('tipo') != perfil_exigido:
                flash(f"Acesso negado. Área restrita para {perfil_exigido}.", "erro")
                tipo = session.get('tipo')
                if tipo == 'admin': return redirect(url_for('admin.admin_painel'))
                elif tipo == 'professor': return redirect(url_for('professor.professor_dashboard'))
                elif tipo == 'aluno': return redirect(url_for('aluno.aluno_dashboard'))
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator