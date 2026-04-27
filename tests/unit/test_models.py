import uuid

from app.models.tenant import Tenant
from app.models.course import Course, Module, Lesson
from app.models.progress import LessonProgress, Note
from app.models.product import Product, ProductCourse
from app.models.enrollment import Enrollment
from app.models.webhook import WebhookLog, Lead
from app.models.company import Company, CompanyMember, CompanyGoal


def test_tenant_instantiation():
    t = Tenant(slug="acme", name="Acme Corp")
    assert t.slug == "acme"
    assert t.name == "Acme Corp"


def test_tenant_defaults():
    t = Tenant(slug="acme", name="Acme Corp")
    assert t.id is None or isinstance(t.id, uuid.UUID)
    assert t.plan is None or t.plan == "free"


def test_tenant_tablename():
    assert Tenant.__tablename__ == "tenants"


def test_tenant_optional_fields():
    t = Tenant(
        slug="acme",
        name="Acme Corp",
        custom_domain="acme.com",
        logo_url="https://cdn.acme.com/logo.png",
        primary_color="#FF5733",
        features={"gamification": True, "community": False},
    )
    assert t.custom_domain == "acme.com"
    assert t.primary_color == "#FF5733"
    assert t.features["gamification"] is True


# ── T18: Course / Module / Lesson ─────────────────────────────────────────────

def test_course_tablename():
    assert Course.__tablename__ == "courses"


def test_course_instantiation():
    tid = uuid.uuid4()
    c = Course(tenant_id=tid, title="Python Basics", slug="python-basics")
    assert c.title == "Python Basics"
    assert c.slug == "python-basics"


def test_course_defaults():
    c = Course(tenant_id=uuid.uuid4(), title="T", slug="t")
    assert c.status is None or c.status == "draft"
    assert c.is_free is None or c.is_free is False


def test_module_tablename():
    assert Module.__tablename__ == "modules"


def test_module_instantiation():
    m = Module(tenant_id=uuid.uuid4(), course_id=uuid.uuid4(), title="Intro", order_index=1)
    assert m.title == "Intro"
    assert m.order_index == 1


def test_lesson_tablename():
    assert Lesson.__tablename__ == "lessons"


def test_lesson_video_fields():
    l = Lesson(
        tenant_id=uuid.uuid4(),
        module_id=uuid.uuid4(),
        title="First Lesson",
        video_provider="bunny",
        video_external_id="abc123",
        video_metadata={"duration": 300},
    )
    assert l.video_provider == "bunny"
    assert l.video_metadata["duration"] == 300


def test_lesson_drip_fields():
    l = Lesson(
        tenant_id=uuid.uuid4(),
        module_id=uuid.uuid4(),
        title="Drip Lesson",
        drip_type="days_after_enrollment",
        drip_value={"days": 7},
    )
    assert l.drip_type == "days_after_enrollment"
    assert l.drip_value["days"] == 7


def test_lesson_transcript_field():
    l = Lesson(
        tenant_id=uuid.uuid4(),
        module_id=uuid.uuid4(),
        title="Transcript Lesson",
        transcript_text={"words": [{"word": "hello", "start": 0.0}]},
    )
    assert l.transcript_text["words"][0]["word"] == "hello"


# ── T19: LessonProgress / Note ───────────────────────────────────────────────

def test_progress_tablename():
    assert LessonProgress.__tablename__ == "lesson_progress"


def test_progress_instantiation():
    p = LessonProgress(user_id=uuid.uuid4(), lesson_id=uuid.uuid4(), watch_seconds=120)
    assert p.watch_seconds == 120
    assert p.completed_at is None


def test_note_tablename():
    assert Note.__tablename__ == "notes"


def test_note_instantiation():
    n = Note(user_id=uuid.uuid4(), lesson_id=uuid.uuid4(), content="Great point!", video_timestamp_seconds=42)
    assert n.content == "Great point!"
    assert n.video_timestamp_seconds == 42


# ── T20: Product / Enrollment ────────────────────────────────────────────────

def test_product_tablename():
    assert Product.__tablename__ == "products"


def test_product_instantiation():
    p = Product(tenant_id=uuid.uuid4(), type="course", title="LMS Course", slug="lms-course")
    assert p.type == "course"
    assert p.slug == "lms-course"


def test_product_gateway_ids_jsonb():
    p = Product(
        tenant_id=uuid.uuid4(), type="bundle", title="Bundle", slug="bundle",
        gateway_ids={"hotmart": "HOT123", "kiwify": "KIW456"},
    )
    assert p.gateway_ids["hotmart"] == "HOT123"


def test_enrollment_tablename():
    assert Enrollment.__tablename__ == "enrollments"


def test_enrollment_instantiation():
    e = Enrollment(
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        status="active",
        enrolled_by="webhook",
    )
    assert e.status == "active"
    assert e.enrolled_by == "webhook"


def test_enrollment_status_values():
    for status in ("active", "expired", "suspended", "cancelled", "refunded"):
        e = Enrollment(tenant_id=uuid.uuid4(), user_id=uuid.uuid4(), product_id=uuid.uuid4(), status=status)
        assert e.status == status


# ── T26: WebhookLog / Lead ───────────────────────────────────────────────────

def test_webhook_log_tablename():
    assert WebhookLog.__tablename__ == "webhook_logs"


def test_webhook_log_instantiation():
    wl = WebhookLog(
        tenant_id=uuid.uuid4(),
        provider="hotmart",
        event_type="PURCHASE_APPROVED",
        payload={"order_id": "123"},
        signature_valid=True,
    )
    assert wl.provider == "hotmart"
    assert wl.event_type == "PURCHASE_APPROVED"
    assert wl.signature_valid is True


def test_webhook_log_defaults():
    wl = WebhookLog(tenant_id=uuid.uuid4(), provider="stripe", event_type="charge.succeeded")
    assert wl.processed is None or wl.processed is False
    assert wl.attempts is None or wl.attempts == 0


def test_lead_tablename():
    assert Lead.__tablename__ == "leads"


def test_lead_instantiation():
    l = Lead(
        tenant_id=uuid.uuid4(),
        email="bruno@corp.com",
        source="landing_page",
        utm_source="google",
        utm_campaign="spring2026",
    )
    assert l.email == "bruno@corp.com"
    assert l.source == "landing_page"
    assert l.utm_campaign == "spring2026"


# ── T34: Company / CompanyMember / CompanyGoal ───────────────────────────────

def test_company_tablename():
    assert Company.__tablename__ == "companies"


def test_company_instantiation():
    c = Company(tenant_id=uuid.uuid4(), legal_name="Acme Corp")
    assert c.legal_name == "Acme Corp"
    assert c.status == "active" or c.status is None


def test_company_member_tablename():
    assert CompanyMember.__tablename__ == "company_members"


def test_company_member_instantiation():
    cm = CompanyMember(company_id=uuid.uuid4(), user_id=uuid.uuid4(), team="Engineering")
    assert cm.team == "Engineering"


def test_company_goal_tablename():
    assert CompanyGoal.__tablename__ == "company_goals"


def test_company_goal_instantiation():
    cg = CompanyGoal(
        company_id=uuid.uuid4(),
        title="80% Compliance",
        target_metric="completion_rate",
        target_value=80.0,
    )
    assert cg.title == "80% Compliance"
    assert cg.target_metric == "completion_rate"
