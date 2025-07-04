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
"""
The PID Issuer Web service is a component of the PID Provider backend. 
Its main goal is to issue the PID and MDL in cbor/mdoc (ISO 18013-5 mdoc) and SD-JWT format.


This route_formatter.py file is the blueprint for the route /formatter of the PID Issuer Web service.
"""
import base64
import logging


from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
    jsonify,
)

from validate import validate_mandatory_args, validate_date_format
from app_config.config_service import ConfService as cfgservice
from formatter_func import mdocFormatter, sdjwtFormatter

from app_config.config_countries import ConfCountries as cfcountries

# /formatter blueprint
formatter = Blueprint("formatter", __name__, url_prefix="/formatter")

# Log
logger = logging.getLogger()


# --------------------------------------------------------------------------------------------------------------------------------------
# route to /formatter
# @formatter.route('', methods=['GET','POST'])
# # route to /formatter/
# @formatter.route('/', methods=['GET','POST'])
# def formatter_root():
#     """Initial eIDAS-node page.
#     Loads country config information and renders pid_index.html so that the user can select the PID issuer country."""


#     if 'country' in request.form.keys():
#         print(cfgcountries.supported_countries[request.form.get('country')]['pid_url'])
#     return render_template('route_pid/pid-countries.html', countries = create_dict(cfgcountries.supported_countries, 'name'))
#     return "to be implemented", status.HTTP_200_OK


