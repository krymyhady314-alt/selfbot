import asyncio
import importlib
import inspect
import json
import os
import pkgutil
import platform
import tempfile
import time
import uuid

import flet as ft
import httpx

LICENSE_SERVER_URL = "https://selfbot-license.krymyhady314.workers.dev"

# مسیر مجاز و قابل نوشتن در حافظه داخلی اندروید
STORAGE_DIR = os.getenv("FLET_APP_STORAGE_DATA") or tempfile.gettempdir()
os.makedirs(STORAGE_DIR, exist_ok=True)

DEVICE_ID_FILE = os.path.join(STORAGE_DIR, "v3x_device_id.txt")
LICENSE_FILE = os.path.join(STORAGE_DIR, "v3x_license.json")
SESSION_PATH = os.path.join(STORAGE_DIR, "v3x_soroush_session")


def resolve_client_class():
    """کلاس اصلی کلاینت را به‌صورت خودکار از داخل پکیج splusthon پیدا می‌کند."""
    import splusthon

    for direct_name in ("SPlusClient", "Client", "SoroushClient", "UserClient"):
        cls = getattr(splusthon, direct_name, None)
        if inspect.isclass(cls):
            return cls

    candidates = []
    if hasattr(splusthon, "__path__"):
        for _, mod_name, _ in pkgutil.walk_packages(splusthon.__path__, prefix="splusthon."):
            try:
                mod = importlib.import_module(mod_name)
                for attr_name, obj in inspect.getmembers(mod, inspect.isclass):
                    if obj.__module__ != mod_name:
                        continue
                    low = attr_name.lower()
                    if "client" in low and not any(x in low for x in ("base", "http", "abstract", "bot")):
                        candidates.append((attr_name, obj))
            except Exception:
                continue

    priority = ("SPlusClient", "Client", "SoroushClient", "UserClient")
    for p in priority:
        for name, obj in candidates:
            if name == p:
                return obj

    if candidates:
        return candidates[0][1]

    raise RuntimeError(f"کلاس کلاینت در splusthon پیدا نشد. محتویات: {dir(splusthon)}")


def instantiate_client(session_path: str):
    """ساخت نمونه کلاینت با تطبیق خودکار آرگومان‌های سازنده."""
    cls = resolve_client_class()
    sig = inspect.signature(cls.__init__)
    params = [p for name, p in sig.parameters.items() if name != "self"]

    if not params:
        return cls()

    kwargs = {}
    session_assigned = False
    for p in params:
        if p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        if p.name in ("name", "session", "session_name", "path", "session_path"):
            kwargs[p.name] = session_path
            session_assigned = True
        elif p.default is inspect.Parameter.empty and not session_assigned:
            kwargs[p.name] = session_path
            session_assigned = True

    try:
        return cls(**kwargs)
    except TypeError:
        return cls(session_path)


async def invoke_smart(obj, method_names: tuple, kwargs_pool: dict, positional_fallback: tuple = ()):
    """متد مناسب را در کلاینت پیدا کرده و با پارامترهای سازگار اجرا می‌کند."""
    targets = [obj]
    for sub in ("auth", "account", "messages", "methods"):
        if hasattr(obj, sub):
            targets.append(getattr(obj, sub))

    fn = None
    for target in targets:
        for m_name in method_names:
            cand = getattr(target, m_name, None)
            if callable(cand):
                fn = cand
                break
        if fn is not None:
            break

    if fn is None:
        avail = [m for m in dir(obj) if not m.startswith("_")]
        raise AttributeError(f"متد {method_names} یافت نشد. متدهای موجود: {avail[:25]}")

    sig = inspect.signature(fn)
    params = sig.parameters
    has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())

    call_kwargs = {}
    for p_name, p_obj in params.items():
        if p_name == "self":
            continue
        if p_name in kwargs_pool:
            call_kwargs[p_name] = kwargs_pool[p_name]

    try:
        if call_kwargs or not positional_fallback:
            res = fn(**call_kwargs)
        else:
            res = fn(*positional_fallback)
    except TypeError:
        if has_var_kw:
            res = fn(**kwargs_pool)
        else:
            res = fn(*positional_fallback)

    if inspect.isawaitable(res):
        return await res
    return res


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


def normalize_phone(raw: str) -> tuple[str, str]:
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits.startswith("09") and len(digits) == 11:
        return "98" + digits[1:], digits
    if digits.startswith("989") and len(digits) == 12:
        return digits, "0" + digits[2:]
    if digits.startswith("9") and len(digits) == 10:
        return "98" + digits, "0" + digits
    return digits, digits


