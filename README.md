# Focus Publisher

> Agente e Esteira de Preparação e Publicação no TikTok a partir do Google Drive  
> **Identidade:** Focus Tech (Preto & Laranja) | **Fuso Oficial:** America/Fortaleza  
> **Status:** MVP Funcional Completo | **Modo Padrão:** DEMO  

---

## 1. Visão Geral

O **Focus Publisher** é uma solução de engenharia de software desenvolvida para automatizar com segurança e conformidade a ingestão de vídeos finalizados de uma pasta do Google Drive, inspeção técnica via `ffprobe`, enriquecimento e consentimento de legendas e distribuição programada no TikTok com uma meta de **10 publicações diárias**.

O sistema opera sob o fuso horário **`America/Fortaleza`** (UTC-3), persistindo os horários no banco em UTC e exibindo todas as datas e horários ajustados para o operador.

### Identidade Visual Focus Tech
* **Fundo:** Dark Obsidian (`#0a0b0d`, `#13151a`)
* **Destaques:** Laranja Focus (`#ff6600`, `#ff7d1a`)
* **Interface:** Limpa, orientada a dados operacionais, com feedback em tempo real via HTMX.

---

## 2. A Realidade sobre a "Fila do TikTok Studio"

> [!WARNING]
> **RESTRIÇÃO FUNDAMENTAL DE API:**  
> A TikTok Content Posting API oficial **NÃO possui endpoint público para programar publicações dentro da tela do TikTok Studio Web**.  
> Qualquer ferramenta que prometa injetar posts na fila nativa do Studio por API oficial está inventando especificações inexistentes.

O Focus Publisher soluciona essa exigência com dois caminhos complementares:
1. **Calendário Interno com Publicação Direta (`DIRECT_POST`):**  
   O PostgreSQL é a fonte da verdade do calendário. O Celery Beat avalia a fila a cada minuto e o Celery Worker realiza a chamada da API do TikTok no minuto exato programado.
2. **Pacote de Agendamento Manual no Studio (`MANUAL_STUDIO`):**  
   Para criadores que precisam visualizar o conteúdo agendado na tela web do Studio, o sistema gera:
   * **Manifesto CSV oficial** com o nome do arquivo, legenda completa, hashtags, horário em `America/Fortaleza` e configurações de privacidade.
   * Tela de conferência com botão de **cópia de legenda em 1 clique**.
   * Status inequívoco no painel: *"Aguardando agendamento manual no TikTok Studio"*.

---

## 3. Arquitetura Modular

Construído como um monólito modular em **Python 3.12**:

* **Web (FastAPI + Jinja2 + HTMX):** Painel administrativo, rotas de OAuth, aprovação de consentimento e download de manifestos.
* **Worker (Celery + Redis):** Sincronização com o Drive, inspeção com `ffprobe`, upload para o TikTok e reconciliação.
* **Beat (Celery Beat):** Instância única de agendador periódico (disparo a cada 60s, sincronização a cada 15m).
* **Persistência (PostgreSQL 16 + Alembic):** Fonte da verdade para estados, integridade transacional e locks concorrentes.
* **Segurança de Segredos:** Tokens OAuth criptografados em repouso no banco usando cifra simétrica **Fernet (AES-128-CBC + HMAC-SHA256)**.
* **Deduplicação & Consentimento:** Detecção de duplicatas por **SHA-256** e hash de consentimento individual inviolável.

```
 intelligent-borg/
 ├── app/
 │   ├── adapters/          # Adaptadores Google Drive e TikTok (Mock e Oficial)
 │   ├── core/              # Cifra Fernet, Fusos (America/Fortaleza) e Máquina de Estados
 │   ├── models/            # Modelos relacionais SQLAlchemy
 │   ├── services/          # Sincronização, Inspeção, Calendário, Aprovação e Publicador
 │   ├── tasks/             # Tarefas assíncronas Celery e agendamento Beat
 │   └── web/               # FastAPI, rotas, templates e estilização Focus Tech
 ├── alembic/               # Migrações versionadas de banco de dados
 ├── docs/                  # Guias de API, arquitetura, elegibilidade e produção
 ├── tests/                 # Suíte com 13 testes automatizados essenciais
 ├── docker-compose.yml     # Orquestração de web, worker, beat, postgres e redis
 ├── Dockerfile             # Imagem oficial Python 3.12 com ffmpeg e ffprobe
 └── run_local_demo.py      # Executador local imediato em modo DEMO
```

---

## 4. Modos de Operação

| Modo | Comportamento |
| :--- | :--- |
| **`DEMO`** (Padrão) | Utiliza adaptadores simulados, mock da pasta do Drive com 15 vídeos de exemplo e simulador de resposta da TikTok API. **Nunca faz publicações reais.** |
| **`DIRECT_POST`** | Publicação direta via API oficial v2. Exige credenciais aprovadas pela ByteDance, OAuth com escopo `video.publish` e conta elegível. |
| **`MANUAL_STUDIO`** | Prepara o pacote com vídeos e manifesto CSV para que o operador faça a programação no TikTok Studio Web. |
| **`UPLOAD`** | Envia o vídeo para a caixa de entrada do criador (`Creator Inbox`) para finalização manual no app mobile. |

