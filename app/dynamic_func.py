# coding: latin-1
###############################################################################
# Copyright (c) 2023 European Commission
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
import datetime
import json
import uuid

from flask import session

from app.redirect_func import json_data_post_with_header
from app_config.config_service import ConfService as cfgserv
from app_config.config_countries import ConfCountries as cfgcountries
from misc import calculate_age, doctype2credential, doctype2credentialSDJWT, getIssuerFilledAttributes, \
    getIssuerFilledAttributesSDJWT, getMandatoryAttributes, getMandatoryAttributesSDJWT, getNamespaces, \
    getOptionalAttributes, getOptionalAttributesSDJWT, b64pem_to_cose_and_jwk_base64
from redirect_func import json_post
import base64
from flask import session
from app_config.config_service import ConfService as cfgserv
from misc import calculate_age
from redirect_func import json_post
from app import oidc_metadata


def dynamic_formatter(format, doctype, form_data, device_publickey):

    if doctype == "org.iso.18013.5.1.mDL":
        un_distinguishing_sign = cfgcountries.supported_countries[session["country"]][
            "un_distinguishing_sign"
        ]
    else:
        un_distinguishing_sign = ""

    data, requested_credential = formatter(dict(form_data), un_distinguishing_sign, doctype, format)
    print(data)

    # TODO At the moment data's org.iso.18013.5.1 elements must be enclosed in "credential" object
    if "org.iso.18013.5.1" in data:
        credential_ns = data["org.iso.18013.5.1"]
        data["org.iso.18013.5.1"] = {"credential": credential_ns}
    print(data)

    if doctype == "org.iso.18013.5.1.mDL":
        if format == "mso_mdoc":
            url = cfgserv.cbor_service_url

        elif format == "dc+sd-jwt":
            url = cfgserv.service_url + "formatter/sd-jwt"
        cose_key, device_public_key_b64jwk = b64pem_to_cose_and_jwk_base64(device_publickey)
        # Calling Cbor Service
        r = json_data_post_with_header(
            url=url,
            payload=data,
            headers = {
                "X-Request-ID": str(uuid.uuid4()),
                "X-Device-JWK": device_public_key_b64jwk,
                "Content-Type": "application/json"
            }
        )
        r.raise_for_status()
        base64_mdoc = r.json().get("credential")
        print(base64_mdoc)
    else:
        if format == "mso_mdoc":
            url = cfgserv.service_url + "formatter/cbor"

        elif format == "dc+sd-jwt":
            url = cfgserv.service_url + "formatter/sd-jwt"
        r = json_post(
            url,
            {
                "version": session["version"],
                "country": session["country"],
                "credential_metadata": requested_credential,
                "device_publickey": device_publickey,
                "data": data,
            },
        ).json()
        base64_mdoc = r["mdoc"]

    if format == "mso_mdoc":
        mdoc = bytes(base64_mdoc, "utf-8")
        credential = mdoc.decode("utf-8")
    elif format == "dc+sd-jwt":
        credential = r["sd-jwt"]

    return credential


