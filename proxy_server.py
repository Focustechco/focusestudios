import os
import sys
import ssl
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from datetime import datetime, timedelta
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [PROXY] %(message)s")
logger = logging.getLogger("focus_proxy")

BACKEND_URL = os.environ.get("PROXY_BACKEND_URL", "http://127.0.0.1:8000")
PROXY_PORT = int(os.environ.get("PROXY_PORT", "8080"))
PROXY_HOST = os.environ.get("PROXY_HOST", "0.0.0.0")
ENABLE_SSL = os.environ.get("PROXY_ENABLE_SSL", "false").lower() == "true"
SSL_CERT_PATH = os.environ.get("PROXY_SSL_CERT", "storage/proxy_cert.pem")
SSL_KEY_PATH = os.environ.get("PROXY_SSL_KEY", "storage/proxy_key.pem")

# Pool de conexões HTTPX de alta performance sem seguir redirecionamentos (preserva 302/303)
http_client = httpx.Client(follow_redirects=False, timeout=60.0)


def generate_self_signed_cert(cert_path: str, key_path: str):
    """Gera certificado SSL autoassinado para testes locais HTTPS com OAuth."""
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    import ipaddress

    os.makedirs(os.path.dirname(cert_path), exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Focus Tech"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(u"localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))
            ]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    logger.info(f"Certificado SSL autoassinado gerado em: {cert_path}")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Servidor multithread para evitar bloqueios concorrentes."""
    daemon_threads = True


class ReverseProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_proxy(self):
        # 1. Healthcheck nativo do proxy
        if self.path == "/proxy-health":
            resp_data = json.dumps({
                "status": "ok",
                "proxy": "Focus Reverse Proxy",
                "backend_url": BACKEND_URL,
                "ssl_enabled": ENABLE_SSL,
                "timestamp": datetime.utcnow().isoformat()
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(resp_data)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(resp_data)
            self.close_connection = True
            return

        target_url = f"{BACKEND_URL.rstrip('/')}{self.path}"
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        # Repassa cabeçalhos do cliente com cabeçalhos de proxy reverso
        req_headers = {}
        for k, v in self.headers.items():
            if k.lower() not in ("host", "content-length", "connection"):
                req_headers[k] = v

        client_ip = self.client_address[0]
        req_headers["X-Forwarded-For"] = client_ip
        req_headers["X-Forwarded-Proto"] = "https" if ENABLE_SSL else "http"
        req_headers["X-Forwarded-Host"] = self.headers.get("Host", "localhost")
        req_headers["X-Real-IP"] = client_ip

        try:
            resp = http_client.request(
                method=self.command,
                url=target_url,
                headers=req_headers,
                content=body
            )

            self.send_response(resp.status_code)
            for h_name, h_val in resp.headers.items():
                if h_name.lower() not in ("transfer-encoding", "content-encoding", "content-length", "connection"):
                    self.send_header(h_name, h_val)

            self.send_header("Content-Length", str(len(resp.content)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(resp.content)
            self.close_connection = True

        except httpx.ConnectError:
            err_msg = json.dumps({
                "error": "Bad Gateway - Backend Inacessivel",
                "detail": f"Nao foi possivel conectar ao servidor FastAPI em {BACKEND_URL}. Certifique-se de que ele esteja rodando (ex: python run_with_proxy.py)."
            }, indent=2).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(err_msg)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(err_msg)
            self.close_connection = True

        except Exception as ex:
            logger.error(f"Erro no encaminhamento do proxy para {target_url}: {str(ex)}")
            err_msg = json.dumps({
                "error": "Proxy Error",
                "detail": str(ex)
            }).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(err_msg)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(err_msg)
            self.close_connection = True

    def do_GET(self):
        self.do_proxy()

    def do_POST(self):
        self.do_proxy()

    def do_PUT(self):
        self.do_proxy()

    def do_DELETE(self):
        self.do_proxy()

    def do_HEAD(self):
        self.do_proxy()

    def log_message(self, format, *args):
        logger.info(f"{self.client_address[0]} - {self.command} {self.path} - {args[1] if len(args) > 1 else ''}")


def run_proxy(port: int = PROXY_PORT, host: str = PROXY_HOST, enable_ssl: bool = ENABLE_SSL):
    server = ThreadedHTTPServer((host, port), ReverseProxyHandler)
    proto = "http"

    if enable_ssl:
        if not (os.path.exists(SSL_CERT_PATH) and os.path.exists(SSL_KEY_PATH)):
            generate_self_signed_cert(SSL_CERT_PATH, SSL_KEY_PATH)

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=SSL_CERT_PATH, keyfile=SSL_KEY_PATH)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        proto = "https"

    print("=" * 70)
    print("  FOCUS PUBLISHER - SERVIDOR PROXY REVERSO ATIVO")
    print(f"  Ouvindo em: {proto}://{host if host != '0.0.0.0' else '127.0.0.1'}:{port}")
    print(f"  Encaminhando para: {BACKEND_URL}")
    print(f"  SSL Ativo: {'Sim' if enable_ssl else 'Não (HTTP)'}")
    print("=" * 70)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Servidor proxy encerrado pelo operador.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_proxy()
