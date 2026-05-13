from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

# Google Drive API scope (read-only access)
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Path to service account credentials
SERVICE_ACCOUNT_FILE = Path(__file__).resolve().parent.parent / "credentials" / "service-account.json"


def get_drive_service():
    """
    Authenticate using the service account and return a Google Drive API client.
    """
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
    )

    service = build("drive", "v3", credentials=credentials)
    return service


def search_files(query: str, page_size: int = 20):
    """
    Search Google Drive using a Google Drive query string.

    Example query:
        "name contains 'invoice'"

    Returns:
        List of file dictionaries containing:
        - id
        - name
        - mimeType
        - webViewLink
        - modifiedTime
    """
    service = get_drive_service()

    results = service.files().list(
        q=query,
        pageSize=page_size,
        fields="files(id, name, mimeType, webViewLink, modifiedTime)",
    ).execute()

    return results.get("files", [])