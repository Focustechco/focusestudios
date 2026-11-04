import os
from fastapi.templating import Jinja2Templates

# Garante path absoluto robusto para execução local, Docker ou serverless (Vercel)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

if not os.path.isdir(TEMPLATES_DIR):
    # Fallback para execução a partir do diretório raiz
    TEMPLATES_DIR = os.path.join(os.getcwd(), "app", "web", "templates")

templates = Jinja2Templates(directory=TEMPLATES_DIR)
