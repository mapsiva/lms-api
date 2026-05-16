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
from app.models.community import Channel, Comment, Post, PostLike, Space
from app.models.company import Company, CompanyGoal, CompanyMember
from app.models.course import Course, Lesson, Module
from app.models.enrollment import Enrollment
from app.models.gamification import Badge, UserBadge, UserLevel, UserStreak, XPEvent
from app.models.landing_page import LandingPage, PageView
from app.models.menu import MenuConfig
from app.models.notification import Notification
from app.models.product import Product, ProductCourse
from app.models.progress import LessonProgress, Note
from app.models.tenant import Tenant
from app.models.user import User

PASSWORD = "Senha123!"


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


async def seed_tenant(db: AsyncSession) -> Tenant:
    tenant, _ = await one_or_create(
        db,
        Tenant,
        (Tenant.slug == "acme",),
        slug="acme",
        name="Acme Learning",
        custom_domain="localhost",
        subdomain="acme.localhost",
        app_name="Acme Learning",
        primary_color="#2563EB",
        secondary_color="#16A34A",
        font_family="Inter",
        plan="pro",
        features={
            "community": True,
            "gamification": True,
            "companies": True,
            "analytics": True,
        },
    )

    for role, items in (("student", STUDENT_MENU), ("manager", MANAGER_MENU), ("admin", ADMIN_MENU)):
        await one_or_create(
            db,
            MenuConfig,
            (MenuConfig.tenant_id == tenant.id, MenuConfig.role == role),
            tenant_id=tenant.id,
            role=role,
            items=items,
        )
    return tenant


async def seed_users(db: AsyncSession, tenant: Tenant, company: Company | None = None) -> dict[str, User]:
    legacy_result = await db.execute(
        select(User).where(User.tenant_id == tenant.id, User.email.like("%@acme.test"))
    )
    for legacy_user in legacy_result.scalars():
        await db.delete(legacy_user)
    await db.flush()

    users = {}
    for email, name, role, bio in (
        ("admin@acmelearning.com", "Ana Admin", "admin", "Admin da plataforma Acme Learning."),
        ("manager@acmelearning.com", "Marcos Manager", "manager", "Gestor do time Comercial."),
        ("aluno@acmelearning.com", "Bruna Aluna", "student", "Estudante focada em vendas consultivas."),
        ("aluno2@acmelearning.com", "Diego Aluno", "student", "Estudante do time de atendimento."),
    ):
        user, _ = await one_or_create(
            db,
            User,
            (User.tenant_id == tenant.id, User.email == email),
            tenant_id=tenant.id,
            email=email,
            name=name,
            password_hash=hash_password(PASSWORD),
            role=role,
            company_id=company.id if company and role in {"manager", "student"} else None,
            is_active=True,
            is_suspended=False,
            bio=bio,
        )
        users[email] = user
    return users


async def seed_company(db: AsyncSession, tenant: Tenant) -> Company:
    company, _ = await one_or_create(
        db,
        Company,
        (Company.tenant_id == tenant.id, Company.legal_name == "Acme Comercial Ltda"),
        tenant_id=tenant.id,
        cnpj="12.345.678/0001-90",
        legal_name="Acme Comercial Ltda",
        trade_name="Acme Comercial",
        max_seats=80,
        status="active",
        contract_start=datetime.now(timezone.utc) - timedelta(days=45),
        contract_end=datetime.now(timezone.utc) + timedelta(days=320),
    )
    return company


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
            db,
            Course,
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

        for module_index, (module_title, lesson_titles) in enumerate(modules):
            module, _ = await one_or_create(
                db,
                Module,
                (Module.tenant_id == tenant.id, Module.course_id == course.id, Module.title == module_title),
                tenant_id=tenant.id,
                course_id=course.id,
                title=module_title,
                order_index=module_index,
                is_hidden=False,
            )
            for lesson_index, lesson_title in enumerate(lesson_titles):
                lesson, _ = await one_or_create(
                    db,
                    Lesson,
                    (Lesson.tenant_id == tenant.id, Lesson.module_id == module.id, Lesson.title == lesson_title),
                    tenant_id=tenant.id,
                    module_id=module.id,
                    title=lesson_title,
                    order_index=lesson_index,
                    lesson_type="video",
                    is_hidden=False,
                    is_free_preview=lesson_index == 0,
                    duration_seconds=480 + (lesson_index * 180),
                    video_provider="youtube",
                    video_external_id="dQw4w9WgXcQ",
                    ai_summary=f"Resumo pratico da aula {lesson_title.lower()}.",
                    transcript_text={"items": [{"text": f"Conteudo demonstrativo de {lesson_title}."}]},
                )
                lessons.append(lesson)
    return courses, lessons


