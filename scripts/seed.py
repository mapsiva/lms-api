import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.append(str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.core.config import get_settings
from app.core.security import hash_password
from app.models.audit import AuditLog
from app.models.community import Channel, Comment, Post, PostLike, Space
from app.models.company import Company, CompanyGoal, CompanyMember
from app.models.course import Course, Lesson, Module
from app.models.email import EmailAudience, EmailAutomation, EmailCampaign, EmailSend, EmailTemplate
from app.models.enrollment import Enrollment
from app.models.gamification import Badge, UserBadge, UserLevel, UserStreak, XPEvent
from app.models.landing_page import LandingPage, PageView
from app.models.menu import MenuConfig
from app.models.messaging import Conversation, ConversationParticipant, Message
from app.models.notification import Notification
from app.models.product import Product, ProductCourse, ProductSpace
from app.models.progress import LessonProgress, Note
from app.models.quiz import QuizBattle, QuizBattleAnswer
from app.models.tenant import Tenant
from app.models.user import User
from app.models.webhook import Lead, WebhookLog

PASSWORD = "Senha123!"
NOW = datetime.now(timezone.utc)

STUDENT_MENU = [
    {"id": "courses", "label": "Cursos", "icon": "book", "url": "/courses", "order": 1, "group": "principal", "visible": True},
    {"id": "community", "label": "Comunidade", "icon": "message-circle", "url": "/community", "order": 2, "group": "principal", "visible": True},
    {"id": "profile", "label": "Perfil", "icon": "user", "url": "/profile", "order": 3, "group": "principal", "visible": True},
]
MANAGER_MENU = [
    {"id": "dashboard", "label": "Dashboard", "icon": "bar-chart", "url": "/manager", "order": 0, "group": "principal", "visible": True},
    *STUDENT_MENU,
]
ADMIN_MENU = [
    *MANAGER_MENU,
    {"id": "admin", "label": "Admin", "icon": "settings", "url": "/admin", "order": 10, "group": "admin", "visible": True},
]


async def one_or_create(db: AsyncSession, model, where: tuple, **values):
    result = await db.execute(select(model).where(*where))
    item = result.scalar_one_or_none()
    if item:
        for k, v in values.items():
            setattr(item, k, v)
        return item, False
    item = model(id=uuid.uuid4(), **values)
    db.add(item)
    await db.flush()
    return item, True


# ─── Tenant ───────────────────────────────────────────────────────────────────

async def seed_tenant(db: AsyncSession) -> Tenant:
    tenant, _ = await one_or_create(
        db, Tenant, (Tenant.slug == "acme",),
        slug="acme", name="Acme Learning", custom_domain="localhost",
        subdomain="acme.localhost", app_name="Acme Learning",
        primary_color="#2563EB", secondary_color="#16A34A", font_family="Inter",
        plan="pro",
        features={"community": True, "gamification": True, "companies": True, "analytics": True},
    )
    for role, items in (("student", STUDENT_MENU), ("manager", MANAGER_MENU), ("admin", ADMIN_MENU)):
        await one_or_create(
            db, MenuConfig,
            (MenuConfig.tenant_id == tenant.id, MenuConfig.role == role),
            tenant_id=tenant.id, role=role, items=items,
        )
    return tenant


# ─── Companies ────────────────────────────────────────────────────────────────

COMPANY_SPECS = [
    ("12.345.678/0001-90", "Acme Comercial Ltda",      "Acme Comercial",      80,  -45,  320),
    ("98.765.432/0001-11", "Beta Vendas Ltda",          "Beta Vendas",         40,  -20,  280),
    ("55.123.456/0001-22", "Gamma Tech S.A.",            "Gamma Tech",          60,  -60,  240),
    ("33.987.654/0001-33", "Delta Servicos Ltda",        "Delta Servicos",      30,  -10,  180),
]

async def seed_companies(db: AsyncSession, tenant: Tenant) -> list[Company]:
    companies = []
    for cnpj, legal, trade, seats, start_offset, end_offset in COMPANY_SPECS:
        c, _ = await one_or_create(
            db, Company,
            (Company.tenant_id == tenant.id, Company.legal_name == legal),
            tenant_id=tenant.id, cnpj=cnpj, legal_name=legal, trade_name=trade,
            max_seats=seats, status="active",
            contract_start=NOW + timedelta(days=start_offset),
            contract_end=NOW + timedelta(days=end_offset),
        )
        companies.append(c)
    return companies


# ─── Users ────────────────────────────────────────────────────────────────────

async def seed_users(db: AsyncSession, tenant: Tenant, companies: list[Company]) -> dict[str, User]:
    legacy = await db.execute(
        select(User).where(User.tenant_id == tenant.id, User.email.like("%@acme.test"))
    )
    for u in legacy.scalars():
        await db.delete(u)
    await db.flush()

    users: dict[str, User] = {}

    # 1 admin
    u, _ = await one_or_create(
        db, User, (User.tenant_id == tenant.id, User.email == "admin@acmelearning.com"),
        tenant_id=tenant.id, email="admin@acmelearning.com", name="Ana Admin",
        password_hash=hash_password(PASSWORD), role="admin",
        company_id=None, is_active=True, is_suspended=False,
        bio="Admin da plataforma Acme Learning.",
    )
    users["admin@acmelearning.com"] = u

    # managers — one per company
    manager_specs = [
        ("manager@acmelearning.com",  "Marcos Manager",   companies[0]),
        ("gerente@betavendas.com",     "Giulia Gerente",   companies[1]),
        ("lider@gammatech.com",        "Lucas Lider",      companies[2]),
        ("coord@deltaservicos.com",    "Clara Coord",      companies[3]),
    ]
    for email, name, company in manager_specs:
        u, _ = await one_or_create(
            db, User, (User.tenant_id == tenant.id, User.email == email),
            tenant_id=tenant.id, email=email, name=name,
            password_hash=hash_password(PASSWORD), role="manager",
            company_id=company.id, is_active=True, is_suspended=False,
            bio=f"Gestor do time em {company.trade_name}.",
        )
        users[email] = u

    # students — 4 per company = 16 students total
    student_specs = [
        # company 0
        ("aluno@acmelearning.com",      "Bruna Aluna",      companies[0], "Focada em vendas consultivas."),
        ("aluno2@acmelearning.com",     "Diego Aluno",      companies[0], "Especialista em atendimento."),
        ("pedro@acmelearning.com",      "Pedro Silva",      companies[0], "SDR em ramp-up."),
        ("julia@acmelearning.com",      "Julia Ramos",      companies[0], "AE com foco em enterprise."),
        # company 1
        ("ana@betavendas.com",          "Ana Souza",        companies[1], "Vendedora inside sales."),
        ("carlos@betavendas.com",       "Carlos Lima",      companies[1], "Key account manager."),
        ("fernanda@betavendas.com",     "Fernanda Cruz",    companies[1], "BDR prospeccao outbound."),
        ("rafael@betavendas.com",       "Rafael Mendes",    companies[1], "Sales engineer."),
        # company 2
        ("tatiane@gammatech.com",       "Tatiane Pires",    companies[2], "CS especialista."),
        ("rodrigo@gammatech.com",       "Rodrigo Alves",    companies[2], "Tech lead onboarding."),
        ("camila@gammatech.com",        "Camila Nunes",     companies[2], "Implementation manager."),
        ("vitor@gammatech.com",         "Vitor Castelo",    companies[2], "Support engineer."),
        # company 3
        ("leticia@deltaservicos.com",   "Leticia Faria",    companies[3], "Coordenadora de projetos."),
        ("thiago@deltaservicos.com",    "Thiago Borges",    companies[3], "Analista de processos."),
        ("mariana@deltaservicos.com",   "Mariana Vieira",   companies[3], "Especialista em qualidade."),
        ("gustavo@deltaservicos.com",   "Gustavo Teixeira", companies[3], "Consultor de negocios."),
    ]
    for email, name, company, bio in student_specs:
        u, _ = await one_or_create(
            db, User, (User.tenant_id == tenant.id, User.email == email),
            tenant_id=tenant.id, email=email, name=name,
            password_hash=hash_password(PASSWORD), role="student",
            company_id=company.id, is_active=True, is_suspended=False, bio=bio,
        )
        users[email] = u

    return users


# ─── Company members & goals ──────────────────────────────────────────────────

async def seed_company_members(
    db: AsyncSession,
    companies: list[Company],
    users: dict[str, User],
) -> None:
    members_by_company = [
        # company 0
        [
            ("manager@acmelearning.com", "Comercial", "Sales Manager"),
            ("aluno@acmelearning.com",   "Comercial", "Account Executive"),
            ("aluno2@acmelearning.com",  "Atendimento", "Customer Support"),
            ("pedro@acmelearning.com",   "Comercial", "SDR"),
            ("julia@acmelearning.com",   "Comercial", "Account Executive"),
        ],
        # company 1
        [
            ("gerente@betavendas.com",   "Vendas", "Sales Manager"),
            ("ana@betavendas.com",       "Vendas", "Inside Sales"),
            ("carlos@betavendas.com",    "Vendas", "Key Account"),
            ("fernanda@betavendas.com",  "Prospeccao", "BDR"),
            ("rafael@betavendas.com",    "Pre-venda", "Sales Engineer"),
        ],
        # company 2
        [
            ("lider@gammatech.com",      "CS", "CS Lead"),
            ("tatiane@gammatech.com",    "CS", "CS Specialist"),
            ("rodrigo@gammatech.com",    "Tech", "Tech Lead"),
            ("camila@gammatech.com",     "Implementation", "Impl. Manager"),
            ("vitor@gammatech.com",      "Support", "Support Engineer"),
        ],
        # company 3
        [
            ("coord@deltaservicos.com",  "Projetos", "Coordinator"),
            ("leticia@deltaservicos.com","Projetos", "Project Manager"),
            ("thiago@deltaservicos.com", "Processos", "Process Analyst"),
            ("mariana@deltaservicos.com","Qualidade", "Quality Specialist"),
            ("gustavo@deltaservicos.com","Negocios", "Business Consultant"),
        ],
    ]

    goals_by_company = [
        ("Concluir onboarding comercial", "completion_rate", 80, 30),
        ("Certificar equipe de vendas",   "completion_rate", 90, 45),
        ("Meta de engajamento Q2",        "enrollments",     50, 60),
        ("Formacao de consultores",       "completion_rate", 75, 90),
    ]

    for i, (company, members) in enumerate(zip(companies, members_by_company)):
        for email, team, job_role in members:
            if email not in users:
                continue
            await one_or_create(
                db, CompanyMember,
                (CompanyMember.company_id == company.id, CompanyMember.user_id == users[email].id),
                company_id=company.id, user_id=users[email].id,
                team=team, job_role=job_role, is_active=True,
            )

        title, metric, target, days = goals_by_company[i]
        await one_or_create(
            db, CompanyGoal,
            (CompanyGoal.company_id == company.id, CompanyGoal.title == title),
            company_id=company.id, title=title,
            target_metric=metric, target_value=target,
            course_id=None, deadline=NOW + timedelta(days=days), status="active",
        )


# ─── Courses ──────────────────────────────────────────────────────────────────

COURSE_SPECS = [
    (
        "Onboarding Comercial B2B",
        "onboarding-comercial-b2b",
        "Fundamentos para ramp-up de novos vendedores B2B.",
        "https://images.unsplash.com/photo-1556761175-4b46a572b786",
        [
            ("Fundamentos", ["Visao geral do playbook", "ICP e qualificacao", "Cadencia de prospeccao"]),
            ("Execucao",    ["Diagnostico consultivo", "Proposta de valor", "Follow-up e fechamento"]),
        ],
    ),
    (
        "Customer Success na Pratica",
        "customer-success-na-pratica",
        "Rotinas para onboarding, expansao e retencao de clientes.",
        "https://images.unsplash.com/photo-1552664730-d307ca884978",
        [
            ("Operacao de CS",  ["Jornada do cliente", "Health score", "Ritos de QBR"]),
            ("Crescimento",     ["Playbooks de expansao", "Gestao de churn", "Comunidade de clientes"]),
        ],
    ),
    (
        "Negociacao Avancada",
        "negociacao-avancada",
        "Tecnicas de negociacao para fechar contratos complexos.",
        "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40",
        [
            ("Preparacao",  ["Mapeamento de stakeholders", "BATNA e ZOPA", "Ancoragem de preco"]),
            ("Conducao",    ["Gestao de objecoes", "Concessoes estrategicas", "Fechamento win-win"]),
        ],
    ),
    (
        "Gestao de Pipeline",
        "gestao-de-pipeline",
        "Metodologia para construir e gerir pipeline de vendas previsivel.",
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71",
        [
            ("Construcao",  ["Prospeccao multicanal", "Qualificacao MEDDIC", "Forecasting"]),
            ("Gestao",      ["Revisao de pipeline", "Deal coaching", "CRM best practices"]),
        ],
    ),
    (
        "Lideranca de Times Comerciais",
        "lideranca-times-comerciais",
        "Como construir, motivar e escalar equipes de alta performance.",
        "https://images.unsplash.com/photo-1522071820081-009f0129c71c",
        [
            ("Recrutamento", ["Perfil ideal de vendedor", "Processo seletivo", "Onboarding de novos"]),
            ("Gestao",       ["1on1 efetivo", "Metas e compensacao", "Cultura de performance"]),
        ],
    ),
    (
        "Vendas Consultivas",
        "vendas-consultivas",
        "Abordagem centrada no cliente para vendas complexas B2B.",
        "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d",
        [
            ("Descoberta",  ["Escuta ativa", "SPIN Selling", "Mapeamento de dor"]),
            ("Solucao",     ["Prova de valor", "Business case", "Referencias e casos"]),
        ],
    ),
    (
        "Marketing e Vendas Integrados",
        "marketing-vendas-integrados",
        "Como alinhar marketing e vendas para gerar mais receita.",
        "https://images.unsplash.com/photo-1533750349088-cd871a92f312",
        [
            ("Alinhamento", ["SLA entre times", "Funil unificado", "Personas e ICP"]),
            ("Execucao",    ["ABM na pratica", "Conteudo para vendas", "Metricas compartilhadas"]),
        ],
    ),
    (
        "Analise de Dados para Vendas",
        "analise-dados-vendas",
        "Usando dados e metricas para tomar decisoes comerciais melhores.",
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71",
        [
            ("Fundamentos", ["KPIs essenciais", "Leitura de dashboards", "Cohort analysis"]),
            ("Aplicacao",   ["Previsao de churn", "Territorio e quota", "A/B testing em vendas"]),
        ],
    ),
]

async def seed_courses(db: AsyncSession, tenant: Tenant, instructor: User) -> tuple[list[Course], list[Lesson]]:
    courses: list[Course] = []
    lessons: list[Lesson] = []

    for title, slug, desc, thumb, modules in COURSE_SPECS:
        course, _ = await one_or_create(
            db, Course,
            (Course.tenant_id == tenant.id, Course.slug == slug),
            tenant_id=tenant.id, title=title, slug=slug, description=desc,
            thumbnail_url=thumb, status="published", is_free=False,
            certificate_enabled=True, instructor_id=instructor.id,
        )
        courses.append(course)

        for mi, (mod_title, lesson_titles) in enumerate(modules):
            module, _ = await one_or_create(
                db, Module,
                (Module.tenant_id == tenant.id, Module.course_id == course.id, Module.title == mod_title),
                tenant_id=tenant.id, course_id=course.id,
                title=mod_title, order_index=mi, is_hidden=False,
            )
            for li, lt in enumerate(lesson_titles):
                lesson, _ = await one_or_create(
                    db, Lesson,
                    (Lesson.tenant_id == tenant.id, Lesson.module_id == module.id, Lesson.title == lt),
                    tenant_id=tenant.id, module_id=module.id, title=lt,
                    order_index=li, lesson_type="video", is_hidden=False,
                    is_free_preview=(li == 0),
                    duration_seconds=480 + (li * 180),
                    video_provider="youtube", video_external_id="dQw4w9WgXcQ",
                    ai_summary=f"Resumo pratico: {lt.lower()}.",
                    transcript_text={"items": [{"text": f"Conteudo de {lt}."}]},
                )
                lessons.append(lesson)

    return courses, lessons


# ─── Community ────────────────────────────────────────────────────────────────

SPACE_SPECS = [
    ("Comunidade Comercial B2B",   "Exclusivo para alunos do Onboarding Comercial.", True),
    ("Comunidade Customer Success","Exclusivo para alunos de CS na Pratica.",         True),
    ("Comunidade Negociacao",      "Exclusivo para alunos de Negociacao Avancada.",    True),
    ("Comunidade Gestao de Time",  "Exclusivo para lideranca e gestores.",             True),
    ("Hub de Boas Praticas",       "Espaco aberto para compartilhar aprendizados.",    False),
    ("Espaco Livre",               "Discussoes gerais da plataforma.",                  False),
]

CHANNEL_SPECS_PER_SPACE = [
    # space 0
    [("Geral", "discussion", "open"), ("Avisos", "announcement", "admins"), ("Duvidas", "qna", "open"), ("Cases de Sucesso", "showcase", "open")],
    # space 1
    [("Geral", "discussion", "open"), ("Estrategias de CS", "discussion", "open"), ("Ferramentas", "qna", "open")],
    # space 2
    [("Geral", "discussion", "open"), ("Duvidas", "qna", "open"), ("Role-play", "showcase", "moderators")],
    # space 3
    [("Gestores", "discussion", "moderators"), ("Avisos", "announcement", "admins"), ("Benchmarks", "discussion", "open")],
    # space 4 (open)
    [("Boas Praticas", "discussion", "open"), ("Templates", "showcase", "open"), ("Ferramentas", "discussion", "open")],
    # space 5 (open)
    [("Apresentacoes", "discussion", "open"), ("Off-topic", "discussion", "open")],
]

POST_SPECS = [
    ("Como voces estruturam o primeiro contato com um lead?",
     "Compartilhem o script de abertura que funciona melhor para voces.",
     0, 0),  # space_idx, channel_idx
    ("Novo modulo de Execucao liberado!",
     "O modulo ja esta disponivel na plataforma. Bons estudos.",
     0, 1),
    ("Diferenca entre ICP e Persona",
     "Quando usar ICP vs Persona no processo comercial?",
     0, 2),
    ("Case: fechi deal de 6 digitos usando SPIN",
     "Quero compartilhar como apliquei SPIN Selling em uma venda enterprise.",
     0, 3),
    ("Health score: quais metricas voces monitoram?",
     "No nosso CS acompanhamos NPS, engajamento e uso de features. E voces?",
     1, 0),
    ("Ferramenta recomendada para QBR",
     "Estamos avaliando Notion vs Slides para os ritos de QBR. Sugestoes?",
     1, 2),
    ("Como lidar com silencio apos enviar proposta?",
     "Cliente sumiu depois da proposta. Qual o follow-up de voces?",
     2, 0),
    ("Duvida sobre BATNA em negociacao publica",
     "Como calcular BATNA quando o cliente e orgao publico?",
     2, 1),
    ("Template de 1on1 que uso com meu time",
     "Compartilho o template de 1on1 semanal que aumentou minha retencao.",
     3, 2),
    ("Meta de conversao realista para SDR outbound",
     "Qual taxa de conversao de cadencia para reuniao voces consideram saudavel?",
     4, 0),
    ("Stack de ferramentas de vendas 2025",
     "Lista atualizada das ferramentas que usamos: CRM, sequencer, enriquecimento.",
     4, 2),
    ("Ola a todos!",
     "Me chamo Bruna, sou AE no time comercial. Animada para aprender aqui!",
     5, 0),
    ("Dica de produtividade: blocos de prospecao",
     "Separo 2h manha e 2h tarde para prospecao. Mudou meu resultado.",
     4, 0),
    ("Livro recomendado: Never Split the Difference",
     "O livro do ex-negociador do FBI e obrigatorio para quem trabalha com vendas complexas.",
     4, 1),
    ("Podcast de vendas favorito",
     "Quais podcasts de vendas e CS voces recomendam? Aceito sugestoes em PT e EN.",
     5, 1),
    ("Erro que cometi na minha primeira negociacao",
     "Ancoro o preco muito baixo com medo de perder o deal. Aprendi da forma dificil.",
     2, 0),
    ("Como voces medem saude de conta no CS?",
     "Criamos um score composto com NPS + atividade + tickets. Funciona bem.",
     1, 0),
    ("Revisao de pipeline: frequencia ideal",
     "Fazemos revisao semanal com cada rep. Como e na empresa de voces?",
     0, 0),
    ("ABM: como priorizamos contas alvo",
     "Usamos firmografia + sinais de intencao para montar nossa lista de ABM.",
     4, 0),
    ("Duvida: como qualificar lead que nao tem budget agora",
     "Lead quer comprar mas budget so libera em Q3. Mantenho no pipeline?",
     0, 2),
]

COMMENT_TEXTS = [
    "Excelente ponto! Isso faz muito sentido na pratica.",
    "Obrigado por compartilhar. Vou aplicar na proxima semana.",
    "Concordo totalmente. Tive a mesma experiencia aqui.",
    "Voce pode detalhar um pouco mais? Fiquei curioso.",
    "Isso e ouro! Salvei para revisar antes da minha proxima reuniao.",
    "Boa pergunta. Na minha experiencia, depende muito do segmento.",
    "Ótima abordagem. Nós usamos algo similar com bons resultados.",
    "Discordo um pouco — acho que o timing importa mais que o script.",
    "Posso complementar: tambem usamos gatilhos comportamentais.",
    "Isso mudou minha forma de ver o processo. Obrigado!",
    "Vou levar esse template para o meu gestor. Muito util!",
    "No nosso contexto funciona diferente, mas a base e a mesma.",
    "Ja testei isso e funcionou muito bem em enterprise.",
    "Cuidado com esse approach em PME — o decisor e diferente.",
    "Perfeito para o momento que estou passando. Muito obrigado.",
]


async def seed_community(db: AsyncSession, tenant: Tenant, users: dict[str, User]) -> list[Space]:
    all_users = list(users.values())
    students = [u for u in all_users if u.role == "student"]
    managers = [u for u in all_users if u.role == "manager"]
    admin = users["admin@acmelearning.com"]

    spaces: list[Space] = []
    all_channels: list[list[Channel]] = []

    for si, (sname, sdesc, _) in enumerate(SPACE_SPECS):
        space, _ = await one_or_create(
            db, Space,
            (Space.tenant_id == tenant.id, Space.name == sname),
            tenant_id=tenant.id, name=sname, description=sdesc, is_active=True,
        )
        spaces.append(space)

        channels: list[Channel] = []
        for cname, ctype, policy in CHANNEL_SPECS_PER_SPACE[si]:
            ch, _ = await one_or_create(
                db, Channel,
                (Channel.tenant_id == tenant.id, Channel.space_id == space.id, Channel.name == cname),
                tenant_id=tenant.id, space_id=space.id,
                name=cname, channel_type=ctype, post_policy=policy, is_active=True,
            )
            channels.append(ch)
        all_channels.append(channels)

    # posts
    all_posts: list[Post] = []
    for pi, (title, body, si, ci) in enumerate(POST_SPECS):
        if si >= len(all_channels) or ci >= len(all_channels[si]):
            continue
        channel = all_channels[si][ci]
        # choose author: admin for announcements, else cycle students/managers
        if channel.post_policy == "admins":
            author = admin
        elif channel.post_policy == "moderators":
            author = managers[pi % len(managers)]
        else:
            author = students[pi % len(students)]

        post, _ = await one_or_create(
            db, Post,
            (Post.tenant_id == tenant.id, Post.channel_id == channel.id, Post.title == title),
            tenant_id=tenant.id, channel_id=channel.id,
            user_id=author.id, title=title, body=body,
            likes_count=0, comments_count=0, is_hidden=False,
        )
        all_posts.append(post)

    # comments — 3 per post, cycling through students
    for pi, post in enumerate(all_posts):
        commenters = [u for u in students if u.id != post.user_id]
        for ci in range(3):
            commenter = commenters[(pi * 3 + ci) % len(commenters)]
            text = COMMENT_TEXTS[(pi * 3 + ci) % len(COMMENT_TEXTS)]
            existing = await db.execute(
                select(Comment).where(
                    Comment.post_id == post.id,
                    Comment.user_id == commenter.id,
                    Comment.body == text,
                )
            )
            if not existing.scalar_one_or_none():
                db.add(Comment(
                    id=uuid.uuid4(), post_id=post.id, tenant_id=tenant.id,
                    user_id=commenter.id, body=text, is_hidden=False,
                ))
                post.comments_count += 1
        await db.flush()

    # likes — 4 per post, cycling
    for pi, post in enumerate(all_posts):
        likers = [u for u in students if u.id != post.user_id]
        for li in range(4):
            liker = likers[(pi * 4 + li) % len(likers)]
            existing = await db.execute(
                select(PostLike).where(PostLike.post_id == post.id, PostLike.user_id == liker.id)
            )
            if not existing.scalar_one_or_none():
                db.add(PostLike(id=uuid.uuid4(), post_id=post.id, user_id=liker.id))
                post.likes_count += 1
        await db.flush()

    return spaces


# ─── Products & enrollments ───────────────────────────────────────────────────

async def seed_products(
    db: AsyncSession,
    tenant: Tenant,
    companies: list[Company],
    courses: list[Course],
    spaces: list[Space],
    users: dict[str, User],
) -> list[Product]:
    products: list[Product] = []
    prices = [299.90, 399.90, 349.90, 279.90, 449.90, 329.90, 289.90, 319.90]

    for i, course in enumerate(courses):
        product, _ = await one_or_create(
            db, Product,
            (Product.tenant_id == tenant.id, Product.slug == f"produto-{course.slug}"),
            tenant_id=tenant.id, type="course", title=course.title,
            slug=f"produto-{course.slug}", status="published", visibility="public",
            price=prices[i % len(prices)],
            gateway_ids={"hotmart": f"HM-{1000 + i}", "stripe": f"price_seed_{i + 1}"},
            access_days=365, is_free=False,
        )
        products.append(product)

        await one_or_create(
            db, ProductCourse,
            (ProductCourse.product_id == product.id, ProductCourse.course_id == course.id),
            product_id=product.id, course_id=course.id, order_index=i,
        )

        # first 4 gated spaces linked to first 4 products
        if i < 4:
            await one_or_create(
                db, ProductSpace,
                (ProductSpace.product_id == product.id, ProductSpace.space_id == spaces[i].id),
                product_id=product.id, space_id=spaces[i].id,
            )

    # enroll all non-admin users in all products
    all_users = list(users.values())
    for user in all_users:
        if user.role == "admin":
            continue
        for product in products:
            await one_or_create(
                db, Enrollment,
                (Enrollment.tenant_id == tenant.id, Enrollment.user_id == user.id, Enrollment.product_id == product.id),
                tenant_id=tenant.id, user_id=user.id, product_id=product.id,
                status="active", enrolled_by="admin",
                company_id=user.company_id,
                expires_at=NOW + timedelta(days=365),
            )

    return products


# ─── Gamification ─────────────────────────────────────────────────────────────

BADGE_SPECS = [
    ("Primeira Semana",    "Concluiu atividades na primeira semana.",           "completion", "common",   "lesson_completed",  {"min_completed_lessons": 5},  100),
    ("7 Dias Seguidos",    "Manteve sequencia de 7 dias consecutivos.",         "behavior",   "rare", "streak_milestone",  {"min_streak": 7},             200),
    ("Top Performer",      "Atingiu o top 3 do ranking da empresa.",            "event",      "rare",     "ranking_top3",      {"top_n": 3},                  500),
    ("Mestre Negociador",  "Completou o curso de Negociacao Avancada.",         "completion", "rare", "course_completed",  {"course_slug": "negociacao-avancada"}, 300),
    ("Mentor da Turma",    "Respondeu 10 duvidas na comunidade.",               "social",     "rare",     "community_answers", {"min_answers": 10},           400),
    ("Velocista",          "Completou 3 cursos em menos de 30 dias.",           "completion", "epic",     "multi_course",      {"courses": 3, "days": 30},    1000),
    ("Embaixador CS",      "Completou o curso de Customer Success.",            "completion", "common",   "course_completed",  {"course_slug": "customer-success-na-pratica"}, 150),
    ("Pipeline Master",    "Completou o curso de Gestao de Pipeline.",          "completion", "common",   "course_completed",  {"course_slug": "gestao-de-pipeline"}, 150),
    ("Streaker de Platina", "Manteve sequencia de 30 dias.",                    "behavior",   "epic",     "streak_milestone",  {"min_streak": 30},            800),
    ("Data-Driven",        "Completou o curso de Analise de Dados para Vendas.","completion", "rare", "course_completed",  {"course_slug": "analise-dados-vendas"}, 250),
]

async def seed_gamification(
    db: AsyncSession,
    tenant: Tenant,
    companies: list[Company],
    users: dict[str, User],
    lessons: list[Lesson],
) -> list[Badge]:
    badges: list[Badge] = []
    for name, desc, cat, rarity, event, conditions, xp in BADGE_SPECS:
        b, _ = await one_or_create(
            db, Badge,
            (Badge.tenant_id == tenant.id, Badge.name == name),
            tenant_id=tenant.id, name=name, description=desc,
            category=cat, rarity=rarity, rule_event=event,
            rule_conditions=conditions, xp_reward=xp, is_active=True,
        )
        badges.append(b)

    students = [u for u in users.values() if u.role == "student"]

    for si, student in enumerate(students):
        company = next((c for c in companies if c.id == student.company_id), companies[0])
        lesson_count = 3 + (si % 6)  # 3 to 8 lessons per student
        xp_total = lesson_count * 50 + (si * 20)
        level = max(1, xp_total // 100)
        streak_curr = (si * 3 + 2) % 15
        streak_max = streak_curr + (si % 10)

        # lesson progress + XP
        for li, lesson in enumerate(lessons[:lesson_count]):
            await one_or_create(
                db, LessonProgress,
                (LessonProgress.user_id == student.id, LessonProgress.lesson_id == lesson.id),
                user_id=student.id, lesson_id=lesson.id,
                completed_at=NOW - timedelta(days=max(1, lesson_count - li)),
                last_watched_at=NOW - timedelta(days=max(1, lesson_count - li - 1)),
                watch_seconds=lesson.duration_seconds or 300,
            )
            await one_or_create(
                db, XPEvent,
                (XPEvent.tenant_id == tenant.id, XPEvent.user_id == student.id, XPEvent.reference_id == lesson.id),
                tenant_id=tenant.id, user_id=student.id, company_id=company.id,
                action="lesson_completed", amount=50,
                reference_id=lesson.id, reference_type="lesson",
            )

        await one_or_create(
            db, UserLevel,
            (UserLevel.tenant_id == tenant.id, UserLevel.user_id == student.id),
            tenant_id=tenant.id, user_id=student.id, total_xp=xp_total, level=level,
        )
        await one_or_create(
            db, UserStreak, (UserStreak.user_id == student.id,),
            user_id=student.id, company_id=company.id,
            current_streak=streak_curr, longest_streak=streak_max,
            last_activity_date=NOW - timedelta(days=si % 2),
            shields_available=si % 3,
        )

        # notes — first 2 students get notes
        if si < 2 and lessons:
            await one_or_create(
                db, Note,
                (Note.user_id == student.id, Note.lesson_id == lessons[si].id),
                user_id=student.id, lesson_id=lessons[si].id,
                content=f"Nota pessoal de {student.name}: revisar este topico antes da proxima call.",
                video_timestamp_seconds=120 + si * 60,
            )

        # distribute badges
        earned_badges = badges[:2 + (si % (len(badges) - 1))]
        for badge in earned_badges:
            await one_or_create(
                db, UserBadge,
                (UserBadge.user_id == student.id, UserBadge.badge_id == badge.id),
                user_id=student.id, badge_id=badge.id,
            )

    return badges


# ─── Messaging ────────────────────────────────────────────────────────────────

CONVERSATION_SPECS = [
    # (user1_email, user2_email, messages: [(content, sender_idx)])
    (
        "aluno@acmelearning.com", "manager@acmelearning.com",
        [
            ("Oi Marcos, tenho duvida sobre o modulo de fechamento.", 0),
            ("Claro Bruna, me conta o que esta acontecendo.", 1),
            ("Dificuldade em identificar o momento certo para proposta.", 0),
            ("Foque nos sinais: urgencia e budget confirmados. Entao avance.", 1),
            ("Faz sentido! Vou testar na call de amanha.", 0),
            ("Me conta como foi. Boa sorte!", 1),
        ],
    ),
    (
        "aluno@acmelearning.com", "aluno2@acmelearning.com",
        [
            ("Diego, viu o post sobre ICP vs Persona? Marcos explicou bem.", 0),
            ("Vi sim! Salvei para revisar antes da apresentacao.", 1),
            ("Vou usar na minha proxima qualificacao.", 0),
            ("Me conta como foi. Estou curioso.", 1),
        ],
    ),
    (
        "tatiane@gammatech.com", "lider@gammatech.com",
        [
            ("Lucas, como voce quer estruturar o QBR de agosto?", 0),
            ("Prefiro formato de apresentacao + discussao aberta, 2h no total.", 1),
            ("Ok. Preparo o deck com health score e expansao.", 0),
            ("Perfeito. Inclui os top 5 riscos de churn tambem.", 1),
        ],
    ),
    (
        "pedro@acmelearning.com", "julia@acmelearning.com",
        [
            ("Julia, como voce faz o handoff de SDR para AE?", 0),
            ("Uso um doc padrao com contexto + proximos passos acordados.", 1),
            ("Pode compartilhar o template?", 0),
            ("Claro! Vou mandar no canal de boas praticas da comunidade.", 1),
            ("Valeu! Vou adaptar para o nosso processo.", 0),
        ],
    ),
    (
        "ana@betavendas.com", "gerente@betavendas.com",
        [
            ("Giulia, consegui marcar demo com a Empresa X.", 0),
            ("Otimo! Que perfil? Qual o budget estimado?", 1),
            ("PME, 50 funcionarios. Budget ainda nao confirmado.", 0),
            ("Qualifica o budget antes da demo. Nao queremos perder tempo.", 1),
            ("Faz sentido. Vou enviar um email de pre-qualificacao.", 0),
        ],
    ),
    (
        "carlos@betavendas.com", "fernanda@betavendas.com",
        [
            ("Fernanda, quantas cadencias ativas voce tem agora?", 0),
            ("14 cadencias rodando. Taxa de reply em 8%.", 1),
            ("Bom numero. Qual canal performa melhor?", 0),
            ("Email com personalizacao manual. LinkedIn em segundo.", 1),
        ],
    ),
    (
        "rodrigo@gammatech.com", "camila@gammatech.com",
        [
            ("Camila, o cliente Omega solicitou customizacao no onboarding.", 0),
            ("Ja vi o ticket. Precisamos de mais 2 semanas de prazo.", 1),
            ("Beleza. Vou alinhar com o CS sobre expectativa do cliente.", 0),
        ],
    ),
    (
        "leticia@deltaservicos.com", "coord@deltaservicos.com",
        [
            ("Clara, o projeto Alpha esta com risco de atraso.", 0),
            ("Identifiquei isso tambem. Qual o principal gargalo?", 1),
            ("Aprovacao de escopo com o cliente. Travou ha 5 dias.", 0),
            ("Vou escalar para o sponsor. Nao podemos deixar passar semana.", 1),
            ("Obrigada. Vou preparar o resumo executivo para voce.", 0),
        ],
    ),
]

async def seed_messaging(db: AsyncSession, tenant: Tenant, users: dict[str, User]) -> None:
    for u1_email, u2_email, messages in CONVERSATION_SPECS:
        if u1_email not in users or u2_email not in users:
            continue
        u1, u2 = users[u1_email], users[u2_email]

        # find or create conversation
        r1 = await db.execute(
            select(ConversationParticipant.conversation_id).where(ConversationParticipant.user_id == u1.id)
        )
        r2 = await db.execute(
            select(ConversationParticipant.conversation_id).where(ConversationParticipant.user_id == u2.id)
        )
        shared = set(r1.scalars().all()) & set(r2.scalars().all())
        if shared:
            conv = await db.get(Conversation, next(iter(shared)))
        else:
            conv = Conversation(id=uuid.uuid4(), tenant_id=tenant.id)
            db.add(conv)
            await db.flush()
            for u in (u1, u2):
                db.add(ConversationParticipant(id=uuid.uuid4(), conversation_id=conv.id, user_id=u.id))
            await db.flush()

        for content, sender_idx in messages:
            sender = u1 if sender_idx == 0 else u2
            existing = await db.execute(
                select(Message).where(
                    Message.conversation_id == conv.id,
                    Message.sender_id == sender.id,
                    Message.content == content,
                )
            )
            if not existing.scalar_one_or_none():
                db.add(Message(id=uuid.uuid4(), conversation_id=conv.id, sender_id=sender.id, content=content))
        await db.flush()


# ─── Quiz ─────────────────────────────────────────────────────────────────────

QUIZ_QUESTIONS = [
    {"id": 1, "text": "O que significa ICP?",
     "options": ["Ideal Customer Profile", "Internal Client Process", "Initial Contact Plan", "Integrated Campaign Plan"], "correct": 0},
    {"id": 2, "text": "Qual etapa vem apos a qualificacao?",
     "options": ["Proposta", "Fechamento", "Diagnostico", "Prospeccao"], "correct": 2},
    {"id": 3, "text": "BANT significa:",
     "options": ["Budget, Authority, Need, Timeline", "Buy, Assess, Negotiate, Track", "Brand, Audience, Network, Target", "Budget, Acquisition, Need, Test"], "correct": 0},
    {"id": 4, "text": "SPIN Selling foca em qual tipo de perguntas?",
     "options": ["Situacao, Problema, Implicacao, Necessidade", "Speed, Price, Interest, Need", "Sales, Pipeline, Insight, Nurture", "Nenhuma das alternativas"], "correct": 0},
    {"id": 5, "text": "Health score de CS mede:",
     "options": ["Saude financeira do cliente", "Engajamento e satisfacao do cliente", "Performance da equipe de vendas", "Numero de tickets abertos"], "correct": 1},
]

BATTLE_SPECS = [
    # (challenger_email, opponent_email, status, winner_idx)  winner_idx: 0=challenger, 1=opponent, None=pending
    ("aluno@acmelearning.com",      "aluno2@acmelearning.com",    "completed", 0),
    ("aluno2@acmelearning.com",     "aluno@acmelearning.com",     "pending",   None),
    ("pedro@acmelearning.com",      "julia@acmelearning.com",     "completed", 1),
    ("julia@acmelearning.com",      "pedro@acmelearning.com",     "completed", 0),
    ("ana@betavendas.com",          "carlos@betavendas.com",      "completed", 0),
    ("carlos@betavendas.com",       "fernanda@betavendas.com",    "pending",   None),
    ("tatiane@gammatech.com",       "rodrigo@gammatech.com",      "completed", 0),
    ("rodrigo@gammatech.com",       "camila@gammatech.com",       "completed", 1),
    ("leticia@deltaservicos.com",   "thiago@deltaservicos.com",   "completed", 0),
    ("gustavo@deltaservicos.com",   "mariana@deltaservicos.com",  "pending",   None),
    ("aluno@acmelearning.com",      "pedro@acmelearning.com",     "completed", 0),
    ("fernanda@betavendas.com",     "rafael@betavendas.com",      "completed", 1),
]

async def seed_quiz(
    db: AsyncSession, tenant: Tenant, users: dict[str, User], courses: list[Course]
) -> None:
    course = courses[0]
    for challenger_email, opponent_email, status, winner_idx in BATTLE_SPECS:
        if challenger_email not in users or opponent_email not in users:
            continue
        challenger = users[challenger_email]
        opponent = users[opponent_email]
        winner = challenger if winner_idx == 0 else opponent if winner_idx == 1 else None

        existing = await db.execute(
            select(QuizBattle).where(
                QuizBattle.tenant_id == tenant.id,
                QuizBattle.challenger_id == challenger.id,
                QuizBattle.opponent_id == opponent.id,
                QuizBattle.status == status,
            )
        )
        if existing.scalar_one_or_none():
            continue

        battle = QuizBattle(
            id=uuid.uuid4(), tenant_id=tenant.id,
            challenger_id=challenger.id, opponent_id=opponent.id,
            course_id=course.id, questions=QUIZ_QUESTIONS,
            status=status, winner_id=winner.id if winner else None,
            expires_at=NOW + timedelta(hours=24),
        )
        db.add(battle)
        await db.flush()

        if status == "completed":
            challenger_score = 5 if winner_idx == 0 else 2
            opponent_score   = 5 if winner_idx == 1 else 2
            db.add(QuizBattleAnswer(
                id=uuid.uuid4(), battle_id=battle.id, user_id=challenger.id,
                answers={str(q["id"]): q["correct"] for q in QUIZ_QUESTIONS[:challenger_score]},
                score=challenger_score,
            ))
            db.add(QuizBattleAnswer(
                id=uuid.uuid4(), battle_id=battle.id, user_id=opponent.id,
                answers={str(q["id"]): q["correct"] for q in QUIZ_QUESTIONS[:opponent_score]},
                score=opponent_score,
            ))
        await db.flush()


# ─── Email marketing ──────────────────────────────────────────────────────────

async def seed_email(
    db: AsyncSession, tenant: Tenant, users: dict[str, User]
) -> None:
    students = [u for u in users.values() if u.role == "student"]
    managers = [u for u in users.values() if u.role == "manager"]

    # audiences
    audience_specs = [
        ("Todos os Alunos",       {"role": "student"}),
        ("Todos os Gestores",     {"role": "manager"}),
        ("Alunos Empresa 0",      {"role": "student", "company_index": 0}),
        ("Alunos Engajados",      {"role": "student", "min_lessons": 5}),
        ("Alunos em Risco",       {"role": "student", "max_streak": 2}),
        ("Toda a Plataforma",     {}),
    ]
    audiences: list[EmailAudience] = []
    for name, filter_json in audience_specs:
        a, _ = await one_or_create(
            db, EmailAudience,
            (EmailAudience.tenant_id == tenant.id, EmailAudience.name == name),
            tenant_id=tenant.id, name=name, filter_json=filter_json,
        )
        audiences.append(a)

    # templates
    template_specs = [
        ("Boas-vindas",              "Bem-vindo ao Acme Learning, {{user_name}}!",
         "<h1>Ola {{user_name}}!</h1><p>Sua jornada comecou. Acesse agora.</p>"),
        ("Atualizacao de Conteudo",  "Novo conteudo disponivel para voce",
         "<h1>Novidade!</h1><p>Ola {{user_name}}, novo modulo liberado.</p>"),
        ("Lembrete de Engajamento",  "Sentimos sua falta, {{user_name}}!",
         "<h1>Voltou?</h1><p>Faz {{days_inactive}} dias que voce nao acessa.</p>"),
        ("Certificado Disponivel",   "Seu certificado esta pronto, {{user_name}}!",
         "<h1>Parabens!</h1><p>Voce concluiu {{course_name}}. Baixe seu certificado.</p>"),
        ("Novidades do Mes",         "Resumo de {{month}}: o que tem de novo",
         "<h1>Novidades</h1><p>Confira o que rolou em {{month}} na plataforma.</p>"),
        ("Alerta de Streak",         "Sua sequencia de {{streak_days}} dias esta em risco!",
         "<h1>Nao perca sua sequencia!</h1><p>Acesse hoje para manter {{streak_days}} dias.</p>"),
    ]
    templates: list[EmailTemplate] = []
    for name, subject, html in template_specs:
        t, _ = await one_or_create(
            db, EmailTemplate,
            (EmailTemplate.tenant_id == tenant.id, EmailTemplate.name == name),
            tenant_id=tenant.id, name=name, subject=subject, html_body=html,
        )
        templates.append(t)

    # automations
    automation_specs = [
        ("Sequencia de Onboarding",  "enrollment.active",   [
            {"delay_days": 0,  "template": "enrollment_access_granted"},
            {"delay_days": 3,  "template": "course_reminder"},
            {"delay_days": 7,  "template": "streak_at_risk"},
            {"delay_days": 14, "template": "course_halfway"},
        ]),
        ("Re-engajamento",           "streak.lost",         [
            {"delay_days": 0, "template": "streak_at_risk"},
            {"delay_days": 2, "template": "comeback_incentive"},
        ]),
        ("Conclusao de Curso",       "course.completed",    [
            {"delay_days": 0, "template": "course_completed"},
            {"delay_days": 1, "template": "certificate_ready"},
            {"delay_days": 7, "template": "upsell_next_course"},
        ]),
    ]
    for name, trigger, steps in automation_specs:
        await one_or_create(
            db, EmailAutomation,
            (EmailAutomation.tenant_id == tenant.id, EmailAutomation.name == name),
            tenant_id=tenant.id, name=name,
            trigger_event=trigger, steps=steps, is_active=True,
        )

    # campaigns
    campaign_specs = [
        ("Lancamento Plataforma",    0, 0, "sent",      -30, 2),
        ("Novidades de Abril",       1, 5, "sent",      -15, 1),
        ("Alerta de Engajamento",    2, 4, "sent",       -7, 1),
        ("Campanha de Maio",         3, 0, "scheduled",   7, 0),
        ("Newsletter Gestores",      1, 1, "draft",       0, 0),
    ]
    for cname, t_idx, a_idx, status, sent_offset, sent_count in campaign_specs:
        camp, _ = await one_or_create(
            db, EmailCampaign,
            (EmailCampaign.tenant_id == tenant.id, EmailCampaign.name == cname),
            tenant_id=tenant.id, name=cname,
            template_id=templates[t_idx].id,
            audience_id=audiences[a_idx].id,
            status=status,
            sent_at=NOW + timedelta(days=sent_offset) if status == "sent" else None,
            scheduled_at=NOW + timedelta(days=sent_offset) if status == "scheduled" else None,
            sent_count=sent_count,
        )

        if status == "sent":
            recipients = students if a_idx in (0, 4) else managers if a_idx == 1 else students[:5]
            for ri, user in enumerate(recipients[:8]):
                is_opened = ri % 3 != 2
                existing = await db.execute(
                    select(EmailSend).where(EmailSend.campaign_id == camp.id, EmailSend.user_id == user.id)
                )
                if not existing.scalar_one_or_none():
                    db.add(EmailSend(
                        id=uuid.uuid4(), campaign_id=camp.id, user_id=user.id, email=user.email,
                        status="opened" if is_opened else "sent",
                        sent_at=NOW + timedelta(days=sent_offset),
                        opened_at=NOW + timedelta(days=sent_offset, hours=2) if is_opened else None,
                    ))
    await db.flush()


# ─── Webhooks & leads ─────────────────────────────────────────────────────────

WEBHOOK_LOG_SPECS = [
    ("hotmart",    "PURCHASE_COMPLETE",            True,  True,  "aluno@acmelearning.com",     "HM-TRX-001"),
    ("hotmart",    "PURCHASE_COMPLETE",            True,  True,  "ana@betavendas.com",          "HM-TRX-002"),
    ("hotmart",    "PURCHASE_COMPLETE",            True,  True,  "tatiane@gammatech.com",       "HM-TRX-003"),
    ("hotmart",    "PURCHASE_REFUNDED",            True,  True,  "vitor@gammatech.com",         "HM-TRX-004"),
    ("stripe",     "checkout.session.completed",   True,  True,  "carlos@betavendas.com",       "cs_001"),
    ("stripe",     "checkout.session.completed",   True,  True,  "leticia@deltaservicos.com",   "cs_002"),
    ("stripe",     "customer.subscription.deleted",True,  True,  "thiago@deltaservicos.com",    "cs_003"),
    ("kiwify",     "order.approved",               True,  True,  "pedro@acmelearning.com",      "KW-001"),
    ("kiwify",     "order.refunded",               True,  True,  "julia@acmelearning.com",      "KW-002"),
    ("greenn",     "purchase_approved",            True,  True,  "rodrigo@gammatech.com",       "GR-001"),
    ("greenn",     "purchase_approved",            True,  True,  "camila@gammatech.com",        "GR-002"),
    ("hotmart",    "PURCHASE_COMPLETE",            False, False, "invalido@hacker.com",         "HM-INVALID"),
    ("stripe",     "checkout.session.expired",     True,  False, "gustavo@deltaservicos.com",   "cs_expired"),
]

LEAD_SPECS = [
    ("lead1@exemplo.com",   "Lead Um",      "landing_page",         "google",   "cpc",     "onboarding-comercial"),
    ("lead2@exemplo.com",   "Lead Dois",    "hotmart_checkout",     "hotmart",  "organic", "onboarding-comercial"),
    ("lead3@exemplo.com",   "Lead Tres",    "kiwify_checkout",      "facebook", "social",  "customer-success"),
    ("lead4@exemplo.com",   "Lead Quatro",  "landing_page",         "linkedin", "paid",    "negociacao"),
    ("lead5@exemplo.com",   "Lead Cinco",   "landing_page",         "google",   "cpc",     "gestao-pipeline"),
    ("lead6@exemplo.com",   "Lead Seis",    "greenn_checkout",      "greenn",   "organic", "lideranca"),
    ("lead7@exemplo.com",   "Lead Sete",    "landing_page",         "youtube",  "video",   "onboarding-comercial"),
    ("lead8@exemplo.com",   "Lead Oito",    "hotmart_checkout",     "hotmart",  "email",   "vendas-consultivas"),
]

async def seed_webhooks(
    db: AsyncSession, tenant: Tenant, products: list[Product], users: dict[str, User]
) -> None:
    for provider, event_type, sig_valid, processed, buyer_email, tx_id in WEBHOOK_LOG_SPECS:
        existing = await db.execute(
            select(WebhookLog).where(
                WebhookLog.tenant_id == tenant.id,
                WebhookLog.provider == provider,
                WebhookLog.event_type == event_type,
                WebhookLog.payload["transaction_id"].astext == tx_id,
            )
        )
        if not existing.scalar_one_or_none():
            db.add(WebhookLog(
                id=uuid.uuid4(), tenant_id=tenant.id,
                provider=provider, event_type=event_type,
                payload={"buyer_email": buyer_email, "transaction_id": tx_id, "event": event_type},
                signature_valid=sig_valid, processed=processed,
                attempts=1 if processed else 3,
                error_message=None if processed else "Assinatura invalida.",
            ))

    for email, name, source, utm_source, utm_medium, utm_campaign in LEAD_SPECS:
        existing = await db.execute(
            select(Lead).where(Lead.tenant_id == tenant.id, Lead.email == email)
        )
        if not existing.scalar_one_or_none():
            db.add(Lead(
                id=uuid.uuid4(), tenant_id=tenant.id,
                email=email, name=name, source=source,
                utm_source=utm_source, utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                product_id=products[0].id if products else None,
            ))
    await db.flush()


# ─── Landing pages ────────────────────────────────────────────────────────────

LANDING_SPECS = [
    ("onboarding-comercial",    "Onboarding Comercial B2B",        "Treinamento B2B.", "vendas,b2b,onboarding", 0),
    ("customer-success",        "Customer Success na Pratica",      "CS pratico.",      "cs,retencao,clientes",  1),
    ("negociacao-avancada",     "Negociacao Avancada",              "Negociacao.",      "negociacao,vendas",     2),
    ("gestao-pipeline",         "Gestao de Pipeline",               "Pipeline.",        "pipeline,forecasting",  3),
    ("lideranca-comercial",     "Lideranca de Times Comerciais",    "Lideranca.",       "lideranca,gestao",      4),
]

async def seed_landing(
    db: AsyncSession, tenant: Tenant, products: list[Product]
) -> None:
    for slug, title, desc, keywords, p_idx in LANDING_SPECS:
        page, _ = await one_or_create(
            db, LandingPage,
            (LandingPage.tenant_id == tenant.id, LandingPage.slug == slug),
            tenant_id=tenant.id, slug=slug, title=title,
            seo_description=desc, seo_keywords=keywords,
            status="published",
            product_id=products[p_idx].id if p_idx < len(products) else None,
            page_metadata={"hero": title, "cta": "Comecar agora"},
        )
        for i in range(3):
            await one_or_create(
                db, PageView,
                (PageView.page_id == page.id, PageView.ip_hash == f"seed-{slug}-{i}"),
                page_id=page.id, ip_hash=f"seed-{slug}-{i}",
                user_agent="Seed Browser", utm_source="google",
                utm_medium="cpc", utm_campaign=slug,
            )


# ─── Notifications ────────────────────────────────────────────────────────────

async def seed_notifications(
    db: AsyncSession, tenant: Tenant, users: dict[str, User]
) -> None:
    notif_specs = [
        ("aluno@acmelearning.com",      "Nova trilha disponivel",       "O onboarding comercial foi atualizado. Confira!"),
        ("aluno@acmelearning.com",      "Badge conquistado!",            "Voce ganhou o badge Primeira Semana. Continue!"),
        ("aluno@acmelearning.com",      "Novo comentario no seu post",   "Marcos comentou no seu post da comunidade."),
        ("aluno2@acmelearning.com",     "Badge conquistado!",            "Voce ganhou o badge Primeira Semana!"),
        ("aluno2@acmelearning.com",     "Desafio recebido",              "Bruna te desafiou num quiz de Onboarding Comercial."),
        ("aluno2@acmelearning.com",     "Lembrete de aula",              "Voce nao acessa ha 2 dias. Continue aprendendo!"),
        ("pedro@acmelearning.com",      "Novo conteudo",                 "Modulo de Negociacao liberado para voce."),
        ("pedro@acmelearning.com",      "Meta da empresa atualizada",    "A meta de completar 80% do onboarding esta proxima!"),
        ("julia@acmelearning.com",      "Certificado disponivel",        "Voce concluiu Vendas Consultivas. Baixe seu certificado!"),
        ("julia@acmelearning.com",      "Novidade na comunidade",        "Novo post no canal de Cases de Sucesso."),
        ("manager@acmelearning.com",    "Meta da equipe atualizada",     "Time Comercial: 65% de progresso na meta mensal."),
        ("manager@acmelearning.com",    "Relatorio semanal pronto",      "O relatorio de engajamento da semana esta disponivel."),
        ("gerente@betavendas.com",      "Novo membro na equipe",         "Rafael Mendes foi adicionado ao time Beta Vendas."),
        ("lider@gammatech.com",         "Meta atingida!",                "O time Gamma Tech atingiu 90% da meta de certificacao!"),
        ("tatiane@gammatech.com",       "Alerta de churn",               "Cliente Omega com health score abaixo de 40. Atencao!"),
        ("rodrigo@gammatech.com",       "Novo curso recomendado",        "Analise de Dados para Vendas pode te ajudar no trabalho."),
        ("leticia@deltaservicos.com",   "Prazo se aproximando",          "Projeto Alpha vence em 7 dias. Acompanhe o status."),
        ("camila@gammatech.com",        "Feedback recebido",             "Voce recebeu 5 estrelas no ultimo onboarding de cliente."),
        ("thiago@deltaservicos.com",    "Badge conquistado!",            "Voce ganhou 7 Dias Seguidos. Incrivel!"),
        ("gustavo@deltaservicos.com",   "Novo desafio disponivel",       "Desafio semanal: complete 2 aulas ate sexta-feira."),
    ]
    for email, title, body in notif_specs:
        if email not in users:
            continue
        await one_or_create(
            db, Notification,
            (Notification.tenant_id == tenant.id, Notification.user_id == users[email].id, Notification.title == title),
            tenant_id=tenant.id, user_id=users[email].id,
            type="seed", title=title, body=body,
            data={"source": "scripts/seed.py"}, is_read=False,
        )


# ─── Audit logs ───────────────────────────────────────────────────────────────

async def seed_audit(
    db: AsyncSession, tenant: Tenant, users: dict[str, User], products: list[Product]
) -> None:
    admin = users["admin@acmelearning.com"]
    students = [u for u in users.values() if u.role == "student"]

    entries = []
    for p in products:
        entries += [
            ("create",  "product", str(p.id), {"title": p.title}),
            ("publish", "product", str(p.id), {"status": "published"}),
        ]
    for i, s in enumerate(students[:5]):
        entries += [
            ("enroll",   "user", str(s.id), {"product_index": i}),
            ("view",     "user", str(s.id), {"page": "dashboard"}),
        ]
    entries += [
        ("create",  "space",   "community-comercial",  {"name": "Comunidade Comercial B2B"}),
        ("create",  "space",   "community-cs",         {"name": "Comunidade Customer Success"}),
        ("suspend", "user",    str(students[0].id),    {"reason": "test"}),
        ("unsuspend","user",   str(students[0].id),    {}),
        ("update",  "tenant",  str(tenant.id),         {"field": "primary_color"}),
        ("export",  "report",  "company-0-report",     {"format": "csv"}),
    ]

    for action, resource_type, resource_id, details in entries:
        existing = await db.execute(
            select(AuditLog).where(
                AuditLog.tenant_id == tenant.id,
                AuditLog.user_id == admin.id,
                AuditLog.action == action,
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == resource_id,
            )
        )
        if not existing.scalar_one_or_none():
            db.add(AuditLog(
                tenant_id=tenant.id, user_id=admin.id,
                action=action, resource_type=resource_type,
                resource_id=resource_id, details=details,
            ))
    await db.flush()


# ─── Main ─────────────────────────────────────────────────────────────────────

async def run() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        tenant    = await seed_tenant(db)
        companies = await seed_companies(db, tenant)
        users     = await seed_users(db, tenant, companies)
        await seed_company_members(db, companies, users)
        courses, lessons = await seed_courses(db, tenant, users["admin@acmelearning.com"])
        spaces    = await seed_community(db, tenant, users)
        products  = await seed_products(db, tenant, companies, courses, spaces, users)
        await seed_gamification(db, tenant, companies, users, lessons)
        await seed_messaging(db, tenant, users)
        await seed_quiz(db, tenant, users, courses)
        await seed_email(db, tenant, users)
        await seed_webhooks(db, tenant, products, users)
        await seed_landing(db, tenant, products)
        await seed_notifications(db, tenant, users)
        await seed_audit(db, tenant, users, products)
        await db.commit()

    await engine.dispose()
    print("Seed concluido.")
    print("Tenant: localhost ou acme.localhost")
    print(f"Senha padrao: {PASSWORD}")
    print()
    print("Usuarios (21 total):")
    print("  admin@acmelearning.com             — admin")
    print("  manager@acmelearning.com           — manager  (Acme Comercial)")
    print("  gerente@betavendas.com             — manager  (Beta Vendas)")
    print("  lider@gammatech.com                — manager  (Gamma Tech)")
    print("  coord@deltaservicos.com            — manager  (Delta Servicos)")
    print("  aluno@acmelearning.com             — student  (Acme Comercial)")
    print("  aluno2@acmelearning.com            — student  (Acme Comercial)")
    print("  pedro@acmelearning.com             — student  (Acme Comercial)")
    print("  julia@acmelearning.com             — student  (Acme Comercial)")
    print("  ana@betavendas.com                 — student  (Beta Vendas)")
    print("  carlos@betavendas.com              — student  (Beta Vendas)")
    print("  fernanda@betavendas.com            — student  (Beta Vendas)")
    print("  rafael@betavendas.com              — student  (Beta Vendas)")
    print("  tatiane@gammatech.com              — student  (Gamma Tech)")
    print("  rodrigo@gammatech.com              — student  (Gamma Tech)")
    print("  camila@gammatech.com               — student  (Gamma Tech)")
    print("  vitor@gammatech.com                — student  (Gamma Tech)")
    print("  leticia@deltaservicos.com          — student  (Delta Servicos)")
    print("  thiago@deltaservicos.com           — student  (Delta Servicos)")
    print("  mariana@deltaservicos.com          — student  (Delta Servicos)")
    print("  gustavo@deltaservicos.com          — student  (Delta Servicos)")


if __name__ == "__main__":
    asyncio.run(run())
