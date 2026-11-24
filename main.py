import asyncio, datetime, hashlib, importlib, inspect, json, os, pkgutil, platform, re, subprocess, tempfile, time, urllib.request
import flet as ft
import httpx

if hasattr(ft, "border") and hasattr(ft, "Border") and not hasattr(ft.border, "all"):
    ft.border.all, ft.border.only, ft.border.symmetric = ft.Border.all, ft.Border.only, ft.Border.symmetric
if hasattr(ft, "padding") and hasattr(ft, "Padding") and not hasattr(ft.padding, "all"):
    ft.padding.all, ft.padding.only, ft.padding.symmetric = ft.Padding.all, ft.Padding.only, ft.Padding.symmetric
if hasattr(ft, "margin") and hasattr(ft, "Margin") and not hasattr(ft.margin, "all"):
    ft.margin.all, ft.margin.only, ft.margin.symmetric = ft.Margin.all, ft.Margin.only, ft.Margin.symmetric
if hasattr(ft, "border_radius") and hasattr(ft, "BorderRadius") and not hasattr(ft.border_radius, "all"):
    ft.border_radius.all, ft.border_radius.only = ft.BorderRadius.all, ft.BorderRadius.only

APP_VERSION = "2.2.5"
WEBSITE_URL = "https://v3xsys.pages.dev/"
DEFAULT_UPDATE_URL = "https://v3xsys.pages.dev/"
LICENSE_URL = "https://selfbot-license.krymyhady314.workers.dev"
CREATOR_ID = "@V3XSYS"

BG_GALAXY, BG_CARD, BG_INPUT = "#030306", "#0A0A12", "#12121D"
RED_PRIMARY, RED_DARK, RED_NEON, RED_LIGHT = "#DC2626", "#991B1B", "#FF1E42", "#EF4444"
BORDER_CRIMSON, BORDER_ACTIVE = "#450A0A", "#EF4444"
TEXT_WHITE, TEXT_MUTED = "#FFFFFF", "#CBD5E1"
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


def load_json(path: str, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(default, dict) and isinstance(data, dict):
                out = dict(default)
                out.update(data)
                return out
            if isinstance(default, list) and isinstance(data, list) and data:
                return data
    except Exception:
        pass
    return dict(default) if isinstance(default, dict) else list(default)


def save_json(path: str, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def parse_ver(v: str) -> tuple[int, ...]:
    nums = re.findall(r"\d+", str(v or "0"))
    return tuple(int(x) for x in nums) if nums else (0,)


def get_device_id() -> str:
    parts = [platform.system(), platform.machine(), platform.node()]
    for prop in ("ro.product.brand", "ro.product.model", "ro.product.device", "ro.build.id"):
        try:
            out = subprocess.check_output(["getprop", prop], stderr=subprocess.DEVNULL, timeout=1).decode().strip()
            if out:
                parts.append(out)
        except Exception:
            pass
    did = "V3X-" + hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16].upper()
    try:
        open(DEV_FILE, "w", encoding="utf-8").write(did)
    except Exception:
        pass
    return did


def notify_android_service(cmd: str):
    def _ping():
        try:
            urllib.request.urlopen(f"http://127.0.0.1:48391/{cmd}", timeout=0.6).read()
        except Exception:
            pass
    try:
        asyncio.get_running_loop().run_in_executor(None, _ping)
    except Exception:
        _ping()


def format_clock(style: str = "bold") -> str:
    raw = datetime.datetime.now(TEHRAN_TZ).strftime("%H:%M")
    if style == "bold":
        return raw.translate(str.maketrans("0123456789", "𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"))
    if style == "mono":
        return raw.translate(str.maketrans("0123456789", "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"))
    return raw


def strip_clock(name: str) -> str:
    return re.sub(r"\s*[\|•\-–—]?\s*[0-9𝟎-𝟗𝟶-𝟿]{2}:[0-9𝟎-𝟗𝟶-𝟿]{2}\s*$", "", (name or "").strip()).strip()


def clean_key(raw: str) -> str:
    txt = str(raw or "").translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩–—−", "01234567890123456789---"))
    txt = re.sub(r"[\u200b-\u200f\ufeff`\"'\s]", "", txt)
    m = re.search(r"(V3X-[A-Za-z0-9\-_]{3,})", txt, re.IGNORECASE)
    return m.group(1).upper() if m else txt.upper()


async def check_license(raw_key: str, did: str) -> tuple[str, str, str, str]:
    ck = clean_key(raw_key)
    if not ck:
        return "ERROR", "لطفاً کلید لایسنس را وارد کنید.", "", DEFAULT_UPDATE_URL
    payload = {"action": "verify", "source": "app", "key": ck, "license": ck, "hwid": did, "device_id": did, "app_version": APP_VERSION}
    base = LICENSE_URL.rstrip("/")
    routes = [("POST_JSON", f"{base}/api/verify"), ("POST_JSON", f"{base}/verify"), ("GET", f"{base}/verify"), ("GET", base), ("POST_JSON", base)]
    last_err = "عدم اتصال به سرور لایسنس؛ اینترنت خود را بررسی کنید."
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http:
        for mode, url in routes:
            try:
                r = await http.post(url, params=payload, json=payload) if mode == "POST_JSON" else await http.get(url, params=payload)
                if r.status_code in (404, 405):
                    continue
                d = r.json()
                if not isinstance(d, dict):
                    continue
                upd = str(d.get("update_url") or d.get("download_url") or DEFAULT_UPDATE_URL)
                sv = str(d.get("status", "")).lower().strip()
                mv = str(d.get("min_version") or d.get("required_version") or "").strip()
                if d.get("force_update") is True or d.get("outdated") is True or sv in ("outdated", "update_required", "disabled") or (mv and parse_ver(APP_VERSION) < parse_ver(mv)):
                    return "OUTDATED", str(d.get("message") or f"نسخه فعلی ({APP_VERSION}) غیرفعال شده است."), ck, upd
                if d.get("valid") is True or d.get("ok") is True or d.get("success") is True or sv in ("valid", "ok", "active", "success"):
                    return "OK", str(d.get("message") or d.get("msg") or "لایسنس تایید شد ✅"), ck, upd
                msg = d.get("message") or d.get("error") or d.get("reason") or d.get("msg")
                if msg:
                    return "ERROR", str(msg), ck, upd
            except Exception as e:
                last_err = f"خطا در ارتباط با سرور: {e}"
    return "ERROR", last_err, ck, DEFAULT_UPDATE_URL


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
        return cls(SESSION_PATH)


async def apply_profile_name(c, first_name: str, last_name: str):
    fn = getattr(c, "update_profile", None)
    if callable(fn):
        res = fn(first_name=first_name, last_name=last_name)
        if inspect.isawaitable(res):
            await res
        return
    for mp in ("splusthon.tl.functions.account", "splusthon.functions.account"):
        try:
            req = getattr(importlib.import_module(mp), "UpdateProfileRequest", None)
            if req:
                await c(req(first_name=first_name, last_name=last_name))
                return
        except Exception:
            pass
    raise RuntimeError("متد تغییر نام پروفایل یافت نشد.")


def make_btn(label: str, on_click, bgcolor: str = RED_PRIMARY, color: str = TEXT_WHITE, height: int = 40, kind: str = "filled", expand: bool = False):
    lbl = ft.Text(label, color=color, weight=ft.FontWeight.W_600, size=12)
    if kind == "outlined":
        return getattr(ft, "OutlinedButton", ft.Button)(content=lbl, on_click=on_click, height=height, expand=expand), lbl
    if kind == "text":
        return getattr(ft, "TextButton", ft.Button)(content=lbl, on_click=on_click, expand=expand), lbl
    btn_cls = getattr(ft, "Button", None) or getattr(ft, "ElevatedButton", None)
    return btn_cls(content=lbl, bgcolor=bgcolor, color=color, height=height, on_click=on_click, expand=expand), lbl


def make_toggle_card(title: str, subtitle: str, initial_val: bool, on_toggle):
    ref = {"val": bool(initial_val)}
    b_txt = ft.Text("✅ روشن" if ref["val"] else "⭕ خاموش", size=12, weight=ft.FontWeight.BOLD, color="#10B981" if ref["val"] else RED_NEON)
    b_box = ft.Container(padding=ft.Padding.symmetric(horizontal=12, vertical=6), border_radius=ft.BorderRadius.all(10), bgcolor="#06281E" if ref["val"] else "#26080E", border=ft.Border.all(1.5, "#10B981" if ref["val"] else RED_NEON), content=b_txt)
    card = ft.Container(
        padding=ft.Padding.all(11), border_radius=ft.BorderRadius.all(12),
        bgcolor="#0C1F1A" if ref["val"] else "#180A10", border=ft.Border.all(1.5, "#10B981" if ref["val"] else BORDER_ACTIVE),
        content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=8, controls=[
            ft.Column(spacing=2, expand=True, controls=[ft.Text(title, size=13, weight=ft.FontWeight.BOLD, color=TEXT_WHITE), ft.Text(subtitle, size=11, color=TEXT_MUTED)]),
            b_box,
        ]),
    )

    def _click(e):
        ref["val"] = not ref["val"]
        v = ref["val"]
        b_txt.value = "✅ روشن" if v else "⭕ خاموش"
        b_txt.color = "#10B981" if v else RED_NEON
        b_box.bgcolor = "#06281E" if v else "#26080E"
        b_box.border = ft.Border.all(1.5, "#10B981" if v else RED_NEON)
        card.bgcolor = "#0C1F1A" if v else "#180A10"
        card.border = ft.Border.all(1.5, "#10B981" if v else BORDER_ACTIVE)
        on_toggle(v)

    card.on_click = _click
    return card, ref


