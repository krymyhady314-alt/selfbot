import asyncio
import hashlib
import inspect
import json
import os
import re
import time
import uuid
import flet as ft
import httpx

Client = None
SPLUSTHON_MOD = None
SPLUSTHON_ERR = "کتابخانه splusthon روی این پایتون نصب نیست. در ترمینال بزنید: python -m pip install -U splusthon"
try:
    import splusthon as SPLUSTHON_MOD

    Client = (
        getattr(SPLUSTHON_MOD, "Client", None)
        or getattr(SPLUSTHON_MOD, "SplusClient", None)
        or getattr(SPLUSTHON_MOD, "SoroushClient", None)
    )
    if Client is None:
        SPLUSTHON_ERR = f"کلاس کلاینت در splusthon پیدا نشد. محتویات: {dir(SPLUSTHON_MOD)}"
except Exception as e:
    SPLUSTHON_ERR = f"خطای بارگذاری splusthon: {e}"

# ==========================================================
# تنظیمات اصلی سرور لایسنس (متصل به Cloudflare Worker)
# ==========================================================
SERVER_URL = "https://selfbot-license.krymyhady314.workers.dev"
APP_TITLE = "V3X Soroush+ Selfbot"
HTTP_CLIENT = httpx.AsyncClient(timeout=12)


def normalize_iran_phone(raw: str) -> str:
    """تبدیل خودکار تمام فرمت‌های شماره موبایل ایران به +989XXXXXXXXX"""
    if not raw:
        return ""
    trans_table = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    cleaned = raw.translate(trans_table).strip()
    cleaned = re.sub(r"[\s\-\(\)]", "", cleaned)

    if cleaned.startswith("0098"):
        cleaned = "+98" + cleaned[4:]
    elif cleaned.startswith("+98"):
        pass
    elif cleaned.startswith("98") and len(cleaned) == 12:
        cleaned = "+" + cleaned
    elif cleaned.startswith("09") and len(cleaned) == 11:
        cleaned = "+98" + cleaned[1:]
    elif cleaned.startswith("9") and len(cleaned) == 10:
        cleaned = "+98" + cleaned

    return cleaned


def get_storage_dir() -> str:
    """مسیر ذخیره‌سازی امن برای ویندوز و اندروید"""
    base = os.getenv("FLET_APP_STORAGE_DATA") or os.path.expanduser("~")
    path = os.path.join(base, ".v3x_selfbot_data")
    os.makedirs(path, exist_ok=True)
    return path


STORAGE_DIR = get_storage_dir()
CONFIG_FILE = os.path.join(STORAGE_DIR, "config.json")
SESSION_PATH = os.path.join(STORAGE_DIR, "v3x_session")


def session_exists() -> bool:
    return any(fname.startswith("v3x_session") for fname in os.listdir(STORAGE_DIR))


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(data: dict) -> None:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_device_id() -> str:
    """تولید و ذخیره شناسه یکتای سخت‌افزاری دستگاه"""
    cfg = load_config()
    if cfg.get("device_id"):
        return cfg["device_id"]

    raw = f"{uuid.getnode()}-{os.name}-{uuid.uuid4().hex[:8]}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12].upper()
    dev_id = f"V3X-DEV-{digest}"
    cfg["device_id"] = dev_id
    save_config(cfg)
    return dev_id


def pick(obj, *keys, default=None):
    """استخراج ایمن مقدار از دیکشنری یا آبجکت"""
    if obj is None:
        return default
    for k in keys:
        if isinstance(obj, dict) and k in obj and obj[k] is not None:
            return obj[k]
        val = getattr(obj, k, None)
        if val is not None:
            return val
    return default


async def resolve_iterable(items):
    """تبدیل لیست، دیکشنری یا AsyncGenerator به لیست معمولی"""
    if items is None:
        return []
    if isinstance(items, dict):
        for k in ("dialogs", "chats", "messages", "items", "result", "data"):
            if isinstance(items.get(k), list):
                return items[k]
        return list(items.values())
    if inspect.isasyncgen(items):
        out = []
        async for x in items:
            out.append(x)
        return out
    try:
        return list(items)
    except TypeError:
        return [items]


