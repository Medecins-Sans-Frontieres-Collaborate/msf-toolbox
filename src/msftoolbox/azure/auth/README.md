# Azure Authentication Module

Minimal, policy-driven authentication for all Azure clients in this codebase.

* **Single surface:** return a standard `TokenCredential` that works with every Azure SDK.
* **Configuration, not code:** choose a strategy (Default, CLI, Managed Identity, Client Secret, Certificate, Workload Identity, Interactive) via env vars or a typed settings object.
* **Pure helpers:** scope utilities for Graph and SharePoint; client wiring lives in their respective modules.
* **Python 3.10+** with `match` in the factory.

---

## Why this module exists

Most of our clients (Storage, Key Vault, OpenAI, Graph, SharePoint) need the same thing: a correctly constructed `TokenCredential` and, occasionally, a scope string. This module centralizes:

* **Credential selection policy** (how we decide *which* credential to use).
* **Configuration & validation** (via Pydantic settings).
* **Scope helpers** (so callers don’t hand-roll resource scopes).

We rely on Azure’s own abstraction: `azure.core.credentials.TokenCredential`.

---

## Install

This module assumes these dependencies in your project:

```bash
pip install azure-identity pydantic>=2 pydantic-settings>=2
```

---

## Module layout

```
msftoolbox/azure/auth/
├── __init__.py          # re-exports: get_credential, scopes.*
├── config.py            # Pydantic BaseSettings (AuthConfig, Strategy)
├── factory.py           # get_credential(config: AuthConfig|None) -> TokenCredential
└── scopes.py            # GRAPH_DEFAULT_SCOPE, authority_from_url(), spo_scope_from_url()
```

> SharePoint wiring (building a `ClientContext` / token factory) is intentionally **not** here. It lives in `msftoolbox/sharepoint/`, which can import `get_credential()` and `scopes.spo_scope_from_url()`.

---

## Public API (stable)

* `msftoolbox.azure.auth.factory.get_credential(config: AuthConfig | None = None) -> TokenCredential`
* `msftoolbox.azure.auth.config.AuthConfig` (Pydantic `BaseSettings`)
* `msftoolbox.azure.auth.config.Strategy` (enum)
* `msftoolbox.azure.auth.scopes.authority_from_url(site_url: str) -> str`
* `msftoolbox.azure.auth.scopes.GRAPH_DEFAULT_SCOPE -> Final[str]`
* `msftoolbox.azure.auth.scopes.spo_scope_from_url(site_url: str) -> str`

`__init__.py` re-exports the most common items for convenience:

```python
from msftoolbox.azure.auth import get_credential
from msftoolbox.azure.auth import scopes
```

---

## Quick start

### Configure via environment variables

Pick a strategy:

```bash
# Default chain (managed identity, env vars, etc.)
export AZURE_AUTH_STRATEGY=default

# or use CLI
export AZURE_AUTH_STRATEGY=cli

# or managed identity (optionally specify user-assigned)
export AZURE_AUTH_STRATEGY=managed_identity
export AZURE_MANAGED_IDENTITY_CLIENT_ID=<client-id>

# or client secret
export AZURE_AUTH_STRATEGY=client_secret
export AZURE_TENANT_ID=<tenant-id>
export AZURE_CLIENT_ID=<client-id>
export AZURE_CLIENT_SECRET=<secret>

# or certificate
export AZURE_AUTH_STRATEGY=client_certificate
export AZURE_TENANT_ID=<tenant-id>
export AZURE_CLIENT_ID=<client-id>
export AZURE_CLIENT_CERTIFICATE_PATH=/path/to/cert.pem
export AZURE_CLIENT_CERTIFICATE_PASSWORD=<optional-password>

# optional for sovereign clouds
export AZURE_AUTHORITY_HOST=https://login.microsoftonline.us
```

Then:

```python
from msftoolbox.azure.auth import get_credential

credential = get_credential()  # reads env, validates, returns a TokenCredential
```

### Or configure in code

```python
from msftoolbox.azure.auth import AuthConfig, Strategy, get_credential

cfg = AuthConfig(
    strategy=Strategy.CLIENT_SECRET,
    tenant_id="00000000-0000-0000-0000-000000000000",
    client_id="11111111-1111-1111-1111-111111111111",
    client_secret="super-secret",  # SecretStr also accepted via env
)

credential = get_credential(cfg)
```

Since Strategy is an enum, you can of course choose to just write a string equivalent e.g. "client_secret".

---

## Using the credential

### Azure SDK clients (Storage, Key Vault, etc.)

```python
from azure.storage.blob import BlobServiceClient
from azure.keyvault.secrets import SecretClient

from msftoolbox.azure.auth import get_credential

cred = get_credential()

blob = BlobServiceClient(account_url="https://<acct>.blob.core.windows.net", credential=cred)
kv = SecretClient(vault_url="https://<vault>.vault.azure.net/", credential=cred)
```

