# Guia de Elegibilidade, Modos de Publicação e Integração TikTok

## 1. Regras de Elegibilidade do Direct Post

A TikTok Content Posting API (Direct Post) possui diretrizes de conformidade estritas estabelecidas pela ByteDance:

1. **Aprovação de Aplicativo no TikTok Developer Portal:**
   * Qualquer app que pretenda utilizar o escopo `video.publish` para postagem direta em produção precisa passar por revisão manual do TikTok.
   * **Utilitários Exclusivos Internos / Contas Próprias:** O TikTok não aprova aplicativos como "públicos" se forem utilitários criados apenas para gerenciar contas de uma equipe sem intenção de distribuição a terceiros. Nesses casos, o app deve ser registrado na categoria adequada ou mantido em status de desenvolvimento (sandbox) com as contas associadas como testadores autorizados.
   * **Não Simulação de Produto:** É estritamente vedado criar falsas páginas de marketing ou declarar funcionalidade pública enganosa para obter aprovação da API.

2. **Verificação de Domínio e Termos:**
   * O Redirect URI precisa ser HTTPS com domínio verificado no portal.
   * Política de Privacidade e Termos de Serviço acessíveis publicamente.

3. **Modos de Operação do Focus Publisher:**
   * **DEMO:** Modo padrão de inicialização do sistema. Permite testar todo o fluxo de importação, inspeção técnica, agendamento de 10 posts/dia, calendário, aprovações e simulação de resposta do TikTok sem qualquer chamada à rede externa.
   * **DIRECT_POST:** Utilizado exclusivamente quando as credenciais oficiais estiverem configuradas, o usuário tiver completado o OAuth com os escopos `video.publish` e `user.info.basic`, e a conta tiver elegibilidade aprovada.
   * **MANUAL_STUDIO:** Modo seguro de contingência e operação operacional. Gera o pacote com os vídeos inspecionados, o manifesto CSV com a exata data/hora, legenda, hashtags e privacidade, além de tela de apoio para o operador copiar e colar rapidamente no TikTok Studio web.
   * **UPLOAD:** Modo voltado para "Creator Inbox" (`/v2/post/publish/inbox/video/init/`), onde o vídeo é enviado para as notificações do criador no app mobile para que este finalize a postagem com filtros ou edições manuais.

---

## 2. A Realidade sobre a "Fila do TikTok Studio"

> [!IMPORTANT]
> **ATENÇÃO DE ENGENHARIA:**  
> Não existe endpoint na API oficial do TikTok para agendar conteúdo dentro da interface "Agendado" do TikTok Studio.  
> Se o cliente ou a equipe requisitar que o vídeo apareça no Studio com status "Agendado", isso **NÃO é suportado pela API pública**.  
> O Focus Publisher resolve essa necessidade através do:
> 1. Agendamento interno confiável no PostgreSQL com disparo no minuto exato via Celery Worker (`DIRECT_POST`).
> 2. Pacote de preparação para agendamento manual no TikTok Studio (`MANUAL_STUDIO`).

---

## 3. Fluxo de Consentimento e Auditoria de Conteúdo

O Focus Publisher não adota consentimento genérico:
1. Conectar uma conta TikTok via OAuth dá permissão técnica, **mas não constitui consentimento para postar automaticamente**.
2. Cada rascunho de postagem passa por uma etapa de **Revisão e Consentimento**:
   * O operador/criador confere o vídeo, a duração e os metadados técnicos.
   * Edita o título/legenda e define as hashtags.
   * Define declarações obrigatórias:
     * Nível de privacidade (`PUBLIC_TO_EVERYONE`, `SELF_ONLY`, etc., baseado nas opções reais obtidas do endpoint `/v2/post/publish/creator_info/query/`).
     * Permissões de comentários, dueto e costura.
     * Declaração de conteúdo comercial (Branded Content / Brand Organic).
     * Declaração de conteúdo gerado por IA (AIGC).
3. Ao aprovar, um registro na tabela `approvals` armazena:
   * O hash criptográfico do conteúdo (`SHA-256(media_hash + title + privacy_level + settings)`).
   * O identificador do usuário aprovador e timestamp UTC.
4. **Invalidação Automática:** Qualquer alteração na legenda, no horário ou na configuração de privacidade revoga a aprovação e exige novo consentimento antes do envio.

---

## 4. Tratamento de Timeouts e Reconciliação (Sem Duplicações)

Quando o worker envia a requisição de inicialização ou upload e ocorre um timeout de rede:
* **Nunca reenviar imediatamente.** A requisição pode ter sido processada nos servidores do TikTok.
* O post transiciona para o estado `UNKNOWN` / `RECONCILING`.
* A tarefa de reconciliação consulta o endpoint `/v2/post/publish/status/fetch/` utilizando o `publish_id`.
* Se o `publish_id` não tiver sido retornado antes do timeout, a tentativa é registrada e posta em quarentena para inspeção manual no painel de auditoria.