def session_exists() -> bool:
    try:
        base_name = os.path.basename(SESSION_PATH)
        return any(f.startswith(base_name) for f in os.listdir(STORAGE_DIR))
    except Exception:
        return False


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
        "phone_local": "",
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

    def build_client():
        if state["client"] is not None:
            return state["client"]
        client = instantiate_client(SESSION_PATH)
        state["client"] = client
        return client

    async def ensure_connected(client):
        for m in ("connect", "initialize", "init"):
            fn = getattr(client, m, None)
            if callable(fn):
                res = fn()
                if inspect.isawaitable(res):
                    await res
                return

    async def check_authorized(client) -> bool:
        try:
            await ensure_connected(client)
            for m in ("is_user_authorized", "is_authorized", "check_auth"):
                fn = getattr(client, m, None)
                if callable(fn):
                    res = fn()
                    if inspect.isawaitable(res):
                        res = await res
                    return bool(res)
            me = await invoke_smart(client, ("get_me", "get_self"), {})
            return me is not None
        except Exception:
            return False

    async def start_listener(client):
        try:
            if hasattr(client, "on_message"):
                @client.on_message()
                async def on_new_msg(update):
                    if not state["auto_reply_enabled"]:
                        return
                    try:
                        if getattr(update, "is_outgoing", False) or getattr(update, "out", False):
                            return
                        chat_id = (
                            getattr(update, "object_guid", None)
                            or getattr(update, "chat_id", None)
                            or getattr(update, "author_guid", None)
                        )
                        if not chat_id:
                            return
                        if state["auto_reply_pv_only"] and not str(chat_id).startswith("u0"):
                            return
                        now = time.time()
                        if now - state["last_replied"].get(str(chat_id), 0) < 15:
                            return
                        state["last_replied"][str(chat_id)] = now
                        await send_soroush_message(client, str(chat_id), state["auto_reply_text"])
                        add_log(f"ریپلای خودکار ارسال شد به: {chat_id}", "#10B981")
                    except Exception as ex:
                        add_log(f"خطای ریپلای خودکار: {ex}", "#EF4444")

            for runner in ("run_until_disconnected", "run", "idle"):
                fn = getattr(client, runner, None)
                if callable(fn):
                    res = fn()
                    if inspect.isawaitable(res):
                        await res
                    break
        except asyncio.CancelledError:
            pass
        except Exception as ex:
            add_log(f"وضعیت پس‌زمینه: {ex}", "#F59E0B")

    async def send_soroush_message(client, target: str, text: str):
        await invoke_smart(
            client,
            ("send_message", "send_text", "send_msg"),
            {
                "object_guid": target,
                "chat_id": target,
                "peer": target,
                "guid": target,
                "user_id": target,
                "text": text,
                "message": text,
                "msg": text,
            },
            positional_fallback=(target, text),
        )

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

            if session_exists():
                try:
                    client = build_client()
                    if await check_authorized(client):
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
        status_text = ft.Text(initial_msg, size=13, color="#F59E0B", selectable=True)
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
            phone_intl, phone_local = normalize_phone(raw_phone)
            if len(phone_intl) < 10:
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
                await ensure_connected(client)

                used_phone = phone_intl
                try:
                    res = await invoke_smart(
                        client,
                        ("send_code", "request_code", "send_verification_code", "send_otp"),
                        {
                            "phone_number": phone_intl,
                            "phone": phone_intl,
                            "mobile": phone_intl,
                            "number": phone_intl,
                        },
                        positional_fallback=(phone_intl,),
                    )
                except Exception:
                    used_phone = phone_local
                    res = await invoke_smart(
                        client,
                        ("send_code", "request_code", "send_verification_code", "send_otp"),
                        {
                            "phone_number": phone_local,
                            "phone": phone_local,
                            "mobile": phone_local,
                            "number": phone_local,
                        },
                        positional_fallback=(phone_local,),
                    )

                state["phone"] = used_phone
                state["phone_local"] = phone_local
                if isinstance(res, str):
                    state["phone_code_hash"] = res
                elif isinstance(res, dict):
                    state["phone_code_hash"] = (
                        res.get("phone_code_hash")
                        or res.get("code_hash")
                        or res.get("hash")
                    )
                else:
                    state["phone_code_hash"] = (
                        getattr(res, "phone_code_hash", None)
                        or getattr(res, "code_hash", None)
                        or getattr(res, "hash", None)
                    )

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
                    