# --------------------------------------------------------------------------------------------------------------------------------------
# route to /formatter/cbor
@formatter.route("/cbor", methods=["POST"])
def cborformatter():
    """Creates ISO 18013-5 mdoc in cbor format, and returns signed mdoc

    POST json parameters:
    + version (mandatory) - API version.
    + country (mandatory) - Two-letter country code according to ISO 3166-1 alpha-2.
    + doctype (mandatory) - mdoc doctype
    + device_publickey(mandatory) - Public key from user device
    + data (mandatory) - doctype data "dictionary" with one or more "namespace": {"namespace data and fields"} tuples
    + signature (optional) - "dictionary" with the following fields: "signing_certificate_hash", "signed_country", "signed_doctype", "signed_data". Purpose of this field is twofold:
         + formatter/cbor request can only be performed by allowed entities;
          + non-repudiation of the formatter/cbor request.

    Return: Returns the mdoc, error_code and error_message in a JSON object:
    + mdoc - signed cbor encoded 18013-5 mdoc (in base 64 urlsafe encode).
    + error_code - error number. 0 if no error. Additional errors defined below. If error != 0, mdoc field may have an empty value.
    + error_message - Error information.
    """

    (b, l) = validate_mandatory_args(
        request.json, ["version", "country", "credential_metadata", "device_publickey", "data"]
    )
    if not b:  # nota all mandatory args are present
        return jsonify(
            {
                "error_code": 401,
                "error_message": cfgservice.error_list["401"],
                "mdoc": "",
            }
        )
    
    if request.json["version"] not in cfgservice.getpid_or_mdl_response_field:
        return jsonify(
            {"error_code": 13, "error_message": cfgservice.error_list["13"], "mdoc": ""}
        )
    
    if request.json["country"] not in cfcountries.supported_countries:
        return jsonify(
            {
                "error_code": 102,
                "error_message": cfgservice.error_list["102"],
                "mdoc": "",
            }
        )

    """if request.json["doctype"] == "org.iso.18013.5.1.mDL":
        (b, l) = validate_mandatory_args(
            request.json["data"]["org.iso.18013.5.1"],
            [
                "family_name",
                "given_name",
                "birth_date",
                "issue_date",
                "expiry_date",
                "issuing_country",
                "issuing_authority",
                "document_number",
                "portrait",
                "driving_privileges",
                "un_distinguishing_sign",
            ],
        )

    if request.json["doctype"] == "eu.europa.ec.eudi.pid.1":
        (b, l) = validate_mandatory_args(
            request.json["data"]["eu.europa.ec.eudi.pid.1"],
            ["family_name", "given_name", "birth_date", "nationality", "birth_place"],
        ) """

    if request.json["credential_metadata"]["doctype"] == "org.iso.18013.5.1.mDL":
        expiry_date = request.json["data"]["org.iso.18013.5.1"].get("expiry_date")
        issue_date = request.json["data"]["org.iso.18013.5.1"].get("issue_date")

        if expiry_date is not None:
            if not validate_date_format(expiry_date):
                return jsonify(
                    {
                        "error_code": 306,
                        "error_message": cfgservice.error_list["306"],
                        "mdoc": "",
                    }
                )
        if issue_date is not None:
            if not validate_date_format(issue_date):
                return jsonify(
                    {
                        "error_code": 306,
                        "error_message": cfgservice.error_list["306"],
                        "mdoc": "",
                    }
                )

    if not b:  # nota all mandatory args are present
        return jsonify(
            {
                "error_code": 401,
                "error_message": cfgservice.error_list["401"],
                "mdoc": "",
            }
        )

    base64_mdoc = mdocFormatter(
        request.json["data"],
        request.json["credential_metadata"],
        request.json["country"],
        request.json["device_publickey"],
    )

    import requests

    url = "https://stoplight.io/mocks/infocert-api/cborservice/772136026/v1/signed-mdoc-credentials/mdl"

    payload = {
        "org.iso.18013.5.1": {"credential": {
            "given_name": "RIMIRIZ GUMORE",
            "family_name": "GIARGO ANTHONY",
            "birth_date": "1989-11-13",
            "birth_place": "LIMA (PE )",
            "issue_date": "2024-10-06",
            "issuing_country": "IT",
            "issuing_authority": "MC-RM",
            "expiry_date": "2025-02-11",
            "document_number": "RM8375134J",
            "portrait": "data:image/png;base64,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8KV8Of8AP7qv/f2P/wCIre8LeAtL8JXc9zYXF5K8yCNhO6kAZzxhRUVMbUqQcGlqVDDxhLmR1NFcZ0H/2QD/7REEUGhvdG9zaG9wIDMuMAA4QklNBAQAAAAAAAccAgAAAuaRADhCSU0EJQAAAAAAEJYZu79k1Vo1RsiQJvesLLc4QklNBC8AAAAAAEo2AQEAWAIAAFgCAAAAAAAAAAAAAHsaAACYEgAAiv///5z////xGgAA/BIAAAABewUAAOADAAABAA8nAQBjAGIAOwAqAC4AdgBzADhCSU0D7QAAAAAAEADIAAAAAQACAMgAAAABAAI4QklNBCYAAAAAAA4AAAAAAAAAAAAAP4AAADhCSU0EDQAAAAAABAAAAB44QklNBBkAAAAAAAQAAAAeOEJJTQPzAAAAAAAJAAAAAAAAAAABADhCSU0ECgAAAAAAAQAAOEJJTScQAAAAAAAKAAEAAAAAAAAAAjhCSU0D9QAAAAAASAAvZmYAAQBsZmYABgAAAAAAAQAvZmYAAQChmZoABgAAAAAAAQAyAAAAAQBaAAAABgAAAAAAAQA1AAAAAQAtAAAABgAAAAAAAThCSU0D+AAAAAAAcAAA/////////////////////////////wPoAAAAAP////////////////////////////8D6AAAAAD/////////////////////////////A+gAAAAA/////////////////////////////wPoAAA4QklNBAgAAAAAABAAAAABAAACQAAAAkAAAAAAOEJJTQQeAAAAAAAEAAAAADhCSU0EGgAAAAADRwAAAAYAAAAAAAAAAAAAATsAAAEEAAAACQBGAG8AdABvAE4AdQBvAHYAYQAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAABBAAAATsAAAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAQAAAAAQAAAAAAAG51bGwAAAACAAAABmJvdW5kc09iamMAAAABAAAAAAAAUmN0MQAAAAQAAAAAVG9wIGxvbmcAAAAAAAAAAExlZnRsb25nAAAAAAAAAABCdG9tbG9uZwAAATsAAAAAUmdodGxvbmcAAAEEAAAABnNsaWNlc1ZsTHMAAAABT2JqYwAAAAEAAAAAAAVzbGljZQAAABIAAAAH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YzlkIj8+DQo8eDp4bXBtZXRhIHhtbG5zOng9ImFkb2JlOm5zOm1ldGEvIiB4OnhtcHRrPSJBZG9iZSBYTVAgQ29yZSA0LjEtYzAzNiA0Ni4yNzY3MjAsIE1vbiBGZWIgMTkgMjAwNyAyMjo0MDowOCAgICAgICAgIj4NCgk8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPg0KCQk8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0iIiB4bWxuczp4YXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtbG5zOmRjPSJodHRwOi8vcHVybC5vcmcvZGMvZWxlbWVudHMvMS4xLyIgeG1sbnM6cGhvdG9zaG9wPSJodHRwOi8vbnMuYWRvYmUuY29tL3Bob3Rvc2hvcC8xLjAvIiB4bWxuczp4YXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6dGlmZj0iaHR0cDovL25zLmFkb2JlLmNvbS90aWZmLzEuMC8iIHhtbG5zOmV4aWY9Imh0dHA6Ly9ucy5hZG9iZS5jb20vZXhpZi8xLjAvIiB4YXA6Q3JlYXRlRGF0ZT0iMjAxMi0xMi0xMFQxMTozOTowMiswMTowMCIgeGFwOk1vZGlmeURhdGU9IjIwMTItMTItMTBUMTI6NTk6MzgrMDE6MDAiIHhhcDpNZXRhZGF0YURhdGU9IjIwMTItMTItMTBUMTI6NTk6MzgrMDE6MDAiIHhhcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIENTMyBXaW5kb3dzIiBkYzpmb3JtYXQ9ImltYWdlL2pwZWciIHBob3Rvc2hvcDpDb2xvck1vZGU9IjMiIHBob3Rvc2hvcDpIaXN0b3J5PSIiIHhhcE1NOkluc3RhbmNlSUQ9InV1aWQ6NEU4MUU3MTNCQTQyRTIxMUE4OTlFQTVEQjY5QTI2QkEiIHRpZmY6WFJlc29sdXRpb249IjIwMDAwMDAvMTAwMDAiIHRpZmY6WVJlc29sdXRpb249IjIwMDAwMDAvMTAwMDAiIHRpZmY6UmVzb2x1dGlvblVuaXQ9IjIiIHRpZmY6TmF0aXZlRGlnZXN0PSIyNTYsMjU3LDI1OCwyNTksMjYyLDI3NCwyNzcsMjg0LDUzMCw1MzEsMjgyLDI4MywyOTYsMzAxLDMxOCwzMTksNTI5LDUzMiwzMDYsMjcwLDI3MSwyNzIsMzA1LDMxNSwzMzQzMjswRjVBQzIwOTQ4MTg5MkJBRkU3OUM5OTg2NjQyQUI1NCIgZXhpZjpQaXhlbFhEaW1lbnNpb249IjI2MCIgZXhpZjpQaXhlbFlEaW1lbnNpb249IjMxNSIgZXhpZjpDb2xvclNwYWNlPSItMSIgZXhpZjpOYXRpdmVEaWdlc3Q9IjM2ODY0LDQwOTYwLDQwOTYxLDM3MTIxLDM3MTIyLDQwOTYyLDQwOTYzLDM3NTEwLDQwOTY0LDM2ODY3LDM2ODY4LDMzNDM0LDMzNDM3LDM0ODUwLDM0ODUyLDM0ODU1LDM0ODU2LDM3Mzc3LDM3Mzc4LDM3Mzc5LDM3MzgwLDM3MzgxLDM3MzgyLDM3MzgzLDM3Mzg0LDM3Mzg1LDM3Mzg2LDM3Mzk2LDQxNDgzLDQxNDg0LDQxNDg2LDQxNDg3LDQxNDg4LDQxNDkyLDQxNDkzLDQxNDk1LDQxNzI4LDQxNzI5LDQxNzMwLDQxOTg1LDQxOTg2LDQxOTg3LDQxOTg4LDQxOTg5LDQxOTkwLDQxOTkxLDQxOTkyLDQxOTkzLDQxOTk0LDQxOTk1LDQxOTk2LDQyMDE2LDAsMiw0LDUsNiw3LDgsOSwxMCwxMSwxMiwxMywxNCwxNSwxNiwxNywxOCwyMCwyMiwyMywyNCwyNSwyNiwyNywyOCwzMDtBNTE2MjU1NjZCMzE4NTM1NUNBQTFGNTg3RTRBODZGMyIvPg0KCTwvcmRmOlJERj4NCjwveDp4bXBtZXRhPg0KICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIDw/eHBhY2tldCBlbmQ9J3cnPz7/2wBDAAIBAQIBAQICAgICAgICAwUDAwMDAwYEBAMFBwYHBwcGBwcICQsJCAgKCAcHCg0KCgsMDAwMBwkODw0MDgsMDAz/2wBDAQICAgMDAwYDAwYMCAcIDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAz/wAARCAE7AQQDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD9/KKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigA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",
            "driving_privileges": [
                {
                    "vehicleCategoryCode": "AM",
                    "issueDate": "2013-01-19",
                    "expiryDate": "2025-02-11",
                    "codes": [
                        {
                            "code": "71.RM6946167J.I",
                            "sign": "string",
                            "value": "string"
                        }
                    ]
                }
            ],
            "un_distinguishing_sign": "I"
        }},
        "org.iso.18013.5.1.IT": {
            "sub": "a7d94053-5719-432c-9ac6-88a76b7376c9",
            "verification": {
                "trust_framework": "it_spid",
                "assurance_level": "high",
                "evidence": [
                    {
                        "type": "vouch",
                        "time": "2019-08-24T14:15:22Z",
                        "attestation": {
                            "type": "digital_attestation",
                            "reference_number": "6485-1619-3976-6671",
                            "date_of_issuance": "2019-08-24T14:15:22Z",
                            "voucher": {"organization": "Ministero dell'Interno"}
                        }
                    }
                ]
            }
        }
    }
    headers = {
        "x-request-id": "ciao",
        "x-device-jwk": "ciao",
        "Prefer": "code=200",
        "Content-Type": "application/json",
        "Accept": "application/json, application/problem+json"
    }

    response = requests.post(url, json=payload, headers=headers)

    #hex_string_mdoc = response.json()["credential"]
    hex_string_mdoc = "a36776657273696f6e63312e3069646f63756d656e747381a367646f6354797065756f72672e69736f2e31383031332e352e312e6d444c6c6973737565725369676e6564a26a6e616d65537061636573a1716f72672e69736f2e31383031332e352e3186d8185863a4686469676573744944006672616e646f6d58208798645b20ea200e19ffabac92624bee6aec63aceedecfb1b80077d22bfc20e971656c656d656e744964656e7469666965726b66616d696c795f6e616d656c656c656d656e7456616c756563446f65d818586ca4686469676573744944036672616e646f6d5820b23f627e8999c706df0c0a4ed98ad74af988af619b4bb078b89058553f44615d71656c656d656e744964656e7469666965726a69737375655f646174656c656c656d656e7456616c7565d903ec6a323031392d31302d3230d818586da4686469676573744944046672616e646f6d5820c7ffa307e5de921e67ba5878094787e8807ac8e7b5b3932d2ce80f00f3e9abaf71656c656d656e744964656e7469666965726b6578706972795f646174656c656c656d656e7456616c7565d903ec6a323032342d31302d3230d818586da4686469676573744944076672616e646f6d582026052a42e5880557a806c1459af3fb7eb505d3781566329d0b604b845b5f9e6871656c656d656e744964656e7469666965726f646f63756d656e745f6e756d6265726c656c656d656e7456616c756569313233343536373839d818590471a4686469676573744944086672616e646f6d5820d094dad764a2eb9deb5210e9d899643efbd1d069cc311d3295516ca0b024412d71656c656d656e744964656e74696669657268706f7274726169746c656c656d656e7456616c7565590412ffd8ffe000104a46494600010101009000900000ffdb004300130d0e110e0c13110f11151413171d301f1d1a1a1d3a2a2c2330453d4947443d43414c566d5d4c51685241435f82606871757b7c7b4a5c869085778f6d787b76ffdb0043011415151d191d381f1f38764f434f7676767676767676767676767676767676767676767676767676767676767676767676767676767676767676767676767676ffc00011080018006403012200021101031101ffc4001b00000301000301000000000000000000000005060401020307ffc400321000010303030205020309000000000000010203040005110612211331141551617122410781a1163542527391b2c1f1ffc4001501010100000000000000000000000000000001ffc4001a110101010003010000000000000000000000014111213161ffda000c03010002110311003f00a5bbde22da2329c7d692bc7d0d03f52cfb0ff75e7a7ef3e7709723a1d0dae146ddfbb3c039ce07ad2bd47a7e32dbb8dd1d52d6ef4b284f64a480067dfb51f87ffb95ff00eb9ff14d215de66af089ce44b7dbde9cb6890a2838eddf18078f7add62d411ef4db9b10a65d6b95a147381ea0d495b933275fe6bba75c114104a8ba410413e983dff004f5af5d34b4b4cde632d0bf1fd1592bdd91c6411f3934c2fa6af6b54975d106dcf4a65ae56e856001ebc03c7ce29dd9eef1ef10fc447dc9da76ad2aee93537a1ba7e4f70dd8eff0057c6dffb5e1a19854a83758e54528750946ec6704850cd037bceb08b6d7d2cc76d3317fc7b5cc04fb6707269c5c6e0c5b60ae549242123b0e493f602a075559e359970d98db89525456b51c951c8afa13ea8e98e3c596836783d5c63f5a61a99fdb7290875db4be88ab384bbbbbfc7183fdeaa633e8951db7da396dc48524fb1a8bd611a5aa2a2432f30ab420a7a6d3240c718cf031fa9ef4c9ad550205aa02951df4a1d6c8421b015b769db8c9229837ea2be8b1b0d39d0eba9c51484efdb8c0efd8d258daf3c449699f2edbd4584e7af9c64e3f96b9beb28d4ac40931e6478c8e76a24a825449501d867d2b1dcdebae99b9c752ae4ecd6dde4a179c1c1e460938f9149ef655e515c03919a289cb3dca278fb7bf177f4faa829dd8ce3f2ac9a7ecde490971fafd7dce15eed9b71c018c64fa514514b24e8e4f8c5c9b75c1e82579dc1233dfec08238f6add62d391acc1c5256a79e706d52d431c7a0145140b9fd149eb3a60dc5e88cbbc2da092411e9dc71f39a7766b447b344e847dcac9dcb5abba8d145061d43a6fcf1e65cf15d0e90231d3dd9cfe62995c6dcc5ca12a2c904a15f71dd27d451453e09d1a21450961cbb3ea8a956433b781f1ce33dfed54f0e2b50a2b71d84ed6db18028a28175f74fc6bda105c529a791c25c4f3c7a11f71586268f4a66b726e33de9ea6f1b52b181c760724e47b514520a5a28a283ffd9d81858ffa4686469676573744944096672616e646f6d58204599f81beaa2b20bd0ffcc9aa03a6f985befab3f6beaffa41e6354cdb2ab2ce471656c656d656e744964656e7469666965727264726976696e675f70726976696c656765736c656c656d656e7456616c756582a37576656869636c655f63617465676f72795f636f646561416a69737375655f64617465d903ec6a323031382d30382d30396b6578706972795f64617465d903ec6a323032342d31302d3230a37576656869636c655f63617465676f72795f636f646561426a69737375655f64617465d903ec6a323031372d30322d32336b6578706972795f64617465d903ec6a323032342d31302d32306a697373756572417574688443a10126a118215901f3308201ef30820195a00302010202143c4416eed784f3b413e48f56f075abfa6d87eb84300a06082a8648ce3d04030230233114301206035504030c0b75746f7069612069616361310b3009060355040613025553301e170d3230313030313030303030305a170d3231313030313030303030305a30213112301006035504030c0975746f706961206473310b30090603550406130255533059301306072a8648ce3d020106082a8648ce3d03010703420004ace7ab7340e5d9648c5a72a9a6f56745c7aad436a03a43efea77b5fa7b88f0197d57d8983e1b37d3a539f4d588365e38cbbf5b94d68c547b5bc8731dcd2f146ba381a83081a5301e0603551d120417301581136578616d706c65406578616d706c652e636f6d301c0603551d1f041530133011a00fa00d820b6578616d706c652e636f6d301d0603551d0e0416041414e29017a6c35621ffc7a686b7b72db06cd12351301f0603551d2304183016801454fa2383a04c28e0d930792261c80c4881d2c00b300e0603551d0f0101ff04040302078030150603551d250101ff040b3009060728818c5d050102300a06082a8648ce3d040302034800304502210097717ab9016740c8d7bcdaa494a62c053bbdecce1383c1aca72ad08dbc04cbb202203bad859c13a63c6d1ad67d814d43e2425caf90d422422c04a8ee0304c0d3a68d5903a2d81859039da66776657273696f6e63312e306f646967657374416c676f726974686d675348412d3235366c76616c756544696765737473a2716f72672e69736f2e31383031332e352e31ad00582075167333b47b6c2bfb86eccc1f438cf57af055371ac55e1e359e20f254adcebf01582067e539d6139ebd131aef441b445645dd831b2b375b390ca5ef6279b205ed45710258203394372ddb78053f36d5d869780e61eda313d44a392092ad8e0527a2fbfe55ae0358202e35ad3c4e514bb67b1a9db51ce74e4cb9b7146e41ac52dac9ce86b8613db555045820ea5c3304bb7c4a8dcb51c4c13b65264f845541341342093cca786e058fac2d59055820fae487f68b7a0e87a749774e56e9e1dc3a8ec7b77e490d21f0e1d3475661aa1d0658207d83e507ae77db815de4d803b88555d0511d894c897439f5774056416a1c7533075820f0549a145f1cf75cbeeffa881d4857dd438d627cf32174b1731c4c38e12ca936085820b68c8afcb2aaf7c581411d2877def155be2eb121a42bc9ba5b7312377e068f660958200b3587d1dd0c2a07a35bfb120d99a0abfb5df56865bb7fa15cc8b56a66df6e0c0a5820c98a170cf36e11abb724e98a75a5343dfa2b6ed3df2ecfbb8ef2ee55dd41c8810b5820b57dd036782f7b14c6a30faaaae6ccd5054ce88bdfa51a016ba75eda1edea9480c5820651f8736b18480fe252a03224ea087b5d10ca5485146c67c74ac4ec3112d4c3a746f72672e69736f2e31383031332e352e312e5553a4005820d80b83d25173c484c5640610ff1a31c949c1d934bf4cf7f18d5223b15dd4f21c0158204d80e1e2e4fb246d97895427ce7000bb59bb24c8cd003ecf94bf35bbd2917e340258208b331f3b685bca372e85351a25c9484ab7afcdf0d2233105511f778d98c2f544035820c343af1bd1690715439161aba73702c474abf992b20c9fb55c36a336ebe01a876d6465766963654b6579496e666fa1696465766963654b6579a40102200121582096313d6c63e24e3372742bfdb1a33ba2c897dcd68ab8c753e4fbd48dca6b7f9a2258201fb3269edd418857de1b39a4e4a44b92fa484caa722c228288f01d0c03a2c3d667646f6354797065756f72672e69736f2e31383031332e352e312e6d444c6c76616c6964697479496e666fa3667369676e6564c074323032302d31302d30315431333a33303a30325a6976616c696446726f6dc074323032302d31302d30315431333a33303a30325a6a76616c6964556e74696cc074323032312d31302d30315431333a33303a30325a584059e64205df1e2f708dd6db0847aed79fc7c0201d80fa55badcaf2e1bcf5902e1e5a62e4832044b890ad85aa53f129134775d733754d7cb7a413766aeff13cb2e6c6465766963655369676e6564a26a6e616d65537061636573d81841a06a64657669636541757468a1696465766963654d61638443a10105a0f65820e99521a85ad7891b806a07f8b5388a332d92c189a7bf293ee1f543405ae6824d6673746174757300"
    base64_mdoc = base64.urlsafe_b64encode(bytes.fromhex(hex_string_mdoc)).decode("utf-8")
    print(base64_mdoc)

    return jsonify(
        {
            "error_code": 0,
            "error_message": cfgservice.error_list["0"],
            "mdoc": base64_mdoc,
        }
    )


