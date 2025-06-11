import uuid
from datetime import datetime, timezone, timedelta

from flask import Blueprint, request, redirect, render_template

from app.usecases.ewc.utils import get_offer_data
from app.app_config.config_service import ConfService as cfgservice
from app.usecases.ewc import top_utilities

top_usecase = Blueprint("top_usecase", __name__, url_prefix="/top")


@top_usecase.route("/identification", methods=["GET"])
def start_identification():
    dossier_id = request.args.get("dossierId", default=str(uuid.uuid4()))
    identification_url = top_utilities.onboard(dossier_id=dossier_id)

    if not identification_url:
        cfgservice.app_logger.error("Failed to generate identification URL")
        return error_page("Failed to generate identification URL")

    return redirect(location=identification_url, code=302)


@top_usecase.route("/issue", methods=["GET"])
def issue_credential():
    try:
        dossier_id = request.args.get("dossierId")
        format = request.args.get("format", default="mdoc")
        if format not in ["mdoc", "vc_sd_jwt"]:
            cfgservice.app_logger.error("Invalid format specified")
            return error_page("Invalid format specified")
        if not dossier_id:
            cfgservice.app_logger.error("Missing dossier_id")
            return error_page("Missing dossier_id")

        dossier_info = top_utilities.get_dossier(dossier_id=dossier_id)

        if not dossier_info:
            cfgservice.app_logger.error("Failed to retrieve dossier information")
            return error_page("Failed to retrieve dossier information")

        identity_credential_id = "it.infocert.eudi.identity_" + format
        credential_data = {
            "given_name": dossier_info.signers[0].person.personal_data.full_first_name,
            "family_name": dossier_info.signers[0].person.personal_data.full_last_name,
            "tin": dossier_info.signers[0].person.personal_data.fiscal_code,
        }
        if dossier_info.signers[0].person.personal_data.birth_date:
            credential_data["birth_date"] = dossier_info.signers[0].person.personal_data.birth_date
        if dossier_info.signers[0].person.contact_details.email:
            credential_data["email"] = dossier_info.signers[0].person.contact_details.email
        if dossier_info.signers[0].person.contact_details.mobile_number:
            credential_data["phone_number"] = dossier_info.signers[0].person.contact_details.mobile_number


        payload = {
            "exp": datetime.now(timezone.utc) + timedelta(hours=5),
            "credentials": [
                {
                    "credential_configuration_id": identity_credential_id,
                    "data": credential_data
                }
            ]
        }

        offer_data = get_offer_data(payload, transaction_id=dossier_id)
        if not offer_data:
            cfgservice.app_logger.error("Unable to generate credential offer")
            return error_page("Unable to generate credential offer")

        return render_template(
            "ewc/top_issue_sample.html",
            credential_offer=offer_data.get("credential_offer"),
            uri=offer_data.get("uri"),
            qr_code=offer_data.get("qr_code"),
            tx_code=offer_data.get("tx_code"),
            transaction_id=offer_data.get("transaction_id"),
            dossier_info=dossier_info.signers[0].person
        )

    except Exception as e:
        cfgservice.app_logger.error(f"Error in issue_credential: {str(e)}")
        return error_page(f"Error in issue_credential: {str(e)}")




@top_usecase.route("/failure", methods=["GET"])
def identification_failure():
    return render_template("ewc/top_issue_failure.html")


def error_page(error_message):
    return render_template(
        "ewc/top_issue_failure.html",
        error_message=error_message
    )
