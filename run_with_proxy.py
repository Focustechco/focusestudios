import os
import sys
import time
import threading
import uvicorn
import httpx

# Garante path raiz
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.config import settings
from proxy_server import run_proxy


def start_uvicorn_backend():
    """Inicia o servidor FastAPI na porta 8000."""
    uvicorn.run("app.web.app:app", host="127.0.0.1", port=8000, log_level="warning")


def wait_for_backend(url: str = "http://127.0.0.1:8000/healthz", timeout_seconds: int = 15):
    """Aguarda até que o backend FastAPI esteja respondendo com sucesso."""
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        try:
            resp = httpx.get(url, timeout=1.0)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


if __name__ == "__main__":
    print("=" * 70)
    print("  FOCUS PUBLISHER - INICIALIZANDO BACKEND E PROXY REVERSO")
    print(f"  Modo de Operação: {settings.OPERATION_MODE}")
    print(f"  Fuso Horário: {settings.TIMEZONE}")
    print("=" * 70)

    # 1. Inicia backend FastAPI em thread daemon
    print("[1/3] Iniciando backend FastAPI em 127.0.0.1:8000...")
    backend_thread = threading.Thread(target=start_uvicorn_backend, daemon=True)
    backend_thread.start()

    # 2. Aguarda prontidão do backend
    print("[2/3] Aguardando prontidão da API...")
    if not wait_for_backend():
        print("[ERRO] O backend FastAPI não respondeu no tempo limite. Encerrando.")
        sys.exit(1)
    print("  -> Backend FastAPI ONLINE e respondendo em http://127.0.0.1:8000/healthz")

    # 3. Inicia servidor proxy reverso
    proxy_port = int(os.environ.get("PROXY_PORT", "8080"))
    ssl_enabled = os.environ.get("PROXY_ENABLE_SSL", "false").lower() == "true"
    proto = "https" if ssl_enabled else "http"

    print(f"[3/3] Iniciando servidor proxy reverso em {proto}://127.0.0.1:{proxy_port}...")
    print("=" * 70)
    print("  TUDO PRONTO! ACESSE O PAINEL FOCUS PUBLISHER PELO PROXY:")
    print(f"  --> {proto}://localhost:{proxy_port}")
    print("=" * 70)

    try:
        run_proxy(port=proxy_port, enable_ssl=ssl_enabled)
    except KeyboardInterrupt:
        print("\nServiços encerrados com sucesso.")
