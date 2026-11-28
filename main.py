import asyncio, datetime, hashlib, importlib, inspect, json, os, pkgutil, platform, random, re, sqlite3, subprocess, tempfile, time, urllib.request
import flet as ft, httpx

for _cls, _attrs in (
    ("Padding", {"only": lambda left=0, top=0, right=0, bottom=0: ft.Padding(left=left, top=top, right=right, bottom=bottom), "all": lambda v: ft.Padding(left=v, top=v, right=v, bottom=v), "symmetric": lambda vertical=0, horizontal=0: ft.Padding(left=horizontal, top=vertical, right=horizontal, bottom=vertical)}),
    ("Margin", {"only": lambda left=0, top=0, right=0, bottom=0: ft.Margin(left=left, top=top, right=right, bottom=bottom), "all": lambda v: ft.Margin(left=v, top=v, right=v, bottom=v), "symmetric": lambda vertical=0, horizontal=0: ft.Margin(left=horizontal, top=vertical, right=horizontal, bottom=vertical)}),
    ("Border", {"all": lambda width=1, color=None: ft.Border(top=ft.BorderSide(width, color), right=ft.BorderSide(width, color), bottom=ft.BorderSide(width, color), left=ft.BorderSide(width, color))}),
    ("BorderRadius", {"all": lambda v: ft.BorderRadius(top_left=v, top_right=v, bottom_left=v, bottom_right=v)}),
):
    _obj = getattr(ft, _cls, None)
    if _obj:
        for _k, _fn in _attrs.items():
            if not hasattr(_obj, _k):
                setattr(_obj, _k, staticmethod(_fn))
        _low = getattr(ft, re.sub(r'(?<!^)(?=[A-Z])', '_', _cls).lower(), None)
        if _low and not hasattr(_low, "all"):
            for _k in _attrs:
                if hasattr(_obj, _k):
                    setattr(_low, _k, getattr(_obj, _k))

APP_VERSION, WEBSITE_URL, LICENSE_URL, CREATOR_ID = "2.9.0", "https://v3xsys.pages.dev/", "https://selfbot-license.krymyhady314.workers.dev", "@V3XSYS"
BG_GALAXY, BG_CARD, BG_INPUT = "#030306", "#0A0A12", "#12121D"
RED_PRIMARY, RED_DARK, RED_NEON, RED_LIGHT = "#DC2626", "#991B1B", "#FF1E42", "#EF4444"
BORDER_CRIMSON, BORDER_ACTIVE, TEXT_WHITE, TEXT_MUTED = "#450A0A", "#EF4444", "#FFFFFF", "#CBD5E1"
TEHRAN_TZ = datetime.timezone(datetime.timedelta(hours=3, minutes=30))

STORAGE_DIR = os.getenv("FLET_APP_STORAGE_DATA") or tempfile.gettempdir()
os.makedirs(STORAGE_DIR, exist_ok=True)
DEV_FILE, LIC_FILE, SESSION_PATH = os.path.join(STORAGE_DIR, "v3x_dev.txt"), os.path.join(STORAGE_DIR, "v3x_lic.json"), os.path.join(STORAGE_DIR, "v3x_splus")
SAVED_MSGS_FILE, CLOCK_CFG_FILE = os.path.join(STORAGE_DIR, "v3x_saved_msgs.json"), os.path.join(STORAGE_DIR, "v3x_clock_cfg.json")

def bind_async(fn, *args):
    async def _h(e): await fn(e, *args)
    return _h

def boost_sqlite_session(client=None):
    try:
        conn = getattr(getattr(client, "session", None), "_conn", None)
        if conn is not None:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=OFF;")
            conn.execute("PRAGMA temp_store=MEMORY;")
            conn.execute("PRAGMA cache_size=-8000;")
            return
    except Exception:
        pass
    for fn in os.listdir(STORAGE_DIR):
        if fn.startswith("v3x_splus") and not fn.endswith(("-wal", "-shm")):
            p = os.path.join(STORAGE_DIR, fn)
            try:
                con = sqlite3.connect(p, timeout=1.0)
                con.execute("PRAGMA journal_mode=WAL;")
                con.execute("PRAGMA synchronous=OFF;")
                con.close()
            except Exception:
                pass

def load_json(path: str, default):
    try:
        if os.path.exists(path):
            data = json.load(open(path, "r", encoding="utf-8"))
            if isinstance(default, dict) and isinstance(data, dict): return {**default, **data}
            if isinstance(default, list) and isinstance(data, list) and data: return data
    except Exception: pass
    return dict(default) if isinstance(default, dict) else list(default)

def save_json(path: str, data):
    try: json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception: pass

def parse_ver(v: str) -> tuple[int, ...]:
    nums = re.findall(r"\d+", str(v or "0"))
    return tuple(int(x) for x in nums) if nums else (0,)

def get_device_id() -> str:
    parts = [platform.system(), platform.machine(), platform.node()]
    for p in ("ro.product.brand", "ro.product.model", "ro.product.device", "ro.build.id"):
        try:
            out = subprocess.check_output(["getprop", p], stderr=subprocess.DEVNULL, timeout=1).decode().strip()
            if out: parts.append(out)
        except Exception: pass
    did = "V3X-" + hashlib.sha256("|".join(parts).encode()).hexdigest()[:16].upper()
    try: open(DEV_FILE, "w", encoding="utf-8").write(did)
    except Exception: pass
    return did

def notify_android(cmd: str):
    def _p():
        try: urllib.request.urlopen(f"http://127.0.0.1:48391/{cmd}", timeout=0.6).read()
        except Exception: pass
    try: asyncio.get_running_loop().run_in_executor(None, _p)
    except Exception: _p()

def format_clock(style: str = "bold") -> str:
    raw = datetime.datetime.now(TEHRAN_TZ).strftime("%H:%M")
    if style == "bold": return raw.translate(str.maketrans("0123456789", "𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"))
    if style == "mono": return raw.translate(str.maketrans("0123456789", "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"))
    return raw

def strip_clock(name: str) -> str:
    return re.sub(r"\s*[\|•\-–—]?\s*[0-9𝟎-𝟗𝟶-𝟿]{2}:[0-9𝟎-𝟗𝟶-𝟿]{2}\s*$", "", (name or "").strip()).strip()

def clean_key(raw: str) -> str:
    txt = re.sub(r"[\u200b-\u200f\ufeff`\"'\s]", "", str(raw or "").translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩–—−", "01234567890123456789---")))
    m = re.search(r"(V3X-[A-Za-z0-9\-_]{3,})", txt, re.I)
    return m.group(1).upper() if m else txt.upper()

async def check_license(raw_key: str, did: str) -> tuple[str, str, str, str]:
    ck = clean_key(raw_key)
    if not ck: return "ERROR", "لطفاً کلید لایسنس را وارد کنید.", "", WEBSITE_URL
    payload = {"action": "verify", "source": "app", "key": ck, "license": ck, "hwid": did, "device_id": did, "app_version": APP_VERSION}
    base, err = LICENSE_URL.rstrip("/"), "عدم اتصال به سرور لایسنس؛ اینترنت خود را بررسی کنید."
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http:
        for mode, url in (("POST", f"{base}/api/verify"), ("POST", f"{base}/verify"), ("GET", f"{base}/verify"), ("GET", base), ("POST", base)):
            try:
                r = await (http.post(url, params=payload, json=payload) if mode == "POST" else http.get(url, params=payload))
                if r.status_code in (404, 405): continue
                d = r.json()
                if not isinstance(d, dict): continue
                upd = str(d.get("update_url") or d.get("download_url") or WEBSITE_URL)
                sv, mv = str(d.get("status", "")).lower().strip(), str(d.get("min_version") or d.get("required_version") or "").strip()
                if d.get("force_update") or d.get("outdated") or sv in ("outdated", "update_required", "disabled") or (mv and parse_ver(APP_VERSION) < parse_ver(mv)):
                    return "OUTDATED", str(d.get("message") or f"نسخه فعلی ({APP_VERSION}) غیرفعال شده است."), ck, upd
                if d.get("valid") or d.get("ok") or d.get("success") or sv in ("valid", "ok", "active", "success"):
                    return "OK", str(d.get("message") or d.get("msg") or "لایسنس تایید شد ✅"), ck, upd
                msg = d.get("message") or d.get("error") or d.get("reason") or d.get("msg")
                if msg: return "ERROR", str(msg), ck, upd
            except Exception as e: err = f"خطا در ارتباط با سرور: {e}"
    return "ERROR", err, ck, WEBSITE_URL

def create_splus_client():
    import splusthon
    cls = next((getattr(splusthon, n) for n in ("SPlusClient", "Client", "SoroushClient", "UserClient") if inspect.isclass(getattr(splusthon, n, None))), None)
    if cls is None and hasattr(splusthon, "__path__"):
        for _, mn, _ in pkgutil.walk_packages(splusthon.__path__, "splusthon."):
            try:
                m = importlib.import_module(mn)
                cls = next((o for n, o in inspect.getmembers(m, inspect.isclass) if o.__module__ == mn and "client" in n.lower() and "base" not in n.lower()), None)
                if cls: break
            except Exception: pass
    if cls is None: raise RuntimeError("کلاس کلاینت در splusthon یافت نشد")
    try: c = cls(SESSION_PATH, connection_retries=-1, retry_delay=1, auto_reconnect=True)
    except TypeError: c = cls(SESSION_PATH)
    boost_sqlite_session(c)
    return c

async def apply_profile_name(c, first: str, last: str):
    fn = getattr(c, "update_profile", None)
    if callable(fn):
        r = fn(first_name=first, last_name=last)
        if inspect.isawaitable(r): await asyncio.wait_for(r, timeout=8.0)
        return
    for mp in ("splusthon.tl.functions.account", "splusthon.functions.account"):
        try:
            req = getattr(importlib.import_module(mp), "UpdateProfileRequest", None)
            if req: await asyncio.wait_for(c(req(first_name=first, last_name=last)), timeout=8.0); return
        except Exception: pass
    raise RuntimeError("متد تغییر نام پروفایل یافت نشد.")

async def to_list(res, timeout: float = 14.0) -> list:
    if res is None: return []
    if hasattr(res, "__aiter__"): return [x async for x in res]
    if inspect.isawaitable(res): res = await asyncio.wait_for(res, timeout=timeout)
    if res is None: return []
    if hasattr(res, "__aiter__"): return [x async for x in res]
    if isinstance(res, list): return res
    for a in ("dialogs", "chats", "messages", "users", "participants", "members", "items", "results"):
        v = getattr(res, a, None) if not isinstance(res, dict) else res.get(a)
        if isinstance(v, list): return v
    try: return list(res)
    except Exception: return []

def is_perm_denied(err_str: str) -> bool:
    low = (err_str or "").lower()
    return any(k in low for k in ("admin", "right", "forbidden", "403", "permission", "not enough", "دسترسی", "مجاز", "ادمین"))

def make_btn(label: str, on_click, bgcolor: str = RED_PRIMARY, color: str = TEXT_WHITE, height: int = 40, kind: str = "filled", expand: bool = False):
    lbl = ft.Text(label, color=color, weight=ft.FontWeight.W_600, size=12)
    if kind == "outlined": return (getattr(ft, "OutlinedButton", None) or ft.ElevatedButton)(content=lbl, on_click=on_click, height=height, expand=expand), lbl
    if kind == "text": return (getattr(ft, "TextButton", None) or ft.ElevatedButton)(content=lbl, on_click=on_click, expand=expand), lbl
    return (getattr(ft, "ElevatedButton", None) or getattr(ft, "Button", None))(content=lbl, bgcolor=bgcolor, color=color, height=height, on_click=on_click, expand=expand), lbl

def make_toggle(title: str, sub: str, init: bool, on_toggle):
    ref = {"val": bool(init)}
    bt = ft.Text("✅ روشن" if ref["val"] else "⭕ خاموش", size=12, weight=ft.FontWeight.BOLD, color="#10B981" if ref["val"] else RED_NEON)
    bb = ft.Container(padding=ft.Padding.symmetric(horizontal=12, vertical=6), border_radius=ft.BorderRadius.all(10), bgcolor="#06281E" if ref["val"] else "#26080E", border=ft.Border.all(1.5, "#10B981" if ref["val"] else RED_NEON), content=bt)
    card = ft.Container(padding=ft.Padding.all(11), border_radius=ft.BorderRadius.all(12), ink=True, bgcolor="#0C1F1A" if ref["val"] else "#180A10", border=ft.Border.all(1.5, "#10B981" if ref["val"] else BORDER_ACTIVE), content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=8, controls=[ft.Column(spacing=2, expand=True, controls=[ft.Text(title, size=13, weight=ft.FontWeight.BOLD, color=TEXT_WHITE), ft.Text(sub, size=11, color=TEXT_MUTED)]), bb]))
    async def _clk(e):
        ref["val"] = not ref["val"]; v = ref["val"]
        bt.value, bt.color = ("✅ روشن" if v else "⭕ خاموش"), ("#10B981" if v else RED_NEON)
        bb.bgcolor, bb.border = ("#06281E" if v else "#26080E"), ft.Border.all(1.5, "#10B981" if v else RED_NEON)
        card.bgcolor, card.border = ("#0C1F1A" if v else "#180A10"), ft.Border.all(1.5, "#10B981" if v else BORDER_ACTIVE)
        r = on_toggle(v)
        if inspect.isawaitable(r): await r
    card.on_click = _clk
    return card, ref

