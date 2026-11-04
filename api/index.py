import os
import sys
import traceback

# Garante inclusão da raiz do projeto no sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from app.web.app import app
except Exception as e:
    print(f"[FATAL VERCEL IMPORT ERROR]: {e}")
    traceback.print_exc()
    raise

__all__ = ["app"]
