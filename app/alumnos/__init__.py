from flask import Blueprint

alumnos_bp = Blueprint('alumnos', __name__, url_prefix='/alumnos')

from app.alumnos import routes  # noqa
