from flask import Blueprint

# Import each use case blueprint
from .ewc import ewc_bp

usecases_bp = Blueprint("usecases", __name__, url_prefix="/usecases")

# Register each use case blueprint
usecases_bp.register_blueprint(ewc_bp)