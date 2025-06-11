import uuid

import requests

from app.app_config.config_service import ConfService as cfgservice


def get_offer_data(payload, transaction_id=None, tx_code=None):
    import jwt
    from app.app_config.config_secrets import hmac_secret
    if hmac_secret:
        issuance_request_payload = jwt.encode(payload, hmac_secret, algorithm="HS256")
    else:
        issuance_request_payload = jwt.encode(payload, "1234abcd", algorithm="HS256")

    if not transaction_id:
        transaction_id = str(uuid.uuid4())

    data = {"request": issuance_request_payload, "transaction_id": transaction_id}
    if tx_code:
        data["tx_code"] = tx_code
    response = requests.post(
        f"{cfgservice.service_url}generateCredentialOffer",
        data=data,
    )

    if response.status_code != 200:
        return None

    offer_data = response.json()
    return offer_data
