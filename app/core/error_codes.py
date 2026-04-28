"""
Error codes for the LMS API.

Each constant is a machine-readable identifier (for frontend logic and logging),
and maps to a human-readable Portuguese message shown to the end user.

Usage:
    from app.core.error_codes import ErrorCode
    raise AppError(ErrorCode.USER_NOT_FOUND)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorDefinition:
    """Defines an error with its machine-readable code and user-facing message."""
    code: str
    message: str
    http_status: int


class ErrorCode:
    """Centralized registry of all application error codes."""

    # ─── General / Validation ─────────────────────────────────────────────────
    VALIDATION_ERROR = ErrorDefinition(
        code="VALIDATION_ERROR",
        message="Dados inválidos.",
        http_status=400,
    )
    INVALID_REQUEST = ErrorDefinition(
        code="INVALID_REQUEST",
        message="Requisição inválida.",
        http_status=400,
    )
    NOT_FOUND = ErrorDefinition(
        code="NOT_FOUND",
        message="Recurso não encontrado.",
        http_status=404,
    )
    CONFLICT = ErrorDefinition(
        code="CONFLICT",
        message="Conflito detectado.",
        http_status=409,
    )

    # ─── Authentication ───────────────────────────────────────────────────────
    INVALID_CREDENTIALS = ErrorDefinition(
        code="INVALID_CREDENTIALS",
        message="E-mail ou senha incorretos.",
        http_status=401,
    )
    INVALID_TOKEN = ErrorDefinition(
        code="INVALID_TOKEN",
        message="Token de autenticação inválido.",
        http_status=401,
    )
    TOKEN_EXPIRED = ErrorDefinition(
        code="TOKEN_EXPIRED",
        message="Token de autenticação expirado.",
        http_status=401,
    )
    REFRESH_TOKEN_INVALID = ErrorDefinition(
        code="REFRESH_TOKEN_INVALID",
        message="Token de atualização inválido.",
        http_status=401,
    )
    REFRESH_TOKEN_REVOKED = ErrorDefinition(
        code="REFRESH_TOKEN_REVOKED",
        message="Token de atualização foi revogado.",
        http_status=401,
    )
    REFRESH_TOKEN_EXPIRED = ErrorDefinition(
        code="REFRESH_TOKEN_EXPIRED",
        message="Token de atualização expirado.",
        http_status=401,
    )
    INVALID_OTP = ErrorDefinition(
        code="INVALID_OTP",
        message="Código OTP inválido ou expirado.",
        http_status=401,
    )
    NOT_AUTHENTICATED = ErrorDefinition(
        code="NOT_AUTHENTICATED",
        message="Não autenticado.",
        http_status=401,
    )
    ACCOUNT_SUSPENDED = ErrorDefinition(
        code="ACCOUNT_SUSPENDED",
        message="Conta suspensa.",
        http_status=403,
    )
    INVALID_MAGIC_LINK = ErrorDefinition(
        code="INVALID_MAGIC_LINK",
        message="Link mágico inválido ou expirado.",
        http_status=401,
    )
    INVALID_PASSWORD_RESET_TOKEN = ErrorDefinition(
        code="INVALID_PASSWORD_RESET_TOKEN",
        message="Token de redefinição de senha inválido ou expirado.",
        http_status=401,
    )
    PASSWORD_RESET_TOKEN_USED = ErrorDefinition(
        code="PASSWORD_RESET_TOKEN_USED",
        message="Token de redefinição de senha já foi utilizado.",
        http_status=400,
    )

    # ─── Authorization ────────────────────────────────────────────────────────
    PERMISSION_DENIED = ErrorDefinition(
        code="PERMISSION_DENIED",
        message="Você não tem permissão para realizar esta ação.",
        http_status=403,
    )
    ADMIN_REQUIRED = ErrorDefinition(
        code="ADMIN_REQUIRED",
        message="Acesso exclusivo para administradores.",
        http_status=403,
    )
    MANAGER_REQUIRED = ErrorDefinition(
        code="MANAGER_REQUIRED",
        message="Acesso exclusivo para gestores.",
        http_status=403,
    )
    SUPERADMIN_REQUIRED = ErrorDefinition(
        code="SUPERADMIN_REQUIRED",
        message="Acesso exclusivo para super administradores.",
        http_status=403,
    )
    ACCOUNT_INACTIVE = ErrorDefinition(
        code="ACCOUNT_INACTIVE",
        message="Esta conta está inativa.",
        http_status=403,
    )
    EMAIL_NOT_VERIFIED = ErrorDefinition(
        code="EMAIL_NOT_VERIFIED",
        message="É necessário verificar seu e-mail antes de continuar.",
        http_status=403,
    )
    NO_COMPANY_CONTEXT = ErrorDefinition(
        code="NO_COMPANY_CONTEXT",
        message="Nenhuma empresa selecionada. Selecione uma empresa para continuar.",
        http_status=403,
    )
    COMPANY_ACCESS_DENIED = ErrorDefinition(
        code="COMPANY_ACCESS_DENIED",
        message="Você não tem acesso a esta empresa.",
        http_status=403,
    )

    # ─── Tenant ───────────────────────────────────────────────────────────────
    TENANT_NOT_FOUND = ErrorDefinition(
        code="TENANT_NOT_FOUND",
        message="Tenant não encontrado.",
        http_status=404,
    )

    # ─── Company ──────────────────────────────────────────────────────────────
    COMPANY_NOT_FOUND = ErrorDefinition(
        code="COMPANY_NOT_FOUND",
        message="Empresa não encontrada.",
        http_status=404,
    )
    MEMBER_NOT_FOUND = ErrorDefinition(
        code="MEMBER_NOT_FOUND",
        message="Membro não encontrado.",
        http_status=404,
    )

    # ─── User ─────────────────────────────────────────────────────────────────
    USER_NOT_FOUND = ErrorDefinition(
        code="USER_NOT_FOUND",
        message="Usuário não encontrado.",
        http_status=404,
    )
    AUTH_USER_NOT_FOUND = ErrorDefinition(
        code="AUTH_USER_NOT_FOUND",
        message="Usuário não encontrado.",
        http_status=401,
    )
    USER_ALREADY_EXISTS = ErrorDefinition(
        code="USER_ALREADY_EXISTS",
        message="Este e-mail já está cadastrado.",
        http_status=409,
    )
    USER_NOT_IN_COMPANY = ErrorDefinition(
        code="USER_NOT_IN_COMPANY",
        message="Usuário não pertence a esta empresa.",
        http_status=404,
    )

    # ─── Course / Module / Lesson ─────────────────────────────────────────────
    COURSE_NOT_FOUND = ErrorDefinition(
        code="COURSE_NOT_FOUND",
        message="Curso não encontrado.",
        http_status=404,
    )
    MODULE_NOT_FOUND = ErrorDefinition(
        code="MODULE_NOT_FOUND",
        message="Módulo não encontrado.",
        http_status=404,
    )
    LESSON_NOT_FOUND = ErrorDefinition(
        code="LESSON_NOT_FOUND",
        message="Aula não encontrada.",
        http_status=404,
    )
    NOT_ENROLLED = ErrorDefinition(
        code="NOT_ENROLLED",
        message="Você não está matriculado neste curso.",
        http_status=403,
    )
    LESSON_NO_VIDEO = ErrorDefinition(
        code="LESSON_NO_VIDEO",
        message="Aula não possui vídeo Bunny configurado.",
        http_status=400,
    )
    TRANSCRIPT_NOT_AVAILABLE = ErrorDefinition(
        code="TRANSCRIPT_NOT_AVAILABLE",
        message="Transcrição não disponível.",
        http_status=400,
    )
    NO_PENDING_LESSON = ErrorDefinition(
        code="NO_PENDING_LESSON",
        message="Nenhuma aula pendente.",
        http_status=404,
    )

    # ─── Enrollment ───────────────────────────────────────────────────────────
    ENROLLMENT_NOT_FOUND = ErrorDefinition(
        code="ENROLLMENT_NOT_FOUND",
        message="Matrícula não encontrada.",
        http_status=404,
    )
    MISSING_REQUIRED_FIELDS = ErrorDefinition(
        code="MISSING_REQUIRED_FIELDS",
        message="Campos obrigatórios ausentes.",
        http_status=400,
    )
    BULK_LIMIT_EXCEEDED = ErrorDefinition(
        code="BULK_LIMIT_EXCEEDED",
        message="Limite de 50 usuários por requisição em lote excedido.",
        http_status=400,
    )
    UNKNOWN_ACTION = ErrorDefinition(
        code="UNKNOWN_ACTION",
        message="Ação desconhecida.",
        http_status=400,
    )

    # ─── Product ──────────────────────────────────────────────────────────────
    PRODUCT_NOT_FOUND = ErrorDefinition(
        code="PRODUCT_NOT_FOUND",
        message="Produto não encontrado.",
        http_status=404,
    )

    # ─── Community ────────────────────────────────────────────────────────────
    SPACE_NOT_FOUND = ErrorDefinition(
        code="SPACE_NOT_FOUND",
        message="Espaço não encontrado.",
        http_status=404,
    )
    CHANNEL_NOT_FOUND = ErrorDefinition(
        code="CHANNEL_NOT_FOUND",
        message="Canal não encontrado.",
        http_status=404,
    )
    POST_NOT_FOUND = ErrorDefinition(
        code="POST_NOT_FOUND",
        message="Post não encontrado.",
        http_status=404,
    )
    COMMENT_NOT_FOUND = ErrorDefinition(
        code="COMMENT_NOT_FOUND",
        message="Comentário não encontrado.",
        http_status=404,
    )
    REPORT_NOT_FOUND = ErrorDefinition(
        code="REPORT_NOT_FOUND",
        message="Denúncia não encontrada.",
        http_status=404,
    )
    POSTING_RESTRICTED = ErrorDefinition(
        code="POSTING_RESTRICTED",
        message="Publicação restrita.",
        http_status=403,
    )
    POSTING_RESTRICTED_ADMINS = ErrorDefinition(
        code="POSTING_RESTRICTED_ADMINS",
        message="Publicação restrita a administradores.",
        http_status=403,
    )
    CANNOT_EDIT_OTHERS_POST = ErrorDefinition(
        code="CANNOT_EDIT_OTHERS_POST",
        message="Não é possível editar posts de outros usuários.",
        http_status=403,
    )
    CANNOT_DELETE_OTHERS_POST = ErrorDefinition(
        code="CANNOT_DELETE_OTHERS_POST",
        message="Não é possível excluir posts de outros usuários.",
        http_status=403,
    )
    ALREADY_LIKED = ErrorDefinition(
        code="ALREADY_LIKED",
        message="Você já curtiu este post.",
        http_status=409,
    )
    LIKE_NOT_FOUND = ErrorDefinition(
        code="LIKE_NOT_FOUND",
        message="Curtida não encontrada.",
        http_status=404,
    )

    # ─── Quiz ─────────────────────────────────────────────────────────────────
    OPPONENT_NOT_FOUND = ErrorDefinition(
        code="OPPONENT_NOT_FOUND",
        message="Oponente não encontrado.",
        http_status=404,
    )
    CANNOT_CHALLENGE_SELF = ErrorDefinition(
        code="CANNOT_CHALLENGE_SELF",
        message="Não é possível desafiar a si mesmo.",
        http_status=400,
    )
    BATTLE_NOT_FOUND = ErrorDefinition(
        code="BATTLE_NOT_FOUND",
        message="Batalha não encontrada.",
        http_status=404,
    )
    BATTLE_EXPIRED = ErrorDefinition(
        code="BATTLE_EXPIRED",
        message="Batalha expirada.",
        http_status=400,
    )
    BATTLE_COMPLETED = ErrorDefinition(
        code="BATTLE_COMPLETED",
        message="Batalha já foi concluída.",
        http_status=400,
    )
    ALREADY_ANSWERED = ErrorDefinition(
        code="ALREADY_ANSWERED",
        message="Resposta já enviada.",
        http_status=400,
    )

    # ─── Notification ─────────────────────────────────────────────────────────
    NOTIFICATION_NOT_FOUND = ErrorDefinition(
        code="NOTIFICATION_NOT_FOUND",
        message="Notificação não encontrada.",
        http_status=404,
    )

    # ─── Menu ─────────────────────────────────────────────────────────────────
    MENU_CONFIG_NOT_FOUND = ErrorDefinition(
        code="MENU_CONFIG_NOT_FOUND",
        message="Configuração de menu não encontrada.",
        http_status=404,
    )

    # ─── Landing Page / Public ────────────────────────────────────────────────
    LANDING_PAGE_NOT_FOUND = ErrorDefinition(
        code="LANDING_PAGE_NOT_FOUND",
        message="Landing page não encontrada.",
        http_status=404,
    )
    PAGE_NOT_FOUND = ErrorDefinition(
        code="PAGE_NOT_FOUND",
        message="Página não encontrada.",
        http_status=404,
    )

    # ─── Email ────────────────────────────────────────────────────────────────
    CAMPAIGN_NOT_FOUND = ErrorDefinition(
        code="CAMPAIGN_NOT_FOUND",
        message="Campanha não encontrada.",
        http_status=404,
    )
    TEMPLATE_NOT_FOUND = ErrorDefinition(
        code="TEMPLATE_NOT_FOUND",
        message="Template não encontrado.",
        http_status=404,
    )
    AUDIENCE_NOT_FOUND = ErrorDefinition(
        code="AUDIENCE_NOT_FOUND",
        message="Audiência não encontrada.",
        http_status=404,
    )
    EMAIL_REQUIRED = ErrorDefinition(
        code="EMAIL_REQUIRED",
        message="E-mail obrigatório.",
        http_status=400,
    )

    # ─── Webhook ──────────────────────────────────────────────────────────────
    WEBHOOK_LOG_NOT_FOUND = ErrorDefinition(
        code="WEBHOOK_LOG_NOT_FOUND",
        message="Log de webhook não encontrado.",
        http_status=404,
    )
    INVALID_CURSOR = ErrorDefinition(
        code="INVALID_CURSOR",
        message="Cursor inválido.",
        http_status=400,
    )

    # ─── Internal / Transcription ─────────────────────────────────────────────
    INTERNAL_AUTH_INVALID = ErrorDefinition(
        code="INTERNAL_AUTH_INVALID",
        message="Autenticação interna inválida.",
        http_status=401,
    )
    MISSING_TRANSCRIPT_ID = ErrorDefinition(
        code="MISSING_TRANSCRIPT_ID",
        message="ID da transcrição obrigatório.",
        http_status=400,
    )
    TRANSCRIPT_NOT_READY = ErrorDefinition(
        code="TRANSCRIPT_NOT_READY",
        message="Transcrição ainda não está pronta.",
        http_status=202,
    )

    # ─── Notes ────────────────────────────────────────────────────────────────
    NOTE_NOT_FOUND = ErrorDefinition(
        code="NOTE_NOT_FOUND",
        message="Nota não encontrada.",
        http_status=404,
    )

    # ─── Messages ─────────────────────────────────────────────────────────────
    CONVERSATION_NOT_FOUND = ErrorDefinition(
        code="CONVERSATION_NOT_FOUND",
        message="Conversa não encontrada.",
        http_status=404,
    )
    CONTENT_REQUIRED = ErrorDefinition(
        code="CONTENT_REQUIRED",
        message="Conteúdo obrigatório.",
        http_status=400,
    )

    # ─── Gamification / Manager ───────────────────────────────────────────────
    GOAL_NOT_FOUND = ErrorDefinition(
        code="GOAL_NOT_FOUND",
        message="Meta não encontrada.",
        http_status=404,
    )
    BADGE_NOT_FOUND = ErrorDefinition(
        code="BADGE_NOT_FOUND",
        message="Badge não encontrado.",
        http_status=404,
    )
    SPECIAL_EVENT_NOT_FOUND = ErrorDefinition(
        code="SPECIAL_EVENT_NOT_FOUND",
        message="Evento especial não encontrado.",
        http_status=404,
    )

    # ─── Uploads ──────────────────────────────────────────────────────────────
    FILE_TOO_LARGE = ErrorDefinition(
        code="FILE_TOO_LARGE",
        message="Arquivo muito grande (máx. 10MB).",
        http_status=413,
    )
    UNSUPPORTED_FILE_TYPE = ErrorDefinition(
        code="UNSUPPORTED_FILE_TYPE",
        message="Tipo de arquivo não suportado.",
        http_status=400,
    )
