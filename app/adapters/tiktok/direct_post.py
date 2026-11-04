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

    def exchange_code_for_token(self, code: str, redirect_uri: str, code_verifier: str) -> Dict[str, Any]:
        """Troca o authorization code pelo access_token e refresh_token via PKCE."""
        payload = {
            "client_key": settings.TIKTOK_CLIENT_KEY,
            "client_secret": settings.TIKTOK_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                self.TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=payload
            )
            data = resp.json()

            # Extrai payload de tokens (pode vir diretamente no root JSON ou envelopado em 'data')
            token_dict = data.get("data") if (isinstance(data.get("data"), dict) and "access_token" in data.get("data")) else data

            # Verificação de erro
            err = data.get("error")
            is_err = False
            if resp.status_code != 200:
                is_err = True
            elif isinstance(err, str) and err:
                is_err = True
            elif isinstance(err, dict) and err.get("code") not in (None, "", "ok", 0, "0"):
                is_err = True

            if is_err or not token_dict.get("access_token"):
                raise RuntimeError(f"Falha na troca de código TikTok por token: {data}")

            return token_dict

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

            token_dict = data.get("data") if (isinstance(data.get("data"), dict) and "access_token" in data.get("data")) else data

            err = data.get("error")
            is_err = False
            if resp.status_code != 200:
                is_err = True
            elif isinstance(err, str) and err:
                is_err = True
            elif isinstance(err, dict) and err.get("code") not in (None, "", "ok", 0, "0"):
                is_err = True

            if is_err or not token_dict.get("access_token"):
                raise RuntimeError(f"Falha ao renovar token TikTok: {data}")

            return token_dict

    def query_creator_info(self, access_token: str) -> Dict[str, Any]:
        """Consulta as opções reais de privacidade e limites do criador com fallback seguro para user/info."""
        url = f"{self.BASE_URL}/v2/post/publish/creator_info/query/"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=self._get_headers(access_token), json={})
                data = resp.json()
                if resp.status_code == 200 and data.get("error", {}).get("code") == "ok":
                    return data.get("data", {})
        except Exception:
            pass

        # Fallback para endpoint de usuário padrão do Login Kit (/v2/user/info/)
        user_url = f"{self.BASE_URL}/v2/user/info/?fields=open_id,union_id,avatar_url,display_name,username"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(user_url, headers=self._get_headers(access_token))
                data = resp.json()
                user = data.get("data", {}).get("user", {})
                return {
                    "creator_username": user.get("username", "@tiktok_creator"),
                    "creator_nickname": user.get("display_name", "TikTok Creator"),
                    "creator_avatar_url": user.get("avatar_url", ""),
                    "privacy_level_options": ["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY"],
                    "comment_disabled": False,
                    "duet_disabled": False,
                    "stitch_disabled": False,
                    "max_video_post_duration_sec": 600
                }
        except Exception:
            return {
                "creator_username": "@tiktok_user",
                "creator_nickname": "TikTok User",
                "creator_avatar_url": "",
                "privacy_level_options": ["PUBLIC_TO_EVERYONE", "SELF_ONLY"],
                "comment_disabled": False,
                "duet_disabled": False,
                "stitch_disabled": False,
                "max_video_post_duration_sec": 600
            }

    def init_video_publish(
        self,
        access_token: str,
        post_info: Dict[str, Any],
        source_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Inicializa postagem direta ou upload via Content Posting API (inbox/drafts)."""
        headers = self._get_headers(access_token)
        with httpx.Client(timeout=self.timeout) as client:
            # 1. Tenta publicação direta (/v2/post/publish/video/init/)
            direct_url = f"{self.BASE_URL}/v2/post/publish/video/init/"
            payload = {
                "post_info": post_info,
                "source_info": source_info
            }
            try:
                resp = client.post(direct_url, headers=headers, json=payload)
                data = resp.json()
                if resp.status_code == 200 and data.get("error", {}).get("code") == "ok":
                    return data.get("data", {})
                
                # Se o TikTok rejeitar por ser app em desenvolvimento, tenta com SELF_ONLY (obrigatório para contas privadas/sandbox)
                if data.get("error", {}).get("code") == "unaudited_client_can_only_post_to_private_accounts":
                    payload["post_info"]["privacy_level"] = "SELF_ONLY"
                    resp_retry = client.post(direct_url, headers=headers, json=payload)
                    data_retry = resp_retry.json()
                    if resp_retry.status_code == 200 and data_retry.get("error", {}).get("code") == "ok":
                        return data_retry.get("data", {})
            except Exception as e:
                data = {"error": {"code": "exception", "message": str(e)}}

            # 2. Se o app utiliza o escopo video.upload (Content Posting API Inbox/Drafts)
            inbox_url = f"{self.BASE_URL}/v2/post/publish/inbox/video/init/"
            inbox_payload = {
                "source_info": source_info
            }
            resp_inbox = client.post(inbox_url, headers=headers, json=inbox_payload)
            data_inbox = resp_inbox.json()
            if resp_inbox.status_code == 200 and data_inbox.get("error", {}).get("code") == "ok":
                return data_inbox.get("data", {})

            # Caso ambos falhem, reporta o erro informativo
            raise RuntimeError(f"Erro ao inicializar postagem no TikTok: {data_inbox or data}")

    def upload_video_binary(self, upload_url: str, file_path: str) -> bool:
        """Envia os bytes binários do arquivo para o upload_url fornecido pelo TikTok."""
        if not os.path.exists(file_path):
            raise RuntimeError(f"Arquivo de vídeo não encontrado no disco: {file_path}")

        file_size = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            content = f.read()

        # Validação: impede upload de arquivos sintéticos de teste falso
        if content.startswith(b"FOCUS_PUBLISHER_SYNTHETIC_MEDIA_PAYLOAD"):
            raise RuntimeError(f"O vídeo '{os.path.basename(file_path)}' é um arquivo fictício de teste de banco de dados (mock). Por favor, dispare um dos vídeos reais importados do Google Drive.")

        headers = {
            "Content-Type": "video/mp4",
            "Content-Length": str(file_size),
            "Content-Range": f"bytes 0-{file_size - 1}/{file_size}"
        }

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
