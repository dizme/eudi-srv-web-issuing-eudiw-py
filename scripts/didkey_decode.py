import base64
from multiformats import multibase, multicodec
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicNumbers

def decode_did_key_to_jwk(did_key: str) -> dict:
    try:
        if not did_key.startswith("did:key:"):
            raise ValueError("Not a valid did:key")

        method_specific_id = did_key.split(":")[2]
        raw_bytes = multibase.decode(method_specific_id)

        codec, key_bytes = multicodec.unwrap(raw_bytes)
        if codec.name != "jwk_jcs-pub":
            raise ValueError(f"Unsupported key type: {codec.name}")

        # key_bytes now contains the UTF-8 encoded JWK JSON
        import json
        jwk = json.loads(key_bytes.decode("utf-8"))

        # optionally validate EC curve
        if jwk.get("kty") != "EC" or jwk.get("crv") != "P-256":
            raise ValueError("Only EC P-256 JWKs are supported")

        # sanity check
        x_bytes = base64.urlsafe_b64decode(jwk["x"] + "==")
        y_bytes = base64.urlsafe_b64decode(jwk["y"] + "==")

        public_numbers = EllipticCurvePublicNumbers(
            x=int.from_bytes(x_bytes, "big"),
            y=int.from_bytes(y_bytes, "big"),
            curve=ec.SECP256R1()
        )
        public_numbers.public_key()

        return jwk

    except Exception as e:
        return {
            "error": "invalid_proof",
            "error_description": str(e)
        }

if __name__ == "__main__":

    didkey = "did:key:z2dmzD81cgPx8Vki7JbuuMmFYrWPgYoytykUZ3eyqht1j9KbsYahEzrVoTZpBAERn7Ns16GVBB9qoqbaCBGdQ2p6uMVntXD14Zc7czsUiRAjw2Xvzsgge5U5EKaYacbtyxx32NiGTjHySVaSRcFJ4U4gp37RnrDCpgm9uZUn9dhaLwQCkU#z2dmzD81cgPx8Vki7JbuuMmFYrWPgYoytykUZ3eyqht1j9KbsYahEzrVoTZpBAERn7Ns16GVBB9qoqbaCBGdQ2p6uMVntXD14Zc7czsUiRAjw2Xvzsgge5U5EKaYacbtyxx32NiGTjHySVaSRcFJ4U4gp37RnrDCpgm9uZUn9dhaLwQCkU"
    twoKeys = didkey.split("#")
    if len(twoKeys) > 1:
        print("Found two keys in didkey, printing them:")
        twoKeys[1] = "did:key:"+twoKeys[1]
        print(f"Key 1: {twoKeys[0]}")
        print(f"Key 2: {twoKeys[1]}")
        print("Decoding both keys to JWK format:")
        for key in twoKeys:
            result = decode_did_key_to_jwk(key)
            print(result)
    else:
        print("Only one key found, printing it")
        print(f"Key: {didkey}")
        print("Decoding key to JWK format:")
        result = decode_did_key_to_jwk(didkey)
        print(result)
