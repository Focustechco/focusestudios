# Relatório de Verificação de APIs Oficiais (TikTok & Google Drive)

**Data da Verificação:** 03 de novembro de 2026  
**Engenheiro Responsável:** Senior Systems Engineer (Focus Publisher Team)  
**Status de Conformidade:** Documentação Oficial Verificada & Aderente  

---

## 1. TikTok Content Posting API v2

### 1.1 Documentação Consultada
* **Portal Oficial de Desenvolvedores TikTok:**  
  * Visão Geral da Content Posting API: `https://developers.tiktok.com/doc/content-posting-api-get-started`
  * Direct Post (Video Post): `https://developers.tiktok.com/doc/content-posting-api-reference-direct-post`
  * Creator Information Query: `https://developers.tiktok.com/doc/content-posting-api-reference-query-creator-info`
  * Status Fetch (Polling de Publicação): `https://developers.tiktok.com/doc/content-posting-api-reference-get-post-status`
  * Login Kit & Escopos OAuth: `https://developers.tiktok.com/doc/login-kit-web`

### 1.2 Endpoints e Parâmetros Canônicos

1. **Consulta de Informações do Criador (Obrigatório pré-publicação):**
   * **Endpoint:** `POST https://open.tiktokapis.com/v2/post/publish/creator_info/query/`
   * **Cabeçalhos:** `Authorization: Bearer <access_token>`, `Content-Type: application/json; charset=UTF-8`
   * **Payload:** `{}`
   * **Retorno relevante:**
     * `privacy_level_options`: Lista de visibilidades permitidas para a conta (`PUBLIC_TO_EVERYONE`, `MUTUAL_FOLLOW_FRIENDS`, `FOLLOWER_OF_CREATOR`, `SELF_ONLY`).
     * `comment_disabled`, `duet_disabled`, `stitch_disabled`: Flags de recursos permitidos.
     * `max_video_post_duration_sec`: Duração máxima permitida para o criador.
   * **Rate Limit:** 6 requisições por minuto por token de usuário.

2. **Inicialização de Postagem Direta (`FILE_UPLOAD`):**
   * **Endpoint:** `POST https://open.tiktokapis.com/v2/post/publish/video/init/`
   * **Escopo:** `video.publish`
   * **Payload:**
     ```json
     {
       "post_info": {
         "title": "Legenda com #hashtags",
         "privacy_level": "SELF_ONLY",
         "disable_duet": false,
         "disable_comment": false,
         "disable_stitch": false,
         "brand_content_toggle": false,
         "brand_organic_toggle": false,
         "is_aigc": false
       },
       "source_info": {
         "source": "FILE_UPLOAD",
         "video_size": 15420300,
         "chunk_size": 15420300,
         "total_chunk_count": 1
       }
     }
     ```
   * **Retorno:** `data.publish_id` e `data.upload_url`.

3. **Upload de Binário (Transferência via PUT):**
   * **Endpoint:** `{upload_url}` retornado no passo 2.
   * **Método:** `PUT`
   * **Cabeçalhos:**
     * `Content-Range: bytes 0-{size-1}/{size}`
     * `Content-Type: video/mp4`
   * **Corpo:** Binário do arquivo de vídeo.

4. **Verificação de Status de Publicação:**
   * **Endpoint:** `POST https://open.tiktokapis.com/v2/post/publish/status/fetch/`
   * **Payload:** `{"publish_id": "v_pub_file~v2.xxxx"}`
   * **Rate Limit:** 30 requisições por minuto por token.
   * **Estados oficiais:** `PROCESSING_DOWNLOAD`, `PROCESSING_UPLOAD`, `SEND_TO_AUDIT`, `PUBLISH_COMPLETE`, `FAILED`.

---

## 2. Realidade Técnica do TikTok Studio vs. API

> [!WARNING]
> **RESTRIÇÃO FUNDAMENTAL #2 e #3:**  
> A TikTok Content Posting API **NÃO possui endpoint público para injetar vídeos na "Fila de Agendamento do TikTok Studio"**.  
> Qualquer alegação de que uma API de terceiro agenda nativamente dentro da tela do TikTok Studio é falsa.

* **Calendário Interno do Focus Publisher:**  
  O agendamento é **estritamente interno**. O PostgreSQL mantém a agenda exata em UTC (convertida para `America/Fortaleza`), e o Celery Worker dispara a chamada de postagem direta no horário programado.
* **Modo `MANUAL_STUDIO`:**  
  Para criadores que exigem a aprovação manual na interface nativa do TikTok Studio, o Focus Publisher disponibiliza um **Pacote de Exportação**:
  1. Manifesto em CSV formatado com nome do arquivo, legenda, hashtags, data/hora pretendida e privacidade.
  2. Download direto dos vídeos validados.
  3. Botão de cópia rápida de legenda com 1 clique.
  4. Status no painel marcado expressamente como: `"Aguardando agendamento manual no TikTok Studio"`.

---

## 3. Google Drive API v3

### 3.1 Documentação Consultada
* **Google Drive API Reference:** `https://developers.google.com/drive/api/v3/reference/files/list`
* **Google Drive Download Media:** `https://developers.google.com/drive/api/guides/manage-downloads`
* **Shared Drives Support:** `https://developers.google.com/drive/api/guides/enable-shareddrives`

### 3.2 Endpoints e Regras Canônicas

1. **Listagem Paginada com Suporte a Shared Drives:**
   * **Endpoint:** `GET https://www.googleapis.com/drive/v3/files`
   * **Parâmetros Obrigatórios:**
     * `q`: `'<FOLDER_ID>' in parents and trashed = false and mimeType != 'application/vnd.google-apps.folder'`
     * `fields`: `nextPageToken, files(id, name, mimeType, size, md5Checksum, modifiedTime, createdTime)`
     * `pageSize`: 100
     * `supportsAllDrives`: `true`
     * `includeItemsFromAllDrives`: `true`
     * `corpora`: `allDrives` (quando operando em drive compartilhado)

2. **Download Streaming Autenticado:**
   * **Endpoint:** `GET https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&supportsAllDrives=true`
   * **Regra:** Nunca tornar arquivos públicos na nuvem do Google Drive. O download é feito pelo worker em stream temporário com hash SHA-256 verificado.
