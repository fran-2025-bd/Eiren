from flask import Blueprint

asistencia_bp = Blueprint('asistencia', __name__, url_prefix='/asistencia')

from app.asistencia import routes  # noqa
