import os
from fastapi.templating import Jinja2Templates

# Múltiplos caminhos de busca para garantir compatibilidade em qualquer ambiente (local, Docker, Vercel)
possible_dirs = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
    os.path.join(os.getcwd(), "app", "web", "templates"),
    os.path.join(os.getcwd(), "templates"),
    "/var/task/app/web/templates",
]

chosen_dir = next((d for d in possible_dirs if os.path.isdir(d)), possible_dirs[0])

templates = Jinja2Templates(directory=chosen_dir)

# ==========================================
# TRADUÇÕES DE STATUS & ETIQUETAS (PT-BR)
# ==========================================
STATUS_MAP = {
    # Status de Publicações, Mídias e Rascunhos
    "SCHEDULED": "AGENDADO",
    "PUBLISHED": "PUBLICADO",
    "APPROVED": "APROVADO",
    "DISCOVERED": "DESCOBERTO",
    "DRAFT": "RASCUNHO",
    "NEEDS_REVIEW": "EM REVISÃO",
    "VALIDATING": "VALIDANDO",
    "READY": "PRONTO",
    "FAILED": "FALHA",
    "CANCELLED": "CANCELADO",
    "PROCESSING": "PROCESSANDO",
    "UPLOADING": "ENVIANDO",
    "PENDING": "PENDENTE",
    "REJECTED": "REJEITADO",
    "ACTIVE": "ATIVO",
    "INACTIVE": "INATIVO",
    "ERROR": "ERRO",
    "SUCCESS": "SUCESSO",
    # Modos de operação
    "DEMO": "DEMONSTRAÇÃO",
    "DIRECT_POST": "PUBLICAÇÃO DIRETA",
    "MANUAL_STUDIO": "TIKTOK STUDIO",
    "UPLOAD": "UPLOAD DIRETO",
    "HYBRID": "HÍBRIDO",
}

PRIVACY_MAP = {
    "PUBLIC_TO_EVERYONE": "PÚBLICO",
    "MUTUAL_FOLLOW_FRIENDS": "AMIGOS MÚTUOS",
    "FOLLOWER_OF_CREATOR": "SEGUIDORES",
    "SELF_ONLY": "SOMENTE EU",
    "PUBLIC": "PÚBLICO",
    "PRIVATE": "PRIVADO",
    "FRIENDS": "AMIGOS",
}

def status_pt(val):
    if not val:
        return ""
    return STATUS_MAP.get(str(val).upper(), str(val))

def privacy_pt(val):
    if not val:
        return ""
    return PRIVACY_MAP.get(str(val).upper(), str(val))

templates.env.filters["status_pt"] = status_pt
templates.env.filters["privacy_pt"] = privacy_pt
templates.env.globals["STATUS_MAP"] = STATUS_MAP
templates.env.globals["PRIVACY_MAP"] = PRIVACY_MAP

