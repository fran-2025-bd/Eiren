from flask import Blueprint

cursos_bp = Blueprint('cursos', __name__, url_prefix='/cursos')

from app.cursos import routes  # noqa
