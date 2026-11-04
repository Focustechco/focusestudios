# Guia de Implantação em Produção (VPS com Docker Compose)

## 1. Dimensionamento de Servidor (Hardware & Recursos)

Estimativas considerando o processamento de vídeos diários (10 publicações/dia, arquivos MP4 de 50MB a 500MB):

* **CPU:** Mínimo 2 vCPUs (Recomendado: 4 vCPUs se houver inspeção e extração de thumbnails concorrentes com ffmpeg).
* **Memória RAM:** Mínimo 4 GB (Recomendado: 8 GB para PostgreSQL, Redis, Celery workers e buffer de download streaming).
* **Armazenamento:** Mínimo 50 GB SSD NVMe (Considerando 30 dias de arquivos em staging local antes da limpeza de retenção).
* **Rede:** Mínimo 100 Mbps uplink para streaming de upload ao TikTok.

---

## 2. Serviços e Arquitetura Docker Compose

O stack de produção é composto por:
1. **`web`**: Servidor FastAPI (painel, webhook, OAuth callbacks) rodando via Uvicorn por trás de proxy reverso.
2. **`worker`**: Celery Worker responsável por sincronização com Drive, inspeção técnica ffprobe, uploads ao TikTok e reconciliação.
3. **`beat`**: Celery Beat (única instância dedicada ao agendador).
4. **`postgres`**: Banco relacional PostgreSQL 16 com volume persistente para dados e migrações Alembic.
5. **`redis`**: Broker de mensagens e cache.
6. **`caddy` ou `nginx`**: Proxy reverso HTTPS automático com certificado Let's Encrypt para os domínios de OAuth.

---

## 3. Segurança e Gerenciamento de Segredos

* As credenciais sensíveis (OAuth Client Secrets, Tokens de Usuário) são **criptografadas em repouso no PostgreSQL** utilizando o algoritmo simétrico Fernet (AES-128-CBC + HMAC-SHA256) com a chave configurada em `TOKEN_ENCRYPTION_KEY`.
* Todas as variáveis de ambiente devem ser fornecidas via arquivo `.env` (com permissões `chmod 600 .env`) ou gestor de segredos da VPS (Docker Swarm Secrets, HashiCorp Vault ou AWS SSM).
* **Nenhum segredo ou token deve ser gravado em logs.** O formatador estruturado de logs sanitiza chaves como `access_token`, `refresh_token`, `client_secret` e `password`.

---

## 4. Política de Retenção e Limpeza de Arquivos Temporários

* Arquivos baixados do Google Drive são armazenados temporariamente em `/tmp/focus_publisher/media`.
* Uma tarefa agendada do Celery (`cleanup_temporary_media`) remove arquivos de mídias já publicadas ou em quarentena com mais de 7 dias, liberando espaço em disco automaticamente.
* A saúde do disco é monitorada e exibida no dashboard administrativo.

---

## 5. Rotina de Backup e Restauração do PostgreSQL

### Backup Diário Automatizado:
```bash
docker compose exec -T postgres pg_dump -U focus -d focus_publisher | gzip > /backups/focus_db_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Procedimento de Restauração:
```bash
gunzip < /backups/focus_db_20261103_120000.sql.gz | docker compose exec -T postgres psql -U focus -d focus_publisher
```
