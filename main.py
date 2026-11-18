import asyncio, hashlib, importlib, inspect, json, os, pkgutil, platform, subprocess, tempfile, time
import flet as ft
import httpx

# لایه سازگاری کامل با Flet 1.1.2 برای جلوگیری از هرگونه خطای border / padding / radius
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

LICENSE_URL = "https://selfbot-license.krymyhady314.workers.dev"
OWNER_TEST_KEY = "V3X-OWNER-2026"
CREATOR_ID = "@V3XSYS"

STORAGE_DIR = os.getenv("FLET_APP_STORAGE_DATA") or tempfile.gettempdir()
os.makedirs(STORAGE_DIR, exist_ok=True)

DEV_FILE = os.path.join(STORAGE_DIR, "v3x_dev.txt")
LIC_FILE = os.path.join(STORAGE_DIR, "v3x_lic.json")
SESSION_PATH = os.path.join(STORAGE_DIR, "v3x_splus")


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


async def check_license(key: str, did: str) -> tuple[bool, str]:
    clean_key = key.strip()
    if clean_key.upper() == OWNER_TEST_KEY:
        return True, "ورود با کلید مدیریت تایید شد"

    params = {
        "key": clean_key,
        "license": clean_key,
        "license_key": clean_key,
        "code": clean_key,
        "hwid": did,
        "device_id": did,
        "device": did,
    }
    base = LICENSE_URL.rstrip("/")
    routes = [
        ("POST", f"{base}/check"),
        ("GET", f"{base}/check"),
        ("POST", f"{base}/verify"),
        ("GET", f"{base}/verify"),
        ("POST", f"{base}/validate"),
        ("GET", f"{base}/validate"),
        ("POST", f"{base}/activate"),
        ("GET", f"{base}/activate"),
        ("GET", base),
        ("POST", base),
    ]

    last_err = "پاسخ معتبری از سرور لایسنس دریافت نشد"
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http:
        for method, url in routes:
            try:
                r = await http.post(url, params=params, json=params) if method == "POST" else await http.get(url, params=params)
                if r.status_code in (404, 405):
                    continue
                try:
                    d = r.json()
                except Exception:
                    txt = r.text.strip()
                    low = txt.lower()
                    if any(w in low for w in ("valid", "active", "success", "authorized")):
                        return True, "لایسنس تایید شد"
                    if txt and "online" not in low:
                        last_err = txt[:100]
                    continue

                if not isinstance(d, dict):
                    continue

                status_val = str(d.get("status", "")).lower().strip()
                is_ok = (
                    d.get("valid") is True
                    or d.get("ok") is True
                    or d.get("success") is True
                    or d.get("authorized") is True
                    or status_val in ("valid", "ok", "active", "success", "activated", "true")
                )
                if is_ok:
                    return True, str(d.get("message") or d.get("msg") or "لایسنس تایید شد")

                if status_val == "online" and len(d) <= 2 and not any(k in d for k in ("valid", "ok", "error", "reason", "message")):
                    continue

                msg = d.get("message") or d.get("error") or d.get("reason") or d.get("detail") or d.get("msg")
                if msg:
                    return False, str(msg)
            except Exception as e:
                last_err = f"خطای شبکه: {e}"

    return False, last_err


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
        return cls(SESSION_PATH)
    except TypeError:
        return cls()


def get_events_module():
    try:
        import splusthon
        if hasattr(splusthon, "events"):
            return splusthon.events
        return importlib.import_module("splusthon.events")
    except Exception:
        return None


