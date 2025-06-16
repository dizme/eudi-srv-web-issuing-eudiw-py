import base64
import json

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from pyasn1.type import univ, tag
from pyasn1.type.univ import Sequence


def b64pem_to_cose_and_jwk_base64(b64pem_str: str) -> tuple[dict, str]:
    # Decode the base64 PEM string
    device_key_bytes = base64.urlsafe_b64decode(b64pem_str.encode("utf-8"))

    # Load PEM public key
    public_key = serialization.load_pem_public_key(device_key_bytes)
    numbers = public_key.public_numbers()

    # Get coordinates
    x_bytes = numbers.x.to_bytes(32, byteorder="big")
    y_bytes = numbers.y.to_bytes(32, byteorder="big")

    # COSE_Key (EC2, ES256, P-256)
    cose_key = {
        1: 2,    # kty: EC2
        3: -7,   # alg: ES256
        -1: 1,   # crv: P-256
        -2: x_bytes,
        -3: y_bytes,
    }

    # JWK dict
    jwk = {
        "kty": "EC",
        "crv": "P-256",
        "x": base64.urlsafe_b64encode(x_bytes).decode().rstrip("="),
        "y": base64.urlsafe_b64encode(y_bytes).decode().rstrip("="),
    }

    # Base64 (not URL-safe) encode of the JWK JSON
    jwk_json = json.dumps(jwk, separators=(',', ':'))
    jwk_b64 = base64.b64encode(jwk_json.encode()).decode()

    return cose_key, jwk_b64

devicekeyinfo = "LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUZrd0V3WUhLb1pJemowQ0FRWUlLb1pJemowREFRY0RRZ0FFQXFJRjgvTlBhd1BjQzBqbjU3YUx1cm1BL2tGNApGT1RrVDBUVEJHOE15SFRVSnFZTWZaK0ZiUTlISnVUZDBmODJ4ZlBmK3ZjN0JhMnd2RCs1RWVveFpRPT0KLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tCg=="

cose_key, jwk_b64 = b64pem_to_cose_and_jwk_base64(devicekeyinfo)
# Print the results
print("COSE Key:", cose_key)
print("JWK Base64:", jwk_b64)

from pyasn1.codec.der.decoder import decode as der_decode
from pyasn1_modules import rfc2459

def load_tbs_cert_from_pem(pem_str):
    cert = x509.load_pem_x509_certificate(pem_str.encode())
    der = cert.public_bytes(serialization.Encoding.DER)
    seq, _ = der_decode(der, asn1Spec=rfc2459.Certificate())
    return cert, seq.getComponentByName("tbsCertificate")

def load_tbs_cert_from_der_file(path):
    with open(path, "rb") as f:
        cert = x509.load_der_x509_certificate(f.read(), backend=default_backend())
        seq, _ = der_decode(cert.public_bytes(serialization.Encoding.DER), asn1Spec=rfc2459.Certificate())
        return cert, seq.getComponentByName("tbsCertificate")

def compare_tbs_cert_fields(tbs1, tbs2):
    def compare_tbs_cert_fields(tbs1, tbs2):
        print("\n=== Comparison of TBSCertificate Fields ===")
        names = [nt.name for nt in tbs1.componentType.namedTypes]
        for name in names:
            val1 = tbs1.getComponentByName(name)
            val2 = tbs2.getComponentByName(name)

            exists1 = val1 is not None and val1.hasValue()
            exists2 = val2 is not None and val2.hasValue()

            status = "✅ Both present" if exists1 and exists2 else "❌ Mismatch"
            print(f"\n{name}: {status}")
            print(f"  PEM cert: {val1.prettyPrint() if exists1 else '❌ MISSING'}")
            print(f"  DER cert: {val2.prettyPrint() if exists2 else '❌ MISSING'}")