async def seed_products_and_enrollments(
    db: AsyncSession,
    tenant: Tenant,
    company: Company,
    courses: list[Course],
    users: dict[str, User],
) -> list[Product]:
    products: list[Product] = []
    for index, course in enumerate(courses):
        product, _ = await one_or_create(
            db,
            Product,
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
            db,
            ProductCourse,
            (ProductCourse.product_id == product.id, ProductCourse.course_id == course.id),
            product_id=product.id,
            course_id=course.id,
            order_index=index,
        )

    for user in users.values():
        if user.role == "admin":
            continue
        for product in products:
            await one_or_create(
                db,
                Enrollment,
                (Enrollment.tenant_id == tenant.id, Enrollment.user_id == user.id, Enrollment.product_id == product.id),
                tenant_id=tenant.id,
                user_id=user.id,
                product_id=product.id,
                status="active",
                enrolled_by="admin",
                company_id=company.id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            )
    return products


async def seed_activity(db: AsyncSession, tenant: Tenant, company: Company, users: dict[str, User], lessons: list[Lesson]) -> None:
    student = users["aluno@acmelearning.com"]
    second_student = users["aluno2@acmelearning.com"]
    manager = users["manager@acmelearning.com"]

    for user, team, job_role in (
        (student, "Comercial", "Account Executive"),
        (second_student, "Atendimento", "Customer Support"),
        (manager, "Comercial", "Sales Manager"),
    ):
        user.company_id = company.id
        await one_or_create(
            db,
            CompanyMember,
            (CompanyMember.company_id == company.id, CompanyMember.user_id == user.id),
            company_id=company.id,
            user_id=user.id,
            team=team,
            job_role=job_role,
            is_active=True,
        )

    for index, lesson in enumerate(lessons[:7]):
        await one_or_create(
            db,
            LessonProgress,
            (LessonProgress.user_id == student.id, LessonProgress.lesson_id == lesson.id),
            user_id=student.id,
            lesson_id=lesson.id,
            completed_at=datetime.now(timezone.utc) - timedelta(days=max(1, 7 - index)) if index < 5 else None,
            last_watched_at=datetime.now(timezone.utc) - timedelta(days=max(1, 5 - index)),
            watch_seconds=lesson.duration_seconds or 300,
        )
        await one_or_create(
            db,
            XPEvent,
            (XPEvent.tenant_id == tenant.id, XPEvent.user_id == student.id, XPEvent.reference_id == lesson.id),
            tenant_id=tenant.id,
            user_id=student.id,
            company_id=company.id,
            action="lesson_completed",
            amount=50,
            reference_id=lesson.id,
            reference_type="lesson",
        )

    await one_or_create(
        db,
        Note,
        (Note.user_id == student.id, Note.lesson_id == lessons[0].id),
        user_id=student.id,
        lesson_id=lessons[0].id,
        content="Revisar a parte de criterios de qualificacao antes da proxima call.",
        video_timestamp_seconds=210,
    )
    await one_or_create(
        db,
        UserLevel,
        (UserLevel.tenant_id == tenant.id, UserLevel.user_id == student.id),
        tenant_id=tenant.id,
        user_id=student.id,
        total_xp=350,
        level=4,
    )
    await one_or_create(
        db,
        UserStreak,
        (UserStreak.user_id == student.id,),
        user_id=student.id,
        company_id=company.id,
        current_streak=6,
        longest_streak=14,
        last_activity_date=datetime.now(timezone.utc),
        shields_available=1,
    )
    badge, _ = await one_or_create(
        db,
        Badge,
        (Badge.tenant_id == tenant.id, Badge.name == "Primeira Semana"),
        tenant_id=tenant.id,
        name="Primeira Semana",
        description="Concluiu atividades em uma semana de onboarding.",
        category="completion",
        rarity="common",
        rule_event="lesson_completed",
        rule_conditions={"min_completed_lessons": 5},
        xp_reward=100,
        is_active=True,
    )
    await one_or_create(
        db,
        UserBadge,
        (UserBadge.user_id == student.id, UserBadge.badge_id == badge.id),
        user_id=student.id,
        badge_id=badge.id,
    )
    await one_or_create(
        db,
        CompanyGoal,
        (CompanyGoal.company_id == company.id, CompanyGoal.title == "Concluir onboarding comercial"),
        company_id=company.id,
        title="Concluir onboarding comercial",
        target_metric="completion_rate",
        target_value=80,
        course_id=None,
        deadline=datetime.now(timezone.utc) + timedelta(days=30),
        status="active",
    )


