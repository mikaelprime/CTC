from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ruta a la raíz del proyecto (CTC)
BASE_DIR = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Envío de correo vía la API HTTP de Brevo (no SMTP): Render bloquea las
    # conexiones SMTP salientes en su plan gratuito, así que un socket a
    # smtp.gmail.com falla con "Network is unreachable" sin importar las
    # credenciales. La API HTTP de Brevo corre sobre HTTPS/443, que ningún
    # host bloquea. Ver https://app.brevo.com/settings/keys/api.
    BREVO_API_KEY: str = ""
    EMAIL_FROM_ADDRESS: str = ""
    EMAIL_FROM_NAME: str = "CTC El Salvador"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()