### Microsoft Graph (scoped token)

```python
from azure.auth import get_credential, scopes

cred = get_credential()
token = cred.get_token(scopes.GRAPH_DEFAULT_SCOPE)
headers = {"Authorization": f"Bearer {token.token}"}
# use with requests

# or for MS Graph SDK
from msgraph import GraphServiceClient
graph_client = GraphServiceClient(cred, [scopes.GRAPH_DEFAULT_SCOPE])
```

### SharePoint (handled in `msftoolbox/sharepoint/`)

Your SharePoint module can do:

```python
from time import time
from office365.runtime.auth.token_response import TokenResponse
from office365.sharepoint.client_context import ClientContext
from azure.auth import get_credential, scopes

def build_client_context(site_url: str) -> ClientContext:
    cred = get_credential()
    scope = scopes.spo_scope_from_url(site_url)

    def _factory() -> TokenResponse:
        tok = cred.get_token(scope)
        return TokenResponse.from_json({
            "token_type": "Bearer",
            "access_token": tok.token,
            "expires_in": max(1, int(tok.expires_on - time())),
        })

    return ClientContext(site_url).with_access_token(_factory)
```

---

## Strategies & environment variables

| Strategy            | `AZURE_AUTH_STRATEGY` value | Required vars                                                         | Optional vars                                                |
| ------------------- | --------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------ |
| Default chain       | `default`                   | —                                                                     | `AZURE_AUTHORITY_HOST`                                       |
| Azure CLI           | `cli`                       | —                                                                     | `AZURE_AUTHORITY_HOST`                                       |
| Managed Identity    | `managed_identity`          | —                                                                     | `AZURE_MANAGED_IDENTITY_CLIENT_ID`, `AZURE_AUTHORITY_HOST`   |
| Client Secret       | `client_secret`             | `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`           | `AZURE_AUTHORITY_HOST`                                       |
| Client Certificate  | `client_certificate`        | `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_CERTIFICATE_PATH` | `AZURE_CLIENT_CERTIFICATE_PASSWORD`, `AZURE_AUTHORITY_HOST`  |                                     |
| Interactive Browser | `interactive_browser`       | —                                                                     | `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_AUTHORITY_HOST` |

Notes:

* All `AZURE_` prefixed environment variables are treated as **aliases** for e.g. `client_id`, `client_secret` so you can also define them
this way in your `.env` (`CLIENT_SECRET`).
* Paths (certificate/token file) must exist; invalid paths raise at startup.
* Secrets use `SecretStr` when loaded from env through Pydantic; they’re only unwrapped inside the factory.

---

## Design decisions

* **No custom base classes:** We rely on `TokenCredential` everywhere. One abstraction, zero indirection.
* **Factory first:** `get_credential()` is the only way to build credentials, implemented with `match` (Python 3.10+).
* **Pydantic settings:** Typed, validated configuration; environment-first by default.
* **Scopes:** `spo_scope_from_url()` is a  small helper; no hidden state. `GRAPH_DEFAULT_SCOPE` is a simple constant.

This makes the module easy to test, predictable to operate, and simple to extend.

---

## Extending the module

Add a new credential strategy in **four** small changes:

1. **Enum:** add the name to `Strategy`.
2. **Fields:** add any required config fields to `AuthConfig` (with env aliases).
3. **Validation:** update the `@model_validator` in `AuthConfig` to enforce required fields.
4. **Factory:** add a new `case` to `get_credential()` that constructs the appropriate `azure-identity` credential.

Because callers consume only `TokenCredential`, you won’t break downstream code.

---

## Error handling

* Misconfiguration raises a `pydantic.ValidationError` when instantiating `AuthConfig()` from env or in code.
* Construction-time failures (e.g., malformed certificate) are raised by `azure-identity` on first use.
* At runtime, `get_token()` may raise `CredentialUnavailableError` or `ClientAuthenticationError`; handle at call sites where appropriate.

---

## Security & operations

* Never log secrets. This module never prints/returns secret values.
* Prefer managed identity or client certificate in production.
* If you rotate secrets/certs, restart processes (or build a reloading layer in your service; this module intentionally keeps no background threads).

---

## Example Workflow

```python
from msftoolbox.azure.auth import get_credential, scopes
from azure.storage.blob import BlobServiceClient
from azure.keyvault.secrets import SecretClient

# Build once and reuse across clients
cred = get_credential()

# Blob Storage
blob = BlobServiceClient("https://example.blob.core.windows.net", credential=cred)

# Key Vault
secrets = SecretClient("https://example.vault.azure.net/", credential=cred)

# Microsoft Graph token (if needed for a custom call)
graph_token = cred.get_token(scopes.graph_scope()).token
```

---

If you spot gaps or need another strategy supported, open a PR that follows the **Extending the module** steps above.
