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
        for key, value in values.items():
            setattr(item, key, value)
        return item, False
    item = model(id=uuid.uuid4(), **values)
    db.add(item)
    await db.flush()
    return item, True


# ─── Tenant & config ──────────────────────────────────────────────────────────

async def seed_tenant(db: AsyncSession) -> Tenant:
    tenant, _ = await one_or_create(
        db, Tenant, (Tenant.slug == "acme",),
        slug="acme",
        name="Acme Learning",
        custom_domain="localhost",
        subdomain="acme.localhost",
        app_name="Acme Learning",
        primary_color="#2563EB",
        secondary_color="#16A34A",
        font_family="Inter",
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


# ─── Company ─────────────────────────────────────────────────────────────────

async def seed_company(db: AsyncSession, tenant: Tenant) -> Company:
    company, _ = await one_or_create(
        db, Company,
        (Company.tenant_id == tenant.id, Company.legal_name == "Acme Comercial Ltda"),
        tenant_id=tenant.id,
        cnpj="12.345.678/0001-90",
        legal_name="Acme Comercial Ltda",
        trade_name="Acme Comercial",
        max_seats=80,
        status="active",
        contract_start=NOW - timedelta(days=45),
        contract_end=NOW + timedelta(days=320),
    )
    return company


# ─── Users ───────────────────────────────────────────────────────────────────

async def seed_users(db: AsyncSession, tenant: Tenant, company: Company) -> dict[str, User]:
    legacy = await db.execute(
        select(User).where(User.tenant_id == tenant.id, User.email.like("%@acme.test"))
    )
    for u in legacy.scalars():
        await db.delete(u)
    await db.flush()

    users = {}
    for email, name, role, bio in (
        ("admin@acmelearning.com", "Ana Admin", "admin", "Admin da plataforma Acme Learning."),
        ("manager@acmelearning.com", "Marcos Manager", "manager", "Gestor do time Comercial."),
        ("aluno@acmelearning.com", "Bruna Aluna", "student", "Estudante focada em vendas consultivas."),
        ("aluno2@acmelearning.com", "Diego Aluno", "student", "Estudante do time de atendimento."),
    ):
        user, _ = await one_or_create(
            db, User,
            (User.tenant_id == tenant.id, User.email == email),
            tenant_id=tenant.id,
            email=email,
            name=name,
            password_hash=hash_password(PASSWORD),
            role=role,
            company_id=company.id if role in {"manager", "student"} else None,
            is_active=True,
            is_suspended=False,
            bio=bio,
        )
        users[email] = user
    return users


# ─── Courses ─────────────────────────────────────────────────────────────────

async def seed_courses(db: AsyncSession, tenant: Tenant, instructor: User) -> tuple[list[Course], list[Lesson]]:
    courses: list[Course] = []
    lessons: list[Lesson] = []
    course_specs = [
        (
            "Onboarding Comercial B2B",
            "onboarding-comercial-b2b",
            "Fundamentos para ramp-up de novos vendedores B2B.",
            "https://images.unsplash.com/photo-1556761175-4b46a572b786",
            [
                ("Fundamentos", ["Visao geral do playbook", "ICP e qualificacao", "Cadencia de prospeccao"]),
                ("Execucao", ["Diagnostico consultivo", "Proposta de valor", "Follow-up e fechamento"]),
            ],
        ),
        (
            "Customer Success na Pratica",
            "customer-success-na-pratica",
            "Rotinas para onboarding, expansao e retencao de clientes.",
            "https://images.unsplash.com/photo-1552664730-d307ca884978",
            [
                ("Operacao de CS", ["Jornada do cliente", "Health score", "Ritos de QBR"]),
                ("Crescimento", ["Playbooks de expansao", "Gestao de churn", "Comunidade de clientes"]),
            ],
        ),
    ]

    for title, slug, description, thumbnail_url, modules in course_specs:
        course, _ = await one_or_create(
            db, Course,
            (Course.tenant_id == tenant.id, Course.slug == slug),
            tenant_id=tenant.id,
            title=title,
            slug=slug,
            description=description,
            thumbnail_url=thumbnail_url,
            status="published",
            is_free=False,
            certificate_enabled=True,
            instructor_id=instructor.id,
        )
        courses.append(course)

        for mi, (module_title, lesson_titles) in enumerate(modules):
            module, _ = await one_or_create(
                db, Module,
                (Module.tenant_id == tenant.id, Module.course_id == course.id, Module.title == module_title),
                tenant_id=tenant.id, course_id=course.id,
                title=module_title, order_index=mi, is_hidden=False,
            )
            for li, lesson_title in enumerate(lesson_titles):
                lesson, _ = await one_or_create(
                    db, Lesson,
                    (Lesson.tenant_id == tenant.id, Lesson.module_id == module.id, Lesson.title == lesson_title),
                    tenant_id=tenant.id,
                    module_id=module.id,
                    title=lesson_title,
                    order_index=li,
                    lesson_type="video",
                    is_hidden=False,
                    is_free_preview=(li == 0),
                    duration_seconds=480 + (li * 180),
                    video_provider="youtube",
                    video_external_id="dQw4w9WgXcQ",
                    ai_summary=f"Resumo pratico da aula {lesson_title.lower()}.",
                    transcript_text={"items": [{"text": f"Conteudo demonstrativo de {lesson_title}."}]},
                )
                lessons.append(lesson)
    return courses, lessons


# ─── Products & enrollments ───────────────────────────────────────────────────

async def seed_products(
    db: AsyncSession,
    tenant: Tenant,
    company: Company,
    courses: list[Course],
    spaces: list[Space],
    users: dict[str, User],
) -> list[Product]:
    products: list[Product] = []
    for index, course in enumerate(courses):
        product, _ = await one_or_create(
            db, Product,
            (Product.tenant_id == tenant.id, Product.slug == f"produto-{course.slug}"),
            tenant_id=tenant.id,
            type="course",
            title=course.title,
            slug=f"produto-{course.slug}",
            status="published",
            visibility="public",
            price=299.90 + (index * 100),
            gateway_ids={"hotmart": f"HM-{index + 1000}", "stripe": f"price_seed_{index + 1}"},
            access_days=365,
            is_free=False,
        )
        products.append(product)

        await one_or_create(
            db, ProductCourse,
            (ProductCourse.product_id == product.id, ProductCourse.course_id == course.id),
            product_id=product.id, course_id=course.id, order_index=index,
        )

        # each product unlocks the corresponding space
        if index < len(spaces):
            await one_or_create(
                db, ProductSpace,
                (ProductSpace.product_id == product.id, ProductSpace.space_id == spaces[index].id),
                product_id=product.id, space_id=spaces[index].id,
            )

    for user in users.values():
        if user.role == "admin":
            continue
        for product in products:
            await one_or_create(
                db, Enrollment,
                (Enrollment.tenant_id == tenant.id, Enrollment.user_id == user.id, Enrollment.product_id == product.id),
                tenant_id=tenant.id,
                user_id=user.id,
                product_id=product.id,
                status="active",
                enrolled_by="admin",
                company_id=company.id,
                expires_at=NOW + timedelta(days=365),
            )
    return products


# ─── Activity / gamification ─────────────────────────────────────────────────

async def seed_activity(
    db: AsyncSession,
    tenant: Tenant,
    company: Company,
    users: dict[str, User],
    lessons: list[Lesson],
) -> None:
    student = users["aluno@acmelearning.com"]
    student2 = users["aluno2@acmelearning.com"]
    manager = users["manager@acmelearning.com"]

    for user, team, job_role in (
        (student, "Comercial", "Account Executive"),
        (student2, "Atendimento", "Customer Support"),
        (manager, "Comercial", "Sales Manager"),
    ):
        user.company_id = company.id
        await one_or_create(
            db, CompanyMember,
            (CompanyMember.company_id == company.id, CompanyMember.user_id == user.id),
            company_id=company.id, user_id=user.id,
            team=team, job_role=job_role, is_active=True,
        )

    # student: 7 lesson progress entries + XP
    for i, lesson in enumerate(lessons[:7]):
        await one_or_create(
            db, LessonProgress,
            (LessonProgress.user_id == student.id, LessonProgress.lesson_id == lesson.id),
            user_id=student.id, lesson_id=lesson.id,
            completed_at=NOW - timedelta(days=max(1, 7 - i)) if i < 5 else None,
            last_watched_at=NOW - timedelta(days=max(1, 5 - i)),
            watch_seconds=lesson.duration_seconds or 300,
        )
        await one_or_create(
            db, XPEvent,
            (XPEvent.tenant_id == tenant.id, XPEvent.user_id == student.id, XPEvent.reference_id == lesson.id),
            tenant_id=tenant.id, user_id=student.id,
            company_id=company.id, action="lesson_completed",
            amount=50, reference_id=lesson.id, reference_type="lesson",
        )

    # student2: 3 lesson progress entries + XP
    for i, lesson in enumerate(lessons[:3]):
        await one_or_create(
            db, LessonProgress,
            (LessonProgress.user_id == student2.id, LessonProgress.lesson_id == lesson.id),
            user_id=student2.id, lesson_id=lesson.id,
            completed_at=NOW - timedelta(days=3 - i),
            last_watched_at=NOW - timedelta(days=2 - i),
            watch_seconds=lesson.duration_seconds or 300,
        )
        await one_or_create(
            db, XPEvent,
            (XPEvent.tenant_id == tenant.id, XPEvent.user_id == student2.id, XPEvent.reference_id == lesson.id),
            tenant_id=tenant.id, user_id=student2.id,
            company_id=company.id, action="lesson_completed",
            amount=50, reference_id=lesson.id, reference_type="lesson",
        )

    await one_or_create(
        db, Note,
        (Note.user_id == student.id, Note.lesson_id == lessons[0].id),
        user_id=student.id, lesson_id=lessons[0].id,
        content="Revisar criterios de qualificacao antes da proxima call.",
        video_timestamp_seconds=210,
    )

    # levels
    await one_or_create(
        db, UserLevel,
        (UserLevel.tenant_id == tenant.id, UserLevel.user_id == student.id),
        tenant_id=tenant.id, user_id=student.id, total_xp=350, level=4,
    )
    await one_or_create(
        db, UserLevel,
        (UserLevel.tenant_id == tenant.id, UserLevel.user_id == student2.id),
        tenant_id=tenant.id, user_id=student2.id, total_xp=150, level=2,
    )

    # streaks
    await one_or_create(
        db, UserStreak, (UserStreak.user_id == student.id,),
        user_id=student.id, company_id=company.id,
        current_streak=6, longest_streak=14,
        last_activity_date=NOW, shields_available=1,
    )
    await one_or_create(
        db, UserStreak, (UserStreak.user_id == student2.id,),
        user_id=student2.id, company_id=company.id,
        current_streak=3, longest_streak=5,
        last_activity_date=NOW - timedelta(days=1), shields_available=0,
    )

    # badges
    badge_onboarding, _ = await one_or_create(
        db, Badge,
        (Badge.tenant_id == tenant.id, Badge.name == "Primeira Semana"),
        tenant_id=tenant.id, name="Primeira Semana",
        description="Concluiu atividades em uma semana de onboarding.",
        category="completion", rarity="common",
        rule_event="lesson_completed",
        rule_conditions={"min_completed_lessons": 5},
        xp_reward=100, is_active=True,
    )
    badge_streak, _ = await one_or_create(
        db, Badge,
        (Badge.tenant_id == tenant.id, Badge.name == "7 Dias Seguidos"),
        tenant_id=tenant.id, name="7 Dias Seguidos",
        description="Manteve sequencia de 7 dias consecutivos.",
        category="streak", rarity="uncommon",
        rule_event="streak_milestone",
        rule_conditions={"min_streak": 7},
        xp_reward=200, is_active=True,
    )
    badge_top, _ = await one_or_create(
        db, Badge,
        (Badge.tenant_id == tenant.id, Badge.name == "Top Performer"),
        tenant_id=tenant.id, name="Top Performer",
        description="Atingiu o top 3 do ranking da empresa.",
        category="ranking", rarity="rare",
        rule_event="ranking_top3",
        rule_conditions={"top_n": 3},
        xp_reward=500, is_active=True,
    )
    await one_or_create(
        db, UserBadge,
        (UserBadge.user_id == student.id, UserBadge.badge_id == badge_onboarding.id),
        user_id=student.id, badge_id=badge_onboarding.id,
    )
    await one_or_create(
        db, UserBadge,
        (UserBadge.user_id == student.id, UserBadge.badge_id == badge_streak.id),
        user_id=student.id, badge_id=badge_streak.id,
    )

    await one_or_create(
        db, CompanyGoal,
        (CompanyGoal.company_id == company.id, CompanyGoal.title == "Concluir onboarding comercial"),
        company_id=company.id,
        title="Concluir onboarding comercial",
        target_metric="completion_rate",
        target_value=80,
        course_id=None,
        deadline=NOW + timedelta(days=30),
        status="active",
    )

    _ = badge_top  # referenced but not yet earned by anyone


# ─── Community ───────────────────────────────────────────────────────────────

async def seed_community(
    db: AsyncSession,
    tenant: Tenant,
    users: dict[str, User],
) -> list[Space]:
    student = users["aluno@acmelearning.com"]
    student2 = users["aluno2@acmelearning.com"]
    manager = users["manager@acmelearning.com"]
    admin = users["admin@acmelearning.com"]

    spaces: list[Space] = []

    # Space 1 — gated via product (seeded in seed_products)
    space1, _ = await one_or_create(
        db, Space,
        (Space.tenant_id == tenant.id, Space.name == "Comunidade Comercial"),
        tenant_id=tenant.id,
        name="Comunidade Comercial",
        description="Espaco exclusivo para alunos do Onboarding Comercial B2B.",
        is_active=True,
    )
    spaces.append(space1)

    ch_geral, _ = await one_or_create(
        db, Channel,
        (Channel.tenant_id == tenant.id, Channel.space_id == space1.id, Channel.name == "Geral"),
        tenant_id=tenant.id, space_id=space1.id,
        name="Geral", channel_type="discussion", post_policy="open", is_active=True,
    )
    ch_avisos, _ = await one_or_create(
        db, Channel,
        (Channel.tenant_id == tenant.id, Channel.space_id == space1.id, Channel.name == "Avisos"),
        tenant_id=tenant.id, space_id=space1.id,
        name="Avisos", channel_type="announcement", post_policy="admins", is_active=True,
    )
    ch_duvidas, _ = await one_or_create(
        db, Channel,
        (Channel.tenant_id == tenant.id, Channel.space_id == space1.id, Channel.name == "Duvidas"),
        tenant_id=tenant.id, space_id=space1.id,
        name="Duvidas", channel_type="qna", post_policy="open", is_active=True,
    )

    # Space 2 — gated via product 2 (CS)
    space2, _ = await one_or_create(
        db, Space,
        (Space.tenant_id == tenant.id, Space.name == "Comunidade CS"),
        tenant_id=tenant.id,
        name="Comunidade CS",
        description="Espaco exclusivo para alunos de Customer Success.",
        is_active=True,
    )
    spaces.append(space2)

    ch_cs_geral, _ = await one_or_create(
        db, Channel,
        (Channel.tenant_id == tenant.id, Channel.space_id == space2.id, Channel.name == "Geral"),
        tenant_id=tenant.id, space_id=space2.id,
        name="Geral", channel_type="discussion", post_policy="open", is_active=True,
    )

    # Space 3 — open (no product linked)
    space3, _ = await one_or_create(
        db, Space,
        (Space.tenant_id == tenant.id, Space.name == "Espaco Livre"),
        tenant_id=tenant.id,
        name="Espaco Livre",
        description="Espaco aberto para todos os usuarios da plataforma.",
        is_active=True,
    )
    spaces.append(space3)

    ch_livre, _ = await one_or_create(
        db, Channel,
        (Channel.tenant_id == tenant.id, Channel.space_id == space3.id, Channel.name == "Apresentacoes"),
        tenant_id=tenant.id, space_id=space3.id,
        name="Apresentacoes", channel_type="discussion", post_policy="open", is_active=True,
    )

    # Posts & interactions
    post1, _ = await one_or_create(
        db, Post,
        (Post.tenant_id == tenant.id, Post.channel_id == ch_geral.id, Post.title == "Como voces estao usando o playbook?"),
        tenant_id=tenant.id, channel_id=ch_geral.id,
        user_id=student.id,
        title="Como voces estao usando o playbook?",
        body="Compartilhem exemplos de abordagem que funcionaram bem nas primeiras conversas.",
        likes_count=2, comments_count=2, is_hidden=False,
    )
    await one_or_create(
        db, Comment,
        (Comment.tenant_id == tenant.id, Comment.post_id == post1.id, Comment.user_id == manager.id),
        tenant_id=tenant.id, post_id=post1.id, user_id=manager.id,
        body="Boa pauta. Vou adicionar os melhores exemplos na reuniao semanal.",
        is_hidden=False,
    )
    await one_or_create(
        db, Comment,
        (Comment.tenant_id == tenant.id, Comment.post_id == post1.id, Comment.user_id == student2.id),
        tenant_id=tenant.id, post_id=post1.id, user_id=student2.id,
        body="Estou usando o script de qualificacao BANT, funcionou bem na ultima call.",
        is_hidden=False,
    )
    await one_or_create(
        db, PostLike,
        (PostLike.user_id == student2.id, PostLike.post_id == post1.id),
        user_id=student2.id, post_id=post1.id,
    )
    await one_or_create(
        db, PostLike,
        (PostLike.user_id == manager.id, PostLike.post_id == post1.id),
        user_id=manager.id, post_id=post1.id,
    )

    post2, _ = await one_or_create(
        db, Post,
        (Post.tenant_id == tenant.id, Post.channel_id == ch_avisos.id, Post.title == "Novo modulo liberado"),
        tenant_id=tenant.id, channel_id=ch_avisos.id,
        user_id=admin.id,
        title="Novo modulo liberado",
        body="O modulo de Execucao ja esta disponivel. Bons estudos!",
        likes_count=0, comments_count=0, is_hidden=False,
    )

    post3, _ = await one_or_create(
        db, Post,
        (Post.tenant_id == tenant.id, Post.channel_id == ch_duvidas.id, Post.title == "Diferenca entre ICP e Persona"),
        tenant_id=tenant.id, channel_id=ch_duvidas.id,
        user_id=student2.id,
        title="Diferenca entre ICP e Persona",
        body="Alguem pode explicar quando usar ICP vs Persona no processo comercial?",
        likes_count=1, comments_count=1, is_hidden=False,
    )
    await one_or_create(
        db, Comment,
        (Comment.tenant_id == tenant.id, Comment.post_id == post3.id, Comment.user_id == manager.id),
        tenant_id=tenant.id, post_id=post3.id, user_id=manager.id,
        body="ICP define o perfil ideal de empresa. Persona define o decisor dentro dela.",
        is_hidden=False,
    )
    await one_or_create(
        db, PostLike,
        (PostLike.user_id == student.id, PostLike.post_id == post3.id),
        user_id=student.id, post_id=post3.id,
    )

    post4, _ = await one_or_create(
        db, Post,
        (Post.tenant_id == tenant.id, Post.channel_id == ch_livre.id, Post.title == "Ola a todos!"),
        tenant_id=tenant.id, channel_id=ch_livre.id,
        user_id=student.id,
        title="Ola a todos!",
        body="Me chamo Bruna, sou AE no time comercial. Animada para aprender aqui!",
        likes_count=1, comments_count=0, is_hidden=False,
    )
    await one_or_create(
        db, PostLike,
        (PostLike.user_id == manager.id, PostLike.post_id == post4.id),
        user_id=manager.id, post_id=post4.id,
    )

    _ = (ch_cs_geral, post2)  # referenced, no extra interactions needed
    return spaces


# ─── Messaging ───────────────────────────────────────────────────────────────

async def seed_messaging(db: AsyncSession, tenant: Tenant, users: dict[str, User]) -> None:
    student = users["aluno@acmelearning.com"]
    manager = users["manager@acmelearning.com"]
    student2 = users["aluno2@acmelearning.com"]

    async def get_or_create_conversation(p1: User, p2: User) -> Conversation:
        # find existing conversation with exactly these two participants
        result = await db.execute(
            select(ConversationParticipant.conversation_id)
            .where(ConversationParticipant.user_id == p1.id)
        )
        p1_convs = set(result.scalars().all())
        result = await db.execute(
            select(ConversationParticipant.conversation_id)
            .where(ConversationParticipant.user_id == p2.id)
        )
        p2_convs = set(result.scalars().all())
        shared = p1_convs & p2_convs
        if shared:
            conv = await db.get(Conversation, next(iter(shared)))
            return conv  # type: ignore

        conv = Conversation(id=uuid.uuid4(), tenant_id=tenant.id)
        db.add(conv)
        await db.flush()
        for user in (p1, p2):
            db.add(ConversationParticipant(
                id=uuid.uuid4(), conversation_id=conv.id, user_id=user.id
            ))
        await db.flush()
        return conv

    # Conversa: student ↔ manager
    conv1 = await get_or_create_conversation(student, manager)
    for content, sender in (
        ("Oi Marcos, tenho uma duvida sobre o modulo de fechamento.", student),
        ("Claro Bruna, me conta o que esta acontecendo.", manager),
        ("Tenho dificuldade em identificar o momento certo para fazer a proposta.", student),
        ("Foque nos sinais de compra: urgencia e budget confirmados. A partir disso pode avançar.", manager),
    ):
        existing = await db.execute(
            select(Message).where(
                Message.conversation_id == conv1.id,
                Message.sender_id == sender.id,
                Message.content == content,
            )
        )
        if not existing.scalar_one_or_none():
            db.add(Message(id=uuid.uuid4(), conversation_id=conv1.id, sender_id=sender.id, content=content))
    await db.flush()

    # Conversa: student ↔ student2
    conv2 = await get_or_create_conversation(student, student2)
    for content, sender in (
        ("Diego, viu o post sobre ICP vs Persona? O Marcos explicou bem.", student),
        ("Vi sim! Salvei para revisar antes da proxima apresentacao.", student2),
    ):
        existing = await db.execute(
            select(Message).where(
                Message.conversation_id == conv2.id,
                Message.sender_id == sender.id,
                Message.content == content,
            )
        )
        if not existing.scalar_one_or_none():
            db.add(Message(id=uuid.uuid4(), conversation_id=conv2.id, sender_id=sender.id, content=content))
    await db.flush()


# ─── Quiz battles ─────────────────────────────────────────────────────────────

async def seed_quiz(
    db: AsyncSession,
    tenant: Tenant,
    users: dict[str, User],
    courses: list[Course],
) -> None:
    student = users["aluno@acmelearning.com"]
    student2 = users["aluno2@acmelearning.com"]
    course = courses[0]

    QUESTIONS = [
        {
            "id": 1,
            "text": "O que significa ICP?",
            "options": ["Ideal Customer Profile", "Internal Client Process", "Initial Contact Plan", "Integrated Campaign Plan"],
            "correct": 0,
        },
        {
            "id": 2,
            "text": "Qual etapa vem apos a qualificacao?",
            "options": ["Proposta", "Fechamento", "Diagnostico", "Prospeccao"],
            "correct": 2,
        },
        {
            "id": 3,
            "text": "BANT significa:",
            "options": [
                "Budget, Authority, Need, Timeline",
                "Buy, Assess, Negotiate, Track",
                "Brand, Audience, Network, Target",
                "Budget, Acquisition, Need, Test",
            ],
            "correct": 0,
        },
    ]

    # completed battle: student venceu
    existing = await db.execute(
        select(QuizBattle).where(
            QuizBattle.tenant_id == tenant.id,
            QuizBattle.challenger_id == student.id,
            QuizBattle.opponent_id == student2.id,
            QuizBattle.status == "completed",
        )
    )
    if not existing.scalar_one_or_none():
        battle = QuizBattle(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            challenger_id=student.id,
            opponent_id=student2.id,
            course_id=course.id,
            questions=QUESTIONS,
            status="completed",
            winner_id=student.id,
            expires_at=NOW + timedelta(hours=24),
        )
        db.add(battle)
        await db.flush()
        db.add(QuizBattleAnswer(
            id=uuid.uuid4(), battle_id=battle.id, user_id=student.id,
            answers={str(q["id"]): q["correct"] for q in QUESTIONS}, score=3,
        ))
        db.add(QuizBattleAnswer(
            id=uuid.uuid4(), battle_id=battle.id, user_id=student2.id,
            answers={str(q["id"]): (q["correct"] + 1) % 4 for q in QUESTIONS}, score=0,
        ))
        await db.flush()

    # pending battle: student2 desafiou student
    existing = await db.execute(
        select(QuizBattle).where(
            QuizBattle.tenant_id == tenant.id,
            QuizBattle.challenger_id == student2.id,
            QuizBattle.opponent_id == student.id,
            QuizBattle.status == "pending",
        )
    )
    if not existing.scalar_one_or_none():
        db.add(QuizBattle(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            challenger_id=student2.id,
            opponent_id=student.id,
            course_id=course.id,
            questions=QUESTIONS,
            status="pending",
            expires_at=NOW + timedelta(hours=24),
        ))
        await db.flush()


# ─── Email marketing ─────────────────────────────────────────────────────────

async def seed_email(
    db: AsyncSession,
    tenant: Tenant,
    users: dict[str, User],
) -> None:
    student = users["aluno@acmelearning.com"]
    manager = users["manager@acmelearning.com"]

    audience, _ = await one_or_create(
        db, EmailAudience,
        (EmailAudience.tenant_id == tenant.id, EmailAudience.name == "Todos os Alunos"),
        tenant_id=tenant.id,
        name="Todos os Alunos",
        filter_json={"role": "student"},
    )
    audience_mgr, _ = await one_or_create(
        db, EmailAudience,
        (EmailAudience.tenant_id == tenant.id, EmailAudience.name == "Gestores"),
        tenant_id=tenant.id,
        name="Gestores",
        filter_json={"role": "manager"},
    )

    template, _ = await one_or_create(
        db, EmailTemplate,
        (EmailTemplate.tenant_id == tenant.id, EmailTemplate.name == "Boas-vindas Comercial"),
        tenant_id=tenant.id,
        name="Boas-vindas Comercial",
        subject="Bem-vindo ao Onboarding Comercial B2B!",
        html_body="<h1>Ola {{user_name}}!</h1><p>Sua jornada de aprendizado comecou. Acesse a plataforma e comece agora.</p>",
    )
    template_update, _ = await one_or_create(
        db, EmailTemplate,
        (EmailTemplate.tenant_id == tenant.id, EmailTemplate.name == "Atualizacao de Conteudo"),
        tenant_id=tenant.id,
        name="Atualizacao de Conteudo",
        subject="Novo conteudo disponivel para voce",
        html_body="<h1>Novidade na plataforma!</h1><p>Ola {{user_name}}, um novo modulo foi liberado para voce.</p>",
    )

    campaign, _ = await one_or_create(
        db, EmailCampaign,
        (EmailCampaign.tenant_id == tenant.id, EmailCampaign.name == "Lancamento Onboarding Comercial"),
        tenant_id=tenant.id,
        name="Lancamento Onboarding Comercial",
        template_id=template.id,
        audience_id=audience.id,
        status="sent",
        sent_at=NOW - timedelta(days=10),
        sent_count=2,
    )

    automation, _ = await one_or_create(
        db, EmailAutomation,
        (EmailAutomation.tenant_id == tenant.id, EmailAutomation.name == "Sequencia de Engajamento"),
        tenant_id=tenant.id,
        name="Sequencia de Engajamento",
        trigger_event="enrollment.active",
        is_active=True,
        steps=[
            {"delay_days": 0, "template": "enrollment_access_granted"},
            {"delay_days": 3, "template": "course_reminder"},
            {"delay_days": 7, "template": "streak_at_risk"},
        ],
    )

    for user, status, opened in (
        (student, "opened", NOW - timedelta(days=9)),
        (manager, "sent", None),
    ):
        existing = await db.execute(
            select(EmailSend).where(
                EmailSend.campaign_id == campaign.id,
                EmailSend.user_id == user.id,
            )
        )
        if not existing.scalar_one_or_none():
            db.add(EmailSend(
                id=uuid.uuid4(),
                campaign_id=campaign.id,
                user_id=user.id,
                email=user.email,
                status=status,
                sent_at=NOW - timedelta(days=10),
                opened_at=opened,
            ))
    await db.flush()

    _ = (audience_mgr, template_update, automation)


# ─── Webhooks & leads ─────────────────────────────────────────────────────────

async def seed_webhooks(
    db: AsyncSession,
    tenant: Tenant,
    products: list[Product],
    users: dict[str, User],
) -> None:
    student = users["aluno@acmelearning.com"]

    existing = await db.execute(
        select(WebhookLog).where(
            WebhookLog.tenant_id == tenant.id,
            WebhookLog.provider == "hotmart",
            WebhookLog.event_type == "PURCHASE_COMPLETE",
        )
    )
    if not existing.scalar_one_or_none():
        db.add(WebhookLog(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            provider="hotmart",
            event_type="PURCHASE_COMPLETE",
            payload={
                "event": "PURCHASE_COMPLETE",
                "data": {
                    "buyer": {"email": student.email, "name": student.name},
                    "product": {"id": "HM-1000"},
                    "purchase": {"status": "APPROVED", "transaction": "HM-TRX-001"},
                },
            },
            signature_valid=True,
            processed=True,
            attempts=1,
        ))

    existing = await db.execute(
        select(WebhookLog).where(
            WebhookLog.tenant_id == tenant.id,
            WebhookLog.provider == "stripe",
            WebhookLog.event_type == "checkout.session.completed",
        )
    )
    if not existing.scalar_one_or_none():
        db.add(WebhookLog(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            provider="stripe",
            event_type="checkout.session.completed",
            payload={
                "type": "checkout.session.completed",
                "data": {"object": {"customer_email": "novo@cliente.com", "metadata": {"product_id": str(products[0].id)}}},
            },
            signature_valid=True,
            processed=True,
            attempts=1,
        ))

    existing = await db.execute(
        select(Lead).where(
            Lead.tenant_id == tenant.id,
            Lead.email == "lead@exemplo.com",
        )
    )
    if not existing.scalar_one_or_none():
        db.add(Lead(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email="lead@exemplo.com",
            name="Lead Exemplo",
            source="landing_page",
            utm_source="google",
            utm_medium="cpc",
            utm_campaign="onboarding-comercial",
            product_id=products[0].id,
        ))
    await db.flush()


# ─── Landing page & notifications ────────────────────────────────────────────

async def seed_marketing(
    db: AsyncSession,
    tenant: Tenant,
    products: list[Product],
    users: dict[str, User],
) -> None:
    page, _ = await one_or_create(
        db, LandingPage,
        (LandingPage.tenant_id == tenant.id, LandingPage.slug == "onboarding-comercial"),
        tenant_id=tenant.id,
        slug="onboarding-comercial",
        title="Onboarding Comercial B2B",
        seo_description="Treinamento pratico para equipes comerciais B2B.",
        seo_keywords="vendas,b2b,onboarding",
        status="published",
        product_id=products[0].id,
        page_metadata={"hero": "Acelere o ramp-up comercial", "cta": "Comecar agora"},
    )
    await one_or_create(
        db, PageView,
        (PageView.page_id == page.id, PageView.ip_hash == "seed-localhost"),
        page_id=page.id,
        ip_hash="seed-localhost",
        user_agent="Seed Browser",
        utm_source="google",
        utm_medium="cpc",
        utm_campaign="onboarding-comercial",
    )

    for email, title, body in (
        ("aluno@acmelearning.com", "Nova trilha disponivel", "Voce ja pode continuar o onboarding comercial."),
        ("aluno2@acmelearning.com", "Badge conquistado!", "Voce ganhou o badge Primeira Semana. Continue assim!"),
        ("manager@acmelearning.com", "Meta da equipe atualizada", "Acompanhe o progresso do time no dashboard gerencial."),
    ):
        await one_or_create(
            db, Notification,
            (Notification.tenant_id == tenant.id, Notification.user_id == users[email].id, Notification.title == title),
            tenant_id=tenant.id,
            user_id=users[email].id,
            type="seed",
            title=title,
            body=body,
            data={"source": "scripts/seed.py"},
            is_read=False,
        )


# ─── Audit logs ──────────────────────────────────────────────────────────────

async def seed_audit(
    db: AsyncSession,
    tenant: Tenant,
    users: dict[str, User],
    products: list[Product],
) -> None:
    admin = users["admin@acmelearning.com"]
    entries = [
        ("create", "product", str(products[0].id), {"title": products[0].title}),
        ("publish", "product", str(products[0].id), {"status": "published"}),
        ("create", "product", str(products[1].id), {"title": products[1].title}),
        ("suspend", "user", str(users["aluno2@acmelearning.com"].id), {"reason": "seed"}),
        ("unsuspend", "user", str(users["aluno2@acmelearning.com"].id), {}),
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
                tenant_id=tenant.id,
                user_id=admin.id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
            ))
    await db.flush()


