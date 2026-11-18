import asyncio
import inspect
import json
import os
import platform
import tempfile
import time
import uuid

import flet as ft
import httpx

try:
    from splusthon import Client, events
except ImportError:
    from splusthon.client import Client
    events = None

LICENSE_SERVER_URL = "https://selfbot-license.krymyhady314.workers.dev"

# مسیر مجاز و قابل نوشتن در حافظه داخلی اندروید
STORAGE_DIR = os.getenv("FLET_APP_STORAGE_DATA") or tempfile.gettempdir()
os.makedirs(STORAGE_DIR, exist_ok=True)

DEVICE_ID_FILE = os.path.join(STORAGE_DIR, "v3x_device_id.txt")
LICENSE_FILE = os.path.join(STORAGE_DIR, "v3x_license.json")
SESSION_PATH = os.path.join(STORAGE_DIR, "v3x_soroush_session")


def get_device_id() -> str:
    if os.path.exists(DEVICE_ID_FILE):
        try:
            saved = open(DEVICE_ID_FILE, "r", encoding="utf-8").read().strip()
            if saved:
                return saved
        except Exception:
            pass

    raw = f"{uuid.getnode()}-{platform.machine()}-{uuid.uuid4().hex[:12]}"
    device_id = "V3X-" + uuid.uuid5(uuid.NAMESPACE_DNS, raw).hex[:16].upper()
    try:
        with open(DEVICE_ID_FILE, "w", encoding="utf-8") as f:
            f.write(device_id)
    except Exception:
        pass
    return device_id


def save_license_local(key: str, info: dict):
    try:
        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            json.dump({"key": key, "info": info}, f, ensure_ascii=False)
    except Exception:
        pass


def load_license_local() -> str:
    if os.path.exists(LICENSE_FILE):
        try:
            data = json.load(open(LICENSE_FILE, "r", encoding="utf-8"))
            return str(data.get("key", "")).strip()
        except Exception:
            pass
    return ""


async def verify_license_online(license_key: str, device_id: str) -> tuple[bool, str, dict]:
    payload = {
        "key": license_key,
        "license": license_key,
        "license_key": license_key,
        "device_id": device_id,
        "hwid": device_id,
    }
    endpoints = [
        f"{LICENSE_SERVER_URL.rstrip('/')}/verify",
        LICENSE_SERVER_URL.rstrip("/"),
    ]
    last_err = "خطا در ارتباط با سرور لایسنس"

    async with httpx.AsyncClient(timeout=15.0) as http:
        for url in endpoints:
            try:
                resp = await http.post(url, json=payload)
                if resp.status_code in (404, 405):
                    continue
                data = resp.json()
                status_str = str(data.get("status", "")).lower()
                is_valid = (
                    data.get("valid") is True
                    or data.get("ok") is True
                    or status_str in ("valid", "ok", "active", "success")
                )
                msg = (
                    data.get("message")
                    or data.get("error")
                    or data.get("msg")
                    or ("لایسنس معتبر است" if is_valid else "لایسنس نامعتبر یا منقضی است")
                )
                return is_valid, str(msg), data
            except Exception as ex:
                last_err = f"خطای شبکه: {ex}"

    return False, last_err, {}


def normalize_phone(raw: str) -> str:
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits.startswith("09") and len(digits) == 11:
        return "98" + digits[1:]
    if digits.startswith("9") and len(digits) == 10:
        return "98" + digits
    return digits


def session_exists() -> bool:
    return (
        os.path.exists(SESSION_PATH)
        or os.path.exists(f"{SESSION_PATH}.session")
        or os.path.exists(f"{SESSION_PATH}.json")
    )


