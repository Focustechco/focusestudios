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
