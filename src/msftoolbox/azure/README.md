# AzureKeyvaultClient

## Overview

`AzureKeyvaultClient` is a Python class designed to interact with the Azure KeyVault API. It provides methods for creating, reading, updating, and deleting KeyVault secrets and certificates.

## Features

- **Managing Secrets**: Fetch, upload, or delete secrets from a given keyvault url.
- **Managing Certificates**: Fetch, import, download, or delete keyvault certificates from a given keyvault url.

## Usage

### Initialization

The `AzureKeyvaultClient` class includes a `local_run` flag that can be set to `True` to enable interaction with Azure using a local credential; i.e. when set to `False` the client will be authenticated using the `managed_identity_client_id` instead.

By default, `local_run` is set to `True` so the only argument that needs to be provided is the `keyvault_url`.

```python
from msftoolbox.azure.azure_keyvault import AzureKeyvaultClient

client = AzureKeyvaultClient(
    keyvault_url="your-keyvault-url",
    local_run=True,
    managed_identity_client_id=None,
)
```

### Methods

#### Get Keyvault Secret

Fetch a secret value (str) from the KeyVault:

```python
secret = client.get_keyvault_secret_value(
    secret_name="super-secret"
    )
```

#### List Secrets

List of all secret names in KeyVault:

```python
secrets = client.list_secret_names()
```

#### Create or Update Secret

Create or update a secret in the KeyVault:

```python
kv_secret = client.set_keyvault_secret_value(
    secret_name="super-secret",
    secret_value="super-secret-value",
    )
```

This method returns a KeyVaultSecret object with attributes `kv_secret.name` and `kv_secret.value`.

#### Deleted Secrets

Delete a secret from the KeyVault:

```python
deleted_secret = client.delete_keyvault_secret(
    secret_name="super-secret"
    )
```

Returns secret properties/attributes. If soft-delete is enabled, returns information about its recovery as well.

List deleted secrets (only when vault has soft-delete enabled):

```python
deleted_secrets = client.list_deleted_keyvault_secrets()
```

Recover deleted secrets when soft-delete is enabled:

```python
kv_secret = client.recover_keyvault_secret(
    secret_name="deleted-super-secret"
    )
```

#### Get KeyVault Certificate

Get a certificate object from KeyVault:

```python
kv_certificate = client.get_keyvault_certificate(
    certificate_name="my-certificate"
    )
```

The KeyVault certificate object has properties like `id`, `name`, and `policy`.

#### List Certificate Names

Lists all certificates in KeyVault:

```python
certificate_names = client.list_certificate_names()
```

#### Save KeyVault Certificate to .pem

Saves a KeyVault certificate string to a local .pem file (will fail if string is in a different format):

```python
client.save_keyvault_certificate_to_pem(
    certificate_name="my-certificate",
    out_path="path/to/destination.pem",
    )
```

#### Import KeyVault Certificate

Import a certificate (CER, PFX, PEM) to the KeyVault:

```python
kv_certificate = client.import_keyvault_certificate_from_file(
    certificate_name="my-certificate",
    certificate_path="path/to/certificate.pem",
    # Optional key-word arguments
    password="secret-password",
    enabled=True,
    tags={"some-tag": "tag-value"},
)
```

#### Deleted Certificates

Delete a certificate in KeyVault:

```python
deleted_certificate = client.delete_keyvault_certificate(
    certificate_name="my-certificate",
)
```

List deleted certificates when soft-delete is enabled for the vault:

```python
deleted_certificates = client.list_deleted_keyvault_certificates()
```

Recover a deleted certificate when soft-delete is enabled:

```python
kv_certificate = client.recover_keyvault_certificate(
    certificate_name="my-deleted-certificate",
)
```

# AzureOpenAiClient

## Overview

`AzureOpenAiClient` is a Python class designed to interact with the Azure OpenAI API. It provides methods for generating chat completions, handling structured outputs using Pydantic models, and creating text embeddings.

## Features

