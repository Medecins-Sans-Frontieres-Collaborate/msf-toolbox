from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from azure.core.credentials import TokenCredential
from azure.identity import (
    AzureCliCredential,
    DefaultAzureCredential,
    ManagedIdentityCredential,
)
from azure.keyvault.certificates import (
    CertificateClient,
    CertificateContentType,
    CertificatePolicy,
)
from azure.keyvault.certificates._models import KeyVaultCertificate
from azure.keyvault.secrets import DeletedSecret, KeyVaultSecret, SecretClient

if TYPE_CHECKING:
    from azure.keyvault.certificates import DeletedCertificate


def _read_certificate_file(certificate_path: str | Path) -> bytes:
    """Read a certificate file from disk and return its bytes.

    Notes:
        For PEM imports, the returned bytes must contain both the private key and
        the certificate(s).

    Args:
        certificate_path: Path to a certificate file (for example, ``.pfx``, ``.pem``, ``.cer``).

    Returns:
        Raw bytes of the certificate file.

    Raises:
        FileNotFoundError: If the certificate file does not exist.
        OSError: If there is an error reading the file.
    """
    path = Path(certificate_path)

    if not path.is_file():
        raise FileNotFoundError(f"Certificate file not found: {path}")

    try:
        return path.read_bytes()
    except OSError as exc:
        msg = f"Error reading certificate file {path}"
        raise OSError(msg) from exc


