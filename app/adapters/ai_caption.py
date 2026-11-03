from typing import Optional, Dict
from app.config import settings


class AICaptionAdapter:
    """
    Adaptador opcional de Inteligência Artificial para sugestão de legendas.
    Desativado por padrão (AI_CAPTION_ENABLED = False).
    Nunca inventa fatos sobre o conteúdo; se faltar contexto, indica revisão humana.
    """

    def __init__(self):
        self.enabled = settings.AI_CAPTION_ENABLED
        self.provider = settings.AI_PROVIDER

    def generate_caption(self, filename: str, metadata_notes: Optional[str] = None) -> Dict[str, str]:
        if not self.enabled:
            # Fallback direto: extrai título amigável do nome do arquivo
            clean_title = filename.replace("_", " ").replace("-", " ").replace(".mp4", "").title()
            return {
                "title": clean_title,
                "caption": f"Confira esta dica prática: {clean_title}. Siga a Focus Tech para mais atualizações!",
                "hashtags": "#focustech #produtividade #tecnologia #desenvolvimento",
                "notes": "Legenda gerada a partir dos metadados do arquivo (IA desativada por padrão)."
            }

        # Quando habilitada em modo mock / provider
        clean_title = filename.replace("_", " ").replace("-", " ").replace(".mp4", "").title()
        return {
            "title": clean_title,
            "caption": f"{clean_title} | Aplique este método para acelerar sua rotina técnica com máxima eficiência.",
            "hashtags": "#focustech #devtips #tecnologia #produtividade #coding",
            "notes": "Legenda sugerida pelo assistente de IA. Revise os fatos antes de consentir com a publicação."
        }
