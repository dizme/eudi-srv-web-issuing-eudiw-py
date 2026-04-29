# Signing certificate (CA-issued end-entity)

This folder contains the material required to generate an **end-entity (leaf) signing
certificate** issued by a local Certification Authority (CA).

Some applications reject self-signed leaf certificates (treating them as trust anchors
or IACA certificates). For this reason, the signing certificate is issued by a dedicated
local CA and must be validated against that CA.

The generated certificate is intended for **document or artifact signing**
(e.g. PID / wallet-related signatures) and **not** for TLS.

---

## Output layout

Artifacts are generated into a date-based folder one level above the script location:

../YYYY-MM-dd/

### Files

- `YYYY-MM-dd.key.pem`  
  ECDSA **end-entity private key** (PEM).  
  Used by the application to create signatures.  
  **Must be kept secret.**

- `YYYY-MM-dd.cert.der`  
  End-entity X.509 certificate (DER), issued by the local CA.  
  Used by the application to identify the signer.

- `YYYY-MM-dd.cert.pem`  
  End-entity certificate in PEM format.  
  Generated temporarily and used only for DER conversion.

- `YYYY-MM-dd.ca.cert.pem`  
  Local **Issuing CA certificate** (PEM).  
  This certificate must be imported into the application or trust store
  as a trusted CA.

- `YYYY-MM-dd.ca.key.pem`  
  Local CA private key (PEM).  
  **Highly sensitive** — should be stored securely and ideally offline.

---

## Certificate profile (end-entity)

The end-entity (leaf) certificate is generated with the following extensions:

- `basicConstraints`: critical, `CA:FALSE`
- `keyUsage`: critical, `digitalSignature`
- `extendedKeyUsage`: critical, `1.3.130.2.0.0.1.2` (custom / private EKU OID)
- `subjectKeyIdentifier`: hash
- `authorityKeyIdentifier`: keyid

Key characteristics:

- Key algorithm: ECDSA (prime256v1 / P-256)
- Signature algorithm: SHA256withECDSA
- Certificate role: End-entity (non-CA)

---

## Trust model

- The **CA certificate** (`YYYY-MM-dd.ca.cert.pem`) acts as the trust anchor
- The **end-entity certificate** (`YYYY-MM-dd.cert.der`) is used for signing
- The application must:
  1. Trust the CA certificate
  2. Validate the end-entity certificate chain against that CA

The end-entity certificate is **not self-signed**.

---

## How to generate

### Prerequisites

- OpenSSL (1.1.1 or newer)
- Configuration file `issuing.cnf` defining:
  - CA profile
  - End-entity signing profile (`v3_sign_ee`)

### Generation steps

```bash
# Date prefix
DATE=$(date +%Y-%m-%d)

# Target directory (one level up)
OUTDIR="../${DATE}"

# Create output directory
mkdir -p "${OUTDIR}"

# --- A) Generate CA key and certificate ---

openssl ecparam \
  -name prime256v1 \
  -genkey \
  -noout \
  -out "${OUTDIR}/${DATE}.ca.key.pem"

openssl req -new -x509 \
  -key "${OUTDIR}/${DATE}.ca.key.pem" \
  -out "${OUTDIR}/${DATE}.ca.cert.pem" \
  -days 3650 \
  -sha256 \
  -extensions v3_ca \
  -config issuing.cnf

# --- B) Generate end-entity key and CSR ---

openssl ecparam \
  -name prime256v1 \
  -genkey \
  -noout \
  -out "${OUTDIR}/${DATE}.key.pem"

openssl req -new \
  -key "${OUTDIR}/${DATE}.key.pem" \
  -out "${OUTDIR}/${DATE}.csr.pem"

# --- C) Issue end-entity certificate from CA ---

openssl ca -batch \
  -config issuing.cnf \
  -keyfile "${OUTDIR}/${DATE}.ca.key.pem" \
  -cert "${OUTDIR}/${DATE}.ca.cert.pem" \
  -in "${OUTDIR}/${DATE}.csr.pem" \
  -out "${OUTDIR}/${DATE}.cert.pem" \
  -extensions v3_sign_ee

# --- D) Convert end-entity cert to DER ---

openssl x509 \
  -in "${OUTDIR}/${DATE}.cert.pem" \
  -out "${OUTDIR}/${DATE}.cert.der" \
  -outform DER

# Optional cleanup
rm "${OUTDIR}/${DATE}.csr.pem"

```

Verification

Verify the certificate chain:

```bash
openssl verify \
  -CAfile "../YYYY-MM-dd/YYYY-MM-dd.ca.cert.pem" \
  "../YYYY-MM-dd/YYYY-MM-dd.cert.pem"
```

Inspect the end-entity certificate (DER):

```bash
openssl x509 \
  -in "../YYYY-MM-dd/YYYY-MM-dd.cert.der" \
  -inform DER \
  -text -noout
```

Notes
	•	This setup is intended for controlled / internal environments
	•	The CA certificate must be explicitly trusted by any verifier
	•	Key rotation is handled naturally via date-based folders
	•	Do not reuse the CA private key across unrelated environments