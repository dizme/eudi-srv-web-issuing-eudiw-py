DATE=$(date +%Y-%m-%d)
OUTDIR="../${DATE}"

# Verify chain (leaf validates against CA)
openssl verify -CAfile "${OUTDIR}/${DATE}.ca.cert.pem" "${OUTDIR}/${DATE}.cert.pem"

# Inspect leaf extensions (DER)
openssl x509 -in "${OUTDIR}/${DATE}.cert.der" -inform DER -text -noout