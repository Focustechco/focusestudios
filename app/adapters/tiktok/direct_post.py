import os
import time
import random
from typing import Dict, Any, Optional
import httpx
from app.adapters.tiktok.base import BaseTikTokAdapter
from app.config import settings


class TikTokDirectPostAdapter(BaseTikTokAdapter):
    """
    Adaptador oficial para a TikTok Content Posting API v2.
    Respeita timeouts, backoff com jitter, cabeçalho Retry-After e limites de taxa.
    """

    BASE_URL = "https://open.tiktokapis.com"
    AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
    TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    def _get_headers(self, access_token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8"
        }

    def _handle_backoff(self, attempt: int, response: Optional[httpx.Response] = None):
        """Aplica backoff exponencial com jitter e respeita Retry-After."""
        if response and response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                time.sleep(float(retry_after))
                return

        delay = min(60.0, (2 ** attempt) + random.uniform(0.5, 2.0))
        time.sleep(delay)

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Renova o access_token através do refresh_token oficial."""
        payload = {
            "client_key": settings.TIKTOK_CLIENT_KEY,
            "client_secret": settings.TIKTOK_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                self.TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=payload
            )
            data = resp.json()
            if resp.status_code != 200 or data.get("error", {}).get("code") != "ok":
                raise RuntimeError(f"Falha ao renovar token TikTok: {data}")
            return data.get("data", {})

    def query_creator_info(self, access_token: str) -> Dict[str, Any]:
        """Consulta as opções reais de privacidade e limites do criador."""
        url = f"{self.BASE_URL}/v2/post/publish/creator_info/query/"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=self._get_headers(access_token), json={})
            data = resp.json()
            if resp.status_code != 200 or data.get("error", {}).get("code") != "ok":
                raise RuntimeError(f"Erro ao consultar creator info: {data}")
            return data.get("data", {})

    def init_video_publish(
        self,
        access_token: str,
        post_info: Dict[str, Any],
        source_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Inicializa postagem direta e obtém publish_id e upload_url."""
        url = f"{self.BASE_URL}/v2/post/publish/video/init/"
        payload = {
            "post_info": post_info,
            "source_info": source_info
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=self._get_headers(access_token), json=payload)
            data = resp.json()
            if resp.status_code != 200 or data.get("error", {}).get("code") != "ok":
                raise RuntimeError(f"Erro ao inicializar postagem no TikTok: {data}")
            return data.get("data", {})

    def upload_video_binary(self, upload_url: str, file_path: str) -> bool:
        """Envia os bytes binários do arquivo para o upload_url fornecido pelo TikTok."""
        file_size = os.path.getsize(file_path)
        headers = {
            "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
            "Content-Type": "video/mp4"
        }
        with open(file_path, "rb") as f:
            content = f.read()

        with httpx.Client(timeout=120.0) as client:
            resp = client.put(upload_url, headers=headers, content=content)
            if resp.status_code not in (200, 201, 206):
                raise RuntimeError(f"Erro no upload de binário: status {resp.status_code} - {resp.text}")
        return True

    def fetch_publish_status(self, access_token: str, publish_id: str) -> Dict[str, Any]:
        """Consulta o status da publicação (taxa máx 30 req/min)."""
        url = f"{self.BASE_URL}/v2/post/publish/status/fetch/"
        payload = {"publish_id": publish_id}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=self._get_headers(access_token), json=payload)
            data = resp.json()
            if resp.status_code != 200 or data.get("error", {}).get("code") != "ok":
                raise RuntimeError(f"Erro ao consultar status no TikTok: {data}")
            return data.get("data", {})
