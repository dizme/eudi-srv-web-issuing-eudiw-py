import os
import re
import uuid
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse, parse_qs
from xml.etree import ElementTree as ET

import requests

from app.app_config.config_service import ConfService as cfgservice


# Data classes
@dataclass
class ContactDetails:
    email: str
    mobile_number: str

@dataclass
class PersonalData:
    fiscal_code: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    birth_date: Optional[str]
    sex: Optional[str]
    citizenship: Optional[str]
    birth_place: Optional[str]
    birth_province: Optional[str]
    birth_country: Optional[str]
    full_first_name: Optional[str]
    full_last_name: Optional[str]

@dataclass
class LegalId:
    country_code: str
    serial_type: str
    serial_number: str

@dataclass
class Person:
    identified: bool
    legal_id: LegalId
    personal_data: PersonalData
    contact_details: ContactDetails

@dataclass
class Signer:
    signer_id: str
    identified: bool
    personal_data_updated: bool
    address_updated: bool
    identity_document_info_updated: bool
    contact_info_updated: bool
    person: Person

@dataclass
class DossierInfo:
    business_id: str
    status: str
    creation_date: str
    last_activity_date: str
    signers: List[Signer]

def parse_soap_response(xml_str: str) -> DossierInfo:
    ns = {
        'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
        'ns3': 'http://www.infocert.it/legalbus/cop/onboarding',
    }
    root = ET.fromstring(xml_str)
    dossier_info_el = root.find('.//ns3:getDossierResponse/dossier-info', ns)

    business_id = dossier_info_el.findtext('business-id')
    status = dossier_info_el.findtext('status')
    creation_date = dossier_info_el.findtext('creation-date')
    last_activity_date = dossier_info_el.findtext('last-activity-date')

    signers_list = []
    for signer_el in dossier_info_el.findall('.//signers/signers'):
        signer_id = signer_el.attrib.get('signer-id')
        identified = signer_el.findtext('identified') == 'true'
        personal_data_updated = signer_el.findtext('personal-data-updated') == 'true'
        address_updated = signer_el.findtext('address-updated') == 'true'
        identity_document_info_updated = signer_el.findtext('identity-document-info-updated') == 'true'
        contact_info_updated = signer_el.findtext('contact-info-updated') == 'true'

        person_el = signer_el.find('person')
        person_identified = person_el.attrib.get('identified') == 'true'

        legal_id_el = person_el.find('legal-id')
        legal_id = LegalId(
            country_code=legal_id_el.attrib.get('country-code'),
            serial_type=legal_id_el.attrib.get('serial-type'),
            serial_number=legal_id_el.attrib.get('serial-number')
        )

        personal_data_el = person_el.find('personal-data')
        personal_data = PersonalData(
            fiscal_code=personal_data_el.findtext('fiscal-code'),
            first_name=personal_data_el.findtext('first-name'),
            last_name=personal_data_el.findtext('last-name'),
            birth_date=personal_data_el.findtext('birth-date'),
            sex=personal_data_el.findtext('sex'),
            citizenship=personal_data_el.findtext('citizenship'),
            birth_place=personal_data_el.findtext('birth-place'),
            birth_province=personal_data_el.findtext('birth-province'),
            birth_country=personal_data_el.findtext('birth-country'),
            full_first_name=personal_data_el.findtext('full-first-name'),
            full_last_name=personal_data_el.findtext('full-last-name')
        )

        contact_el = person_el.find('contact-details')
        contact_details = ContactDetails(
            email=contact_el.attrib.get('email'),
            mobile_number=contact_el.attrib.get('mobile-number')
        )

        person = Person(
            identified=person_identified,
            legal_id=legal_id,
            personal_data=personal_data,
            contact_details=contact_details
        )

        signer = Signer(
            signer_id=signer_id,
            identified=identified,
            personal_data_updated=personal_data_updated,
            address_updated=address_updated,
            identity_document_info_updated=identity_document_info_updated,
            contact_info_updated=contact_info_updated,
            person=person
        )

        signers_list.append(signer)

    return DossierInfo(
        business_id=business_id,
        status=status,
        creation_date=creation_date,
        last_activity_date=last_activity_date,
        signers=signers_list
    )