def make_btn(label: str, on_click, bgcolor: str = "#2563EB", color: str = "#FFFFFF", height: int = 44, kind: str = "filled", expand: bool = False):
    lbl = ft.Text(label, color=color, weight=ft.FontWeight.W_600, size=13)
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
                ft.Text("طراحی و توسعه: ", size=12, color="#94A3B8"),
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
    st = {
        "client": None,
        "phone": "",
        "hash": None,
        "need_2fa": False,
        "listener_added": False,
        "active_tab": "chats",  # chats | multi | turbo | autoreply
        "chat_filter": "all",   # all | pv | group
        "dialogs": [],
        "selected_targets": {},  # {id_str: title}
        "active_target": "",
        "multi_messages": ["سلام!", "چطوری؟", "پیام تست سلف‌بات V3X"],
        "multi_running": False,
        "turbo_running": False,
        "ar_enabled": False,
        "ar_text": "سلام! در حال حاضر آفلاین هستم، پیام شما ثبت شد.",
        "ar_pv_only": True,
        "replied": {},
    }
    logs = ft.Column(spacing=4, height=120, scroll=ft.ScrollMode.AUTO)

    def log(txt: str, col: str = "#94A3B8"):
        logs.controls.insert(0, ft.Text(f"[{time.strftime('%H:%M:%S')}] {txt}", size=12, color=col))
        logs.controls = logs.controls[:25]
        try:
            page.update()
        except Exception:
            pass

    def get_client():
        if st["client"] is None:
            st["client"] = create_splus_client()
        return st["client"]

    # ==========================================
    # صفحه ۱: لایسنس
    # ==========================================
    def show_license(msg: str = ""):
        page.controls.clear()
        info = ft.Text(msg, size=13, color="#F59E0B", selectable=True)
        dev_box = ft.TextField(label="شناسه سخت‌افزاری (Device ID)", value=did, read_only=True, text_align=ft.TextAlign.LEFT, bgcolor="#0F172A")
        key_box = ft.TextField(label="کلید لایسنس", value=get_saved_license(), hint_text="V3X-XXXX", text_align=ft.TextAlign.LEFT, bgcolor="#1E293B")

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
            page.update()

        async def verify(e):
            k = (key_box.value or "").strip()
            if not k:
                info.value, info.color = "کلید لایسنس را وارد کنید.", "#EF4444"
                page.update()
                return
            btn.disabled = True
            info.value, info.color = "در حال بررسی لایسنس...", "#38BDF8"
            page.update()
            ok, m = await check_license(k, did)
            btn.disabled = False
            if not ok:
                info.value, info.color = f"❌ {m}", "#EF4444"
                page.update()
                return
            save_license(k)
            try:
                c = get_client()
                await c.connect()
                if await c.is_user_authorized():
                    show_dashboard()
                    return
            except Exception:
                pass
            show_phone()

        btn, _ = make_btn("بررسی و ورود", verify, bgcolor="#2563EB")
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
        page.update()

    # ==========================================
    # صفحه ۲: شماره موبایل
    # ==========================================
    def show_phone(msg: str = ""):
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
                page.update()
                return

            btn.disabled = True
            info.value, info.color = "در حال ارسال کد تایید...", "#38BDF8"
            page.update()
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
                page.update()

        btn, _ = make_btn("ارسال کد تایید", send_otp, bgcolor="#10B981")
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
        page.update()

    # ==========================================
    # صفحه ۳: کد تایید
    # ==========================================
    def show_otp():
        page.controls.clear()
        info = ft.Text(f"کد تایید به {st['phone']} ارسال شد.", size=13, color="#38BDF8")
        code_box = ft.TextField(label="کد تایید", hint_text="12345", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor="#1E293B")
        pwd_box = ft.TextField(label="رمز تایید دومرحله‌ای (در صورت داشتن)", password=True, can_reveal_password=True, visible=st["need_2fa"], text_align=ft.TextAlign.LEFT, bgcolor="#1E293B")

        async def confirm(e):
            code = (code_box.value or "").strip()
            pwd = (pwd_box.value or "").strip()
            if not st["need_2fa"] and len(code) < 4:
                info.value, info.color = "کد تایید را کامل وارد کنید.", "#EF4444"
                page.update()
                return
            btn.disabled = True
            info.value, info.color = "در حال ورود...", "#38BDF8"
            page.update()
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
                page.update()

        btn, _ = make_btn("تایید و ورود", confirm, bgcolor="#2563EB")
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
        page.update()

    # ==========================================
    # صفحه ۴: داشبورد کامل سلف‌بات (چت‌ها، چندتایی، توربو، ریپلای)
    # ==========================================
    def show_dashboard():
        page.controls.clear()
        c = get_client()
        log("سلف‌بات با موفقیت به سروش‌پلاس متصل شد ✅", "#10B981")

        ev_mod = get_events_module()
        if not st["listener_added"] and ev_mod is not None and hasattr(ev_mod, "NewMessage"):
            st["listener_added"] = True

            @c.on(ev_mod.NewMessage(incoming=True))
            async def on_new_msg(event):
                if not st["ar_enabled"] or getattr(event, "out", False):
                    return
                if st["ar_pv_only"] and not getattr(event, "is_private", True):
                    return
                cid = str(getattr(event, "chat_id", "") or getattr(event, "sender_id", ""))
                if not cid or time.time() - st["replied"].get(cid, 0) < 15:
                    return
                st["replied"][cid] = time.time()
                try:
                    await event.reply(st["ar_text"])
                    log(f"ریپلای خودکار ارسال شد به {cid}", "#10B981")
                except Exception:
                    try:
                        await c.send_message(event.chat_id, st["ar_text"])
                        log(f"ریپلای خودکار ارسال شد به {cid}", "#10B981")
                    except Exception as ex:
                        log(f"خطای ریپلای: {ex}", "#EF4444")

        async def keep_alive():
            try:
                if callable(getattr(c, "run_until_disconnected", None)):
                    await c.run_until_disconnected()
            except Exception:
                pass

        asyncio.create_task(keep_alive())

        body_host = ft.Column(spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

        async def fetch_dialogs_list():
            items = []
            try:
                raw_dialogs = []
                if callable(getattr(c, "get_dialogs", None)):
                    raw_dialogs = await c.get_dialogs(limit=60)
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

        # --- ویجت بخش چت‌ها (پی‌وی و گپ) ---
        def build_chats_widget():
            manual_target = ft.TextField(
                label="آیدی یا شناسه چت انتخاب‌شده",
                hint_text="@username یا شناسه عددی",
                value=st["active_target"],
                text_align=ft.TextAlign.LEFT,
                bgcolor="#1E293B",
                on_change=lambda e: st.update({"active_target": (e.control.value or "").strip()}),
            )
            chat_list_col = ft.Column(spacing=8)

            def toggle_chat_item(e, cid: str, title: str):
                st["active_target"] = cid
                manual_target.value = cid
                if cid in st["selected_targets"]:
                    del st["selected_targets"][cid]
                else:
                    st["selected_targets"][cid] = title
                log(f"چت انتخاب شد: {title} ({cid})", "#38BDF8")
                refresh_chat_cards()
                page.update()

            def refresh_chat_cards():
                chat_list_col.controls.clear()
                flt = st["chat_filter"]
                filtered = [x for x in st["dialogs"] if flt == "all" or x["kind"] == flt]
                if not filtered:
                    chat_list_col.controls.append(
                        ft.Text("چتی یافت نشد. دکمه بروزرسانی لیست را بزنید یا آیدی را بالا وارد کنید.", size=12, color="#94A3B8")
                    )
                    return

                for item in filtered:
                    cid = item["id"]
                    title = item["title"]
                    is_pv = item["kind"] == "pv"
                    selected = cid in st["selected_targets"] or st["active_target"] == cid
                    badge = "👤 پی‌وی" if is_pv else "👥 گپ"
                    card = ft.Container(
                        padding=ft.Padding.all(12),
                        border_radius=ft.BorderRadius.all(10),
                        bgcolor="#1E293B" if selected else "#0F172A",
                        border=ft.Border.all(1.5 if selected else 1, "#38BDF8" if selected else "#1E293B"),
                        on_click=lambda e, c_id=cid, c_title=title: toggle_chat_item(e, c_id, c_title),
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
                                ft.Text("✅ انتخاب شده" if selected else "انتخاب", size=12, color="#10B981" if selected else "#64748B"),
                            ],
                        ),
                    )
                    chat_list_col.controls.append(card)

            def set_filter(e, mode: str):
                st["chat_filter"] = mode
                refresh_chat_cards()
                page.update()

            async def reload_chats(e):
                log("در حال دریافت لیست پی‌وی‌ها و گپ‌ها...", "#38BDF8")
                await fetch_dialogs_list()
                refresh_chat_cards()
                log(f"{len(st['dialogs'])} چت بارگذاری شد ✅", "#10B981")
                page.update()

            def clear_selected(e):
                st["selected_targets"].clear()
                st["active_target"] = ""
                manual_target.value = ""
                refresh_chat_cards()
                page.update()

            f_all, _ = make_btn("همه", lambda e: set_filter(e, "all"), bgcolor="#2563EB" if st["chat_filter"] == "all" else "#1E293B", height=38, expand=True)
            f_pv, _ = make_btn("👤 پی‌وی", lambda e: set_filter(e, "pv"), bgcolor="#2563EB" if st["chat_filter"] == "pv" else "#1E293B", height=38, expand=True)
            f_gp, _ = make_btn("👥 گپ‌ها", lambda e: set_filter(e, "group"), bgcolor="#2563EB" if st["chat_filter"] == "group" else "#1E293B", height=38, expand=True)
            rel_btn, _ = make_btn("🔄 بروزرسانی لیست چت‌ها", reload_chats, bgcolor="#10B981", height=40)
            clr_btn, _ = make_btn("پاک کردن انتخاب‌ها", clear_selected, color="#EF4444", kind="text")

            refresh_chat_cards()
            return ft.Container(
                bgcolor="#111827",
                padding=14,
                border_radius=ft.BorderRadius.all(12),
                border=ft.Border.all(1, "#1E293B"),
                content=ft.Column(
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                            ft.Text("💬 مدیریت پی‌وی و گپ‌ها", size=16, weight=ft.FontWeight.BOLD),
                            clr_btn,
                        ]),
                        manual_target,
                        rel_btn,
                        ft.Row(spacing=6, controls=[f_all, f_pv, f_gp]),
                        ft.Text(f"تعداد چت‌های انتخاب‌شده برای ارسال گروهی: {len(st['selected_targets'])}", size=12, color="#38BDF8"),
                        chat_list_col,
                    ],
                ),
            )

        # --- ویجت بخش ارسال چندتایی (Multi-Message) ---
        def build_multi_msg_widget():
            target_field = ft.TextField(
                label="مقصد ارسال (آیدی یا چت انتخاب‌شده)",
                hint_text="@username یا شناسه عددی",
                value=st["active_target"],
                text_align=ft.TextAlign.LEFT,
                bgcolor="#1E293B",
                on_change=lambda e: st.update({"active_target": (e.control.value or "").strip()}),
            )
            use_multi_targets = ft.Switch(
                label=f"ارسال همزمان به تمام چت‌های تیک‌خورده ({len(st['selected_targets'])} چت)",
                value=len(st["selected_targets"]) > 1,
            )
            new_msg_input = ft.TextField(
                label="متن پیام جدید برای افزودن به لیست چندتایی",
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
                label="تاخیر بین پیام‌ها (ثانیه)",
                value="0.5",
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
                    page.update()

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
                page.update()

            async def run_multi_sender():
                try:
                    rounds = max(1, int(rounds_box.value or 1))
                    dly = max(0.0, float(delay_box.value or 0.5))
                except ValueError:
                    rounds, dly = 1, 0.5

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
                    page.update()
                    return

                messages = list(st["multi_messages"])
                total_ops = rounds * len(targets) * len(messages)
                done = 0

                try:
                    for _ in range(rounds):
                        for raw_t in targets:
                            tgt = parse_target(raw_t)
                            for m_txt in messages:
                                if not st["multi_running"]:
                                    return
                                await c.send_message(tgt, m_txt)
                                done += 1
                                m_stat.value = f"ارسال شد: {done} از {total_ops}"
                                page.update()
                                if dly > 0:
                                    await asyncio.sleep(dly)
                    log(f"ارسال چندتایی با موفقیت انجام شد ({done} پیام) ✅", "#10B981")
                except Exception as ex:
                    log(f"خطا در ارسال چندتایی: {ex}", "#EF4444")
                finally:
                    st["multi_running"] = False
                    m_lbl.value = "🚀 شروع ارسال چندتایی"
                    m_btn.bgcolor = "#10B981"
                    page.update()

            async def toggle_multi(e):
                if st["multi_running"]:
                    st["multi_running"] = False
                    return
                if not st["multi_messages"]:
                    log("حداقل یک پیام به لیست چندتایی اضافه کنید.", "#EF4444")
                    return
                st["multi_running"] = True
                m_lbl.value = "⛔ توقف ارسال چندتایی"
                m_btn.bgcolor = "#EF4444"
                page.update()
                asyncio.create_task(run_multi_sender())

            add_btn, _ = make_btn("➕ افزودن به لیست", add_msg_item, bgcolor="#2563EB", height=40)
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
                        target_field,
                        use_multi_targets,
                        new_msg_input,
                        add_btn,
                        msg_items_col,
                        ft.Row(spacing=8, controls=[rounds_box, delay_box]),
                        m_btn,
                        m_stat,
                    ],
                ),
            )

        # --- ویجت بخش ارسال توربو ---
        def build_turbo_widget():
            target_box = ft.TextField(
                label="آیدی یا شناسه مقصد",
                hint_text="@username یا 12345678",
                value=st["active_target"],
                text_align=ft.TextAlign.LEFT,
                bgcolor="#1E293B",
                on_change=lambda e: st.update({"active_target": (e.control.value or "").strip()}),
            )
            msg_box = ft.TextField(label="متن پیام توربو", bgcolor="#1E293B")
            cnt_box = ft.TextField(label="تعداد", value="20", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor="#1E293B", expand=True)
            dly_box = ft.TextField(label="تاخیر (ثانیه)", value="0.1", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor="#1E293B", expand=True)
            t_stat = ft.Text("آماده", size=12, color="#94A3B8")

            async def turbo_run():
                sent = 0
                try:
                    total = max(1, int(cnt_box.value or 10))
                    dly = max(0.0, float(dly_box.value or 0.1))
                except ValueError:
                    total, dly = 10, 0.1
                tgt = parse_target(target_box.value or "")
                txt = (msg_box.value or "").strip()
                try:
                    while st["turbo_running"] and sent < total:
                        await c.send_message(tgt, txt)
                        sent += 1
                        t_stat.value = f"ارسال شد: {sent}/{total}"
                        page.update()
                        if dly > 0:
                            await asyncio.sleep(dly)
                    log(f"پایان ارسال توربو ({sent} پیام)", "#10B981")
                except Exception as ex:
                    log(f"خطای توربو: {ex}", "#EF4444")
                finally:
                    st["turbo_running"] = False
                    t_lbl.value = "🚀 شروع توربو"
                    t_btn.bgcolor = "#10B981"
                    page.update()

            async def toggle_turbo(e):
                if st["turbo_running"]:
                    st["turbo_running"] = False
                    return
                if not (target_box.value or "").strip() or not (msg_box.value or "").strip():
                    log("مقصد و متن را وارد کنید.", "#EF4444")
                    return
                st["turbo_running"] = True
                t_lbl.value = "⛔ توقف توربو"
                t_btn.bgcolor = "#EF4444"
                page.update()
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
                        ft.Text("🚀 ارسال توربو", size=16, weight=ft.FontWeight.BOLD),
                        target_box,
                        msg_box,
                        ft.Row(spacing=8, controls=[cnt_box, dly_box]),
                        t_btn,
                        t_stat,
                    ],
                ),
            )

        # --- ویجت بخش ریپلای خودکار ---
        def build_autoreply_widget():
            ar_sw = ft.Switch(label="فعال‌سازی ریپلای خودکار", value=st["ar_enabled"])
            pv_sw = ft.Switch(label="فقط در پی‌وی (PV)", value=st["ar_pv_only"])
            ar_box = ft.TextField(label="متن پاسخ خودکار", value=st["ar_text"], multiline=True, min_lines=2, bgcolor="#1E293B")

            def save_ar(e):
                st["ar_enabled"] = bool(ar_sw.value)
                st["ar_pv_only"] = bool(pv_sw.value)
                st["ar_text"] = (ar_box.value or "").strip() or "پاسخ خودکار"
                log("تنظیمات ریپلای خودکار ذخیره شد ✅", "#38BDF8")

            save_btn, _ = make_btn("ذخیره تنظیمات ریپلای", save_ar, bgcolor="#2563EB", height=44)
            return ft.Container(
                bgcolor="#111827",
                padding=14,
                border_radius=ft.BorderRadius.all(12),
                border=ft.Border.all(1, "#1E293B"),
                content=ft.Column(
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("🤖 ریپلای خودکار", size=16, weight=ft.FontWeight.BOLD),
                        ar_sw,
                        pv_sw,
                        ar_box,
                        save_btn,
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
            elif tab == "autoreply":
                body_host.controls.append(build_autoreply_widget())

        def switch_tab(e, tab_name: str):
            st["active_tab"] = tab_name
            for k, btn_ctrl in nav_buttons.items():
                btn_ctrl.bgcolor = "#2563EB" if k == tab_name else "#1E293B"
            render_body()
            page.update()

        async def logout(e):
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
            st["listener_added"] = False
            base = os.path.basename(SESSION_PATH)
            for f in os.listdir(STORAGE_DIR):
                if f.startswith(base):
                    try:
                        os.remove(os.path.join(STORAGE_DIR, f))
                    except Exception:
                        pass
            show_phone("از حساب خارج شدید.")

        out_btn, _ = make_btn("خروج", logout, color="#EF4444", kind="text")
        b_chats, _ = make_btn("💬 چت‌ها", lambda e: switch_tab(e, "chats"), bgcolor="#2563EB", height=40, expand=True)
        b_multi, _ = make_btn("📨 چندتایی", lambda e: switch_tab(e, "multi"), bgcolor="#1E293B", height=40, expand=True)
        b_turbo, _ = make_btn("🚀 توربو", lambda e: switch_tab(e, "turbo"), bgcolor="#1E293B", height=40, expand=True)
        b_ar, _ = make_btn("🤖 ریپلای", lambda e: switch_tab(e, "autoreply"), bgcolor="#1E293B", height=40, expand=True)
        nav_buttons = {"chats": b_chats, "multi": b_multi, "turbo": b_turbo, "autoreply": b_ar}

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
                        ft.Text("⚡ V3X Selfbot", size=18, weight=ft.FontWeight.BOLD, color="#38BDF8"),
                        out_btn,
                    ],
                ),
            ),
            ft.Row(spacing=6, controls=[b_chats, b_multi, b_turbo, b_ar]),
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
        page.update()
        asyncio.create_task(fetch_dialogs_list())

    saved = get_saved_license()
    if saved:
        ok, m = await check_license(saved, did)
        if ok:
            try:
                c = get_client()
                await c.connect()
                if await c.is_user_authorized():
                    show_dashboard()
                    return
            except Exception:
                pass
            show_phone()
            return
        show_license(m)
        return
    show_license()


if hasattr(ft, "run"):
    ft.run(main)
else:
    ft.app(target=main)
