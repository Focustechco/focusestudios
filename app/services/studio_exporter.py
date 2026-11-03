import csv
import io
import os
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.scheduled_post import ScheduledPost
from app.core.timezone import to_fortaleza, format_fortaleza
from app.config import settings


class StudioExporter:
    """
    Exportador de Pacote para TikTok Studio (Modo MANUAL_STUDIO).
    Gera manifesto CSV e auxilia o operador humano no agendamento manual,
    deixando inequívoco que a TikTok API não possui endpoint para a fila do Studio.
    """

    def __init__(self, db: Session):
        self.db = db

    def generate_manifest_csv(self, post_ids: Optional[List[str]] = None) -> str:
        query = self.db.query(ScheduledPost).order_by(ScheduledPost.scheduled_time_utc.asc())
        if post_ids:
            query = query.filter(ScheduledPost.id.in_(post_ids))
        else:
            query = query.filter(ScheduledPost.status.in_(["SCHEDULED", "APPROVED", "READY"]))

        posts = query.all()

        output = io.StringIO()
        writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        
        # Cabeçalho do manifesto
        writer.writerow([
            "ID_Agendamento",
            "Nome_Arquivo_Video",
            "Data_Hora_Fortaleza",
            "Titulo_Legenda_Completa",
            "Privacidade_Recomendada",
            "Comentarios_Ativos",
            "Dueto_Ativo",
            "Costura_Ativa",
            "Declaracao_IA_AIGC",
            "Status_Focus_Publisher"
        ])

        for post in posts:
            draft = post.post_draft
            media = draft.media_asset if draft else None
            local_dt_str = format_fortaleza(post.scheduled_time_utc)
            full_caption = f"{draft.title}\n\n{draft.caption}\n\n{draft.hashtags}".strip() if draft else ""

            writer.writerow([
                post.id,
                media.name if media else "video.mp4",
                local_dt_str,
                full_caption,
                draft.privacy_level if draft else "SELF_ONLY",
                "Sim" if draft and not draft.disable_comment else "Nao",
                "Sim" if draft and not draft.disable_duet else "Nao",
                "Sim" if draft and not draft.disable_stitch else "Nao",
                "Sim" if draft and draft.is_aigc else "Nao",
                "Aguardando agendamento manual no TikTok Studio"
            ])

        return output.getvalue()

    def get_manual_studio_items(self) -> List[Dict[str, Any]]:
        posts = self.db.query(ScheduledPost).filter(
            ScheduledPost.status.in_(["SCHEDULED", "APPROVED", "READY"])
        ).order_by(ScheduledPost.scheduled_time_utc.asc()).all()

        items = []
        for p in posts:
            draft = p.post_draft
            media = draft.media_asset if draft else None
            full_caption = f"{draft.title} {draft.caption} {draft.hashtags}".strip() if draft else ""
            items.append({
                "scheduled_post_id": p.id,
                "video_name": media.name if media else "video.mp4",
                "file_path": media.local_storage_path if media else "",
                "time_fortaleza": format_fortaleza(p.scheduled_time_utc),
                "full_caption": full_caption,
                "privacy_level": draft.privacy_level if draft else "SELF_ONLY",
                "status_label": "Aguardando agendamento manual no TikTok Studio"
            })
        return items