- **Chat Completions**: Generate responses to user input using specified models.
- **Chat History**: Generate responses to user input while keeping the chat history as context for the prompt.
- **Structured Outputs**: Parse API responses into structured data using Pydantic models.
- **Embeddings Generation**: Convert text data into numerical embeddings for further analysis.

## Usage

### Initialization
The AzureOpenAiClient class includes a `keep_history` toggle that can be set to `True` to enable the retention of chat history. When enabled, the chat history is stored as a list of `Tuple[str, str]`, where each tuple contains a `(question, answer)` pair. This history is stored as an instance attribute named `chat_history`. Note that the `chat_history` attribute is specific to the instance of the class and will reset when the Python process ends or the instance is reinitialized.

By default, this toggle does not automatically include the stored history in prompts sent to the Azure OpenAI API. The inclusion of chat history in prompts is controlled by the `chat_completions` method explained below.

```python
from msftoolbox.azure.azure_open_ai import AzureOpenAiClient

client = AzureOpenAiClient(
    open_ai_key="your_api_key",
    base_endpoint="https://your_base_endpoint",
    api_version="2023-03-15-preview",
    keep_history=True # Defaults to False
)
```

### Methods
#### Chat Completions
Generate a response based on user input and system guidance.

```python
response = client.chat_completions(
    model="gpt-4o",
    system_content="The system's instructions for context",
    user_content="User's message",
    temperature=0.5,
    max_tokens=3000
)
```

#### Chat Completions with chat history
The `chat_completions` method generates a response based on the user's input, system guidance, and optionally the previous message(s) in the conversation history. The inclusion of chat history starts by setting the instance attribute `keep_chat_history` to `True` in the initialisation of the client. The inclusion of chat history in the prompt itself is controlled by the method arguments `add_history_to_prompt` and `history_depth`.

Including chat history in the prompt increases token usage, which directly impacts costs. You will be billed for:
- Tokens in the current prompt and response
- Tokens for the included chat history: Each question/answer pair added to the prompt contributes to the total token count. The number of pairs is controlled by `history_depth`.

Be mindful of these costs, particularly when using long histories or when generating responses with high token limits.

```python
response = client.chat_completions(
    model="gpt-4o",
    system_content="The system's instructions for context",
    user_content="User's message",
    add_history_to_prompt=True, 
    history_depth=1,
    temperature=0.5,
    max_tokens=3000
)
```

#### Structured Chat Completion
Send a chat completion request with structured output parsing using Pydantic models.
Refer to the documentation [here](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/structured-outputs?tabs=python-secure) for other options. Note that structured outputs was first introduced in API version 2024-08-01-preview.

```python

from typing import List
from pydantic import BaseModel, Field

class MessageClassification(BaseModel):
    region: str
    confidence: float = Field(description="Confidence in the location of the region (0-1)")

# Define user message and system instructions
message = "We are horrified by the recent bombing of Ahli Arab Hospital..."
system_message = "Classify each user message into one of the following regions: Middle East, Europe, North America, South America, Asia"

response = client.structured_chat_completion(
    model="gpt-4o-structured-outputs",
    user_content=message,
    system_content=system_message,
    response_format=MessageClassification
)

print(response.region)
print(response.confidence)
```

#### Create Embedding
Generate embeddings for a given text using a specified model.

```python

embeddings, total_tokens = client.create_embedding(
    data_to_vectorize="Sample text for embedding",
    embedding_model="text-embedding-ada-002"
)
```

## Example Workflow
Chat Completion: Generate a response for user input.
Structured Output: Parse the response into structured data.
Embeddings: Convert text into embeddings for analysis.

