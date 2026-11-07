import os
from flask import Flask
from werkzeug.exceptions import HTTPException
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect
from extensions import limiter
from config import Config

# Importação de todos os Blueprints do projeto
from blueprints.auth import auth_bp
from blueprints.aluno import aluno_bp
from blueprints.professor import professor_bp
from blueprints.admin import admin_bp

def create_app(configuracao_teste=None):
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(Config)

    if configuracao_teste:
        app.config.update(configuracao_teste)

    @app.before_request
    def configure_session_lifetime():
        session_type = __import__('flask').session.get('tipo')
        app.permanent_session_lifetime = (
            app.config['ADMIN_SESSION_LIFETIME']
            if session_type == 'admin'
            else app.config['COMMON_SESSION_LIFETIME']
        )

    @app.after_request
    def set_device_cookie(response):
        from utils.security import DEVICE_COOKIE, new_device_id
        if not __import__('flask').request.cookies.get(DEVICE_COOKIE):
            response.set_cookie(
                DEVICE_COOKIE,
                new_device_id(),
                max_age=60 * 60 * 24 * 365,
                httponly=True,
                secure=app.config['SESSION_COOKIE_SECURE'],
                samesite='Lax',
            )
        return response

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        if isinstance(error, HTTPException):
            return error
        app.logger.exception('Erro não tratado na aplicação', exc_info=error)
        return 'Ocorreu um erro interno. Tente novamente mais tarde.', 500

    csrf = CSRFProtect(app)
    limiter.init_app(app)
    app.extensions['csrf'] = csrf
    app.extensions['limiter'] = limiter

    # Registro de todas as rotas modularizadas
    app.register_blueprint(auth_bp)
    app.register_blueprint(aluno_bp)
    app.register_blueprint(professor_bp)
    app.register_blueprint(admin_bp)

    from utils.logging import configure_logging
    configure_logging(app)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)
