from pydantic_settings import BaseSettings, SettingsConfigDict
from decimal import Decimal

class Settings(BaseSettings):
    app_name: str = "Trend Earning Mini App"
    app_secret: str = "CHANGE_ME_NOW"
    database_url: str = "postgresql+asyncpg://earning:change_me@localhost:5432/earning"
    bot_token: str = ""
    min_withdraw_usd: Decimal = Decimal("10.00")
    referral_bonus_usd: Decimal = Decimal("1.00")
    admin_telegram_ids: str = ""
    webapp_url: str = "https://your-domain.example"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def admin_ids(self) -> set[int]:
        ids = set()
        for part in self.admin_telegram_ids.split(","):
            part = part.strip()
            if part.isdigit():
                ids.add(int(part))
        return ids

settings = Settings()
