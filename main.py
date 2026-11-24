import asyncio, datetime, hashlib, importlib, inspect, json, os, pkgutil, platform, re, subprocess, tempfile, time, urllib.request
import flet as ft
import httpx

# لایه سازگاری کامل با Flet 1.1.2 و 0.25.2
if hasattr(ft, "border") and hasattr(ft, "Border") and not hasattr(ft.border, "all"):
    ft.border.all = ft.Border.all
    ft.border.only = ft.Border.only
    ft.border.symmetric = ft.Border.symmetric
if hasattr(ft, "padding") and hasattr(ft, "Padding") and not hasattr(ft.padding, "all"):
    ft.padding.all = ft.Padding.all
    ft.padding.only = ft.Padding.only
    ft.padding.symmetric = ft.Padding.symmetric
if hasattr(ft, "margin") and hasattr(ft, "Margin") and not hasattr(ft.margin, "all"):
    ft.margin.all = ft.Margin.all
    ft.margin.only = ft.Margin.only
    ft.margin.symmetric = ft.Margin.symmetric
if hasattr(ft, "border_radius") and hasattr(ft, "BorderRadius") and not hasattr(ft.border_radius, "all"):
    ft.border_radius.all = ft.BorderRadius.all
    ft.border_radius.only = ft.BorderRadius.only

APP_VERSION = "2.2.3"
WEBSITE_URL = "https://v3xsys.pages.dev/"
DEFAULT_UPDATE_URL = "https://v3xsys.pages.dev/"
LICENSE_URL = "https://selfbot-license.krymyhady314.workers.dev"
CREATOR_ID = "@V3XSYS"

# پالت رنگی مشکی کهکشانی و قرمز نئونی
BG_GALAXY = "#030306"
BG_CARD = "#0A0A12"
BG_INPUT = "#12121D"
RED_PRIMARY = "#DC2626"
RED_DARK = "#991B1B"
RED_NEON = "#FF1E42"
RED_LIGHT = "#EF4444"
BORDER_CRIMSON = "#450A0A"
BORDER_ACTIVE = "#EF4444"
TEXT_WHITE = "#FFFFFF"
TEXT_MUTED = "#CBD5E1"

TEHRAN_TZ = datetime.timezone(datetime.timedelta(hours=3, minutes=30))

STORAGE_DIR = os.getenv("FLET_APP_STORAGE_DATA") or tempfile.gettempdir()
os.makedirs(STORAGE_DIR, exist_ok=True)

DEV_FILE = os.path.join(STORAGE_DIR, "v3x_dev.txt")
LIC_FILE = os.path.join(STORAGE_DIR, "v3x_lic.json")
SESSION_PATH = os.path.join(STORAGE_DIR, "v3x_splus")
SAVED_MSGS_FILE = os.path.join(STORAGE_DIR, "v3x_saved_msgs.json")
CLOCK_CFG_FILE = os.path.join(STORAGE_DIR, "v3x_clock_cfg.json")
AUTOREPLY_CFG_FILE = os.path.join(STORAGE_DIR, "v3x_autoreply_cfg.json")
FORWARD_CFG_FILE = os.path.join(STORAGE_DIR, "v3x_forward_cfg.json")


def parse_version_tuple(v: str) -> tuple[int, ...]:
    nums = re.findall(r"\d+", str(v or "0"))
    return tuple(int(x) for x in nums) if nums else (0,)


def get_device_id() -> str:
    parts = [platform.system(), platform.machine(), platform.node()]
    for prop in ("ro.product.brand", "ro.product.model", "ro.product.device", "ro.build.id", "ro.hardware"):
        try:
            out = subprocess.check_output(["getprop", prop], stderr=subprocess.DEVNULL, timeout=1).decode().strip()
            if out:
                parts.append(out)
        except Exception:
            pass
    raw = "|".join(parts)
    did = "V3X-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16].upper()
    try:
        open(DEV_FILE, "w", encoding="utf-8").write(did)
    except Exception:
        pass
    return did


def get_saved_license() -> str:
    try:
        if os.path.exists(LIC_FILE):
            return str(json.load(open(LIC_FILE, "r", encoding="utf-8")).get("key", "")).strip()
    except Exception:
        pass
    return ""


