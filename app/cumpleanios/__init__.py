from flask import Blueprint

cumpleanios_bp = Blueprint('cumpleanios', __name__, url_prefix='/cumpleanios')

from app.cumpleanios import routes  # noqa
