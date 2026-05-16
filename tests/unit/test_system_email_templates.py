import pytest

from app.services.system_email import (
    SystemEmailTemplateKey,
    list_system_email_templates,
    render_system_email_template,
)


def test_catalog_maps_expected_system_templates():
    keys = {template.key for template in list_system_email_templates()}

    assert SystemEmailTemplateKey.AUTH_MAGIC_LINK in keys
    assert SystemEmailTemplateKey.AUTH_PASSWORD_RESET in keys
    assert SystemEmailTemplateKey.COMPANY_INVITE_MEMBER in keys
    assert SystemEmailTemplateKey.ENROLLMENT_ACCESS_GRANTED in keys
    assert SystemEmailTemplateKey.WEBHOOK_PROCESSING_FAILED in keys


def test_render_system_email_template_escapes_html_values():
    rendered = render_system_email_template(
        SystemEmailTemplateKey.AUTH_MAGIC_LINK,
        {
            "app_name": "Acme <Learning>",
            "user_name": "Bruna",
            "magic_link_url": "https://app.example.com/magic?token=<abc>",
            "expires_minutes": 15,
        },
    )

    assert "Seu link de acesso" in rendered.subject
    assert "Acme &lt;Learning&gt;" in rendered.html_body
    assert "&lt;abc&gt;" in rendered.html_body


def test_render_system_email_template_requires_variables():
    with pytest.raises(ValueError, match="magic_link_url"):
        render_system_email_template(
            SystemEmailTemplateKey.AUTH_MAGIC_LINK,
            {
                "app_name": "Acme",
                "user_name": "Bruna",
                "expires_minutes": 15,
            },
        )