def footer_box():
    return ft.Container(margin=ft.Margin.only(top=6), padding=ft.Padding.symmetric(vertical=8, horizontal=12), border_radius=ft.BorderRadius.all(10), bgcolor=BG_CARD, border=ft.Border.all(1, BORDER_CRIMSON), content=ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[ft.Text(f"نسخه {APP_VERSION}  |  طراحی و توسعه: ", size=11, color=TEXT_MUTED), ft.Text(CREATOR_ID, size=12, weight=ft.FontWeight.BOLD, color=RED_NEON, selectable=True)]))

async def main(page: ft.Page):
    page.title, page.bgcolor, page.theme_mode, page.scroll, page.rtl = "V3X Selfbot Pro", BG_GALAXY, ft.ThemeMode.DARK, ft.ScrollMode.AUTO, True
    page.padding = ft.Padding.only(top=32, left=10, right=10, bottom=10)

    did = get_device_id()
    clock_cfg = load_json(CLOCK_CFG_FILE, {"enabled": False, "base_first": "", "base_last": "", "style": "bold", "target_field": "first", "sep": "|", "bg_keep_alive": True})
    rec_lock, clk_lock = asyncio.Lock(), asyncio.Lock()

    st = {
        "client": None, "me_id": None, "phone": "", "hash": None, "need_2fa": False, "bg_started": False,
        "last_clock_min": "", "last_clock_sync_str": "هنوز آپدیت نشده", "last_net_ok": 0.0, "last_rec_ts": 0.0,
        "active_tab": "chats", "chat_filter": "all", "dialogs": [], "dialogs_loading": True,
        "selected_targets": {}, "active_target": "", "recent_messages": [], "reply_to_id": None, "reply_to_preview": "", "reply_chat_id": "",
        "multi_messages": load_json(SAVED_MSGS_FILE, ["سلام!", "چطوری؟", "خوبی؟", "چه خبر؟", "پیام تست V3X"]),
        "multi_rounds": "10", "multi_rate": "10", "multi_delay": "0", "multi_running": False, "multi_status": "آماده ارسال چندتایی",
        "turbo_count": "100", "turbo_rate": "10", "turbo_delay": "0", "turbo_running": False, "turbo_status": "آماده ارسال توربو",
        "anti_lag": True, "reply_hop": False, "entity_cache": {},
        "kick_target_id": "", "kick_target_title": "", "kick_has_perm": None, "kick_members_count": 0,
        "kick_running": False, "kick_status": "یک گپ را از لیست زیر انتخاب کنید",
    }
    logs = ft.Column(spacing=2, height=75, scroll=ft.ScrollMode.AUTO)
    conn_badge = ft.Text("🟢 متصل", size=12, color="#10B981", weight=ft.FontWeight.W_600)

    def safe_up():
        try: page.update()
        except Exception: pass

    def up_ctrl(c):
        try:
            if getattr(c, "page", None) is not None: c.update()
        except Exception: pass

    def log(txt: str, col: str = TEXT_MUTED):
        if st["turbo_running"] or st["multi_running"]: return
        logs.controls.insert(0, ft.Text(f"[{time.strftime('%H:%M:%S')}] {txt}", size=11, color=col))
        del logs.controls[10:]
        up_ctrl(logs) if getattr(logs, "page", None) else safe_up()

    def get_client():
        if st["client"] is None: st["client"] = create_splus_client()
        return st["client"]

    async def get_my_id(c) -> str:
        if st["me_id"]: return st["me_id"]
        try:
            me = await asyncio.wait_for(c.get_me(), timeout=7.0)
            uid = getattr(me, "id", None) or getattr(me, "user_id", None) or getattr(me, "guid", None)
            if uid is not None: st["me_id"] = str(uid)
        except Exception: pass
        return st["me_id"] or ""

    async def ensure_online(c, reset: bool = False) -> bool:
        async with rec_lock:
            now = time.monotonic()
            if c.is_connected() and (not reset or (now - st["last_rec_ts"] < 4.0)):
                return True
            try:
                if reset:
                    st["last_rec_ts"] = now
                    try: await asyncio.wait_for(c.disconnect(), timeout=2.5)
                    except Exception: pass
                    await asyncio.sleep(0.3)
                if not c.is_connected():
                    conn_badge.value, conn_badge.color = "🟡 اتصال مجدد...", "#F59E0B"; up_ctrl(conn_badge)
                    await asyncio.wait_for(c.connect(), timeout=10.0); st["last_rec_ts"] = time.monotonic()
                if conn_badge.value != "🟢 متصل":
                    conn_badge.value, conn_badge.color = "🟢 متصل", "#10B981"; up_ctrl(conn_badge)
                st["last_net_ok"] = time.monotonic()
                return True
            except Exception:
                conn_badge.value, conn_badge.color = "🔴 قطع اتصال", RED_NEON; up_ctrl(conn_badge)
                return False

    async def verify_alive(c):
        if st["turbo_running"] or st["multi_running"] or st["kick_running"]: return
        if not c.is_connected(): await ensure_online(c, False); return
        if time.monotonic() - st["last_net_ok"] > 45.0:
            try: await asyncio.wait_for(c.get_me(), timeout=5.0); st["last_net_ok"] = time.monotonic()
            except Exception: await ensure_online(c, True)

    async def resolve_peer(c, raw: str):
        k = (raw or "").strip()
        if not k: return None
        if k in st["entity_cache"]: return st["entity_cache"][k]
        p = int(k) if k.lstrip("-").isdigit() else k
        for mn in ("get_input_entity", "get_entity"):
            fn = getattr(c, mn, None)
            if callable(fn):
                try:
                    ent = await asyncio.wait_for(fn(p), timeout=7.0)
                    if ent is not None: st["entity_cache"][k] = ent; return ent
                except Exception: pass
        return p

    async def get_dialogs_list(c, lim: int = 80) -> list:
        for mn in ("get_dialogs", "iter_dialogs", "get_chats"):
            fn = getattr(c, mn, None)
            if callable(fn):
                try:
                    items = await to_list(fn(limit=lim) if "limit" in inspect.signature(fn).parameters else fn())
                    if items: st["last_net_ok"] = time.monotonic(); return items
                except Exception: pass
        return []

    async def get_msgs_list(c, peer, lim: int = 15) -> list:
        for mn in ("get_messages", "iter_messages", "get_history"):
            fn = getattr(c, mn, None)
            if callable(fn):
                try:
                    items = await to_list(fn(peer, limit=lim) if "limit" in inspect.signature(fn).parameters else fn(peer))
                    if items: st["last_net_ok"] = time.monotonic(); return items
                except Exception: pass
        return []

    async def get_group_members(c, peer, my_id: str) -> list:
        raw_users = []
        for mn in ("get_participants", "iter_participants", "get_members", "iter_members", "get_chat_members"):
            fn = getattr(c, mn, None)
            if not callable(fn): continue
            try:
                sig = inspect.signature(fn).parameters
                res = fn(peer, limit=5000) if "limit" in sig else fn(peer)
                raw_users = await to_list(res, timeout=20.0)
                if raw_users: break
            except TypeError:
                try:
                    raw_users = await to_list(fn(peer), timeout=20.0)
                    if raw_users: break
                except Exception: pass
            except Exception as ex:
                if is_perm_denied(str(ex)): raise ex

        members, seen = [], set()
        for u in raw_users:
            user_obj = getattr(u, "user", None) or u
            uid = getattr(user_obj, "id", None) or getattr(user_obj, "user_id", None) or getattr(user_obj, "guid", None)
            if uid is None: continue
            uid_str = str(uid).strip()
            if not uid_str or uid_str == my_id or uid_str in seen: continue
            part = getattr(u, "participant", None)
            if part and (getattr(part, "is_creator", False) or "creator" in type(part).__name__.lower()):
                continue
            seen.add(uid_str)
            members.append(user_obj)
        return members

    async def check_group_admin_perm(c, peer) -> bool | None:
        gp = getattr(c, "get_permissions", None)
        if callable(gp):
            try:
                p = await asyncio.wait_for(gp(peer), timeout=7.0)
                if p is not None:
                    if getattr(p, "is_creator", False) or getattr(p, "is_admin", False) or getattr(p, "ban_users", False):
                        return True
                    return False
            except Exception as ex:
                if is_perm_denied(str(ex)): return False
        ge = getattr(c, "get_entity", None)
        if callable(ge):
            try:
                ent = await asyncio.wait_for(ge(peer), timeout=7.0)
                if getattr(ent, "creator", False) or getattr(ent, "admin_rights", None):
                    return True
            except Exception: pass
        return None

    async def kick_one_member(c, peer, user_obj, method_box: dict) -> str:
        """حذف یک ممبر از گپ؛ خروجی: 'OK' | 'NO_PERM' | 'ERR'"""
        uid = getattr(user_obj, "id", None) or getattr(user_obj, "user_id", None) or user_obj
        candidates = []

        if callable(getattr(c, "kick_participant", None)):
            candidates.append(("kick_participant", lambda: c.kick_participant(peer, user_obj)))
        if callable(getattr(c, "edit_permissions", None)):
            candidates.append(("edit_permissions", lambda: c.edit_permissions(peer, user_obj, view_messages=False)))
        for mn in ("kick_user", "remove_user", "ban_user", "delete_chat_user", "remove_chat_member"):
            fn = getattr(c, mn, None)
            if callable(fn):
                candidates.append((mn, lambda f=fn: f(peer, uid)))

        if method_box.get("name"):
            candidates.sort(key=lambda x: 0 if x[0] == method_box["name"] else 1)

        for att in range(1, 3):
            for name, caller in candidates:
                try:
                    r = caller()
                    if inspect.isawaitable(r): await asyncio.wait_for(r, timeout=8.0)
                    method_box["name"] = name
                    st["last_net_ok"] = time.monotonic()
                    return "OK"
                except TypeError:
                    continue
                except Exception as ex:
                    es = str(ex)
                    if is_perm_denied(es):
                        return "NO_PERM"
                    w = getattr(ex, "seconds", None) or (int(m.group(1)) if (m := re.search(r"(?:wait of|flood_wait[_ ]?)(\d+)", es.lower())) else None)
                    if w:
                        await asyncio.sleep(min(int(w) + 1, 15))
                        break
            await asyncio.sleep(0.15)
        return "ERR"

    async def _call_send(fn, peer, txt: str, rep=None):
        if rep is not None:
            for kw in ("reply_to", "reply_to_msg_id", "reply_to_message_id"):
                try:
                    r = fn(peer, txt, **{kw: rep})
                    return await asyncio.wait_for(r, timeout=4.5) if inspect.isawaitable(r) else r
                except TypeError: continue
        r = fn(peer, txt)
        return await asyncio.wait_for(r, timeout=4.5) if inspect.isawaitable(r) else r

    async def send_pipeline_msg(c, peer, raw_t: str, text: str, rep=None, rpool: list | None = None, flood_box: list | None = None) -> bool:
        sfn = getattr(c, "send_message", None) or getattr(c, "send_text", None)
        if not callable(sfn): return False
        exact_text = (text or "").strip()
        if not exact_text: return False
        eff_rep = random.choice(rpool) if (rep is None and rpool and random.random() < 0.5) else rep
        for att in range(1, 3):
            try:
                if not c.is_connected():
                    await ensure_online(c, False)
                    peer = await resolve_peer(c, raw_t)
                await _call_send(sfn, peer, exact_text, eff_rep)
                st["last_net_ok"] = time.monotonic()
                return True
            except Exception as ex:
                w = getattr(ex, "seconds", None) or (int(m.group(1)) if (m := re.search(r"(?:wait of|flood_wait[_ ]?)(\d+)", str(ex).lower())) else None)
                if w:
                    slp = min(int(w) + 1, 15)
                    if flood_box is not None: flood_box[0] = slp
                    await asyncio.sleep(slp)
                    if flood_box is not None: flood_box[0] = 0
                    continue
                if att == 1:
                    st["entity_cache"].pop((raw_t or "").strip(), None)
                    peer = await resolve_peer(c, raw_t)
                    await asyncio.sleep(0.08)
        return False

    async def sync_clock(c, force: bool = False):
        if not clock_cfg.get("enabled"): return
        now_m = datetime.datetime.now(TEHRAN_TZ).strftime("%H:%M")
        if (not force and st["last_clock_min"] == now_m) or clk_lock.locked(): return
        async with clk_lock:
            for att in (1, 2):
                try:
                    await verify_alive(c)
                    if not clock_cfg.get("base_first"):
                        me = await asyncio.wait_for(c.get_me(), timeout=7.0)
                        clock_cfg["base_first"], clock_cfg["base_last"] = strip_clock(getattr(me, "first_name", "") or ""), strip_clock(getattr(me, "last_name", "") or "")
                        save_json(CLOCK_CFG_FILE, clock_cfg)
                    clk, sep, bf, bl = format_clock(clock_cfg.get("style", "bold")), clock_cfg.get("sep", "|"), clock_cfg.get("base_first", ""), clock_cfg.get("base_last", "")
                    nf, nl = (bf, f"{bl} {sep} {clk}".strip() if bl else clk) if clock_cfg.get("target_field") == "last" else (f"{bf} {sep} {clk}".strip() if bf else clk, bl)
                    await apply_profile_name(c, nf, nl)
                    st["last_clock_min"], st["last_clock_sync_str"], st["last_net_ok"] = now_m, datetime.datetime.now(TEHRAN_TZ).strftime("%H:%M:%S"), time.monotonic()
                    log(f"⏰ ساعت آپدیت شد: {nf} {nl}".strip(), RED_LIGHT); return
                except Exception as ex:
                    if att == 1 and not (st["turbo_running"] or st["multi_running"] or st["kick_running"]): await ensure_online(c, True)
                    else: log(f"خطای ساعت: {ex}", RED_NEON)

    async def start_bg(c):
        if st["bg_started"]: return
        st["bg_started"] = True
        async def _tick(r, w):
            try: await asyncio.wait_for(r.read(256), timeout=1.0); w.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nOK"); await w.drain(); w.close()
            except Exception: pass
            if clock_cfg.get("enabled"): asyncio.create_task(sync_clock(c, False))
        try: await asyncio.start_server(_tick, "127.0.0.1", 48392)
        except Exception: pass
        async def _loop():
            while st["client"] is not None:
                try:
                    if clock_cfg.get("enabled"): await sync_clock(c, False)
                except Exception: pass
                await asyncio.sleep(max(1.5, 60.2 - datetime.datetime.now(TEHRAN_TZ).second) if clock_cfg.get("enabled") else 5.0)
        asyncio.create_task(_loop())

    def show_update(msg: str, url: str):
        page.controls.clear()
        ub, st_t = ft.TextField(label="آدرس سایت رسمی", value=url or WEBSITE_URL, read_only=True, text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_ACTIVE), ft.Text("", size=12, color="#10B981")
        async def _dl(e):
            try:
                if hasattr(page, "launch_url"):
                    r = page.launch_url(url or WEBSITE_URL)
                    if inspect.isawaitable(r): await r
                if hasattr(ft, "Clipboard"): await ft.Clipboard().set(url or WEBSITE_URL)
                st_t.value = "لینک کپی شد ✅"
            except Exception: st_t.value = "لینک بالا را کپی کنید."
            safe_up()
        b, _ = make_btn("🌐 ورود به سایت و دانلود نسخه جدید", _dl, height=46)
        page.add(ft.Container(bgcolor=BG_CARD, padding=18, border_radius=ft.BorderRadius.all(14), border=ft.Border.all(1.5, RED_NEON), content=ft.Column(spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[ft.Text("⚠️ این نسخه غیرفعال شده است", size=19, weight=ft.FontWeight.BOLD, color=RED_NEON), ft.Text(msg, size=13, color=TEXT_WHITE), ub, b, st_t])), footer_box()); safe_up()

    async def after_lic():
        try:
            c = get_client(); await c.connect(); boost_sqlite_session(c); st["last_net_ok"] = time.monotonic()
            if await c.is_user_authorized(): await start_bg(c); show_dashboard(); return
        except Exception: pass
        show_phone()

    def show_license(msg: str = ""):
        page.controls.clear()
        inf = ft.Text(msg, size=13, color="#F59E0B", selectable=True)
        db = ft.TextField(label="شناسه سخت‌افزاری دستگاه", value=did, read_only=True, text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_CRIMSON)
        kb = ft.TextField(label="کلید لایسنس", value=str(load_json(LIC_FILE, {}).get("key", "")).strip(), hint_text="V3X-XXXX-XXXX", text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_ACTIVE)
        async def _cp(e):
            try:
                if hasattr(ft, "Clipboard"): await ft.Clipboard().set(did)
                inf.value, inf.color = "شناسه دستگاه کپی شد ✅", "#10B981"
            except Exception: inf.value, inf.color = "متن را انتخاب و کپی کنید.", "#F59E0B"
            safe_up()
        async def _vf(e):
            btn.disabled = True; inf.value, inf.color = "در حال بررسی لایسنس...", RED_LIGHT; safe_up()
            s, m, ck, u = await check_license(kb.value or "", did); btn.disabled = False
            if s == "OUTDATED": show_update(m, u); return
            if s != "OK": inf.value, inf.color = f"❌ {m}", RED_NEON; safe_up(); return
            save_json(LIC_FILE, {"key": ck}); await after_lic()
        btn, _ = make_btn("بررسی لایسنس و ورود", _vf, height=46)
        cb, _ = make_btn("📋 کپی شناسه دستگاه", _cp, color=RED_LIGHT, kind="outlined")
        page.add(ft.Container(bgcolor=BG_CARD, padding=16, border_radius=ft.BorderRadius.all(14), border=ft.Border.all(1.2, BORDER_ACTIVE), content=ft.Column(spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[ft.Text("V3X SELFBOT PRO", size=22, weight=ft.FontWeight.BOLD, color=RED_NEON), ft.Text(f"نسخه {APP_VERSION} | فعال‌سازی اشتراک پرو", size=12, color=TEXT_MUTED), db, cb, kb, btn, inf])), footer_box()); safe_up()

    def show_phone(msg: str = ""):
        page.controls.clear()
        inf = ft.Text(msg, size=13, color="#F59E0B", selectable=True)
        pb = ft.TextField(label="شماره موبایل سروش‌پلاس", hint_text="09123456789", keyboard_type=ft.KeyboardType.PHONE, text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_ACTIVE)
        async def _otp(e):
            d = "".join(c for c in (pb.value or "") if c.isdigit())
            p98, p09 = ("98" + d[1:], d) if d.startswith("09") and len(d) == 11 else ((d, "0" + d[2:]) if d.startswith("989") and len(d) == 12 else (("98" + d, "0" + d) if d.startswith("9") and len(d) == 10 else ("", "")))
            if not p98: inf.value, inf.color = "شماره موبایل معتبر وارد کنید.", RED_NEON; safe_up(); return
            btn.disabled = True; inf.value, inf.color = "در حال ارسال کد تایید...", RED_LIGHT; safe_up()
            try:
                c = get_client()
                if not c.is_connected(): await c.connect()
                res, used, err = None, p98, None
                for fmt in (p98, f"+{p98}", p09):
                    try: res = await c.send_code_request(fmt); used, err = fmt, None; break
                    except Exception as ex: err = ex
                if err: raise err
                st["phone"], st["hash"], st["need_2fa"] = used, getattr(res, "phone_code_hash", None), False
                btn.disabled = False; show_otp()
            except Exception as ex: btn.disabled = False; inf.value, inf.color = f"خطا: {ex}", RED_NEON; safe_up()
        btn, _ = make_btn("ارسال کد تایید", _otp, height=46)
        page.add(ft.Container(bgcolor=BG_CARD, padding=16, border_radius=ft.BorderRadius.all(14), border=ft.Border.all(1.2, BORDER_ACTIVE), content=ft.Column(spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[ft.Text("ورود به سروش‌پلاس", size=19, weight=ft.FontWeight.BOLD, color=RED_NEON), pb, btn, inf])), footer_box()); safe_up()

    def show_otp():
        page.controls.clear()
        inf = ft.Text(f"کد تایید به {st['phone']} ارسال شد.", size=13, color=RED_LIGHT)
        cb = ft.TextField(label="کد تایید", hint_text="12345", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_ACTIVE)
        pw = ft.TextField(label="رمز دومرحله‌ای", password=True, can_reveal_password=True, visible=st["need_2fa"], text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_ACTIVE)
        async def _cf(e):
            code, pwd = (cb.value or "").strip(), (pw.value or "").strip()
            if not st["need_2fa"] and len(code) < 4: inf.value, inf.color = "کد تایید را کامل وارد کنید.", RED_NEON; safe_up(); return
            btn.disabled = True; inf.value, inf.color = "در حال ورود...", RED_LIGHT; safe_up()
            try:
                c = get_client()
                if st["need_2fa"]: await c.sign_in(password=pwd)
                else:
                    try: await (c.sign_in(phone=st["phone"], code=code, phone_code_hash=st["hash"]) if st["hash"] else c.sign_in(st["phone"], code))
                    except TypeError: await c.sign_in(st["phone"], code)
                btn.disabled = False; boost_sqlite_session(c); await start_bg(c); show_dashboard()
            except Exception as ex:
                btn.disabled = False
                if "password" in str(ex).lower() or "2fa" in str(ex).lower(): st["need_2fa"], pw.visible = True, True; inf.value, inf.color = "رمز دومرحله‌ای را وارد کنید.", "#F59E0B"
                else: inf.value, inf.color = f"خطا: {ex}", RED_NEON
                safe_up()
        async def _bk(e): show_phone()
        btn, _ = make_btn("تایید و ورود", _cf, height=46); chg, _ = make_btn("تغییر شماره", _bk, color=TEXT_MUTED, kind="text")
        page.add(ft.Container(bgcolor=BG_CARD, padding=16, border_radius=ft.BorderRadius.all(14), border=ft.Border.all(1.2, BORDER_ACTIVE), content=ft.Column(spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[ft.Text("تایید کد", size=19, weight=ft.FontWeight.BOLD, color=RED_NEON), cb, pw, btn, chg, inf])), footer_box()); safe_up()

    def show_dashboard():
        page.controls.clear(); c = get_client(); log("سلف‌بات پرو با موفقیت متصل شد ✅", "#10B981")
        body_host, on_dlg_cb = ft.Column(spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH), None

        async def fetch_dialogs(lim: int = 80) -> list[dict]:
            st["dialogs_loading"] = True; items = []
            try:
                await ensure_online(c)
                for d in await get_dialogs_list(c, lim):
                    ent = getattr(d, "entity", None)
                    cid = getattr(d, "id", None) or (getattr(ent, "id", None) if ent else None) or getattr(d, "chat_id", None)
                    if cid is None: continue
                    title = getattr(d, "name", None) or getattr(d, "title", None) or (getattr(ent, "title", None) or getattr(ent, "first_name", None) if ent else None) or str(cid)
                    cs, iu, ig, ic = str(cid), getattr(d, "is_user", None), getattr(d, "is_group", None), getattr(d, "is_channel", None)
                    kind = "pv" if (iu is True or cs.startswith("u0") or (cs.lstrip("-").isdigit() and int(cs) > 0 and not ig and not ic)) else ("channel" if (cs.startswith("c0") or (ic and (getattr(ent, "broadcast", False) or not getattr(ent, "megagroup", False)) and not ig)) else "group")
                    items.append({"id": cs, "title": str(title), "kind": kind})
            except Exception as ex: log(f"خطا در دریافت چت‌ها: {ex}", RED_NEON)
            st["dialogs_loading"], st["dialogs"] = False, items
            if callable(on_dlg_cb): on_dlg_cb()
            return items

        async def fetch_msgs(raw: str, lim: int = 15) -> list[dict]:
            msgs, tgt = [], (raw or "").strip()
            if not tgt: return msgs
            try:
                await ensure_online(c)
                for m in await get_msgs_list(c, await resolve_peer(c, tgt), lim):
                    mid = getattr(m, "id", None) or getattr(m, "message_id", None)
                    if mid is None: continue
                    txt = (getattr(m, "raw_text", None) or getattr(m, "text", None) or getattr(m, "message", None) or getattr(m, "caption", None) or ("[رسانه / فایل]" if getattr(m, "media", None) else "")).strip()
                    if not txt: continue
                    snd = getattr(m, "sender", None)
                    sn = getattr(snd, "first_name", None) or getattr(snd, "title", None) or ("شما" if getattr(m, "out", False) else str(getattr(m, "sender_id", "کاربر")))
                    msgs.append({"id": mid, "sender": str(sn), "text": txt})
            except Exception as ex: log(f"خطا در دریافت پیام‌ها: {ex}", RED_NEON)
            return msgs

        def set_tgt(v: str):
            val = (v or "").strip()
            if st["reply_chat_id"] and st["reply_chat_id"] != val: st.update({"reply_to_id": None, "reply_to_preview": "", "reply_chat_id": ""})
            st["active_target"] = val

        def rep_banner(on_clr=None):
            if st["reply_to_id"] is None: return ft.Container(visible=False)
            async def _clr(e):
                st.update({"reply_to_id": None, "reply_to_preview": "", "reply_chat_id": ""})
                if on_clr: on_clr()
                safe_up()
            cb, _ = make_btn("✖️", _clr, color=RED_NEON, kind="text")
            return ft.Container(padding=ft.Padding.symmetric(horizontal=10, vertical=5), border_radius=ft.BorderRadius.all(8), bgcolor=BG_INPUT, border=ft.Border.all(1, RED_LIGHT), content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text(f"↩️ ریپلای #{st['reply_to_id']}: {st['reply_to_preview'][:35]}", size=12, color=RED_LIGHT, expand=True), cb]))

        # ==========================================
        # تب ۱: چت‌ها
        # ==========================================
        def build_chats():
            nonlocal on_dlg_cb
            tb = ft.TextField(label="آیدی یا شناسه چت", value=st["active_target"], text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_CRIMSON, on_change=lambda e: set_tgt(e.control.value or ""))
            cc, mc = ft.Column(spacing=6, height=160, scroll=ft.ScrollMode.AUTO), ft.Column(spacing=6, height=175, scroll=ft.ScrollMode.AUTO)
            cl = ft.Text(f"چت‌های انتخاب‌شده: {len(st['selected_targets'])}", size=12, color=RED_LIGHT)
            rh = ft.Column(controls=[rep_banner(lambda: draw_m())])

            async def _pick_m(e, i, t: str):
                st.update({"reply_to_id": i, "reply_to_preview": t, "reply_chat_id": st["active_target"]})
                rh.controls = [rep_banner(draw_m)]; draw_m(); log(f"پیام #{i} برای ریپلای انتخاب شد ↩️", RED_LIGHT)

            def draw_m():
                mc.controls.clear()
                if not st["recent_messages"]: mc.controls.append(ft.Text("پیامی بارگذاری نشده است. روی یک چت بزنید.", size=12, color=TEXT_MUTED)); return
                for m in st["recent_messages"]:
                    mid, sel = m["id"], st["reply_to_id"] == m["id"]
                    mc.controls.append(ft.Container(padding=ft.Padding.all(8), border_radius=ft.BorderRadius.all(8), ink=True, bgcolor="#1C0A10" if sel else BG_INPUT, border=ft.Border.all(1.5 if sel else 1, RED_NEON if sel else BORDER_CRIMSON), on_click=bind_async(_pick_m, mid, m["text"]), content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Column(spacing=2, expand=True, controls=[ft.Text(f"{m['sender']} (#{mid})", size=11, color=RED_LIGHT), ft.Text(m["text"], size=12, color=TEXT_WHITE, max_lines=2)]), ft.Text("✅" if sel else "ریپلای", size=11, color=RED_NEON if sel else TEXT_MUTED)])))

            async def _clk_c(e, cid: str, title: str):
                set_tgt(cid); tb.value = cid
                if cid in st["selected_targets"]: del st["selected_targets"][cid]
                else: st["selected_targets"][cid] = title
                cl.value = f"چت‌های انتخاب‌شده: {len(st['selected_targets'])}"; rh.controls = [rep_banner(draw_m)]; draw_c(); safe_up()
                st["recent_messages"] = await fetch_msgs(cid, 15); draw_m(); safe_up()

            def draw_c():
                cc.controls.clear(); flt = st["chat_filter"]
                lst = st["dialogs"] if flt == "all" else [x for x in st["dialogs"] if (x["kind"] == "pv" if flt == "pv" else x["kind"] in ("group", "channel"))]
                if not lst: cc.controls.append(ft.Text("⏳ در حال دریافت لیست چت‌ها..." if st["dialogs_loading"] else "چتی یافت نشد. بروزرسانی را بزنید.", size=12, color=TEXT_MUTED)); return
                for it in lst:
                    cid, title = it["id"], it["title"]; sel = cid in st["selected_targets"] or st["active_target"] == cid
                    bdg = "👤 پی‌وی" if it["kind"] == "pv" else ("📢 کانال" if it["kind"] == "channel" else "👥 گپ")
                    cc.controls.append(ft.Container(padding=ft.Padding.all(8), border_radius=ft.BorderRadius.all(9), ink=True, bgcolor="#1C0A10" if sel else BG_INPUT, border=ft.Border.all(1.5 if sel else 1, RED_NEON if sel else BORDER_CRIMSON), on_click=bind_async(_clk_c, cid, title), content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Column(spacing=1, expand=True, controls=[ft.Text(title, size=13, weight=ft.FontWeight.W_600, color=TEXT_WHITE), ft.Text(f"{bdg} | {cid}", size=11, color=TEXT_MUTED)]), ft.Text("✅" if sel else "انتخاب", size=12, color=RED_NEON if sel else "#64748B")])))

            async def _flt(e, m: str):
                st["chat_filter"] = m
                fa.bgcolor, fp.bgcolor, fg.bgcolor = (RED_PRIMARY if m == "all" else BG_INPUT), (RED_PRIMARY if m == "pv" else BG_INPUT), (RED_PRIMARY if m == "group" else BG_INPUT)
                draw_c(); safe_up()
            async def _rel(e): log("در حال دریافت چت‌ها...", RED_LIGHT); r = await fetch_dialogs(80); draw_c(); log(f"{len(r)} چت بارگذاری شد ✅", "#10B981")
            async def _lm(e):
                t = (tb.value or st["active_target"] or "").strip()
                if not t: log("ابتدا چت را انتخاب کنید.", RED_NEON); return
                set_tgt(t); st["recent_messages"] = await fetch_msgs(t, 15); draw_m(); log(f"{len(st['recent_messages'])} پیام دریافت شد ✅", "#10B981")
            async def _clr_all(e):
                st["selected_targets"].clear(); set_tgt(""); st["recent_messages"].clear(); tb.value = ""; cl.value = "چت‌های انتخاب‌شده: 0"; rh.controls = [rep_banner(draw_m)]; draw_c(); draw_m(); safe_up()

            on_dlg_cb = lambda: (draw_c(), safe_up())
            fa, _ = make_btn("همه", bind_async(_flt, "all"), bgcolor=RED_PRIMARY if st["chat_filter"] == "all" else BG_INPUT, height=34, expand=True)
            fp, _ = make_btn("👤 پی‌وی", bind_async(_flt, "pv"), bgcolor=RED_PRIMARY if st["chat_filter"] == "pv" else BG_INPUT, height=34, expand=True)
            fg, _ = make_btn("👥 گپ‌ها", bind_async(_flt, "group"), bgcolor=RED_PRIMARY if st["chat_filter"] == "group" else BG_INPUT, height=34, expand=True)
            rb, _ = make_btn("🔄 بروزرسانی چت‌ها", _rel, height=38, expand=True); lb, _ = make_btn("📜 پیام‌های اخیر", _lm, bgcolor=RED_DARK, height=38, expand=True); cb, _ = make_btn("پاک کردن", _clr_all, color=RED_NEON, kind="text")
            draw_c(); draw_m()
            return ft.Column(spacing=8, controls=[
                ft.Container(bgcolor=BG_CARD, padding=12, border_radius=ft.BorderRadius.all(12), border=ft.Border.all(1, BORDER_CRIMSON), content=ft.Column(spacing=8, controls=[ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text("💬 انتخاب پی‌وی یا گپ", size=15, weight=ft.FontWeight.BOLD), cb]), tb, ft.Row(spacing=6, controls=[rb, lb]), ft.Row(spacing=6, controls=[fa, fp, fg]), cl, cc])),
                ft.Container(bgcolor=BG_CARD, padding=12, border_radius=ft.BorderRadius.all(12), border=ft.Border.all(1, BORDER_CRIMSON), content=ft.Column(spacing=6, controls=[ft.Text("📜 پیام‌های اخیر (برای ریپلای لمس کنید)", size=13, color=RED_LIGHT), rh, mc])),
            ])

        # ==========================================
        # تب ۲: ارسال چندتایی
        # ==========================================
        def build_multi():
            tb = ft.TextField(label="مقصد ارسال", value=st["active_target"], text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_CRIMSON, on_change=lambda e: set_tgt(e.control.value or ""))
            mc, mr = make_toggle("ارسال همزمان به چت‌های تیک‌خورده", f"انتخاب‌شده: {len(st['selected_targets'])} چت", len(st["selected_targets"]) > 1, lambda v: safe_up())
            al_c, al_r = make_toggle("⚡ موتور ضدهنگ در پی‌وی شلوغ (Pipeline)", "کانال‌های موازی مستقل بدون انتظار برای پیام‌های معلق طرف مقابل", st["anti_lag"], lambda v: (st.update({"anti_lag": v}), safe_up()))
            rh_c, rh_r = make_toggle("↩️ پرش خودکار ریپلای (بدون تغییر در متن)", "ارسال دقیق متن شما به عنوان ریپلای روی پیام‌های اخیر", st["reply_hop"], lambda v: (st.update({"reply_hop": v}), safe_up()))
            ni, sl = ft.TextField(label="متن پیام جدید", bgcolor=BG_INPUT, border_color=BORDER_CRIMSON), ft.Text("", size=12, color="#F59E0B", weight=ft.FontWeight.W_600)

            def calc_sum():
                rv = max(1, int(ri.value or 1)) if (ri.value or "").isdigit() else 1
                rt = max(1, min(25, int(rti.value or 10))) if (rti.value or "").isdigit() else 10
                try: dl = max(0.0, float(di.value or 0))
                except ValueError: dl = 0.0
                tot = rv * (len(st["selected_targets"]) if (mr["val"] and st["selected_targets"]) else 1) * len(st["multi_messages"])
                sl.value = f"📊 مجموع: {tot} پیام | " + (f"هر {dl:g}ث، {rt} کانال" if dl > 0 else f"حداکثر سرعت ({rt} کانال موازی)")

            def _cfg(e):
                st.update({"multi_rounds": ri.value or "10", "multi_rate": rti.value or "10", "multi_delay": di.value or "0"}); calc_sum(); up_ctrl(sl)

            ri = ft.TextField(label="تعداد دور", value=st["multi_rounds"], keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_CRIMSON, expand=True, on_change=_cfg)
            rti = ft.TextField(label="کانال همزمان", value=st["multi_rate"], keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_ACTIVE, expand=True, on_change=_cfg)
            di = ft.TextField(label="تاخیر (0=فوری)", value=st["multi_delay"], keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_CRIMSON, expand=True, on_change=_cfg)
            stat, icol = ft.Text(st["multi_status"], size=12, color="#10B981" if st["multi_running"] else TEXT_MUTED), ft.Column(spacing=5)

            async def _del(e, i: int):
                if 0 <= i < len(st["multi_messages"]): st["multi_messages"].pop(i); draw_it(); calc_sum(); safe_up()
            def draw_it():
                icol.controls.clear()
                for idx, txt in enumerate(st["multi_messages"]):
                    db, _ = make_btn("حذف", bind_async(_del, idx), color=RED_NEON, kind="text")
                    icol.controls.append(ft.Container(padding=ft.Padding.symmetric(horizontal=8, vertical=4), border_radius=ft.BorderRadius.all(8), bgcolor=BG_INPUT, border=ft.Border.all(1, BORDER_CRIMSON), content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text(f"{idx+1}. {txt}", size=12, expand=True), db])))
            def set_ms(t: str, col: str = "#10B981"):
                st["multi_status"] = t; stat.value, stat.color = t, col; up_ctrl(stat)

            async def run_m():
                rounds = max(1, int(st["multi_rounds"] or 1)) if (st["multi_rounds"] or "").isdigit() else 1
                rate = max(1, min(25, int(st["multi_rate"] or 10))) if (st["multi_rate"] or "").isdigit() else 10
                try: dly = max(0.0, float(st["multi_delay"] or 0.0))
                except ValueError: dly = 0.0
                use_al, use_rh = bool(al_r["val"]), bool(rh_r["val"])
                rpool = [m["id"] for m in st["recent_messages"][:10] if m.get("id") is not None] if use_rh else None
                tgts = list(st["selected_targets"].keys()) if (mr["val"] and st["selected_targets"]) else ([(tb.value or "").strip()] if (tb.value or "").strip() else [])
                msgs = list(st["multi_messages"])
                if not tgts or not msgs:
                    st["multi_running"] = False; ml.value, mb.bgcolor = "🚀 شروع ارسال چندتایی", RED_PRIMARY; up_ctrl(mb); return

                n_t, n_m = len(tgts), len(msgs)
                total = rounds * n_t * n_m
                box = {"idx": 0, "done": 0, "fail": 0}
                flood_box = [0]
                t0 = time.monotonic()

                try:
                    boost_sqlite_session(c)
                    await ensure_online(c, False)
                    peers = {t: await resolve_peer(c, t) for t in tgts}
                    reps = {t: (st["reply_to_id"] if st["reply_chat_id"] == t else None) for t in tgts}

                    async def _ui_ticker():
                        while st["multi_running"]:
                            await asyncio.sleep(0.55)
                            if not st["multi_running"]: break
                            if flood_box[0] > 0:
                                set_ms(f"⏳ مکث سرور ({flood_box[0]}ث) | ارسال شده: {box['done']}/{total}", "#F59E0B")
                            else:
                                rps = box["done"] / max(0.1, time.monotonic() - t0)
                                set_ms(f"⚡ روان و فعال: {box['done']}/{total} | سرعت: {rps:.1f}/ث", "#10B981")

                    async def _worker(wid: int):
                        if use_al and dly == 0: await asyncio.sleep(wid * 0.03)
                        while st["multi_running"]:
                            i = box["idx"]
                            if i >= total: break
                            box["idx"] = i + 1
                            rem = i % (n_t * n_m)
                            rt = tgts[rem // n_m]
                            tx = msgs[rem % n_m]
                            ok = await send_pipeline_msg(c, peers[rt], rt, tx, reps[rt], rpool if n_t == 1 else None, flood_box)
                            if ok: box["done"] += 1
                            else: box["fail"] += 1
                            if dly > 0 and box["idx"] < total and st["multi_running"]:
                                await asyncio.sleep(dly)
                            else:
                                await asyncio.sleep(0.005)

                    tk = asyncio.create_task(_ui_ticker())
                    workers_cnt = min(rate, total) if use_al else min(4, total)
                    await asyncio.gather(*(_worker(w) for w in range(workers_cnt)))
                    was_running = st["multi_running"]
                    st["multi_running"] = False
                    tk.cancel()
                    set_ms(f"✅ پایان ارسال: {box['done']}/{total}" if was_running else f"⛔ متوقف شد: {box['done']}/{total}", "#10B981" if was_running else "#F59E0B")
                except Exception as ex:
                    set_ms(f"❌ خطا: {ex}", RED_NEON)
                finally:
                    st["multi_running"] = False; ml.value, mb.bgcolor = "🚀 شروع ارسال چندتایی", RED_PRIMARY; up_ctrl(mb)

            async def _tog(e):
                if st["multi_running"]: st["multi_running"] = False; set_ms("⏳ در حال توقف فوری...", "#F59E0B"); return
                st.update({"multi_rounds": ri.value or "10", "multi_rate": rti.value or "10", "multi_delay": di.value or "0", "multi_running": True})
                ml.value, mb.bgcolor = "⛔ توقف ارسال", RED_DARK; up_ctrl(mb); asyncio.create_task(run_m())
            async def _add(e):
                v = (ni.value or "").strip()
                if v: st["multi_messages"].append(v); ni.value = ""; draw_it(); calc_sum(); safe_up()
            async def _sav(e): save_json(SAVED_MSGS_FILE, st["multi_messages"]); log("ذخیره شد ✅", "#10B981")

            ab, _ = make_btn("➕ افزودن", _add, height=38, expand=True); sb, _ = make_btn("💾 ذخیره", _sav, bgcolor=RED_DARK, height=38, expand=True)
            mb, ml = make_btn("⛔ توقف ارسال" if st["multi_running"] else "🚀 شروع ارسال چندتایی", _tog, bgcolor=RED_DARK if st["multi_running"] else RED_PRIMARY, height=44)
            draw_it(); calc_sum()
            return ft.Container(bgcolor=BG_CARD, padding=12, border_radius=ft.BorderRadius.all(12), border=ft.Border.all(1, BORDER_CRIMSON), content=ft.Column(spacing=8, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[ft.Text("📨 ارسال چندتایی پرسرعت", size=15, weight=ft.FontWeight.BOLD), rep_banner(), tb, mc, ni, ft.Row(spacing=6, controls=[ab, sb]), icol, ft.Row(spacing=5, controls=[ri, rti, di]), sl, al_c, rh_c, mb, stat]))

        # ==========================================
        # تب ۳: ارسال توربو
        # ==========================================
        def build_turbo():
            tb = ft.TextField(label="آیدی یا شناسه مقصد", value=st["active_target"], text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_CRIMSON, on_change=lambda e: set_tgt(e.control.value or ""))
            mi = ft.TextField(label="متن پیام توربو", bgcolor=BG_INPUT, border_color=BORDER_CRIMSON)
            al_c, al_r = make_toggle("⚡ موتور ضدهنگ در پی‌وی شلوغ (Pipeline)", "کانال‌های موازی مستقل بدون انتظار برای پیام‌های معلق طرف مقابل", st["anti_lag"], lambda v: (st.update({"anti_lag": v}), safe_up()))
            rh_c, rh_r = make_toggle("↩️ پرش خودکار ریپلای (بدون تغییر در متن)", "ارسال دقیق متن شما به عنوان ریپلای روی پیام‌های اخیر", st["reply_hop"], lambda v: (st.update({"reply_hop": v}), safe_up()))
            def _cfg(e): st.update({"turbo_count": ci.value or "100", "turbo_rate": tri.value or "10", "turbo_delay": di.value or "0"})
            ci = ft.TextField(label="تعداد کل", value=st["turbo_count"], keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_CRIMSON, expand=True, on_change=_cfg)
            tri = ft.TextField(label="کانال همزمان", value=st["turbo_rate"], keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_ACTIVE, expand=True, on_change=_cfg)
            di = ft.TextField(label="تاخیر (0=فوری)", value=st["turbo_delay"], keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_CRIMSON, expand=True, on_change=_cfg)
            stat = ft.Text(st["turbo_status"], size=12, color="#10B981" if st["turbo_running"] else TEXT_MUTED)
            def set_ts(t: str, col: str = "#10B981"): st["turbo_status"] = t; stat.value, stat.color = t, col; up_ctrl(stat)

            async def run_t():
                total = max(1, int(st["turbo_count"] or 100)) if (st["turbo_count"] or "").isdigit() else 100
                rate = max(1, min(25, int(st["turbo_rate"] or 10))) if (st["turbo_rate"] or "").isdigit() else 10
                try: dly = max(0.0, float(st["turbo_delay"] or 0.0))
                except ValueError: dly = 0.0
                use_al, use_rh = bool(al_r["val"]), bool(rh_r["val"])
                rpool = [m["id"] for m in st["recent_messages"][:10] if m.get("id") is not None] if use_rh else None
                raw_t, txt = (tb.value or "").strip(), (mi.value or "").strip()
                rep = st["reply_to_id"] if st["reply_chat_id"] == raw_t else None
                box = {"idx": 0, "done": 0, "fail": 0}
                flood_box = [0]
                t0 = time.monotonic()

                try:
                    boost_sqlite_session(c)
                    await ensure_online(c, False)
                    peer = await resolve_peer(c, raw_t)

                    async def _ui_ticker():
                        while st["turbo_running"]:
                            await asyncio.sleep(0.55)
                            if not st["turbo_running"]: break
                            if flood_box[0] > 0:
                                set_ts(f"⏳ مکث سرور ({flood_box[0]}ث) | ارسال شده: {box['done']}/{total}", "#F59E0B")
                            else:
                                rps = box["done"] / max(0.1, time.monotonic() - t0)
                                set_ts(f"⚡ روان و فعال: {box['done']}/{total} | سرعت: {rps:.1f}/ث", "#10B981")

                    async def _worker(wid: int):
                        if use_al and dly == 0: await asyncio.sleep(wid * 0.03)
                        while st["turbo_running"]:
                            i = box["idx"]
                            if i >= total: break
                            box["idx"] = i + 1
                            ok = await send_pipeline_msg(c, peer, raw_t, txt, rep, rpool, flood_box)
                            if ok: box["done"] += 1
                            else: box["fail"] += 1
                            if dly > 0 and box["idx"] < total and st["turbo_running"]:
                                await asyncio.sleep(dly)
                            else:
                                await asyncio.sleep(0.005)

                    tk = asyncio.create_task(_ui_ticker())
                    workers_cnt = min(rate, total) if use_al else min(4, total)
                    await asyncio.gather(*(_worker(w) for w in range(workers_cnt)))
                    was_running = st["turbo_running"]
                    st["turbo_running"] = False
                    tk.cancel()
                    set_ts(f"✅ پایان ارسال: {box['done']}/{total}" if was_running else f"⛔ متوقف شد: {box['done']}/{total}", "#10B981" if was_running else "#F59E0B")
                except Exception as ex:
                    set_ts(f"❌ خطا: {ex}", RED_NEON)
                finally:
                    st["turbo_running"] = False; tl.value, tbtn.bgcolor = "🚀 شروع توربو", RED_PRIMARY; up_ctrl(tbtn)

            async def _tog(e):
                if st["turbo_running"]: st["turbo_running"] = False; set_ts("⏳ در حال توقف فوری...", "#F59E0B"); return
                if not (tb.value or "").strip() or not (mi.value or "").strip(): return
                st.update({"turbo_count": ci.value or "100", "turbo_rate": tri.value or "10", "turbo_delay": di.value or "0", "turbo_running": True})
                tl.value, tbtn.bgcolor = "⛔ توقف توربو", RED_DARK; up_ctrl(tbtn); asyncio.create_task(run_t())

            tbtn, tl = make_btn("⛔ توقف توربو" if st["turbo_running"] else "🚀 شروع توربو", _tog, bgcolor=RED_DARK if st["turbo_running"] else RED_PRIMARY, height=44)
            return ft.Container(bgcolor=BG_CARD, padding=12, border_radius=ft.BorderRadius.all(12), border=ft.Border.all(1, BORDER_CRIMSON), content=ft.Column(spacing=8, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[ft.Text("🚀 ارسال توربو فوق‌سریع", size=15, weight=ft.FontWeight.BOLD), rep_banner(), tb, mi, ft.Row(spacing=5, controls=[ci, tri, di]), al_c, rh_c, tbtn, stat]))

        # ==========================================
        # تب ۴: ریم کامل ممبرهای گپ (با بررسی دسترسی)
        # ==========================================
        def build_kick_all():
            nonlocal on_dlg_cb
            gid_in = ft.TextField(label="شناسه یا آیدی گپ انتخاب‌شده", value=st["kick_target_id"], text_align=ft.TextAlign.LEFT, bgcolor=BG_INPUT, border_color=BORDER_CRIMSON, on_change=lambda e: st.update({"kick_target_id": (e.control.value or "").strip(), "kick_has_perm": None}))
            g_col = ft.Column(spacing=6, height=185, scroll=ft.ScrollMode.AUTO)
            sel_info = ft.Text(
                f"🎯 گپ انتخاب‌شده: {st['kick_target_title']} ({st['kick_target_id']})" if st["kick_target_id"] else "⚠️ هنوز گپی انتخاب نشده است",
                size=12, color="#10B981" if st["kick_target_id"] else "#F59E0B", weight=ft.FontWeight.W_600
            )
            k_stat = ft.Text(st["kick_status"], size=12, color=RED_NEON if st["kick_has_perm"] is False else ("#10B981" if st["kick_has_perm"] is True else TEXT_MUTED))

            def set_ks(t: str, col: str = TEXT_MUTED):
                st["kick_status"] = t; k_stat.value, k_stat.color = t, col; up_ctrl(k_stat)

            async def inspect_group(cid: str, title: str):
                st.update({"kick_target_id": cid, "kick_target_title": title, "kick_has_perm": None, "kick_members_count": 0})
                gid_in.value = cid
                sel_info.value, sel_info.color = f"🎯 گپ انتخاب‌شده: {title} ({cid})", "#10B981"
                draw_groups()
                set_ks(f"⏳ در حال بررسی دسترسی ادمین و لیست ممبرهای «{title}»...", "#F59E0B")
                safe_up()
                try:
                    await ensure_online(c, False)
                    peer = await resolve_peer(c, cid)
                    my_id = await get_my_id(c)
                    perm = await check_group_admin_perm(c, peer)
                    if perm is False:
                        st["kick_has_perm"] = False
                        set_ks(f"❌ دسترسی ندارید! شما در گپ «{title}» ادمین نیستید.", RED_NEON)
                        return
                    members = await get_group_members(c, peer, my_id)
                    st["kick_has_perm"] = True
                    st["kick_members_count"] = len(members)
                    set_ks(f"✅ دسترسی تایید شد | ممبرهای قابل ریم در «{title}»: {len(members)} نفر", "#10B981")
                except Exception as ex:
                    if is_perm_denied(str(ex)):
                        st["kick_has_perm"] = False
                        set_ks(f"❌ دسترسی ادمین برای ریم ممبر در «{title}» ندارید!", RED_NEON)
                    else:
                        set_ks(f"⚠️ آماده اجرا (خطای بررسی: {ex})", "#F59E0B")

            def draw_groups():
                g_col.controls.clear()
                groups = [x for x in st["dialogs"] if x["kind"] == "group"]
                if not groups:
                    msg = "⏳ در حال دریافت لیست گپ‌ها..." if st["dialogs_loading"] else "گپی یافت نشد. دکمه بروزرسانی لیست گپ‌ها را بزنید."
                    g_col.controls.append(ft.Text(msg, size=12, color=TEXT_MUTED))
                    return
                for it in groups:
                    cid, title = it["id"], it["title"]
                    sel = st["kick_target_id"] == cid
                    g_col.controls.append(ft.Container(
                        padding=ft.Padding.all(8), border_radius=ft.BorderRadius.all(9), ink=True,
                        bgcolor="#1C0A10" if sel else BG_INPUT,
                        border=ft.Border.all(1.5 if sel else 1, RED_NEON if sel else BORDER_CRIMSON),
                        on_click=bind_async(lambda e, i=cid, t=title: inspect_group(i, t)),
                        content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                            ft.Column(spacing=1, expand=True, controls=[
                                ft.Text(f"👥 {title}", size=13, weight=ft.FontWeight.W_600, color=TEXT_WHITE),
                                ft.Text(f"شناسه: {cid}", size=11, color=TEXT_MUTED),
                            ]),
                            ft.Text("✅ انتخاب‌شده" if sel else "انتخاب گپ", size=12, color=RED_NEON if sel else "#64748B"),
                        ]),
                    ))

            async def _rel_groups(e):
                set_ks("⏳ در حال دریافت لیست گپ‌ها...", "#F59E0B")
                await fetch_dialogs(80)
                draw_groups()
                g_cnt = sum(1 for x in st["dialogs"] if x["kind"] == "group")
                set_ks(f"✅ {g_cnt} گپ بارگذاری شد. روی گپ مورد نظر بزنید.", "#10B981")

            async def run_kick_all():
                cid = (gid_in.value or st["kick_target_id"] or "").strip()
                title = st["kick_target_title"] or cid
                if not cid:
                    st["kick_running"] = False; kl.value, kbtn.bgcolor = "🗑️ ریم کامل کل ممبرهای گپ", RED_PRIMARY; up_ctrl(kbtn)
                    set_ks("❌ ابتدا یک گپ را انتخاب کنید!", RED_NEON); return

                box = {"idx": 0, "kicked": 0, "fail": 0, "no_perm": False}
                method_box = {"name": None}
                try:
                    await ensure_online(c, False)
                    peer = await resolve_peer(c, cid)
                    my_id = await get_my_id(c)
                    perm = await check_group_admin_perm(c, peer)
                    if perm is False:
                        st["kick_has_perm"] = False
                        set_ks(f"❌ دسترسی ندارید! در «{title}» ادمین نیستید.", RED_NEON)
                        return

                    set_ks(f"⏳ در حال دریافت لیست کامل ممبرهای «{title}»...", "#F59E0B")
                    members = await get_group_members(c, peer, my_id)
                    total = len(members)
                    if total == 0:
                        set_ks("⚠️ ممبری برای ریم یافت نشد یا دسترسی ادمین ندارید.", "#F59E0B")
                        return

                    async def _ui_ticker():
                        while st["kick_running"]:
                            await asyncio.sleep(0.5)
                            if not st["kick_running"]: break
                            set_ks(f"🔥 در حال ریم کامل ممبرها: {box['kicked']}/{total} نفر...", "#F59E0B")

                    async def _kick_worker():
                        while st["kick_running"] and not box["no_perm"]:
                            i = box["idx"]
                            if i >= total: break
                            box["idx"] = i + 1
                            res = await kick_one_member(c, peer, members[i], method_box)
                            if res == "OK":
                                box["kicked"] += 1
                            elif res == "NO_PERM":
                                box["no_perm"] = True
                                st["kick_running"] = False
                                break
                            else:
                                box["fail"] += 1
                            await asyncio.sleep(0.05)

                    tk = asyncio.create_task(_ui_ticker())
                    await asyncio.gather(*(_kick_worker() for _ in range(min(4, total))))
                    was_running = st["kick_running"]
                    st["kick_running"] = False
                    tk.cancel()

                    if box["no_perm"]:
                        st["kick_has_perm"] = False
                        set_ks(f"❌ دسترسی ندارید! ریم متوقف شد ({box['kicked']} انجام شد).", RED_NEON)
                    elif was_running:
                        set_ks(f"✅ ریم کامل انجام شد! {box['kicked']} از {total} ممبر حذف شدند.", "#10B981")
                        log(f"🗑️ ریم کامل گپ «{title}» انجام شد ({box['kicked']} ممبر) ✅", "#10B981")
                    else:
                        set_ks(f"⛔ ریم متوقف شد ({box['kicked']} از {total} ممبر حذف شدند).", "#F59E0B")
                except Exception as ex:
                    if is_perm_denied(str(ex)):
                        st["kick_has_perm"] = False
                        set_ks(f"❌ دسترسی ادمین در «{title}» ندارید!", RED_NEON)
                    else:
                        set_ks(f"❌ خطا در ریم ممبرها: {ex}", RED_NEON)
                finally:
                    st["kick_running"] = False; kl.value, kbtn.bgcolor = "🗑️ ریم کامل کل ممبرهای گپ", RED_PRIMARY; up_ctrl(kbtn)

            async def _tog_kick(e):
                if st["kick_running"]:
                    st["kick_running"] = False
                    set_ks("⏳ در حال توقف فوری ریم...", "#F59E0B")
                    return
                cid = (gid_in.value or st["kick_target_id"] or "").strip()
                if not cid:
                    set_ks("❌ ابتدا یک گپ را از لیست زیر انتخاب کنید!", RED_NEON)
                    return
                if st["kick_has_perm"] is False:
                    set_ks("❌ در این گپ دسترسی ادمین برای ریم ممبر ندارید!", RED_NEON)
                    return
                st["kick_running"] = True
                kl.value, kbtn.bgcolor = "⛔ توقف ریم ممبرها", RED_DARK
                up_ctrl(kbtn)
                asyncio.create_task(run_kick_all())

            on_dlg_cb = lambda: (draw_groups(), safe_up())
            rg_btn, _ = make_btn("🔄 بروزرسانی لیست گپ‌ها", _rel_groups, height=38, expand=True)
            chk_btn, _ = make_btn("🔍 بررسی دسترسی گپ", lambda e: inspect_group((gid_in.value or st["kick_target_id"] or "").strip(), st["kick_target_title"] or (gid_in.value or "").strip()), bgcolor=RED_DARK, height=38, expand=True)
            kbtn, kl = make_btn("⛔ توقف ریم ممبرها" if st["kick_running"] else "🗑️ ریم کامل کل ممبرهای گپ", _tog_kick, bgcolor=RED_DARK if st["kick_running"] else RED_PRIMARY, height=46)
            draw_groups()
            return ft.Container(
                bgcolor=BG_CARD, padding=12, border_radius=ft.BorderRadius.all(12), border=ft.Border.all(1.2, BORDER_ACTIVE),
                content=ft.Column(spacing=8, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[
                    ft.Text("🗑️ ریم کامل ممبرهای گپ (نیازمند ادمین)", size=15, weight=ft.FontWeight.BOLD, color=RED_NEON),
                    gid_in,
                    ft.Row(spacing=6, controls=[rg_btn, chk_btn]),
                    sel_info,
                    g_col,
                    kbtn,
                    k_stat,
                ]),
            )

        # ==========================================
        # تب ۵: ساعت افق تهران کنار اسم
        # ==========================================
        def build_clock():
            lsl = ft.Text(f"🕒 آخرین همگام‌سازی: {st['last_clock_sync_str']}", size=12, color="#10B981")
            cc, cr = make_toggle("⏰ ساعت افق تهران کنار اسم", "لمس کنید تا روشن یا خاموش شود", bool(clock_cfg.get("enabled", False)), lambda v: (clock_cfg.update({"enabled": v}), save_json(CLOCK_CFG_FILE, clock_cfg), safe_up()))
            bc, br = make_toggle("🔒 سرویس ضدخواب اندروید", "فعال نگه داشتن ساعت در پس‌زمینه و قفل صفحه", bool(clock_cfg.get("bg_keep_alive", True)), lambda v: (clock_cfg.update({"bg_keep_alive": v}), save_json(CLOCK_CFG_FILE, clock_cfg), notify_android("start" if v else "stop"), safe_up()))
            bfi = ft.TextField(label="نام اصلی (بدون ساعت)", value=clock_cfg.get("base_first", ""), bgcolor=BG_INPUT, border_color=BORDER_CRIMSON)
            bli = ft.TextField(label="نام خانوادگی (اختیاری)", value=clock_cfg.get("base_last", ""), bgcolor=BG_INPUT, border_color=BORDER_CRIMSON)
            spi = ft.TextField(label="جداکننده", value=clock_cfg.get("sep", "|"), bgcolor=BG_INPUT, border_color=BORDER_CRIMSON)
            sty = {"v": clock_cfg.get("style", "bold"), "p": clock_cfg.get("target_field", "first")}

            async def _fetch_nm(e):
                try:
                    async with clk_lock: await ensure_online(c); me = await asyncio.wait_for(c.get_me(), timeout=7.0)
                    bf, bl = strip_clock(getattr(me, "first_name", "") or ""), strip_clock(getattr(me, "last_name", "") or "")
                    bfi.value, bli.value = bf, bl; clock_cfg.update({"base_first": bf, "base_last": bl}); save_json(CLOCK_CFG_FILE, clock_cfg); log(f"نام دریافت شد: {bf} {bl}".strip(), "#10B981"); safe_up()
                except Exception as ex: log(f"خطا: {ex}", RED_NEON)

            async def _ap(e):
                bf, bl = strip_clock(bfi.value or ""), strip_clock(bli.value or "")
                if not bf and not bl:
                    try:
                        async with clk_lock: me = await asyncio.wait_for(c.get_me(), timeout=7.0)
                        bf, bl = strip_clock(getattr(me, "first_name", "") or ""), strip_clock(getattr(me, "last_name", "") or ""); bfi.value, bli.value = bf, bl
                    except Exception: pass
                clock_cfg.update({"enabled": cr["val"], "bg_keep_alive": br["val"], "base_first": bf, "base_last": bl, "style": sty["v"], "target_field": sty["p"], "sep": (spi.value or "|").strip()})
                save_json(CLOCK_CFG_FILE, clock_cfg); notify_android("start" if br["val"] else "stop"); st["last_clock_min"] = ""
                if cr["val"]: await sync_clock(c, True); lsl.value = f"🕒 آخرین همگام‌سازی: {st['last_clock_sync_str']}"
                else:
                    async with clk_lock: await apply_profile_name(c, bf or "User", bl)
                    log("ساعت غیرفعال شد ✅", RED_LIGHT)
                safe_up()

            async def _sty(e, v: str):
                sty["v"] = v; sn.bgcolor, sb.bgcolor, sm.bgcolor = (RED_PRIMARY if v == "normal" else BG_INPUT), (RED_PRIMARY if v == "bold" else BG_INPUT), (RED_PRIMARY if v == "mono" else BG_INPUT); safe_up()
            async def _pos(e, p: str):
                sty["p"] = p; pf.bgcolor, pl.bgcolor = (RED_PRIMARY if p == "first" else BG_INPUT), (RED_PRIMARY if p == "last" else BG_INPUT); safe_up()
            async def _bat(e): notify_android("battery")

            sn, _ = make_btn("14:30", bind_async(_sty, "normal"), bgcolor=RED_PRIMARY if sty["v"] == "normal" else BG_INPUT, height=34, expand=True)
            sb, _ = make_btn("𝟏𝟒:𝟑𝟎", bind_async(_sty, "bold"), bgcolor=RED_PRIMARY if sty["v"] == "bold" else BG_INPUT, height=34, expand=True)
            sm, _ = make_btn("𝟷𝟺:𝟹𝟶", bind_async(_sty, "mono"), bgcolor=RED_PRIMARY if sty["v"] == "mono" else BG_INPUT, height=34, expand=True)
            pf, _ = make_btn("کنار اسم", bind_async(_pos, "first"), bgcolor=RED_PRIMARY if sty["p"] == "first" else BG_INPUT, height=34, expand=True)
            pl, _ = make_btn("کنار فامیل", bind_async(_pos, "last"), bgcolor=RED_PRIMARY if sty["p"] == "last" else BG_INPUT, height=34, expand=True)
            gn, _ = make_btn("📥 خواندن اسم فعلی من", _fetch_nm, bgcolor=RED_DARK, height=36); ap, _ = make_btn("💾 ذخیره و اعمال ساعت", _ap, height=44); bt, _ = make_btn("🔋 حذف محدودیت باتری گوشی", _bat, bgcolor=BG_INPUT, color="#F59E0B", height=36)
            return ft.Container(bgcolor=BG_CARD, padding=12, border_radius=ft.BorderRadius.all(12), border=ft.Border.all(1, BORDER_CRIMSON), content=ft.Column(spacing=8, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[ft.Text("⏰ ساعت افق تهران کنار اسم", size=15, weight=ft.FontWeight.BOLD), lsl, cc, bc, bt, gn, bfi, bli, spi, ft.Row(spacing=5, controls=[sn, sb, sm]), ft.Row(spacing=5, controls=[pf, pl]), ap]))

        def render_tab():
            body_host.controls.clear()
            body_host.controls.append({"chats": build_chats, "multi": build_multi, "turbo": build_turbo, "kick": build_kick_all, "clock": build_clock}[st["active_tab"]]())

        async def _sw(e, nm: str):
            if st["active_tab"] != nm:
                st["active_tab"] = nm
                for k, b in nav.items(): b.bgcolor = RED_PRIMARY if k == nm else BG_INPUT
                render_tab(); safe_up()

        async def _out(e):
            st.update({"turbo_running": False, "multi_running": False, "kick_running": False}); notify_android("stop")
            try: await c.log_out()
            except Exception: pass
            st["client"] = None
            for f in os.listdir(STORAGE_DIR):
                if f.startswith(os.path.basename(SESSION_PATH)):
                    try: os.remove(os.path.join(STORAGE_DIR, f))
                    except Exception: pass
            show_phone("از حساب خارج شدید.")

        ob, _ = make_btn("خروج", _out, color=RED_NEON, kind="text")
        b1, _ = make_btn("💬 چت‌ها", bind_async(_sw, "chats"), bgcolor=RED_PRIMARY, height=38, expand=True)
        b2, _ = make_btn("📨 چندتایی", bind_async(_sw, "multi"), bgcolor=BG_INPUT, height=38, expand=True)
        b3, _ = make_btn("🚀 توربو", bind_async(_sw, "turbo"), bgcolor=BG_INPUT, height=38, expand=True)
        b4, _ = make_btn("⏰ ساعت", bind_async(_sw, "clock"), bgcolor=BG_INPUT, height=38, expand=True)
        b5, _ = make_btn("🗑️ ریم کامل ممبرهای گپ", bind_async(_sw, "kick"), bgcolor=BG_INPUT, height=38, expand=True)
        nav = {"chats": b1, "multi": b2, "turbo": b3, "clock": b4, "kick": b5}; render_tab()

        page.add(
            ft.Container(bgcolor=BG_CARD, padding=10, border_radius=ft.BorderRadius.all(12), border=ft.Border.all(1.2, BORDER_ACTIVE), content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Row(spacing=8, controls=[ft.Text("⚡ V3X Pro", size=17, weight=ft.FontWeight.BOLD, color=RED_NEON), conn_badge]), ob])),
            ft.Row(spacing=5, controls=[b1, b2]),
            ft.Row(spacing=5, controls=[b3, b4]),
            ft.Row(spacing=5, controls=[b5]),
            body_host,
            ft.Container(bgcolor=BG_CARD, padding=10, border_radius=ft.BorderRadius.all(12), border=ft.Border.all(1, BORDER_CRIMSON), content=ft.Column(spacing=4, controls=[ft.Text("📜 گزارش عملکرد", size=12, color=RED_LIGHT), logs])),
            footer_box(),
        )
        safe_up(); notify_android("start" if clock_cfg.get("bg_keep_alive", True) else "stop"); asyncio.create_task(fetch_dialogs())

    saved = str(load_json(LIC_FILE, {}).get("key", "")).strip()
    if saved:
        s, m, _, u = await check_license(saved, did)
        if s == "OUTDATED": show_update(m, u); return
        if s == "OK": await after_lic(); return
        try: os.remove(LIC_FILE)
        except Exception: pass
        show_license(m); return
    show_license()

if hasattr(ft, "run"): ft.run(main)
else: ft.app(target=main)
# END_OF_V3X_MAIN
