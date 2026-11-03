import uvicorn
import os
import sys

# Garante que o diretório raiz esteja no path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.config import settings

if __name__ == "__main__":
    print("=" * 70)
    print("  FOCUS PUBLISHER - Agente TikTok & Google Drive")
    print(f"  Modo de Operação: {settings.OPERATION_MODE}")
    print(f"  Fuso Horário: {settings.TIMEZONE}")
    print(f"  Painel Administrativo: http://localhost:8000")
    print("=" * 70)
    uvicorn.run("app.web.app:app", host="0.0.0.0", port=8000, reload=True)
