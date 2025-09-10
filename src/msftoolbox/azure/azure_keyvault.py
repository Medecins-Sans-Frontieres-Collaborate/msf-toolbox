import os
from typing import TYPE_CHECKING

from azure.keyvault.certificates._models import KeyVaultCertificate
from azure.keyvault.secrets import SecretClient
from azure.keyvault.certificates import CertificateClient, CertificatePolicy, CertificateContentType
from azure.identity import AzureCliCredential, DefaultAzureCredential, ManagedIdentityCredential

if TYPE_CHECKING:
    from azure.keyvault.certificates import DeletedCertificate, KeyVaultCertificate

def _read_certificate_file(certificate_path: str) -> bytes:
    """Read a certificate file from disk and return its bytes.

    Notes:
        For PEM imports, the returned bytes must contain both the private key and
        the certificate(s). If your key and cert are separate files, use
        `read_pem_bundle` instead.

    Args:
        path: Path to a certificate file (e.g., `.pfx`, `.pem`, `.cer`).

    Returns:
        Raw bytes of the certificate file.

    Raises:
        FileNotFoundError: If the certificate file does not exist.
        IOError: If there is an error reading the file.
    """
    if not os.path.isfile(certificate_path):
        raise FileNotFoundError(f"Certificate file not found: {certificate_path}")

    try:
        with open(certificate_path, 'rb') as cert_file:
            certificate_bytes = cert_file.read()
        return certificate_bytes
    except IOError as e:
        raise IOError(f"Error reading certificate file {certificate_path}: {e}")

