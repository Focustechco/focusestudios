from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseTikTokAdapter(ABC):
    @abstractmethod
    def query_creator_info(self, access_token: str) -> Dict[str, Any]:
        """Consulta as opções permitidas de privacidade e limites do criador."""
        pass

    @abstractmethod
    def init_video_publish(
        self,
        access_token: str,
        post_info: Dict[str, Any],
        source_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Inicializa a publicação via Direct Post e obtém publish_id e upload_url."""
        pass

    @abstractmethod
    def upload_video_binary(self, upload_url: str, file_path: str) -> bool:
        """Envia os bytes binários do arquivo para o upload_url fornecido pelo TikTok."""
        pass

    @abstractmethod
    def fetch_publish_status(self, access_token: str, publish_id: str) -> Dict[str, Any]:
        """Consulta o status da publicação na TikTok Content Posting API."""
        pass
