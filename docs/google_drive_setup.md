# Guia de Configuração e Permissões do Google Drive

## 1. Escolha do Modo de Autenticação

O Focus Publisher suporta dois modelos de autenticação com a Google Drive API v3:

### Opção A: Conta de Serviço (Service Account) - Recomendada para Pastas Dedicadas / Shared Drives
1. No console do Google Cloud Platform, crie um projeto e ative a **Google Drive API**.
2. Crie uma Conta de Serviço (ex: `focus-publisher@meu-projeto.iam.gserviceaccount.com`).
3. Gere e baixe a chave privada JSON.
4. Salve o JSON seguro em `secrets/google_credentials.json` ou defina seu conteúdo na variável de ambiente `GOOGLE_SERVICE_ACCOUNT_JSON`.
5. **No Google Drive:** Abra a pasta de vídeos designada, clique em **Compartilhar**, adicione o e-mail da Conta de Serviço e atribua permissão de **Leitor (Viewer)**.
6. Copie o ID da pasta (presente na URL `drive.google.com/drive/folders/<FOLDER_ID>`) e configure em `GOOGLE_DRIVE_FOLDER_ID`.

### Opção B: OAuth 2.0 de Usuário (Para contas pessoais @gmail.com)
1. Crie credenciais do tipo **ID do cliente OAuth 2.0 (Aplicativo Web)** no GCP Console.
2. Defina os URIs de redirecionamento autorizados (ex: `https://seu-dominio.com/connections/google/callback`).
3. Configure `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET`.
4. Conecte pelo painel administrativo em **Conexões**.

---

## 2. Parâmetros e Boas Práticas

* **Inclusão de Subpastas (`DRIVE_INCLUDE_SUBFOLDERS`):**  
  Por padrão vem **desativada (`False`)** para evitar ingestão acidental de lixeiras ou pastas de arquivos brutos não finalizados.
* **Política FIFO (First-In, First-Out):**  
  A sincronização ordena os arquivos por data de criação/modificação mais antiga para mais recente, garantindo que vídeos gravados primeiro sejam publicados primeiro, com possibilidade de ajuste manual de prioridade no painel.
* **Detecção de Duplicidade por SHA-256:**  
  Não nos baseamos apenas no nome do arquivo (que pode mudar no Drive). O sistema calcula o hash SHA-256 e MD5 do arquivo para impedir ingestão ou agendamento duplo do mesmo binário.
* **Preservação dos Arquivos:**  
  O Focus Publisher **NUNCA** apaga nem move arquivos originais no Google Drive por padrão. Os arquivos são tratados como somente leitura.