async def run_smart(func, *args, timeout: float = 15.0, **kwargs):
    """اجرای سریع توابع همگام و ناهمگام بدون سربار اضافی"""
    if inspect.iscoroutinefunction(func):
        return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
    res = func(*args, **kwargs)
    if inspect.isawaitable(res):
        return await asyncio.wait_for(res, timeout=timeout)
    return res


def build_splusthon_client():
    """ساخت نمونه کلاینت سازگار با نسخه‌های مختلف splusthon"""
    try:
        return Client(SESSION_PATH)
    except TypeError:
        try:
            return Client(session_name=SESSION_PATH)
        except TypeError:
            return Client()


async def verify_license_online(license_key: str, device_id: str) -> dict:
    url = f"{SERVER_URL.rstrip('/')}/api/verify"
    try:
        resp = await HTTP_CLIENT.post(
            url,
            json={"key": license_key.strip().upper(), "device_id": device_id},
        )
        if resp.status_code == 200:
            return resp.json()
        return {"valid": False, "days_left": 0, "msg": f"خطای سرور ({resp.status_code})"}
    except Exception as e:
        return {"valid": False, "days_left": 0, "msg": f"خطا در اتصال به سرور: {e}"}


async def main(page: ft.Page):
    page.title = APP_TITLE
    page.rtl = True
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0B0E14"
    page.padding = 16
    page.scroll = ft.ScrollMode.AUTO

    try:
        page.window.width = 480
        page.window.height = 840
    except Exception:
        pass

    device_id = get_device_id()
    cfg = load_config()

    state = {
        "days_left": 0,
        "client": None,
        "my_id": None,
        "phone": "",
        "phone_hash": "",
        "chats": {},
        "selected_chat_id": "",
        "reply_to_id": None,
        "reply_preview": "",
        "running": False,
        "sent_count": 0,
    }

    def notify(text: str, is_error: bool = False):
        try:
            sb = ft.SnackBar(
                content=ft.Text(text, color=ft.Colors.WHITE, weight=ft.FontWeight.W_600),
                bgcolor="#B91C1C" if is_error else "#047857",
                open=True,
            )
            if hasattr(page, "show_dialog"):
                page.show_dialog(sb)
            else:
                page.overlay.append(sb)
                page.update()
        except Exception:
            pass

    # ==========================================================
    # بخش ۱: صفحه فعال‌سازی لایسنس
    # ==========================================================
    license_input = ft.TextField(
        label="کد لایسنس (مثال: V3X-XXXX-XXXX)",
        value=cfg.get("license_key", ""),
        border_color="#38BDF8",
        text_align=ft.TextAlign.LEFT,
    )
    license_status_text = ft.Text("", size=13, color="#F87171")

    async def copy_device_id(_):
        try:
            if hasattr(page, "set_clipboard"):
                res = page.set_clipboard(device_id)
                if inspect.isawaitable(res):
                    await res
            else:
                cb = ft.Clipboard()
                page.overlay.append(cb)
                res = cb.set(device_id)
                if inspect.isawaitable(res):
                    await res
            notify("شناسه دستگاه کپی شد.")
        except Exception:
            notify(f"شناسه: {device_id}")

    async def handle_activate_license(_=None):
        key = (license_input.value or "").strip().upper()
        if not key:
            license_status_text.value = "لطفاً کد لایسنس را وارد کنید."
            license_status_text.update()
            return

        activate_btn.disabled = True
        license_status_text.value = "در حال بررسی لایسنس..."
        license_status_text.color = "#38BDF8"
        page.update()

        res = await verify_license_online(key, device_id)
        activate_btn.disabled = False

        if res.get("valid"):
            cfg["license_key"] = key
            save_config(cfg)
            state["days_left"] = res.get("days_left", 0)
            days_badge.content.value = f"اعتبار: {state['days_left']} روز"
            license_view.visible = False
            login_view.visible = True
            page.update()
            await init_soroush_session(auto=True)
        else:
            license_status_text.value = res.get("msg", "لایسنس نامعتبر است.")
            license_status_text.color = "#F87171"
            page.update()

    activate_btn = ft.Button(
        "بررسی و ورود به برنامه",
        icon=ft.Icons.VERIFIED_USER,
        bgcolor="#0284C7",
        color=ft.Colors.WHITE,
        width=420,
        height=46,
        on_click=handle_activate_license,
    )

    license_view = ft.Container(
        visible=True,
        padding=20,
        border_radius=16,
        bgcolor="#131824",
        border=ft.Border.all(1, "#1E293B"),
        content=ft.Column(
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.SHIELD, size=48, color="#38BDF8"),
                ft.Text("سیستم احراز هویت و لایسنس", size=20, weight=ft.FontWeight.BOLD),
                ft.Container(
                    padding=10,
                    border_radius=10,
                    bgcolor="#0B0E14",
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(f"Device ID: {device_id}", size=12, color="#94A3B8"),
                            ft.IconButton(
                                icon=ft.Icons.COPY,
                                icon_size=18,
                                tooltip="کپی شناسه",
                                on_click=copy_device_id,
                            ),
                        ],
                    ),
                ),
                license_input,
                activate_btn,
                license_status_text,
            ],
        ),
    )

    # ==========================================================
    # بخش ۲: صفحه اتصال به حساب سروش‌پلاس
    # ==========================================================
    phone_input = ft.TextField(
        label="شماره موبایل (0912... یا +98912...)",
        value=cfg.get("phone", ""),
        keyboard_type=ft.KeyboardType.PHONE,
        border_color="#38BDF8",
        text_align=ft.TextAlign.LEFT,
    )
    code_input = ft.TextField(
        label="کد تایید پیامک / سروش",
        visible=False,
        keyboard_type=ft.KeyboardType.NUMBER,
        border_color="#10B981",
        text_align=ft.TextAlign.LEFT,
    )
    login_status_text = ft.Text(
        SPLUSTHON_ERR if Client is None else "شماره خود را وارد کرده و دکمه ارسال کد را بزنید.",
        size=13,
        selectable=True,
        color="#F87171" if Client is None else "#94A3B8",
    )

    async def handle_send_code(_):
        if Client is None:
            notify(SPLUSTHON_ERR, is_error=True)
            login_status_text.value = SPLUSTHON_ERR
            login_status_text.color = "#F87171"
            login_status_text.update()
            return

        phone = normalize_iran_phone(phone_input.value or "")
        if not phone or not phone.startswith("+98") or len(phone) < 13:
            notify("شماره موبایل معتبر نیست (مثال: 09123456789).", is_error=True)
            login_status_text.value = f"فرمت شماره صحیح نیست ({phone_input.value}). مثال: 09123456789"
            login_status_text.color = "#F87171"
            login_status_text.update()
            return

        phone_input.value = phone
        send_code_btn.disabled = True
        login_status_text.value = f"در حال ارسال کد تایید به {phone} ..."
        login_status_text.color = "#38BDF8"
        page.update()

        try:
            client = state["client"] or build_splusthon_client()
            state["client"] = client

            if hasattr(client, "connect"):
                await run_smart(client.connect, timeout=15)

            send_method = None
            for m_name in ("send_code", "send_code_request", "request_code", "send_verification_code"):
                if hasattr(client, m_name):
                    send_method = getattr(client, m_name)
                    break

            if send_method is None:
                avail = [m for m in dir(client) if not m.startswith("_")]
                raise RuntimeError(f"متد ارسال کد پیدا نشد. متدهای موجود: {avail}")

            sent = None
            last_err = None
            for candidate in (phone, phone.lstrip("+"), "0" + phone[3:]):
                try:
                    sent = await run_smart(send_method, candidate, timeout=15)
                    phone = candidate
                    break
                except TypeError:
                    try:
                        sent = await run_smart(send_method, phone=candidate, timeout=15)
                        phone = candidate
                        break
                    except Exception as err2:
                        last_err = err2
                except Exception as err:
                    last_err = err

            if sent is None:
                raise last_err or RuntimeError("پاسخی از سرور سروش‌پلاس دریافت نشد.")

            state["phone"] = phone
            state["phone_hash"] = pick(sent, "phone_code_hash", "hash", default=str(sent))
            cfg["phone"] = phone
            save_config(cfg)

            code_input.visible = True
            verify_code_btn.visible = True
            login_status_text.value = "✅ کد تایید ارسال شد! کد پیامک/سروش را وارد کنید."
            login_status_text.color = "#34D399"
            notify("کد تایید ارسال شد.")
        except Exception as e:
            login_status_text.value = f"❌ خطا در ارسال کد: {e}"
            login_status_text.color = "#F87171"
        finally:
            send_code_btn.disabled = False
            page.update()

    async def handle_verify_code(_):
        raw_code = (code_input.value or "").strip()
        code = raw_code.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
        if not code:
            notify("کد تایید را وارد کنید.", is_error=True)
            return

        verify_code_btn.disabled = True
        login_status_text.value = "در حال ورود به حساب سروش‌پلاس..."
        login_status_text.color = "#38BDF8"
        page.update()

        try:
            client = state["client"]
            sign_method = None
            for m_name in ("sign_in", "verify_code", "login", "check_code"):
                if hasattr(client, m_name):
                    sign_method = getattr(client, m_name)
                    break

            if sign_method is None:
                raise RuntimeError("متد تایید کد (sign_in) در Client پیدا نشد.")

            try:
                await run_smart(sign_method, state["phone"], state["phone_hash"], code, timeout=15)
            except TypeError:
                try:
                    await run_smart(sign_method, state["phone"], code, timeout=15)
                except TypeError:
                    await run_smart(sign_method, phone=state["phone"], code=code, timeout=15)

            if hasattr(client, "get_me"):
                try:
                    me = await run_smart(client.get_me, timeout=10)
                    state["my_id"] = pick(me, "id", "user_id", "guid")
                except Exception:
                    pass

            register_in_chat_commands(client)

            login_view.visible = False
            main_view.visible = True
            notify("حساب سروش‌پلاس با موفقیت متصل شد.")
            page.update()
            page.run_task(fetch_chats)
        except Exception as e:
            login_status_text.value = f"❌ خطا در تایید کد: {e}"
            login_status_text.color = "#F87171"
        finally:
            verify_code_btn.disabled = False
            page.update()

    send_code_btn = ft.Button(
        "ارسال کد تایید",
        icon=ft.Icons.SEND_TO_MOBILE,
        bgcolor="#0284C7",
        color=ft.Colors.WHITE,
        width=420,
        height=44,
        on_click=handle_send_code,
    )
    verify_code_btn = ft.Button(
        "تایید کد و اتصال اکانت",
        icon=ft.Icons.LOGIN,
        bgcolor="#059669",
        color=ft.Colors.WHITE,
        visible=False,
        width=420,
        height=44,
        on_click=handle_verify_code,
    )

    login_view = ft.Container(
        visible=False,
        padding=20,
        border_radius=16,
        bgcolor="#131824",
        border=ft.Border.all(1, "#1E293B"),
        content=ft.Column(
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=48, color="#38BDF8"),
                ft.Text("اتصال به حساب سروش‌پلاس", size=19, weight=ft.FontWeight.BOLD),
                phone_input,
                send_code_btn,
                code_input,
                verify_code_btn,
                ft.Container(
                    padding=10,
                    border_radius=8,
                    bgcolor="#0B0E14",
                    width=420,
                    content=login_status_text,
                ),
            ],
        ),
    )

    # ==========================================================
    # بخش ۳: پنل اصلی کنترل سلف‌بات (موتور پرسرعت)
    # ==========================================================
    days_badge = ft.Container(
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
        border_radius=20,
        bgcolor="#064E3B",
        content=ft.Text("اعتبار: -- روز", size=12, color="#6EE7B7", weight=ft.FontWeight.BOLD),
    )

    chat_dropdown = ft.Dropdown(
        label="انتخاب از لیست چت‌ها / گروه‌ها",
        options=[],
        border_color="#38BDF8",
        expand=True,
    )

    target_chat_input = ft.TextField(
        label="آیدی عددی یا یوزرنیم چت / گروه مقصد",
        value=cfg.get("last_chat_id", ""),
        border_color="#38BDF8",
        text_align=ft.TextAlign.LEFT,
    )

    messages_column = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, height=150)
    reply_banner_text = ft.Text("حالت ارسال: عادی (بدون ریپلای)", size=12, color="#94A3B8")

    def clear_reply(_=None):
        state["reply_to_id"] = None
        state["reply_preview"] = ""
        reply_banner_text.value = "حالت ارسال: عادی (بدون ریپلای)"
        reply_banner_text.color = "#94A3B8"
        reply_banner_text.update()

    clear_reply_btn = ft.IconButton(
        icon=ft.Icons.CLOSE,
        icon_size=18,
        tooltip="لغو ریپلای",
        on_click=clear_reply,
    )

    msg_text_input = ft.TextField(
        label="متن پیام برای ارسال تکراری",
        multiline=True,
        min_lines=2,
        max_lines=4,
        border_color="#38BDF8",
    )
    interval_input = ft.TextField(
        label="فاصله زمانی (ثانیه - 0 = حداکثر سرعت)",
        value="0.1",
        keyboard_type=ft.KeyboardType.NUMBER,
        border_color="#38BDF8",
        expand=True,
    )
    count_input = ft.TextField(
        label="تعداد پیام (0 = نامحدود)",
        value="20",
        keyboard_type=ft.KeyboardType.NUMBER,
        border_color="#38BDF8",
        expand=True,
    )

    turbo_switch = ft.Switch(
        label="حالت توربو (ارسال همزمان فوق‌سریع با ۴ رشته)",
        value=True,
    )

    chat_cmd_switch = ft.Switch(
        label="دستورات داخل چت (.spam تعداد متن | .stop)",
        value=True,
    )

    status_badge = ft.Text("وضعیت: آماده به کار | ارسال‌شده: 0", size=13, selectable=True, color="#38BDF8")

    def set_status(text: str, color: str = "#38BDF8"):
        status_badge.value = text
        status_badge.color = color
        try:
            status_badge.update()
        except Exception:
            pass

    def get_active_chat_id() -> str:
        manual = (target_chat_input.value or "").strip()
        if manual:
            return manual
        return (state["selected_chat_id"] or chat_dropdown.value or "").strip()

    async def fetch_chats(_=None):
        client = state["client"]
        if not client:
            return

        set_status("در حال دریافت لیست چت‌ها...", "#38BDF8")
        try:
            dialog_method = None
            for method_name in ("get_dialogs", "get_chats", "get_all_chats", "dialogs", "chats"):
                if hasattr(client, method_name):
                    dialog_method = getattr(client, method_name)
                    break

            if dialog_method is None:
                set_status("آیدی چت را در کادر بالا وارد کنید.", "#FBBF24")
                return

            raw_dialogs = await run_smart(dialog_method, timeout=12) if callable(dialog_method) else dialog_method
            dialogs = await resolve_iterable(raw_dialogs)

            OptionCls = getattr(ft, "DropdownOption", None) or ft.dropdown.Option
            options = []
            state["chats"].clear()

            for d in dialogs:
                chat_obj = pick(d, "chat", "peer", "entity", default=d)
                cid = str(
                    pick(chat_obj, "id", "chat_id", "guid", "user_id", "peer_id")
                    or pick(d, "id", "chat_id", "guid", default="")
                ).strip()
                title = (
                    pick(chat_obj, "title", "name", "first_name", "username")
                    or pick(d, "title", "name")
                    or cid
                )
                if cid:
                    state["chats"][cid] = str(title)
                    options.append(OptionCls(key=cid, text=f"{title} ({cid})"))

            chat_dropdown.options = options
            if options:
                chat_dropdown.value = options[0].key
                state["selected_chat_id"] = options[0].key
                if not target_chat_input.value:
                    target_chat_input.value = options[0].key
                set_status(f"✅ {len(options)} چت بارگذاری شد.", "#34D399")
            else:
                set_status("چتی یافت نشد؛ آیدی چت را دستی وارد کنید.", "#FBBF24")
            page.update()
        except Exception as e:
            set_status(f"⚠️ دریافت لیست چت انجام نشد ({e}) — آیدی را دستی وارد کنید.", "#FBBF24")

    def on_chat_selected(e):
        val = str(e.control.value or "").strip()
        state["selected_chat_id"] = val
        if val:
            target_chat_input.value = val
            target_chat_input.update()
        clear_reply()

    chat_dropdown.on_change = on_chat_selected
    if hasattr(chat_dropdown, "on_select"):
        chat_dropdown.on_select = on_chat_selected

    async def fetch_chat_messages(_=None):
        client = state["client"]
        cid = get_active_chat_id()
        if not client or not cid:
            notify("ابتدا آیدی چت یا گروه را انتخاب/وارد کنید.", is_error=True)
            return

        messages_column.controls.clear()
        messages_column.update()
        set_status(f"در حال دریافت پیام‌های چت {cid}...", "#38BDF8")

        try:
            msg_method = None
            for method_name in ("get_messages", "get_history", "get_chat_history", "get_messages_history"):
                if hasattr(client, method_name):
                    msg_method = getattr(client, method_name)
                    break

            if msg_method is None:
                raise RuntimeError("متد دریافت پیام‌ها در این نسخه splusthon موجود نیست.")

            target_arg = int(cid) if cid.lstrip("-").isdigit() else cid
            try:
                raw_msgs = await run_smart(msg_method, target_arg, limit=30, timeout=12)
            except TypeError:
                raw_msgs = await run_smart(msg_method, target_arg, timeout=12)

            msgs = await resolve_iterable(raw_msgs)
            my_id = str(state["my_id"] or "")
            added = 0

            for m in msgs:
                is_out = bool(pick(m, "outgoing", "is_out", "from_me", default=False))
                sender = pick(m, "from_user", "sender", "author")
                sender_id = str(
                    pick(m, "sender_id", "from_id", "user_id")
                    or pick(sender, "id", "user_id", default="")
                )
                if is_out or (my_id and sender_id == my_id):
                    continue

                mid = pick(m, "id", "message_id", "msg_id")
                text = str(pick(m, "text", "message", "caption", default="[رسانه]")).strip()
                sender_name = str(
                    pick(sender, "first_name", "name", "title")
                    or pick(m, "sender_name", default="کاربر")
                )
                if not mid:
                    continue

                def make_select_handler(target_id, preview_txt):
                    def _select(_):
                        state["reply_to_id"] = target_id
                        state["reply_preview"] = preview_txt
                        reply_banner_text.value = f"ریپلای روی: {preview_txt[:38]}"
                        reply_banner_text.color = "#34D399"
                        reply_banner_text.update()

                    return _select

                preview = f"{sender_name}: {text}"
                messages_column.controls.append(
                    ft.Container(
                        padding=8,
                        border_radius=8,
                        bgcolor="#0B0E14",
                        border=ft.Border.all(1, "#1E293B"),
                        on_click=make_select_handler(mid, preview),
                        content=ft.Text(preview[:90], size=12, color="#E2E8F0"),
                    )
                )
                added += 1

            if added == 0:
                messages_column.controls.append(
                    ft.Text("پیامی از اعضای دیگر پیدا نشد.", size=12, color="#94A3B8")
                )
            messages_column.update()
            set_status(f"وضعیت: آماده | {added} پیام بارگذاری شد.", "#34D399")
        except Exception as e:
            set_status(f"❌ خطا در دریافت پیام‌ها: {e}", "#F87171")

    async def create_fast_sender(cid: str, text: str, reply_id=None):
        """ارسال پیام اول با تشخیص دقیق متد و برگرداندن تابع ارسال مستقیم فوق‌سریع"""
        client = state["client"]
        if not client:
            raise RuntimeError("کلاینت سروش‌پلاس متصل نیست.")

        send_fn = None
        for m_name in ("send_message", "send_text", "send"):
            if hasattr(client, m_name):
                send_fn = getattr(client, m_name)
                break

        if send_fn is None:
            raise RuntimeError("متد ارسال پیام پیدا نشد.")

        is_coro = inspect.iscoroutinefunction(send_fn)

        def make_caller(fn, *args, **kwargs):
            if is_coro:
                return lambda: fn(*args, **kwargs)
            return lambda: asyncio.to_thread(fn, *args, **kwargs)

        candidates = [cid]
        if cid.lstrip("-").isdigit():
            candidates.append(int(cid))

        last_err = None
        for target in candidates:
            if reply_id:
                for kw in (
                    {"reply_to_message_id": reply_id},
                    {"reply_to": reply_id},
                    {"reply_message_id": reply_id},
                ):
                    try:
                        caller = make_caller(send_fn, target, text, **kw)
                        res = caller()
                        if inspect.isawaitable(res):
                            await res
                        return caller
                    except TypeError:
                        pass
                    except Exception as e:
                        last_err = e

            try:
                caller = make_caller(send_fn, target, text)
                res = caller()
                if inspect.isawaitable(res):
                    await res
                return caller
            except TypeError:
                for kw in (
                    {"chat_id": target, "text": text},
                    {"peer": target, "message": text},
                    {"guid": target, "text": text},
                ):
                    try:
                        caller = make_caller(send_fn, **kw)
                        res = caller()
                        if inspect.isawaitable(res):
                            await res
                        return caller
                    except Exception as e2:
                        last_err = e2
            except Exception as e:
                last_err = e

        raise last_err or RuntimeError("ارسال پیام با خطا مواجه شد.")

    async def spam_worker(cid: str, text: str, delay: float, total: int, reply_id=None, turbo: bool = False):
        state["running"] = True
        state["sent_count"] = 0
        start_ts = time.monotonic()
        last_ui = start_ts

        try:
            # ارسال پیام اول و ساخت تابع مستقیم بدون سربار
            fast_send = await create_fast_sender(cid, text, reply_id=reply_id)
            state["sent_count"] = 1
            set_status("⚡ در حال ارسال پرسرعت... | ارسال‌شده: 1", "#34D399")

            if total == 1 or not state["running"]:
                return

            counter = {"dispatched": 1}
            workers_count = 4 if turbo else 1

            async def worker_loop():
                nonlocal last_ui
                while state["running"]:
                    if total > 0 and counter["dispatched"] >= total:
                        break
                    counter["dispatched"] += 1

                    if delay > 0:
                        await asyncio.sleep(delay)
                    elif not turbo:
                        await asyncio.sleep(0)

                    if not state["running"]:
                        break

                    res = fast_send()
                    if inspect.isawaitable(res):
                        await res

                    state["sent_count"] += 1
                    now = time.monotonic()
                    if now - last_ui >= 0.15:
                        last_ui = now
                        elapsed = max(0.01, now - start_ts)
                        rate = state["sent_count"] / elapsed
                        set_status(
                            f"⚡ در حال ارسال... | ارسال‌شده: {state['sent_count']} ({rate:.1f} پیام/ثانیه)",
                            "#34D399",
                        )

            await asyncio.gather(*(worker_loop() for _ in range(workers_count)))

        except Exception as e:
            set_status(f"❌ خطا در ارسال: {e}", "#F87171")
            notify(f"توقف به دلیل خطا: {e}", is_error=True)
        finally:
            state["running"] = False
            elapsed = max(0.01, time.monotonic() - start_ts)
            rate = state["sent_count"] / elapsed
            if not status_badge.value.startswith("❌"):
                set_status(
                    f"✅ پایان یافت | مجموع: {state['sent_count']} پیام در {elapsed:.2f} ثانیه ({rate:.1f}/ثانیه)",
                    "#FBBF24",
                )

    async def start_spam_click(_):
        if state["running"]:
            notify("ارسال هم‌اکنون در حال اجراست.", is_error=True)
            return

        cid = get_active_chat_id()
        text = (msg_text_input.value or "").strip()
        if not cid or not text:
            notify("لطفاً آیدی/چت مقصد و متن پیام را وارد کنید.", is_error=True)
            set_status("⚠️ آیدی چت مقصد یا متن پیام خالی است.", "#FBBF24")
            return

        try:
            delay = max(0.0, float((interval_input.value or "0").replace(",", ".")))
        except ValueError:
            notify("مقدار فاصله زمانی نامعتبر است.", is_error=True)
            return

        try:
            total = int(count_input.value or "0")
        except ValueError:
            notify("مقدار تعداد پیام باید عدد صحیح باشد.", is_error=True)
            return

        cfg["last_chat_id"] = cid
        save_config(cfg)
        set_status("⚡ در حال شروع ارسال...", "#38BDF8")
        page.run_task(spam_worker, cid, text, delay, total, state["reply_to_id"], bool(turbo_switch.value))

    def stop_spam_click(_):
        state["running"] = False
        set_status(f"⏹ متوقف شد | ارسال‌شده: {state['sent_count']}", "#FBBF24")

    def register_in_chat_commands(client):
        if not client or not hasattr(client, "on_message"):
            return

        try:
            @client.on_message()
            async def _on_msg(_, message):
                if not chat_cmd_switch.value:
                    return
                is_out = bool(pick(message, "outgoing", "is_out", "from_me", default=False))
                if not is_out:
                    return
                txt = str(pick(message, "text", "message", default="")).strip()
                chat_obj = pick(message, "chat", default=message)
                cid = str(pick(chat_obj, "id", "chat_id", "guid", default=""))
                if txt.lower() == ".stop":
                    state["running"] = False
                elif txt.lower().startswith(".spam "):
                    parts = txt.split(maxsplit=2)
                    if len(parts) == 3 and parts[1].isdigit() and not state["running"]:
                        cnt = int(parts[1])
                        body = parts[2]
                        rep = pick(message, "reply_to_message_id", "reply_to")
                        delay = max(0.0, float((interval_input.value or "0").replace(",", ".")))
                        page.run_task(spam_worker, cid, body, delay, cnt, rep, bool(turbo_switch.value))
        except Exception:
            pass

    main_view = ft.Container(
        visible=False,
        padding=16,
        border_radius=16,
        bgcolor="#131824",
        border=ft.Border.all(1, "#1E293B"),
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(APP_TITLE, size=18, weight=ft.FontWeight.BOLD, color="#38BDF8"),
                        days_badge,
                    ],
                ),
                ft.Divider(color="#1E293B"),
                ft.Row(
                    controls=[
                        chat_dropdown,
                        ft.IconButton(
                            icon=ft.Icons.REFRESH,
                            tooltip="بروزرسانی چت‌ها",
                            on_click=fetch_chats,
                        ),
                    ]
                ),
                target_chat_input,
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Button(
                            "دریافت پیام‌های گروه برای ریپلای",
                            icon=ft.Icons.FORUM,
                            on_click=fetch_chat_messages,
                        ),
                        clear_reply_btn,
                    ],
                ),
                reply_banner_text,
                ft.Container(
                    padding=8,
                    border_radius=10,
                    bgcolor="#0F172A",
                    content=messages_column,
                ),
                msg_text_input,
                ft.Row(controls=[interval_input, count_input]),
                turbo_switch,
                chat_cmd_switch,
                ft.Row(
                    controls=[
                        ft.Button(
                            "شروع ارسال",
                            icon=ft.Icons.PLAY_ARROW,
                            bgcolor="#059669",
                            color=ft.Colors.WHITE,
                            expand=True,
                            height=46,
                            on_click=start_spam_click,
                        ),
                        ft.Button(
                            "توقف فوری",
                            icon=ft.Icons.STOP,
                            bgcolor="#DC2626",
                            color=ft.Colors.WHITE,
                            expand=True,
                            height=46,
                            on_click=stop_spam_click,
                        ),
                    ]
                ),
                ft.Container(
                    padding=10,
                    border_radius=8,
                    bgcolor="#0B0E14",
                    width=420,
                    content=status_badge,
                ),
            ],
        ),
    )

    page.add(license_view, login_view, main_view)

    # ==========================================================
    # منطق اتصال سلف‌بات و اعتبارسنجی لایسنس
    # ==========================================================
    async def init_soroush_session(auto: bool = False):
        if Client is None:
            login_status_text.value = SPLUSTHON_ERR
            login_status_text.color = "#F87171"
            login_status_text.update()
            return

        try:
            client = build_splusthon_client()
            state["client"] = client
            if auto and session_exists():
                if hasattr(client, "connect"):
                    await run_smart(client.connect, timeout=12)
                elif hasattr(client, "start"):
                    await run_smart(client.start, timeout=12)

                if hasattr(client, "get_me"):
                    me = await run_smart(client.get_me, timeout=10)
                    state["my_id"] = pick(me, "id", "user_id", "guid")
                register_in_chat_commands(client)
                login_view.visible = False
                main_view.visible = True
                page.update()
                page.run_task(fetch_chats)
        except Exception as e:
            login_status_text.value = f"شماره خود را وارد کنید ({e})"
            login_status_text.color = "#94A3B8"
            login_status_text.update()

    # بررسی خودکار لایسنس ذخیره‌شده هنگام باز شدن برنامه
    if cfg.get("license_key"):
        await handle_activate_license()


if __name__ == "__main__":
    try:
        ft.run(main)
    except AttributeError:
        ft.app(target=main)