async def main(page: ft.Page):
    page.title = "V3X Soroush+ Selfbot"
    page.bgcolor = "#0B1120"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 16
    page.scroll = ft.ScrollMode.AUTO
    page.rtl = True

    device_id = get_device_id()
    state = {
        "license_key": "",
        "license_info": {},
        "client": None,
        "phone": "",
        "phone_code_hash": None,
        "client_task": None,
        "turbo_running": False,
        "turbo_task": None,
        "auto_reply_enabled": False,
        "auto_reply_text": "سلام! در حال حاضر آفلاین هستم، پیام شما ثبت شد.",
        "auto_reply_pv_only": True,
        "last_replied": {},
        "logs": [],
    }

    log_view = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=150)

    def add_log(text: str, color: str = "#94A3B8"):
        ts = time.strftime("%H:%M:%S")
        state["logs"].append((f"[{ts}] {text}", color))
        if len(state["logs"]) > 40:
            state["logs"] = state["logs"][-40:]
        log_view.controls = [
            ft.Text(msg, size=12, color=col, selectable=True)
            for msg, col in reversed(state["logs"])
        ]
        try:
            page.update()
        except Exception:
            pass

    async def copy_text(val: str, status_ctrl: ft.Text):
        try:
            res = page.set_clipboard(val)
            if inspect.isawaitable(res):
                await res
            status_ctrl.value = "شناسه دستگاه کپی شد ✅"
            status_ctrl.color = "#10B981"
        except Exception:
            status_ctrl.value = "متن را انتخاب و دستی کپی کنید"
            status_ctrl.color = "#F59E0B"
        page.update()

    def build_client() -> Client:
        if state["client"] is not None:
            return state["client"]
        client = Client(SESSION_PATH)
        state["client"] = client
        return client

    async def start_listener(client: Client):
        if events is not None:
            @client.on(events.NewMessage(incoming=True))
            async def on_new_message(event):
                if not state["auto_reply_enabled"]:
                    return
                try:
                    if getattr(event, "out", False):
                        return
                    if state["auto_reply_pv_only"] and not getattr(event, "is_private", True):
                        return
                    sender_id = str(getattr(event, "sender_id", "") or getattr(event, "chat_id", "unknown"))
                    now = time.time()
                    if now - state["last_replied"].get(sender_id, 0) < 15:
                        return
                    state["last_replied"][sender_id] = now
                    await event.reply(state["auto_reply_text"])
                    add_log(f"ریپلای خودکار ارسال شد به: {sender_id}", "#10B981")
                except Exception as ex:
                    add_log(f"خطای ریپلای خودکار: {ex}", "#EF4444")

        try:
            if hasattr(client, "run_until_disconnected"):
                await client.run_until_disconnected()
        except asyncio.CancelledError:
            pass
        except Exception as ex:
            add_log(f"قطع ارتباط پس‌زمینه: {ex}", "#F59E0B")

    # ==========================================
    # صفحه ۱: فعال‌سازی لایسنس
    # ==========================================
    def show_license_screen(initial_msg: str = ""):
        page.clean()
        status_text = ft.Text(initial_msg, size=13, color="#F59E0B")
        key_input = ft.TextField(
            label="کلید لایسنس (License Key)",
            hint_text="V3X-XXXX-XXXX",
            value=load_license_local(),
            text_align=ft.TextAlign.LEFT,
            bgcolor="#1E293B",
            border_color="#334155",
            border_radius=10,
        )
        device_box = ft.TextField(
            label="شناسه سخت‌افزاری دستگاه شما (Device ID)",
            value=device_id,
            read_only=True,
            text_align=ft.TextAlign.LEFT,
            bgcolor="#0F172A",
            border_color="#334155",
            border_radius=10,
        )

        async def on_verify_click(e):
            key = (key_input.value or "").strip()
            if not key:
                status_text.value = "لطفاً کلید لایسنس را وارد کنید."
                status_text.color = "#EF4444"
                page.update()
                return

            verify_btn.disabled = True
            status_text.value = "در حال بررسی لایسنس در سرور..."
            status_text.color = "#38BDF8"
            page.update()

            ok, msg, info = await verify_license_online(key, device_id)
            verify_btn.disabled = False

            if not ok:
                status_text.value = f"❌ {msg}"
                status_text.color = "#EF4444"
                page.update()
                return

            state["license_key"] = key
            state["license_info"] = info
            save_license_local(key, info)
            status_text.value = "✅ لایسنس تایید شد! در حال بررسی وضعیت اکانت..."
            status_text.color = "#10B981"
            page.update()

            # بررسی دقیق نشست قبلی؛ اگر سشن واقعی وجود نداشت حتماً به صفحه شماره می‌رود
            if session_exists():
                try:
                    client = build_client()
                    await client.connect()
                    authorized = await client.is_user_authorized()
                    if authorized is True:
                        show_dashboard()
                        return
                except Exception:
                    pass

            show_phone_screen()

        verify_btn = ft.ElevatedButton(
            "بررسی و ورود",
            bgcolor="#2563EB",
            color="#FFFFFF",
            height=48,
            on_click=on_verify_click,
        )
        copy_btn = ft.OutlinedButton(
            "📋 کپی شناسه دستگاه",
            on_click=lambda e: page.run_task(copy_text, device_id, status_text),
        )

        page.add(
            ft.Container(
                bgcolor="#111827",
                padding=20,
                border_radius=14,
                content=ft.Column(
                    spacing=14,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("V3X SELFBOT", size=24, weight=ft.FontWeight.BOLD, color="#38BDF8"),
                        ft.Text("فعال‌سازی لایسنس و قفل سخت‌افزاری", size=14, color="#94A3B8"),
                        ft.Divider(color="#1F2937"),
                        device_box,
                        copy_btn,
                        key_input,
                        verify_btn,
                        status_text,
                    ],
                ),
            )
        )
        page.update()

    # ==========================================
    # صفحه ۲: ورود شماره موبایل سروش‌پلاس
    # ==========================================
    def show_phone_screen(initial_msg: str = ""):
        page.clean()
        status_text = ft.Text(initial_msg, size=13, color="#F59E0B")
        phone_input = ft.TextField(
            label="شماره موبایل سروش‌پلاس",
            hint_text="09123456789",
            keyboard_type=ft.KeyboardType.PHONE,
            text_align=ft.TextAlign.LEFT,
            bgcolor="#1E293B",
            border_color="#334155",
            border_radius=10,
        )

        async def on_send_code(e):
            raw_phone = (phone_input.value or "").strip()
            phone = normalize_phone(raw_phone)
            if len(phone) < 10:
                status_text.value = "لطفاً یک شماره موبایل معتبر وارد کنید (مثلاً 09123456789)."
                status_text.color = "#EF4444"
                page.update()
                return

            send_btn.disabled = True
            status_text.value = "در حال اتصال به سروش‌پلاس و ارسال کد..."
            status_text.color = "#38BDF8"
            page.update()

            try:
                client = build_client()
                await client.connect()
                res = await client.send_code(phone)
                state["phone"] = phone
                if isinstance(res, str):
                    state["phone_code_hash"] = res
                elif isinstance(res, dict):
                    state["phone_code_hash"] = res.get("phone_code_hash")
                else:
                    state["phone_code_hash"] = getattr(res, "phone_code_hash", None)

                send_btn.disabled = False
                show_otp_screen()
            except Exception as ex:
                send_btn.disabled = False
                status_text.value = f"خطا در ارسال کد: {ex}"
                status_text.color = "#EF4444"
                page.update()

        send_btn = ft.ElevatedButton(
            "ارسال کد تایید",
            bgcolor="#10B981",
            color="#FFFFFF",
            height=48,
            on_click=on_send_code,
        )

        page.add(
            ft.Container(
                bgcolor="#111827",
                padding=20,
                border_radius=14,
                content=ft.Column(
                    spacing=14,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("ورود به حساب سروش‌پلاس", size=20, weight=ft.FontWeight.BOLD, color="#F9FAFB"),
                        ft.Text("شماره خود را وارد کنید تا کد تایید ارسال شود:", size=13, color="#94A3B8"),
                        phone_input,
                        send_btn,
                        status_text,
                    ],
                ),
            )
        )
        page.update()

    # ==========================================
    # صفحه ۳: ورود کد تایید (OTP)
    # ==========================================
    def show_otp_screen():
        page.clean()
        status_text = ft.Text(f"کد تایید به شماره {state['phone']} ارسال شد.", size=13, color="#38BDF8")
        code_input = ft.TextField(
            label="کد تایید پیامک / سروش‌پلاس",
            hint_text="12345",
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.LEFT,
            bgcolor="#1E293B",
            border_color="#334155",
            border_radius=10,
        )

        async def on_confirm_code(e):
            code = (code_input.value or "").strip()
            if len(code) < 4:
                status_text.value = "لطفاً کد تایید را کامل وارد کنید."
                status_text.color = "#EF4444"
                page.update()
                return

            confirm_btn.disabled = True
            status_text.value = "در حال تایید کد و ورود..."
            status_text.color = "#38BDF8"
            page.update()

            try:
                client = build_client()
                sig = inspect.signature(client.sign_in)
                params = sig.parameters

                if "phone_code_hash" in params and state["phone_code_hash"]:
                    await client.sign_in(
                        phone=state["phone"],
                        code=code,
                        phone_code_hash=state["phone_code_hash"],
                    )
                else:
                    await client.sign_in(state["phone"], code)

                authorized = await client.is_user_authorized()
                if authorized is not True:
                    raise RuntimeError("احراز هویت کامل نشد؛ کد را دوباره بررسی کنید.")

                confirm_btn.disabled = False
                show_dashboard()
            except Exception as ex:
                confirm_btn.disabled = False
                status_text.value = f"خطا در تایید کد: {ex}"
                status_text.color = "#EF4444"
                page.update()

        confirm_btn = ft.ElevatedButton(
            "تایید کد و ورود به سلف‌بات",
            bgcolor="#2563EB",
            color="#FFFFFF",
            height=48,
            on_click=on_confirm_code,
        )
        back_btn = ft.TextButton(
            "تغییر شماره موبایل",
            on_click=lambda e: show_phone_screen(),
        )

        page.add(
            ft.Container(
                bgcolor="#111827",
                padding=20,
                border_radius=14,
                content=ft.Column(
                    spacing=14,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("تایید کد ورود", size=20, weight=ft.FontWeight.BOLD, color="#F9FAFB"),
                        code_input,
                        confirm_btn,
                        back_btn,
                        status_text,
                    ],
                ),
            )
        )
        page.update()

    # ==========================================
    # صفحه ۴: پنل اصلی مدیریت سلف‌بات
    # ==========================================
    def show_dashboard():
        page.clean()
        client = build_client()

        if state["client_task"] is None or state["client_task"].done():
            state["client_task"] = asyncio.create_task(start_listener(client))

        add_log("سلف‌بات با موفقیت به سروش‌پلاس متصل شد ✅", "#10B981")

        # --- بخش ریپلای خودکار ---
        ar_switch = ft.Switch(
            label="فعال‌سازی ریپلای خودکار",
            value=state["auto_reply_enabled"],
        )
        ar_pv_switch = ft.Switch(
            label="فقط در چت خصوصی (PV)",
            value=state["auto_reply_pv_only"],
        )
        ar_text_input = ft.TextField(
            label="متن پاسخ خودکار",
            value=state["auto_reply_text"],
            multiline=True,
            min_lines=2,
            bgcolor="#1E293B",
            border_color="#334155",
            border_radius=10,
        )

        def save_auto_reply(e):
            state["auto_reply_enabled"] = bool(ar_switch.value)
            state["auto_reply_pv_only"] = bool(ar_pv_switch.value)
            state["auto_reply_text"] = (ar_text_input.value or "").strip() or "پاسخ خودکار"
            status_str = "روشن" if state["auto_reply_enabled"] else "خاموش"
            add_log(f"تنظیمات ریپلای خودکار ذخیره شد ({status_str})", "#38BDF8")

        # --- بخش موتور ارسال توربو ---
        target_input = ft.TextField(
            label="شناسه چت / آیدی مقصد (Chat ID / GUID)",
            hint_text="مثال: u0XXXX... یا @username",
            text_align=ft.TextAlign.LEFT,
            bgcolor="#1E293B",
            border_color="#334155",
            border_radius=10,
        )
        turbo_msg_input = ft.TextField(
            label="متن پیام توربو",
            hint_text="متن مورد نظر برای ارسال سریع...",
            bgcolor="#1E293B",
            border_color="#334155",
            border_radius=10,
        )
        count_input = ft.TextField(
            label="تعداد ارسال",
            value="20",
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.LEFT,
            bgcolor="#1E293B",
            border_color="#334155",
            border_radius=10,
            expand=True,
        )
        delay_input = ft.TextField(
            label="تاخیر (ثانیه)",
            value="0.1",
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.LEFT,
            bgcolor="#1E293B",
            border_color="#334155",
            border_radius=10,
            expand=True,
        )
        turbo_counter = ft.Text("آماده ارسال", size=13, color="#94A3B8")

        async def run_turbo_loop(target: str, text: str, total: int, delay: float):
            sent = 0
            add_log(f"شروع ارسال توربو ({total} پیام) به {target}", "#38BDF8")
            try:
                while state["turbo_running"] and sent < total:
                    await client.send_message(target, text)
                    sent += 1
                    turbo_counter.value = f"ارسال شده: {sent} از {total}"
                    turbo_counter.color = "#10B981"
                    page.update()
                    if delay > 0:
                        await asyncio.sleep(delay)
                add_log(f"عملیات توربو پایان یافت ({sent} پیام ارسال شد)", "#10B981")
            except asyncio.CancelledError:
                add_log("ارسال توربو متوقف شد.", "#F59E0B")
            except Exception as ex:
                add_log(f"خطا در ارسال توربو: {ex}", "#EF4444")
                turbo_counter.value = f"خطا: {ex}"
                turbo_counter.color = "#EF4444"
            finally:
                state["turbo_running"] = False
                turbo_btn.text = "🚀 شروع ارسال توربو"
                turbo_btn.bgcolor = "#10B981"
                page.update()

        async def toggle_turbo(e):
            if state["turbo_running"]:
                state["turbo_running"] = False
                if state["turbo_task"]:
                    state["turbo_task"].cancel()
                return

            target = (target_input.value or "").strip()
            msg_txt = (turbo_msg_input.value or "").strip()
            if not target or not msg_txt:
                add_log("مقصد و متن پیام توربو را وارد کنید.", "#EF4444")
                return

            try:
                total = max(1, int(count_input.value or "10"))
                delay = max(0.0, float(delay_input.value or "0.1"))
            except ValueError:
                add_log("تعداد یا تاخیر نامعتبر است.", "#EF4444")
                return

            state["turbo_running"] = True
            turbo_btn.text = "⛔ توقف فوری توربو"
            turbo_btn.bgcolor = "#EF4444"
            page.update()
            state["turbo_task"] = asyncio.create_task(run_turbo_loop(target, msg_txt, total, delay))

        turbo_btn = ft.ElevatedButton(
            "🚀 شروع ارسال توربو",
            bgcolor="#10B981",
            color="#FFFFFF",
            height=46,
            on_click=toggle_turbo,
        )

        async def logout_account(e):
            state["turbo_running"] = False
            if state["client_task"]:
                state["client_task"].cancel()
            try:
                await client.disconnect()
            except Exception:
                pass
            state["client"] = None
            for ext in ("", ".session", ".json"):
                p = f"{SESSION_PATH}{ext}"
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
            show_phone_screen("از حساب خارج شدید. شماره جدید وارد کنید.")

        page.add(
            ft.Container(
                bgcolor="#111827",
                padding=16,
                border_radius=14,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text("⚡ V3X Selfbot Panel", size=20, weight=ft.FontWeight.BOLD, color="#38BDF8"),
                                ft.TextButton("خروج از اکانت", on_click=logout_account),
                            ],
                        ),
                        ft.Text(f"شناسه دستگاه: {device_id}", size=12, color="#94A3B8"),
                    ],
                ),
            ),
            ft.Container(
                bgcolor="#111827",
                padding=16,
                border_radius=14,
                content=ft.Column(
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("🚀 موتور ارسال توربو", size=16, weight=ft.FontWeight.BOLD, color="#F9FAFB"),
                        target_input,
                        turbo_msg_input,
                        ft.Row(spacing=10, controls=[count_input, delay_input]),
                        turbo_btn,
                        turbo_counter,
                    ],
                ),
            ),
            ft.Container(
                bgcolor="#111827",
                padding=16,
                border_radius=14,
                content=ft.Column(
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("🤖 ریپلای خودکار", size=16, weight=ft.FontWeight.BOLD, color="#F9FAFB"),
                        ar_switch,
                        ar_pv_switch,
                        ar_text_input,
                        ft.ElevatedButton("ذخیره تنظیمات ریپلای", bgcolor="#2563EB", color="#FFFFFF", on_click=save_auto_reply),
                    ],
                ),
            ),
            ft.Container(
                bgcolor="#0F172A",
                padding=14,
                border_radius=14,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Text("📜 گزارش زنده عملکرد (Logs)", size=14, weight=ft.FontWeight.BOLD, color="#94A3B8"),
                        log_view,
                    ],
                ),
            ),
        )
        page.update()

    # شروع برنامه با بررسی خودکار لایسنس ذخیره شده
    saved_key = load_license_local()
    if saved_key:
        ok, msg, info = await verify_license_online(saved_key, device_id)
        if ok:
            state["license_key"] = saved_key
            state["license_info"] = info
            if session_exists():
                try:
                    c = build_client()
                    await c.connect()
                    if await c.is_user_authorized() is True:
                        show_dashboard()
                        return
                except Exception:
                    pass
            show_phone_screen()
            return
        else:
            show_license_screen(f"وضعیت لایسنس قبلی: {msg}")
            return

    show_license_screen()


if __name__ == "__main__":
    ft.app(target=main)