```python

# Initialize the client
client = AzureOpenAiClient(
    open_ai_key="your_api_key",
    base_endpoint="https://your_base_endpoint"
)

# Chat completion example
response = client.chat_completions(
    model="gpt-3.5-turbo",
    system_content="Provide a summary",
    user_content="Explain the significance of AI in modern technology.",
    temperature=0.7
)

# Structured output example
class MessageClassification(BaseModel):
    region: str
    confidence: float = Field(description="Confidence in the location of the region (0-1)")

message = "Peacefull protests were condudcted in Barcelona ..."
system_message = "Classify each user message into one of the following regions: Middle East, Europe, North America, South America, Asia"

structured_response = client.structured_chat_completion(
    model="gpt-4o-structured-outputs",
    user_content=message,
    system_content=system_message,
    response_format=MessageClassification
)

# Embedding example
embeddings, total_tokens = client.create_embedding(
    data_to_vectorize="Sample text for embedding"
)
```

This class provides a robust framework for interacting with Azure OpenAI services, enabling seamless integration of AI capabilities into your applications.

--------------------
# AzureStorageContainerClient

## Overview

`AzureStorageContainerClient` is a Python class designed to interact with Azure Blob Storage. It provides methods for downloading and uploading files, listing files in a container, and deleting blobs. The class supports multiple authentication mechanisms, including Azure CLI, Managed Identity, Default Azure Credentials, and storage account keys.

## Features

- **Multiple Authentication Options**: Authenticate using Azure CLI, Managed Identity, Default Azure Credentials, or a storage account key.
- **Blob Download**: Download blob files to local storage or directly to a stream.
- **Blob Upload**: Upload files from local storage to Azure Blob Storage.
- **List Files**: List all files in a specific folder within a container.
- **Delete Blobs**: Delete one or more blobs from the container.
- **DataFrame Conversion**: Convert CSV blob files to pandas DataFrames for data analysis.

## Usage

### Initialization

Initialize the `AzureStorageContainerClient` with the necessary credentials and parameters.

```python
from your_module import AzureStorageContainerClient

client = AzureStorageContainerClient(
    storage_account_url="https://<your_account_name>.blob.core.windows.net",
    container_name="your-container-name",
    local_run=True,  # Set to False if running in production
    managed_identity_client_id="your-managed-identity-client-id",  # Optional
    account_key="your-storage-account-key"  # Optional
)
```

### Methods

#### Download Blob to Stream

Download a blob file directly to a stream for further processing.

```python
stream = client.download_blob_file_to_stream(
    datalake_path="path/to/blob"
)
```

#### Download Blob to Local File

Download a blob file to a specified local path.

```python
client.download_blob_file(
    datalake_path="path/to/blob",
    destination_path="/local/path/to/save/file"
)
```

#### Upload File to Blob

Upload a local file to a specified path in Azure Blob Storage.

```python
client.upload_object_to_blob(
    temp_location="/local/path/to/file",
    datalake_destination="path/in/blob/storage"
)
```

#### List Files in Folder

List all files in a specific folder within the container.

```python
files = client.list_files_in_folder(
    folder_path="path/to/folder"
)
```

#### Download Blob to DataFrame

Convert a CSV blob file to a pandas DataFrame for data analysis.

```python
df = client.download_blob_file_to_dataframe(
    datalake_path="path/to/csv/blob"
)
```

#### Delete Files

Delete one or more blobs from the container.

```python
client.delete_files(
    file_paths=["path/to/blob1", "path/to/blob2"]
)
```

## Example Workflow

Download a CSV file, convert it to a DataFrame, and then upload a modified version back to Azure Blob Storage.

```python
# Initialize the client
client = AzureStorageContainerClient(
    storage_account_url="https://<your_account_name>.blob.core.windows.net",
    container_name="your-container-name",
    account_key="your-storage-account-key"
)

# Download CSV and convert to DataFrame
df = client.download_blob_file_to_dataframe(
    datalake_path="path/to/csv/blob"
)

# Perform data manipulation
df['new_column'] = df['existing_column'] * 2

# Save modified DataFrame to a local CSV
df.to_csv("/local/path/to/modified.csv", index=False)

# Upload modified CSV back to Azure Blob Storage
client.upload_object_to_blob(
    temp_location="/local/path/to/modified.csv",
    datalake_destination="path/to/modified/blob"
)
```

This class provides a comprehensive interface for managing Azure Blob Storage operations, enabling efficient data handling and storage management.