class AzureKeyvaultClient:
    """Client for interacting with an Azure Key Vault.

    This client provides methods for working with secrets and certificates.
    """

    def __init__(
        self,
        keyvault_url: str,
        local_run: bool = True,
        managed_identity_client_id: str | None = None,
    ) -> None:
        """Initialize the AzureKeyvaultClient and underlying Azure SDK clients.

        Args:
            keyvault_url: The URL of the Key Vault.
            local_run: Flag indicating if code is running locally.
            managed_identity_client_id: Optional managed identity client ID used
                when authenticating with ``ManagedIdentityCredential``.
        """
        self.local_run: bool = local_run
        self.managed_identity_client_id: str | None = managed_identity_client_id
        self.credential: TokenCredential = self._get_credential()
        self.keyvault_url: str = keyvault_url

        self.keyvault_client: SecretClient = SecretClient(
            vault_url=self.keyvault_url,
            credential=self.credential,
        )
        self.certificate_client: CertificateClient = CertificateClient(
            vault_url=self.keyvault_url,
            credential=self.credential,
        )

    def _get_credential(self) -> TokenCredential:
        """Determine the credential type based on the local_run flag.

        Returns:
            The credential instance used for authentication.
        """
        if self.local_run:
            return AzureCliCredential()

        if self.managed_identity_client_id is not None:
            return ManagedIdentityCredential(
                client_id=self.managed_identity_client_id,
            )

        return DefaultAzureCredential()

    def get_keyvault_secret_value(self, secret_name: str) -> str:
        """Get the value of a secret from the Key Vault.

        Args:
            secret_name: The name of the secret in the Key Vault.

        Returns:
            The secret value.
        """
        secret_value = self.keyvault_client.get_secret(secret_name).value
        return secret_value

    def list_secret_names(self) -> list[str]:
        """List the names of all secrets in the Key Vault.

        Returns:
            A list of secret names.
        """
        secrets = self.keyvault_client.list_properties_of_secrets()
        return [secret.name for secret in secrets]

    def set_keyvault_secret_value(
        self,
        secret_name: str,
        secret_value: str,
    ) -> KeyVaultSecret:
        """Create or update a secret in the Key Vault.

        Args:
            secret_name: The name of the secret to create or update.
            secret_value: The value of the secret.

        Returns:
            The newly created or updated secret.
        """
        secret = self.keyvault_client.set_secret(secret_name, secret_value)
        return secret

    def delete_keyvault_secret(self, secret_name: str) -> DeletedSecret:
        """Delete a secret from the Key Vault.

        Args:
            secret_name: The name of the secret to delete.

        Returns:
            The deleted secret.
        """
        deleted_secret = self.keyvault_client.begin_delete_secret(secret_name).result()
        return deleted_secret

    def list_deleted_keyvault_secrets(
        self,
        maxresults: int | None = None,
    ) -> list[str]:
        """List deleted secrets in the Key Vault.

        Args:
            maxresults: The maximum number of results to return, if any.

        Returns:
            A list of deleted secret names.
        """
        deleted_secrets = self.keyvault_client.list_deleted_secrets(
            max_page_size=maxresults,
        )
        return [secret.name for secret in deleted_secrets]

    def recover_keyvault_secret(self, secret_name: str) -> KeyVaultSecret:
        """Recover a soft-deleted secret in the Key Vault.

        Args:
            secret_name: The name of the secret to recover.

        Returns:
            The recovered secret.
        """
        recovered_secret = self.keyvault_client.begin_recover_deleted_secret(
            secret_name,
        ).result()
        return recovered_secret

    def get_keyvault_certificate(self, certificate_name: str) -> KeyVaultCertificate:
        """Get the latest version of a certificate from the Key Vault.

        Args:
            certificate_name: The name of the certificate in the Key Vault.

        Returns:
            The KeyVaultCertificate including policy and properties.
        """
        return self.certificate_client.get_certificate(certificate_name)

    def save_cert_string_to_pem(
        self,
        cert_string: str,
        out_path: str | Path,
    ) -> None:
        """Save a certificate string to a PEM file.

        If the input does not appear to be in PEM format (containing ``-----BEGIN``),
        a ValueError is raised.

        Args:
            cert_string: Certificate content from Azure Key Vault.
            out_path: Destination path for the output PEM file.

        Raises:
            ValueError: If ``cert_string`` is not in PEM format.
        """
        if not cert_string:
            raise ValueError(
                "cert_string is empty. Did you actually fetch it from Key Vault?",
            )

        cert_string = cert_string.strip()

        # Case 1: Already PEM.
        if "-----BEGIN" in cert_string:
            pem_bytes = cert_string.encode("ascii")
        else:
            raise ValueError(
                "Certificate string does not appear to be in PEM format.",
            )

        output_path = Path(out_path)
        output_path.write_bytes(pem_bytes)

    def save_keyvault_certificate_to_pem(
        self,
        certificate_name: str,
        out_path: str | Path,
    ) -> None:
        """Save a keyvault certificate to a PEM file.

        Notes:
            This method retrieves the certificate value from Key Vault as a secret,
            then saves it to a PEM file. When you create a certificate in Key Vault,
            the certificate is also stored as a secret with the same name.

        Args:
            certificate_name: Certificate name in Azure Key Vault.
            out_path: Destination path for the output PEM file.

        Raises:
            ResourceNotFoundError: If the certificate does not exist in Key Vault.
        """
        secret_value = self.get_keyvault_secret_value(certificate_name)
        self.save_cert_string_to_pem(secret_value, out_path)

    def list_certificate_names(self) -> list[str]:
        """List all certificate names in the Key Vault.

        Returns:
            A list of certificate names.
        """
        certs = self.certificate_client.list_properties_of_certificates()
        return [cert.name for cert in certs]

    def import_keyvault_certificate(
        self,
        certificate_name: str,
        certificate_bytes: bytes,
        **kwargs,
    ) -> KeyVaultCertificate:
        """Import a certificate (for example, PFX/PKCS12, PEM) into the Key Vault.

        Args:
            certificate_name: The name of the certificate to create or update.
            certificate_bytes: The certificate bytes (DER-encoded ``.cer``, PFX, or PEM-encoded ``.pem``).
            **kwargs: Additional keyword arguments passed to
                :meth:`CertificateClient.import_certificate`, such as:

                * ``password``: Password for the certificate, if applicable.
                * ``enabled``: Whether the certificate should be enabled.
                * ``tags``: Tags to associate with the certificate.

        Returns:
            The imported KeyVaultCertificate.
        """
        return self.certificate_client.import_certificate(
            certificate_name=certificate_name,
            certificate_bytes=certificate_bytes,
            **kwargs,
        )

    def import_keyvault_certificate_from_file(
        self,
        certificate_name: str,
        certificate_path: str | Path,
        **kwargs,
    ) -> KeyVaultCertificate:
        """Import a certificate from a file into the Key Vault.

        Args:
            certificate_name: The name of the certificate to create or update.
            certificate_path: Path to the certificate file (``.cer``, ``.pfx``, or ``.pem``).
            **kwargs: Additional keyword arguments passed to
                :meth:`CertificateClient.import_certificate`. See
                :meth:`import_keyvault_certificate` for commonly used options.

        Returns:
            The imported KeyVaultCertificate.
        """
        certificate_bytes = _read_certificate_file(certificate_path)

        # Policy must be added if importing a PEM file.
        certificate_path_str = str(certificate_path)
        if certificate_path_str.lower().endswith(".pem"):
            policy = CertificatePolicy(content_type=CertificateContentType.pem)
            kwargs["policy"] = policy

        return self.import_keyvault_certificate(
            certificate_name=certificate_name,
            certificate_bytes=certificate_bytes,
            **kwargs,
        )

    def delete_keyvault_certificate(
        self,
        certificate_name: str,
    ) -> DeletedCertificate:
        """Delete a certificate from the Key Vault.

        Args:
            certificate_name: The name of the certificate to delete.

        Returns:
            The DeletedCertificate result.
        """
        return self.certificate_client.begin_delete_certificate(
            certificate_name,
        ).result()

    def list_deleted_keyvault_certificates(
        self,
        maxresults: int | None = None,
    ) -> list[str]:
        """List deleted certificates in the Key Vault (when soft-delete is enabled).

        Args:
            maxresults: The maximum number of results to return, if any.

        Returns:
            A list of deleted certificate names.
        """
        deleted_certificates = self.certificate_client.list_deleted_certificates(
            max_page_size=maxresults,
        )
        return [cert.name for cert in deleted_certificates]

    def recover_keyvault_certificate(
        self,
        certificate_name: str,
    ) -> KeyVaultCertificate:
        """Recover a deleted certificate in the Key Vault.

        Args:
            certificate_name: The name of the deleted certificate to recover.

        Returns:
            The recovered KeyVaultCertificate.
        """
        return self.certificate_client.begin_recover_deleted_certificate(
            certificate_name,
        ).result()
