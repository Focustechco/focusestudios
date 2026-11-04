import os
import sys

# Garante path raiz
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.web.app import app

# Export explícito para plataformas de deploy (Vercel, Railway, Render, etc.)
__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
