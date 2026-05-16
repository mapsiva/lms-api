"""Unit tests for email Celery tasks."""
from unittest.mock import MagicMock, patch

from app.tasks.email import _append_tracking_pixel, BATCH_SIZE


def test_append_tracking_pixel_with_body():
    html = "<html><body>Hello</body></html>"
    result = _append_tracking_pixel(html, "send-123", "https://app.example.com")
    assert "send-123/open.gif" in result
    assert result.endswith("</body></html>")


def test_append_tracking_pixel_without_body():
    html = "<p>Hello</p>"
    result = _append_tracking_pixel(html, "send-123", "https://app.example.com")
    assert "send-123/open.gif" in result


@patch("app.tasks.email.send_email")
@patch("app.tasks.email.get_settings")
def test_send_transactional_email_task(mock_settings, mock_send_email):
    mock_settings.return_value = MagicMock(frontend_url="https://app.example.com")
    mock_send_email.return_value = "msg-123"

    from app.tasks.email import send_transactional_email_task

    result = send_transactional_email_task.run(
        to="user@example.com",
        subject="Test",
        html_body="<p>Hi</p>",
        send_id="send-123",
        track_opens=True,
    )
    assert result == "msg-123"
    mock_send_email.assert_called_once()
    call = mock_send_email.call_args
    assert call.args[0] == "user@example.com"
    assert "open.gif" in call.args[2]


@patch("app.tasks.email.send_email")
def test_send_system_email_task(mock_send_email):
    mock_send_email.return_value = "msg-456"

    from app.tasks.email import send_system_email_task

    result = send_system_email_task.run(
        to="user@example.com",
        template_key="company.invite_member",
        context={
            "app_name": "Acme",
            "company_name": "Acme Comercial",
            "user_name": "User",
            "invite_url": "https://app.example.com/invites/token/accept",
        },
    )

    assert result == "msg-456"
    call = mock_send_email.call_args
    assert call.args[0] == "user@example.com"
    assert "Acme Comercial" in call.args[1]
    assert "Aceitar convite" in call.args[2]


@patch("app.tasks.email.send_email")
@patch("app.tasks.email.get_settings")
def test_send_campaign_batch_task(mock_settings, mock_send_email):
    mock_settings.return_value = MagicMock(frontend_url="https://app.example.com")

    from app.tasks.email import send_campaign_batch_task

    batch = [
        {"email": "a@example.com", "send_id": "s1"},
        {"email": "b@example.com", "send_id": "s2"},
    ]
    send_campaign_batch_task.run(batch, "camp-1", "Subject", "<p>Body</p>")
    assert mock_send_email.call_count == 2


def test_batch_size_constant():
    assert BATCH_SIZE == 100