class AzureKeyvaultClient:
    """
    A class to interact with an Azure Key Vault.

    This class provides methods to send, read, and delete secrets in Azure Key Vault.
    """
    def __init__(
        self,
        keyvault_url: str,
        local_run: bool = True,
        managed_identity_client_id: str = None
        ):
        """
        Initialize the AzureConnector with subscription_id and determine the credential type.

        Args:
            keyvault_url (string): The URL of the Key Vault.
            local_run (bool): Flag to determine if running locally or in production.
            managed_identity_client_id (str): The managed_identity_client_id required for ManagedIdentityCredentials
        """
        self.local_run = local_run
        self.managed_identity_client_id = managed_identity_client_id
        self.credential = self._get_credential()
        self.keyvault_url = keyvault_url
        self.keyvault_client = SecretClient(
            vault_url=self.keyvault_url,
            credential=self.credential
            )
        
        self.certificate_client = CertificateClient(
            vault_url=self.keyvault_url, credential=self.credential
        )

    def _get_credential(
        self
        ):
        """
        Determine the credential type based on the local_run flag.

        Returns:
            credential (object): The credentials to be used for authentication.
        """
        if self.local_run:
            return AzureCliCredential()
        elif self.managed_identity_client_id is not None:
            return ManagedIdentityCredential(
                client_id = self.managed_identity_client_id
                )
        else:
            return DefaultAzureCredential()


    def get_keyvault_secret_value(
        self,
        secret_name: str
        ):
        """
        Get a secret from the Key Vault.

        Args:
            secret_name (string): The name of the secret in the Key Vault.

        Returns:
            String: The secret value.
        """
        secret_value = self.keyvault_client.get_secret(
            secret_name
            ).value

        return secret_value

    def list_secret_names(
        self
        ):
        """
        List all secrets in the Key Vault.

        Returns:
            List: A list of secret names.
        """

        secrets = self.keyvault_client.list_properties_of_secrets()
        return [secret.name for secret in secrets]

    def set_keyvault_secret_value(
        self,
        secret_name: str,
        secret_value: str
        ):
        """
        Set a secret in the Key Vault.

        Args:
            secret_name (string): The name of the secret to be set in the Key Vault.
            secret_value (string): The value of the secret to be set in the Key Vault.

        Returns:
            Secret: The newly created or updated secret.
        """
        secret = self.keyvault_client.set_secret(
            secret_name,
            secret_value
            )

        return secret

    def delete_keyvault_secret(
        self,
        secret_name: str
        ):
        """
        Delete a secret from the Key Vault.

        Args:
            secret_name (string): The name of the secret to be deleted from the Key Vault.

        Returns:
            DeletedSecret: The deleted secret.
        """
        deleted_secret = self.keyvault_client.begin_delete_secret(
            secret_name
            ).result()

        return deleted_secret

    def list_deleted_keyvault_secrets(
        self,
        maxresults: int | None=None
        ):
        """
        List deleted secrets in the Key Vault.

        Args:
            maxresults (int, optional): The maximum number of results to return.

        Returns:
            List: A list of deleted secret names.
        """
        deleted_secrets = self.keyvault_client.list_deleted_secrets(
            max_page_size=maxresults
            )

        return [secret.name for secret in deleted_secrets]

    def recover_keyvault_secret(
        self,
        secret_name: str
        ):
        """
        Recover a deleted secret in the Key Vault.

        Args:
            secret_name (string): The name of the secret to be recovered from the Key Vault.

        Returns:
            Secret: The recovered secret.
        """
        recovered_secret = self.keyvault_client.begin_recover_deleted_secret(
            secret_name
            ).result()

        return recovered_secret

    def get_keyvault_certificate(self, certificate_name: str) -> "KeyVaultCertificate":
        """Get a certificate (latest version) from the Key Vault.

        Args:
            certificate_name: The name of the certificate in the Key Vault.

        Returns:
            The KeyVaultCertificate object (includes policy and properties).
        """
        return self.certificate_client.get_certificate(certificate_name)

    def list_certificate_names(self) -> list[str]:
        """List all certificate names in the Key Vault.

        Returns:
            A list of certificate names.
        """
        certs = self.certificate_client.list_properties_of_certificates()
        return [c.name for c in certs]

    def import_keyvault_certificate(
        self,
        certificate_name: str,
        certificate_bytes: bytes,
        **kwargs
    ) -> "KeyVaultCertificate":
        """Import a certificate (e.g., PFX/PKCS12) into the Key Vault.

        Args:
            certificate_name: The name of the certificate to create/update.
            certificate_bytes: The certificate bytes (DER-encoded .cer or PFX).
        
        Kwargs:
            password: Password for the PFX if applicable.
            enabled: Whether the certificate should be enabled.
            tags: Optional tags to associate with the certificate.

        Returns:
            The imported KeyVaultCertificate.
        """
        
        return self.certificate_client.import_certificate(
            certificate_name=certificate_name,
            certificate_bytes=certificate_bytes,
            **kwargs
        )
    
    def import_keyvault_certificate_from_file(
        self,
        certificate_name: str,
        certificate_path: str,
        **kwargs
    ) -> "KeyVaultCertificate":
        """Import a certificate from a file into the Key Vault.

        Args:
            certificate_name: The name of the certificate to create/update.
            certificate_path: Path to the certificate file (.cer or .pfx).
        
        Kwargs:
            password: Password for the PFX if applicable.
            enabled: Whether the certificate should be enabled.
            tags: Optional tags to associate with the certificate.

        Returns:
            The imported KeyVaultCertificate.
        """
        certificate_bytes: bytes = _read_certificate_file(certificate_path)

        # Policy must be added if importing a .pem file
        if ".pem" in certificate_path:
            policy = CertificatePolicy(content_type=CertificateContentType.pem)
            kwargs["policy"] = policy

        return self.import_keyvault_certificate(
            certificate_name=certificate_name,
            certificate_bytes=certificate_bytes,
            **kwargs
        )

    def delete_keyvault_certificate(self, certificate_name: str) -> "DeletedCertificate":
        """Delete a certificate from the Key Vault.

        Args:
            certificate_name: The name of the certificate to delete.

        Returns:
            The DeletedCertificate result.
        """
        return self.certificate_client.begin_delete_certificate(certificate_name).result()

    def list_deleted_keyvault_certificates(
        self, maxresults: int | None = None
    ) -> list[str]:
        """List deleted certificates in the Key Vault (only if soft-delete is enabled).

        Args:
            maxresults: The maximum number of results to return.

        Returns:
            A list of deleted certificate names.
        """
        deleted = self.certificate_client.list_deleted_certificates(
            max_page_size=maxresults
        )
        return [c.name for c in deleted]

    def recover_keyvault_certificate(self, certificate_name: str) -> KeyVaultCertificate:
        """Recover a deleted certificate in the Key Vault.

        Args:
            certificate_name: The name of the deleted certificate to recover.

        Returns:
            The recovered KeyVaultCertificate.
        """
        return self.certificate_client.begin_recover_deleted_certificate(
            certificate_name
        ).result()
