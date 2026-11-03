from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple


class DriveFileMetadata:
    def __init__(
        self,
        file_id: str,
        name: str,
        mime_type: str,
        size_bytes: int,
        md5_checksum: Optional[str] = None,
        modified_time: Optional[str] = None
    ):
        self.file_id = file_id
        self.name = name
        self.mime_type = mime_type
        self.size_bytes = size_bytes
        self.md5_checksum = md5_checksum
        self.modified_time = modified_time


class BaseDriveAdapter(ABC):
    @abstractmethod
    def list_files(
        self,
        folder_id: str,
        page_token: Optional[str] = None,
        include_subfolders: bool = False
    ) -> Tuple[List[DriveFileMetadata], Optional[str]]:
        """Lista arquivos de vídeo da pasta designada com paginação."""
        pass

    @abstractmethod
    def download_file(self, file_id: str, target_path: str) -> str:
        """Faz o download autenticado em streaming e calcula o SHA-256."""
        pass
