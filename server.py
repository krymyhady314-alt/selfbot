import asyncio
import math
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import httpx
import psycopg2
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

DATABASE_URL = os.getenv("DATABASE_URL", "")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "123456")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = os.getenv("ADMIN_ID", "")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    if not DATABASE_URL:
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS licenses (
                    license_key TEXT PRIMARY KEY,
                    days INTEGER NOT NULL,
                    device_id TEXT,
                    expires_at TIMESTAMPTZ,
                    banned BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )
        conn.commit()


def create_license_key(days: int) -> str:
    part1 = secrets.token_hex(2).upper()
    part2 = secrets.token_hex(2).upper()
    key = f"V3X-{part1}-{part2}"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO licenses (license_key, days) VALUES (%s, %s)",
                (key, days),
            )
        conn.commit()
    return key


def add_days_to_key(key: str, extra_days: int) -> str:
    key = key.strip().upper()
    now = datetime.now(timezone.utc)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT days, expires_at FROM licenses WHERE license_key = %s", (key,))
            row = cur.fetchone()
            if not row:
                return "❌ لایسنس پیدا نشد."
            days, expires_at = row
            if expires_at is None:
                new_days = days + extra_days
                cur.execute("UPDATE licenses SET days = %s WHERE license_key = %s", (new_days, key))
                conn.commit()
                return f"✅ {extra_days} روز اضافه شد (مجموع اعتبار قبل از فعال‌سازی: {new_days} روز)."
            else:
                base = expires_at if expires_at > now else now
                new_exp = base + timedelta(days=extra_days)
                cur.execute("UPDATE licenses SET expires_at = %s WHERE license_key = %s", (new_exp, key))
                conn.commit()
                left = math.ceil((new_exp - now).total_seconds() / 86400)
                return f"✅ {extra_days} روز به لایسنس اضافه شد. اعتبار باقی‌مانده: {left} روز."


def set_ban_status(key: str, banned: bool) -> str:
    key = key.strip().upper()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE licenses SET banned = %s WHERE license_key = %s", (banned, key))
            if cur.rowcount == 0:
                return "❌ لایسنس پیدا نشد."
        conn.commit()
    return "🚫 لایسنس مسدود شد." if banned else "✅ مسدودیت لایسنس برداشته شد."


def reset_device_binding(key: str) -> str:
    key = key.strip().upper()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE licenses SET device_id = NULL WHERE license_key = %s", (key,))
            if cur.rowcount == 0:
                return "❌ لایسنس پیدا نشد."
        conn.commit()
    return "🔓 قفل دستگاه باز شد؛ کاربر می‌تواند روی گوشی جدید وارد شود."


async def telegram_bot_worker():
    if not BOT_TOKEN or not ADMIN_ID:
        return
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}"
    offset = 0
    async with httpx.AsyncClient(timeout=35) as client:
        while True:
            try:
                resp = await client.get(f"{api_url}/getUpdates", params={"offset": offset, "timeout": 25})
                data = resp.json()
                for item in data.get("result", []):
                    offset = item["update_id"] + 1
                    msg = item.get("message") or {}
                    chat_id = str(msg.get("chat", {}).get("id", ""))
                    text = (msg.get("text") or "").strip()

                    if chat_id != str(ADMIN_ID).strip() or not text:
                        continue

                    reply = ""
                    parts = text.split()
                    cmd = parts[0].lower()

                    if cmd == "/start":
                        reply = (
                            "پنل مدیریت لایسنس آماده است:\n"
                            "/gen 30 — ساخت لایسنس ۳۰ روزه\n"
                            "/addtime KEY 7 — تمدید لایسنس\n"
                            "/ban KEY — مسدود کردن\n"
                            "/unban KEY — رفع مسدودی\n"
                            "/reset KEY — حذف قفل گوشی"
                        )
                    elif cmd == "/gen" and len(parts) >= 2 and parts[1].isdigit():
                        days = int(parts[1])
                        new_key = await asyncio.to_thread(create_license_key, days)
                        reply = f"✅ لایسنس {days} روزه ساخته شد:\n`{new_key}`"
                    elif cmd == "/addtime" and len(parts) >= 3 and parts[2].isdigit():
                        reply = await asyncio.to_thread(add_days_to_key, parts[1], int(parts[2]))
                    elif cmd == "/ban" and len(parts) >= 2:
                        reply = await asyncio.to_thread(set_ban_status, parts[1], True)
                    elif cmd == "/unban" and len(parts) >= 2:
                        reply = await asyncio.to_thread(set_ban_status, parts[1], False)
                    elif cmd == "/reset" and len(parts) >= 2:
                        reply = await asyncio.to_thread(reset_device_binding, parts[1])

                    if reply:
                        await client.post(
                            f"{api_url}/sendMessage",
                            json={"chat_id": chat_id, "text": reply, "parse_mode": "Markdown"},
                        )
            except Exception:
                await asyncio.sleep(3)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(telegram_bot_worker())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


class VerifyRequest(BaseModel):
    key: str
    device_id: str


@app.get("/")
def health():
    return {"status": "online"}


@app.post("/api/verify")
def verify_license(req: VerifyRequest):
    key = req.key.strip().upper()
    dev_id = req.device_id.strip()
    now = datetime.now(timezone.utc)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT days, device_id, expires_at, banned FROM licenses WHERE license_key = %s",
                (key,),
            )
            row = cur.fetchone()
            if not row:
                return {"valid": False, "days_left": 0, "msg": "کد لایسنس اشتباه است."}

            days, saved_device, expires_at, banned = row
            if banned:
                return {"valid": False, "days_left": 0, "msg": "این لایسنس توسط مدیریت مسدود شده است."}

            if saved_device is None:
                expires_at = now + timedelta(days=days)
                cur.execute(
                    "UPDATE licenses SET device_id = %s, expires_at = %s WHERE license_key = %s",
                    (dev_id, expires_at, key),
                )
                conn.commit()
            elif saved_device != dev_id:
                return {"valid": False, "days_left": 0, "msg": "این کد قبلاً روی یک گوشی دیگر فعال شده است."}

            if now >= expires_at:
                return {"valid": False, "days_left": 0, "msg": "اعتبار زمانی لایسنس شما به پایان رسیده است."}

            days_left = max(1, math.ceil((expires_at - now).total_seconds() / 86400))
            return {"valid": True, "days_left": days_left, "msg": "لایسنس معتبر است."}


@app.get("/admin/gen")
def web_generate_key(secret: str = Query(...), days: int = Query(30)):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="رمز ادمین اشتباه است")
    new_key = create_license_key(days)
    return {"license_key": new_key, "days": days}
