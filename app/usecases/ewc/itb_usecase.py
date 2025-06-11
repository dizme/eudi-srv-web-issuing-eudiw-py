import uuid
from datetime import datetime, timezone, timedelta

from flask import Blueprint, request, render_template, jsonify

from app.usecases.ewc.utils import get_offer_data
from app.app_config.config_service import ConfService as cfgservice
from app.data_management import transactions_statuses

itb_bp = Blueprint("itb_bp", __name__, url_prefix="/itb")

# https://marmot-civil-gratefully.ngrok-free.app/ewc/itb/issuanceRequest?sessionId=123&credentialType=it.infocert.eudi.identity_vc_sd_jwt
@itb_bp.route("/issuanceRequest", methods=["GET"])
def issuance_request():
    try:
        session_id = request.args.get("sessionId")
        credential_type = request.args.get("credentialType")
        if not credential_type:
            cfgservice.app_logger.error("Missing credentialType")
            return jsonify({
                "status": "fail",
                "reason": "credential type not supported",
                "sessionId": "123"
            }), 500

        if not session_id:
            session_id = str(uuid.uuid4())

        supported_credential_types = ["it.infocert.eudi.identity_mdoc", "it.infocert.eudi.identity_vc_sd_jwt"]
        if credential_type not in supported_credential_types:
            cfgservice.app_logger.error("Unsupported credential type")
            return jsonify({
                "status": "fail",
                "reason": "credential type not supported",
                "sessionId": session_id
            }), 500

        identity_credential_id = credential_type
        credential_data = {
            "given_name": "Mario",
            "family_name": "Smith",
            "tax_id_code": "SMITHM123456789",
            "birth_date": "1980-01-01",
            "email": "mario.smith@email.com",
            "phone_number": "3659123456"
        }


        payload = {
            "exp": datetime.now(timezone.utc) + timedelta(hours=5),
            "credentials": [
                {
                    "credential_configuration_id": identity_credential_id,
                    "data": credential_data
                }
            ]
        }

        offer_data = get_offer_data(payload, transaction_id=session_id, tx_code="11111")
        if not offer_data:
            cfgservice.app_logger.error("Unable to generate credential offer")
            raise Exception("Unable to generate credential offer")

        return jsonify(
            {
                "qr": offer_data["qr_code"],
                "sessionId": offer_data["transaction_id"],
            }
        ), 200

        # return render_template(
        #     "ewc/itb_issue_sample.html",
        #     credential_offer=offer_data.get("credential_offer"),
        #     uri=offer_data.get("uri"),
        #     qr_code=offer_data.get("qr_code"),
        #     tx_code=offer_data.get("tx_code"),
        #     transaction_id=offer_data.get("transaction_id"),
        #     status_url=cfgservice.service_url + "usecases/ewc/itb/issueStatus?sessionId=" + offer_data.get("transaction_id"),
        # )

    except Exception as e:
        cfgservice.app_logger.error(f"Error in issue_credential: {str(e)}")
        return jsonify({
            "status": "fail",
            "reason": "unable to generate credential offer",
        }), 500




@itb_bp.route("/issueStatus", methods=["GET"])
def issue_status():
    session_id = request.args.get("sessionId")
    if not session_id:
        cfgservice.app_logger.error("Missing session_id")
        return jsonify({
            "status": "fail",
            "reason": "session id not found",
            "sessionId": "123"
        }), 500

    transaction_status = transactions_statuses.get(session_id)
    if not transaction_status:
        cfgservice.app_logger.error("Transaction not found")
        return jsonify({
            "status": "fail",
            "reason": "no issuance session found",
            "sessionId": session_id
        }), 500

    return jsonify({
        "status": transaction_status["status"],
        "reason": transaction_status["reason"],
        "sessionId": session_id
    })
