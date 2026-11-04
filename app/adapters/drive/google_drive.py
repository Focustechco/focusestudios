import os
import hashlib
import json
from typing import List, Optional, Tuple
import httpx
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

from app.adapters.drive.base import BaseDriveAdapter, DriveFileMetadata
from app.config import settings


class GoogleDriveAdapter(BaseDriveAdapter):
    """
    Adaptador oficial para Google Drive API v3.
    Suporta Contas de Serviço (Shared Drives) e OAuth de Usuário.
    Implementa paginação completa e download streaming autenticado com hash SHA-256.
    """

    def __init__(self):
        self.service = self._init_service()

    def _init_service(self):
        # 1. Tentar Conta de Serviço via JSON
        if settings.GOOGLE_SERVICE_ACCOUNT_JSON and os.path.exists(settings.GOOGLE_SERVICE_ACCOUNT_JSON):
            creds = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_SERVICE_ACCOUNT_JSON,
                scopes=["https://www.googleapis.com/auth/drive.readonly"]
            )
            return build("drive", "v3", credentials=creds)

        # 2. Tentar credentials inline se fornecido em string JSON
        if settings.GOOGLE_SERVICE_ACCOUNT_JSON and settings.GOOGLE_SERVICE_ACCOUNT_JSON.strip().startswith("{"):
            info = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
            creds = service_account.Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/drive.readonly"]
            )
            return build("drive", "v3", credentials=creds)

        # 3. Tentar OAuth 2.0 de Usuário via token.json (Bypass de política organizacional)
        token_path = "secrets/google_token.json"
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(
                token_path,
                scopes=["https://www.googleapis.com/auth/drive.readonly"]
            )
            return build("drive", "v3", credentials=creds)

        return None

    def list_files(
        self,
        folder_id: str,
        page_token: Optional[str] = None,
        include_subfolders: bool = False
    ) -> Tuple[List[DriveFileMetadata], Optional[str]]:
        if not self.service:
            raise RuntimeError(
                "Credenciais do Google Drive não configuradas. Use GOOGLE_SERVICE_ACCOUNT_JSON ou opere em modo DEMO."
            )

        query = f"'{folder_id}' in parents and trashed = false and mimeType != 'application/vnd.google-apps.folder' and mimeType contains 'video/'"

        request = self.service.files().list(
            q=query,
            pageSize=50,
            pageToken=page_token,
            fields="nextPageToken, files(id, name, mimeType, size, md5Checksum, modifiedTime)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            orderBy="createdTime asc"  # Política FIFO
        )
        response = request.execute()

        items = response.get("files", [])
        next_page = response.get("nextPageToken")

        results = []
        for file in items:
            results.append(
                DriveFileMetadata(
                    file_id=file["id"],
                    name=file["name"],
                    mime_type=file.get("mimeType", "video/mp4"),
                    size_bytes=int(file.get("size", 0)),
                    md5_checksum=file.get("md5Checksum"),
                    modified_time=file.get("modifiedTime")
                )
            )

        return results, next_page

    def download_file(self, file_id: str, target_path: str) -> str:
        if not self.service:
            raise RuntimeError("Credenciais do Google Drive não configuradas.")

        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        request = self.service.files().get_media(fileId=file_id, supportsAllDrives=True)

        sha256 = hashlib.sha256()
        with open(target_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request, chunksize=1024 * 1024 * 8)
            done = False
            while not done:
                status, done = downloader.next_chunk()

        # Calcula o SHA-256 do arquivo baixado
        with open(target_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)

        return sha256.hexdigest()
