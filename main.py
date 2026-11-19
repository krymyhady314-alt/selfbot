import asyncio, datetime, hashlib, importlib, inspect, json, os, pkgutil, platform, re, subprocess, tempfile, time
import flet as ft
import httpx

# لایه سازگاری کامل با Flet 1.1.2
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

APP_VERSION = "2.0.0"
DEFAULT_UPDATE_URL = "https://github.com/krymyhady314-alt/selfbot/releases/latest/download/V3X-Selfbot.apk"
LICENSE_URL = "https://selfbot-license.krymyhady314.workers.dev"
CREATOR_ID = "@V3XSYS"

TEHRAN_TZ = datetime.timezone(datetime.timedelta(hours=3, minutes=30))

STORAGE_DIR = os.getenv("FLET_APP_STORAGE_DATA") or tempfile.gettempdir()
os.makedirs(STORAGE_DIR, exist_ok=True)

DEV_FILE = os.path.join(STORAGE_DIR, "v3x_dev.txt")
LIC_FILE = os.path.join(STORAGE_DIR, "v3x_lic.json")
SESSION_PATH = os.path.join(STORAGE_DIR, "v3x_splus")
SAVED_MSGS_FILE = os.path.join(STORAGE_DIR, "v3x_saved_msgs.json")
CLOCK_CFG_FILE = os.path.join(STORAGE_DIR, "v3x_clock_cfg.json")


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
        "style": "bold",  # normal | bold | mono | circle
        "target_field": "first",  # first | last
        "sep": "|",
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
    txt = re.sub(r"\s*[\|•\-–—]?\s*[0-9𝟎-𝟗𝟶-𝟿⓪-⑨]{2}:[0-9𝟎-𝟗𝟶-𝟿⓪-⑨]{2}\s*$", "", txt)
    return txt.strip()