def save_license(key: str):
    try:
        json.dump({"key": key}, open(LIC_FILE, "w", encoding="utf-8"))
    except Exception:
        pass


def clear_saved_license():
    try:
        if os.path.exists(LIC_FILE):
            os.remove(LIC_FILE)
    except Exception:
        pass


def load_saved_multi_messages() -> list[str]:
    try:
        if os.path.exists(SAVED_MSGS_FILE):
            data = json.load(open(SAVED_MSGS_FILE, "r", encoding="utf-8"))
            if isinstance(data, list) and data:
                return [str(x) for x in data if str(x).strip()]
    except Exception:
        pass
    return ["سلام!", "چطوری؟", "پیام تست سلف‌بات V3X"]


def save_multi_messages_disk(msgs: list[str]):
    try:
        json.dump([str(x) for x in msgs if str(x).strip()], open(SAVED_MSGS_FILE, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass


def load_clock_config() -> dict:
    default_cfg = {
        "enabled": False,
        "base_first": "",
        "base_last": "",
        "style": "bold",
        "target_field": "first",
        "sep": "|",
        "bg_keep_alive": True,
    }
    try:
        if os.path.exists(CLOCK_CFG_FILE):
            data = json.load(open(CLOCK_CFG_FILE, "r", encoding="utf-8"))
            if isinstance(data, dict):
                default_cfg.update(data)
    except Exception:
        pass
    return default_cfg


def save_clock_config(cfg: dict):
    try:
        json.dump(cfg, open(CLOCK_CFG_FILE, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass


def load_autoreply_config() -> dict:
    default_cfg = {
        "enabled": False,
        "text": "سلام، در حال حاضر آفلاین هستم. به محض آنلاین شدن پاسخ می‌دهم.",
        "replied_users": [],
    }
    try:
        if os.path.exists(AUTOREPLY_CFG_FILE):
            data = json.load(open(AUTOREPLY_CFG_FILE, "r", encoding="utf-8"))
            if isinstance(data, dict):
                default_cfg.update(data)
    except Exception:
        pass
    return default_cfg


def save_autoreply_config(cfg: dict):
    try:
        json.dump(cfg, open(AUTOREPLY_CFG_FILE, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass


def load_forward_config() -> dict:
    default_cfg = {"interval_min": 5}
    try:
        if os.path.exists(FORWARD_CFG_FILE):
            data = json.load(open(FORWARD_CFG_FILE, "r", encoding="utf-8"))
            if isinstance(data, dict):
                default_cfg.update(data)
    except Exception:
        pass
    return default_cfg


def save_forward_config(cfg: dict):
    try:
        json.dump(cfg, open(FORWARD_CFG_FILE, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass


def notify_native_android_service(cmd: str):
    """ارسال فرمان به سرویس بومی اندروید (start / stop / battery) بدون مسدود کردن UI."""
    def _ping():
        try:
            urllib.request.urlopen(f"http://127.0.0.1:48391/{cmd}", timeout=0.6).read()
        except Exception:
            pass
    try:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, _ping)
    except Exception:
        _ping()


def format_tehran_clock(style: str = "bold") -> str:
    now = datetime.datetime.now(TEHRAN_TZ)
    raw = now.strftime("%H:%M")
    if style == "bold":
        return raw.translate(str.maketrans("0123456789", "𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"))
    if style == "mono":
        return raw.translate(str.maketrans("0123456789", "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"))
    if style == "circle":
        return raw.translate(str.maketrans("0123456789", "⓪①②③④⑤⑥⑦⑧⑨"))
    return raw


def strip_clock_suffix(name: str) -> str:
    txt = (name or "").strip()
    txt = re.sub(r"\s*[\|•\-–—]?\s*[0-9𝟎-𝟗𝟶-𝟿⓪①-⑨]{2}:[0-9𝟎-𝟗𝟶-𝟿⓪①-⑨]{2}\s*$", "", txt)
    return txt.strip()


def extract_clean_key(raw_input: str) -> str:
    txt = str(raw_input or "")
    txt = txt.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩–—−", "01234567890123456789---"))
    txt = re.sub(r"[\u200b-\u200f\ufeff`\"'\s]", "", txt)
    m = re.search(r"(V3X-[A-Za-z0-9\-_]{3,})", txt, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return txt.upper()


async def check_license(raw_key: str, did: str) -> tuple[str, str, str, str]:
    clean_key = extract_clean_key(raw_key)
    if not clean_key:
        return "ERROR", "لطفاً کلید لایسنس را وارد کنید.", "", DEFAULT_UPDATE_URL

    payload = {
        "action": "verify",
        "source": "app",
        "key": clean_key,
        "license": clean_key,
        "license_key": clean_key,
        "code": clean_key,
        "hwid": did,
        "device_id": did,
        "device": did,
        "app_version": APP_VERSION,
        "version": APP_VERSION,
    }
    base = LICENSE_URL.rstrip("/")
    routes = [
        ("POST_JSON", f"{base}/api/verify"),
        ("POST_JSON", f"{base}/verify"),
        ("GET", f"{base}/verify"),
        ("POST_JSON", f"{base}/check"),
        ("GET", f"{base}/check"),
        ("POST_JSON", f"{base}/validate"),
        ("GET", f"{base}/validate"),
        ("POST_JSON", f"{base}/activate"),
        ("GET", base),
        ("POST_JSON", base),
    ]

    saw_only_online = False
    last_err = "عدم اتصال به سرور لایسنس؛ اینترنت یا فیلترشکن خود را بررسی کنید."

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http:
        for mode, url in routes:
            try:
                r = await http.post(url, params=payload, json=payload) if mode == "POST_JSON" else await http.get(url, params=payload)
                if r.status_code in (404, 405):
                    continue

                try:
                    d = r.json()
                except Exception:
                    txt = r.text.strip()
                    low = txt.lower()
                    if any(w in low for w in ("valid", "active", "success", "authorized")) and "invalid" not in low:
                        return "OK", "لایسنس تایید شد ✅", clean_key, DEFAULT_UPDATE_URL
                    if txt:
                        last_err = f"پاسخ سرور ({r.status_code}): {txt[:90]}"
                    continue

                if not isinstance(d, dict):
                    continue

                upd_url = str(d.get("update_url") or d.get("download_url") or DEFAULT_UPDATE_URL)
                status_val = str(d.get("status", "")).lower().strip()
                min_ver = str(d.get("min_version") or d.get("required_version") or "").strip()

                if (
                    d.get("force_update") is True
                    or d.get("outdated") is True
                    or status_val in ("outdated", "update_required", "deprecated", "disabled")
                    or (min_ver and parse_version_tuple(APP_VERSION) < parse_version_tuple(min_ver))
                ):
                    msg = d.get("message") or f"نسخه فعلی ({APP_VERSION}) غیرفعال شده است. برای دانلود نسخه جدید ({min_ver or 'جدید'}) وارد سایت زیر شوید:"
                    return "OUTDATED", str(msg), clean_key, upd_url

                is_ok = (
                    d.get("valid") is True
                    or d.get("ok") is True
                    or d.get("success") is True
                    or d.get("authorized") is True
                    or status_val in ("valid", "ok", "active", "success", "activated", "true")
                )
                if is_ok:
                    msg = d.get("message") or d.get("msg") or "لایسنس تایید شد ✅"
                    return "OK", str(msg), clean_key, upd_url

                if status_val == "online" and len(d) <= 2 and not any(
                    k in d for k in ("valid", "ok", "error", "reason", "message")
                ):
                    saw_only_online = True
                    continue

                msg = d.get("message") or d.get("error") or d.get("reason") or d.get("detail") or d.get("msg")
                if msg:
                    return "ERROR", str(msg), clean_key, upd_url

                last_err = f"لایسنس نامعتبر است ({json.dumps(d, ensure_ascii=False)})"
            except (httpx.ConnectError, httpx.TimeoutException):
                last_err = "خطا در ارتباط با سرور؛ در صورت فعال بودن محدودیت اینترنت، فیلترشکن را روشن کنید."
            except Exception as e:
                last_err = f"خطای اتصال به سرور لایسنس: {e}"

    if saw_only_online:
        return "ERROR", "سرور آنلاین است اما مسیر بررسی لایسنس (/verify) در Worker تنظیم نشده است.", clean_key, DEFAULT_UPDATE_URL

    return "ERROR", last_err, clean_key, DEFAULT_UPDATE_URL


def create_splus_client():
    import splusthon
    cls = None
    for name in ("SPlusClient", "Client", "SoroushClient", "UserClient"):
        c = getattr(splusthon, name, None)
        if inspect.isclass(c):
            cls = c
            break
    if cls is None and hasattr(splusthon, "__path__"):
        for _, mod_name, _ in pkgutil.walk_packages(splusthon.__path__, "splusthon."):
            try:
                m = importlib.import_module(mod_name)
                for n, obj in inspect.getmembers(m, inspect.isclass):
                    if obj.__module__ == mod_name and "client" in n.lower() and "base" not in n.lower():
                        cls = obj
                        break
                if cls:
                    break
            except Exception:
                pass
    if cls is None:
        raise RuntimeError("کلاس کلاینت در splusthon یافت نشد")

    try:
        return cls(SESSION_PATH, connection_retries=-1, retry_delay=1, auto_reconnect=True)
    except TypeError:
        try:
            return cls(SESSION_PATH)
        except TypeError:
            return cls()


async def apply_profile_name(c, first_name: str, last_name: str) -> bool:
    fn_direct = getattr(c, "update_profile", None)
    if callable(fn_direct):
        res = fn_direct(first_name=first_name, last_name=last_name)
        if inspect.isawaitable(res):
            await res
        return True

    for mod_path in ("splusthon.tl.functions.account", "splusthon.functions.account"):
        try:
            mod = importlib.import_module(mod_path)
            req_cls = getattr(mod, "UpdateProfileRequest", None)
            if req_cls is not None:
                await c(req_cls(first_name=first_name, last_name=last_name))
                return True
        except Exception:
            continue

    raise RuntimeError("متد تغییر نام پروفایل در این نسخه کتابخانه یافت نشد.")


def make_btn(label: str, on_click, bgcolor: str = RED_PRIMARY, color: str = TEXT_WHITE, height: int = 42, kind: str = "filled", expand: bool = False):
    lbl = ft.Text(label, color=color, weight=ft.FontWeight.W_600, size=12)
    if kind == "outlined":
        btn_cls = getattr(ft, "OutlinedButton", ft.Button)
        return btn_cls(content=lbl, on_click=on_click, height=height, expand=expand), lbl
    if kind == "text":
        btn_cls = getattr(ft, "TextButton", ft.Button)
        return btn_cls(content=lbl, on_click=on_click, expand=expand), lbl
    btn_cls = getattr(ft, "Button", None) or getattr(ft, "ElevatedButton", None)
    return btn_cls(content=lbl, bgcolor=bgcolor, color=color, height=height, on_click=on_click, expand=expand), lbl


def make_toggle_card(title: str, subtitle: str, initial_val: bool, on_toggle_callback):
    state_ref = {"val": bool(initial_val)}

    badge_txt = ft.Text(
        "✅ روشن" if state_ref["val"] else "⭕ خاموش",
        size=12,
        weight=ft.FontWeight.BOLD,
        color="#10B981" if state_ref["val"] else RED_NEON,
    )
    badge_box = ft.Container(
        padding=ft.Padding.symmetric(horizontal=12, vertical=7),
        border_radius=ft.BorderRadius.all(10),
        bgcolor="#06281E" if state_ref["val"] else "#26080E",
        border=ft.Border.all(1.5, "#10B981" if state_ref["val"] else RED_NEON),
        content=badge_txt,
    )
    card_container = ft.Container(
        padding=ft.Padding.all(12),
        border_radius=ft.BorderRadius.all(12),
        bgcolor="#0C1F1A" if state_ref["val"] else "#180A10",
        border=ft.Border.all(1.5, "#10B981" if state_ref["val"] else BORDER_ACTIVE),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
            controls=[
                ft.Column(
                    spacing=3,
                    expand=True,
                    controls=[
                        ft.Text(title, size=13, weight=ft.FontWeight.BOLD, color=TEXT_WHITE),
                        ft.Text(subtitle, size=11, color=TEXT_MUTED),
                    ],
                ),
                badge_box,
            ],
        ),
    )

    def sync_visual(val: bool):
        state_ref["val"] = bool(val)
        badge_txt.value = "✅ روشن" if state_ref["val"] else "⭕ خاموش"
        badge_txt.color = "#10B981" if state_ref["val"] else RED_NEON
        badge_box.bgcolor = "#06281E" if state_ref["val"] else "#26080E"
        badge_box.border = ft.Border.all(1.5, "#10B981" if state_ref["val"] else RED_NEON)
        card_container.bgcolor = "#0C1F1A" if state_ref["val"] else "#180A10"
        card_container.border = ft.Border.all(1.5, "#10B981" if state_ref["val"] else BORDER_ACTIVE)

    def handle_click(e):
        new_val = not state_ref["val"]
        sync_visual(new_val)
        if callable(on_toggle_callback):
            on_toggle_callback(new_val)

    card_container.on_click = handle_click
    return card_container, state_ref, sync_visual


def creator_footer():
    return ft.Container(
        margin=ft.Margin.only(top=6),
        padding=ft.Padding.symmetric(vertical=8, horizontal=12),
        border_radius=ft.BorderRadius.all(10),
        bgcolor=BG_CARD,
        border=ft.Border.all(1, BORDER_CRIMSON),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Text(f"نسخه {APP_VERSION}  |  طراحی و توسعه: ", size=11, color=TEXT_MUTED),
                ft.Text(CREATOR_ID, size=12, weight=ft.FontWeight.BOLD, color=RED_NEON, selectable=True),
            ],
        ),
    )


def parse_target(raw: str):
    val = (raw or "").strip()
    if val.lstrip("-").isdigit():
        return int(val)
    return val


async def main(page: ft.Page):
    page.title = "V3X Selfbot"
    page.bgcolor = BG_GALAXY
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = ft.Padding.only(top=32, left=10, right=10, bottom=10)
    page.scroll = ft.ScrollMode.AUTO
    page.rtl = True

    did = get_device_id()
    clock_cfg = load_clock_config()
    autoreply_cfg = load_autoreply_config()
    forward_cfg = load_forward_config()

    notify_native_android_service("start" if clock_cfg.get("bg_keep_alive", True) else "stop")

    st = {
        "client": None,
        "me_id": None,
        "phone": "",
        "hash": None,
        "need_2fa": False,
        "bg_workers_started": False,
        "event_hook_attached": False,
        "last_clock_min": "",
        "in_dashboard": False,
        "active_tab": "chats",  # chats | multi | turbo | forward | autoreply | clock
        "chat_filter": "all",
        "dialogs": [],
        "selected_targets": {},
        "active_target": "",
        "active_target_title": "",
        "recent_messages": [],
        "reply_to_id": None,
        "reply_to_preview": "",
        "reply_chat_id": "",
        "multi_messages": load_saved_multi_messages(),
        "multi_running": False,
        "turbo_running": False,
        "entity_cache": {},
        # وضعیت‌های بخش فوروارد
        "fwd_source_chat": "",
        "fwd_source_title": "",
        "fwd_messages": [],
        "fwd_selected_msg_id": None,
        "fwd_selected_msg_preview": "",
        "fwd_running": False,
        "fwd_status": "آماده شروع فوروارد هوشمند به کاربران ۲۰۰ پیام اخیر گپ‌ها",
    }
    logs = ft.Column(spacing=2, height=85, scroll=ft.ScrollMode.AUTO)
    conn_badge = ft.Text("🟢 متصل", size=12, color="#10B981", weight=ft.FontWeight.W_600)

    def safe_page_update():
        try:
            page.update()
        except Exception:
            pass

    def log(txt: str, col: str = TEXT_MUTED):
        logs.controls.insert(0, ft.Text(f"[{time.strftime('%H:%M:%S')}] {txt}", size=11, color=col))
        if len(logs.controls) > 12:
            del logs.controls[12:]
        try:
            if logs.page is not None:
                logs.update()
                return
        except Exception:
            pass
        safe_page_update()

    def get_client():
        if st["client"] is None:
            st["client"] = create_splus_client()
        return st["client"]

    async def get_my_user_id(c) -> str:
        if st["me_id"]:
            return st["me_id"]
        try:
            me = await asyncio.wait_for(c.get_me(), timeout=8.0)
            uid = getattr(me, "id",