---

## 5. Como Executar

### 5.1 Execução Local Imediata (Modo DEMO)
Com Python 3.12 instalado:

```bash
# 1. Ativar o ambiente virtual
.venv\Scripts\activate   # No Windows
# source .venv/bin/activate # No Linux/Mac

# 2. Executar migrações do banco de dados
alembic upgrade head

# 3. Iniciar o painel Focus Publisher
python run_local_demo.py
```
Acesse no seu navegador: **`http://localhost:8000`**

### 5.2 Execução em Produção via Docker Compose

```bash
# 1. Criar arquivo de configuração a partir do modelo
cp .env.example .env

# 2. Subir todos os serviços (web, worker, beat, postgres, redis)
docker compose up --build -d

# 3. Acompanhar os logs
docker compose logs -f web worker
```

---

## 6. Calendário Interno (Meta de 10 Posts/Dia)

A meta diária padrão é de **10 publicações por dia** nos horários (America/Fortaleza):
* `08:00`, `09:30`, `11:00`, `12:30`, `14:00`, `15:30`, `17:00`, `18:30`, `20:00`, `21:30`.

### Regras do Calendário:
1. **Nunca repete vídeos já publicados** para preencher metas.
2. Se o estoque de vídeos aprovados for menor que 10, o sistema **exibe o déficit explicitamente no dashboard**.
3. **Proteção pós-indisponibilidade:** Se o servidor ficar desligado por horas, os posts atrasados **não são disparados em rajada** (o que geraria ban por spam no TikTok). Posts com atraso superior à tolerância (`OVERDUE_TOLERANCE_MINUTES=15`) são marcados como `NEEDS_REVIEW` para reagendamento com espaçamento seguro.

---

## 7. Consentimento e Máquina de Estados

O consentimento não é genérico:
1. Cada post passa por revisão individual de título, legenda, hashtags, privacidade e declarações obrigatórias (IA/AIGC, conteúdo comercial).
2. Ao aprovar, o sistema calcula um hash criptográfico:  
   `SHA-256(media_sha256 + title + privacy_level + flags)`
3. **Invalidação Automática:** Qualquer edição posterior no texto ou configuração revoga a aprovação e remove o post do status `SCHEDULED`, retornando para `NEEDS_REVIEW`.

---

## 8. Testes Automatizados Validados

Todos os cenários críticos exigidos foram implementados e validados via `pytest`:

```bash
pytest tests/ -v
```

### Relatório de Casos Validados:
1. **Deduplicação & Paginação (`test_deduplication.py`):** Validação de paginação do Drive e rejeição de duplicatas por SHA-256 entre arquivos de nomes diferentes.
2. **Conversão de Fuso (`test_timezone_calendar.py`):** Conversão precisa entre `America/Fortaleza` e UTC e imunidade a variações sazonais.
3. **Reserva Concorrente (`test_concurrency_lock.py`):** Proteção atômica impedindo que dois workers processem o mesmo post (`SKIP LOCKED`).
4. **Recuperação de Falhas & Anti-Spam (`test_restart_recovery.py`):** Recuperação pós-reinício garantindo que jobs muito atrasados não sejam disparados em rajada.
5. **Timeout com Estado Remoto Incerto (`test_reconciliation_timeout.py`):** Timeout após chamada remota entra em `UNKNOWN/RECONCILING` e consulta o `publish_id`, sem duplicar o post.
6. **Tokens Expirados & Criptografia (`test_token_refresh.py`):** Detecção de expiração de token e validação de criptografia Fernet em repouso no banco.
7. **Limites de Taxa & Backoff (`test_rate_limits.py`):** Tratamento do status 429 e respeito estrito ao cabeçalho `Retry-After`.
8. **Estoque & Déficit (`test_stock_deficit.py`):** Cálculo automático de dias de cobertura e registro numérico de déficit de publicações.
9. **Invalidação de Consentimento (`test_approval_invalidation.py`):** Alterações de texto invalidam consentimento e exigem nova aprovação.
10. **Estados de Publicação (`test_upload_vs_publish_states.py`):** Confirmação de que upload binário concluído difere de moderação (`SEND_TO_AUDIT`) e publicação (`PUBLISH_COMPLETE`).

---

## 9. Documentação Complementar

* [Relatório de Verificação de APIs Oficiais](docs/api_verification_report.md)
* [Arquitetura e Máquina de Estados](docs/architecture_and_state_machine.md)
* [Guia de Elegibilidade e Integração TikTok](docs/tiktok_eligibility_and_integration.md)
* [Guia de Configuração do Google Drive](docs/google_drive_setup.md)
* [Manual de Implantação em Produção](docs/production_deployment.md)