def formatter(data, un_distinguishing_sign, doctype, format):
    credentialsSupported = oidc_metadata["credential_configurations_supported"]
    today = datetime.date.today()

    if format == "mso_mdoc":
        requested_credential = doctype2credential(doctype, format)
        doctype_config = requested_credential["issuer_config"]
        expiry = today + datetime.timedelta(days=doctype_config["validity"])
        namespaces = getNamespaces(requested_credential["claims"])

        combined_attributes = {}
        combined_opt_attributes = {}
        combined_issuer_attributes = {}
        pdata = {}

        for ns in namespaces:
            combined_attributes.update(getMandatoryAttributes(requested_credential["claims"], ns))
            combined_opt_attributes.update(getOptionalAttributes(requested_credential["claims"], ns))
            combined_issuer_attributes.update(getIssuerFilledAttributes(requested_credential["claims"], ns))
            pdata[ns] = {}  # Init namespace-specific section

        attributes_req = combined_attributes
        attributes_req2 = combined_opt_attributes
        issuer_claims = combined_issuer_attributes

    elif format == "dc+sd-jwt":
        requested_credential = doctype2credentialSDJWT(doctype, format)
        doctype_config = requested_credential["issuer_config"]
        expiry = today + datetime.timedelta(days=doctype_config["validity"])

        pdata = {
            "evidence": [{
                "type": doctype,
                "source": {
                    "organization_name": doctype_config["organization_name"],
                    "organization_id": doctype_config["organization_id"],
                    "country_code": data["issuing_country"],
                },
            }],
            "claims": {}
        }

        attributes_req = getMandatoryAttributesSDJWT(requested_credential["claims"])
        attributes_req2 = getOptionalAttributesSDJWT(requested_credential["claims"])
        issuer_claims = getIssuerFilledAttributesSDJWT(requested_credential["claims"])

    else:
        raise ValueError("Unsupported format: {}".format(format))

    age_thresholds = [13, 16, 18, 21, 25, 60, 62, 65, 68]
    for threshold in age_thresholds:
        key = f"age_over_{threshold}"
        if key in issuer_claims and "birth_date" in data:
            data[key] = calculate_age(data["birth_date"]) >= threshold

    if "age_over_18" in data:
        attributes_req2["age_over_18"] = data["age_over_18"]

    # if "portrait" in data:
    #     data["portrait"] = base64.urlsafe_b64decode(
    #         data["portrait"]
    #     )

    if "un_distinguishing_sign" in issuer_claims:
        data["un_distinguishing_sign"] = un_distinguishing_sign

    if "issuance_date" in issuer_claims:
        data["issuance_date"] = today.strftime("%Y-%m-%d")

    if "issue_date" in issuer_claims:
        data["issue_date"] = today.strftime("%Y-%m-%d")

    if "expiry_date" in issuer_claims:
        data["expiry_date"] = expiry.strftime("%Y-%m-%d")

    if "issuing_authority" in issuer_claims:
        data["issuing_authority"] = doctype_config["issuing_authority"]

    if "issuing_authority_unicode" in issuer_claims:
        data["issuing_authority_unicode"] = doctype_config["issuing_authority"]

    if "issuing_jurisdiction" in issuer_claims:
        data["issuing_jurisdiction"] = doctype_config.get("issuing_jurisdiction", "EU")

    if "credential_type" in issuer_claims:
        data["credential_type"] = doctype_config["credential_type"]
        attributes_req["credential_type"] = ""

    if "verification" in issuer_claims:
        data["verification"] = {
            "trust_framework": "it_wallet",
            "assurance_level": "substantial",
            "evidence": [{
                "type": "vouch",
                "time": int(datetime.datetime.now().timestamp()),
                "attestation": {
                    "type": "digital_attestation",
                    "reference_number": "REF-2025-0001",
                    "date_of_issuance": today.strftime("%Y-%m-%d"),
                    "voucher": {
                        "organization": doctype_config["organization_name"]
                    }
                }
            }]
        }

    for k in ["at_least_one_of"]:
        attributes_req.pop(k, None)
        attributes_req2.pop(k, None)

    for attr in ["driving_privileges", "places_of_work", "legislation", "employment_details", "competent_institution", "credential_holder", "subject"]:
        if attr in attributes_req or attr in attributes_req2:
            if isinstance(data.get(attr), str):
                data[attr] = json.loads(data[attr])
            elif isinstance(data.get(attr), list) and attr not in ["places_of_work", "employment_details"]:
                data[attr] = data[attr][0]

    for attr in ["age_in_years", "age_birth_year"]:
        if isinstance(data.get(attr), str):
            data[attr] = int(data[attr])

    # wallet attestation fields
    wallet_attestation = doctype_config.get("wallet_attestation", {})
    if "wallet_name" in issuer_claims:
        data["wallet_name"] = wallet_attestation.get("wallet_name", "EU Digital Wallet")
    if "wallet_link" in issuer_claims:
        data["wallet_link"] = wallet_attestation.get("wallet_link", "https://ec.europa.eu/digital-wallet")
    if "sub" in issuer_claims:
        data["sub"] = str(uuid.uuid4())
    if "aal" in issuer_claims:
        data["aal"] = wallet_attestation.get("aal", "https://ec.europa.eu/digital-wallet/aal")

    if format == "mso_mdoc":
        for ns in namespaces:
            for attribute in getMandatoryAttributes(requested_credential["claims"], ns):
                pdata[ns][attribute] = data[attribute]
            for attribute in getOptionalAttributes(requested_credential["claims"], ns):
                if attribute in data:
                    pdata[ns][attribute] = data[attribute]
            for attribute in getIssuerFilledAttributes(requested_credential["claims"], ns):
                if attribute in data:
                    pdata[ns][attribute] = data[attribute]

    elif format == "dc+sd-jwt":
        for attribute in attributes_req:
            pdata["claims"][attribute] = data[attribute]
        for attribute in attributes_req2:
            if attribute in data:
                pdata["claims"][attribute] = data[attribute]
        for attribute in issuer_claims:
            if attribute in data:
                pdata["claims"][attribute] = data[attribute]

    return pdata, requested_credential
