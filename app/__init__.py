import os
from flask import Flask, redirect, url_for
from config import config
from app.extensions import db, login_manager

def create_app(env=None):
    app = Flask(__name__)

    env = env or os.environ.get('FLASK_ENV', 'default')
    app.config.from_object(config[env])

    db.init_app(app)
    login_manager.init_app(app)

    # Blueprints
    from app.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.alumnos import alumnos_bp
    app.register_blueprint(alumnos_bp)

    from app.profesores import profesores_bp
    app.register_blueprint(profesores_bp)

    from app.cursos import cursos_bp
    app.register_blueprint(cursos_bp)

    from app.asistencia import asistencia_bp
    app.register_blueprint(asistencia_bp)

    from app.caja import caja_bp
    app.register_blueprint(caja_bp)

    from app.usuarios import usuarios_bp
    app.register_blueprint(usuarios_bp)

    from app.cumpleanios import cumpleanios_bp  
    app.register_blueprint(cumpleanios_bp)

    # Filtro de moneda argentina — sin centavos, separador de miles con punto
    def formato_moneda(valor):
        if valor is None:
            return '0'
        redondeado = int(round(float(valor)))
        return f'{redondeado:,}'.replace(',', '.')

    app.jinja_env.filters['moneda'] = formato_moneda

    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    return app
