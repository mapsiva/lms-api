"""System email template catalog and rendering."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from html import escape
from typing import Any


class SystemEmailTemplateKey(StrEnum):
    AUTH_MAGIC_LINK = "auth.magic_link"
    AUTH_PASSWORD_RESET = "auth.password_reset"
    AUTH_PASSWORD_CHANGED = "auth.password_changed"
    USER_WELCOME = "user.welcome"
    COMPANY_INVITE_MEMBER = "company.invite_member"
    COMPANY_MEMBER_WELCOME = "company.member_welcome"
    COMPANY_BULK_IMPORT_MEMBER_WELCOME = "company.bulk_import_member_welcome"
    ENROLLMENT_ACCESS_GRANTED = "enrollment.access_granted"
    ENROLLMENT_ACCESS_REACTIVATED = "enrollment.access_reactivated"
    ENROLLMENT_ACCESS_SUSPENDED = "enrollment.access_suspended"
    ENROLLMENT_ACCESS_CANCELLED = "enrollment.access_cancelled"
    ENROLLMENT_ACCESS_REFUNDED = "enrollment.access_refunded"
    ENROLLMENT_ACCESS_EXPIRING = "enrollment.access_expiring"
    COURSE_DRIP_LESSON_RELEASED = "course.drip_lesson_released"
    COURSE_COMPLETED = "course.completed"
    COURSE_CERTIFICATE_ISSUED = "course.certificate_issued"
    COMMUNITY_COMMENT_REPLY = "community.comment_reply"
    COMMUNITY_MENTION = "community.mention"
    COMMUNITY_POST_REPORTED = "community.post_reported"
    GAMIFICATION_BADGE_EARNED = "gamification.badge_earned"
    GAMIFICATION_LEVEL_UP = "gamification.level_up"
    GAMIFICATION_STREAK_AT_RISK = "gamification.streak_at_risk"
    GAMIFICATION_GOAL_ACHIEVED = "gamification.goal_achieved"
    QUIZ_BATTLE_INVITE = "quiz_battle.invite"
    QUIZ_BATTLE_RESULT = "quiz_battle.result"
    MESSAGE_NEW_DIRECT = "message.new_direct"
    NOTIFICATION_BROADCAST = "notification.broadcast"
    TRANSCRIPTION_READY = "transcription.ready"
    TRANSCRIPTION_FAILED = "transcription.failed"
    WEBHOOK_PROCESSING_FAILED = "webhook.processing_failed"


@dataclass(frozen=True)
class SystemEmailTemplate:
    key: SystemEmailTemplateKey
    name: str
    description: str
    category: str
    subject: str
    html_body: str
    required_variables: tuple[str, ...]
    sample_context: dict[str, Any]


@dataclass(frozen=True)
class RenderedSystemEmail:
    key: str
    subject: str
    html_body: str


_TOKEN_RE = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")


def _template(
    key: SystemEmailTemplateKey,
    name: str,
    description: str,
    category: str,
    subject: str,
    html_body: str,
    required_variables: tuple[str, ...],
    sample_context: dict[str, Any],
) -> SystemEmailTemplate:
    return SystemEmailTemplate(
        key=key,
        name=name,
        description=description,
        category=category,
        subject=subject,
        html_body=html_body,
        required_variables=required_variables,
        sample_context=sample_context,
    )


SYSTEM_EMAIL_TEMPLATES: dict[SystemEmailTemplateKey, SystemEmailTemplate] = {
    SystemEmailTemplateKey.AUTH_MAGIC_LINK: _template(
        SystemEmailTemplateKey.AUTH_MAGIC_LINK,
        "Magic link de acesso",
        "Enviado quando o usuario solicita login sem senha.",
        "auth",
        "Seu link de acesso ao {{app_name}}",
        """
        <p>Ola, {{user_name}}.</p>
        <p>Use o link abaixo para acessar sua conta no {{app_name}}.</p>
        <p><a href="{{magic_link_url}}">Entrar agora</a></p>
        <p>Este link expira em {{expires_minutes}} minutos.</p>
        """,
        ("app_name", "user_name", "magic_link_url", "expires_minutes"),
        {
            "app_name": "Acme Learning",
            "user_name": "Bruna",
            "magic_link_url": "https://app.example.com/magic-link/verify?token=abc",
            "expires_minutes": 15,
        },
    ),
    SystemEmailTemplateKey.AUTH_PASSWORD_RESET: _template(
        SystemEmailTemplateKey.AUTH_PASSWORD_RESET,
        "Redefinicao de senha",
        "Enviado quando o usuario solicita reset de senha.",
        "auth",
        "Redefina sua senha no {{app_name}}",
        """
        <p>Ola, {{user_name}}.</p>
        <p>Recebemos uma solicitacao para redefinir sua senha.</p>
        <p><a href="{{reset_url}}">Criar nova senha</a></p>
        <p>Se voce nao solicitou isso, ignore este email.</p>
        """,
        ("app_name", "user_name", "reset_url"),
        {
            "app_name": "Acme Learning",
            "user_name": "Bruna",
            "reset_url": "https://app.example.com/reset-password?token=abc",
        },
    ),
    SystemEmailTemplateKey.AUTH_PASSWORD_CHANGED: _template(
        SystemEmailTemplateKey.AUTH_PASSWORD_CHANGED,
        "Senha alterada",
        "Confirma que a senha foi alterada.",
        "auth",
        "Sua senha foi alterada",
        "<p>Ola, {{user_name}}. Sua senha no {{app_name}} foi alterada com sucesso.</p>",
        ("app_name", "user_name"),
        {"app_name": "Acme Learning", "user_name": "Bruna"},
    ),
    SystemEmailTemplateKey.USER_WELCOME: _template(
        SystemEmailTemplateKey.USER_WELCOME,
        "Boas-vindas",
        "Enviado quando uma conta e criada pelo sistema.",
        "user",
        "Boas-vindas ao {{app_name}}",
        """
        <p>Ola, {{user_name}}.</p>
        <p>Sua conta no {{app_name}} foi criada.</p>
        <p><a href="{{login_url}}">Acessar plataforma</a></p>
        """,
        ("app_name", "user_name", "login_url"),
        {
            "app_name": "Acme Learning",
            "user_name": "Bruna",
            "login_url": "https://app.example.com/login",
        },
    ),
    SystemEmailTemplateKey.COMPANY_INVITE_MEMBER: _template(
        SystemEmailTemplateKey.COMPANY_INVITE_MEMBER,
        "Convite de membro B2B",
        "Enviado quando um admin convida alguem para uma empresa.",
        "company",
        "Voce foi convidado para {{company_name}} no {{app_name}}",
        """
        <p>Ola, {{user_name}}.</p>
        <p>Voce foi convidado para acessar os treinamentos da {{company_name}}.</p>
        <p><a href="{{invite_url}}">Aceitar convite</a></p>
        """,
        ("app_name", "company_name", "user_name", "invite_url"),
        {
            "app_name": "Acme Learning",
            "company_name": "Acme Comercial",
            "user_name": "Diego",
            "invite_url": "https://app.example.com/invites/token/accept",
        },
    ),
    SystemEmailTemplateKey.COMPANY_MEMBER_WELCOME: _template(
        SystemEmailTemplateKey.COMPANY_MEMBER_WELCOME,
        "Membro adicionado",
        "Enviado quando um usuario existente entra em uma empresa.",
        "company",
        "Voce entrou em {{company_name}}",
        "<p>Ola, {{user_name}}. Seu acesso a {{company_name}} no {{app_name}} esta ativo.</p>",
        ("app_name", "company_name", "user_name"),
        {"app_name": "Acme Learning", "company_name": "Acme Comercial", "user_name": "Bruna"},
    ),
    SystemEmailTemplateKey.COMPANY_BULK_IMPORT_MEMBER_WELCOME: _template(
        SystemEmailTemplateKey.COMPANY_BULK_IMPORT_MEMBER_WELCOME,
        "Boas-vindas por importacao",
        "Enviado para contas criadas por importacao CSV.",
        "company",
        "Seu acesso a {{app_name}} foi criado",
        """
        <p>Ola, {{user_name}}.</p>
        <p>Voce foi adicionado a {{company_name}}.</p>
        <p>Senha temporaria: <strong>{{temporary_password}}</strong></p>
        <p><a href="{{login_url}}">Entrar na plataforma</a></p>
        """,
        ("app_name", "company_name", "user_name", "temporary_password", "login_url"),
        {
            "app_name": "Acme Learning",
            "company_name": "Acme Comercial",
            "user_name": "Diego",
            "temporary_password": "TempPass123!",
            "login_url": "https://app.example.com/login",
        },
    ),
    SystemEmailTemplateKey.ENROLLMENT_ACCESS_GRANTED: _template(
        SystemEmailTemplateKey.ENROLLMENT_ACCESS_GRANTED,
        "Acesso liberado",
        "Enviado quando uma matricula ativa e criada.",
        "enrollment",
        "Seu acesso a {{product_title}} foi liberado",
        """
        <p>Ola, {{user_name}}.</p>
        <p>Seu acesso a <strong>{{product_title}}</strong> esta ativo.</p>
        <p><a href="{{product_url}}">Comecar agora</a></p>
        """,
        ("user_name", "product_title", "product_url"),
        {
            "user_name": "Bruna",
            "product_title": "Onboarding Comercial B2B",
            "product_url": "https://app.example.com/courses",
        },
    ),
    SystemEmailTemplateKey.ENROLLMENT_ACCESS_REACTIVATED: _template(
        SystemEmailTemplateKey.ENROLLMENT_ACCESS_REACTIVATED,
        "Acesso reativado",
        "Enviado quando uma matricula volta para ativa.",
        "enrollment",
        "Seu acesso a {{product_title}} foi reativado",
        "<p>Ola, {{user_name}}. Seu acesso a {{product_title}} esta ativo novamente.</p>",
        ("user_name", "product_title"),
        {"user_name": "Bruna", "product_title": "Onboarding Comercial B2B"},
    ),
    SystemEmailTemplateKey.ENROLLMENT_ACCESS_SUSPENDED: _template(
        SystemEmailTemplateKey.ENROLLMENT_ACCESS_SUSPENDED,
        "Acesso suspenso",
        "Enviado quando uma matricula e suspensa.",
        "enrollment",
        "Seu acesso a {{product_title}} foi suspenso",
        "<p>Ola, {{user_name}}. Seu acesso a {{product_title}} foi suspenso.</p>",
        ("user_name", "product_title"),
        {"user_name": "Bruna", "product_title": "Onboarding Comercial B2B"},
    ),
    SystemEmailTemplateKey.ENROLLMENT_ACCESS_CANCELLED: _template(
        SystemEmailTemplateKey.ENROLLMENT_ACCESS_CANCELLED,
        "Acesso cancelado",
        "Enviado quando uma matricula e cancelada.",
        "enrollment",
        "Seu acesso a {{product_title}} foi cancelado",
        "<p>Ola, {{user_name}}. Seu acesso a {{product_title}} foi cancelado.</p>",
        ("user_name", "product_title"),
        {"user_name": "Bruna", "product_title": "Onboarding Comercial B2B"},
    ),
    SystemEmailTemplateKey.ENROLLMENT_ACCESS_REFUNDED: _template(
        SystemEmailTemplateKey.ENROLLMENT_ACCESS_REFUNDED,
        "Acesso removido por reembolso",
        "Enviado quando uma compra e reembolsada.",
        "enrollment",
        "Reembolso confirmado para {{product_title}}",
        "<p>Ola, {{user_name}}. O reembolso de {{product_title}} foi processado.</p>",
        ("user_name", "product_title"),
        {"user_name": "Bruna", "product_title": "Onboarding Comercial B2B"},
    ),
    SystemEmailTemplateKey.ENROLLMENT_ACCESS_EXPIRING: _template(
        SystemEmailTemplateKey.ENROLLMENT_ACCESS_EXPIRING,
        "Acesso perto de expirar",
        "Enviado antes da expiracao de uma matricula.",
        "enrollment",
        "Seu acesso a {{product_title}} expira em {{days_left}} dias",
        "<p>Ola, {{user_name}}. Seu acesso a {{product_title}} expira em {{days_left}} dias.</p>",
        ("user_name", "product_title", "days_left"),
        {"user_name": "Bruna", "product_title": "Onboarding Comercial B2B", "days_left": 7},
    ),
    SystemEmailTemplateKey.COURSE_DRIP_LESSON_RELEASED: _template(
        SystemEmailTemplateKey.COURSE_DRIP_LESSON_RELEASED,
        "Aula liberada por drip",
        "Enviado quando uma aula programada fica disponivel.",
        "course",
        "Nova aula disponivel: {{lesson_title}}",
        "<p>A aula {{lesson_title}} do curso {{course_title}} ja esta liberada.</p>",
        ("lesson_title", "course_title"),
        {"lesson_title": "Proposta de valor", "course_title": "Onboarding Comercial B2B"},
    ),
    SystemEmailTemplateKey.COURSE_COMPLETED: _template(
        SystemEmailTemplateKey.COURSE_COMPLETED,
        "Curso concluido",
        "Enviado quando o aluno conclui um curso.",
        "course",
        "Parabens por concluir {{course_title}}",
        "<p>Ola, {{user_name}}. Voce concluiu {{course_title}}.</p>",
        ("user_name", "course_title"),
        {"user_name": "Bruna", "course_title": "Onboarding Comercial B2B"},
    ),
    SystemEmailTemplateKey.COURSE_CERTIFICATE_ISSUED: _template(
        SystemEmailTemplateKey.COURSE_CERTIFICATE_ISSUED,
        "Certificado emitido",
        "Enviado quando um certificado fica disponivel.",
        "course",
        "Seu certificado de {{course_title}} esta pronto",
        "<p>Ola, {{user_name}}. Baixe seu certificado: <a href=\"{{certificate_url}}\">abrir certificado</a>.</p>",
        ("user_name", "course_title", "certificate_url"),
        {
            "user_name": "Bruna",
            "course_title": "Onboarding Comercial B2B",
            "certificate_url": "https://app.example.com/certificates/abc",
        },
    ),
    SystemEmailTemplateKey.COMMUNITY_COMMENT_REPLY: _template(
        SystemEmailTemplateKey.COMMUNITY_COMMENT_REPLY,
        "Resposta em comentario",
        "Enviado quando alguem responde uma publicacao do usuario.",
        "community",
        "{{actor_name}} respondeu sua publicacao",
        "<p>{{actor_name}} respondeu em {{post_title}}.</p><p><a href=\"{{post_url}}\">Ver conversa</a></p>",
        ("actor_name", "post_title", "post_url"),
        {
            "actor_name": "Marcos",
            "post_title": "Como usar o playbook?",
            "post_url": "https://app.example.com/community/posts/abc",
        },
    ),
    SystemEmailTemplateKey.COMMUNITY_MENTION: _template(
        SystemEmailTemplateKey.COMMUNITY_MENTION,
        "Mencao na comunidade",
        "Enviado quando um usuario e mencionado.",
        "community",
        "{{actor_name}} mencionou voce",
        "<p>{{actor_name}} mencionou voce na comunidade.</p><p><a href=\"{{target_url}}\">Abrir</a></p>",
        ("actor_name", "target_url"),
        {"actor_name": "Marcos", "target_url": "https://app.example.com/community/posts/abc"},
    ),
    SystemEmailTemplateKey.COMMUNITY_POST_REPORTED: _template(
        SystemEmailTemplateKey.COMMUNITY_POST_REPORTED,
        "Publicacao denunciada",
        "Alerta administrativo para moderacao.",
        "community",
        "Nova denuncia na comunidade",
        "<p>A publicacao {{post_title}} foi denunciada por {{report_reason}}.</p>",
        ("post_title", "report_reason"),
        {"post_title": "Post de exemplo", "report_reason": "conteudo inadequado"},
    ),
    SystemEmailTemplateKey.GAMIFICATION_BADGE_EARNED: _template(
        SystemEmailTemplateKey.GAMIFICATION_BADGE_EARNED,
        "Badge conquistado",
        "Enviado quando um usuario ganha um badge.",
        "gamification",
        "Voce conquistou o badge {{badge_name}}",
        "<p>Ola, {{user_name}}. Voce conquistou {{badge_name}} e ganhou {{xp_reward}} XP.</p>",
        ("user_name", "badge_name", "xp_reward"),
        {"user_name": "Bruna", "badge_name": "Primeira Semana", "xp_reward": 100},
    ),
    SystemEmailTemplateKey.GAMIFICATION_LEVEL_UP: _template(
        SystemEmailTemplateKey.GAMIFICATION_LEVEL_UP,
        "Subiu de nivel",
        "Enviado quando o usuario sobe de nivel.",
        "gamification",
        "Voce chegou ao nivel {{level}}",
        "<p>Ola, {{user_name}}. Seu novo nivel e {{level}}.</p>",
        ("user_name", "level"),
        {"user_name": "Bruna", "level": 4},
    ),
    SystemEmailTemplateKey.GAMIFICATION_STREAK_AT_RISK: _template(
        SystemEmailTemplateKey.GAMIFICATION_STREAK_AT_RISK,
        "Sequencia em risco",
        "Enviado quando uma streak pode ser perdida.",
        "gamification",
        "Sua sequencia de {{current_streak}} dias esta em risco",
        "<p>Volte hoje para manter sua sequencia de {{current_streak}} dias.</p>",
        ("current_streak",),
        {"current_streak": 6},
    ),
    SystemEmailTemplateKey.GAMIFICATION_GOAL_ACHIEVED: _template(
        SystemEmailTemplateKey.GAMIFICATION_GOAL_ACHIEVED,
        "Meta alcancada",
        "Enviado quando uma empresa ou usuario alcanca uma meta.",
        "gamification",
        "Meta alcancada: {{goal_title}}",
        "<p>A meta {{goal_title}} foi alcancada por {{company_name}}.</p>",
        ("goal_title", "company_name"),
        {"goal_title": "Concluir onboarding", "company_name": "Acme Comercial"},
    ),
    SystemEmailTemplateKey.QUIZ_BATTLE_INVITE: _template(
        SystemEmailTemplateKey.QUIZ_BATTLE_INVITE,
        "Convite para quiz battle",
        "Enviado quando um usuario e desafiado.",
        "quiz_battle",
        "{{challenger_name}} desafiou voce",
        "<p>{{challenger_name}} iniciou um quiz battle. <a href=\"{{battle_url}}\">Responder</a></p>",
        ("challenger_name", "battle_url"),
        {"challenger_name": "Diego", "battle_url": "https://app.example.com/quiz/battles/abc"},
    ),
    SystemEmailTemplateKey.QUIZ_BATTLE_RESULT: _template(
        SystemEmailTemplateKey.QUIZ_BATTLE_RESULT,
        "Resultado do quiz battle",
        "Enviado quando um quiz battle termina.",
        "quiz_battle",
        "Resultado do desafio: {{result_label}}",
        "<p>Resultado: {{result_label}}. Sua pontuacao: {{score}}.</p>",
        ("result_label", "score"),
        {"result_label": "vitoria", "score": 8},
    ),
    SystemEmailTemplateKey.MESSAGE_NEW_DIRECT: _template(
        SystemEmailTemplateKey.MESSAGE_NEW_DIRECT,
        "Nova mensagem direta",
        "Enviado quando chega uma mensagem privada.",
        "messages",
        "Nova mensagem de {{sender_name}}",
        "<p>{{sender_name}} enviou uma mensagem. <a href=\"{{conversation_url}}\">Abrir conversa</a></p>",
        ("sender_name", "conversation_url"),
        {"sender_name": "Marcos", "conversation_url": "https://app.example.com/messages/abc"},
    ),
    SystemEmailTemplateKey.NOTIFICATION_BROADCAST: _template(
        SystemEmailTemplateKey.NOTIFICATION_BROADCAST,
        "Comunicado geral",
        "Espelho por email de uma notificacao broadcast.",
        "notification",
        "{{notification_title}}",
        "<p>{{notification_body}}</p>",
        ("notification_title", "notification_body"),
        {"notification_title": "Manutencao", "notification_body": "A plataforma ficara indisponivel as 22h."},
    ),
    SystemEmailTemplateKey.TRANSCRIPTION_READY: _template(
        SystemEmailTemplateKey.TRANSCRIPTION_READY,
        "Transcricao pronta",
        "Enviado a admins quando a transcricao de uma aula termina.",
        "transcription",
        "Transcricao pronta: {{lesson_title}}",
        "<p>A transcricao da aula {{lesson_title}} foi concluida.</p>",
        ("lesson_title",),
        {"lesson_title": "Diagnostico consultivo"},
    ),
    SystemEmailTemplateKey.TRANSCRIPTION_FAILED: _template(
        SystemEmailTemplateKey.TRANSCRIPTION_FAILED,
        "Falha na transcricao",
        "Enviado a admins quando uma transcricao falha.",
        "transcription",
        "Falha ao transcrever {{lesson_title}}",
        "<p>A transcricao da aula {{lesson_title}} falhou: {{error_message}}.</p>",
        ("lesson_title", "error_message"),
        {"lesson_title": "Diagnostico consultivo", "error_message": "arquivo indisponivel"},
    ),
    SystemEmailTemplateKey.WEBHOOK_PROCESSING_FAILED: _template(
        SystemEmailTemplateKey.WEBHOOK_PROCESSING_FAILED,
        "Falha no processamento de webhook",
        "Alerta administrativo quando um webhook falha apos retries.",
        "webhook",
        "Falha no webhook {{provider}}",
        "<p>O webhook {{provider}} falhou para o evento {{event_type}}: {{error_message}}.</p>",
        ("provider", "event_type", "error_message"),
        {"provider": "hotmart", "event_type": "purchase.approved", "error_message": "produto nao encontrado"},
    ),
}


def list_system_email_templates() -> list[SystemEmailTemplate]:
    return sorted(SYSTEM_EMAIL_TEMPLATES.values(), key=lambda template: template.key.value)


def get_system_email_template(key: str | SystemEmailTemplateKey) -> SystemEmailTemplate:
    template_key = SystemEmailTemplateKey(str(key))
    return SYSTEM_EMAIL_TEMPLATES[template_key]


def render_system_email_template(
    key: str | SystemEmailTemplateKey,
    context: dict[str, Any],
) -> RenderedSystemEmail:
    template = get_system_email_template(key)
    missing = [name for name in template.required_variables if context.get(name) is None]
    if missing:
        raise ValueError(f"Missing system email variables: {', '.join(missing)}")

    return RenderedSystemEmail(
        key=template.key.value,
        subject=_render(template.subject, context, escape_html=False),
        html_body=_render(template.html_body, context, escape_html=True),
    )


def _render(template: str, context: dict[str, Any], *, escape_html: bool) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        value = "" if context.get(key) is None else str(context[key])
        return escape(value, quote=True) if escape_html else value

    return _TOKEN_RE.sub(replace, template).strip()
