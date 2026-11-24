import asyncio, datetime, hashlib, importlib, inspect, json, os, pkgutil, platform, re, subprocess, tempfile, time
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

APP_VERSION = "2.2.1"
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


_WAKE_LOCK_REF = None


def set_android_wakelock(enable: bool):
    """جلوگیری از خواب پردازنده اندروید برای ادامه کار ساعت و پاسخگوی خودکار در پس‌زمینه."""
    global _WAKE_LOCK_REF
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Context = autoclass("android.content.Context")
        PowerManager = autoclass("android.os.PowerManager")
        activity = PythonActivity.mActivity
        if enable:
            if _WAKE_LOCK_REF is None:
                pm = activity.getSystemService(Context.POWER_SERVICE)
                _WAKE_LOCK_REF = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "V3X:KeepAliveLock")
            if not _WAKE_LOCK_REF.isHeld():
                _WAKE_LOCK_REF.acquire()
        else:
            if _WAKE_LOCK_REF is not None and _WAKE_LOCK_REF.isHeld():
                _WAKE_LOCK_REF.release()
    except Exception:
        pass


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


def make_btn(label: str, on_click, bgcolor: str = RED_PRIMARY, color: str = TEXT_WHITE, height: int = 44, kind: str = "filled", expand: bool = False):
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
    """کارت تیک اختصاصی پررنگ و کاملاً خوانا در موبایل (بدون بیرون‌زدگی در حالت RTL)."""
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
        margin=ft.Margin.only(top=8),
        padding=ft.Padding.symmetric(vertical=10, horizontal=14),
        border_radius=ft.BorderRadius.all(12),
        bgcolor=BG_CARD,
        border=ft.Border.all(1, BORDER_CRIMSON),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Text(f"نسخه {APP_VERSION}  |  طراحی و توسعه: ", size=12, color=TEXT_MUTED),
                ft.Text(CREATOR_ID, size=13, weight=ft.FontWeight.BOLD, color=RED_NEON, selectable=True),
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
    page.padding = ft.Padding.only(top=34, left=12, right=12, bottom=12)
    page.scroll = ft.ScrollMode.AUTO
    page.rtl = True

    did = get_device_id()
    clock_cfg = load_clock_config()
    autoreply_cfg = load_autoreply_config()
    forward_cfg = load_forward_config()

    if clock_cfg.get("bg_keep_alive", True):
        set_android_wakelock(True)

    client_lock = asyncio.Lock()

    st = {
        "client": None,
        "me_id": None,
        "phone": "",
        "hash": None,
        "need_2fa": False,
        "watchdog_started": False,
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
        # وضعیت‌های بخش پی‌وی خودکار
        "pv_seen_msg_ids": set(),
        "pv_seeded": False,
    }
    logs = ft.Column(spacing=3, height=95, scroll=ft.ScrollMode.AUTO)
    conn_badge = ft.Text("🟢 متصل", size=12, color="#10B981", weight=ft.FontWeight.W_600)

    def safe_page_update():
        try:
            page.update()
        except Exception:
            pass

    def log(txt: str, col: str = TEXT_MUTED):
        logs.controls.insert(0, ft.Text(f"[{time.strftime('%H:%M:%S')}] {txt}", size=11, color=col))
        if len(logs.controls) > 15:
            del logs.controls[15:]
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
            uid = getattr(me, "id", None) or getattr(me, "user_id", None) or getattr(me, "guid", None)
            if uid is not None:
                st["me_id"] = str(uid)
                return st["me_id"]
        except Exception:
            pass
        return ""

    async def ensure_online(c, force_reset: bool = False) -> bool:
        try:
            if force_reset:
                try:
                    await asyncio.wait_for(c.disconnect(), timeout=3.0)
                except Exception:
                    pass
            if not c.is_connected():
                conn_badge.value = "🟡 اتصال مجدد..."
                conn_badge.color = "#F59E0B"
                safe_page_update()
                await asyncio.wait_for(c.connect(), timeout=10.0)
            if conn_badge.value != "🟢 متصل":
                conn_badge.value = "🟢 متصل"
                conn_badge.color = "#10B981"
                safe_page_update()
            return True
        except Exception:
            if conn_badge.value != "🔴 قطع اتصال":
                conn_badge.value = "🔴 قطع اتصال"
                conn_badge.color = RED_NEON
                safe_page_update()
            return False

    async def resolve_peer(c, raw_target: str):
        key = (raw_target or "").strip()
        if not key:
            return None
        if key in st["entity_cache"]:
            return st["entity_cache"][key]
        parsed = parse_target(key)
        try:
            if callable(getattr(c, "get_input_entity", None)):
                ent = await asyncio.wait_for(c.get_input_entity(parsed), timeout=8.0)
                st["entity_cache"][key] = ent
                return ent
        except Exception:
            pass
        return parsed

    async def send_fast_single(c, peer, raw_target: str, text: str, reply_id=None):
        for attempt in range(1, 4):
            try:
                if reply_id is not None:
                    try:
                        await asyncio.wait_for(c.send_message(peer, text, reply_to=reply_id), timeout=10.0)
                        return
                    except TypeError:
                        await asyncio.wait_for(c.send_message(peer, text), timeout=10.0)
                        return
                    except Exception as rep_ex:
                        if "reply" in str(rep_ex).lower() or "msg_id" in str(rep_ex).lower():
                            await asyncio.wait_for(c.send_message(peer, text), timeout=10.0)
                            return
                        raise rep_ex
                else:
                    await asyncio.wait_for(c.send_message(peer, text), timeout=10.0)
                    return
            except Exception as ex:
                err_low = str(ex).lower()
                wait_sec = getattr(ex, "seconds", None)
                if wait_sec is None:
                    m = re.search(r"wait of (\d+)", err_low)
                    if m:
                        wait_sec = int(m.group(1))
                if wait_sec:
                    sleep_t = min(int(wait_sec) + 1, 20)
                    log(f"محدودیت سرعت سرور؛ مکث {sleep_t} ثانیه...", "#F59E0B")
                    await asyncio.sleep(sleep_t)
                    continue
                if attempt < 3:
                    await ensure_online(c, force_reset=True)
                    st["entity_cache"].pop((raw_target or "").strip(), None)
                    peer = await resolve_peer(c, raw_target)
                    await asyncio.sleep(0.3)
                else:
                    raise ex

    async def forward_fast_single(c, to_peer, raw_to: str, from_peer, msg_id):
        fwd_fn = getattr(c, "forward_messages", None) or getattr(c, "forward", None)
        if not callable(fwd_fn):
            raise RuntimeError("متد forward_messages در splusthon یافت نشد.")

        sig_params = list(inspect.signature(fwd_fn).parameters.keys())
        for attempt in range(1, 3):
            try:
                if "from_peer" in sig_params:
                    coro = fwd_fn(to_peer, msg_id, from_peer=from_peer)
                elif "from_chat_id" in sig_params:
                    coro = fwd_fn(to_peer, from_peer, msg_id)
                else:
                    coro = fwd_fn(to_peer, msg_id, from_peer)
                if inspect.isawaitable(coro):
                    await asyncio.wait_for(coro, timeout=12.0)
                return
            except Exception as ex:
                err_low = str(ex).lower()
                wait_sec = getattr(ex, "seconds", None)
                if wait_sec is None:
                    m = re.search(r"wait of (\d+)", err_low)
                    if m:
                        wait_sec = int(m.group(1))
                if wait_sec:
                    sleep_t = min(int(wait_sec) + 1, 25)
                    log(f"محدودیت سرعت فوروارد؛ مکث {sleep_t} ثانیه...", "#F59E0B")
                    await asyncio.sleep(sleep_t)
                    continue
                if attempt < 2:
                    await ensure_online(c, force_reset=True)
                    st["entity_cache"].pop((raw_to or "").strip(), None)
                    to_peer = await resolve_peer(c, raw_to)
                    await asyncio.sleep(0.3)
                else:
                    raise ex

    def on_lifecycle_change(e):
        try:
            state_str = str(getattr(e, "state", "")).lower()
            if clock_cfg.get("bg_keep_alive", True):
                set_android_wakelock(True)
            if st["client"] is not None and (st["in_dashboard"] or clock_cfg.get("bg_keep_alive", True)):
                asyncio.create_task(ensure_online(st["client"]))
                if "resume" in state_str:
                    safe_page_update()
        except Exception:
            pass

    try:
        page.on_app_lifecycle_state_change = on_lifecycle_change
    except Exception:
        pass

    # ==========================================
    # صفحه توقف نسخه قدیمی و هدایت به سایت
    # ==========================================
    def show_update_required(msg: str, update_url: str):
        st["in_dashboard"] = False
        target_site = update_url or WEBSITE_URL
        page.controls.clear()
        url_box = ft.TextField(
            label="آدرس سایت رسمی جهت دانلود نسخه جدید",
            value=target_site,
            read_only=True,
            text_align=ft.TextAlign.LEFT,
            bgcolor=BG_INPUT,
            border_color=BORDER_ACTIVE,
        )
        copy_stat = ft.Text("", size=12, color="#10B981")

        async def open_dl(e):
            try:
                if hasattr(page, "launch_url"):
                    r = page.launch_url(target_site)
                    if inspect.isawaitable(r):
                        await r
            except Exception:
                pass
            try:
                if hasattr(ft, "Clipboard"):
                    await ft.Clipboard().set(target_site)
                copy_stat.value = "لینک سایت کپی شد؛ در مرورگر باز کنید ✅"
            except Exception:
                copy_stat.value = "لینک بالا را کپی و در مرورگر باز کنید."
            safe_page_update()

        dl_btn, _ = make_btn("🌐 ورود به سایت و دانلود نسخه جدید", open_dl, bgcolor=RED_PRIMARY, height=48)
        page.add(
            ft.Container(
                bgcolor=BG_CARD,
                padding=20,
                border_radius=ft.BorderRadius.all(14),
                border=ft.Border.all(1.5, RED_NEON),
                content=ft.Column(
                    spacing=14,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("⚠️ این نسخه غیرفعال شده است", size=20, weight=ft.FontWeight.BOLD, color=RED_NEON),
                        ft.Text(msg, size=14, color=TEXT_WHITE),
                        url_box,
                        dl_btn,
                        copy_stat,
                    ],
                ),
            ),
            creator_footer(),
        )
        safe_page_update()

    async def proceed_after_license():
        try:
            c = get_client()
            await c.connect()
            if await c.is_user_authorized():
                show_dashboard()
                return
        except Exception:
            pass
        show_phone()

    # ==========================================
    # صفحه ۱: احراز هویت لایسنس
    # ==========================================
    def show_license(msg: str = ""):
        st["in_dashboard"] = False
        page.controls.clear()
        info = ft.Text(msg, size=13, color="#F59E0B", selectable=True)
        dev_box = ft.TextField(
            label="شناسه سخت‌افزاری دستگاه (Device ID)",
            value=did,
            read_only=True,
            text_align=ft.TextAlign.LEFT,
            bgcolor=BG_INPUT,
            border_color=BORDER_CRIMSON,
        )
        key_box = ft.TextField(
            label="کلید لایسنس",
            value=get_saved_license(),
            hint_text="V3X-XXXX-XXXX",
            text_align=ft.TextAlign.LEFT,
            bgcolor=BG_INPUT,
            border_color=BORDER_ACTIVE,
        )

        async def copy_id(e):
            try:
                if hasattr(ft, "Clipboard"):
                    await ft.Clipboard().set(did)
                elif hasattr(page, "set_clipboard"):
                    r = page.set_clipboard(did)
                    if inspect.isawaitable(r):
                        await r
                info.value, info.color = "شناسه دستگاه کپی شد ✅", "#10B981"
            except Exception:
                info.value, info.color = "متن را انتخاب و دستی کپی کنید.", "#F59E0B"
            safe_page_update()

        async def verify(e):
            btn.disabled = True
            info.value, info.color = "در حال استعلام لایسنس و بررسی نسخه...", RED_LIGHT
            safe_page_update()
            status, m, clean_k, upd_url = await check_license(key_box.value or "", did)
            btn.disabled = False
            if status == "OUTDATED":
                show_update_required(m, upd_url)
                return
            if status != "OK":
                info.value, info.color = f"❌ {m}", RED_NEON
                safe_page_update()
                return
            save_license(clean_k)
            await proceed_after_license()

        btn, _ = make_btn("بررسی لایسنس و ورود", verify, bgcolor=RED_PRIMARY, height=48)
        copy_btn, _ = make_btn("📋 کپی شناسه دستگاه", copy_id, color=RED_LIGHT, kind="outlined")

        page.add(
            ft.Container(
                bgcolor=BG_CARD,
                padding=18,
                border_radius=ft.BorderRadius.all(14),
                border=ft.Border.all(1.2, BORDER_ACTIVE),
                content=ft.Column(
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("V3X SELFBOT", size=24, weight=ft.FontWeight.BOLD, color=RED_NEON),
                        ft.Text(f"نسخه {APP_VERSION}  |  فعال‌سازی اشتراک اختصاصی", size=13, color=TEXT_MUTED),
                        dev_box,
                        copy_btn,
                        key_box,
                        btn,
                        info,
                    ],
                ),
            ),
            creator_footer(),
        )
        safe_page_update()

    # ==========================================
    # صفحه ۲: ورود شماره موبایل
    # ==========================================
    def show_phone(msg: str = ""):
        st["in_dashboard"] = False
        page.controls.clear()
        info = ft.Text(msg, size=13, color="#F59E0B", selectable=True)
        ph_box = ft.TextField(
            label="شماره موبایل سروش‌پلاس",
            hint_text="09123456789",
            keyboard_type=ft.KeyboardType.PHONE,
            text_align=ft.TextAlign.LEFT,
            bgcolor=BG_INPUT,
            border_color=BORDER_ACTIVE,
        )

        async def send_otp(e):
            d = "".join(c for c in (ph_box.value or "") if c.isdigit())
            if d.startswith("09") and len(d) == 11:
                p98, p09 = "98" + d[1:], d
            elif d.startswith("989") and len(d) == 12:
                p98, p09 = d, "0" + d[2:]
            elif d.startswith("9") and len(d) == 10:
                p98, p09 = "98" + d, "0" + d
            else:
                info.value, info.color = "شماره موبایل معتبر وارد کنید (مثلاً 09123456789).", RED_NEON
                safe_page_update()
                return

            btn.disabled = True
            info.value, info.color = "در حال ارسال کد تایید...", RED_LIGHT
            safe_page_update()
            try:
                c = get_client()
                if not c.is_connected():
                    await c.connect()

                res = None
                used_phone = p98
                last_err = None
                for fmt in (p98, f"+{p98}", p09):
                    try:
                        res = await c.send_code_request(fmt)
                        used_phone = fmt
                        last_err = None
                        break
                    except Exception as ex:
                        last_err = ex
                if last_err is not None:
                    raise last_err

                st["phone"] = used_phone
                st["hash"] = getattr(res, "phone_code_hash", None)
                st["need_2fa"] = False
                btn.disabled = False
                show_otp()
            except Exception as ex:
                btn.disabled = False
                info.value, info.color = f"خطا: {ex}", RED_NEON
                safe_page_update()

        btn, _ = make_btn("ارسال کد تایید", send_otp, bgcolor=RED_PRIMARY, height=48)
        page.add(
            ft.Container(
                bgcolor=BG_CARD,
                padding=18,
                border_radius=ft.BorderRadius.all(14),
                border=ft.Border.all(1.2, BORDER_ACTIVE),
                content=ft.Column(
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("ورود به سروش‌پلاس", size=20, weight=ft.FontWeight.BOLD, color=RED_NEON),
                        ph_box,
                        btn,
                        info,
                    ],
                ),
            ),
            creator_footer(),
        )
        safe_page_update()

    # ==========================================
    # صفحه ۳: کد تایید
    # ==========================================
    def show_otp():
        st["in_dashboard"] = False
        page.controls.clear()
        info = ft.Text(f"کد تایید به {st['phone']} ارسال شد.", size=13, color=RED_LIGHT)
        code_box = ft.TextField(
            label="کد تایید",
            hint_text="12345",
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.LEFT,
            bgcolor=BG_INPUT,
            border_color=BORDER_ACTIVE,
        )
        pwd_box = ft.TextField(
            label="رمز تایید دومرحله‌ای (در صورت داشتن)",
            password=True,
            can_reveal_password=True,
            visible=st["need_2fa"],
            text_align=ft.TextAlign.LEFT,
            bgcolor=BG_INPUT,
            border_color=BORDER_ACTIVE,
        )

        async def confirm(e):
            code = (code_box.value or "").strip()
            pwd = (pwd_box.value or "").strip()
            if not st["need_2fa"] and len(code) < 4:
                info.value, info.color = "کد تایید را کامل وارد کنید.", RED_NEON
                safe_page_update()
                return
            btn.disabled = True
            info.value, info.color = "در حال ورود...", RED_LIGHT
            safe_page_update()
            try:
                c = get_client()
                if st["need_2fa"]:
                    await c.sign_in(password=pwd)
                else:
                    try:
                        if st["hash"]:
                            await c.sign_in(phone=st["phone"], code=code, phone_code_hash=st["hash"])
                        else:
                            await c.sign_in(st["phone"], code)
                    except TypeError:
                        await c.sign_in(st["phone"], code)
                btn.disabled = False
                show_dashboard()
            except Exception as ex:
                btn.disabled = False
                err_str = str(ex)
                if "password" in err_str.lower() or "2fa" in err_str.lower():
                    st["need_2fa"] = True
                    pwd_box.visible = True
                    info.value, info.color = "اکانت شما رمز دومرحله‌ای دارد؛ رمز را وارد و دوباره تایید کنید.", "#F59E0B"
                else:
                    info.value, info.color = f"خطا: {ex}", RED_NEON
                safe_page_update()

        btn, _ = make_btn("تایید و ورود", confirm, bgcolor=RED_PRIMARY, height=48)
        chg_btn, _ = make_btn("تغییر شماره", lambda e: show_phone(), color=TEXT_MUTED, kind="text")
        page.add(
            ft.Container(
                bgcolor=BG_CARD,
                padding=18,
                border_radius=ft.BorderRadius.all(14),
                border=ft.Border.all(1.2, BORDER_ACTIVE),
                content=ft.Column(
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("تایید کد", size=20, weight=ft.FontWeight.BOLD, color=RED_NEON),
                        code_box,
                        pwd_box,
                        btn,
                        chg_btn,
                        info,
                    ],
                ),
            ),
            creator_footer(),
        )
        safe_page_update()

    # ==========================================
    # صفحه ۴: داشبورد کامل سلف‌بات (بهینه‌سازی‌شده بدون لگ)
    # ==========================================
    def show_dashboard():
        st["in_dashboard"] = True
        page.controls.clear()
        c = get_client()
        log("سلف‌بات با موفقیت به سروش‌پلاس متصل شد ✅", "#10B981")

        if clock_cfg.get("bg_keep_alive", True):
            set_android_wakelock(True)

        # اتصال به رویداد آنی پیام جدید در پی‌وی (بدون مصرف پردازنده)
        if not st["event_hook_attached"] and callable(getattr(c, "add_event_handler", None)):
            try:
                ev_mod = importlib.import_module("splusthon.events")
                NewMessage = getattr(ev_mod, "NewMessage", None)
                if NewMessage is not None:
                    async def _on_incoming_pv(event):
                        try:
                            if not autoreply_cfg.get("enabled"):
                                return
                            if not getattr(event, "is_private", False) or getattr(event, "out", False):
                                return
                            reply_msg = str(autoreply_cfg.get("text") or "").strip()
                            if not reply_msg:
                                return
                            sender = await event.get_sender()
                            if sender is not None and bool(getattr(sender, "bot", False) or getattr(sender, "is_bot", False)):
                                return
                            cid = getattr(event, "chat_id", None) or getattr(event, "sender_id", None)
                            if cid is None:
                                return
                            cid_str = str(cid)
                            my_id = await get_my_user_id(c)
                            if cid_str == my_id:
                                return
                            replied_set = set(str(x) for x in autoreply_cfg.get("replied_users", []))
                            if cid_str in replied_set:
                                return
                            peer = await resolve_peer(c, cid_str)
                            await send_fast_single(c, peer, cid_str, reply_msg)
                            replied_set.add(cid_str)
                            autoreply_cfg["replied_users"] = list(replied_set)
                            save_autoreply_config(autoreply_cfg)
                            title = getattr(sender, "first_name", None) or cid_str
                            log(f"🤖 پاسخ خودکار آفلاین به «{title}» ارسال شد ✅", "#10B981")
                        except Exception:
                            pass

                    c.add_event_handler(_on_incoming_pv, NewMessage(incoming=True))
                    st["event_hook_attached"] = True
            except Exception:
                pass

        async def sync_profile_clock(force: bool = False):
            if not clock_cfg.get("enabled"):
                return
            now_min = datetime.datetime.now(TEHRAN_TZ).strftime("%H:%M")
            if not force and st["last_clock_min"] == now_min:
                return
            try:
                await ensure_online(c)
                if not clock_cfg.get("base_first"):
                    me = await asyncio.wait_for(c.get_me(), timeout=8.0)
                    clock_cfg["base_first"] = strip_clock_suffix(getattr(me, "first_name", "") or "")
                    clock_cfg["base_last"] = strip_clock_suffix(getattr(me, "last_name", "") or "")
                    save_clock_config(clock_cfg)

                clk_str = format_tehran_clock(clock_cfg.get("style", "bold"))
                sep = clock_cfg.get("sep", "|")
                b_first = clock_cfg.get("base_first", "")
                b_last = clock_cfg.get("base_last", "")

                if clock_cfg.get("target_field") == "last":
                    new_first = b_first
                    new_last = f"{b_last} {sep} {clk_str}".strip() if b_last else clk_str
                else:
                    new_first = f"{b_first} {sep} {clk_str}".strip() if b_first else clk_str
                    new_last = b_last

                await apply_profile_name(c, new_first, new_last)
                st["last_clock_min"] = now_min
                log(f"ساعت پروفایل آپدیت شد: {new_first} {new_last}".strip(), RED_LIGHT)
            except Exception as ex:
                log(f"خطا در آپدیت ساعت پروفایل: {ex}", RED_NEON)

        async def check_pv_auto_reply_light():
            """بررسی فوق‌سبک فقط برای چت‌های دارای پیام خوانده‌نشده (بدون لگ)."""
            if not autoreply_cfg.get("enabled"):
                return
            reply_msg = str(autoreply_cfg.get("text") or "").strip()
            if not reply_msg:
                return

            try:
                await ensure_online(c)
                my_id = await get_my_user_id(c)
                raw_dialogs = []
                if callable(getattr(c, "get_dialogs", None)):
                    raw_dialogs = await asyncio.wait_for(c.get_dialogs(limit=15), timeout=8.0)

                replied_set = set(str(x) for x in autoreply_cfg.get("replied_users", []))

                for d in raw_dialogs:
                    unread = getattr(d, "unread_count", 0) or 0
                    if unread <= 0:
                        continue
                    ent = getattr(d, "entity", None)
                    cid = getattr(d, "id", None)
                    if cid is None and ent is not None:
                        cid = getattr(ent, "id", None) or getattr(ent, "guid", None)
                    if cid is None:
                        continue
                    cid_str = str(cid)
                    if cid_str == my_id or cid_str in replied_set:
                        continue

                    is_user = getattr(d, "is_user", None)
                    is_group = getattr(d, "is_group", None) or getattr(d, "is_channel", None)
                    is_pv = (is_user is True or cid_str.startswith("u0") or (isinstance(cid, int) and cid > 0 and not is_group))
                    if not is_pv:
                        continue
                    if ent is not None and bool(getattr(ent, "bot", False) or getattr(ent, "is_bot", False)):
                        continue

                    peer = await resolve_peer(c, cid_str)
                    await send_fast_single(c, peer, cid_str, reply_msg)
                    replied_set.add(cid_str)
                    autoreply_cfg["replied_users"] = list(replied_set)
                    save_autoreply_config(autoreply_cfg)
                    title = getattr(d, "name", None) or getattr(d, "title", None) or cid_str
                    log(f"🤖 پاسخ خودکار آفلاین به «{title}» ارسال شد ✅", "#10B981")
            except Exception:
                pass

        async def connection_and_bg_watchdog():
            """ناظر سبک پس‌زمینه: فقط در صورت آزاد بودن شبکه اجرا می‌شود تا لمس‌ها روان بمانند."""
            while st["in_dashboard"] or clock_cfg.get("bg_keep_alive", True):
                if st["client"] is None:
                    break
                if not client_lock.locked():
                    async with client_lock:
                        try:
                            await ensure_online(c)
                            if clock_cfg.get("enabled"):
                                await sync_profile_clock(force=False)
                            if autoreply_cfg.get("enabled"):
                                await check_pv_auto_reply_light()
                        except Exception:
                            pass
                await asyncio.sleep(10.0)

        if not st["watchdog_started"]:
            st["watchdog_started"] = True
            asyncio.create_task(connection_and_bg_watchdog())

        body_host = ft.Column(spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        on_dialogs_loaded_callback = None

        async def fetch_dialogs_list(limit_count: int = 80):
            items = []
            async with client_lock:
                try:
                    await ensure_online(c)
                    raw_dialogs = []
                    if callable(getattr(c, "get_dialogs", None)):
                        raw_dialogs = await asyncio.wait_for(c.get_dialogs(limit=limit_count), timeout=12.0)
                    elif callable(getattr(c, "iter_dialogs", None)):
                        async for d in c.iter_dialogs(limit=limit_count):
                            raw_dialogs.append(d)

                    for d in raw_dialogs:
                        ent = getattr(d, "entity", None)
                        cid = getattr(d, "id", None)
                        if cid is None and ent is not None:
                            cid = getattr(ent, "id", None) or getattr(ent, "guid", None)
                        if cid is None:
                            continue

                        title = (
                            getattr(d, "name", None)
                            or getattr(d, "title", None)
                            or getattr(ent, "title", None)
                            or getattr(ent, "first_name", None)
                            or str(cid)
                        )
                        is_user = getattr(d, "is_user", None)
                        is_group_flag = getattr(d, "is_group", None)
                        is_channel_flag = getattr(d, "is_channel", None)
                        is_broadcast = bool(getattr(ent, "broadcast", False)) if ent is not None else False
                        is_megagroup = bool(getattr(ent, "megagroup", False)) if ent is not None else False

                        cid_str = str(cid)
                        if is_user is True or cid_str.startswith("u0") or (isinstance(cid, int) and cid > 0 and not is_group_flag and not is_channel_flag):
                            kind = "pv"
                        elif is_channel_flag and (is_broadcast or not is_megagroup) and not is_group_flag:
                            kind = "channel"
                        else:
                            kind = "group"

                        items.append({"id": cid_str, "title": str(title), "kind": kind})
                except Exception as ex:
                    log(f"خطا در دریافت لیست چت‌ها: {ex}", RED_NEON)
            st["dialogs"] = items
            if callable(on_dialogs_loaded_callback):
                on_dialogs_loaded_callback()
            return items

        async def fetch_messages_for_chat(raw_target: str, limit_count: int = 20) -> list[dict]:
            msgs = []
            tgt_str = (raw_target or "").strip()
            if not tgt_str:
                return msgs
            async with client_lock:
                try:
                    await ensure_online(c)
                    peer = await resolve_peer(c, tgt_str)
                    raw_msgs = []
                    if callable(getattr(c, "get_messages", None)):
                        raw_msgs = await asyncio.wait_for(c.get_messages(peer, limit=limit_count), timeout=12.0)
                    elif callable(getattr(c, "iter_messages", None)):
                        async for m in c.iter_messages(peer, limit=limit_count):
                            raw_msgs.append(m)

                    for m in raw_msgs:
                        mid = getattr(m, "id", None)
                        if mid is None:
                            continue
                        txt = (
                            getattr(m, "raw_text", None)
                            or getattr(m, "text", None)
                            or getattr(m, "message", None)
                            or ""
                        ).strip()
                        if not txt and getattr(m, "media", None) is not None:
                            txt = "[رسانه / فایل / استیکر]"
                        if not txt:
                            continue

                        sender = getattr(m, "sender", None)
                        sender_name = (
                            getattr(sender, "first_name", None)
                            or getattr(sender, "title", None)
                            or ("شما" if getattr(m, "out", False) else str(getattr(m, "sender_id", "کاربر")))
                        )
                        msgs.append({
                            "id": mid,
                            "sender": str(sender_name),
                            "text": txt,
                        })
                except Exception as ex:
                    log(f"خطا در دریافت پیام‌های اخیر: {ex}", RED_NEON)
            return msgs

        async def fetch_recent_messages(raw_target: str):
            st["recent_messages"] = await fetch_messages_for_chat(raw_target, limit_count=20)

        def set_active_target_clean(new_val: str, title: str = ""):
            val = (new_val or "").strip()
            if st["reply_chat_id"] and st["reply_chat_id"] != val:
                st["reply_to_id"] = None
                st["reply_to_preview"] = ""
                st["reply_chat_id"] = ""
            st["active_target"] = val
            if title:
                st["active_target_title"] = title

        def build_reply_status_banner(on_clear_callback=None):
            if st["reply_to_id"] is None:
                return ft.Container(visible=False)

            def clear_rep(e):
                st["reply_to_id"] = None
                st["reply_to_preview"] = ""
                st["reply_chat_id"] = ""
                if callable(on_clear_callback):
                    on_clear_callback()
                safe_page_update()

            clr_b, _ = make_btn("✖️ لغو", clear_rep, color=RED_NEON, kind="text")
            preview = st["reply_to_preview"]
            if len(preview) > 40:
                preview = preview[:40] + "..."
            return ft.Container(
                padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                border_radius=ft.BorderRadius.all(8),
                bgcolor=BG_INPUT,
                border=ft.Border.all(1, RED_LIGHT),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(f"↩️ ریپلای روی #{st['reply_to_id']}: {preview}", size=12, color=RED_LIGHT, expand=True),
                        clr_b,
                    ],
                ),
            )

        # ==========================================
        # ویجت ۱: چت‌ها و پیام‌های اخیر برای ریپلای
        # ==========================================
        def build_chats_widget():
            nonlocal on_dialogs_loaded_callback

            manual_target = ft.TextField(
                label="آیدی یا شناسه چت انتخاب‌شده",
                hint_text="@username یا شناسه عددی",
                value=st["active_target"],
                text_align=ft.TextAlign.LEFT,
                bgcolor=BG_INPUT,
                border_color=BORDER_CRIMSON,
                on_change=lambda e: set_active_target_clean(e.control.value or ""),
            )
            chat_list_col = ft.Column(spacing=6, height=175, scroll=ft.ScrollMode.AUTO)
            recent_msgs_col = ft.Column(spacing=6, height=200, scroll=ft.ScrollMode.AUTO)
            selected_count_lbl = ft.Text(f"چت‌های انتخاب‌شده برای ارسال گروهی: {len(st['selected_targets'])}", size=12, color=RED_LIGHT)
            reply_banner_holder = ft.Column(controls=[build_reply_status_banner(lambda: refresh_recent_msg_cards())])

            def rebuild_reply_banner():
                reply_banner_holder.controls = [build_reply_status_banner(lambda: refresh_recent_msg_cards())]

            def select_message_for_reply(e, mid, mtext):
                st["reply_to_id"] = mid
                st["reply_to_preview"] = mtext
                st["reply_chat_id"] = st["active_target"]
                rebuild_reply_banner()
                refresh_recent_msg_cards()
                log(f"پیام #{mid} برای ریپلای انتخاب شد ↩️", RED_LIGHT)
                safe_page_update()

            def refresh_recent_msg_cards():
                recent_msgs_col.controls.clear()
                if not st["recent_messages"]:
                    recent_msgs_col.controls.append(
                        ft.Text("پیامی بارگذاری نشده است. روی یک پی‌وی/گپ بزنید یا دکمه پیام‌های اخیر را بزنید.", size=12, color=TEXT_MUTED)
                    )
                    return

                for m in st["recent_messages"]:
                    mid = m["id"]
                    is_rep_selected = st["reply_to_id"] == mid
                    card = ft.Container(
                        padding=ft.Padding.all(9),
                        border_radius=ft.BorderRadius.all(8),
                        bgcolor="#1C0A10" if is_rep_selected else BG_INPUT,
                        border=ft.Border.all(1.5 if is_rep_selected else 1, RED_NEON if is_rep_selected else BORDER_CRIMSON),
                        on_click=lambda e, m_id=mid, m_txt=m["text"]: select_message_for_reply(e, m_id, m_txt),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Column(
                                    spacing=2,
                                    expand=True,
                                    controls=[
                                        ft.Text(f"{m['sender']}  (#{mid})", size=11, color=RED_LIGHT, weight=ft.FontWeight.W_600),
                                        ft.Text(m["text"], size=13, color=TEXT_WHITE, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                                    ],
                                ),
                                ft.Text("↩️ انتخاب‌شده" if is_rep_selected else "ریپلای", size=12, color=RED_NEON if is_rep_selected else TEXT_MUTED),
                            ],
                        ),
                    )
                    recent_msgs_col.controls.append(card)

            async def load_msgs_for_current_target(e=None):
                tgt = (manual_target.value or st["active_target"] or "").strip()
                if not tgt:
                    log("ابتدا یک چت را انتخاب کنید یا آیدی آن را وارد کنید.", RED_NEON)
                    return
                set_active_target_clean(tgt)
                log(f"در حال دریافت پیام‌های اخیر {tgt}...", RED_LIGHT)
                await fetch_recent_messages(tgt)
                refresh_recent_msg_cards()
                log(f"{len(st['recent_messages'])} پیام اخیر دریافت شد ✅", "#10B981")
                safe_page_update()

            async def on_chat_card_click(e, cid: str, title: str):
                set_active_target_clean(cid, title)
                manual_target.value = cid
                if cid in st["selected_targets"]:
                    del st["selected_targets"][cid]
                else:
                    st["selected_targets"][cid] = title
                selected_count_lbl.value = f"چت‌های انتخاب‌شده برای ارسال گروهی: {len(st['selected_targets'])}"
                rebuild_reply_banner()
                refresh_chat_cards()
                safe_page_update()
                await fetch_recent_messages(cid)
                refresh_recent_msg_cards()
                safe_page_update()

            def refresh_chat_cards():
                chat_list_col.controls.clear()
                flt = st["chat_filter"]
                if flt == "all":
                    filtered = st["dialogs"]
                elif flt == "pv":
                    filtered = [x for x in st["dialogs"] if x["kind"] == "pv"]
                else:
                    filtered = [x for x in st["dialogs"] if x["kind"] in ("group", "channel")]

                if not filtered:
                    chat_list_col.controls.append(
                        ft.Text("چتی یافت نشد. دکمه بروزرسانی چت‌ها را بزنید.", size=12, color=TEXT_MUTED)
                    )
                    return

                for item in filtered:
                    cid = item["id"]
                    title = item["title"]
                    selected = cid in st["selected_targets"] or st["active_target"] == cid
                    if item["kind"] == "pv":
                        badge = "👤 پی‌وی"
                    elif item["kind"] == "channel":
                        badge = "📢 کانال"
                    else:
                        badge = "👥 گپ"
                    card = ft.Container(
                        padding=ft.Padding.all(9),
                        border_radius=ft.BorderRadius.all(10),
                        bgcolor="#1C0A10" if selected else BG_INPUT,
                        border=ft.Border.all(1.5 if selected else 1, RED_NEON if selected else BORDER_CRIMSON),
                        on_click=lambda e, c_id=cid, c_title=title: page.run_task(on_chat_card_click, e, c_id, c_title),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Column(
                                    spacing=2,
                                    expand=True,
                                    controls=[
                                        ft.Text(title, size=14, weight=ft.FontWeight.W_600, color=TEXT_WHITE),
                                        ft.Text(f"{badge}  |  ID: {cid}", size=11, color=TEXT_MUTED),
                                    ],
                                ),
                                ft.Text("✅ انتخاب" if selected else "انتخاب", size=12, color=RED_NEON if selected else "#64748B"),
                            ],
                        ),
                    )
                    chat_list_col.controls.append(card)

            def set_filter(e, mode: str):
                st["chat_filter"] = mode
                f_all.bgcolor = RED_PRIMARY if mode == "all" else BG_INPUT
                f_pv.bgcolor = RED_PRIMARY if mode == "pv" else BG_INPUT
                f_gp.bgcolor = RED_PRIMARY if mode == "group" else BG_INPUT
                refresh_chat_cards()
                safe_page_update()

            async def reload_chats(e):
                log("در حال دریافت لیست پی‌وی‌ها و گپ‌ها...", RED_LIGHT)
                await fetch_dialogs_list()
                refresh_chat_cards()
                log(f"{len(st['dialogs'])} چت بارگذاری شد ✅", "#10B981")
                safe_page_update()

            def clear_selected(e):
                st["selected_targets"].clear()
                set_active_target_clean("")
                st["recent_messages"].clear()
                manual_target.value = ""
                selected_count_lbl.value = "چت‌های انتخاب‌شده برای ارسال گروهی: 0"
                rebuild_reply_banner()
                refresh_chat_cards()
                refresh_recent_msg_cards()
                safe_page_update()

            on_dialogs_loaded_callback = lambda: (refresh_chat_cards(), safe_page_update())

            f_all, _ = make_btn("همه", lambda e: set_filter(e, "all"), bgcolor=RED_PRIMARY if st["chat_filter"] == "all" else BG_INPUT, height=36, expand=True)
            f_pv, _ = make_btn("👤 پی‌وی", lambda e: set_filter(e, "pv"), bgcolor=RED_PRIMARY if st["chat_filter"] == "pv" else BG_INPUT, height=36, expand=True)
            f_gp, _ = make_btn("👥 گپ‌ها", lambda e: set_filter(e, "group"), bgcolor=RED_PRIMARY if st["chat_filter"] == "group" else BG_INPUT, height=36, expand=True)
            rel_btn, _ = make_btn("🔄 بروزرسانی چت‌ها", reload_chats, bgcolor=RED_PRIMARY, height=40, expand=True)
            load_msg_btn, _ = make_btn("📜 پیام‌های اخیر", load_msgs_for_current_target, bgcolor=RED_DARK, height=40, expand=True)
            clr_btn, _ = make_btn("پاک کردن", clear_selected, color=RED_NEON, kind="text")

            refresh_chat_cards()
            refresh_recent_msg_cards()

            return ft.Column(
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.Container(
                        bgcolor=BG_CARD,
                        padding=14,
                        border_radius=ft.BorderRadius.all(12),
                        border=ft.Border.all(1, BORDER_CRIMSON),
                        content=ft.Column(
                            spacing=10,
                            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                            controls=[
                                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                                    ft.Text("💬 انتخاب پی‌وی یا گپ", size=16, weight=ft.FontWeight.BOLD, color=TEXT_WHITE),
                                    clr_btn,
                                ]),
                                manual_target,
                                ft.Row(spacing=6, controls=[rel_btn, load_msg_btn]),
                                ft.Row(spacing=6, controls=[f_all, f_pv, f_gp]),
                                selected_count_lbl,
                                chat_list_col,
                            ],
                        ),
                    ),
                    ft.Container(
                        bgcolor=BG_CARD,
                        padding=14,
                        border_radius=ft.BorderRadius.all(12),
                        border=ft.Border.all(1, BORDER_CRIMSON),
                        content=ft.Column(
                            spacing=8,
                            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                            controls=[
                                ft.Text("📜 پیام‌های اخیر چت (برای ریپلای لمس کنید)", size=14, weight=ft.FontWeight.BOLD, color=RED_LIGHT),
                                reply_banner_holder,
                                recent_msgs_col,
                            ],
                        ),
                    ),
                ],
            )

        # ==========================================
        # ویجت ۲: ارسال چندتایی پرسرعت + حافظه ذخیره پیام‌ها
        # ==========================================
        def build_multi_msg_widget():
            target_field = ft.TextField(
                label="مقصد ارسال (آیدی یا چت انتخاب‌شده)",
                hint_text="@username یا شناسه عددی",
                value=st["active_target"],
                text_align=ft.TextAlign.LEFT,
                bgcolor=BG_INPUT,
                border_color=BORDER_CRIMSON,
                on_change=lambda e: set_active_target_clean(e.control.value or ""),
            )
            multi_targets_card, multi_targets_state, _ = make_toggle_card(
                title="ارسال همزمان به تمام چت‌های تیک‌خورده",
                subtitle=f"تعداد چت‌های انتخاب‌شده فعلی: {len(st['selected_targets'])} چت",
                initial_val=len(st["selected_targets"]) > 1,
                on_toggle_callback=lambda val: safe_page_update(),
            )
            new_msg_input = ft.TextField(
                label="متن پیام جدید برای افزودن به لیست",
                hint_text="متن پیام را بنویسید...",
                bgcolor=BG_INPUT,
                border_color=BORDER_CRIMSON,
            )
            rounds_box = ft.TextField(
                label="تعداد دور ارسال کل لیست",
                value="1",
                keyboard_type=ft.KeyboardType.NUMBER,
                text_align=ft.TextAlign.LEFT,
                bgcolor=BG_INPUT,
                border_color=BORDER_CRIMSON,
                expand=True,
            )
            delay_box = ft.TextField(
                label="تاخیر (0 = حداکثر سرعت)",
                value="0",
                keyboard_type=ft.KeyboardType.NUMBER,
                text_align=ft.TextAlign.LEFT,
                bgcolor=BG_INPUT,
                border_color=BORDER_CRIMSON,
                expand=True,
            )
            m_stat = ft.Text("آماده ارسال چندتایی", size=12, color=TEXT_MUTED)
            msg_items_col = ft.Column(spacing=6)

            def remove_msg_item(e, index: int):
                if 0 <= index < len(st["multi_messages"]):
                    st["multi_messages"].pop(index)
                    render_msg_items()
                    safe_page_update()

            def render_msg_items():
                msg_items_col.controls.clear()
                if not st["multi_messages"]:
                    msg_items_col.controls.append(ft.Text("لیست پیام‌های چندتایی خالی است.", size=12, color=TEXT_MUTED))
                    return
                for idx, txt in enumerate(st["multi_messages"]):
                    del_btn, _ = make_btn("حذف", lambda e, i=idx: remove_msg_item(e, i), color=RED_NEON, kind="text")
                    row_card = ft.Container(
                        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                        border_radius=ft.BorderRadius.all(8),
                        bgcolor=BG_INPUT,
                        border=ft.Border.all(1, BORDER_CRIMSON),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(f"{idx + 1}. {txt}", size=13, color=TEXT_WHITE, expand=True),
                                del_btn,
                            ],
                        ),
                    )
                    msg_items_col.controls.append(row_card)

            def add_msg_item(e):
                val = (new_msg_input.value or "").strip()
                if not val:
                    return
                st["multi_messages"].append(val)
                new_msg_input.value = ""
                render_msg_items()
                safe_page_update()

            def save_messages_as_default(e):
                if not st["multi_messages"]:
                    log("لیست پیام‌ها خالی است؛ پیامی برای ذخیره وجود ندارد.", RED_NEON)
                    return
                save_multi_messages_disk(st["multi_messages"])
                log(f"{len(st['multi_messages'])} پیام در حافظه پیش‌فرض ذخیره شد 💾✅", "#10B981")

            async def run_multi_sender():
                try:
                    rounds = max(1, int(rounds_box.value or 1))
                    dly = max(0.0, float(delay_box.value or 0.0))
                except ValueError:
                    rounds, dly = 1, 0.0

                targets = []
                if multi_targets_state["val"] and st["selected_targets"]:
                    targets = list(st["selected_targets"].keys())
                elif (target_field.value or "").strip():
                    targets = [(target_field.value or "").strip()]

                if not targets:
                    log("ابتدا یک پی‌وی/گپ انتخاب کنید یا آیدی مقصد را وارد کنید.", RED_NEON)
                    st["multi_running"] = False
                    m_lbl.value = "🚀 شروع ارسال چندتایی"
                    m_btn.bgcolor = RED_PRIMARY
                    safe_page_update()
                    return

                messages = list(st["multi_messages"])
                total_ops = rounds * len(targets) * len(messages)
                done = 0
                last_ui_tick = 0.0

                try:
                    async with client_lock:
                        await ensure_online(c)
                        resolved_peers = {}
                        for t_raw in targets:
                            resolved_peers[t_raw] = await resolve_peer(c, t_raw)

                        queue = []
                        for _ in range(rounds):
                            for raw_t in targets:
                                rep_id = st["reply_to_id"] if (st["reply_to_id"] and st["reply_chat_id"] == raw_t) else None
                                for m_txt in messages:
                                    queue.append((raw_t, resolved_peers[raw_t], m_txt, rep_id))

                        if dly == 0:
                            batch_size = 5
                            for i in range(0, len(queue), batch_size):
                                if not st["multi_running"]:
                                    log(f"ارسال چندتایی متوقف شد ({done} از {total_ops}).", "#F59E0B")
                                    return
                                chunk = queue[i:i + batch_size]
                                await asyncio.gather(
                                    *(send_fast_single(c, peer, rt, txt, rep) for rt, peer, txt, rep in chunk)
                                )
                                done += len(chunk)
                                now = time.monotonic()
                                if now - last_ui_tick >= 0.3 or done == total_ops:
                                    last_ui_tick = now
                                    m_stat.value = f"ارسال شد: {done} از {total_ops}"
                                    m_stat.color = "#10B981"
                                    safe_page_update()
                        else:
                            for rt, peer, txt, rep in queue:
                                if not st["multi_running"]:
                                    log(f"ارسال چندتایی متوقف شد ({done} از {total_ops}).", "#F59E0B")
                                    return
                                await send_fast_single(c, peer, rt, txt, rep)
                                done += 1
                                now = time.monotonic()
                                if now - last_ui_tick >= 0.3 or done == total_ops:
                                    last_ui_tick = now
                                    m_stat.value = f"ارسال شد: {done} از {total_ops}"
                                    m_stat.color = "#10B981"
                                    safe_page_update()
                                if done < total_ops:
                                    await asyncio.sleep(dly)

                    log(f"ارسال چندتایی با موفقیت کامل شد ({done} پیام) ✅", "#10B981")
                except asyncio.CancelledError:
                    log("ارسال چندتایی متوقف شد.", "#F59E0B")
                except Exception as ex:
                    log(f"خطا در ارسال چندتایی: {ex}", RED_NEON)
                    m_stat.value = f"توقف در {done}/{total_ops}: {ex}"
                    m_stat.color = RED_NEON
                finally:
                    st["multi_running"] = False
                    m_lbl.value = "🚀 شروع ارسال چندتایی"
                    m_btn.bgcolor = RED_PRIMARY
                    safe_page_update()

            async def toggle_multi(e):
                if st["multi_running"]:
                    st["multi_running"] = False
                    return
                if st["turbo_running"]:
                    log("ابتدا ارسال توربو را متوقف کنید.", "#F59E0B")
                    return
                if not st["multi_messages"]:
                    log("حداقل یک پیام به لیست چندتایی اضافه کنید.", RED_NEON)
                    return
                st["multi_running"] = True
                m_lbl.value = "⛔ توقف ارسال چندتایی"
                m_btn.bgcolor = RED_DARK
                safe_page_update()
                asyncio.create_task(run_multi_sender())

            add_btn, _ = make_btn("➕ افزودن به لیست", add_msg_item, bgcolor=RED_PRIMARY, height=40, expand=True)
            save_msgs_btn, _ = make_btn("💾 ذخیره پیام‌ها (پیش‌فرض)", save_messages_as_default, bgcolor=RED_DARK, height=40, expand=True)
            m_btn, m_lbl = make_btn("🚀 شروع ارسال چندتایی", toggle_multi, bgcolor=RED_PRIMARY, height=46)
            render_msg_items()

            return ft.Container(
                bgcolor=BG_CARD,
                padding=14,
                border_radius=ft.BorderRadius.all(12),
                border=ft.Border.all(1, BORDER_CRIMSON),
                content=ft.Column(
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("📨 ارسال چندتایی (Multi-Message)", size=16, weight=ft.FontWeight.BOLD, color=TEXT_WHITE),
                        build_reply_status_banner(),
                        target_field,
                        multi_targets_card,
                        new_msg_input,
                        ft.Row(spacing=6, controls=[add_btn, save_msgs_btn]),
                        msg_items_col,
                        ft.Row(spacing=8, controls=[rounds_box, delay_box]),
                        m_btn,
                        m_stat,
                    ],
                ),
            )

        # ==========================================
        # ویجت ۳: ارسال توربو فوق‌سریع
        # ==========================================
        def build_turbo_widget():
            target_box = ft.TextField(
                label="آیدی یا شناسه مقصد",
                hint_text="@username یا 12345678",
                value=st["active_target"],
                text_align=ft.TextAlign.LEFT,
                bgcolor=BG_INPUT,
                border_color=BORDER_CRIMSON,
                on_change=lambda e: set_active_target_clean(e.control.value or ""),
            )
            msg_box = ft.TextField(label="متن پیام توربو", bgcolor=BG_INPUT, border_color=BORDER_CRIMSON)
            cnt_box = ft.TextField(label="تعداد", value="20", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_CRIMSON, expand=True)
            dly_box = ft.TextField(label="تاخیر (0 = حداکثر سرعت)", value="0", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_CRIMSON, expand=True)
            t_stat = ft.Text("آماده", size=12, color=TEXT_MUTED)

            async def turbo_run():
                sent = 0
                try:
                    total = max(1, int(cnt_box.value or 10))
                    dly = max(0.0, float(dly_box.value or 0.0))
                except ValueError:
                    total, dly = 10, 0.0

                raw_t = (target_box.value or "").strip()
                txt = (msg_box.value or "").strip()
                rep_id = st["reply_to_id"] if (st["reply_to_id"] and st["reply_chat_id"] == raw_t) else None
                last_ui_tick = 0.0

                try:
                    async with client_lock:
                        await ensure_online(c)
                        peer = await resolve_peer(c, raw_t)

                        if dly == 0:
                            batch_size = 5
                            while st["turbo_running"] and sent < total:
                                cur_batch = min(batch_size, total - sent)
                                await asyncio.gather(
                                    *(send_fast_single(c, peer, raw_t, txt, rep_id) for _ in range(cur_batch))
                                )
                                sent += cur_batch
                                now = time.monotonic()
                                if now - last_ui_tick >= 0.3 or sent == total:
                                    last_ui_tick = now
                                    t_stat.value = f"ارسال شد: {sent}/{total}"
                                    t_stat.color = "#10B981"
                                    safe_page_update()
                        else:
                            while st["turbo_running"] and sent < total:
                                await send_fast_single(c, peer, raw_t, txt, rep_id)
                                sent += 1
                                now = time.monotonic()
                                if now - last_ui_tick >= 0.3 or sent == total:
                                    last_ui_tick = now
                                    t_stat.value = f"ارسال شد: {sent}/{total}"
                                    t_stat.color = "#10B981"
                                    safe_page_update()
                                if sent < total:
                                    await asyncio.sleep(dly)

                    log(f"پایان ارسال توربو ({sent} پیام) ✅", "#10B981")
                except asyncio.CancelledError:
                    log("ارسال توربو متوقف شد.", "#F59E0B")
                except Exception as ex:
                    log(f"خطای توربو: {ex}", RED_NEON)
                    t_stat.value = f"توقف در {sent}/{total}: {ex}"
                    t_stat.color = RED_NEON
                finally:
                    st["turbo_running"] = False
                    t_lbl.value = "🚀 شروع توربو"
                    t_btn.bgcolor = RED_PRIMARY
                    safe_page_update()

            async def toggle_turbo(e):
                if st["turbo_running"]:
                    st["turbo_running"] = False
                    return
                if st["multi_running"]:
                    log("ابتدا ارسال چندتایی را متوقف کنید.", "#F59E0B")
                    return
                if not (target_box.value or "").strip() or not (msg_box.value or "").strip():
                    log("مقصد و متن را وارد کنید.", RED_NEON)
                    return
                st["turbo_running"] = True
                t_lbl.value = "⛔ توقف توربو"
                t_btn.bgcolor = RED_DARK
                safe_page_update()
                asyncio.create_task(turbo_run())

            t_btn, t_lbl = make_btn("🚀 شروع توربو", toggle_turbo, bgcolor=RED_PRIMARY, height=44)
            return ft.Container(
                bgcolor=BG_CARD,
                padding=14,
                border_radius=ft.BorderRadius.all(12),
                border=ft.Border.all(1, BORDER_CRIMSON),
                content=ft.Column(
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("🚀 ارسال توربو فوق‌سریع", size=16, weight=ft.FontWeight.BOLD, color=TEXT_WHITE),
                        build_reply_status_banner(),
                        target_box,
                        msg_box,
                        ft.Row(spacing=8, controls=[cnt_box, dly_box]),
                        t_btn,
                        t_stat,
                    ],
                ),
            )

        # ==========================================
        # ویجت ۴: فوروارد هوشمند به کاربران فعال گپ‌ها (۲۰۰ پیام اخیر)
        # ==========================================
        def build_forward_widget():
            src_id_box = ft.TextField(
                label="شناسه یا آیدی کانال / پی‌وی مبدأ",
                hint_text="از لیست پایین انتخاب کنید یا آیدی وارد کنید",
                value=st["fwd_source_chat"],
                text_align=ft.TextAlign.LEFT,
                bgcolor=BG_INPUT,
                border_color=BORDER_CRIMSON,
                on_change=lambda e: st.update({"fwd_source_chat": (e.control.value or "").strip()}),
            )
            src_chats_col = ft.Column(spacing=6, height=145, scroll=ft.ScrollMode.AUTO)
            src_msgs_col = ft.Column(spacing=6, height=175, scroll=ft.ScrollMode.AUTO)

            selected_msg_lbl = ft.Text(
                f"✅ پیام انتخاب‌شده (#{st['fwd_selected_msg_id']}): {st['fwd_selected_msg_preview']}"
                if st["fwd_selected_msg_id"] is not None
                else "⚠️ هنوز پیامی برای فوروارد انتخاب نشده است",
                size=12,
                color="#10B981" if st["fwd_selected_msg_id"] is not None else "#F59E0B",
                weight=ft.FontWeight.W_600,
            )

            interval_box = ft.TextField(
                label="تایمر تکرار فوروارد (دقیقه)",
                value=str(forward_cfg.get("interval_min", 5)),
                keyboard_type=ft.KeyboardType.NUMBER,
                text_align=ft.TextAlign.LEFT,
                bgcolor=BG_INPUT,
                border_color=BORDER_ACTIVE,
                on_change=lambda e: save_forward_config({"interval_min": max(1, int(e.control.value))}) if (e.control.value or "").isdigit() and int(e.control.value) >= 1 else None,
            )

            fwd_stat_lbl = ft.Text(st["fwd_status"], size=12, color=TEXT_MUTED)

            def render_src_messages():
                src_msgs_col.controls.clear()
                if not st["fwd_messages"]:
                    src_msgs_col.controls.append(
                        ft.Text("پیامی بارگذاری نشده است. یک کانال یا پی‌وی را انتخاب کنید.", size=12, color=TEXT_MUTED)
                    )
                    return

                for m in st["fwd_messages"]:
                    mid = m["id"]
                    is_sel = st["fwd_selected_msg_id"] == mid
                    preview = m["text"]
                    if len(preview) > 55:
                        preview = preview[:55] + "..."

                    def pick_fwd_msg(e, m_id=mid, m_prev=preview):
                        st["fwd_selected_msg_id"] = m_id
                        st["fwd_selected_msg_preview"] = m_prev
                        selected_msg_lbl.value = f"✅ پیام انتخاب‌شده (#{m_id}): {m_prev}"
                        selected_msg_lbl.color = "#10B981"
                        render_src_messages()
                        log(f"پیام #{m_id} برای فوروارد خودکار انتخاب شد 📢", RED_LIGHT)
                        safe_page_update()

                    src_msgs_col.controls.append(
                        ft.Container(
                            padding=ft.Padding.all(9),
                            border_radius=ft.BorderRadius.all(8),
                            bgcolor="#1C0A10" if is_sel else BG_INPUT,
                            border=ft.Border.all(1.5 if is_sel else 1, RED_NEON if is_sel else BORDER_CRIMSON),
                            on_click=pick_fwd_msg,
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(f"#{mid} | {preview}", size=12, color=TEXT_WHITE, expand=True),
                                    ft.Text("✅ انتخاب" if is_sel else "انتخاب", size=11, color=RED_NEON if is_sel else TEXT_MUTED),
                                ],
                            ),
                        )
                    )

            async def load_src_messages(e=None):
                cid = (src_id_box.value or st["fwd_source_chat"] or "").strip()
                if not cid:
                    log("ابتدا یک کانال یا پی‌وی را انتخاب کنید.", RED_NEON)
                    return
                st["fwd_source_chat"] = cid
                fwd_stat_lbl.value = "⏳ در حال دریافت پیام‌های اخیر کانال/پی‌وی..."
                safe_page_update()
                st["fwd_messages"] = await fetch_messages_for_chat(cid, limit_count=25)
                render_src_messages()
                fwd_stat_lbl.value = f"✅ {len(st['fwd_messages'])} پیام اخیر بارگذاری شد. پیام مورد نظر را لمس کنید."
                safe_page_update()

            async def on_src_chat_click(e, cid: str, title: str):
                st["fwd_source_chat"] = cid
                st["fwd_source_title"] = title
                st["fwd_selected_msg_id"] = None
                st["fwd_selected_msg_preview"] = ""
                selected_msg_lbl.value = "⚠️ پیام مورد نظر را از لیست پایین انتخاب کنید"
                selected_msg_lbl.color = "#F59E0B"
                src_id_box.value = cid
                render_src_chats()
                safe_page_update()
                await load_src_messages()

            def render_src_chats():
                src_chats_col.controls.clear()
                pv_and_channels = [x for x in st["dialogs"] if x["kind"] in ("pv", "channel")]
                target_list = pv_and_channels if pv_and_channels else st["dialogs"]
                if not target_list:
                    src_chats_col.controls.append(
                        ft.Text("کانال یا پی‌وی یافت نشد. دکمه بروزرسانی لیست را بزنید.", size=12, color=TEXT_MUTED)
                    )
                    return

                for item in target_list:
                    cid = item["id"]
                    title = item["title"]
                    is_sel = st["fwd_source_chat"] == cid
                    badge = "📢 کانال" if item["kind"] == "channel" else ("👤 پی‌وی" if item["kind"] == "pv" else "👥 گپ")
                    src_chats_col.controls.append(
                        ft.Container(
                            padding=ft.Padding.all(9),
                            border_radius=ft.BorderRadius.all(8),
                            bgcolor="#1C0A10" if is_sel else BG_INPUT,
                            border=ft.Border.all(1.5 if is_sel else 1, RED_NEON if is_sel else BORDER_CRIMSON),
                            on_click=lambda e, c_id=cid, c_t=title: page.run_task(on_src_chat_click, e, c_id, c_t),
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Column(
                                        spacing=1,
                                        expand=True,
                                        controls=[
                                            ft.Text(title, size=13, weight=ft.FontWeight.W_600, color=TEXT_WHITE),
                                            ft.Text(f"{badge} | ID: {cid}", size=11, color=TEXT_MUTED),
                                        ],
                                    ),
                                    ft.Text("✅" if is_sel else "انتخاب", size=12, color=RED_NEON if is_sel else TEXT_MUTED),
                                ],
                            ),
                        )
                    )

            async def reload_src_chats(e):
                fwd_stat_lbl.value = "⏳ در حال دریافت لیست کانال‌ها و پی‌وی‌ها..."
                safe_page_update()
                await fetch_dialogs_list(limit_count=80)
                render_src_chats()
                fwd_stat_lbl.value = "✅ لیست کانال‌ها و پی‌وی‌ها بروزرسانی شد."
                safe_page_update()

            async def forward_worker_loop():
                round_idx = 0
                src_chat_raw = st["fwd_source_chat"]
                msg_id = st["fwd_selected_msg_id"]

                while st["fwd_running"]:
                    round_idx += 1
                    try:
                        await ensure_online(c)
                        my_id = await get_my_user_id(c)
                        src_peer = await resolve_peer(c, src_chat_raw)

                        st["fwd_status"] = f"🔄 دور {round_idx}: در حال دریافت لیست گپ‌های عضو..."
                        fwd_stat_lbl.value = st["fwd_status"]
                        safe_page_update()

                        all_dialogs = await fetch_dialogs_list(limit_count=100)
                        groups = [d for d in all_dialogs if d["kind"] == "group"]

                        unique_users = []
                        seen_users = set()

                        for g_idx, grp in enumerate(groups, start=1):
                            if not st["fwd_running"]:
                                break
                            gid = grp["id"]
                            gtitle = grp["title"]
                            st["fwd_status"] = (
                                f"🔍 دور {round_idx} | بررسی گپ ({g_idx}/{len(groups)}): {gtitle} "
                                f"| کاربران یکتا: {len(unique_users)}"
                            )
                            fwd_stat_lbl.value = st["fwd_status"]
                            safe_page_update()

                            try:
                                async with client_lock:
                                    g_peer = await resolve_peer(c, gid)
                                    recent_g_msgs = []
                                    if callable(getattr(c, "get_messages", None)):
                                        recent_g_msgs = await asyncio.wait_for(c.get_messages(g_peer, limit=200), timeout=15.0)
                                    elif callable(getattr(c, "iter_messages", None)):
                                        async for gm in c.iter_messages(g_peer, limit=200):
                                            recent_g_msgs.append(gm)

                                for gm in recent_g_msgs:
                                    if getattr(gm, "post", False):
                                        continue
                                    sender_obj = getattr(gm, "sender", None)
                                    if sender_obj is not None and bool(getattr(sender_obj, "bot", False) or getattr(sender_obj, "is_bot", False)):
                                        continue
                                    uid = getattr(gm, "sender_id", None) or getattr(gm, "from_id", None)
                                    if uid is None and sender_obj is not None:
                                        uid = getattr(sender_obj, "id", None) or getattr(sender_obj, "guid", None)
                                    if uid is None:
                                        continue
                                    uid_str = str(uid).strip()
                                    if not uid_str or uid_str == my_id or uid_str == gid or uid_str.startswith("-"):
                                        continue
                                    if uid_str not in seen_users:
                                        seen_users.add(uid_str)
                                        unique_users.append(uid_str)
                            except Exception:
                                continue

                        sent_ok = 0
                        total_targets = len(unique_users)
                        log(f"دور {round_idx}: {total_targets} کاربر یکتا از ۲۰۰ پیام اخیر {len(groups)} گپ پیدا شد.", RED_LIGHT)

                        for u_idx, target_uid in enumerate(unique_users, start=1):
                            if not st["fwd_running"]:
                                break
                            try:
                                async with client_lock:
                                    target_peer = await resolve_peer(c, target_uid)
                                    await forward_fast_single(c, target_peer, target_uid, src_peer, msg_id)
                                sent_ok += 1
                                st["fwd_status"] = (
                                    f"📨 دور {round_idx} | ارسال به پی‌وی ({u_idx}/{total_targets}) | موفق: {sent_ok}"
                                )
                                fwd_stat_lbl.value = st["fwd_status"]
                                safe_page_update()
                                await asyncio.sleep(1.5)
                            except Exception:
                                await asyncio.sleep(0.6)

                        if not st["fwd_running"]:
                            break

                        try:
                            wait_mins = max(1, int(interval_box.value or forward_cfg.get("interval_min", 5)))
                        except ValueError:
                            wait_mins = 5
                        forward_cfg["interval_min"] = wait_mins
                        save_forward_config(forward_cfg)

                        log(f"پایان دور {round_idx}: {sent_ok} فوروارد موفق انجام شد ✅", "#10B981")

                        wait_secs = wait_mins * 60
                        for rem in range(wait_secs, 0, -1):
                            if not st["fwd_running"]:
                                break
                            if rem % 5 == 0 or rem <= 10:
                                st["fwd_status"] = (
                                    f"✅ دور {round_idx} تکمیل شد ({sent_ok} ارسال موفق به {total_targets} کاربر یکتا). "
                                    f"دور بعدی تا {rem} ثانیه دیگر..."
                                )
                                fwd_stat_lbl.value = st["fwd_status"]
                                safe_page_update()
                            await asyncio.sleep(1.0)

                    except Exception as ex:
                        log(f"خطا در دور {round_idx} فوروارد: {ex}", RED_NEON)
                        st["fwd_status"] = f"⚠️ خطا: {ex} (تلاش مجدد تا ۲۰ ثانیه)"
                        fwd_stat_lbl.value = st["fwd_status"]
                        safe_page_update()
                        for _ in range(20):
                            if not st["fwd_running"]:
                                break
                            await asyncio.sleep(1.0)

                st["fwd_running"] = False
                fwd_btn_lbl.value = "🚀 شروع فوروارد خودکار"
                fwd_toggle_btn.bgcolor = RED_PRIMARY
                st["fwd_status"] = "🛑 فوروارد خودکار متوقف شد."
                fwd_stat_lbl.value = st["fwd_status"]
                safe_page_update()

            async def toggle_forward(e):
                if st["fwd_running"]:
                    st["fwd_running"] = False
                    log("در حال توقف فوروارد خودکار...", "#F59E0B")
                    return
                if not st["fwd_source_chat"] or st["fwd_selected_msg_id"] is None:
                    log("ابتدا یک کانال/پی‌وی و یک پیام را برای فوروارد انتخاب کنید!", RED_NEON)
                    return
                try:
                    mins = max(1, int(interval_box.value or 5))
                except ValueError:
                    mins = 5
                    interval_box.value = "5"
                forward_cfg["interval_min"] = mins
                save_forward_config(forward_cfg)

                st["fwd_running"] = True
                fwd_btn_lbl.value = "⛔ توقف فوروارد خودکار"
                fwd_toggle_btn.bgcolor = RED_DARK
                safe_page_update()
                asyncio.create_task(forward_worker_loop())

            rel_src_btn, _ = make_btn("🔄 بروزرسانی کانال‌ها و پی‌وی‌ها", reload_src_chats, bgcolor=RED_PRIMARY, height=40, expand=True)
            load_src_msg_btn, _ = make_btn("📜 پیام‌های اخیر", load_src_messages, bgcolor=RED_DARK, height=40, expand=True)
            fwd_toggle_btn, fwd_btn_lbl = make_btn(
                "⛔ توقف فوروارد خودکار" if st["fwd_running"] else "🚀 شروع فوروارد خودکار",
                toggle_forward,
                bgcolor=RED_DARK if st["fwd_running"] else RED_PRIMARY,
                height=46,
            )

            render_src_chats()
            render_src_messages()

            return ft.Container(
                bgcolor=BG_CARD,
                padding=14,
                border_radius=ft.BorderRadius.all(12),
                border=ft.Border.all(1, BORDER_CRIMSON),
                content=ft.Column(
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("📢 فوروارد هوشمند به کاربران فعال گپ‌ها", size=16, weight=ft.FontWeight.BOLD, color=TEXT_WHITE),
                        ft.Text(
                            "یک پیام از کانال یا پی‌وی انتخاب کنید؛ ربات ۲۰۰ پیام اخیر تمام گپ‌های عضو را بررسی کرده و بدون تکرار به پی‌وی آن‌ها فوروارد می‌کند.",
                            size=12,
                            color=TEXT_MUTED,
                        ),
                        src_id_box,
                        ft.Row(spacing=6, controls=[rel_src_btn, load_src_msg_btn]),
                        src_chats_col,
                        ft.Text("📜 پیام‌های اخیر (پیام مورد نظر برای فوروارد را لمس کنید):", size=13, color=RED_LIGHT, weight=ft.FontWeight.W_600),
                        src_msgs_col,
                        selected_msg_lbl,
                        interval_box,
                        fwd_toggle_btn,
                        ft.Container(
                            padding=ft.Padding.all(10),
                            border_radius=ft.BorderRadius.all(8),
                            bgcolor=BG_INPUT,
                            border=ft.Border.all(1, BORDER_ACTIVE),
                            content=fwd_stat_lbl,
                        ),
                    ],
                ),
            )

        # ==========================================
        # ویجت ۵: ارسال پیام خودکار در پی‌وی هنگام آفلاین بودن + کارت تیک واضح
        # ==========================================
        def build_autoreply_widget():
            def on_ar_toggle(new_val: bool):
                autoreply_cfg["enabled"] = new_val
                autoreply_cfg["text"] = (ar_text_box.value or "").strip()
                save_autoreply_config(autoreply_cfg)
                if new_val:
                    log("پیام خودکار آفلاین در پی‌وی روشن شد 🤖✅", "#10B981")
                else:
                    log("پیام خودکار پی‌وی خاموش شد.", RED_LIGHT)
                safe_page_update()

            def on_bg_toggle_from_ar(new_val: bool):
                clock_cfg["bg_keep_alive"] = new_val
                save_clock_config(clock_cfg)
                set_android_wakelock(new_val)
                log("اجرای پس‌زمینه ساعت و پی‌وی خودکار روشن شد 🔒✅" if new_val else "اجرای پس‌زمینه خاموش شد.", "#10B981" if new_val else RED_LIGHT)
                safe_page_update()

            ar_toggle_card, ar_toggle_state, _ = make_toggle_card(
                title="🤖 ارسال پیام خودکار در پی‌وی (حالت آفلاین)",
                subtitle="برای روشن یا خاموش کردن این کارت را لمس کنید",
                initial_val=bool(autoreply_cfg.get("enabled", False)),
                on_toggle_callback=on_ar_toggle,
            )

            ar_text_box = ft.TextField(
                label="متن پیام خودکار (برای هر نفر فقط یک بار ارسال می‌شود)",
                value=autoreply_cfg.get("text", ""),
                multiline=True,
                min_lines=3,
                max_lines=5,
                bgcolor=BG_INPUT,
                border_color=BORDER_CRIMSON,
            )

            bg_keep_card, bg_keep_state, _ = make_toggle_card(
                title="🔒 اجرای مداوم در پس‌زمینه (حتی پس از بستن برنامه)",
                subtitle="فعال ماندن همزمان ساعت و پیام خودکار پی‌وی در پس‌زمینه",
                initial_val=bool(clock_cfg.get("bg_keep_alive", True)),
                on_toggle_callback=on_bg_toggle_from_ar,
            )

            replied_lbl = ft.Text(
                f"تعداد افرادی که تا الان پیام خودکار دریافت کرده‌اند: {len(autoreply_cfg.get('replied_users', []))} نفر",
                size=12,
                color="#10B981",
            )

            def save_ar_settings(e):
                autoreply_cfg["enabled"] = bool(ar_toggle_state["val"])
                autoreply_cfg["text"] = (ar_text_box.value or "").strip()
                save_autoreply_config(autoreply_cfg)

                keep_bg = bool(bg_keep_state["val"])
                clock_cfg["bg_keep_alive"] = keep_bg
                save_clock_config(clock_cfg)
                set_android_wakelock(keep_bg)
                log("متن و تنظیمات پیام خودکار ذخیره شد 💾✅", "#10B981")
                safe_page_update()

            def reset_ar_users(e):
                autoreply_cfg["replied_users"] = []
                save_autoreply_config(autoreply_cfg)
                replied_lbl.value = "تعداد افرادی که تا الان پیام خودکار دریافت کرده‌اند: 0 نفر"
                log("لیست افراد پاسخ‌داده‌شده پاک شد ✅", "#10B981")
                safe_page_update()

            save_ar_btn, _ = make_btn("💾 ذخیره متن پاسخ خودکار", save_ar_settings, bgcolor=RED_PRIMARY, height=44, expand=True)
            reset_ar_btn, _ = make_btn("🗑️ ریست لیست افراد", reset_ar_users, bgcolor=RED_DARK, height=44, expand=True)

            return ft.Container(
                bgcolor=BG_CARD,
                padding=14,
                border_radius=ft.BorderRadius.all(12),
                border=ft.Border.all(1, BORDER_CRIMSON),
                content=ft.Column(
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("🤖 پیام خودکار پی‌وی (حالت آفلاین)", size=16, weight=ft.FontWeight.BOLD, color=TEXT_WHITE),
                        ar_toggle_card,
                        ar_text_box,
                        bg_keep_card,
                        ft.Text(
                            "نکته: برای بسته نشدن برنامه توسط گوشی، در تنظیمات باتری اندروید گزینه مصرف باتری این برنامه را روی Unrestricted (بدون محدودیت) بگذارید.",
                            size=11,
                            color="#F59E0B",
                        ),
                        replied_lbl,
                        ft.Row(spacing=6, controls=[save_ar_btn, reset_ar_btn]),
                    ],
                ),
            )

        # ==========================================
        # ویجت ۶: ساعت افق تهران کنار اسم پروفایل + کارت تیک واضح
        # ==========================================
        def build_clock_widget():
            cur_tehran = format_tehran_clock(clock_cfg.get("style", "bold"))
            live_time_txt = ft.Text(f"🕒 ساعت فعلی به افق تهران: {cur_tehran}", size=14, weight=ft.FontWeight.BOLD, color=RED_NEON)

            def on_clock_card_toggle(new_val: bool):
                clock_cfg["enabled"] = new_val
                save_clock_config(clock_cfg)
                log("تیک ساعت فعال شد (دکمه ذخیره پایین را بزنید)" if new_val else "ساعت غیرفعال شد.", "#10B981" if new_val else RED_LIGHT)
                safe_page_update()

            def on_bg_toggle_from_clock(new_val: bool):
                clock_cfg["bg_keep_alive"] = new_val
                save_clock_config(clock_cfg)
                set_android_wakelock(new_val)
                log("اجرای پس‌زمینه ساعت و پی‌وی خودکار روشن شد 🔒✅" if new_val else "اجرای پس‌زمینه خاموش شد.", "#10B981" if new_val else RED_LIGHT)
                safe_page_update()

            clock_toggle_card, clock_toggle_state, _ = make_toggle_card(
                title="⏰ نمایش ساعت افق تهران کنار اسم پروفایل",
                subtitle="برای روشن یا خاموش کردن ساعت این کارت را لمس کنید",
                initial_val=bool(clock_cfg.get("enabled", False)),
                on_toggle_callback=on_clock_card_toggle,
            )

            bg_keep_clock_card, bg_keep_clock_state, _ = make_toggle_card(
                title="🔒 اجرای مداوم در پس‌زمینه (حتی پس از بستن برنامه)",
                subtitle="فعال ماندن همزمان ساعت و پیام خودکار پی‌وی در پس‌زمینه",
                initial_val=bool(clock_cfg.get("bg_keep_alive", True)),
                on_toggle_callback=on_bg_toggle_from_clock,
            )

            base_first_box = ft.TextField(
                label="نام اصلی شما (بدون ساعت)",
                hint_text="اگر خالی بگذارید خودکار از پروفایل خوانده می‌شود",
                value=clock_cfg.get("base_first", ""),
                bgcolor=BG_INPUT,
                border_color=BORDER_CRIMSON,
            )
            base_last_box = ft.TextField(
                label="نام خانوادگی اصلی شما (اختیاری)",
                value=clock_cfg.get("base_last", ""),
                bgcolor=BG_INPUT,
                border_color=BORDER_CRIMSON,
            )
            sep_box = ft.TextField(
                label="جداکننده بین اسم و ساعت",
                value=clock_cfg.get("sep", "|"),
                bgcolor=BG_INPUT,
                border_color=BORDER_CRIMSON,
                expand=True,
            )

            style_state = {"val": clock_cfg.get("style", "bold"), "pos": clock_cfg.get("target_field", "first")}

            def select_style(e, s_val: str):
                style_state["val"] = s_val
                for k, b in style_btns.items():
                    b.bgcolor = RED_PRIMARY if k == s_val else BG_INPUT
                live_time_txt.value = f"🕒 پیش‌نمایش ساعت تهران: {format_tehran_clock(s_val)}"
                safe_page_update()

            def select_pos(e, p_val: str):
                style_state["pos"] = p_val
                pos_first_btn.bgcolor = RED_PRIMARY if p_val == "first" else BG_INPUT
                pos_last_btn.bgcolor = RED_PRIMARY if p_val == "last" else BG_INPUT
                safe_page_update()

            s_norm, _ = make_btn("ساده 14:30", lambda e: select_style(e, "normal"), bgcolor=RED_PRIMARY if style_state["val"] == "normal" else BG_INPUT, height=36, expand=True)
            s_bold, _ = make_btn("ضخیم 𝟏𝟒:𝟑𝟎", lambda e: select_style(e, "bold"), bgcolor=RED_PRIMARY if style_state["val"] == "bold" else BG_INPUT, height=36, expand=True)
            s_mono, _ = make_btn("فانتزی 𝟷𝟺:𝟹𝟶", lambda e: select_style(e, "mono"), bgcolor=RED_PRIMARY if style_state["val"] == "mono" else BG_INPUT, height=36, expand=True)
            style_btns = {"normal": s_norm, "bold": s_bold, "mono": s_mono}

            pos_first_btn, _ = make_btn("کنار اسم (First Name)", lambda e: select_pos(e, "first"), bgcolor=RED_PRIMARY if style_state["pos"] == "first" else BG_INPUT, height=36, expand=True)
            pos_last_btn, _ = make_btn("کنار فامیل (Last Name)", lambda e: select_pos(e, "last"), bgcolor=RED_PRIMARY if style_state["pos"] == "last" else BG_INPUT, height=36, expand=True)

            async def fetch_current_name(e):
                try:
                    async with client_lock:
                        await ensure_online(c)
                        me = await asyncio.wait_for(c.get_me(), timeout=8.0)
                    bf = strip_clock_suffix(getattr(me, "first_name", "") or "")
                    bl = strip_clock_suffix(getattr(me, "last_name", "") or "")
                    base_first_box.value = bf
                    base_last_box.value = bl
                    clock_cfg["base_first"] = bf
                    clock_cfg["base_last"] = bl
                    save_clock_config(clock_cfg)
                    log(f"نام فعلی پروفایل دریافت شد: {bf} {bl}".strip(), "#10B981")
                    safe_page_update()
                except Exception as ex:
                    log(f"خطا در دریافت نام پروفایل: {ex}", RED_NEON)

            async def save_and_apply_clock(e):
                enabled = bool(clock_toggle_state["val"])
                keep_bg = bool(bg_keep_clock_state["val"])
                bf = strip_clock_suffix(base_first_box.value or "")
                bl = strip_clock_suffix(base_last_box.value or "")

                if not bf and not bl:
                    try:
                        async with client_lock:
                            await ensure_online(c)
                            me = await asyncio.wait_for(c.get_me(), timeout=8.0)
                        bf = strip_clock_suffix(getattr(me, "first_name", "") or "")
                        bl = strip_clock_suffix(getattr(me, "last_name", "") or "")
                        base_first_box.value = bf
                        base_last_box.value = bl
                    except Exception:
                        pass

                clock_cfg["enabled"] = enabled
                clock_cfg["bg_keep_alive"] = keep_bg
                clock_cfg["base_first"] = bf
                clock_cfg["base_last"] = bl
                clock_cfg["style"] = style_state["val"]
                clock_cfg["target_field"] = style_state["pos"]
                clock_cfg["sep"] = (sep_box.value or "|").strip()
                save_clock_config(clock_cfg)
                set_android_wakelock(keep_bg)
                st["last_clock_min"] = ""

                if enabled:
                    async with client_lock:
                        await sync_profile_clock(force=True)
                    log("ساعت افق تهران فعال شد و هر دقیقه آپدیت می‌شود ⏰✅", "#10B981")
                else:
                    try:
                        async with client_lock:
                            await ensure_online(c)
                            await apply_profile_name(c, bf or "User", bl)
                        log("ساعت غیرفعال شد و نام پروفایل به حالت عادی برگشت ✅", RED_LIGHT)
                    except Exception as ex:
                        log(f"خطا در بازگردانی نام: {ex}", RED_NEON)
                safe_page_update()

            get_name_btn, _ = make_btn("📥 خواندن اسم فعلی من", fetch_current_name, bgcolor=RED_DARK, height=40)
            apply_clk_btn, _ = make_btn("💾 ذخیره و اعمال تنظیمات ساعت", save_and_apply_clock, bgcolor=RED_PRIMARY, height=46)

            return ft.Container(
                bgcolor=BG_CARD,
                padding=14,
                border_radius=ft.BorderRadius.all(12),
                border=ft.Border.all(1, BORDER_CRIMSON),
                content=ft.Column(
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("⏰ ساعت افق تهران کنار اسم", size=16, weight=ft.FontWeight.BOLD, color=TEXT_WHITE),
                        live_time_txt,
                        clock_toggle_card,
                        bg_keep_clock_card,
                        get_name_btn,
                        base_first_box,
                        base_last_box,
                        sep_box,
                        ft.Text("فونت نمایش ساعت:", size=12, color=TEXT_MUTED),
                        ft.Row(spacing=6, controls=[s_norm, s_bold, s_mono]),
                        ft.Text("محل قرارگیری ساعت:", size=12, color=TEXT_MUTED),
                        ft.Row(spacing=6, controls=[pos_first_btn, pos_last_btn]),
                        apply_clk_btn,
                    ],
                ),
            )

        def render_body():
            body_host.controls.clear()
            tab = st["active_tab"]
            if tab == "chats":
                body_host.controls.append(build_chats_widget())
            elif tab == "multi":
                body_host.controls.append(build_multi_msg_widget())
            elif tab == "turbo":
                body_host.controls.append(build_turbo_widget())
            elif tab == "forward":
                body_host.controls.append(build_forward_widget())
            elif tab == "autoreply":
                body_host.controls.append(build_autoreply_widget())
            elif tab == "clock":
                body_host.controls.append(build_clock_widget())

        def switch_tab(e, tab_name: str):
            if st["active_tab"] == tab_name:
                return
            st["active_tab"] = tab_name
            for k, btn_ctrl in nav_buttons.items():
                btn_ctrl.bgcolor = RED_PRIMARY if k == tab_name else BG_INPUT
            render_body()
            safe_page_update()

        async def logout(e):
            st["in_dashboard"] = False
            st["turbo_running"] = False
            st["multi_running"] = False
            st["fwd_running"] = False
            clock_cfg["enabled"] = False
            save_clock_config(clock_cfg)
            autoreply_cfg["enabled"] = False
            save_autoreply_config(autoreply_cfg)
            set_android_wakelock(False)
            try:
                await c.log_out()
            except Exception:
                try:
                    await c.disconnect()
                except Exception:
                    pass
            st["client"] = None
            st["me_id"] = None
            st["entity_cache"].clear()
            base = os.path.basename(SESSION_PATH)
            for f in os.listdir(STORAGE_DIR):
                if f.startswith(base):
                    try:
                        os.remove(os.path.join(STORAGE_DIR, f))
                    except Exception:
                        pass
            show_phone("از حساب خارج شدید.")

        out_btn, _ = make_btn("خروج", logout, color=RED_NEON, kind="text")
        b_chats, _ = make_btn("💬 چت‌ها", lambda e: switch_tab(e, "chats"), bgcolor=RED_PRIMARY, height=38, expand=True)
        b_multi, _ = make_btn("📨 چندتایی", lambda e: switch_tab(e, "multi"), bgcolor=BG_INPUT, height=38, expand=True)
        b_turbo, _ = make_btn("🚀 توربو", lambda e: switch_tab(e, "turbo"), bgcolor=BG_INPUT, height=38, expand=True)
        b_fwd, _ = make_btn("📢 فوروارد", lambda e: switch_tab(e, "forward"), bgcolor=BG_INPUT, height=38, expand=True)
        b_auto, _ = make_btn("🤖 پی‌وی خودکار", lambda e: switch_tab(e, "autoreply"), bgcolor=BG_INPUT, height=38, expand=True)
        b_clock, _ = make_btn("⏰ ساعت", lambda e: switch_tab(e, "clock"), bgcolor=BG_INPUT, height=38, expand=True)
        nav_buttons = {
            "chats": b_chats,
            "multi": b_multi,
            "turbo": b_turbo,
            "forward": b_fwd,
            "autoreply": b_auto,
            "clock": b_clock,
        }

        render_body()

        page.add(
            ft.Container(
                bgcolor=BG_CARD,
                padding=14,
                border_radius=ft.BorderRadius.all(14),
                border=ft.Border.all(1.2, BORDER_ACTIVE),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(spacing=8, controls=[
                            ft.Text("⚡ V3X Selfbot", size=18, weight=ft.FontWeight.BOLD, color=RED_NEON),
                            conn_badge,
                        ]),
                        out_btn,
                    ],
                ),
            ),
            ft.Row(spacing=5, controls=[b_chats, b_multi, b_turbo]),
            ft.Row(spacing=5, controls=[b_fwd, b_auto, b_clock]),
            body_host,
            ft.Container(
                bgcolor=BG_CARD,
                padding=12,
                border_radius=ft.BorderRadius.all(12),
                border=ft.Border.all(1, BORDER_CRIMSON),
                content=ft.Column(
                    spacing=6,
                    controls=[
                        ft.Text("📜 گزارش زنده عملکرد", size=13, color=RED_LIGHT),
                        logs,
                    ],
                ),
            ),
            creator_footer(),
        )
        safe_page_update()
        asyncio.create_task(fetch_dialogs_list())

    saved = get_saved_license()
    if saved:
        status, m, _, upd_url = await check_license(saved, did)
        if status == "OUTDATED":
            show_update_required(m, upd_url)
            return
        if status == "OK":
            await proceed_after_license()
            return
        clear_saved_license()
        show_license(m)
        return
    show_license()


if hasattr(ft, "run"):
    ft.run(main)
else:
    ft.app(target=main)
