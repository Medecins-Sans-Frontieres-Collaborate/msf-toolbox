"""Utility for generating self-signed X.509 certificates and private keys."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def generate_self_signed_certificate(
    email_address: str,
    common_name: str,
    country_name: str,
    locality_name: str,
    state_or_province_name: str,
    organization_name: str,
    organizational_unit_name: str,
    serial_number: int = 1,
    validity_days: int = 365,
    key_size: int = 2048,
    cert_path: Optional[str | Path] = "selfsigned.crt",
    key_path: Optional[str | Path] = "private.key",
    combined_pem_path: Optional[str | Path] = None,
) -> tuple[bytes, bytes]:
    """Generate a self-signed X.509 certificate and private key.

    The certificate and private key PEM bytes are always returned. Optionally,
    the certificate, key, and/or a combined PEM can be written to disk.

    Args:
        email_address: Email address for the certificate subject.
        common_name: Common Name (CN) for the certificate subject.
        country_name: Country Name (C) for the certificate subject.
        locality_name: Locality or city (L) for the certificate subject.
        state_or_province_name: State or province (ST) for the certificate subject.
        organization_name: Organization Name (O) for the certificate subject.
        organizational_unit_name: Organizational Unit (OU) for the certificate subject.
        serial_number: Serial number for the certificate.
        validity_days: Offset in days from now for the certificate
            expiration time.
        key_size: RSA key size in bits.
        cert_path: Optional path to write the certificate file. If ``None``, the
            certificate is not written to disk.
        key_path: Optional path to write the private key file. If ``None``, the
            private key is not written to disk.
        combined_pem_path: Optional path to write a combined PEM file containing
            both the certificate and private key. If ``None``, no combined file
            is written.

    Returns:
        A tuple ``(certificate_pem, private_key_pem)`` containing the generated
        certificate and private key in PEM format.
    """
    # Example to inspect the generated certificate with OpenSSL:
    #   openssl x509 -inform pem -in selfsigned.crt -noout -text

    # Generate RSA private key
    key: rsa.RSAPrivateKey = rsa.generate_private_key(
        public_exponent=65537, key_size=key_size
    )

    # Certificate subject/issuer
    name = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, country_name),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, state_or_province_name),
            x509.NameAttribute(NameOID.LOCALITY_NAME, locality_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization_name),
            x509.NameAttribute(
                NameOID.ORGANIZATIONAL_UNIT_NAME, organizational_unit_name
            ),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            x509.NameAttribute(NameOID.EMAIL_ADDRESS, email_address),
        ]
    )

    # Build the certificate
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(serial_number)
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=validity_days))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(private_key=key, algorithm=hashes.SHA512())
    )

    # Convert to PEM
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,  # produces "PRIVATE KEY"
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Write individual files if requested
    if cert_path is not None:
        Path(cert_path).write_bytes(cert_pem)

    if key_path is not None:
        Path(key_path).write_bytes(key_pem)

    # Optional: combined PEM
    if combined_pem_path is not None:
        Path(combined_pem_path).write_bytes(cert_pem + key_pem)

    return cert_pem, key_pem


if __name__ == "__main__":
    # Example usage with placeholder subject fields.
    generate_self_signed_certificate(
        email_address="email@example.com",
        common_name="example.com",
        country_name="NT",
        locality_name="Example City",
        state_or_province_name="Example State",
        organization_name="Example Org",
        organizational_unit_name="Example Unit",
        combined_pem_path="selfsigned_with_key.pem",
    )