der_cert_path = "../api_docs/test_tokens/DS-token/PID-DS-0002/PID-DS-0002.cert.der"
pem_cert = """-----BEGIN CERTIFICATE-----
MIICCjCCAWwCFE7eMyTfI0qEMBTG9El/djOaFO/nMAoGCCqGSM49BAMCMEQxCzAJ
BgNVBAYTAklUMREwDwYDVQQKDAhJbmZvQ2VydDEMMAoGA1UECwwDSW9UMRQwEgYD
VQQDDAtDQk9SU2VydmljZTAeFw0yNTA1MTkxNTM3NTNaFw0yNjA1MTkxNTM3NTNa
MEQxCzAJBgNVBAYTAklUMREwDwYDVQQKDAhJbmZvQ2VydDEMMAoGA1UECwwDSW9U
MRQwEgYDVQQDDAtDQk9SU2VydmljZTCBmzAQBgcqhkjOPQIBBgUrgQQAIwOBhgAE
AFsurXB00MNGDZI10YQykHGRuI6WE9tXq83Paqhd/pfXG/D7Zn0T+zdSmSWenmgF
6GEfV7mdJX3R1lMm3LZJITF0ATkeQQKiohElOlAnt4yZX+90e+ovZN9PMyn84RQ8
xxwsZ8gzVa++QCvd/RnBVJt/MsxpeHojdykEClko0MRrfvrBMAoGCCqGSM49BAMC
A4GLADCBhwJBK7HHjZ29YMFPIo30DhWqbHGdyU+54QE2px8e7FXtqYDK0zrFbiI1
7MOs/V3ojeV0nIrAkOGDUpuI6uRgpQlv7UICQgGdMjGoBOh+SdrdVNaeoMC7lWDa
8PFPBbANKv2cUl4Zr3XLX8w/9Wv6f3ClxKw9b7dyuyjPIFNnkyFGPzIwf6zUvQ==
-----END CERTIFICATE-----"""

# Load certs and compare
cert1, tbs1 = load_tbs_cert_from_pem(pem_cert)
cert2, tbs2 = load_tbs_cert_from_der_file(der_cert_path)

compare_tbs_cert_fields(tbs1, tbs2)

def check_cert_version(pem_str: str):
    cert = x509.load_pem_x509_certificate(pem_str.encode())
    der = cert.public_bytes(serialization.Encoding.DER)
    cert_seq, _ = der_decode(der, asn1Spec=rfc2459.Certificate())
    tbs_cert = cert_seq.getComponentByName("tbsCertificate")
    try:
        version = tbs_cert.getComponentByName("version")
        version_value = int(version) if version.hasValue() else 0
    except Exception:
        version_value = 0
    print(f"Certificate version: v{version_value + 1} (raw={version_value})")
    explicit_version = univ.Integer(version_value).subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0)
    )
    tbs_cert.setComponentByName("version", explicit_version)
    # Re-encode full certificate with updated tbsCertificate
    cert_seq.setComponentByName("tbsCertificate", tbs_cert)
    from pyasn1.codec.der.encoder import encode as der_encode
    updated_der = der_encode(cert_seq)
    return x509.load_der_x509_certificate(updated_der, default_backend())

def has_explicit_version(pem_cert: str) -> bool:
    cert = x509.load_pem_x509_certificate(pem_cert.encode())
    der = cert.public_bytes(serialization.Encoding.DER)

    # Decode the outer Certificate SEQUENCE
    cert_seq, _ = der_decode(der, asn1Spec=Sequence())
    tbs_cert = cert_seq.getComponentByPosition(0)  # TBSCertificate

    first = tbs_cert.getComponentByPosition(0)
    # Check if tag is [0] EXPLICIT (context-specific, constructed, tag number 0)
    return first.tagSet == tag.TagSet(
        tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0)
    )


# Example usage
if has_explicit_version(pem_cert):
    print("✅ version field is explicitly present")
else:
    print("❌ version field is absent (implied v1)")

# # Fix version and reload
cert_fixed = check_cert_version(pem_cert)
seq, _ = der_decode(cert_fixed.public_bytes(serialization.Encoding.DER), asn1Spec=rfc2459.Certificate())
certNew, tbsNew = cert_fixed, seq.getComponentByName("tbsCertificate")
compare_tbs_cert_fields(tbs1, tbsNew)