# --------------------------------------------------------------------------------------------------------------------------------------
# route to /formatter/sd-jwt
@formatter.route("/sd-jwt", methods=["POST"])
def sd_jwtformatter():
    """Creates sd-jwt, and returns sd-jwt

    POST json parameters:
    + version (mandatory) - API version.
    + country (mandatory) - Two-letter country code according to ISO 3166-1 alpha-2.
    + doctype (mandatory) - Sd-jwt doctype
    + device_publickey(mandatory) - Public key from user device
    + data (mandatory) - doctype data "dictionary" with one or more "namespace": {"namespace data and fields"} tuples

    Return: Returns the sd-jwt, error_code and error_message in a JSON object:
    + sd-jwt - Signed sd-jwt
    + error_code - error number. 0 if no error. Additional errors defined below. If error != 0, mdoc field may have an empty value.
    + error_message - Error information.
    """

    """ (b, l) = validate_mandatory_args(
        request.json, ["version", "country", "doctype", "device_publickey", "data"]
    )
    if not b:  # nota all mandatory args are present
        return jsonify(
            {
                "error_code": 401,
                "error_message": cfgservice.error_list["401"],
                "mdoc": "",
            }
        ) """

    PID = request.get_json()

    """   if PID["doctype"] == "eu.europa.ec.eudi.pid.1":
        (b, l) = validate_mandatory_args(
            PID["data"]["claims"],
            ["family_name", "given_name", "birth_date", "nationality", "birth_place"],
        )
    if not b:  # nota all mandatory args are present
        return jsonify(
            {
                "error_code": 401,
                "error_message": cfgservice.error_list["401"],
                "mdoc": "",
            }
        ) """

    # try:

    # validate(PID, schema)

    # except ValidationError as e:

    # error_message = {
    # "error_message":str(e)
    # }

    # return error_message

    sd_jwt = sdjwtFormatter(PID, request.json["country"])

    return jsonify(
        {"error_code": 0, "error_message": cfgservice.error_list["0"], "sd-jwt": sd_jwt}
    )