async def seed_community(db: AsyncSession, tenant: Tenant, users: dict[str, User]) -> None:
    space, _ = await one_or_create(
        db,
        Space,
        (Space.tenant_id == tenant.id, Space.name == "Comunidade Acme"),
        tenant_id=tenant.id,
        name="Comunidade Acme",
        description="Espaco para duvidas, boas praticas e trocas entre times.",
        is_active=True,
    )
    channel, _ = await one_or_create(
        db,
        Channel,
        (Channel.tenant_id == tenant.id, Channel.space_id == space.id, Channel.name == "Geral"),
        tenant_id=tenant.id,
        space_id=space.id,
        name="Geral",
        channel_type="discussion",
        post_policy="open",
        is_active=True,
    )
    post, _ = await one_or_create(
        db,
        Post,
        (Post.tenant_id == tenant.id, Post.channel_id == channel.id, Post.title == "Como voces estao usando o playbook?"),
        tenant_id=tenant.id,
        channel_id=channel.id,
        user_id=users["aluno@acmelearning.com"].id,
        title="Como voces estao usando o playbook?",
        body="Compartilhem exemplos de abordagem que funcionaram bem nas primeiras conversas.",
        likes_count=1,
        comments_count=1,
        is_hidden=False,
    )
    await one_or_create(
        db,
        Comment,
        (Comment.tenant_id == tenant.id, Comment.post_id == post.id, Comment.user_id == users["manager@acmelearning.com"].id),
        tenant_id=tenant.id,
        post_id=post.id,
        user_id=users["manager@acmelearning.com"].id,
        body="Boa pauta. Vou adicionar os melhores exemplos na reuniao semanal.",
        is_hidden=False,
    )
    await one_or_create(
        db,
        PostLike,
        (PostLike.user_id == users["aluno2@acmelearning.com"].id, PostLike.post_id == post.id),
        user_id=users["aluno2@acmelearning.com"].id,
        post_id=post.id,
    )


async def seed_marketing(db: AsyncSession, tenant: Tenant, products: list[Product], users: dict[str, User]) -> None:
    page, _ = await one_or_create(
        db,
        LandingPage,
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
        db,
        PageView,
        (PageView.page_id == page.id, PageView.ip_hash == "seed-localhost"),
        page_id=page.id,
        ip_hash="seed-localhost",
        user_agent="Seed Browser",
        utm_source="seed",
        utm_medium="local",
        utm_campaign="frontend-test",
    )
    for email, title, body in (
        ("aluno@acmelearning.com", "Nova trilha disponivel", "Voce ja pode continuar o onboarding comercial."),
        ("manager@acmelearning.com", "Meta da equipe atualizada", "Acompanhe o progresso do time no dashboard gerencial."),
    ):
        await one_or_create(
            db,
            Notification,
            (Notification.tenant_id == tenant.id, Notification.user_id == users[email].id, Notification.title == title),
            tenant_id=tenant.id,
            user_id=users[email].id,
            type="seed",
            title=title,
            body=body,
            data={"source": "scripts/seed.py"},
            is_read=False,
        )


async def run() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        tenant = await seed_tenant(db)
        company = await seed_company(db, tenant)
        users = await seed_users(db, tenant, company)
        courses, lessons = await seed_courses(db, tenant, users["admin@acmelearning.com"])
        products = await seed_products_and_enrollments(db, tenant, company, courses, users)
        await seed_activity(db, tenant, company, users, lessons)
        await seed_community(db, tenant, users)
        await seed_marketing(db, tenant, products, users)
        await db.commit()

    await engine.dispose()
    print("Seed concluido.")
    print("Tenant: localhost ou acme.localhost")
    print(f"Senha padrao: {PASSWORD}")
    print("Usuarios: admin@acmelearning.com, manager@acmelearning.com, aluno@acmelearning.com, aluno2@acmelearning.com")


if __name__ == "__main__":
    asyncio.run(run())