def footer_box():
    return ft.Container(
        margin=ft.Margin.only(top=6), padding=ft.Padding.symmetric(vertical=8, horizontal=12),
        border_radius=ft.BorderRadius.all(10), bgcolor=BG_CARD, border=ft.Border.all(1, BORDER_CRIMSON),
        content=ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[
            ft.Text(f"نسخه {APP_VERSION}  |  طراحی و توسعه: ", size=11, color=TEXT_MUTED),
            ft.Text(CREATOR_ID, size=12, weight=ft.FontWeight.BOLD, color=RED_NEON, selectable=True),
        ]),
    )


def parse_target(raw: str):
    val = (raw or "").strip()
    return int(val) if val.lstrip("-").isdigit() else val


async def main(page: ft.Page):
    page.title = "V3X Selfbot"
    page.bgcolor = BG_GALAXY
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = ft.Padding.only(top=32, left=10, right=10, bottom=10)
    page.scroll = ft.ScrollMode.AUTO
    page.rtl = True

    did = get_device_id()
    clock_cfg = load_json(CLOCK_CFG_FILE, {"enabled": False, "base_first": "", "base_last": "", "style": "bold", "target_field": "first", "sep": "|", "bg_keep_alive": True})
    ar_cfg = load_json(AUTOREPLY_CFG_FILE, {"enabled": False, "text": "سلام، در حال حاضر آفلاین هستم. به محض آنلاین شدن پاسخ می‌دهم.", "replied_users": []})
    fwd_cfg = load_json(FORWARD_CFG_FILE, {"interval_min": 5})

    st = {
        "client": None, "me_id": None, "phone": "", "hash": None, "need_2fa": False,
        "bg_started": False, "hook_attached": False, "last_clock_min": "", "in_dashboard": False,
        "active_tab": "chats", "chat_filter": "all", "dialogs": [], "selected_targets": {},
        "active_target": "", "recent_messages": [], "reply_to_id": None, "reply_to_preview": "",
        "reply_chat_id": "", "multi_messages": load_json(SAVED_MSGS_FILE, ["سلام!", "چطوری؟", "پیام تست V3X"]),
        "multi_running": False, "turbo_running": False, "entity_cache": {},
        "fwd_source_chat": "", "fwd_messages": [], "fwd_selected_msg_id": None,
        "fwd_selected_msg_preview": "", "fwd_running": False, "fwd_status": "آماده شروع فوروارد به کاربران ۲۰۰ پیام اخیر گپ‌ها",
    }
    logs = ft.Column(spacing=2, height=80, scroll=ft.ScrollMode.AUTO)
    conn_badge = ft.Text("🟢 متصل", size=12, color="#10B981", weight=ft.FontWeight.W_600)

    def safe_update():
        try:
            page.update()
        except Exception:
            pass

    def log(txt: str, col: str = TEXT_MUTED):
        logs.controls.insert(0, ft.Text(f"[{time.strftime('%H:%M:%S')}] {txt}", size=11, color=col))
        del logs.controls[12:]
        try:
            if logs.page is not None:
                logs.update()
                return
        except Exception:
            pass
        safe_update()

    def get_client():
        if st["client"] is None:
            st["client"] = create_splus_client()
        return st["client"]

    async def get_my_id(c) -> str:
        if st["me_id"]:
            return st["me_id"]
        try:
            me = await asyncio.wait_for(c.get_me(), timeout=8.0)
            uid = getattr(me, "id", None) or getattr(me, "user_id", None)
            if uid is not None:
                st["me_id"] = str(uid)
        except Exception:
            pass
        return st["me_id"] or ""

    async def ensure_online(c, reset: bool = False) -> bool:
        try:
            if reset:
                try:
                    await asyncio.wait_for(c.disconnect(), timeout=3.0)
                except Exception:
                    pass
            if not c.is_connected():
                conn_badge.value, conn_badge.color = "🟡 اتصال مجدد...", "#F59E0B"
                safe_update()
                await asyncio.wait_for(c.connect(), timeout=10.0)
            if conn_badge.value != "🟢 متصل":
                conn_badge.value, conn_badge.color = "🟢 متصل", "#10B981"
                safe_update()
            return True
        except Exception:
            conn_badge.value, conn_badge.color = "🔴 قطع اتصال", RED_NEON
            safe_update()
            return False

    async def resolve_peer(c, raw: str):
        key = (raw or "").strip()
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

    async def send_fast(c, peer, raw_target: str, text: str, reply_id=None):
        for attempt in range(1, 4):
            try:
                if reply_id is not None:
                    try:
                        await asyncio.wait_for(c.send_message(peer, text, reply_to=reply_id), timeout=10.0)
                        return
                    except TypeError:
                        await asyncio.wait_for(c.send_message(peer, text), timeout=10.0)
                        return
                await asyncio.wait_for(c.send_message(peer, text), timeout=10.0)
                return
            except Exception as ex:
                w = getattr(ex, "seconds", None)
                if w is None:
                    m = re.search(r"wait of (\d+)", str(ex).lower())
                    if m:
                        w = int(m.group(1))
                if w:
                    await asyncio.sleep(min(int(w) + 1, 20))
                    continue
                if attempt < 3:
                    await ensure_online(c, reset=True)
                    st["entity_cache"].pop((raw_target or "").strip(), None)
                    peer = await resolve_peer(c, raw_target)
                    await asyncio.sleep(0.3)
                else:
                    raise ex

    async def forward_fast(c, to_peer, raw_to: str, from_peer, msg_id):
        fwd_fn = getattr(c, "forward_messages", None) or getattr(c, "forward", None)
        if not callable(fwd_fn):
            raise RuntimeError("متد forward_messages یافت نشد.")
        params = list(inspect.signature(fwd_fn).parameters.keys())
        for attempt in range(1, 3):
            try:
                if "from_peer" in params:
                    coro = fwd_fn(to_peer, msg_id, from_peer=from_peer)
                elif "from_chat_id" in params:
                    coro = fwd_fn(to_peer, from_peer, msg_id)
                else:
                    try:
                        coro = fwd_fn(to_peer, msg_id, from_peer)
                    except TypeError:
                        coro = fwd_fn(to_peer, from_peer, msg_id)
                if inspect.isawaitable(coro):
                    await asyncio.wait_for(coro, timeout=12.0)
                return
            except Exception as ex:
                w = getattr(ex, "seconds", None)
                if w is None:
                    m = re.search(r"wait of (\d+)", str(ex).lower())
                    if m:
                        w = int(m.group(1))
                if w:
                    await asyncio.sleep(min(int(w) + 1, 25))
                    continue
                if attempt < 2:
                    await ensure_online(c, reset=True)
                    st["entity_cache"].pop((raw_to or "").strip(), None)
                    to_peer = await resolve_peer(c, raw_to)
                    await asyncio.sleep(0.3)
                else:
                    raise ex

    async def sync_clock(c, force: bool = False):
        if not clock_cfg.get("enabled"):
            return
        now_min = datetime.datetime.now(TEHRAN_TZ).strftime("%H:%M")
        if not force and st["last_clock_min"] == now_min:
            return
        try:
            await ensure_online(c)
            if not clock_cfg.get("base_first"):
                me = await asyncio.wait_for(c.get_me(), timeout=8.0)
                clock_cfg["base_first"] = strip_clock(getattr(me, "first_name", "") or "")
                clock_cfg["base_last"] = strip_clock(getattr(me, "last_name", "") or "")
                save_json(CLOCK_CFG_FILE, clock_cfg)
            clk = format_clock(clock_cfg.get("style", "bold"))
            sep, bf, bl = clock_cfg.get("sep", "|"), clock_cfg.get("base_first", ""), clock_cfg.get("base_last", "")
            nf, nl = (bf, f"{bl} {sep} {clk}".strip() if bl else clk) if clock_cfg.get("target_field") == "last" else (f"{bf} {sep} {clk}".strip() if bf else clk, bl)
            await apply_profile_name(c, nf, nl)
            st["last_clock_min"] = now_min
            log(f"ساعت آپدیت شد: {nf} {nl}".strip(), RED_LIGHT)
        except Exception as ex:
            log(f"خطای ساعت: {ex}", RED_NEON)

    async def check_unread_pv_autoreply(c):
        if not ar_cfg.get("enabled"):
            return
        txt = str(ar_cfg.get("text") or "").strip()
        if not txt or not callable(getattr(c, "get_dialogs", None)):
            return
        try:
            await ensure_online(c)
            my_id = await get_my_id(c)
            raw = await asyncio.wait_for(c.get_dialogs(limit=12), timeout=8.0)
            replied = set(str(x) for x in ar_cfg.get("replied_users", []))
            for d in raw:
                if (getattr(d, "unread_count", 0) or 0) <= 0:
                    continue
                ent = getattr(d, "entity", None)
                cid = str(getattr(d, "id", None) or (getattr(ent, "id", "") if ent else "")).strip()
                if not cid or cid == my_id or cid in replied:
                    continue
                is_u, is_g, is_ch = getattr(d, "is_user", None), getattr(d, "is_group", None), getattr(d, "is_channel", None)
                if not (is_u is True or cid.startswith("u0") or (cid.lstrip("-").isdigit() and int(cid) > 0 and not is_g and not is_ch)):
                    continue
                if ent and bool(getattr(ent, "bot", False) or getattr(ent, "is_bot", False)):
                    continue
                peer = await resolve_peer(c, cid)
                await send_fast(c, peer, cid, txt)
                replied.add(cid)
                ar_cfg["replied_users"] = list(replied)
                save_json(AUTOREPLY_CFG_FILE, ar_cfg)
                title = getattr(d, "name", None) or getattr(d, "title", None) or cid
                log(f"🤖 پاسخ خودکار به «{title}» ارسال شد ✅", "#10B981")
        except Exception:
            pass

    def attach_pv_hook(c):
        if st["hook_attached"] or not callable(getattr(c, "add_event_handler", None)):
            return
        try:
            NewMessage = getattr(importlib.import_module("splusthon.events"), "NewMessage", None)
            if not NewMessage:
                return

            async def _on_pv(event):
                try:
                    if not ar_cfg.get("enabled") or not getattr(event, "is_private", False) or getattr(event, "out", False):
                        return
                    txt = str(ar_cfg.get("text") or "").strip()
                    if not txt:
                        return
                    sender = await event.get_sender()
                    if sender and bool(getattr(sender, "bot", False) or getattr(sender, "is_bot", False)):
                        return
                    cid = str(getattr(event, "chat_id", None) or getattr(event, "sender_id", None) or "")
                    if not cid or cid == await get_my_id(c):
                        return
                    replied = set(str(x) for x in ar_cfg.get("replied_users", []))
                    if cid in replied:
                        return
                    peer = await resolve_peer(c, cid)
                    await send_fast(c, peer, cid, txt)
                    replied.add(cid)
                    ar_cfg["replied_users"] = list(replied)
                    save_json(AUTOREPLY_CFG_FILE, ar_cfg)
                    log(f"🤖 پاسخ خودکار به «{getattr(sender, 'first_name', cid)}» ارسال شد ✅", "#10B981")
                except Exception:
                    pass

            c.add_event_handler(_on_pv, NewMessage(incoming=True))
            st["hook_attached"] = True
        except Exception:
            pass

    async def start_bg_engine(c):
        attach_pv_hook(c)
        if st["bg_started"]:
            return
        st["bg_started"] = True

        async def _clock_loop():
            while st["client"] is not None:
                try:
                    if clock_cfg.get("enabled"):
                        await sync_clock(c, force=False)
                except Exception:
                    pass
                sec = datetime.datetime.now(TEHRAN_TZ).second
                await asyncio.sleep(max(2.0, 60.5 - sec) if clock_cfg.get("enabled") else 10.0)

        async def _keepalive_and_pv_loop():
            while st["client"] is not None:
                try:
                    if not c.is_connected():
                        await ensure_online(c)
                    if ar_cfg.get("enabled"):
                        await check_unread_pv_autoreply(c)
                except Exception:
                    pass
                await asyncio.sleep(8.0)

        asyncio.create_task(_clock_loop())
        asyncio.create_task(_keepalive_and_pv_loop())

    def show_update_required(msg: str, update_url: str):
        st["in_dashboard"] = False
        site = update_url or WEBSITE_URL
        page.clean()
        url_box = ft.TextField(label="آدرس سایت رسمی", value=site, read_only=True, text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_ACTIVE)
        stat = ft.Text("", size=12, color="#10B981")

        async def open_dl(e):
            try:
                if hasattr(page, "launch_url"):
                    r = page.launch_url(site)
                    if inspect.isawaitable(r):
                        await r
                if hasattr(ft, "Clipboard"):
                    await ft.Clipboard().set(site)
                stat.value = "لینک کپی شد ✅"
            except Exception:
                stat.value = "لینک بالا را کپی کنید."
            safe_update()

        dl_btn, _ = make_btn("🌐 ورود به سایت و دانلود نسخه جدید", open_dl, height=46)
        page.add(ft.Container(bgcolor=BG_CARD, padding=18, border_radius=ft.BorderRadius.all(14), border=ft.Border.all(1.5, RED_NEON), content=ft.Column(spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[ft.Text("⚠️ این نسخه غیرفعال شده است", size=19, weight=ft.FontWeight.BOLD, color=RED_NEON), ft.Text(msg, size=13, color=TEXT_WHITE), url_box, dl_btn, stat])), footer_box())
        safe_update()

    async def proceed_after_license():
        try:
            c = get_client()
            await c.connect()
            if await c.is_user_authorized():
                await start_bg_engine(c)
                show_dashboard()
                return
        except Exception:
            pass
        show_phone()

    def show_license(msg: str = ""):
        st["in_dashboard"] = False
        page.clean()
        info = ft.Text(msg, size=13, color="#F59E0B", selectable=True)
        dev_box = ft.TextField(label="شناسه سخت‌افزاری دستگاه", value=did, read_only=True, text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_CRIMSON)
        saved_k = str(load_json(LIC_FILE, {}).get("key", "")).strip()
        key_box = ft.TextField(label="کلید لایسنس", value=saved_k, hint_text="V3X-XXXX-XXXX", text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_ACTIVE)

        async def copy_id(e):
            try:
                if hasattr(ft, "Clipboard"):
                    await ft.Clipboard().set(did)
                info.value, info.color = "شناسه دستگاه کپی شد ✅", "#10B981"
            except Exception:
                info.value, info.color = "متن را انتخاب و کپی کنید.", "#F59E0B"
            safe_update()

        async def verify(e):
            btn.disabled = True
            info.value, info.color = "در حال بررسی لایسنس...", RED_LIGHT
            safe_update()
            status, m, ck, upd = await check_license(key_box.value or "", did)
            btn.disabled = False
            if status == "OUTDATED":
                show_update_required(m, upd)
                return
            if status != "OK":
                info.value, info.color = f"❌ {m}", RED_NEON
                safe_update()
                return
            save_json(LIC_FILE, {"key": ck})
            await proceed_after_license()

        btn, _ = make_btn("بررسی لایسنس و ورود", verify, height=46)
        copy_btn, _ = make_btn("📋 کپی شناسه دستگاه", copy_id, color=RED_LIGHT, kind="outlined")
        page.add(ft.Container(bgcolor=BG_CARD, padding=16, border_radius=ft.BorderRadius.all(14), border=ft.Border.all(1.2, BORDER_ACTIVE), content=ft.Column(spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[ft.Text("V3X SELFBOT", size=22, weight=ft.FontWeight.BOLD, color=RED_NEON), ft.Text(f"نسخه {APP_VERSION} | فعال‌سازی اشتراک", size=12, color=TEXT_MUTED), dev_box, copy_btn, key_box, btn, info])), footer_box())
        safe_update()

    def show_phone(msg: str = ""):
        st["in_dashboard"] = False
        page.clean()
        info = ft.Text(msg, size=13, color="#F59E0B", selectable=True)
        ph_box = ft.TextField(label="شماره موبایل سروش‌پلاس", hint_text="09123456789", keyboard_type=ft.KeyboardType.PHONE, text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_ACTIVE)

        async def send_otp(e):
            d = "".join(c for c in (ph_box.value or "") if c.isdigit())
            if d.startswith("09") and len(d) == 11:
                p98, p09 = "98" + d[1:], d
            elif d.startswith("989") and len(d) == 12:
                p98, p09 = d, "0" + d[2:]
            elif d.startswith("9") and len(d) == 10:
                p98, p09 = "98" + d, "0" + d
            else:
                info.value, info.color = "شماره موبایل معتبر وارد کنید.", RED_NEON
                safe_update()
                return
            btn.disabled = True
            info.value, info.color = "در حال ارسال کد تایید...", RED_LIGHT
            safe_update()
            try:
                c = get_client()
                if not c.is_connected():
                    await c.connect()
                res, used, err = None, p98, None
                for fmt in (p98, f"+{p98}", p09):
                    try:
                        res = await c.send_code_request(fmt)
                        used, err = fmt, None
                        break
                    except Exception as ex:
                        err = ex
                if err:
                    raise err
                st["phone"], st["hash"], st["need_2fa"] = used, getattr(res, "phone_code_hash", None), False
                btn.disabled = False
                show_otp()
            except Exception as ex:
                btn.disabled = False
                info.value, info.color = f"خطا: {ex}", RED_NEON
                safe_update()

        btn, _ = make_btn("ارسال کد تایید", send_otp, height=46)
        page.add(ft.Container(bgcolor=BG_CARD, padding=16, border_radius=ft.BorderRadius.all(14), border=ft.Border.all(1.2, BORDER_ACTIVE), content=ft.Column(spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[ft.Text("ورود به سروش‌پلاس", size=19, weight=ft.FontWeight.BOLD, color=RED_NEON), ph_box, btn, info])), footer_box())
        safe_update()

    def show_otp():
        st["in_dashboard"] = False
        page.clean()
        info = ft.Text(f"کد تایید به {st['phone']} ارسال شد.", size=13, color=RED_LIGHT)
        code_box = ft.TextField(label="کد تایید", hint_text="12345", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_ACTIVE)
        pwd_box = ft.TextField(label="رمز دومرحله‌ای", password=True, can_reveal_password=True, visible=st["need_2fa"], text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_ACTIVE)

        async def confirm(e):
            code, pwd = (code_box.value or "").strip(), (pwd_box.value or "").strip()
            if not st["need_2fa"] and len(code) < 4:
                info.value, info.color = "کد تایید را کامل وارد کنید.", RED_NEON
                safe_update()
                return
            btn.disabled = True
            info.value, info.color = "در حال ورود...", RED_LIGHT
            safe_update()
            try:
                c = get_client()
                if st["need_2fa"]:
                    await c.sign_in(password=pwd)
                else:
                    try:
                        await c.sign_in(phone=st["phone"], code=code, phone_code_hash=st["hash"]) if st["hash"] else await c.sign_in(st["phone"], code)
                    except TypeError:
                        await c.sign_in(st["phone"], code)
                btn.disabled = False
                await start_bg_engine(c)
                show_dashboard()
            except Exception as ex:
                btn.disabled = False
                if "password" in str(ex).lower() or "2fa" in str(ex).lower():
                    st["need_2fa"], pwd_box.visible = True, True
                    info.value, info.color = "رمز دومرحله‌ای را وارد کنید.", "#F59E0B"
                else:
                    info.value, info.color = f"خطا: {ex}", RED_NEON
                safe_update()

        btn, _ = make_btn("تایید و ورود", confirm, height=46)
        chg_btn, _ = make_btn("تغییر شماره", lambda e: show_phone(), color=TEXT_MUTED, kind="text")
        page.add(ft.Container(bgcolor=BG_CARD, padding=16, border_radius=ft.BorderRadius.all(14), border=ft.Border.all(1.2, BORDER_ACTIVE), content=ft.Column(spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[ft.Text("تایید کد", size=19, weight=ft.FontWeight.BOLD, color=RED_NEON), code_box, pwd_box, btn, chg_btn, info])), footer_box())
        safe_update()

    def show_dashboard():
        st["in_dashboard"] = True
        page.clean()
        c = get_client()
        log("سلف‌بات با موفقیت متصل شد ✅", "#10B981")

        body_host = ft.Column(spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        on_dialogs_cb = None

        async def fetch_dialogs(limit_count: int = 80):
            items = []
            try:
                await ensure_online(c)
                raw = await asyncio.wait_for(c.get_dialogs(limit=limit_count), timeout=12.0) if callable(getattr(c, "get_dialogs", None)) else []
                for d in raw:
                    ent = getattr(d, "entity", None)
                    cid = getattr(d, "id", None) or (getattr(ent, "id", None) if ent else None)
                    if cid is None:
                        continue
                    title = getattr(d, "name", None) or getattr(d, "title", None) or (getattr(ent, "title", None) or getattr(ent, "first_name", None) if ent else None) or str(cid)
                    cid_str = str(cid)
                    is_u, is_g, is_ch = getattr(d, "is_user", None), getattr(d, "is_group", None), getattr(d, "is_channel", None)
                    is_bc = bool(getattr(ent, "broadcast", False)) if ent else False
                    is_mg = bool(getattr(ent, "megagroup", False)) if ent else False
                    if is_u is True or cid_str.startswith("u0") or (isinstance(cid, int) and cid > 0 and not is_g and not is_ch):
                        kind = "pv"
                    elif is_ch and (is_bc or not is_mg) and not is_g:
                        kind = "channel"
                    else:
                        kind = "group"
                    items.append({"id": cid_str, "title": str(title), "kind": kind})
            except Exception as ex:
                log(f"خطا در دریافت چت‌ها: {ex}", RED_NEON)
            st["dialogs"] = items
            if callable(on_dialogs_cb):
                on_dialogs_cb()
            return items

        async def fetch_msgs(raw_target: str, limit_count: int = 25) -> list[dict]:
            msgs = []
            tgt = (raw_target or "").strip()
            if not tgt:
                return msgs
            try:
                await ensure_online(c)
                peer = await resolve_peer(c, tgt)
                raw = await asyncio.wait_for(c.get_messages(peer, limit=limit_count), timeout=12.0) if callable(getattr(c, "get_messages", None)) else []
                for m in raw:
                    mid = getattr(m, "id", None)
                    if mid is None:
                        continue
                    txt = (getattr(m, "raw_text", None) or getattr(m, "text", None) or getattr(m, "message", None) or "").strip()
                    if not txt and getattr(m, "media", None):
                        txt = "[رسانه / فایل]"
                    if not txt:
                        continue
                    sender = getattr(m, "sender", None)
                    sname = getattr(sender, "first_name", None) or getattr(sender, "title", None) or ("شما" if getattr(m, "out", False) else str(getattr(m, "sender_id", "کاربر")))
                    msgs.append({"id": mid, "sender": str(sname), "text": txt})
            except Exception as ex:
                log(f"خطا در دریافت پیام‌ها: {ex}", RED_NEON)
            return msgs

        def set_target(val: str):
            v = (val or "").strip()
            if st["reply_chat_id"] and st["reply_chat_id"] != v:
                st["reply_to_id"], st["reply_to_preview"], st["reply_chat_id"] = None, "", ""
            st["active_target"] = v

        def reply_banner(on_clear=None):
            if st["reply_to_id"] is None:
                return ft.Container(visible=False)
            clr_b, _ = make_btn("✖️", lambda e: (st.update({"reply_to_id": None, "reply_to_preview": "", "reply_chat_id": ""}), on_clear() if on_clear else None, safe_update()), color=RED_NEON, kind="text")
            return ft.Container(padding=ft.Padding.symmetric(horizontal=10, vertical=5), border_radius=ft.BorderRadius.all(8), bgcolor=BG_INPUT, border=ft.Border.all(1, RED_LIGHT), content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text(f"↩️ ریپلای #{st['reply_to_id']}: {st['reply_to_preview'][:35]}", size=12, color=RED_LIGHT, expand=True), clr_b]))

        def build_chats():
            nonlocal on_dialogs_cb
            t_box = ft.TextField(label="آیدی یا شناسه چت", value=st["active_target"], text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_CRIMSON, on_change=lambda e: set_target(e.control.value or ""))
            c_col = ft.Column(spacing=6, height=160, scroll=ft.ScrollMode.AUTO)
            m_col = ft.Column(spacing=6, height=175, scroll=ft.ScrollMode.AUTO)
            cnt_lbl = ft.Text(f"چت‌های انتخاب‌شده: {len(st['selected_targets'])}", size=12, color=RED_LIGHT)
            rep_holder = ft.Column(controls=[reply_banner(lambda: draw_msgs())])

            def draw_msgs():
                m_col.controls.clear()
                if not st["recent_messages"]:
                    m_col.controls.append(ft.Text("پیامی بارگذاری نشده است.", size=12, color=TEXT_MUTED))
                    return
                for m in st["recent_messages"]:
                    mid, is_sel = m["id"], st["reply_to_id"] == m["id"]
                    m_col.controls.append(ft.Container(
                        padding=ft.Padding.all(8), border_radius=ft.BorderRadius.all(8), bgcolor="#1C0A10" if is_sel else BG_INPUT,
                        border=ft.Border.all(1.5 if is_sel else 1, RED_NEON if is_sel else BORDER_CRIMSON),
                        on_click=lambda e, i=mid, t=m["text"]: (st.update({"reply_to_id": i, "reply_to_preview": t, "reply_chat_id": st["active_target"]}), rep_holder.__setattr__("controls", [reply_banner(draw_msgs)]), draw_msgs(), safe_update()),
                        content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Column(spacing=2, expand=True, controls=[ft.Text(f"{m['sender']} (#{mid})", size=11, color=RED_LIGHT), ft.Text(m["text"], size=12, color=TEXT_WHITE, max_lines=2)]), ft.Text("✅" if is_sel else "ریپلای", size=11, color=RED_NEON if is_sel else TEXT_MUTED)]),
                    ))

            async def click_chat(e, cid: str, title: str):
                set_target(cid)
                t_box.value = cid
                if cid in st["selected_targets"]:
                    del st["selected_targets"][cid]
                else:
                    st["selected_targets"][cid] = title
                cnt_lbl.value = f"چت‌های انتخاب‌شده: {len(st['selected_targets'])}"
                rep_holder.controls = [reply_banner(draw_msgs)]
                draw_chats()
                safe_update()
                st["recent_messages"] = await fetch_msgs(cid, 20)
                draw_msgs()
                safe_update()

            def draw_chats():
                c_col.controls.clear()
                flt = st["chat_filter"]
                lst = st["dialogs"] if flt == "all" else [x for x in st["dialogs"] if (x["kind"] == "pv" if flt == "pv" else x["kind"] in ("group", "channel"))]
                if not lst:
                    c_col.controls.append(ft.Text("چتی یافت نشد. دکمه بروزرسانی را بزنید.", size=12, color=TEXT_MUTED))
                    return
                for it in lst:
                    cid, title = it["id"], it["title"]
                    sel = cid in st["selected_targets"] or st["active_target"] == cid
                    badge = "👤 پی‌وی" if it["kind"] == "pv" else ("📢 کانال" if it["kind"] == "channel" else "👥 گپ")
                    c_col.controls.append(ft.Container(
                        padding=ft.Padding.all(8), border_radius=ft.BorderRadius.all(9), bgcolor="#1C0A10" if sel else BG_INPUT,
                        border=ft.Border.all(1.5 if sel else 1, RED_NEON if sel else BORDER_CRIMSON),
                        on_click=lambda e, i=cid, t=title: page.run_task(click_chat, e, i, t),
                        content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Column(spacing=1, expand=True, controls=[ft.Text(title, size=13, weight=ft.FontWeight.W_600, color=TEXT_WHITE), ft.Text(f"{badge} | {cid}", size=11, color=TEXT_MUTED)]), ft.Text("✅" if sel else "انتخاب", size=12, color=RED_NEON if sel else "#64748B")]),
                    ))

            def set_flt(e, m: str):
                st["chat_filter"] = m
                f_all.bgcolor, f_pv.bgcolor, f_gp.bgcolor = (RED_PRIMARY if m == "all" else BG_INPUT), (RED_PRIMARY if m == "pv" else BG_INPUT), (RED_PRIMARY if m == "group" else BG_INPUT)
                draw_chats()
                safe_update()

            async def load_m(e):
                if (t_box.value or "").strip():
                    set_target(t_box.value)
                    st["recent_messages"] = await fetch_msgs(st["active_target"], 20)
                    draw_msgs()
                    safe_update()

            on_dialogs_cb = lambda: (draw_chats(), safe_update())
            f_all, _ = make_btn("همه", lambda e: set_flt(e, "all"), bgcolor=RED_PRIMARY if st["chat_filter"] == "all" else BG_INPUT, height=34, expand=True)
            f_pv, _ = make_btn("👤 پی‌وی", lambda e: set_flt(e, "pv"), bgcolor=RED_PRIMARY if st["chat_filter"] == "pv" else BG_INPUT, height=34, expand=True)
            f_gp, _ = make_btn("👥 گپ‌ها", lambda e: set_flt(e, "group"), bgcolor=RED_PRIMARY if st["chat_filter"] == "group" else BG_INPUT, height=34, expand=True)
            rel_b, _ = make_btn("🔄 بروزرسانی چت‌ها", lambda e: page.run_task(fetch_dialogs), height=38, expand=True)
            lm_b, _ = make_btn("📜 پیام‌های اخیر", load_m, bgcolor=RED_DARK, height=38, expand=True)
            clr_b, _ = make_btn("پاک کردن", lambda e: (st["selected_targets"].clear(), set_target(""), st["recent_messages"].clear(), setattr(t_box, "value", ""), setattr(cnt_lbl, "value", "چت‌های انتخاب‌شده: 0"), draw_chats(), draw_msgs(), safe_update()), color=RED_NEON, kind="text")
            draw_chats()
            draw_msgs()
            return ft.Column(spacing=8, controls=[
                ft.Container(bgcolor=BG_CARD, padding=12, border_radius=ft.BorderRadius.all(12), border=ft.Border.all(1, BORDER_CRIMSON), content=ft.Column(spacing=8, controls=[ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text("💬 انتخاب پی‌وی یا گپ", size=15, weight=ft.FontWeight.BOLD), clr_b]), t_box, ft.Row(spacing=6, controls=[rel_b, lm_b]), ft.Row(spacing=6, controls=[f_all, f_pv, f_gp]), cnt_lbl, c_col])),
                ft.Container(bgcolor=BG_CARD, padding=12, border_radius=ft.BorderRadius.all(12), border=ft.Border.all(1, BORDER_CRIMSON), content=ft.Column(spacing=6, controls=[ft.Text("📜 پیام‌های اخیر (برای ریپلای لمس کنید)", size=13, color=RED_LIGHT), rep_holder, m_col])),
            ])

        def build_multi():
            t_box = ft.TextField(label="مقصد ارسال", value=st["active_target"], text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_CRIMSON, on_change=lambda e: set_target(e.control.value or ""))
            m_card, m_ref = make_toggle_card("ارسال همزمان به چت‌های تیک‌خورده", f"انتخاب‌شده: {len(st['selected_targets'])} چت", len(st["selected_targets"]) > 1, lambda v: safe_update())
            new_in = ft.TextField(label="متن پیام جدید", bgcolor=BG_INPUT, border_color=BORDER_CRIMSON)
            rnd_in = ft.TextField(label="تعداد دور", value="1", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_CRIMSON, expand=True)
            dly_in = ft.TextField(label="تاخیر (0 = توربو)", value="0", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_CRIMSON, expand=True)
            stat = ft.Text("آماده ارسال چندتایی", size=12, color=TEXT_MUTED)
            items_col = ft.Column(spacing=5)

            def draw_items():
                items_col.controls.clear()
                for idx, txt in enumerate(st["multi_messages"]):
                    db, _ = make_btn("حذف", lambda e, i=idx: (st["multi_messages"].pop(i), draw_items(), safe_update()), color=RED_NEON, kind="text")
                    items_col.controls.append(ft.Container(padding=ft.Padding.symmetric(horizontal=8, vertical=4), border_radius=ft.BorderRadius.all(8), bgcolor=BG_INPUT, border=ft.Border.all(1, BORDER_CRIMSON), content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text(f"{idx+1}. {txt}", size=12, expand=True), db])))

            async def run_m():
                try:
                    rounds, dly = max(1, int(rnd_in.value or 1)), max(0.0, float(dly_in.value or 0))
                except ValueError:
                    rounds, dly = 1, 0.0
                targets = list(st["selected_targets"].keys()) if (m_ref["val"] and st["selected_targets"]) else ([(t_box.value or "").strip()] if (t_box.value or "").strip() else [])
                if not targets or not st["multi_messages"]:
                    st["multi_running"] = False
                    m_lbl.value, m_btn.bgcolor = "🚀 شروع ارسال چندتایی", RED_PRIMARY
                    log("مقصد و لیست پیام را کامل کنید.", RED_NEON)
                    return
                total, done = rounds * len(targets) * len(st["multi_messages"]), 0
                try:
                    await ensure_online(c)
                    peers = {t: await resolve_peer(c, t) for t in targets}
                    q = [(rt, peers[rt], msg, st["reply_to_id"] if st["reply_chat_id"] == rt else None) for _ in range(rounds) for rt in targets for msg in st["multi_messages"]]
                    for i in range(0, len(q), 5 if dly == 0 else 1):
                        if not st["multi_running"]:
                            break
                        chunk = q[i:i + (5 if dly == 0 else 1)]
                        await asyncio.gather(*(send_fast(c, p, rt, tx, rp) for rt, p, tx, rp in chunk))
                        done += len(chunk)
                        stat.value, stat.color = f"ارسال شد: {done}/{total}", "#10B981"
                        safe_update()
                        if dly > 0 and done < total:
                            await asyncio.sleep(dly)
                    log(f"پایان ارسال چندتایی ({done} پیام) ✅", "#10B981")
                except Exception as ex:
                    log(f"خطا: {ex}", RED_NEON)
                finally:
                    st["multi_running"] = False
                    m_lbl.value, m_btn.bgcolor = "🚀 شروع ارسال چندتایی", RED_PRIMARY
                    safe_update()

            def toggle_m(e):
                if st["multi_running"]:
                    st["multi_running"] = False
                    return
                st["multi_running"] = True
                m_lbl.value, m_btn.bgcolor = "⛔ توقف ارسال", RED_DARK
                safe_update()
                asyncio.create_task(run_m())

            add_b, _ = make_btn("➕ افزودن", lambda e: (st["multi_messages"].append(new_in.value.strip()) if (new_in.value or "").strip() else None, setattr(new_in, "value", ""), draw_items(), safe_update()), height=38, expand=True)
            sav_b, _ = make_btn("💾 ذخیره پیش‌فرض", lambda e: (save_json(SAVED_MSGS_FILE, st["multi_messages"]), log("لیست پیام‌ها ذخیره شد ✅", "#10B981")), bgcolor=RED_DARK, height=38, expand=True)
            m_btn, m_lbl = make_btn("🚀 شروع ارسال چندتایی", toggle_m, height=44)
            draw_items()
            return ft.Container(bgcolor=BG_CARD, padding=12, border_radius=ft.BorderRadius.all(12), border=ft.Border.all(1, BORDER_CRIMSON), content=ft.Column(spacing=8, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[ft.Text("📨 ارسال چندتایی", size=15, weight=ft.FontWeight.BOLD), reply_banner(), t_box, m_card, new_in, ft.Row(spacing=6, controls=[add_b, sav_b]), items_col, ft.Row(spacing=6, controls=[rnd_in, dly_in]), m_btn, stat]))

        def build_turbo():
            t_box = ft.TextField(label="آیدی یا شناسه مقصد", value=st["active_target"], text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_CRIMSON, on_change=lambda e: set_target(e.control.value or ""))
            msg_in = ft.TextField(label="متن پیام توربو", bgcolor=BG_INPUT, border_color=BORDER_CRIMSON)
            cnt_in = ft.TextField(label="تعداد", value="20", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_CRIMSON, expand=True)
            dly_in = ft.TextField(label="تاخیر (0 = حداکثر سرعت)", value="0", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_CRIMSON, expand=True)
            stat = ft.Text("آماده", size=12, color=TEXT_MUTED)

            async def run_t():
                sent = 0
                try:
                    total, dly = max(1, int(cnt_in.value or 10)), max(0.0, float(dly_in.value or 0))
                    raw_t, txt = (t_box.value or "").strip(), (msg_in.value or "").strip()
                    rep = st["reply_to_id"] if st["reply_chat_id"] == raw_t else None
                    await ensure_online(c)
                    peer = await resolve_peer(c, raw_t)
                    while st["turbo_running"] and sent < total:
                        batch = min(5 if dly == 0 else 1, total - sent)
                        await asyncio.gather(*(send_fast(c, peer, raw_t, txt, rep) for _ in range(batch)))
                        sent += batch
                        stat.value, stat.color = f"ارسال شد: {sent}/{total}", "#10B981"
                        safe_update()
                        if dly > 0 and sent < total:
                            await asyncio.sleep(dly)
                    log(f"پایان توربو ({sent} پیام) ✅", "#10B981")
                except Exception as ex:
                    log(f"خطای توربو: {ex}", RED_NEON)
                finally:
                    st["turbo_running"] = False
                    t_lbl.value, t_btn.bgcolor = "🚀 شروع توربو", RED_PRIMARY
                    safe_update()

            def toggle_t(e):
                if st["turbo_running"]:
                    st["turbo_running"] = False
                    return
                if not (t_box.value or "").strip() or not (msg_in.value or "").strip():
                    log("مقصد و متن را وارد کنید.", RED_NEON)
                    return
                st["turbo_running"] = True
                t_lbl.value, t_btn.bgcolor = "⛔ توقف توربو", RED_DARK
                safe_update()
                asyncio.create_task(run_t())

            t_btn, t_lbl = make_btn("🚀 شروع توربو", toggle_t, height=44)
            return ft.Container(bgcolor=BG_CARD, padding=12, border_radius=ft.BorderRadius.all(12), border=ft.Border.all(1, BORDER_CRIMSON), content=ft.Column(spacing=8, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[ft.Text("🚀 ارسال توربو فوق‌سریع", size=15, weight=ft.FontWeight.BOLD), reply_banner(), t_box, msg_in, ft.Row(spacing=6, controls=[cnt_in, dly_in]), t_btn, stat]))

        def build_forward():
            src_box = ft.TextField(label="شناسه کانال یا پی‌وی مبدأ", value=st["fwd_source_chat"], text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_CRIMSON, on_change=lambda e: st.update({"fwd_source_chat": (e.control.value or "").strip()}))
            c_col = ft.Column(spacing=5, height=130, scroll=ft.ScrollMode.AUTO)
            m_col = ft.Column(spacing=5, height=150, scroll=ft.ScrollMode.AUTO)
            sel_lbl = ft.Text(f"✅ پیام انتخاب‌شده (#{st['fwd_selected_msg_id']}): {st['fwd_selected_msg_preview']}" if st["fwd_selected_msg_id"] else "⚠️ پیامی انتخاب نشده است", size=12, color="#10B981" if st["fwd_selected_msg_id"] else "#F59E0B")
            int_box = ft.TextField(label="تایمر تکرار فوروارد (دقیقه)", value=str(fwd_cfg.get("interval_min", 5)), keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_ACTIVE)
            f_stat = ft.Text(st["fwd_status"], size=12, color=TEXT_MUTED)

            def draw_f_msgs():
                m_col.controls.clear()
                for m in st["fwd_messages"]:
                    mid, is_s, prev = m["id"], st["fwd_selected_msg_id"] == m["id"], m["text"][:50]
                    m_col.controls.append(ft.Container(
                        padding=ft.Padding.all(8), border_radius=ft.BorderRadius.all(8), bgcolor="#1C0A10" if is_s else BG_INPUT,
                        border=ft.Border.all(1.5 if is_s else 1, RED_NEON if is_s else BORDER_CRIMSON),
                        on_click=lambda e, i=mid, p=prev: (st.update({"fwd_selected_msg_id": i, "fwd_selected_msg_preview": p}), setattr(sel_lbl, "value", f"✅ پیام #{i}: {p}"), setattr(sel_lbl, "color", "#10B981"), draw_f_msgs(), safe_update()),
                        content=ft.Text(f"#{mid} | {prev}", size=12, color=TEXT_WHITE),
                    ))

            async def pick_src(e, cid: str):
                st.update({"fwd_source_chat": cid, "fwd_selected_msg_id": None, "fwd_selected_msg_preview": ""})
                src_box.value, sel_lbl.value, sel_lbl.color = cid, "⚠️ پیام را از لیست پایین انتخاب کنید", "#F59E0B"
                draw_f_chats()
                safe_update()
                st["fwd_messages"] = await fetch_msgs(cid, 25)
                draw_f_msgs()
                safe_update()

            def draw_f_chats():
                c_col.controls.clear()
                lst = [x for x in st["dialogs"] if x["kind"] in ("pv", "channel")] or st["dialogs"]
                for it in lst:
                    cid, is_s = it["id"], st["fwd_source_chat"] == it["id"]
                    badge = "📢 کانال" if it["kind"] == "channel" else "👤 پی‌وی"
                    c_col.controls.append(ft.Container(
                        padding=ft.Padding.all(8), border_radius=ft.BorderRadius.all(8), bgcolor="#1C0A10" if is_s else BG_INPUT,
                        border=ft.Border.all(1.5 if is_s else 1, RED_NEON if is_s else BORDER_CRIMSON),
                        on_click=lambda e, i=cid: page.run_task(pick_src, e, i),
                        content=ft.Text(f"{badge} | {it['title']} ({cid})", size=12, color=TEXT_WHITE),
                    ))

            async def fwd_loop():
                rnd = 0
                src_raw, mid = st["fwd_source_chat"], st["fwd_selected_msg_id"]
                while st["fwd_running"]:
                    rnd += 1
                    try:
                        await ensure_online(c)
                        my_id = await get_my_id(c)
                        src_peer = await resolve_peer(c, src_raw)
                        dialogs = await fetch_dialogs(100)
                        groups = [d for d in dialogs if d["kind"] == "group"]
                        users, seen = [], set()
                        for idx, g in enumerate(groups, 1):
                            if not st["fwd_running"]:
                                break
                            f_stat.value = f"🔍 دور {rnd} | بررسی گپ ({idx}/{len(groups)}): {g['title']}"
                            safe_update()
                            try:
                                gp = await resolve_peer(c, g["id"])
                                gms = await asyncio.wait_for(c.get_messages(gp, limit=200), timeout=15.0)
                                for gm in gms:
                                    so = getattr(gm, "sender", None)
                                    if getattr(gm, "post", False) or (so and bool(getattr(so, "bot", False) or getattr(so, "is_bot", False))):
                                        continue
                                    uid = str(getattr(gm, "sender_id", None) or getattr(gm, "from_id", None) or (getattr(so, "id", "") if so else "")).strip()
                                    if uid and uid != my_id and uid != g["id"] and not uid.startswith("-") and uid not in seen:
                                        seen.add(uid)
                                        users.append(uid)
                            except Exception:
                                continue
                        ok = 0
                        for ui, u in enumerate(users, 1):
                            if not st["fwd_running"]:
                                break
                            try:
                                tp = await resolve_peer(c, u)
                                await forward_fast(c, tp, u, src_peer, mid)
                                ok += 1
                                f_stat.value = f"📨 دور {rnd} | ارسال ({ui}/{len(users)}) | موفق: {ok}"
                                safe_update()
                                await asyncio.sleep(1.5)
                            except Exception:
                                await asyncio.sleep(0.5)
                        if not st["fwd_running"]:
                            break
                        mins = max(1, int(int_box.value or 5)) if (int_box.value or "").isdigit() else 5
                        save_json(FORWARD_CFG_FILE, {"interval_min": mins})
                        log(f"دور {rnd} فوروارد تمام شد ({ok} ارسال) ✅", "#10B981")
                        for rem in range(mins * 60, 0, -1):
                            if not st["fwd_running"]:
                                break
                            if rem % 5 == 0 or rem <= 10:
                                f_stat.value = f"✅ دور {rnd} تمام شد ({ok} ارسال). دور بعدی تا {rem} ثانیه..."
                                safe_update()
                            await asyncio.sleep(1.0)
                    except Exception as ex:
                        f_stat.value = f"⚠️ خطا: {ex}"
                        safe_update()
                        await asyncio.sleep(15.0)
                st["fwd_running"] = False
                fb_lbl.value, f_btn.bgcolor = "🚀 شروع فوروارد خودکار", RED_PRIMARY
                safe_update()

            def toggle_f(e):
                if st["fwd_running"]:
                    st["fwd_running"] = False
                    return
                if not st["fwd_source_chat"] or st["fwd_selected_msg_id"] is None:
                    log("کانال/پی‌وی و پیام مبدأ را انتخاب کنید!", RED_NEON)
                    return
                st["fwd_running"] = True
                fb_lbl.value, f_btn.bgcolor = "⛔ توقف فوروارد", RED_DARK
                safe_update()
                asyncio.create_task(fwd_loop())

            rb, _ = make_btn("🔄 بروزرسانی کانال‌ها و پی‌وی‌ها", lambda e: page.run_task(lambda: (fetch_dialogs(80), draw_f_chats())), height=38, expand=True)
            lb, _ = make_btn("📜 پیام‌ها", lambda e: page.run_task(lambda: pick_src(e, src_box.value)), bgcolor=RED_DARK, height=38, expand=True)
            f_btn, fb_lbl = make_btn("⛔ توقف فوروارد" if st["fwd_running"] else "🚀 شروع فوروارد خودکار", toggle_f, bgcolor=RED_DARK if st["fwd_running"] else RED_PRIMARY, height=44)
            draw_f_chats()
            draw_f_msgs()
            return ft.Container(bgcolor=BG_CARD, padding=12, border_radius=ft.BorderRadius.all(12), border=ft.Border.all(1, BORDER_CRIMSON), content=ft.Column(spacing=8, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[ft.Text("📢 فوروارد هوشمند به کاربران فعال گپ‌ها", size=15, weight=ft.FontWeight.BOLD), src_box, ft.Row(spacing=6, controls=[rb, lb]), c_col, m_col, sel_lbl, int_box, f_btn, f_stat]))

        def build_autoreply():
            ar_card, ar_ref = make_toggle_card("🤖 ارسال پیام خودکار در پی‌وی (حالت آفلاین)", "لمس کنید تا روشن یا خاموش شود", bool(ar_cfg.get("enabled", False)), lambda v: (ar_cfg.update({"enabled": v}), save_json(AUTOREPLY_CFG_FILE, ar_cfg), attach_pv_hook(c) if v else None, log("پیام خودکار پی‌وی روشن شد ✅" if v else "خاموش شد."), safe_update()))
            ar_in = ft.TextField(label="متن پیام خودکار (فقط یک بار برای هر نفر)", value=ar_cfg.get("text", ""), multiline=True, min_lines=3, max_lines=4, bgcolor=BG_INPUT, border_color=BORDER_CRIMSON)
            bg_card, bg_ref = make_toggle_card("🔒 سرویس پس‌زمینه اندروید (خروج و بستن برنامه)", "فعال نگه داشتن ساعت و پیام خودکار", bool(clock_cfg.get("bg_keep_alive", True)), lambda v: (clock_cfg.update({"bg_keep_alive": v}), save_json(CLOCK_CFG_FILE, clock_cfg), notify_android_service("start" if v else "stop"), safe_update()))
            rep_lbl = ft.Text(f"تعداد افراد دریافت‌کننده: {len(ar_cfg.get('replied_users', []))} نفر", size=12, color="#10B981")

            sav_b, _ = make_btn("💾 ذخیره متن", lambda e: (ar_cfg.update({"enabled": ar_ref["val"], "text": (ar_in.value or "").strip()}), save_json(AUTOREPLY_CFG_FILE, ar_cfg), log("متن پاسخ خودکار ذخیره شد ✅", "#10B981")), height=40, expand=True)
            rst_b, _ = make_btn("🗑️ ریست افراد", lambda e: (ar_cfg.update({"replied_users": []}), save_json(AUTOREPLY_CFG_FILE, ar_cfg), setattr(rep_lbl, "value", "تعداد افراد دریافت‌کننده: 0 نفر"), safe_update()), bgcolor=RED_DARK, height=40, expand=True)
            bat_b, _ = make_btn("🔋 حذف محدودیت باتری گوشی", lambda e: notify_android_service("battery"), bgcolor=BG_INPUT, color="#F59E0B", height=36)
            return ft.Container(bgcolor=BG_CARD, padding=12, border_radius=ft.BorderRadius.all(12), border=ft.Border.all(1, BORDER_CRIMSON), content=ft.Column(spacing=8, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[ft.Text("🤖 پیام خودکار پی‌وی (حالت آفلاین)", size=15, weight=ft.FontWeight.BOLD), ar_card, ar_in, bg_card, bat_b, rep_lbl, ft.Row(spacing=6, controls=[sav_b, rst_b])]))

        def build_clock():
            clk_card, clk_ref = make_toggle_card("⏰ ساعت افق تهران کنار اسم پروفایل", "لمس کنید تا روشن یا خاموش شود", bool(clock_cfg.get("enabled", False)), lambda v: (clock_cfg.update({"enabled": v}), save_json(CLOCK_CFG_FILE, clock_cfg), safe_update()))
            bg_card, bg_ref = make_toggle_card("🔒 سرویس پس‌زمینه اندروید (خروج و بستن برنامه)", "فعال نگه داشتن ساعت و پیام خودکار", bool(clock_cfg.get("bg_keep_alive", True)), lambda v: (clock_cfg.update({"bg_keep_alive": v}), save_json(CLOCK_CFG_FILE, clock_cfg), notify_android_service("start" if v else "stop"), safe_update()))
            bf_in = ft.TextField(label="نام اصلی (بدون ساعت)", value=clock_cfg.get("base_first", ""), bgcolor=BG_INPUT, border_color=BORDER_CRIMSON)
            bl_in = ft.TextField(label="نام خانوادگی (اختیاری)", value=clock_cfg.get("base_last", ""), bgcolor=BG_INPUT, border_color=BORDER_CRIMSON)
            sep_in = ft.TextField(label="جداکننده", value=clock_cfg.get("sep", "|"), bgcolor=BG_INPUT, border_color=BORDER_CRIMSON)
            sty = {"v": clock_cfg.get("style", "bold"), "p": clock_cfg.get("target_field", "first")}

            async def apply_clk(e):
                bf, bl = strip_clock(bf_in.value or ""), strip_clock(bl_in.value or "")
                if not bf and not bl:
                    try:
                        me = await asyncio.wait_for(c.get_me(), timeout=8.0)
                        bf, bl = strip_clock(getattr(me, "first_name", "") or ""), strip_clock(getattr(me, "last_name", "") or "")
                        bf_in.value, bl_in.value = bf, bl
                    except Exception:
                        pass
                clock_cfg.update({"enabled": clk_ref["val"], "bg_keep_alive": bg_ref["val"], "base_first": bf, "base_last": bl, "style": sty["v"], "target_field": sty["p"], "sep": (sep_in.value or "|").strip()})
                save_json(CLOCK_CFG_FILE, clock_cfg)
                notify_android_service("start" if bg_ref["val"] else "stop")
                st["last_clock_min"] = ""
                if clk_ref["val"]:
                    await sync_clock(c, force=True)
                else:
                    await apply_profile_name(c, bf or "User", bl)
                    log("ساعت غیرفعال شد ✅", RED_LIGHT)
                safe_update()

            sn, _ = make_btn("14:30", lambda e: (sty.update({"v": "normal"}), setattr(sn, "bgcolor", RED_PRIMARY), setattr(sb, "bgcolor", BG_INPUT), setattr(sm, "bgcolor", BG_INPUT), safe_update()), bgcolor=RED_PRIMARY if sty["v"] == "normal" else BG_INPUT, height=34, expand=True)
            sb, _ = make_btn("𝟏𝟒:𝟑𝟎", lambda e: (sty.update({"v": "bold"}), setattr(sb, "bgcolor", RED_PRIMARY), setattr(sn, "bgcolor", BG_INPUT), setattr(sm, "bgcolor", BG_INPUT), safe_update()), bgcolor=RED_PRIMARY if sty["v"] == "bold" else BG_INPUT, height=34, expand=True)
            sm, _ = make_btn("𝟷𝟺:𝟹𝟶", lambda e: (sty.update({"v": "mono"}), setattr(sm, "bgcolor", RED_PRIMARY), setattr(sn, "bgcolor", BG_INPUT), setattr(sb, "bgcolor", BG_INPUT), safe_update()), bgcolor=RED_PRIMARY if sty["v"] == "mono" else BG_INPUT, height=34, expand=True)
            pf, _ = make_btn("کنار اسم", lambda e: (sty.update({"p": "first"}), setattr(pf, "bgcolor", RED_PRIMARY), setattr(pl, "bgcolor", BG_INPUT), safe_update()), bgcolor=RED_PRIMARY if sty["p"] == "first" else BG_INPUT, height=34, expand=True)
            pl, _ = make_btn("کنار فامیل", lambda e: (sty.update({"p": "last"}), setattr(pl, "bgcolor", RED_PRIMARY), setattr(pf, "bgcolor", BG_INPUT), safe_update()), bgcolor=RED_PRIMARY if sty["p"] == "last" else BG_INPUT, height=34, expand=True)
            ap_b, _ = make_btn("💾 ذخیره و اعمال ساعت", apply_clk, height=44)
            bat_b, _ = make_btn("🔋 حذف محدودیت باتری گوشی", lambda e: notify_android_service("battery"), bgcolor=BG_INPUT, color="#F59E0B", height=36)
            return ft.Container(bgcolor=BG_CARD, padding=12, border_radius=ft.BorderRadius.all(12), border=ft.Border.all(1, BORDER_CRIMSON), content=ft.Column(spacing=8, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[ft.Text("⏰ ساعت افق تهران کنار اسم", size=15, weight=ft.FontWeight.BOLD), clk_card, bg_card, bat_b, bf_in, bl_in, sep_in, ft.Row(spacing=5, controls=[sn, sb, sm]), ft.Row(spacing=5, controls=[pf, pl]), ap_b]))

        def render_tab():
            body_host.controls.clear()
            t = st["active_tab"]
            body_host.controls.append({"chats": build_chats, "multi": build_multi, "turbo": build_turbo, "forward": build_forward, "autoreply": build_autoreply, "clock": build_clock}[t]())

        def switch_tab(e, name: str):
            if st["active_tab"] != name:
                st["active_tab"] = name
                for k, b in nav.items():
                    b.bgcolor = RED_PRIMARY if k == name else BG_INPUT
                render_tab()
                safe_update()

        async def logout(e):
            st.update({"in_dashboard": False, "turbo_running": False, "multi_running": False, "fwd_running": False})
            notify_android_service("stop")
            try:
                await c.log_out()
            except Exception:
                pass
            st["client"] = None
            for f in os.listdir(STORAGE_DIR):
                if f.startswith(os.path.basename(SESSION_PATH)):
                    try:
                        os.remove(os.path.join(STORAGE_DIR, f))
                    except Exception:
                        pass
            show_phone("از حساب خارج شدید.")

        out_b, _ = make_btn("خروج", logout, color=RED_NEON, kind="text")
        b1, _ = make_btn("💬 چت‌ها", lambda e: switch_tab(e, "chats"), bgcolor=RED_PRIMARY, height=36, expand=True)
        b2, _ = make_btn("📨 چندتایی", lambda e: switch_tab(e, "multi"), bgcolor=BG_INPUT, height=36, expand=True)
        b3, _ = make_btn("🚀 توربو", lambda e: switch_tab(e, "turbo"), bgcolor=BG_INPUT, height=36, expand=True)
        b4, _ = make_btn("📢 فوروارد", lambda e: switch_tab(e, "forward"), bgcolor=BG_INPUT, height=36, expand=True)
        b5, _ = make_btn("🤖 پی‌وی خودکار", lambda e: switch_tab(e, "autoreply"), bgcolor=BG_INPUT, height=36, expand=True)
        b6, _ = make_btn("⏰ ساعت", lambda e: switch_tab(e, "clock"), bgcolor=BG_INPUT, height=36, expand=True)
        nav = {"chats": b1, "multi": b2, "turbo": b3, "forward": b4, "autoreply": b5, "clock": b6}
        render_tab()

        page.add(
            ft.Container(bgcolor=BG_CARD, padding=10, border_radius=ft.BorderRadius.all(12), border=ft.Border.all(1.2, BORDER_ACTIVE), content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Row(spacing=8, controls=[ft.Text("⚡ V3X Selfbot", size=17, weight=ft.FontWeight.BOLD, color=RED_NEON), conn_badge]), out_b])),
            ft.Row(spacing=5, controls=[b1, b2, b3]),
            ft.Row(spacing=5, controls=[b4, b5, b6]),
            body_host,
            ft.Container(bgcolor=BG_CARD, padding=10, border_radius=ft.BorderRadius.all(12), border=ft.Border.all(1, BORDER_CRIMSON), content=ft.Column(spacing=4, controls=[ft.Text("📜 گزارش عملکرد", size=12, color=RED_LIGHT), logs])),
            footer_box(),
        )
        safe_update()
        notify_android_service("start" if clock_cfg.get("bg_keep_alive", True) else "stop")
        asyncio.create_task(fetch_dialogs())

    saved = str(load_json(LIC_FILE, {}).get("key", "")).strip()
    if saved:
        status, m, _, upd = await check_license(saved, did)
        if status == "OUTDATED":
            show_update_required(m, upd)
            return
        if status == "OK":
            await proceed_after_license()
            return
        try:
            os.remove(LIC_FILE)
        except Exception:
            pass
        show_license(m)
        return
    show_license()


if hasattr(ft, "run"):
    ft.run(main)
else:
    ft.app(target=main)
# END_OF_V3X_MAIN
