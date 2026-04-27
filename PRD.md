# PRD — Plataforma LMS White-Label Corporativa

**Versão:** 2.0  
**Data:** Abril de 2026  
**Status:** Em validação

---

## Sumário

1. [Visão do Produto](#1-visão-do-produto)
2. [Problema](#2-problema)
3. [Oportunidade de Mercado](#3-oportunidade-de-mercado)
4. [Modelo de Negócio](#4-modelo-de-negócio)
5. [Personas](#5-personas)
6. [Jornadas dos Usuários](#6-jornadas-dos-usuários)
7. [Proposta de Valor](#7-proposta-de-valor)
8. [Funcionalidades e Escopo](#8-funcionalidades-e-escopo)
9. [Módulo de Gamificação Corporativa](#9-módulo-de-gamificação-corporativa)
10. [Fora do Escopo do MVP](#10-fora-do-escopo-do-mvp)
11. [Stack Tecnológica](#11-stack-tecnológica)
12. [Arquitetura do Sistema](#12-arquitetura-do-sistema)
13. [Requisitos Não Funcionais](#13-requisitos-não-funcionais)
14. [Métricas de Sucesso](#14-métricas-de-sucesso)
15. [Riscos e Mitigações](#15-riscos-e-mitigações)
16. [Roadmap de Lançamento](#16-roadmap-de-lançamento)
17. [Perguntas em Aberto](#17-perguntas-em-aberto)

---

## 1. Visão do Produto

Plataforma **PWA white-label** que permite **tenants** (produtores de conteúdo, experts, agências de treinamento corporativo) criar e operar uma área de membros completamente personalizada para vender e entregar infoprodutos — cursos, mentorias, trilhas e comunidades.

O diferencial central está no modelo **B2B2C**: o tenant não apenas vende para pessoas físicas, mas pode contratar **empresas clientes** que liberam acesso para seus funcionários, criando uma camada corporativa com gestão de times, metas coletivas e gamificação voltada para formação profissional.

A plataforma integra nativamente: **hospedagem de vídeo** via Bunny.net, **comunidade**, **mensageria direta**, **email marketing**, **páginas de venda**, **transcrição e IA por aula**, **analytics em tempo real** e **painel administrativo** — sem depender de SaaS externos como Ensínio, The Members ou Circle.

> "Qualquer expert ou agência deve conseguir lançar sua própria escola online em horas, com identidade visual própria, experiência de app e ferramentas que transformam o aprendizado corporativo em algo que as pessoas querem usar."

---

## 2. Problema

### 2.1 Para o Tenant (produtor / agência)

- Plataformas genéricas de LMS não oferecem white-label real — o aluno sempre sabe que está em "Hotmart" ou "Teachable"
- Ferramentas com white-label são caras, complexas e não atendem ao mercado B2B corporativo
- Não existe solução que combine área de membros + gestão de empresas clientes + gamificação corporativa + email marketing + comunidade em um único produto acessível

### 2.2 Para a Empresa Cliente (RH / gestor)

- Plataformas de e-learning corporativo (LMS tradicional) são caras, burocráticas e têm UX ruim
- Funcionários não usam voluntariamente — engajamento baixo e difícil de medir
- Falta visibilidade real sobre progresso e ROI do treinamento

### 2.3 Para o Funcionário (estudante)

- Treinamentos corporativos são percebidos como obrigação chata
- Conteúdos sem interatividade geram abandono rápido
- Não há senso de progresso, reconhecimento ou motivação para continuar

---

## 3. Oportunidade de Mercado

- Mercado global de e-learning corporativo deve superar **USD 400 bilhões até 2026**
- No Brasil, segmento de LMS e infoprodutos cresce mais de **30% ao ano**
- A combinação white-label + B2B2C + gamificação é lacuna clara: LMS corporativos tradicionais (Moodle, SAP SuccessFactors) têm UX ultrapassada; plataformas de infoprodutos (Hotmart, Eduzz) não atendem o corporativo
- Modelo SaaS multi-tenant permite escalar com baixo custo incremental por novo tenant

---

## 4. Modelo de Negócio

### 4.1 Estrutura de relacionamento

```
Tenant (ex: agência de treinamento)
  └── Empresa Cliente A (ex: empresa de varejo)
        └── Funcionário 1
        └── Funcionário 2
  └── Empresa Cliente B (ex: rede de franquias)
        └── Funcionário 1
        ...
  └── Aluno B2C (pessoa física)
```

### 4.2 Como o tenant monetiza

- **B2C direto**: vende acesso individual via checkout com gateway externo
- **B2B**: vende pacotes de acesso para empresas (por número de licenças ou acesso ilimitado por CNPJ)
- **Assinatura recorrente**: plano mensal/anual por empresa cliente ou por número de funcionários ativos

### 4.3 Como o produto monetiza o tenant

- Plano SaaS mensal por tenant (freemium ou pago por faixa de alunos ativos)
- Taxa sobre transações processadas pela plataforma (opcional)
- Planos com features avançadas: gamificação, liga entre empresas, builder de páginas, analytics avançado

---

## 5. Personas

### 5.1 Alex — O Tenant / Produtor de Conteúdo

**Perfil:** Consultor de RH ou agência de treinamento, 32–48 anos, já vende cursos online ou treinamentos presenciais.

**Motivações:**
- Quer plataforma com marca própria, sem "Powered by X"
- Precisa vender para empresas, não apenas para pessoas físicas
- Quer escalar sem aumentar equipe operacional

**O que precisa:**
- Cadastrar empresas e gerenciar acessos por CNPJ
- Painel administrativo com visão consolidada de todos os clientes
- White-label real: domínio próprio, logo, cores, nome do app
- Email marketing integrado para nutrir leads e alunos
- Páginas de venda criadas e gerenciadas na própria plataforma

---

### 5.2 Carla — A Gestora de RH / L&D da Empresa Cliente

**Perfil:** Analista ou gerente de RH/Treinamento, 28–42 anos, responsável pelo desenvolvimento dos funcionários.

**Motivações:**
- Precisa comprovar ROI dos treinamentos para a diretoria
- Quer que funcionários realmente usem a plataforma
- Busca solução fácil de operar sem equipe técnica

**O que precisa:**
- Painel de acompanhamento com métricas de engajamento por time
- Ferramentas para criar metas e campanhas de incentivo
- Relatórios exportáveis para apresentar à diretoria

---

### 5.3 Bruno — O Funcionário / Estudante

**Perfil:** Profissional de qualquer área, 22–45 anos, acessa o conteúdo principalmente pelo celular.

**Motivações:**
- Quer crescer na carreira e desenvolver habilidades práticas
- Se engaja com desafios, rankings e reconhecimento
- Prefere aprender em pequenas doses, no próprio ritmo

**O que precisa:**
- App rápido e bonito no celular (PWA)
- Senso claro de progresso: nível, XP, badges
- Transcrição e resumo por IA para revisar conteúdo
- Comunidade ativa para trocar experiências

---

### 5.4 Diego — O Super Admin / Tenant Owner Técnico

**Perfil:** CTO ou desenvolvedor da agência que opera a plataforma como SaaS.

**O que precisa:**
- Multi-tenancy seguro e performático
- APIs bem documentadas e webhooks confiáveis com replay
- Logs estruturados e painel de saúde do sistema
- Observabilidade real para diagnosticar problemas rapidamente

---

## 6. Jornadas dos Usuários

### 6.1 Tenant — Onboarding e primeiro cliente

1. Tenant se cadastra e configura branding: logo, cores, domínio
2. Cria primeiro produto (curso ou trilha) com upload de vídeos via Bunny.net
3. Cria landing page de vendas dentro da plataforma
4. Cadastra empresa cliente com CNPJ e define contrato de acesso
5. Importa lista de funcionários (CSV) ou envia link de convite
6. Configura campanha de email de boas-vindas via automação
7. Acompanha engajamento pelo painel administrativo

**Critério de sucesso:** Tenant consegue ter plataforma operando para um cliente em menos de 1 dia.

---

### 6.2 Gestora de RH — Acompanhamento de time

1. Carla recebe acesso ao painel da empresa
2. Visualiza dashboard com % de conclusão por time
3. Cria meta coletiva: "80% do time conclui módulo de Compliance até sexta"
4. Acompanha progresso em tempo real
5. Envia lembrete para funcionários atrasados via notificação in-app
6. Exporta relatório ao final do mês para apresentar à diretoria

**Critério de sucesso:** Carla consegue criar e monitorar uma meta sem precisar de suporte técnico.

---

### 6.3 Funcionário — Primeiro acesso e engajamento contínuo

1. Bruno recebe e-mail de convite da empresa
2. Acessa pelo celular via link (PWA — sem instalar app)
3. Faz login com magic link (sem precisar criar senha)
4. Vê trilha de onboarding no mapa de jornada
5. Conclui primeira aula assistindo vídeo com transcrição sincronizada
6. Ganha XP + badge de boas-vindas
7. Faz anotações com timestamp na aula
8. Recebe notificação push lembrando do streak no dia seguinte
9. Desafia colega para quiz battle
10. Aparece no ranking do time ao final da semana

**Critério de sucesso:** Bruno abre a plataforma por iniciativa própria, sem ser lembrado pelo RH.

---

### 6.4 Jornada de Compra Externa — Webhook

1. Empresa fecha contrato e paga via gateway externo (Hotmart, Stripe etc.)
2. Gateway dispara webhook para a plataforma
3. Plataforma valida assinatura HMAC e processa evento via fila assíncrona
4. Cria ou atualiza matrícula da empresa
5. Libera acesso aos funcionários cadastrados
6. Dispara automação de email de boas-vindas

**Critério de sucesso:** Acesso liberado automaticamente em menos de 60 segundos após pagamento confirmado.

---

## 7. Proposta de Valor

### Para o Tenant

| Necessidade | Como a plataforma resolve |
|---|---|
| White-label real | Domínio próprio, logo, cores, nome do app, sem menção à plataforma base |
| Vender para empresas | Cadastro de CNPJ, gestão de licenças, relatórios por empresa |
| Escalar sem esforço | Multi-tenant automatizado, onboarding self-service |
| Engajamento alto | Gamificação pronta, sem desenvolvimento adicional |
| Marketing integrado | Email marketing, landing pages, captura de leads com UTM tracking |
| Conteúdo de valor | Transcrição automática e resumo por IA das aulas |

### Para a Empresa Cliente

| Necessidade | Como a plataforma resolve |
|---|---|
| Funcionários que usam o treinamento | Gamificação, streaks, rankings, metas coletivas |
| Visibilidade de ROI | Dashboard de engajamento, relatórios exportáveis |
| Fácil de operar | Interface simples, sem necessidade de equipe técnica |

### Para o Funcionário

| Necessidade | Como a plataforma resolve |
|---|---|
| Aprendizado no celular | PWA responsivo, rápido, sem instalação |
| Motivação para continuar | XP, níveis, badges, streaks, quiz battle |
| Revisão de conteúdo | Transcrição com timestamps, resumo por IA, anotações pessoais |
| Comunidade | Feed, canais, mensagens diretas, feed de conquistas |

---

## 8. Funcionalidades e Escopo

### 8.1 Autenticação e Onboarding

**Endpoints:**
- `POST /auth/register` — cadastro com email/senha
- `POST /auth/login` — retorna `access_token` + `refresh_token` (cookie httpOnly)
- `POST /auth/refresh` — renova access token via refresh token rotativo
- `POST /auth/logout` — revoga refresh token no Redis
- `POST /auth/magic-link` — gera link de login sem senha
- `POST /auth/magic-link/verify` — valida token do magic link
- `POST /auth/forgot-password` — envia email de recuperação
- `POST /auth/reset-password` — confirma reset via token
- `GET /users/me` — perfil do usuário autenticado
- `PATCH /users/me` — atualiza perfil (nome, avatar, bio)

**Modelo `users`:**
```sql
id UUID PK
tenant_id UUID FK NOT NULL          -- isolamento multi-tenant
email VARCHAR NOT NULL
password_hash VARCHAR               -- nullable (magic link only)
name VARCHAR NOT NULL
avatar_url VARCHAR
bio TEXT
role ENUM('student', 'manager', 'admin', 'super_admin')
company_id UUID FK NULLABLE         -- vínculo com empresa cliente
is_active BOOLEAN DEFAULT true
is_suspended BOOLEAN DEFAULT false
last_seen_at TIMESTAMP
created_at TIMESTAMP
```

**Regras:**
- Roles: `student`, `manager` (gestor de RH da empresa cliente), `admin` (tenant admin), `super_admin` (plataforma SaaS).
- Refresh tokens no Redis com TTL 30 dias. Logout invalida imediatamente.
- Magic link com TTL 15 minutos, uso único.
- Rate limiting: 10 tentativas por IP por 15 minutos em `/auth/login` e `/auth/magic-link`.
- Convite por link com token assinado para onboarding de funcionários.
- Reconhecimento de e-mail para identificar tenant automaticamente.

**Critério de aceite:** Funcionário acessa pela primeira vez em menos de 2 minutos, sem criar senha.

---

### 8.2 Modelo de Autorização e Isolamento

#### Hierarquia de acesso

```
super_admin       → todos os tenants (apenas /superadmin/*)
  └── admin       → todos os recursos do próprio tenant
        └── manager → apenas recursos da própria company_id
              └── student → apenas recursos próprios (progresso, notas, conquistas)
```

#### Regras de isolamento obrigatórias

**Nível tenant (`tenant_id`):**
- Toda tabela com dados de usuário ou conteúdo contém `tenant_id NOT NULL`
- Todo request é interceptado por middleware que extrai o tenant via domínio/subdomínio e injeta no contexto
- Nenhuma query executa sem filtro `WHERE tenant_id = :current_tenant`

**Nível empresa (`company_id`):**
- Qualquer endpoint que opera sobre recursos corporativos (funcionários, metas, departamentos, relatórios, rankings) exige `company_id` — enviado explicitamente no path, query param ou body
- Backend valida **sempre** que a `company_id` recebida pertence ao `tenant_id` do usuário autenticado
- Manager tem sua `company_id` gravada no JWT no momento do login — o backend usa este valor, nunca aceita `company_id` diferente do JWT para o role `manager`
- Admin pode enviar qualquer `company_id` válida do seu tenant

**Dependency injection (`dependencies.py`):**
```python
# Injeta e valida tenant via domínio — usado em todos os routers
async def get_current_tenant(request: Request) -> Tenant: ...

# Valida usuário autenticado dentro do tenant
async def get_current_user(tenant: Tenant, token: str) -> User: ...

# Garante role admin
async def require_admin(user: User) -> User: ...

# Garante acesso à company: admin passa company_id no path/body;
# manager: company_id vem do JWT — ignora o que vier no body
async def require_company_access(
    company_id: UUID,
    user: User,
    tenant: Tenant
) -> Company:
    # 1. Busca company WHERE id = company_id AND tenant_id = tenant.id
    # 2. Se não encontrar → 404 (não vaza existência de outras companies)
    # 3. Se user.role == 'manager' e user.company_id != company_id → 403
    ...
```

**Exemplos de endpoints e como `company_id` flui:**

| Endpoint | Quem chama | Fonte do company_id | Validação |
|---|---|---|---|
| `GET /admin/companies/{company_id}/members` | Admin | Path param | tenant_id match |
| `GET /manager/dashboard` | Manager | JWT claim | fixo, não aceita override |
| `POST /manager/goals` | Manager | JWT claim | fixo, não aceita override |
| `GET /admin/companies/{company_id}/report` | Admin | Path param | tenant_id match |
| `POST /admin/companies/{company_id}/members/bulk-import` | Admin | Path param | tenant_id match |
| `GET /gamification/leaderboard?company_id=...` | Student | Query param | tenant_id match + enrollment check |

**O que nunca deve acontecer:**
- Manager vê funcionários de outra empresa enviando `company_id` diferente no body
- Admin de tenant A acessa `company_id` de tenant B, mesmo com UUID válido
- Student acessa progresso ou conquistas de outro usuário fora do seu contexto

---

### 8.3 White-Label e Multi-Tenancy


**Endpoints:**
- `GET /admin/tenant/branding` — configurações de branding do tenant
- `PATCH /admin/tenant/branding` — atualiza logo, cores, fonte, domínio
- `GET /admin/tenant/settings` — configurações gerais (timezone, idioma, features ativas)
- `PATCH /admin/tenant/settings`

**Modelo:**
```sql
tenants: id, slug, name, custom_domain, subdomain,
         logo_url, favicon_url, primary_color, secondary_color,
         font_family, app_name, plan ENUM('free','starter','pro','enterprise'),
         features JSONB, created_at

-- features JSONB: {gamification: true, community: true, email_marketing: true, ...}
```

**Regras:**
- Cada tenant tem domínio próprio ou subdomínio `{slug}.plataforma.com`.
- Isolamento total de dados via `tenant_id` em todas as tabelas.
- Nome do app customizável (aparece no PWA instalado).
- Features ativáveis por plano: gamificação, liga entre empresas, analytics avançado.

**Critério de aceite:** Dois tenants com domínios diferentes têm experiências visuais completamente distintas, sem vazamento de dados entre si.

---

### 8.4 Gestão de Empresas Clientes (B2B)

**Endpoints (Admin) — `company_id` sempre no path, validado contra `tenant_id`:**
- `GET /admin/companies` — lista paginada de empresas do tenant
- `POST /admin/companies` — cadastrar empresa (CNPJ, razão social, contrato)
- `PATCH /admin/companies/{company_id}` — editar dados e período de acesso
- `DELETE /admin/companies/{company_id}`
- `GET /admin/companies/{company_id}/members` — funcionários da empresa
- `POST /admin/companies/{company_id}/members/bulk-import` — importação CSV
- `POST /admin/companies/{company_id}/members/invite` — convite individual por email
- `PATCH /admin/companies/{company_id}/members/{user_id}` — editar vínculo (time, role, status)
- `DELETE /admin/companies/{company_id}/members/{user_id}` — remover funcionário
- `GET /admin/companies/{company_id}/report` — relatório de engajamento exportável (PDF/CSV)
- `GET /admin/companies/{company_id}/dashboard` — métricas por empresa

**Endpoints (Manager) — `company_id` extraído do JWT, nunca do body/path:**
- `GET /manager/dashboard` — dashboard da empresa (company do JWT)
- `GET /manager/members` — funcionários da empresa (company do JWT)
- `POST /manager/goals` — criar meta coletiva (company do JWT)
- `GET /manager/goals` — metas ativas e histórico
- `POST /manager/goals/{goal_id}/reminder` — enviar lembrete para atrasados
- `GET /manager/report` — relatório da empresa (company do JWT)

**Regras de isolamento:**
- `{company_id}` no path (admin) → backend valida `companies.tenant_id = current_tenant.id`; se não bater, retorna `404` — nunca `403`, para não vazar existência
- Manager: `company_id` extraído do `JWT claims.company_id`; body nunca substitui este valor
- Remoção de funcionário: `DELETE` valida que `user.tenant_id = tenant.id` e `company_members.company_id = company.id` antes de remover

**Modelo:**
```sql
companies: id, tenant_id FK NOT NULL, cnpj VARCHAR, legal_name VARCHAR, trade_name VARCHAR,
           contract_start DATE, contract_end DATE,
           max_seats INT, status ENUM('active','suspended','expired'), created_at

company_members: id, company_id FK NOT NULL, user_id FK NOT NULL,
                 team VARCHAR, job_role VARCHAR,
                 joined_at TIMESTAMP, is_active BOOLEAN,
                 UNIQUE(company_id, user_id)

company_goals: id, company_id FK NOT NULL, title VARCHAR, description TEXT,
               target_metric ENUM('completion_rate','xp_total','course_completion'),
               target_value DECIMAL, course_id FK NULLABLE,
               deadline DATE, badge_reward_id FK NULLABLE,
               status ENUM('active','achieved','failed'), created_at
```

**Critério de aceite:** Tenant cadastra empresa e importa 500 funcionários em menos de 10 minutos. Manager não consegue acessar dados de outra empresa mesmo enviando `company_id` arbitrário.

---

### 8.4 Catálogo de Produtos

**Endpoints (Admin):**
- `POST /admin/products` — criar produto (curso, trilha, mentoria, bundle)
- `PATCH /admin/products/{id}` — editar metadados
- `PATCH /admin/products/{id}/status` — rascunho / publicado / arquivado
- `GET /admin/products` — lista com filtros

**Endpoints (Público/Aluno):**
- `GET /catalog` — catálogo público (produtos com visibilidade pública)
- `GET /catalog/{slug}` — página de vendas do produto

**Modelo:**
```sql
products: id, tenant_id FK, type ENUM('course','trail','mentorship','bundle'),
          title, slug UNIQUE, short_description, description TEXT,
          thumbnail_url, cover_url, status ENUM('draft','published','archived'),
          visibility ENUM('public','private','unlisted'),
          price DECIMAL, gateway_ids JSONB,     -- {hotmart_id, kiwify_id, greenn_id}
          access_days INT, created_at

product_courses: product_id FK, course_id FK, order_index  -- para bundles e trilhas
```

---

### 8.5 Cursos, Módulos e Aulas

**Endpoints (Admin):**
- `POST /admin/courses` — criar curso
- `PATCH /admin/courses/{id}` — editar (título, thumbnail, slug)
- `POST /admin/courses/{id}/modules` — criar módulo
- `PATCH /admin/modules/{id}` — editar módulo (título, ordem)
- `PATCH /admin/modules/{id}/reorder` — reordenar aulas via array de IDs
- `POST /admin/modules/{id}/lessons` — criar aula manualmente
- `PATCH /admin/lessons/{id}` — editar aula
- `DELETE /admin/lessons/{id}`
- `POST /admin/modules/{id}/lessons/bulk-import` — importação em massa via Bunny.net
- `POST /admin/lessons/{id}/transcribe` — dispara transcrição via AssemblyAI
- `GET /admin/lessons/{id}/transcript` — status e texto da transcrição
- `POST /admin/lessons/{id}/summarize` — gera resumo via IA (Claude Haiku)

**Endpoints (Aluno):**
- `GET /courses` — cursos matriculados
- `GET /courses/{slug}` — detalhes do curso (módulos + aulas + progresso)
- `GET /lessons/{id}` — dados da aula (URL de streaming assinada via Bunny)
- `POST /lessons/{id}/progress` — marcar concluída / registrar timestamp
- `GET /courses/{id}/continue` — última aula assistida
- `GET /courses/{course_id}/search?q=termo` — busca em transcrições (PostgreSQL FTS)

**Modelo:**
```sql
courses: id, tenant_id FK, title, slug, description, thumbnail_url,
         is_published BOOLEAN, created_at

modules: id, course_id FK, title, order_index, created_at

lessons: id, module_id FK, title, type ENUM('video','text','pdf','live','quiz','embed','download'),
         bunny_video_id, thumbnail_url, duration_seconds,
         is_published BOOLEAN, order_index, preview_allowed BOOLEAN,
         drip_type ENUM('immediate','fixed_date','days_after_enrollment','prerequisite'),
         drip_value JSONB,                -- {date} ou {days} ou {lesson_id}
         transcript_text JSONB,           -- [{text, start_ms, end_ms}]
         ai_summary TEXT, created_at

lesson_progress: id, user_id FK, lesson_id FK, completed_at, last_watched_at,
                 watch_seconds INT, UNIQUE(user_id, lesson_id)

notes: id, user_id FK, lesson_id FK, content TEXT,
       video_timestamp_seconds INT,       -- âncora no vídeo
       created_at, updated_at
```

**Integração Bunny.net:**
- `GET /admin/bunny/library/{folder}` — lista vídeos do folder no Bunny
- Admin seleciona vídeos → bulk-import cria todas as aulas de uma vez
- Streaming via URL assinada com token temporário (TTL 2h) — nunca expõe URL raw

**Fluxo de transcrição:**
1. Admin dispara `/transcribe` → Celery envia para AssemblyAI
2. AssemblyAI notifica via webhook → `POST /internal/transcription-callback`
3. Transcrição salva em `lessons.transcript_text` (JSONB com timestamps)
4. Celery dispara resumo via Claude API → salvo em `lessons.ai_summary`

**Regras Drip Content:**
- Liberação imediata, por data fixa, por dias após matrícula ou por conclusão de pré-requisito
- Aluno vê claramente quais aulas estão bloqueadas, por quê e quando serão liberadas
- Configurável por seção ou por aula individualmente

---

### 8.6 Matrículas e Controle de Acesso

**Endpoints (Admin):**
- `GET /admin/enrollments` — lista paginada com filtros
- `POST /admin/enrollments` — matricular manualmente
- `PATCH /admin/enrollments/{id}` — alterar status, data de expiração
- `DELETE /admin/enrollments/{id}`
- `POST /admin/enrollments/bulk` — ações em massa (matricular, suspender, cancelar)

**Endpoint (Aluno):**
- `GET /users/me/enrollments` — matrículas ativas, datas e histórico

**Modelo:**
```sql
enrollments: id, tenant_id FK, user_id FK, product_id FK,
             status ENUM('active','expired','suspended','cancelled','refunded'),
             expires_at TIMESTAMP, enrolled_at TIMESTAMP,
             enrolled_by ENUM('webhook','manual','admin','bulk_import'),
             company_id FK NULLABLE       -- vínculo corporativo
```

---

### 8.7 Webhooks e Gateways de Pagamento

**Endpoints:**
- `POST /webhooks/hotmart`
- `POST /webhooks/kiwify`
- `POST /webhooks/greenn`
- `POST /webhooks/monetizze`
- `POST /webhooks/stripe`
- `GET /admin/webhooks/logs` — histórico completo com filtros
- `POST /admin/webhooks/{id}/replay` — replay manual de evento com erro
- `POST /admin/webhooks/test` — modo teste (não executa matrícula real)

**Modelo:**
```sql
webhook_logs: id, tenant_id FK, provider ENUM('hotmart','kiwify','greenn','monetizze','stripe','custom'),
              event_type VARCHAR, payload JSONB, signature_valid BOOLEAN,
              processed BOOLEAN, error_message TEXT, attempts INT DEFAULT 0,
              received_at TIMESTAMP

leads: id, tenant_id FK, email, name,
       source ENUM('hotmart_checkout','kiwify_checkout','greenn_checkout','landing_page'),
       utm_source, utm_medium, utm_campaign, utm_content, utm_term,
       product_id FK NULLABLE, created_at
```

**Fluxo:**
1. Webhook chega → valida assinatura HMAC do provider imediatamente
2. Registra em `webhook_logs` antes de qualquer processamento
3. Se `test_mode = true`: registra, não cria matrícula
4. Celery processa de forma assíncrona: encontra produto pelo `gateway_id`, cria/atualiza enrollment
5. Evento de reembolso → status `refunded`, acesso revogado imediatamente
6. Retry automático com backoff exponencial em caso de falha

**Critério de aceite:** Compra confirmada libera acesso em menos de 60 segundos.

---

### 8.8 Comunidade

**Endpoints (Aluno):**
- `GET /community/spaces` — espaços disponíveis para o usuário
- `GET /community/spaces/{slug}/channels` — canais do espaço
- `GET /community/channels/{slug}/posts` — posts paginados
- `POST /community/channels/{slug}/posts` — criar post (texto + imagens)
- `DELETE /community/posts/{id}` — autor ou admin
- `POST /community/posts/{id}/like` / `DELETE /community/posts/{id}/like`
- `GET /community/posts/{id}/comments`
- `POST /community/posts/{id}/comments`
- `DELETE /community/comments/{id}`
- `POST /community/posts/{id}/report` — denúncia

**Endpoints (Admin):**
- `GET /admin/community/reports` — fila de denúncias
- `PATCH /admin/community/reports/{id}` — aprovar/rejeitar
- `POST /admin/community/users/{id}/suspend` — suspender da comunidade
- `POST /admin/community/channels` — criar/editar canal

**Modelo:**
```sql
spaces: id, tenant_id FK, name, slug, description, is_active, order_index

channels: id, space_id FK, slug, name,
          type ENUM('feed','announcements','cases','opportunities','chat'),
          post_policy ENUM('all','moderators','admins'),
          description, order_index, is_active

posts: id, channel_id FK, user_id FK, content TEXT, media_urls JSONB,
       metadata JSONB, likes_count INT DEFAULT 0, comments_count INT DEFAULT 0,
       is_pinned BOOLEAN, created_at

comments: id, post_id FK, user_id FK, content TEXT, created_at

post_likes: user_id FK, post_id FK, PRIMARY KEY(user_id, post_id)

reports: id, reporter_id FK, post_id FK NULLABLE, comment_id FK NULLABLE,
         reason VARCHAR, ai_flagged BOOLEAN,
         status ENUM('pending','resolved','dismissed'),
         resolved_by FK NULLABLE, created_at
```

**Moderação por IA:** Celery analisa texto via Claude Haiku e imagens via Vision. Score de toxicidade > threshold → cria report com `ai_flagged = true`.

---

### 8.9 Mensageria Direta

**Endpoints:**
- `GET /messages/conversations` — lista conversas
- `POST /messages/conversations` — iniciar conversa
- `GET /messages/conversations/{id}/messages` — histórico paginado
- `POST /messages/conversations/{id}/messages` — enviar mensagem
- `WebSocket /ws/messages` — tempo real (JWT no header)

**Modelo:**
```sql
conversations: id, tenant_id FK, created_at

conversation_participants: conversation_id FK, user_id FK, last_read_at

messages: id, conversation_id FK, sender_id FK, content TEXT, created_at
```

---

### 8.10 Notificações e Presença Online

**Notificações:**
- `GET /notifications` — paginado
- `POST /notifications/read-all`
- `PATCH /notifications/{id}/read`
- `POST /admin/notifications/broadcast` — envio em massa (todos ou segmento)
- `WebSocket /ws/notifications` — recebe notificações em tempo real

**Presença:**
- `WebSocket /ws/presence` — heartbeat a cada 30s com página atual
- `GET /admin/users/online` — usuários online agora, página atual, tempo na sessão

```sql
notifications: id, tenant_id FK, user_id FK, type VARCHAR, title VARCHAR, body TEXT,
               action_url VARCHAR, is_read BOOLEAN DEFAULT false, created_at

user_sessions: id, user_id FK, started_at, ended_at,
               pages_visited JSONB, duration_seconds INT
```

**Implementação presença:** Redis key `presence:{tenant_id}:{user_id}` → `{page, last_seen}` com TTL 60s.

**Canais de notificação:**
- In-app via WebSocket
- Email transacional via Resend
- Push notification via PWA (Service Worker)

---

### 8.11 Email Marketing

**Endpoints:**
- `GET|POST /admin/email/audiences` — segmentos dinâmicos
- `GET|POST /admin/email/templates` — templates HTML
- `GET|POST /admin/email/campaigns` — campanhas (template + audiência + agendamento)
- `POST /admin/email/campaigns/{id}/send` — disparar campanha
- `GET|POST /admin/email/automations` — fluxos: trigger + delay + condição + emails

**Modelo:**
```sql
email_audiences: id, tenant_id FK, name, filter_json JSONB

email_templates: id, tenant_id FK, name, subject, html_body, created_at

email_campaigns: id, tenant_id FK, name, template_id FK, audience_id FK,
                 status ENUM('draft','scheduled','sent'),
                 scheduled_at, sent_at, sent_count

email_automations: id, tenant_id FK, name,
                   trigger_event VARCHAR,   -- 'enrollment.created', 'lesson.completed', etc.
                   steps JSONB, is_active

email_sends: id, campaign_id FK NULLABLE, automation_id FK NULLABLE,
             user_id FK, email VARCHAR,
             status ENUM('sent','opened','bounced'), sent_at
```

**Execução:** Celery faz batch send via Resend API. `opened` tracked via pixel 1x1 único por send.

---

### 8.12 Vitrine e Páginas de Venda

**Endpoints:**
- `GET /admin/landing-pages` — lista páginas
- `POST /admin/landing-pages` — criar página (slug + código)
- `PATCH /admin/landing-pages/{id}` — editar código
- `GET /admin/landing-pages/{id}/analytics` — views, leads, conversão
- `GET /p/{slug}` — endpoint público que serve a página
- `POST /p/{slug}/lead` — captura lead com UTM params
- `POST /admin/landing-pages/{id}/links` — gerar link com UTM customizado

**Modelo:**
```sql
landing_pages: id, tenant_id FK, slug UNIQUE, title,
               jsx_code TEXT, is_active, created_at

page_views: id, landing_page_id FK, session_id VARCHAR,
            utm_source, utm_medium, utm_campaign, utm_content, utm_term,
            ip_hash VARCHAR, viewed_at
```

**Editor:** Monaco Editor (VS Code) com syntax highlight. Preview ao lado via `<iframe>`.  
**SEO:** título, descrição e dados estruturados configuráveis por página.

---

### 8.13 Analytics

**Endpoints:**
- `GET /admin/dashboard` — métricas gerais do tenant
- `GET /admin/analytics/engagement` — DAU/WAU/MAU por tenant e por empresa
- `GET /admin/analytics/courses` — taxa de conclusão, tempo médio por aula
- `GET /admin/analytics/community` — engajamento na comunidade
- `GET /admin/analytics/revenue` — receita, churn, LTV
- `GET /admin/users/online` — usuários online em tempo real

**Dashboard retorna:**
```json
{
  "total_students": 0,
  "active_enrollments": 0,
  "total_courses": 0,
  "revenue_this_month": 0,
  "new_students_this_week": 0,
  "dau_mau_ratio": 0.0,
  "top_courses_by_completion": [],
  "online_now": 0,
  "companies_active": 0
}
```

---

### 8.14 Painel Administrativo

- Visão consolidada de alunos, matrículas e receita
- Gestão de usuários, papéis e permissões
- Gestão de conteúdo (cursos, aulas, assets)
- Configuração de gateways e webhooks
- Relatórios de engajamento e progresso exportáveis
- Gestão de empresas clientes e times
- Menu dinâmico configurável por role

**Menu dinâmico:**
- `GET /menu` — retorna menu role-aware para o usuário atual
- `GET /admin/menu` — configuração completa
- `PUT /admin/menu` — salva nova ordem/estrutura

```sql
menu_configs: id, tenant_id FK, role ENUM('student','manager','admin'),
              items JSONB, updated_at
-- items: [{id, label, icon, url, order, group, visible}]
```

---

## 9. Módulo de Gamificação Corporativa

### 9.1 Visão Geral

Módulo ativável por tenant, configurável por empresa cliente. Três camadas:

- **Individual**: XP, níveis, badges, streaks
- **Coletivo**: ranking de times, metas coletivas
- **Inter-empresas**: liga entre empresas (argumento comercial do tenant)

**Isolamento de dados na gamificação:**
- Todos os endpoints de ranking, XP, badges e streaks recebem `company_id` (via path ou query param)
- Backend valida `company.tenant_id = current_tenant.id` antes de retornar qualquer dado
- Rankings não expõem usuários de outras empresas — leaderboard filtrado por `company_id` obrigatoriamente
- Liga entre empresas: empresas veem sua posição relativa no ranking mas **nunca** os dados individuais de funcionários de outras empresas

---

### 9.2 XP e Níveis

Funcionários acumulam XP ao realizar ações. Nunca perdem XP. Tenant personaliza nomes de níveis e limites de XP por empresa.

**Ações que geram XP (configurável):**

| Ação | XP padrão |
|---|---|
| Concluir aula | 10 |
| Completar módulo | 50 |
| Completar curso | 200 |
| Fazer anotação | 5 |
| Comentar na comunidade | 8 |
| Responder dúvida de colega | 15 |
| Participar de quiz battle | 20 |
| Manter streak (por dia) | 5 × multiplicador |

```sql
xp_events: id, tenant_id FK, user_id FK, company_id FK NULLABLE,
           action VARCHAR, xp_awarded INT,
           reference_id UUID, reference_type VARCHAR,
           created_at

user_levels: id, tenant_id FK, user_id FK, company_id FK NULLABLE,
             total_xp INT DEFAULT 0, current_level INT DEFAULT 1,
             updated_at
```

---

### 9.3 Badges e Conquistas

Quatro categorias: **comportamento**, **conclusão**, **social**, **eventos de tempo limitado**.  
Raridade: comum, raro, épico, lendário.

**Exemplos:**
- Madrugador (estudou antes das 8h)
- Consistente (7 dias seguidos)
- Mentor (respondeu 20 dúvidas)
- Velocista (concluiu curso em tempo recorde)

```sql
badges: id, tenant_id FK, name, description, icon_url,
        category ENUM('behavior','completion','social','event'),
        rarity ENUM('common','rare','epic','legendary'),
        rule_event VARCHAR, rule_conditions JSONB, is_active

user_badges: id, user_id FK, badge_id FK, awarded_at, UNIQUE(user_id, badge_id)
```

---

### 9.4 Streaks

Dias consecutivos de estudo com multiplicadores de XP. Escudos de streak protegem a sequência em dias sem acesso. Quebrar streak nunca penaliza XP — apenas reinicia contador.

```sql
user_streaks: id, user_id FK, company_id FK NULLABLE,
              current_streak INT DEFAULT 0,
              longest_streak INT DEFAULT 0,
              last_activity_date DATE,
              shields_available INT DEFAULT 0,
              updated_at
```

---

### 9.5 Ranking de Times e Metas Coletivas

- Times criados pela empresa dentro da plataforma
- Ranking calculado por XP médio ou % de conclusão no período
- Metas coletivas: "80% do time conclui módulo X até [data]" — todos ganham badge ao atingir

**Critério de aceite:** Gestora cria meta coletiva em menos de 3 minutos e acompanha progresso em tempo real.

---

### 9.6 Quiz Battle

Duelos de quiz entre colegas sobre conteúdo de um curso.  
- Modo assíncrono (24h para responder) ou tempo real
- Vencedor ganha XP extra e badge de duelo

```sql
quiz_battles: id, tenant_id FK, challenger_id FK, challenged_id FK,
              course_id FK, status ENUM('pending','active','completed','expired'),
              mode ENUM('async','realtime'),
              winner_id FK NULLABLE, created_at, expires_at

quiz_battle_answers: id, battle_id FK, user_id FK,
                     question_id FK, answer_index INT,
                     is_correct BOOLEAN, answered_at
```

---

### 9.7 Eventos Especiais

Tenant ou empresa cria eventos com janela de tempo e XP em dobro. Badges exclusivos disponíveis apenas durante o evento.

```sql
special_events: id, tenant_id FK, company_id FK NULLABLE,
                name, description, xp_multiplier DECIMAL DEFAULT 2.0,
                starts_at, ends_at, badge_id FK NULLABLE, is_active
```

---

### 9.8 Liga entre Empresas

Tenant cria ligas agrupando empresas clientes. Ranking por índice de engajamento médio. Empresas veem posição relativa sem ver dados das concorrentes (benchmark anônimo).

```sql
leagues: id, tenant_id FK, name, season VARCHAR,
         starts_at DATE, ends_at DATE, is_active

league_companies: league_id FK, company_id FK,
                  rank INT, engagement_score DECIMAL, updated_at
```

---

### 9.9 Hall da Fama e Feed de Conquistas

- Top 3 funcionários do mês por empresa, exibido publicamente
- Feed automático ao concluir curso, subir de nível ou ganhar badge raro
- Empresa pode desativar feed se preferir privacidade

---

## 10. Fora do Escopo do MVP

Arquitetura deve ser preparada para suportar futuramente:

- Certificados digitais com validação
- Quizzes e provas formais com gabarito automático
- Gamificação com cartas colecionáveis
- Mapa de jornada visual estilo RPG
- Busca semântica por transcrição via pgvector
- Chat contextual por curso com IA
- Afiliados e split de receita
- App mobile nativo (iOS/Android)
- SSO e login social (Google, Microsoft)
- CRM interno avançado e automações complexas
- Marketplace de plugins
- Quizzes inline nas aulas (estrutura de banco preparada)

---

## 11. Stack Tecnológica

### Backend

| Camada | Tecnologia | Justificativa |
|---|---|---|
| Framework | **FastAPI** | Performance async, OpenAPI automático, tipagem nativa |
| Banco de dados | **PostgreSQL 16** | Relacional, JSONB para dados flexíveis |
| ORM / Migrations | **SQLAlchemy 2.x + Alembic** | Async sessions, migrations versionadas |
| Autenticação | **JWT (python-jose) + bcrypt** | Access token 15min + Refresh token 30d |
| Cache / Sessões | **Redis 7** | Cache de permissões, presença online, pub/sub |
| Filas assíncronas | **Celery + Redis** | Envio de emails, webhooks, transcrições |
| Real-time | **WebSocket nativo FastAPI** | Presença, notificações, mensageria |
| Storage | **Cloudflare R2 (S3-compatible)** | Thumbnails, imagens, uploads |
| Vídeos | **Bunny.net API** | Streaming barato; import em massa via API |
| Transcrição | **AssemblyAI API** | Transcrição com timestamps |
| IA (resumos + moderação) | **Claude Haiku (Anthropic API)** | Resumos de aulas, moderação de conteúdo |
| Email transacional | **Resend** | SMTP, alta entregabilidade |
| Validação | **Pydantic v2** | Schema validation em todos os endpoints |
| Testes | **pytest + pytest-asyncio + httpx** | Integração com DB real (não mock) |
| Containerização | **Docker + Docker Compose** | Ambiente reproduzível |

### Frontend

| Camada | Tecnologia | Justificativa |
|---|---|---|
| Framework | **React 19 + Vite** | Fast refresh, build rápido |
| Roteamento | **React Router v7** | File-based routing, loaders nativos, nested layouts |
| Estado global | **Zustand** | Simples, sem boilerplate, persiste em localStorage |
| Server state | **TanStack Query v5** | Cache, refetch, optimistic updates |
| Formulários | **React Hook Form + Zod** | Validação isomórfica |
| Estilização | **Tailwind CSS v4 + shadcn/ui** | Componentes acessíveis, customizáveis |
| Player de vídeo | **HLS.js** | Streaming adaptativo via m3u8 do Bunny.net |
| Editor de texto | **Tiptap** | Rich text para posts, anotações, templates de email |
| Editor de código | **Monaco Editor** | Editor de landing pages (syntax highlight JSX) |
| Drag & Drop | **dnd-kit** | Reordenação de aulas, menu dinâmico |
| Gráficos | **Recharts** | Dashboard admin, analytics |
| WebSocket | **hook customizado nativo** | Presença, mensageria, notificações |
| Uploads | **react-dropzone + axios** | Upload direto para R2 com progress bar |
| HTTP client | **axios** | Interceptors para refresh token automático |
| Ícones | **Lucide React** | Consistente, tree-shakeable |
| Datas | **date-fns** | Leve, sem Moment.js |

---

## 12. Arquitetura do Sistema

### 12.1 Estrutura de Pastas (Backend)

```
backend/
├── app/
│   ├── main.py                  # FastAPI app, routers, middleware
│   ├── core/
│   │   ├── config.py            # Settings via pydantic-settings (.env)
│   │   ├── security.py          # JWT encode/decode, bcrypt, magic link
│   │   ├── dependencies.py      # get_current_user, require_admin, require_tenant, require_company_access
│   │   └── database.py          # Async SQLAlchemy engine + session
│   ├── models/                  # SQLAlchemy ORM models
│   ├── schemas/                 # Pydantic v2 request/response schemas
│   ├── routers/                 # Um arquivo por domínio
│   │   ├── auth.py
│   │   ├── courses.py
│   │   ├── enrollments.py
│   │   ├── webhooks.py
│   │   ├── community.py
│   │   ├── messages.py
│   │   ├── notifications.py
│   │   ├── gamification.py
│   │   ├── companies.py
│   │   ├── email_marketing.py
│   │   ├── landing_pages.py
│   │   └── admin.py
│   ├── services/                # Lógica de negócio desacoplada dos routers
│   ├── tasks/                   # Celery tasks
│   │   ├── email.py
│   │   ├── webhooks.py
│   │   ├── transcription.py
│   │   ├── gamification.py      # XP, badges, streaks
│   │   └── moderation.py
│   ├── integrations/
│   │   ├── bunny.py
│   │   ├── assemblyai.py
│   │   ├── resend.py
│   │   ├── anthropic.py
│   │   └── webhooks/            # Parsers: hotmart.py, kiwify.py, greenn.py, etc.
│   └── websockets/              # Handlers de presence, mensageria, notificações
├── alembic/                     # Migrations
├── tests/
│   ├── integration/             # Testes com DB real
│   ├── unit/
│   └── conftest.py
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

### 12.2 Estrutura de Pastas (Frontend)

```
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx                        # Router + Providers
│   ├── routes/
│   │   ├── (auth)/
│   │   │   ├── login.tsx
│   │   │   ├── register.tsx
│   │   │   ├── magic-link.tsx
│   │   │   └── forgot-password.tsx
│   │   ├── (student)/                 # Layout com sidebar do aluno
│   │   │   ├── dashboard.tsx
│   │   │   ├── courses/
│   │   │   │   ├── index.tsx
│   │   │   │   └── [slug]/
│   │   │   │       ├── index.tsx
│   │   │   │       └── [lessonId].tsx  # Player + notas + transcrição
│   │   │   ├── community/
│   │   │   │   ├── [channel].tsx
│   │   │   │   └── post/[id].tsx
│   │   │   ├── messages/
│   │   │   │   ├── index.tsx
│   │   │   │   └── [conversationId].tsx
│   │   │   ├── gamification/
│   │   │   │   ├── ranking.tsx
│   │   │   │   ├── badges.tsx
│   │   │   │   └── battles.tsx
│   │   │   ├── members.tsx
│   │   │   ├── subscription.tsx
│   │   │   └── settings.tsx
│   │   ├── (manager)/                 # Layout para gestor de RH
│   │   │   ├── dashboard.tsx
│   │   │   ├── members.tsx
│   │   │   ├── goals.tsx
│   │   │   └── reports.tsx
│   │   ├── (admin)/                   # Layout com sidebar do admin
│   │   │   ├── dashboard.tsx
│   │   │   ├── users/
│   │   │   ├── companies/
│   │   │   ├── courses/
│   │   │   │   └── [id]/
│   │   │   │       ├── edit.tsx
│   │   │   │       └── modules.tsx    # Drag-and-drop
│   │   │   ├── enrollments/
│   │   │   ├── community/
│   │   │   ├── gamification/
│   │   │   │   ├── badges.tsx
│   │   │   │   ├── events.tsx
│   │   │   │   └── leagues.tsx
│   │   │   ├── landing-pages/
│   │   │   │   └── [id]/
│   │   │   │       ├── editor.tsx
│   │   │   │       └── analytics.tsx
│   │   │   ├── email/
│   │   │   │   ├── campaigns.tsx
│   │   │   │   ├── templates.tsx
│   │   │   │   └── automations.tsx
│   │   │   ├── webhooks/
│   │   │   ├── online-users.tsx
│   │   │   ├── leads.tsx
│   │   │   ├── menu-builder.tsx
│   │   │   └── tenant/
│   │   │       ├── branding.tsx
│   │   │       └── settings.tsx
│   │   └── p/
│   │       └── [slug].tsx             # Landing pages públicas
│   ├── components/
│   │   ├── ui/                        # shadcn/ui re-exports
│   │   ├── layout/
│   │   │   ├── StudentSidebar.tsx
│   │   │   ├── ManagerSidebar.tsx
│   │   │   ├── AdminSidebar.tsx
│   │   │   └── Header.tsx
│   │   ├── player/
│   │   │   ├── VideoPlayer.tsx        # HLS.js + controles customizados
│   │   │   └── TranscriptPanel.tsx    # Scroll sincronizado com timestamp
│   │   ├── community/
│   │   │   ├── PostCard.tsx
│   │   │   ├── PostEditor.tsx         # Tiptap
│   │   │   └── ReportModal.tsx
│   │   ├── chat/
│   │   │   ├── ConversationList.tsx
│   │   │   └── MessageBubble.tsx
│   │   ├── gamification/
│   │   │   ├── XPBar.tsx
│   │   │   ├── BadgeCard.tsx
│   │   │   ├── Leaderboard.tsx
│   │   │   ├── StreakWidget.tsx
│   │   │   └── QuizBattle.tsx
│   │   └── admin/
│   │       ├── DataTable.tsx
│   │       ├── BulkActions.tsx
│   │       └── BunnyImporter.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useWebSocket.ts
│   │   ├── usePresence.ts
│   │   └── useNotifications.ts
│   ├── lib/
│   │   ├── api.ts                     # Axios + interceptors
│   │   ├── queryClient.ts
│   │   └── utils.ts
│   └── types/
├── vite.config.ts
├── tailwind.config.ts
└── .env.example
```

### 12.3 Decisões de Design

- **Async everywhere:** SQLAlchemy com `asyncpg`, Celery para tarefas pesadas. Nenhuma operação I/O bloqueante no request/response cycle.
- **Multi-tenancy via `tenant_id`:** Toda tabela com dados de usuário/conteúdo tem `tenant_id`. Dependency injection do FastAPI injeta e valida o tenant em cada request.
- **JSONB para flexibilidade:** `menu_configs.items`, `webhook_logs.payload`, `transcript_text`, `email_automations.steps`, `badges.rule_conditions` — evita migrations frequentes.
- **WebSocket + Redis Pub/Sub:** mensagens e presença usam canal Redis como broker. Múltiplas instâncias do servidor sem estado compartilhado em memória.
- **Presença via Redis TTL:** sem coluna `is_online` no banco. Key TTL 60s. Para sem heartbeat → some automaticamente.
- **Webhook via fila:** retorna 200 imediatamente, processamento no Celery — evita timeout e retry duplicado dos providers.
- **Busca em transcrições via PostgreSQL FTS:** `tsvector` com índice GIN. Zero infra extra. Migrar para `pgvector` quando precisar de semântica.
- **Adapter pattern para gateways:** cada gateway tem parser próprio em `integrations/webhooks/`. Adicionar novo gateway = novo arquivo, zero mudança no core.

---

## 13. Requisitos Não Funcionais

### 13.1 Performance

- Tempo de carregamento da primeira tela: < 2 segundos em conexão 4G
- API: p95 abaixo de 300ms para endpoints principais
- Suporte a 10.000 usuários ativos simultâneos por tenant no lançamento

### 13.2 Disponibilidade

- SLA de 99,5% de uptime para o MVP
- Processamento de webhooks com retry automático (backoff exponencial)
- WebSocket com reconexão automática no frontend

### 13.3 Segurança

- Senhas com bcrypt (cost factor 12) — nunca armazenadas em texto puro
- Tokens JWT com expiração curta (15min) e refresh token com revogação imediata
- Magic link com TTL 15min e uso único
- Rate limiting via Redis (slowapi) em login, magic link e endpoints críticos
- Validação de assinatura HMAC em todos os webhooks antes de qualquer processamento
- Proteção contra IDOR — dois níveis obrigatórios:
  - `tenant_id` validado em todos os endpoints (nenhum recurso vaza entre tenants)
  - `company_id` validado em todos os endpoints que operam sobre recursos corporativos — enviado explicitamente na request e verificado no backend contra o tenant do usuário autenticado
- Manager só acessa recursos da sua própria `company_id` (extraída do JWT, não do body)
- Admin do tenant acessa todas as companies do seu tenant, nunca de outros tenants
- Super admin acessa qualquer tenant, mas apenas via endpoints exclusivos prefixados `/superadmin/`
- Sanitização de HTML em posts e comentários (DOMPurify no frontend, bleach no backend)
- CORS com whitelist de origens por tenant
- Bunny video URLs via signed token (TTL 2h) — nunca URL raw exposta
- Uploads: validar content-type + tamanho máximo (10MB) antes de subir para R2
- Todas rotas `/admin/*` exigem `role = 'admin'` no JWT
- Logs de auditoria para ações administrativas críticas

### 13.4 Acessibilidade e Dispositivos

- Interface responsiva mobile-first (PWA)
- Funciona em Chrome, Safari, Firefox — versões dos últimos 2 anos
- PWA instalável em Android e iOS
- Controles de vídeo touch-friendly
- Skeleton loaders em todas as queries (evita layout shift)

### 13.5 Privacidade e Conformidade

- Dados de usuários isolados por tenant
- Suporte a exclusão de conta e portabilidade de dados (LGPD)
- Logs de auditoria para ações administrativas críticas

---

## 14. Métricas de Sucesso

### 14.1 Saúde do Produto (Tenants)

| Métrica | Meta MVP (6 meses) |
|---|---|
| Tenants ativos | 10 |
| Empresas clientes cadastradas | 50 |
| Funcionários com acesso ativo | 5.000 |
| Churn mensal de tenants | < 5% |
| NPS dos tenants | > 40 |
| Tempo de onboarding de novo tenant | < 1 dia |

### 14.2 Engajamento dos Funcionários

| Métrica | Meta |
|---|---|
| DAU / MAU (stickiness) | > 20% |
| Taxa de conclusão de cursos | > 40% |
| Funcionários com streak ativo (7+ dias) | > 30% dos ativos |
| Duelos de quiz por semana | > 1 por usuário ativo |
| Taxa de abertura de notificação push | > 25% |
| Posts na comunidade por usuário ativo/mês | > 2 |

### 14.3 Negócio

| Métrica | Meta |
|---|---|
| Tempo para liberar acesso após pagamento | < 60 segundos |
| CSAT do suporte | > 4,0 / 5,0 |
| MRR ao final do MVP | Definir com time comercial |
| Taxa de reprocessamento de webhook | < 1% |

---

## 15. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Baixo engajamento com gamificação | Média | Alto | Pesquisa com 5 empresas antes do lançamento; gamificação opt-in por empresa |
| Bugs de isolamento multi-tenant | Alta | Crítico | Testes de isolamento automatizados obrigatórios; `tenant_id` em todas as queries |
| Gateway externo muda API e quebra webhooks | Média | Alto | Adapter pattern por gateway; testes de contrato; replay manual |
| Escalabilidade insuficiente ao crescer | Baixa | Alto | Índices compostos `(tenant_id, ...)` em todas as tabelas principais; sharding preparado |
| Gestoras de RH não adotam painel | Média | Médio | UX focada em simplicidade; onboarding guiado; tooltips contextuais |
| Custo de IA crescer com escala | Média | Médio | Claude Haiku para tarefas em volume; cache de resumos no banco |
| Concorrente similar durante desenvolvimento | Baixa | Médio | Foco em velocidade do MVP; diferenciais de gamificação corporativa e marketing integrado |

---

## 16. Roadmap de Lançamento

### Fase 1 — Base (Meses 1–2)

**Objetivo:** plataforma funcional para tenant e aluno individual.

- Autenticação completa (senha + magic link + refresh rotativo)
- Multi-tenancy com branding básico
- Cursos, módulos e aulas com integração Bunny.net
- Matrículas manuais e por webhook (Hotmart, Kiwify, Greenn)
- Portal do aluno (progresso, notas com timestamp)
- Painel admin básico com dashboard
- Menu dinâmico por role

**Marco:** Primeiro tenant cadastra e vende um curso.

---

### Fase 2 — Valor Comercial B2B (Meses 3–4)

**Objetivo:** habilitar modelo corporativo.

- Cadastro de empresas clientes (CNPJ, licenças, importação CSV)
- Role de Manager (gestor de RH) com painel próprio
- Drip content por seção e por aula
- Presença online em tempo real
- Vitrine pública e landing pages com analytics
- Email marketing: templates, campanhas, automações básicas
- Transcrição automática e resumo por IA das aulas
- Integração Stripe e Monetizze

**Marco:** Primeiro cliente corporativo com 100+ funcionários usando a plataforma.

---

### Fase 3 — Retenção e Engajamento (Meses 5–6)

**Objetivo:** aumentar stickiness.

- Gamificação V1: XP, níveis, badges, streaks, leaderboard
- Comunidade: espaços, canais, posts, comentários, moderação por IA
- Mensageria direta entre usuários
- Notificações push via PWA
- Metas coletivas e ranking de times
- Analytics avançado (DAU/WAU/MAU, conclusão, receita)

**Marco:** DAU/MAU acima de 20% nos clientes com gamificação ativa.

---

### Fase 4 — Escala e Diferenciação (Meses 7–9)

**Objetivo:** consolidar produto e preparar para crescimento.

- Quiz Battle (assíncrono e tempo real)
- Liga entre empresas
- Eventos especiais com XP em dobro
- Hall da Fama e feed de conquistas
- Builder de landing pages mais avançado
- Dashboards operacionais avançados para o tenant
- Automações de email complexas (branching por comportamento)

**Marco:** 10 tenants ativos com pelo menos 1 empresa cliente cada.

---

## 17. Variáveis de Ambiente

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/lms

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
MAGIC_LINK_EXPIRE_MINUTES=15

# Bunny.net
BUNNY_API_KEY=
BUNNY_STORAGE_ZONE=
BUNNY_CDN_HOSTNAME=
BUNNY_STREAM_LIBRARY_ID=

# AssemblyAI
ASSEMBLYAI_API_KEY=

# Resend
RESEND_API_KEY=
RESEND_FROM_EMAIL=

# Cloudflare R2
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
R2_PUBLIC_URL=

# Gateways (HMAC secrets)
HOTMART_WEBHOOK_SECRET=
KIWIFY_WEBHOOK_SECRET=
GREENN_WEBHOOK_SECRET=
MONETIZZE_WEBHOOK_SECRET=
STRIPE_WEBHOOK_SECRET=

# Anthropic (moderação + resumos)
ANTHROPIC_API_KEY=

# App
FRONTEND_URL=
WEBHOOK_TEST_MODE=false
```

---

## 18. Perguntas em Aberto

1. **Precificação do tenant:** por aluno ativo, por empresa cadastrada ou plano flat?
2. **Certificados:** parte do MVP ou pós-MVP? Impacta modelagem de banco.
3. **Quizzes e provas:** avaliações formais com gabarito no MVP? Define prioridade.
4. **i18n:** suporte a múltiplos idiomas desde o MVP?
5. **SLA de webhook:** tempo máximo aceitável para processar evento de compra?
6. **LGPD:** necessidade de DPO para operar B2B com dados de funcionários de terceiros?
7. **Moderação de comunidade:** manual (admin), automática (IA) ou híbrida?
8. **Gamificação B2C:** mesmas mecânicas corporativas funcionam para alunos individuais?
9. **Limite de armazenamento de vídeo por tenant:** cobrar por GB via Bunny ou tarifa flat?
10. **Quizzes inline nas aulas:** quiz integrado ao player é MVP ou fase 2?
