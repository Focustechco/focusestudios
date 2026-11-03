import uuid
import time
from typing import Dict, Any
from app.adapters.tiktok.base import BaseTikTokAdapter


class MockTikTokAdapter(BaseTikTokAdapter):
    """
    Adaptador simulador para o modo DEMO.
    Simula perfeitamente as respostas da TikTok Content Posting API v2,
    permitindo validar todo o ciclo de vida sem risco de publicações reais.
    """

    def __init__(self):
        # Armazena estado simulado de publicações em memória
        self._mock_posts = {}

    def query_creator_info(self, access_token: str) -> Dict[str, Any]:
        """Retorna opções de criador realistas para preenchimento de telas dinâmicas."""
        return {
            "creator_avatar_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=150",
            "creator_nickname": "Focus Tech Oficial (DEMO)",
            "creator_username": "@focustech_demo",
            "privacy_level_options": [
                "PUBLIC_TO_EVERYONE",
                "MUTUAL_FOLLOW_FRIENDS",
                "FOLLOWER_OF_CREATOR",
                "SELF_ONLY"
            ],
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
        publish_id = f"v_pub_file~v2.demo_{uuid.uuid4().hex[:12]}"
        upload_url = f"https://mock-upload.tiktokapis.com/video/?upload_id={uuid.uuid4().hex}"
        
        self._mock_posts[publish_id] = {
            "created_at": time.time(),
            "status": "PROCESSING_UPLOAD",
            "post_info": post_info,
            "checks_count": 0
        }

        return {
            "publish_id": publish_id,
            "upload_url": upload_url
        }

    def upload_video_binary(self, upload_url: str, file_path: str) -> bool:
        # No modo DEMO, simula a transferência de bytes sem enviar nada para fora
        return True

    def fetch_publish_status(self, access_token: str, publish_id: str) -> Dict[str, Any]:
        if publish_id not in self._mock_posts:
            # Se for ID desconhecido
            return {
                "status": "PUBLISH_COMPLETE",
                "fail_reason": "",
                "publicaly_available_post_id": [f"74321098{uuid.uuid4().hex[:8]}"]
            }

        post = self._mock_posts[publish_id]
        post["checks_count"] += 1

        # Simula ciclo de vida: 1ª verificação -> PROCESSING, 2ª -> SEND_TO_AUDIT, 3ª -> PUBLISH_COMPLETE
        if post["checks_count"] == 1:
            status = "PROCESSING_DOWNLOAD"
        elif post["checks_count"] == 2:
            status = "SEND_TO_AUDIT"
        else:
            status = "PUBLISH_COMPLETE"
            post["status"] = "PUBLISH_COMPLETE"

        return {
            "status": status,
            "fail_reason": "",
            "publicaly_available_post_id": ["7432109876543210987"] if status == "PUBLISH_COMPLETE" else []
        }
