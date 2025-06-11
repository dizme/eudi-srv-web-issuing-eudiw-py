from flask import Blueprint, url_for, render_template

from app.usecases.ewc.top_usecase import top_usecase
from app.usecases.ewc.itb_usecase import itb_bp

ewc_bp = Blueprint("ewc_usecase", __name__, url_prefix="/ewc")

# Register each ewc use case blueprint
ewc_bp.register_blueprint(top_usecase)
ewc_bp.register_blueprint(itb_bp)


@ewc_bp.route("/", methods=["GET"])
def ewc_home():
    """Renders the EWC home with identification and issuance options."""
    identification_url = url_for("usecases.ewc_usecase.top_usecase.start_identification", _external=True)
    issuance_url = url_for("usecases.ewc_usecase.top_usecase.issue_credential", _external=True)

    return render_template(
        "ewc/top_home.html",
        identification_url=identification_url,
        issuance_url=issuance_url,
    )