def extract_clean_key(raw_input: str) -> str:
    txt = (raw_input or "").strip().replace("`", "").replace('"', "").replace("'", "")
    m = re.search(r"(V3X-[A-Za-z0-9\-_]{3,})", txt, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return txt


async def check_license(raw_key: str, did: str) -> tuple[str, str, str, str]:
    """خروجی: (وضعیت: OK | OUTDATED | ERROR, پیام, کلید تمیز, لینک آپدیت)"""
    clean_key = extract_clean_key(raw_key)
    if not clean_key:
        return "ERROR", "لطفاً کلید لایسنس را وارد کنید.", "", DEFAULT_UPDATE_URL

    payload = {
        "action": "verify",
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
    last_err = "پاسخی از سرور لایسنس دریافت نشد. اتصال اینترنت را بررسی کنید."

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

                # بررسی اجباری بودن آپدیت و غیرفعال‌سازی نسخه قدیمی
                if (
                    d.get("force_update") is True
                    or d.get("outdated") is True
                    or status_val in ("outdated", "update_required", "deprecated", "disabled")
                    or (min_ver and parse_version_tuple(APP_VERSION) < parse_version_tuple(min_ver))
                ):
                    msg = d.get("message") or f"نسخه فعلی ({APP_VERSION}) غیرفعال شده است. لطفاً نسخه جدید ({min_ver or 'جدید'}) را نصب کنید."
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
            except Exception as e:
                last_err = f"خطای اتصال به سرور لایسنس: {e}"

    if saw_only_online:
        return "ERROR", "سرور کلودفلر آنلاین است اما مسیر بررسی لایسنس (/verify) در Worker پاسخ نداد.", clean_key, DEFAULT_UPDATE_URL

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
    """به‌روزرسانی نام پروفایل سروش‌پلاس با سازگاری کامل با تمام متدهای splusthon."""
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


def make_btn(label: str, on_click, bgcolor: str = "#2563EB", color: str = "#FFFFFF", height: int = 44, kind: str = "filled", expand: bool = False):
    lbl = ft.Text(label, color=color, weight=ft.FontWeight.W_600, size=12)
    if kind == "outlined":
        btn_cls = getattr(ft, "OutlinedButton", ft.Button)
        return btn_cls(content=lbl, on_click=on_click, height=height, expand=expand), lbl
    if kind == "text":
        btn_cls = getattr(ft, "TextButton", ft.Button)
        return btn_cls(content=lbl, on_click=on_click, expand=expand), lbl
    btn_cls = getattr(ft, "Button", None) or getattr(ft, "ElevatedButton", None)
    return btn_cls(content=lbl, bgcolor=bgcolor, color=color, height=height, on_click=on_click, expand=expand), lbl


def creator_footer():
    return ft.Container(
        margin=ft.Margin.only(top=8),
        padding=ft.Padding.symmetric(vertical=10, horizontal=14),
        border_radius=ft.BorderRadius.all(10),
        bgcolor="#0F172A",
        border=ft.Border.all(1, "#1E293B"),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Text(f"نسخه {APP_VERSION}  |  طراحی و توسعه: ", size=12, color="#94A3B8"),
                ft.Text(CREATOR_ID, size=13, weight=ft.FontWeight.BOLD, color="#38BDF8", selectable=True),
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
    page.bgcolor = "#0B1120"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 14
    page.scroll = ft.ScrollMode.AUTO
    page.rtl = True

    did = get_device_id()
    clock_cfg = load_clock_config()

    st = {
        "client": None,
        "phone": "",
        "hash": None,
        "need_2fa": False,
        "watchdog_started": False,
        "clock_worker_started": False,
        "last_clock_min": "",
        "in_dashboard": False,
        "active_tab": "chats",  # chats | multi | turbo | clock
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
    }
    logs = ft.Column(spacing=4, height=110, scroll=ft.ScrollMode.AUTO)
    conn_badge = ft.Text("🟢 متصل", size=12, color="#10B981", weight=ft.FontWeight.W_600)

    def safe_page_update():
        try:
            page.update()
        except Exception:
            pass

    def log(txt: str, col: str = "#94A3B8"):
        logs.controls.insert(0, ft.Text(f"[{time.strftime('%H:%M:%S')}] {txt}", size=12, color=col))
        logs.controls = logs.controls[:25]
        safe_page_update()

    def get_client():
        if st["client"] is None:
            st["client"] = create_splus_client()
        return st["client"]

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
            conn_badge.value = "🟢 متصل"
            conn_badge.color = "#10B981"
            return True
        except Exception:
            conn_badge.value = "🔴 قطع اتصال"
            conn_badge.color = "#EF4444"
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
        """ارسال فوق‌سریع بدون تاخیر اضافی همراه با مدیریت خودکار خطا و FloodWait."""
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

    def on_lifecycle_change(e):
        try:
            state_str = str(getattr(e, "state", "")).lower()
            if "resume" in state_str and st["in_dashboard"] and st["client"] is not None:
                asyncio.create_task(ensure_online(st["client"]))
                safe_page_update()
        except Exception:
            pass

    try:
        page.on_app_lifecycle_state_change = on_lifecycle_change
    except Exception:
        pass

    # ==========================================
    # صفحه توقف نسخه قدیمی (Force Update)
    # ==========================================
    def show_update_required(msg: str, update_url: str):
        st["in_dashboard"] = False
        page.controls.clear()
        url_box = ft.TextField(
            label="لینک دانلود مستقیم نسخه جدید",
            value=update_url,
            read_only=True,
            text_align=ft.TextAlign.LEFT,
            bgcolor="#0F172A",
        )
        copy_stat = ft.Text("", size=12, color="#10B981")

        async def open_dl(e):
            try:
                if hasattr(page, "launch_url"):
                    r = page.launch_url(update_url)
                    if inspect.isawaitable(r):
                        await r
            except Exception:
                pass
            try:
                if hasattr(ft, "Clipboard"):
                    await ft.Clipboard().set(update_url)
                copy_stat.value = "لینک دانلود کپی شد؛ در مرورگر باز کنید ✅"
            except Exception:
                copy_stat.value = "لینک بالا را کپی و در مرورگر باز کنید."
            safe_page_update()

        dl_btn, _ = make_btn("⬇️ دانلود نسخه جدید برنامه", open_dl, bgcolor="#10B981", height=48)
        page.add(
            ft.Container(
                bgcolor="#111827",
                padding=20,
                border_radius=ft.BorderRadius.all(12),
                border=ft.Border.all(1.5, "#EF4444"),
                content=ft.Column(
                    spacing=14,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("⚠️ این نسخه غیرفعال شده است", size=20, weight=ft.FontWeight.BOLD, color="#EF4444"),
                        ft.Text(msg, size=14, color="#F8FAFC"),
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
        dev_box = ft.TextField(label="شناسه سخت‌افزاری دستگاه (Device ID)", value=did, read_only=True, text_align=ft.TextAlign.LEFT, bgcolor="#0F172A")
        key_box = ft.TextField(label="کلید لایسنس", value=get_saved_license(), hint_text="V3X-XXXX-XXXX", text_align=ft.TextAlign.LEFT, bgcolor="#1E293B")

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
            info.value, info.color = "در حال استعلام لایسنس و بررسی نسخه...", "#38BDF8"
            safe_page_update()
            status, m, clean_k, upd_url = await check_license(key_box.value or "", did)
            btn.disabled = False
            if status == "OUTDATED":
                show_update_required(m, upd_url)
                return
            if status != "OK":
                info.value, info.color = f"❌ {m}", "#EF4444"
                safe_page_update()
                return
            save_license(clean_k)
            await proceed_after_license()

        btn, _ = make_btn("بررسی لایسنس و ورود", verify, bgcolor="#2563EB", height=48)
        copy_btn, _ = make_btn("📋 کپی شناسه دستگاه", copy_id, color="#38BDF8", kind="outlined")

        page.add(
            ft.Container(
                bgcolor="#111827",
                padding=18,
                border_radius=ft.BorderRadius.all(12),
                border=ft.Border.all(1, "#1E293B"),
                content=ft.Column(
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("V3X SELFBOT", size=22, weight=ft.FontWeight.BOLD, color="#38BDF8"),
                        ft.Text(f"نسخه {APP_VERSION}  |  فعال‌سازی لایسنس", size=13, color="#94A3B8"),
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
        ph_box = ft.TextField(label="شماره موبایل سروش‌پلاس", hint_text="09123456789", keyboard_type=ft.KeyboardType.PHONE, text_align=ft.TextAlign.LEFT, bgcolor="#1E293B")

        async def send_otp(e):
            d = "".join(c for c in (ph_box.value or "") if c.isdigit())
            if d.startswith("09") and len(d) == 11:
                p98, p09 = "98" + d[1:], d
            elif d.startswith("989") and len(d) == 12:
                p98, p09 = d, "0" + d[2:]
            elif d.startswith("9") and len(d) == 10:
                p98, p09 = "98" + d, "0" + d
            else:
                info.value, info.color = "شماره موبایل معتبر وارد کنید (مثلاً 09123456789).", "#EF4444"
                safe_page_update()
                return

            btn.disabled = True
            info.value, info.color = "در حال ارسال کد تایید...", "#38BDF8"
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
                info.value, info.color = f"خطا: {ex}", "#EF4444"
                safe_page_update()

        btn, _ = make_btn("ارسال کد تایید", send_otp, bgcolor="#10B981", height=48)
        page.add(
            ft.Container(
                bgcolor="#111827",
                padding=18,
                border_radius=ft.BorderRadius.all(12),
                border=ft.Border.all(1, "#1E293B"),
                content=ft.Column(
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("ورود به سروش‌پلاس", size=20, weight=ft.FontWeight.BOLD),
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
        info = ft.Text(f"کد تایید به {st['phone']} ارسال شد.", size=13, color="#38BDF8")
        code_box = ft.TextField(label="کد تایید", hint_text="12345", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor="#1E293B")
        pwd_box = ft.TextField(label="رمز تایید دومرحله‌ای (در صورت داشتن)", password=True, can_reveal_password=True, visible=st["need_2fa"], text_align=ft.TextAlign.LEFT, bgcolor="#1E293B")

        async def confirm(e):
            code = (code_box.value or "").strip()
            pwd = (pwd_box.value or "").strip()
            if not st["need_2fa"] and len(code) < 4:
                info.value, info.color = "کد تایید را کامل وارد کنید.", "#EF4444"
                safe_page_update()
                return
            btn.disabled = True
            info.value, info.color = "در حال ورود...", "#38BDF8"
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
                    info.value, info.color = f"خطا: {ex}", "#EF4444"
                safe_page_update()

        btn, _ = make_btn("تایید و ورود", confirm, bgcolor="#2563EB", height=48)
        chg_btn, _ = make_btn("تغییر شماره", lambda e: show_phone(), color="#94A3B8", kind="text")
        page.add(
            ft.Container(
                bgcolor="#111827",
                padding=18,
                border_radius=ft.BorderRadius.all(12),
                border=ft.Border.all(1, "#1E293B"),
                content=ft.Column(
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("تایید کد", size=20, weight=ft.FontWeight.BOLD),
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
    # صفحه ۴: داشبورد کامل سلف‌بات
    # ==========================================
    def show_dashboard():
        st["in_dashboard"] = True
        page.controls.clear()
        c = get_client()
        log("سلف‌بات با موفقیت به سروش‌پلاس متصل شد ✅", "#10B981")

        async def sync_profile_clock(force: bool = False):
            """به‌روزرسانی خودکار ساعت افق تهران کنار اسم پروفایل هر دقیقه."""
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
                log(f"ساعت پروفایل آپدیت شد: {new_first} {new_last}".strip(), "#38BDF8")
            except Exception as ex:
                log(f"خطا در آپدیت ساعت پروفایل: {ex}", "#EF4444")

        async def connection_and_clock_watchdog():
            while st["in_dashboard"]:
                try:
                    await ensure_online(c)
                    if clock_cfg.get("enabled"):
                        await sync_profile_clock(force=False)
                except Exception:
                    pass
                await asyncio.sleep(2.5)

        if not st["watchdog_started"]:
            st["watchdog_started"] = True
            asyncio.create_task(connection_and_clock_watchdog())

        body_host = ft.Column(spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        on_dialogs_loaded_callback = None

        async def fetch_dialogs_list():
            items = []
            try:
                await ensure_online(c)
                raw_dialogs = []
                if callable(getattr(c, "get_dialogs", None)):
                    raw_dialogs = await asyncio.wait_for(c.get_dialogs(limit=60), timeout=12.0)
                elif callable(getattr(c, "iter_dialogs", None)):
                    async for d in c.iter_dialogs(limit=60):
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
                    is_group = getattr(d, "is_group", None) or getattr(d, "is_channel", None)

                    cid_str = str(cid)
                    if is_user is True or cid_str.startswith("u0") or (isinstance(cid, int) and cid > 0 and not is_group):
                        kind = "pv"
                    else:
                        kind = "group"

                    items.append({"id": cid_str, "title": str(title), "kind": kind})
            except Exception as ex:
                log(f"خطا در دریافت لیست چت‌ها: {ex}", "#EF4444")
            st["dialogs"] = items
            if callable(on_dialogs_loaded_callback):
                on_dialogs_loaded_callback()

        async def fetch_recent_messages(raw_target: str):
            msgs = []
            tgt_str = (raw_target or "").strip()
            if not tgt_str:
                st["recent_messages"] = []
                return
            try:
                await ensure_online(c)
                peer = await resolve_peer(c, tgt_str)
                raw_msgs = []
                if callable(getattr(c, "get_messages", None)):
                    raw_msgs = await asyncio.wait_for(c.get_messages(peer, limit=25), timeout=12.0)
                elif callable(getattr(c, "iter_messages", None)):
                    async for m in c.iter_messages(peer, limit=25):
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
                log(f"خطا در دریافت پیام‌های اخیر: {ex}", "#EF4444")
            st["recent_messages"] = msgs

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

            clr_b, _ = make_btn("✖️ لغو", clear_rep, color="#EF4444", kind="text")
            preview = st["reply_to_preview"]
            if len(preview) > 40:
                preview = preview[:40] + "..."
            return ft.Container(
                padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                border_radius=ft.BorderRadius.all(8),
                bgcolor="#0F172A",
                border=ft.Border.all(1, "#10B981"),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(f"↩️ ریپلای روی #{st['reply_to_id']}: {preview}", size=12, color="#10B981", expand=True),
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
                bgcolor="#1E293B",
                on_change=lambda e: set_active_target_clean(e.control.value or ""),
            )
            chat_list_col = ft.Column(spacing=6, height=175, scroll=ft.ScrollMode.AUTO)
            recent_msgs_col = ft.Column(spacing=6, height=210, scroll=ft.ScrollMode.AUTO)
            selected_count_lbl = ft.Text(f"چت‌های انتخاب‌شده برای ارسال گروهی: {len(st['selected_targets'])}", size=12, color="#38BDF8")
            reply_banner_holder = ft.Column(controls=[build_reply_status_banner(lambda: refresh_recent_msg_cards())])

            def rebuild_reply_banner():
                reply_banner_holder.controls = [build_reply_status_banner(lambda: refresh_recent_msg_cards())]

            def select_message_for_reply(e, mid, mtext):
                st["reply_to_id"] = mid
                st["reply_to_preview"] = mtext
                st["reply_chat_id"] = st["active_target"]
                rebuild_reply_banner()
                refresh_recent_msg_cards()
                log(f"پیام #{mid} برای ریپلای انتخاب شد ↩️", "#10B981")
                safe_page_update()

            def refresh_recent_msg_cards():
                recent_msgs_col.controls.clear()
                if not st["recent_messages"]:
                    recent_msgs_col.controls.append(
                        ft.Text("پیامی بارگذاری نشده است. روی یک پی‌وی/گپ بزنید یا دکمه پیام‌های اخیر را بزنید.", size=12, color="#94A3B8")
                    )
                    return

                for m in st["recent_messages"]:
                    mid = m["id"]
                    is_rep_selected = st["reply_to_id"] == mid
                    card = ft.Container(
                        padding=ft.Padding.all(10),
                        border_radius=ft.BorderRadius.all(8),
                        bgcolor="#1E293B" if is_rep_selected else "#0F172A",
                        border=ft.Border.all(1.5 if is_rep_selected else 1, "#10B981" if is_rep_selected else "#334155"),
                        on_click=lambda e, m_id=mid, m_txt=m["text"]: select_message_for_reply(e, m_id, m_txt),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Column(
                                    spacing=2,
                                    expand=True,
                                    controls=[
                                        ft.Text(f"{m['sender']}  (#{mid})", size=11, color="#38BDF8", weight=ft.FontWeight.W_600),
                                        ft.Text(m["text"], size=13, color="#F8FAFC", max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                                    ],
                                ),
                                ft.Text("↩️ انتخاب‌شده" if is_rep_selected else "ریپلای", size=12, color="#10B981" if is_rep_selected else "#94A3B8"),
                            ],
                        ),
                    )
                    recent_msgs_col.controls.append(card)

            async def load_msgs_for_current_target(e=None):
                tgt = (manual_target.value or st["active_target"] or "").strip()
                if not tgt:
                    log("ابتدا یک چت را انتخاب کنید یا آیدی آن را وارد کنید.", "#EF4444")
                    return
                set_active_target_clean(tgt)
                log(f"در حال دریافت پیام‌های اخیر {tgt}...", "#38BDF8")
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
                filtered = [x for x in st["dialogs"] if flt == "all" or x["kind"] == flt]
                if not filtered:
                    chat_list_col.controls.append(
                        ft.Text("چتی یافت نشد. دکمه بروزرسانی چت‌ها را بزنید.", size=12, color="#94A3B8")
                    )
                    return

                for item in filtered:
                    cid = item["id"]
                    title = item["title"]
                    is_pv = item["kind"] == "pv"
                    selected = cid in st["selected_targets"] or st["active_target"] == cid
                    badge = "👤 پی‌وی" if is_pv else "👥 گپ"
                    card = ft.Container(
                        padding=ft.Padding.all(10),
                        border_radius=ft.BorderRadius.all(10),
                        bgcolor="#1E293B" if selected else "#0F172A",
                        border=ft.Border.all(1.5 if selected else 1, "#38BDF8" if selected else "#1E293B"),
                        on_click=lambda e, c_id=cid, c_title=title: page.run_task(on_chat_card_click, e, c_id, c_title),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Column(
                                    spacing=2,
                                    expand=True,
                                    controls=[
                                        ft.Text(title, size=14, weight=ft.FontWeight.W_600, color="#F8FAFC"),
                                        ft.Text(f"{badge}  |  ID: {cid}", size=11, color="#94A3B8"),
                                    ],
                                ),
                                ft.Text("✅ انتخاب" if selected else "انتخاب", size=12, color="#10B981" if selected else "#64748B"),
                            ],
                        ),
                    )
                    chat_list_col.controls.append(card)

            def set_filter(e, mode: str):
                st["chat_filter"] = mode
                f_all.bgcolor = "#2563EB" if mode == "all" else "#1E293B"
                f_pv.bgcolor = "#2563EB" if mode == "pv" else "#1E293B"
                f_gp.bgcolor = "#2563EB" if mode == "group" else "#1E293B"
                refresh_chat_cards()
                safe_page_update()

            async def reload_chats(e):
                log("در حال دریافت لیست پی‌وی‌ها و گپ‌ها...", "#38BDF8")
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

            f_all, _ = make_btn("همه", lambda e: set_filter(e, "all"), bgcolor="#2563EB" if st["chat_filter"] == "all" else "#1E293B", height=36, expand=True)
            f_pv, _ = make_btn("👤 پی‌وی", lambda e: set_filter(e, "pv"), bgcolor="#2563EB" if st["chat_filter"] == "pv" else "#1E293B", height=36, expand=True)
            f_gp, _ = make_btn("👥 گپ‌ها", lambda e: set_filter(e, "group"), bgcolor="#2563EB" if st["chat_filter"] == "group" else "#1E293B", height=36, expand=True)
            rel_btn, _ = make_btn("🔄 بروزرسانی چت‌ها", reload_chats, bgcolor="#10B981", height=40, expand=True)
            load_msg_btn, _ = make_btn("📜 پیام‌های اخیر", load_msgs_for_current_target, bgcolor="#2563EB", height=40, expand=True)
            clr_btn, _ = make_btn("پاک کردن", clear_selected, color="#EF4444", kind="text")

            refresh_chat_cards()
            refresh_recent_msg_cards()

            return ft.Column(
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.Container(
                        bgcolor="#111827",
                        padding=14,
                        border_radius=ft.BorderRadius.all(12),
                        border=ft.Border.all(1, "#1E293B"),
                        content=ft.Column(
                            spacing=10,
                            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                            controls=[
                                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                                    ft.Text("💬 انتخاب پی‌وی یا گپ", size=16, weight=ft.FontWeight.BOLD),
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
                        bgcolor="#111827",
                        padding=14,
                        border_radius=ft.BorderRadius.all(12),
                        border=ft.Border.all(1, "#1E293B"),
                        content=ft.Column(
                            spacing=8,
                            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                            controls=[
                                ft.Text("📜 پیام‌های اخیر چت (برای ریپلای لمس کنید)", size=14, weight=ft.FontWeight.BOLD, color="#38BDF8"),
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
                bgcolor="#1E293B",
                on_change=lambda e: set_active_target_clean(e.control.value or ""),
            )
            use_multi_targets = ft.Switch(
                label=f"ارسال همزمان به تمام چت‌های تیک‌خورده ({len(st['selected_targets'])} چت)",
                value=len(st["selected_targets"]) > 1,
            )
            new_msg_input = ft.TextField(
                label="متن پیام جدید برای افزودن به لیست",
                hint_text="متن پیام را بنویسید...",
                bgcolor="#1E293B",
            )
            rounds_box = ft.TextField(
                label="تعداد دور ارسال کل لیست",
                value="1",
                keyboard_type=ft.KeyboardType.NUMBER,
                text_align=ft.TextAlign.LEFT,
                bgcolor="#1E293B",
                expand=True,
            )
            delay_box = ft.TextField(
                label="تاخیر (0 = حداکثر سرعت)",
                value="0",
                keyboard_type=ft.KeyboardType.NUMBER,
                text_align=ft.TextAlign.LEFT,
                bgcolor="#1E293B",
                expand=True,
            )
            m_stat = ft.Text("آماده ارسال چندتایی", size=12, color="#94A3B8")
            msg_items_col = ft.Column(spacing=6)

            def remove_msg_item(e, index: int):
                if 0 <= index < len(st["multi_messages"]):
                    st["multi_messages"].pop(index)
                    render_msg_items()
                    safe_page_update()

            def render_msg_items():
                msg_items_col.controls.clear()
                if not st["multi_messages"]:
                    msg_items_col.controls.append(ft.Text("لیست پیام‌های چندتایی خالی است.", size=12, color="#94A3B8"))
                    return
                for idx, txt in enumerate(st["multi_messages"]):
                    del_btn, _ = make_btn("حذف", lambda e, i=idx: remove_msg_item(e, i), color="#EF4444", kind="text")
                    row_card = ft.Container(
                        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                        border_radius=ft.BorderRadius.all(8),
                        bgcolor="#0F172A",
                        border=ft.Border.all(1, "#334155"),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(f"{idx + 1}. {txt}", size=13, color="#F8FAFC", expand=True),
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
                    log("لیست پیام‌ها خالی است؛ پیامی برای ذخیره وجود ندارد.", "#EF4444")
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
                if use_multi_targets.value and st["selected_targets"]:
                    targets = list(st["selected_targets"].keys())
                elif (target_field.value or "").strip():
                    targets = [(target_field.value or "").strip()]

                if not targets:
                    log("ابتدا یک پی‌وی/گپ انتخاب کنید یا آیدی مقصد را وارد کنید.", "#EF4444")
                    st["multi_running"] = False
                    m_lbl.value = "🚀 شروع ارسال چندتایی"
                    m_btn.bgcolor = "#10B981"
                    safe_page_update()
                    return

                messages = list(st["multi_messages"])
                total_ops = rounds * len(targets) * len(messages)
                done = 0
                last_ui_tick = 0.0

                try:
                    await ensure_online(c)
                    resolved_peers = {}
                    for t_raw in targets:
                        resolved_peers[t_raw] = await resolve_peer(c, t_raw)

                    # ساخت صف کامل عملیات
                    queue = []
                    for _ in range(rounds):
                        for raw_t in targets:
                            rep_id = st["reply_to_id"] if (st["reply_to_id"] and st["reply_chat_id"] == raw_t) else None
                            for m_txt in messages:
                                queue.append((raw_t, resolved_peers[raw_t], m_txt, rep_id))

                    if dly == 0:
                        # ارسال فوق‌سریع دسته‌ای (۵ پیام هم‌زمان در شبکه)
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
                    log(f"خطا در ارسال چندتایی: {ex}", "#EF4444")
                    m_stat.value = f"توقف در {done}/{total_ops}: {ex}"
                    m_stat.color = "#EF4444"
                finally:
                    st["multi_running"] = False
                    m_lbl.value = "🚀 شروع ارسال چندتایی"
                    m_btn.bgcolor = "#10B981"
                    safe_page_update()

            async def toggle_multi(e):
                if st["multi_running"]:
                    st["multi_running"] = False
                    return
                if st["turbo_running"]:
                    log("ابتدا ارسال توربو را متوقف کنید.", "#F59E0B")
                    return
                if not st["multi_messages"]:
                    log("حداقل یک پیام به لیست چندتایی اضافه کنید.", "#EF4444")
                    return
                st["multi_running"] = True
                m_lbl.value = "⛔ توقف ارسال چندتایی"
                m_btn.bgcolor = "#EF4444"
                safe_page_update()
                asyncio.create_task(run_multi_sender())

            add_btn, _ = make_btn("➕ افزودن به لیست", add_msg_item, bgcolor="#2563EB", height=40, expand=True)
            save_msgs_btn, _ = make_btn("💾 ذخیره پیام‌ها (پیش‌فرض)", save_messages_as_default, bgcolor="#0284C7", height=40, expand=True)
            m_btn, m_lbl = make_btn("🚀 شروع ارسال چندتایی", toggle_multi, bgcolor="#10B981", height=46)
            render_msg_items()

            return ft.Container(
                bgcolor="#111827",
                padding=14,
                border_radius=ft.BorderRadius.all(12),
                border=ft.Border.all(1, "#1E293B"),
                content=ft.Column(
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("📨 ارسال چندتایی (Multi-Message)", size=16, weight=ft.FontWeight.BOLD),
                        build_reply_status_banner(),
                        target_field,
                        use_multi_targets,
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
                bgcolor="#1E293B",
                on_change=lambda e: set_active_target_clean(e.control.value or ""),
            )
            msg_box = ft.TextField(label="متن پیام توربو", bgcolor="#1E293B")
            cnt_box = ft.TextField(label="تعداد", value="20", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor="#1E293B", expand=True)
            dly_box = ft.TextField(label="تاخیر (0 = حداکثر سرعت)", value="0", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor="#1E293B", expand=True)
            t_stat = ft.Text("آماده", size=12, color="#94A3B8")

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
                    log(f"خطای توربو: {ex}", "#EF4444")
                    t_stat.value = f"توقف در {sent}/{total}: {ex}"
                    t_stat.color = "#EF4444"
                finally:
                    st["turbo_running"] = False
                    t_lbl.value = "🚀 شروع توربو"
                    t_btn.bgcolor = "#10B981"
                    safe_page_update()

            async def toggle_turbo(e):
                if st["turbo_running"]:
                    st["turbo_running"] = False
                    return
                if st["multi_running"]:
                    log("ابتدا ارسال چندتایی را متوقف کنید.", "#F59E0B")
                    return
                if not (target_box.value or "").strip() or not (msg_box.value or "").strip():
                    log("مقصد و متن را وارد کنید.", "#EF4444")
                    return
                st["turbo_running"] = True
                t_lbl.value = "⛔ توقف توربو"
                t_btn.bgcolor = "#EF4444"
                safe_page_update()
                asyncio.create_task(turbo_run())

            t_btn, t_lbl = make_btn("🚀 شروع توربو", toggle_turbo, bgcolor="#10B981", height=44)
            return ft.Container(
                bgcolor="#111827",
                padding=14,
                border_radius=ft.BorderRadius.all(12),
                border=ft.Border.all(1, "#1E293B"),
                content=ft.Column(
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("🚀 ارسال توربو فوق‌سریع", size=16, weight=ft.FontWeight.BOLD),
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
        # ویجت ۴: ساعت افق تهران کنار اسم پروفایل
        # ==========================================
        def build_clock_widget():
            cur_tehran = format_tehran_clock(clock_cfg.get("style", "bold"))
            live_time_txt = ft.Text(f"🕒 ساعت فعلی به افق تهران: {cur_tehran}", size=14, weight=ft.FontWeight.BOLD, color="#38BDF8")

            clock_check = ft.Checkbox(
                label="فعال‌سازی ساعت افق تهران کنار اسم پروفایل",
                value=bool(clock_cfg.get("enabled", False)),
            )
            base_first_box = ft.TextField(
                label="نام اصلی شما (بدون ساعت)",
                hint_text="اگر خالی بگذارید خودکار از پروفایل خوانده می‌شود",
                value=clock_cfg.get("base_first", ""),
                bgcolor="#1E293B",
            )
            base_last_box = ft.TextField(
                label="نام خانوادگی اصلی شما (اختیاری)",
                value=clock_cfg.get("base_last", ""),
                bgcolor="#1E293B",
            )
            sep_box = ft.TextField(
                label="جداکننده بین اسم و ساعت",
                value=clock_cfg.get("sep", "|"),
                bgcolor="#1E293B",
                expand=True,
            )

            style_state = {"val": clock_cfg.get("style", "bold"), "pos": clock_cfg.get("target_field", "first")}

            def select_style(e, s_val: str):
                style_state["val"] = s_val
                for k, b in style_btns.items():
                    b.bgcolor = "#2563EB" if k == s_val else "#1E293B"
                live_time_txt.value = f"🕒 پیش‌نمایش ساعت تهران: {format_tehran_clock(s_val)}"
                safe_page_update()

            def select_pos(e, p_val: str):
                style_state["pos"] = p_val
                pos_first_btn.bgcolor = "#2563EB" if p_val == "first" else "#1E293B"
                pos_last_btn.bgcolor = "#2563EB" if p_val == "last" else "#1E293B"
                safe_page_update()

            s_norm, _ = make_btn("ساده 14:30", lambda e: select_style(e, "normal"), bgcolor="#2563EB" if style_state["val"] == "normal" else "#1E293B", height=36, expand=True)
            s_bold, _ = make_btn("ضخیم 𝟏𝟒:𝟑𝟎", lambda e: select_style(e, "bold"), bgcolor="#2563EB" if style_state["val"] == "bold" else "#1E293B", height=36, expand=True)
            s_mono, _ = make_btn("فانتزی 𝟷𝟺:𝟹𝟶", lambda e: select_style(e, "mono"), bgcolor="#2563EB" if style_state["val"] == "mono" else "#1E293B", height=36, expand=True)
            style_btns = {"normal": s_norm, "bold": s_bold, "mono": s_mono}

            pos_first_btn, _ = make_btn("کنار اسم (First Name)", lambda e: select_pos(e, "first"), bgcolor="#2563EB" if style_state["pos"] == "first" else "#1E293B", height=36, expand=True)
            pos_last_btn, _ = make_btn("کنار فامیل (Last Name)", lambda e: select_pos(e, "last"), bgcolor="#2563EB" if style_state["pos"] == "last" else "#1E293B", height=36, expand=True)

            async def fetch_current_name(e):
                try:
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
                    log(f"خطا در دریافت نام پروفایل: {ex}", "#EF4444")

            async def save_and_apply_clock(e):
                enabled = bool(clock_check.value)
                bf = strip_clock_suffix(base_first_box.value or "")
                bl = strip_clock_suffix(base_last_box.value or "")

                if not bf and not bl:
                    try:
                        await ensure_online(c)
                        me = await asyncio.wait_for(c.get_me(), timeout=8.0)
                        bf = strip_clock_suffix(getattr(me, "first_name", "") or "")
                        bl = strip_clock_suffix(getattr(me, "last_name", "") or "")
                        base_first_box.value = bf
                        base_last_box.value = bl
                    except Exception:
                        pass

                clock_cfg["enabled"] = enabled
                clock_cfg["base_first"] = bf
                clock_cfg["base_last"] = bl
                clock_cfg["style"] = style_state["val"]
                clock_cfg["target_field"] = style_state["pos"]
                clock_cfg["sep"] = (sep_box.value or "|").strip()
                save_clock_config(clock_cfg)
                st["last_clock_min"] = ""

                if enabled:
                    await sync_profile_clock(force=True)
                    log("ساعت افق تهران فعال شد و هر دقیقه آپدیت می‌شود ⏰✅", "#10B981")
                else:
                    try:
                        await ensure_online(c)
                        await apply_profile_name(c, bf or "User", bl)
                        log("ساعت غیرفعال شد و نام پروفایل به حالت عادی برگشت ✅", "#38BDF8")
                    except Exception as ex:
                        log(f"خطا در بازگردانی نام: {ex}", "#EF4444")
                safe_page_update()

            get_name_btn, _ = make_btn("📥 خواندن اسم فعلی من", fetch_current_name, bgcolor="#1E293B", height=40)
            apply_clk_btn, _ = make_btn("💾 ذخیره و اعمال تنظیمات ساعت", save_and_apply_clock, bgcolor="#10B981", height=46)

            return ft.Container(
                bgcolor="#111827",
                padding=14,
                border_radius=ft.BorderRadius.all(12),
                border=ft.Border.all(1, "#1E293B"),
                content=ft.Column(
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("⏰ ساعت افق تهران کنار اسم", size=16, weight=ft.FontWeight.BOLD),
                        live_time_txt,
                        clock_check,
                        get_name_btn,
                        base_first_box,
                        base_last_box,
                        sep_box,
                        ft.Text("فونت نمایش ساعت:", size=12, color="#94A3B8"),
                        ft.Row(spacing=6, controls=[s_norm, s_bold, s_mono]),
                        ft.Text("محل قرارگیری ساعت:", size=12, color="#94A3B8"),
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
            elif tab == "clock":
                body_host.controls.append(build_clock_widget())

        def switch_tab(e, tab_name: str):
            st["active_tab"] = tab_name
            for k, btn_ctrl in nav_buttons.items():
                btn_ctrl.bgcolor = "#2563EB" if k == tab_name else "#1E293B"
            render_body()
            safe_page_update()

        async def logout(e):
            st["in_dashboard"] = False
            st["turbo_running"] = False
            st["multi_running"] = False
            try:
                await c.log_out()
            except Exception:
                try:
                    await c.disconnect()
                except Exception:
                    pass
            st["client"] = None
            st["entity_cache"].clear()
            base = os.path.basename(SESSION_PATH)
            for f in os.listdir(STORAGE_DIR):
                if f.startswith(base):
                    try:
                        os.remove(os.path.join(STORAGE_DIR, f))
                    except Exception:
                        pass
            show_phone("از حساب خارج شدید.")

        out_btn, _ = make_btn("خروج", logout, color="#EF4444", kind="text")
        b_chats, _ = make_btn("💬 چت‌ها", lambda e: switch_tab(e, "chats"), bgcolor="#2563EB", height=38, expand=True)
        b_multi, _ = make_btn("📨 چندتایی", lambda e: switch_tab(e, "multi"), bgcolor="#1E293B", height=38, expand=True)
        b_turbo, _ = make_btn("🚀 توربو", lambda e: switch_tab(e, "turbo"), bgcolor="#1E293B", height=38, expand=True)
        b_clock, _ = make_btn("⏰ ساعت", lambda e: switch_tab(e, "clock"), bgcolor="#1E293B", height=38, expand=True)
        nav_buttons = {"chats": b_chats, "multi": b_multi, "turbo": b_turbo, "clock": b_clock}

        render_body()

        page.add(
            ft.Container(
                bgcolor="#111827",
                padding=14,
                border_radius=ft.BorderRadius.all(12),
                border=ft.Border.all(1, "#1E293B"),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(spacing=8, controls=[
                            ft.Text("⚡ V3X Selfbot", size=18, weight=ft.FontWeight.BOLD, color="#38BDF8"),
                            conn_badge,
                        ]),
                        out_btn,
                    ],
                ),
            ),
            ft.Row(spacing=5, controls=[b_chats, b_multi, b_turbo, b_clock]),
            body_host,
            ft.Container(
                bgcolor="#0F172A",
                padding=12,
                border_radius=ft.BorderRadius.all(12),
                border=ft.Border.all(1, "#1E293B"),
                content=ft.Column(
                    spacing=6,
                    controls=[
                        ft.Text("📜 گزارش زنده عملکرد", size=13, color="#94A3B8"),
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
