from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str
    admin_ids: str = ""
    channel_id: str = "@palestinasosetxyi"
    channel_url: str = "https://t.me/palestinasosetxyi"
    database_url: str = "sqlite+aiosqlite:///./data/bot.db"

    master_phone: str = "+79859547909"
    master_telegram: str = "@exxtasyyy"

    webhook_host: str = ""
    webhook_path: str = "/webhook"
    webhook_secret: str = ""

    @property
    def admin_id_list(self) -> list[int]:
        if not self.admin_ids.strip():
            return []
        return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip()]

    @property
    def use_webhook(self) -> bool:
        return bool(self.webhook_host.strip())


settings = Settings()