def get_token():
    top_client_id = os.getenv("TOP_AUTH_CLIENT_ID")
    top_client_secret = os.getenv("TOP_AUTH_CLIENT_SECRET")
    url = os.getenv("TOP_AUTH_TOKEN_URL",
                    "https://idpstage.infocert.digital/auth/realms/delivery/protocol/openid-connect/token")

    payload = f'grant_type=client_credentials&scope=onboarding&client_id={top_client_id}&client_secret={top_client_secret}'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.post(url, headers=headers, data=payload)
    response_data = response.json()

    if response.status_code != 200:
        cfgservice.app_logger.error(f"Failed to retrieve token: {response_data}")
        return None

    bearer_token = response_data.get("access_token")

    if not bearer_token:
        cfgservice.app_logger.error("Access token not found in response")
        return None

    return bearer_token


def onboard(dossier_id=None):
    if not dossier_id:
        dossier_id = str(uuid.uuid4())

    access_token = get_token()
    if not access_token:
        cfgservice.app_logger.error("Failed to obtain access token for onboarding")
        return None

    url = os.getenv("TOP_API_URL", "https://apistage.infocert.digital/onboarding/v1/dossier")
    company_id = os.getenv("TOP_COMPANY_ID", "INFOCERT_DEMO_EXT")
    dossier_type = os.getenv("TOP_DOSSIER_TYPE", "SELFQ_DEMO_NO_BO")
    redirect_uri = f"{cfgservice.service_url}usecases/ewc/top/issue?dossierId={dossier_id}&amp;format=mdoc"
    failure_redirect_uri = f"{cfgservice.service_url}usecases/ewc/top/failure"
    payload = _create_dossier_payload(company_id, dossier_id, dossier_type,
                                      default_redirect_url=redirect_uri,
                                      failure_redirect_url=failure_redirect_uri)
    headers = {
        'Content-Type': 'application/xml',
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.post(url, headers=headers, data=payload)

    if response.status_code != 200:
        cfgservice.app_logger.error(f"Failed to onboard dossier: {response.text}")
        return None

    token_url, token_id = extract_token_from_soap(response.text)

    if not token_url:
        cfgservice.app_logger.error("Failed to extract token URL from SOAP response")
        return None

    return token_url


def extract_token_from_soap(response_text):
    match = re.search(r"<soap:Envelope.*?</soap:Envelope>", response_text, re.DOTALL)
    if not match:
        cfgservice.app_logger.error("SOAP XML not found in response.")
        return None, None

    xml_content = match.group(0)
    root = ET.fromstring(xml_content)

    ns = {
        "soap": "http://schemas.xmlsoap.org/soap/envelope/",
        "ns3": "http://www.infocert.it/legalbus/cop/onboarding"
    }

    token_element = root.find(".//ns3:createDossierResponse/dossier-creation-info/tokens/tokens", ns)

    if token_element is None or not token_element.text:
        cfgservice.app_logger.error("Token URL not found in XML.")
        return None, None

    token_url = token_element.text.strip()

    parsed_url = urlparse(token_url)
    token = parse_qs(parsed_url.query).get("id", [None])[0]

    if not token:
        cfgservice.app_logger.error("Failed to extract Token ID from URL.")

    return token_url, token


def get_dossier(dossier_id):
    try:
        url = os.getenv("TOP_API_URL", "https://apistage.infocert.digital/onboarding/v1/dossier?mtom=false")
        company_id = os.getenv("TOP_COMPANY_ID", "INFOCERT_DEMO_EXT")
        payload = _get_dossier_payload(company_id, dossier_id)

        access_token = get_token()
        headers = {
            'Content-Type': 'application/xml',
            'Authorization': f'Bearer {access_token}'
        }

        response = requests.post(url, headers=headers, data=payload)

        if response.status_code != 200:
            cfgservice.app_logger.error(f"Failed to fetch dossier. Status: {response.status_code}, Response: {response.text}")
            return None

        return parse_soap_response(response.text)

    except Exception as e:
        cfgservice.app_logger.error(f"Error retrieving dossier: {str(e)}")
        return None


def _get_dossier_payload(company_id, dossier_id):
    payload = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:onb="http://www.infocert.it/legalbus/cop/onboarding">
            <soapenv:Header/>
            <soapenv:Body>
                <onb:getDossier>
                    <company-id>{company_id}</company-id>
                    <dossier-id>{dossier_id}</dossier-id>
                </onb:getDossier>
            </soapenv:Body>
        </soapenv:Envelope>
        """.strip()
    return payload


def _create_dossier_payload(company_id, dossier_id, dossier_type, default_redirect_url="", failure_redirect_url=""):
    payload = f"""
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <ns3:createDossier xmlns:ns2="http://www.infocert.it/legalbus/cop/onboarding/model/properties" xmlns:ns3="http://www.infocert.it/legalbus/cop/onboarding" xmlns:ns4="http://www.infocert.it/legalbus/cop/onboarding/model/identityassertion" xmlns:ns5="http://www.infocert.it/legalbus/cop/onboarding/model">
              <dossier company-id=\"{company_id}\" dossier-id=\"{dossier_id}\" dossier-type=\"{dossier_type}\">
                <business-id>\"{dossier_id}\"</business-id>
                <signers>
                  <signer signer-id="customer1" identity-assertion-policy="none" role="customer">
                   <person identified="false">
                      <legal-id country-code="IT" serial-type="TIN" serial-number=""/>  
                      <personal-data>
                        <first-name></first-name>
                        <last-name></last-name>
                        <full-first-name></full-first-name>
                        <full-last-name></full-last-name>
                        <birth-country></birth-country>
                      </personal-data>
                      
                      <address></address>
                      <identity-document-info></identity-document-info>
                    </person>
                    <default-redirect-url>{default_redirect_url}</default-redirect-url>
                    <failure-redirect-url>{failure_redirect_url}</failure-redirect-url>
                  </signer>
                </signers>
                <documents>
                  <document id="DOC-16779151841575365596432" type="INFOCERT CONTRACT">
                    <policy compose="false" sign="true" archive="false"/>
                    <content>
                      <mime-type>application/pdf</mime-type>
                      <data>JVBERi0xLjMKJeLjz9MKMSAwIG9iago8PC9QIDIgMCBSL1N1YnR5cGUvV2lkZ2V0L1QoZmlybWExKS9UeXBlL0Fubm90L0YgNC9GVC9TaWcvUmVjdFs5MCA3MCAyMzAgOTVdPj4KZW5kb2JqCjMgMCBvYmoKPDwvUCAyIDAgUi9TdWJ0eXBlL1dpZGdldC9UKGZpcm1hMikvVHlwZS9Bbm5vdC9GIDQvRlQvU2lnL1JlY3RbOTAgMTAwIDIzMCAxMjVdPj4KZW5kb2JqCjQgMCBvYmoKPDwvUCAyIDAgUi9TdWJ0eXBlL1dpZGdldC9UKGZpcm1hMykvVHlwZS9Bbm5vdC9GIDQvRlQvU2lnL1JlY3RbOTAgMTMwIDIzMCAxNTVdPj4KZW5kb2JqCjUgMCBvYmoKPDwvUCAyIDAgUi9TdWJ0eXBlL1dpZGdldC9UKGZpcm1hNCkvVHlwZS9Bbm5vdC9GIDQvRlQvU2lnL1JlY3RbOTAgMTYwIDIzMCAxODVdPj4KZW5kb2JqCjYgMCBvYmoKPDwvVHlwZS9DYXRhbG9nL0Fjcm9Gb3JtPDwvRmllbGRzWzEgMCBSIDMgMCBSIDQgMCBSIDUgMCBSXS9EQSgvSGVsdiAwIFRmIDAgZyApPj4vUGFnZXMgNyAwIFI+PgplbmRvYmoKNyAwIG9iago8PC9LaWRzWzIgMCBSXS9UeXBlL1BhZ2VzL0NvdW50IDEvUm90YXRlIDAvSVRYVCg1LjAuNCk+PgplbmRvYmoKMiAwIG9iago8PC9Db250ZW50cyA4IDAgUi9UeXBlL1BhZ2UvUmVzb3VyY2VzPDwvQ29sb3JTcGFjZSA5IDAgUi9Qcm9jU2V0Wy9QREYvVGV4dF0vRXh0R1N0YXRlIDEwIDAgUi9Gb250IDExIDAgUj4+L1BhcmVudCA3IDAgUi9Bbm5vdHNbMSAwIFIgMyAwIFIgNCAwIFIgNSAwIFJdL1JvdGF0ZSAwL01lZGlhQm94WzAgMCA1OTUgODQyXT4+CmVuZG9iago4IDAgb2JqCjw8L0ZpbHRlci9GbGF0ZURlY29kZS9MZW5ndGggMTM3OT4+c3RyZWFtCnicpVdbb1RVFN5TFeMxQU0glbfzYOgc4+zu++VVRNF4CXS0YMGXGlFDSUgf/A+1ndaa0jadFvEPov/Ab+19bp0WNMJkmjlr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SURTZXQgMjUgMCBSPj4KZW5kb2JqCjI2IDAgb2JqCjw8L0RXIDUwMC9DSURTeXN0ZW1JbmZvIDI3IDAgUi9TdWJ0eXBlL0NJREZvbnRUeXBlMC9CYXNlRm9udC9DVkpKVFcrUGFsYXRpbm9MaW5vdHlwZS1Sb21hbi1JZGVudGl0eS1IL0ZvbnREZXNjcmlwdG9yIDIzIDAgUi9UeXBlL0ZvbnQvV1szWzc3OCA2MTFdIDZbNzc0IDYxMV0gMTFbMzM3XSAxNFs2MTFdIDE2WzgzMSA3ODZdIDIwWzY2OCA1MjVdIDIzWzc3OCA3MjIgMTAwMF0gMTM5WzU1MyA0NDQgNjExIDQ3OSAzMzMgNTU2IDU4MiAyOTEgMjM0XSAxNDlbMjkxIDg4MyA1ODIgNTQ2IDYwMV0gMTU1WzM5NSA0MjQgMzI2IDYwMyA1NjUgODM0IDUxNiA1NTZdIDI4MVs2MDVdIDQ5NVsyNTAgMjUwIDI1MF0gNTUwWzMyMF0gNTU2WzMzM11dPj4KZW5kb2JqCjI3IDAgb2JqCjw8L1N1cHBsZW1lbnQgMC9SZWdpc3RyeShBZG9iZSkvT3JkZXJpbmcoSWRlbnRpdHkpPj4KZW5kb2JqCjI4IDAgb2JqCjw8L1N1YnR5cGUvVHlwZTAvQmFzZUZvbnQvQ1ZKSlRXK1BhbGF0aW5vTGlub3R5cGUtUm9tYW4tSWRlbnRpdHktSC1JZGVudGl0eS1IL1R5cGUvRm9udC9FbmNvZGluZy9JZGVudGl0eS1IL0Rlc2NlbmRhbnRGb250c1syNiAwIFJdPj4KZW5kb2JqCjI5IDAgb2JqCjw8L0Rlc2NlbnQgLTI5MS9DYXBIZWlnaHQgMTA1Mi9TdGVtViAwL0ZvbnRGaWxlMyAzMCAwIFIvVHlwZS9Gb250RGVzY3JpcHRvci9GbGFncyA0L0ZvbnROYW1lL0xPQ1FCVitQYWxhdGlub0xpbm90eXBlLUl0YWxpYy1JZGVudGl0eS1IL0ZvbnRCQm94Wy0xNjIgLTI5MSAwIDEwNTJdL0l0YWxpY0FuZ2xlIDAvQXNjZW50IDEwNTIvQ0lEU2V0IDMxIDAgUj4+CmVuZG9iagozMiAwIG9iago8PC9EVyAzODkvQ0lEU3lzdGVtSW5mbyAzMyAwIFIvU3VidHlwZS9DSURGb250VHlw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ZG9iagp4cmVmCjAgMzYKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDE1IDAwMDAwIG4gCjAwMDAwMDA1NzkgMDAwMDAgbiAKMDAwMDAwMDEwOSAwMDAwMCBuIAowMDAwMDAwMjA1IDAwMDAwIG4gCjAwMDAwMDAzMDEgMDAwMDAgbiAKMDAwMDAwMDM5NyAwMDAwMCBuIAowMDAwMDAwNTA3IDAwMDAwIG4gCjAwMDAwMDA3NzkgMDAwMDAgbiAKMDAwMDAxODQyMSAwMDAwMCBuIAowMDAwMDE4NDUyIDAwMDAwIG4gCjAwMDAwMTg0ODMgMDAwMDAgbiAKMDAwMDAwMjIyNiAwMDAwMCBuIAowMDAwMDAyMzY5IDAwMDAwIG4gCjAwMDAwMDI1MzIgMDAwMDAgbiAKMDAwMDAwMjYwMSAwMDAwMCBuIAowMDAwMDE4NTM3IDAwMDAwIG4gCjAwMDAwMzI3MjYgMDAwMDAgbiAKMDAwMDAwMjgwNSAwMDAwMCBuIAowMDAwMDAzMDM3IDAwMDAwIG4gCjAwMDAwMDMxMDYgMDAwMDAgbiAKMDAwMDAwMzI0MSAwMDAwMCBuIAowMDAwMDE2ODY4IDAwMDAwIG4gCjAwMDAwMTY5MDMgMDAwMDAgbiAKMDAwMDAyMDM4NSAwMDAwMCBuIAowMDAwMDMyODE2IDAwMDAwIG4gCjAwMDAwMTcxMjIgMDAwMDAgbiAKMDAwMDAxNzUwMyAwMDAwMCBuIAowMDAwMDE3NTcyIDAwMDAwIG4gCjAwMDAwMTc3MjIgMDAwMDAgbiAKMDAwMDAyOTE3OSAwMDAwMCBuIAowMDAwMDMyOTI0IDAwMDAwIG4gCjAwMDAwMTc5NDIgMDAwMDAgbiAKMDAwMDAxODIwMSAwMDAwMCBuIAowMDAwMDE4MjcwIDAwMDAwIG4gCjAwMDAwMzMwMTYgMDAwMDAgbiAKdHJhaWxlcgo8PC9JbmZvIDM1IDAgUi9JRCBbPGM3NTVlY2M3M2UyMmUzZDg2Y2RiNjgxODM1NGQ4OWJkPjw0Njg4MTU2MTFhZTc0NGM2Yzk3OWNkNjlmNmM0ZTQ0MT5dL1Jvb3QgNiAwIFIvU2l6ZSAzNj4+CnN0YXJ0eHJlZgozMzMwNQolJUVPRgo=</data>
                    </content>
                    <signature-policy>
                      <signature-fields>
                        <signature-field signer-id="customer1" name="firma1">
                          <reason>Reason firma1</reason>
                          <location>Location firma1</location>
                        </signature-field>
                        <signature-field signer-id="customer1" name="firma2">
                          <reason>Reason firma2</reason>
                          <location>Location firma2</location>
                        </signature-field>
                        <signature-field signer-id="customer1" name="firma3">
                          <reason>Reason firma3</reason>
                          <location>Location firma3</location>
                        </signature-field>
                        <signature-field signer-id="customer1" name="firma4">
                          <reason>Reason firma4</reason>
                          <location>Location firma4</location>
                        </signature-field>
                      </signature-fields>
                    </signature-policy>
                    <archiving-policy/>
                  </document>
                </documents>
              </dossier>
            </ns3:createDossier>
          </soap:Body>
        </soap:Envelope>
        """.strip()
    return payload
