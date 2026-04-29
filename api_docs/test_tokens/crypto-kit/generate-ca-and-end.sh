set -euo pipefail

DATE=$(date +%Y-%m-%d)
OUTDIR="../${DATE}"

mkdir -p "${OUTDIR}"
mkdir -p "./newcerts"

# OpenSSL CA bookkeeping files (required by openssl ca)
: > ./index.txt
[ -f ./serial ] || echo 1000 > ./serial

############################################
# A) Create a local CA (trust anchor)
############################################

# CA private key
openssl ecparam -name prime256v1 -genkey -noout -out "${OUTDIR}/${DATE}.ca.key.pem"

# CA self-signed certificate (this is the one you import as trusted CA)
openssl req -new -x509 \
  -key "${OUTDIR}/${DATE}.ca.key.pem" \
  -out "${OUTDIR}/${DATE}.ca.cert.pem" \
  -days 3650 \
  -sha256 \
  -subj "/C=UT/O=EUDI Wallet Reference Implementation/CN=Local Issuing CA ${DATE}" \
  -extensions v3_ca \
  -config issuing.cnf

############################################
# B) Create end-entity (leaf) key + CSR
############################################

# Leaf private key (the one your app uses for signing)
openssl ecparam -name prime256v1 -genkey -noout -out "${OUTDIR}/${DATE}.key.pem"

# CSR for the leaf
openssl req -new \
  -key "${OUTDIR}/${DATE}.key.pem" \
  -out "${OUTDIR}/${DATE}.csr.pem" \
  -subj "/C=UT/O=EUDI Wallet Reference Implementation/CN=Signing EE ${DATE}"

############################################
# C) Sign leaf cert with CA (end-entity)
############################################

# Issue the end-entity cert (PEM)
openssl ca -batch \
  -config issuing.cnf \
  -keyfile "${OUTDIR}/${DATE}.ca.key.pem" \
  -cert "${OUTDIR}/${DATE}.ca.cert.pem" \
  -in "${OUTDIR}/${DATE}.csr.pem" \
  -out "${OUTDIR}/${DATE}.cert.pem" \
  -extensions v3_sign_ee

# Convert leaf certificate to DER (what your app wants)
openssl x509 \
  -in "${OUTDIR}/${DATE}.cert.pem" \
  -out "${OUTDIR}/${DATE}.cert.der" \
  -outform DER

# Optional cleanup (keep CSR if you want)
rm "${OUTDIR}/${DATE}.csr.pem"