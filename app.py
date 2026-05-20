import os
from datetime import timedelta
from flask import Flask

# Importação de todos os Blueprints do projeto
from blueprints.auth import auth_bp
from blueprints.aluno import aluno_bp
from blueprints.professor import professor_bp
from blueprints.admin import admin_bp

def create_app(configuracao_teste=None):
    app = Flask(__name__)
    
    app.secret_key = os.environ.get('SECRET_KEY', 'chave_segura_unifametro_2026')
    app.permanent_session_lifetime = timedelta(days=7)

    if configuracao_teste:
        app.config.update(configuracao_teste)

    # Registro de todas as rotas modularizadas
    app.register_blueprint(auth_bp)
    app.register_blueprint(aluno_bp)
    app.register_blueprint(professor_bp)
    app.register_blueprint(admin_bp)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)