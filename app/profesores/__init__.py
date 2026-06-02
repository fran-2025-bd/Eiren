from flask import Blueprint

profesores_bp = Blueprint('profesores', __name__, url_prefix='/profesores')

from app.profesores import routes  # noqa