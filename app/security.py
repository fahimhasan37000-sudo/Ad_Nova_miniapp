import hashlib, hmac, json, time
from urllib.parse import parse_qsl
from fastapi import HTTPException, Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .config import settings
from .db import get_db
from .models import User

def verify_telegram_init_data(init_data: str, max_age_seconds: int = 86400) -> dict:
    if not settings.bot_token:
        raise HTTPException(503, "Bot is not configured")
    values = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = values.pop("hash", None)
    if not received_hash:
        raise HTTPException(401, "Missing Telegram signature")
    auth_date = values.get("auth_date")
    if not auth_date or not auth_date.isdigit() or abs(int(time.time()) - int(auth_date)) > max_age_seconds:
        raise HTTPException(401, "Telegram login data expired")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(values.items()))
    secret_key = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        raise HTTPException(401, "Invalid Telegram signature")
    try:
        user_data = json.loads(values["user"])
    except (KeyError, json.JSONDecodeError):
        raise HTTPException(401, "Invalid Telegram user data")
    if not user_data.get("id"):
        raise HTTPException(401, "Missing Telegram user ID")
    return user_data

async def current_user(x_telegram_init_data: str = Header(default="", alias="X-Telegram-Init-Data"),
                       db: AsyncSession = Depends(get_db)) -> User:
    info = verify_telegram_init_data(x_telegram_init_data)
    result = await db.execute(select(User).where(User.telegram_id == int(info["id"])))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(telegram_id=int(info["id"]), username=info.get("username"),
                    first_name=info.get("first_name"))
        db.add(user)
        await db.commit()
        await db.refresh(user)
    if user.is_blocked:
        raise HTTPException(403, "Account is blocked")
    return user

async def admin_user(user: User = Depends(current_user)) -> User:
    if user.telegram_id not in settings.admin_ids:
        raise HTTPException(403, "Admin access required")
    return user