# ─── Main ─────────────────────────────────────────────────────────────────────

async def run() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        tenant = await seed_tenant(db)
        company = await seed_company(db, tenant)
        users = await seed_users(db, tenant, company)
        courses, lessons = await seed_courses(db, tenant, users["admin@acmelearning.com"])
        spaces = await seed_community(db, tenant, users)
        products = await seed_products(db, tenant, company, courses, spaces, users)
        await seed_activity(db, tenant, company, users, lessons)
        await seed_messaging(db, tenant, users)
        await seed_quiz(db, tenant, users, courses)
        await seed_email(db, tenant, users)
        await seed_webhooks(db, tenant, products, users)
        await seed_marketing(db, tenant, products, users)
        await seed_audit(db, tenant, users, products)
        await db.commit()

    await engine.dispose()
    print("Seed concluido.")
    print("Tenant: localhost ou acme.localhost")
    print(f"Senha padrao: {PASSWORD}")
    print("Usuarios:")
    print("  admin@acmelearning.com   — admin")
    print("  manager@acmelearning.com — manager (Acme Comercial)")
    print("  aluno@acmelearning.com   — student (Acme Comercial)")
    print("  aluno2@acmelearning.com  — student (Acme Comercial)")


if __name__ == "__main__":
    asyncio.run(run())
