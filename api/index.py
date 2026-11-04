import os
import sys

# Garante a inclusão do diretório raiz no sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.web.app import app

__all__ = ["app"]
