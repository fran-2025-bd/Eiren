from flask import Blueprint

caja_bp = Blueprint('caja', __name__, url_prefix='/caja')

from app.caja import routes  # noqa
