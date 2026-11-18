import asyncio, importlib, inspect, json, os, pkgutil, platform, tempfile, time, uuid
import flet as ft
import httpx

LICENSE_URL = "https://selfbot-license.krymyhady314.workers.dev"
STORAGE_DIR = os.getenv("FLET_APP_STORAGE_DATA") or tempfile.gettempdir()
os.makedirs(STORAGE_DIR, exist_ok=True)

LIC_FILE = os.path.join(STORAGE_DIR, "v3x_lic.json")
AUTH_FLAG = os.path.join(STORAGE_DIR, "v3x_authed.flag")
SESSION_PATH = os.path.join(STORAGE_DIR, "v3x_splus")


def get_device_id() -> str:
    """ساخت شناسه سخت‌افزاری ثابت که حتی با حذف و نصب مجدد برنامه تغییر نمی‌کند."""
    hw_parts = [platform.machine(), str(uuid.getnode())]
    if os.path.exists("/system/build.prop"):
        try:
            with open("/system/build.prop", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.startswith(("ro.product.model=", "ro.product.device=", "ro.build.fingerprint=", "ro.serialno=")):
                        hw_parts.append(line.strip())
        except Exception:
            pass
    raw = "|".join(hw_parts)
    return "V3X-" + uuid.uuid5(uuid.NAMESPACE_DNS, raw).hex[:16].upper()


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


def _is_truthy(val) -> bool:
    if val is True or val == 1:
        return True
    if isinstance(val, str) and val.strip().lower() in ("true", "1", "valid", "ok", "active", "success", "authorized", "verified"):
        return True
    return False


async def check_license(key: str, did: str) -> tuple[bool, str]:
    payload = {
        "key": key,
        "license": key,
        "license_key": key,
        "code": key,
        "device_id": did,
        "hwid": did,
        "device": did,
        "hardware_id": did,
    }
    base = LICENSE_URL.rstrip("/")
    server_msg = ""

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http:
        # ۱. بررسی با متد POST روی مسیرهای استاندارد
        for path in ("/verify", "/check", "/api/verify", ""):
            try:
                r = await http.post(f"{base}{path}", json=payload)
                if r.status_code in (404, 405):
                    continue
                txt = r.text.strip()
                if txt.lower() in ("valid", "ok", "true", "success"):
                    return True, "لایسنس تایید شد"
                try:
                    d = r.json()
                    if isinstance(d, dict):
                        if any(_is_truthy(d.get(k)) for k in ("valid", "ok", "success", "authorized", "active", "allowed", "verified")):
                            return True, str(d.get("message") or d.get("msg") or "لایسنس تایید شد")
                        if _is_truthy(d.get("status")) or _is_truthy(d.get("result")):
                            return True, str(d.get("message") or d.get("msg") or "لایسنس تایید شد")
                        reason = d.get("message") or d.get("msg") or d.get("error") or d.get("reason") or d.get("detail")
                        if reason:
                            server_msg = str(reason)
                except Exception:
                    if txt and len(txt) < 120:
                        server_msg = txt
            except Exception as e:
                server_msg = f"خطای شبکه: {e}"

        # ۲. بررسی با متد GET در صورت تنظیم Worker روی Query Params
        for path in ("/verify", "/check", ""):
            try:
                r = await http.get(f"{base}{path}", params={"key": key, "license": key, "device_id": did, "hwid": did})
                if r.status_code in (404, 405):
                    continue
                txt = r.text.strip()
                if txt.lower() in ("valid", "ok", "true", "success"):
                    return True, "لایسنس تایید شد"
                try:
                    d = r.json()
                    if isinstance(d, dict):
                        if any(_is_truthy(d.get(k)) for k in ("valid", "ok", "success", "authorized", "active", "allowed", "verified")):
                            return True, str(d.get("message") or d.get("msg") or "لایسنس تایید شد")
                        if _is_truthy(d.get("status")) or _is_truthy(d.get("result")):
                            return True, str(d.get("message") or d.get("msg") or "لایسنس تایید شد")
                        reason = d.get("message") or d.get("msg") or d.get("error") or d.get("reason") or d.get("detail")
                        if reason and not server_msg:
                            server_msg = str(reason)
                except Exception:
                    pass
            except Exception:
                pass

    return False, (server_msg or "لایسنس نامعتبر است یا به دستگاه دیگری متصل شده است")


def create_splus_client():
    import splusthon
    target_methods = {"connect", "send_code", "sign_in", "send_message", "get_me", "start", "run"}
    best_cls = None
    best_score = -1

    modules = [splusthon]
    if hasattr(splusthon, "__path__"):
        for _, mod_name, _ in pkgutil.walk_packages(splusthon.__path__, "splusthon."):
            try:
                modules.append(importlib.import_module(mod_name))
            except Exception:
                pass

    for mod in modules:
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if "base" in name.lower():
                continue
            attrs = set(dir(obj))
            score = len(attrs & target_methods) * 10
            if "client" in name.lower():
                score += 5
            if score > best_score and score > 0:
                best_score = score
                best_cls = obj

    if best_cls is None:
        raise RuntimeError(f"کلاس کلاینت در splusthon یافت نشد: {dir(splusthon)}")

    sig = inspect.signature(best_cls.__init__)
    kwargs = {}
    session_set = False
    for p_name, p in sig.parameters.items():
        if p_name == "self" or p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        if p_name in ("session", "session_name", "name", "path", "session_path"):
            kwargs[p_name] = SESSION_PATH
            session_set = True
        elif p.default is inspect.Parameter.empty:
            if not session_set:
                kwargs[p_name] = SESSION_PATH
                session_set = True
            elif "id" in p_name:
                kwargs[p_name] = 123456
            else:
                kwargs[p_name] = "0123456789abcdef0123456789abcdef"

    try:
        return best_cls(**kwargs)
    except TypeError:
        try:
            return best_cls(SESSION_PATH)
        except TypeError:
            return best_cls()


async def call_api(obj, names: tuple, kw: dict, args: tuple = ()):
    targets = [obj] + [getattr(obj, s) for s in ("auth", "account", "messages", "methods") if hasattr(obj, s)]
    fn = None
    for t in targets:
        for n in names:
            if callable(getattr(t, n, None)):
                fn = getattr(t, n)
                break
        if fn:
            break
    if not fn:
        avail = [m for m in dir(obj) if not m.startswith("_")]
        raise AttributeError(f"متد {names[0]} یافت نشد. متدهای موجود: {avail[:20]}")
    sig = inspect.signature(fn).parameters
    filtered = {k: v for k, v in kw.items() if k in sig}
    try:
        res = fn(**filtered) if (filtered or not args) else fn(*args)
    except TypeError:
        res = fn(*args)
    return await res if inspect.isawaitable(res) else res


def make_btn(label: str, on_click, bgcolor: str = "#2563EB", color: str = "#FFFFFF", height: int = 46, kind: str = "filled"):
    lbl = ft.Text(label, color=color, weight=ft.FontWeight.W_600)
    if kind == "outlined":
        btn_cls = getattr(ft, "OutlinedButton", ft.Button)
        return btn_cls(content=lbl, on_click=on_click, height=height), lbl
    if kind == "text":
        btn_cls = getattr(ft, "TextButton", ft.Button)
        return btn_cls(content=lbl, on_click=on_click), lbl
    btn_cls = getattr(ft, "Button", None) or getattr(ft, "ElevatedButton", None)
    return btn_cls(content=lbl, bgcolor=bgcolor, color=color, height=height, on_click=on_click), lbl


async def main(page: ft.Page):
    page.title = "V3X Selfbot"
    page.bgcolor = "#0B1120"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 16
    page.scroll = ft.ScrollMode.AUTO
    page.rtl = True

    did = get_device_id()
    st = {
        "client": None,
        "phone": "",
        "hash": None,
        "turbo": False,
        "ar": False,
        "ar_text": "آفلاین هستم، پیام شما ثبت شد.",
        "pv_only": True,
        "replied": {},
    }
    logs = ft.Column(spacing=4, height=130, scroll=ft.ScrollMode.AUTO)

    def log(txt: str, col: str = "#94A3B8"):
        logs.controls.insert(0, ft.Text(f"[{time.strftime('%H:%M:%S')}] {txt}", size=12, color=col, selectable=True))
        logs.controls = logs.controls[:25]
        try:
            page.update()
        except Exception:
            pass

    def get_client():
        if st["client"] is None:
            st["client"] = create_splus_client()
        return st["client"]

    def show_license(msg: str = ""):
        page.controls.clear()
        info = ft.Text(msg, size=13, color="#F59E0B", selectable=True)
        dev_box = ft.TextField(label="شناسه سخت‌افزاری دائمی دستگاه (Device ID)", value=did, read_only=True, text_align=ft.TextAlign.LEFT, bgcolor="#0F172A")
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
                info.value, info.color = "متن بالا را لمس کرده و دستی کپی کنید.", "#F59E0B"
            page.update()

        async def verify(e):
            k = (key_box.value or "").strip()
            if not k:
                info.value, info.color = "کلید لایسنس را وارد کنید.", "#EF4444"
                page.update()
                return
            btn.disabled = True
            info.value, info.color = "در حال استعلام از سرور لایسنس...", "#38BDF8"
            page.update()
            ok, m = await check_license(k, did)
            btn.disabled = False
            if not ok:
                info.value, info.color = f"❌ {m}", "#EF4444"
                page.update()
                return
            save_license(k)
            if os.path.exists(AUTH_FLAG):
                try:
                    c = get_client()
                    await call_api(c, ("connect", "initialize"), {})
                    show_dashboard()
                    return
                except Exception:
                    pass
            show_phone()

        btn, _ = make_btn("بررسی و ورود", verify, bgcolor="#2563EB")
        copy_btn, _ = make_btn("📋 کپی شناسه دستگاه", copy_id, color="#38BDF8", kind="outlined")

        page.add(ft.Container(bgcolor="#111827", padding=18, border_radius=12, content=ft.Column(
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
        )))
        page.update()

    def show_phone(msg: str = ""):
        page.controls.clear()
        info = ft.Text(msg, size=13, color="#F59E0B", selectable=True)
        ph_box = ft.TextField(label="شماره موبایل سروش‌پلاس", hint_text="09123456789", keyboard_type=ft.KeyboardType.PHONE, text_align=ft.TextAlign.LEFT, bgcolor="#1E293B")

        async def send_otp(e):
            d = "".join(c for c in (ph_box.value or "") if c.isdigit())
            phone = "98" + d[1:] if d.startswith("09") else ("98" + d if d.startswith("9") and len(d) == 10 else d)
            if len(phone) < 10:
                info.value, info.color = "شماره موبایل معتبر وارد کنید.", "#EF4444"
                page.update()
                return
            btn.disabled = True
            info.value, info.color = "در حال اتصال و ارسال کد تایید...", "#38BDF8"
            page.update()
            try:
                c = get_client()
                await call_api(c, ("connect", "initialize"), {})
                res = await call_api(c, ("send_code", "request_code", "send_otp"), {"phone_number": phone, "phone": phone, "mobile": phone}, (phone,))
                st["phone"] = phone
                st["hash"] = res if isinstance(res, str) else (res.get("phone_code_hash") if isinstance(res, dict) else getattr(res, "phone_code_hash", None))
                btn.disabled = False
                show_otp()
            except Exception as ex:
                btn.disabled = False
                info.value, info.color = f"خطا: {ex}", "#EF4444"
                page.update()

        btn, _ = make_btn("ارسال کد تایید", send_otp, bgcolor="#10B981")
        page.add(ft.Container(bgcolor="#111827", padding=18, border_radius=12, content=ft.Column(
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Text("ورود به سروش‌پلاس", size=20, weight=ft.FontWeight.BOLD),
                ph_box,
                btn,
                info,
            ],
        )))
        page.update()

    def show_otp():
        page.controls.clear()
        info = ft.Text(f"کد تایید به {st['phone']} ارسال شد.", size=13, color="#38BDF8", selectable=True)
        code_box = ft.TextField(label="کد تایید", hint_text="12345", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor="#1E293B")

        async def confirm(e):
            code = (code_box.value or "").strip()
            if len(code) < 4:
                info.value, info.color = "کد تایید را کامل وارد کنید.", "#EF4444"
                page.update()
                return
            btn.disabled = True
            info.value, info.color = "در حال تایید و ورود...", "#38BDF8"
            page.update()
            try:
                c = get_client()
                args = (st["phone"], st["hash"], code) if st["hash"] else (st["phone"], code)
                await call_api(c, ("sign_in", "verify_code", "login"), {"phone_number": st["phone"], "phone": st["phone"], "phone_code": code, "code": code, "phone_code_hash": st["hash"]}, args)
                open(AUTH_FLAG, "w", encoding="utf-8").write("1")
                btn.disabled = False
                show_dashboard()
            except Exception as ex:
                btn.disabled = False
                info.value, info.color = f"خطا: {ex}", "#EF4444"
                page.update()

        btn, _ = make_btn("تایید و ورود", confirm, bgcolor="#2563EB")
        chg_btn, _ = make_btn("تغییر شماره", lambda e: show_phone(), color="#94A3B8", kind="text")
        page.add(ft.Container(bgcolor="#111827", padding=18, border_radius=12, content=ft.Column(
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Text("تایید کد", size=20, weight=ft.FontWeight.BOLD),
                code_box,
                btn,
                chg_btn,
                info,
            ],
        )))
        page.update()

    def show_dashboard():
        page.controls.clear()
        c = get_client()
        log("سلف‌بات آماده به کار است ✅", "#10B981")

        async def bg_worker():
            try:
                if hasattr(c, "on_message"):
                    @c.on_message()
                    async def on_msg(u):
                        if not st["ar"] or getattr(u, "is_outgoing", False):
                            return
                        cid = str(getattr(u, "object_guid", "") or getattr(u, "chat_id", ""))
                        if not cid or (st["pv_only"] and not cid.startswith("u0")):
                            return
                        if time.time() - st["replied"].get(cid, 0) < 15:
                            return
                        st["replied"][cid] = time.time()
                        await call_api(c, ("send_message", "send_text"), {"object_guid": cid, "chat_id": cid, "text": st["ar_text"], "message": st["ar_text"]}, (cid, st["ar_text"]))
                        log(f"ریپلای خودکار به {cid}", "#10B981")
                for r in ("run_until_disconnected", "run", "idle"):
                    if callable(getattr(c, r, None)):
                        res = getattr(c, r)()
                        if inspect.isawaitable(res):
                            await res
                        break
            except Exception:
                pass

        asyncio.create_task(bg_worker())

        target_box = ft.TextField(label="آیدی یا GUID مقصد", hint_text="u0XXXX...", text_align=ft.TextAlign.LEFT, bgcolor="#1E293B")
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
            tgt, txt = (target_box.value or "").strip(), (msg_box.value or "").strip()
            try:
                while st["turbo"] and sent < total:
                    await call_api(c, ("send_message", "send_text"), {"object_guid": tgt, "chat_id": tgt, "text": txt, "message": txt}, (tgt, txt))
                    sent += 1
                    t_stat.value = f"ارسال شد: {sent}/{total}"
                    page.update()
                    if dly > 0:
                        await asyncio.sleep(dly)
                log(f"پایان توربو ({sent} پیام)", "#10B981")
            except Exception as ex:
                log(f"خطای توربو: {ex}", "#EF4444")
            finally:
                st["turbo"] = False
                t_lbl.value = "🚀 شروع توربو"
                t_btn.bgcolor = "#10B981"
                page.update()

        async def toggle_turbo(e):
            if st["turbo"]:
                st["turbo"] = False
                return
            if not (target_box.value or "").strip() or not (msg_box.value or "").strip():
                log("مقصد و متن را وارد کنید.", "#EF4444")
                return
            st["turbo"] = True
            t_lbl.value = "⛔ توقف توربو"
            t_btn.bgcolor = "#EF4444"
            page.update()
            asyncio.create_task(turbo_run())

        t_btn, t_lbl = make_btn("🚀 شروع توربو", toggle_turbo, bgcolor="#10B981", height=44)
        ar_sw = ft.Switch(label="ریپلای خودکار", value=st["ar"])
        pv_sw = ft.Switch(label="فقط پی‌وی", value=st["pv_only"])
        ar_box = ft.TextField(label="متن ریپلای خودکار", value=st["ar_text"], bgcolor="#1E293B")

        def save_ar(e):
            st["ar"], st["pv_only"], st["ar_text"] = bool(ar_sw.value), bool(pv_sw.value), (ar_box.value or "").strip() or "پاسخ خودکار"
            log("تنظیمات ریپلای ذخیره شد ✅", "#38BDF8")

        async def logout(e):
            st["turbo"] = False
            st["client"] = None
            if os.path.exists(AUTH_FLAG):
                try:
                    os.remove(AUTH_FLAG)
                except Exception:
                    pass
            base = os.path.basename(SESSION_PATH)
            for f in os.listdir(STORAGE_DIR):
                if f.startswith(base):
                    try:
                        os.remove(os.path.join(STORAGE_DIR, f))
                    except Exception:
                        pass
            show_phone("خارج شدید.")

        save_btn, _ = make_btn("ذخیره ریپلای", save_ar, bgcolor="#2563EB", height=42)
        out_btn, _ = make_btn("خروج", logout, color="#EF4444", kind="text")

        page.add(
            ft.Container(bgcolor="#111827", padding=14, border_radius=12, content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[ft.Text("⚡ V3X Panel", size=18, weight=ft.FontWeight.BOLD, color="#38BDF8"), out_btn],
            )),
            ft.Container(bgcolor="#111827", padding=14, border_radius=12, content=ft.Column(
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[ft.Text("🚀 ارسال توربو", weight=ft.FontWeight.BOLD), target_box, msg_box, ft.Row(spacing=8, controls=[cnt_box, dly_box]), t_btn, t_stat],
            )),
            ft.Container(bgcolor="#111827", padding=14, border_radius=12, content=ft.Column(
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[ft.Text("🤖 ریپلای خودکار", weight=ft.FontWeight.BOLD), ar_sw, pv_sw, ar_box, save_btn],
            )),
            ft.Container(bgcolor="#0F172A", padding=12, border_radius=12, content=ft.Column(
                spacing=6,
                controls=[ft.Text("📜 گزارش زنده", size=13, color="#94A3B8"), logs],
            )),
        )
        page.update()

    saved = get_saved_license()
    if saved:
        ok, m = await check_license(saved, did)
        if ok:
            if os.path.exists(AUTH_FLAG):
                try:
                    c = get_client()
                    await call_api(c, ("connect", "initialize"), {})
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
