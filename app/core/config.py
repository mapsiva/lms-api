from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    frontend_url: str = "http://localhost:3000"

    # Database & cache
    database_url: str = "postgresql+asyncpg://lms:lms@localhost:5432/lms"
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: SecretStr = SecretStr("change-me")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    magic_link_expire_minutes: int = 15

    # Bunny.net
    bunny_api_key: SecretStr = SecretStr("")
    bunny_storage_zone: str = ""
    bunny_cdn_hostname: str = ""
    bunny_stream_library_id: str = ""

    # AssemblyAI
    assemblyai_api_key: SecretStr = SecretStr("")

    # Resend (email)
    resend_api_key: SecretStr = SecretStr("")
    resend_from_email: str = "noreply@example.com"

    # Cloudflare R2
    r2_access_key_id: SecretStr = SecretStr("")
    r2_secret_access_key: SecretStr = SecretStr("")
    r2_bucket_name: str = ""
    r2_endpoint_url: str = ""
    r2_public_url: str = ""

    # Payment gateway HMAC secrets
    hotmart_webhook_secret: SecretStr = SecretStr("")
    kiwify_webhook_secret: SecretStr = SecretStr("")
    greenn_webhook_secret: SecretStr = SecretStr("")
    monetizze_webhook_secret: SecretStr = SecretStr("")
    stripe_webhook_secret: SecretStr = SecretStr("")

    # Mux
    mux_token_id: str = ""
    mux_token_secret: SecretStr = SecretStr("")
    mux_signing_key_id: str = ""
    mux_signing_key_secret: SecretStr = SecretStr("")  # base64-encoded RSA private key

    # Vimeo
    vimeo_access_token: SecretStr = SecretStr("")

    # Panda Video
    panda_api_key: SecretStr = SecretStr("")
    panda_cdn_hostname: str = ""

    # AI
    anthropic_api_key: SecretStr = SecretStr("")

    # Groq
    groq_api_key: SecretStr = SecretStr("")
    groq_model: str = "llama-3.3-70b-versatile"

    # OpenRouter
    openrouter_api_key: SecretStr = SecretStr("")
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct:free"
    openrouter_site_url: str = ""
    openrouter_app_name: str = "LMS"

    # Web Push (VAPID)
    vapid_private_key: str = ""
    vapid_public_key: str = ""
    vapid_claims_email: str = ""

    # Misc
    webhook_test_mode: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
