from flask import Flask, render_template
from psycopg2 import OperationalError
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

    @app.errorhandler(OperationalError)
    def handle_database_unavailable(error):
        app.logger.error("database_unavailable", exc_info=error)
        return render_template("indisponivel.html"), 503

    from utils.logging import configure_logging
    configure_logging(app)

    @app.get('/health')
    def health():
        return {"status": "ok"}

    @app.get('/ready')
    def readiness():
        from db import obter_conexao

        try:
            with obter_conexao() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            app.logger.exception("database_unavailable")
            return {"status": "unavailable"}, 503
        return {"status": "ok"}

    csrf = CSRFProtect(app)
    limiter.init_app(app)
    app.extensions['csrf'] = csrf
    app.extensions['limiter'] = limiter

    # Registro de todas as rotas modularizadas
    app.register_blueprint(auth_bp)
    app.register_blueprint(aluno_bp)
    app.register_blueprint(professor_bp)
    app.register_blueprint(admin_bp)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)
