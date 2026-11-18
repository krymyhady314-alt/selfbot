import asyncio, hashlib, importlib, inspect, json, os, pkgutil, platform, random, subprocess, tempfile, time
import flet as ft
import httpx

LICENSE_URL = "https://selfbot-license.krymyhady314.workers.dev"
OWNER_TEST_KEY = "V3X-OWNER-2026"

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
    did = "V3X-" + hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16].upper()
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

    payload = {
        "action": "verify",
        "type": "verify",
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
        ("POST", f"{base}/verify"),
        ("GET", f"{base}/verify/{clean_key}"),
        ("POST", f"{base}/check"),
        ("GET", f"{base}/check/{clean_key}"),
        ("POST", f"{base}/validate"),
        ("POST", f"{base}/activate"),
        ("POST", f"{base}/api/verify"),
        ("POST", f"{base}/api/check"),
        ("GET", f"{base}/verify"),
        ("GET", f"{base}/check"),
        ("POST", base),
        ("GET", base),
    ]

    last_err = "کلید لایسنس نامعتبر است یا در سرور ثبت نشده"
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http:
        for method, url in routes:
            try:
                if method == "POST":
                    r = await http.post(url, params=payload, json=payload)
                else:
                    r = await http.get(url, params=payload)

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

                st_val = str(d.get("status", "")).lower().strip()
                if (
                    d.get("valid") is True
                    or d.get("ok") is True
                    or d.get("success") is True
                    or d.get("authorized") is True
                    or st_val in ("valid", "ok", "active", "success", "activated", "true")
                ):
                    return True, str(d.get("message") or d.get("msg") or "لایسنس تایید شد")

                if st_val == "online" and not any(k in d for k in ("valid", "ok", "error", "reason", "message")):
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
        return splusthon.events if hasattr(splusthon, "events") else importlib.import_module("splusthon.events")
    except Exception:
        return None


def make_btn(label: str, on_click, bgcolor: str = "#2563EB", color: str = "#FFFFFF", height: int = 44, kind: str = "filled"):
    lbl = ft.Text(label, color=color, weight=ft.FontWeight.W_600, size=13)
    if kind == "outlined":
        cls = getattr(ft, "OutlinedButton", ft.Button)
        return cls(content=lbl, on_click=on_click, height=height), lbl
    if kind == "text":
        cls = getattr(ft, "TextButton", ft.Button)
        return cls(content=lbl, on_click=on_click), lbl
    cls = getattr(ft, "Button", None) or getattr(ft, "ElevatedButton", None)
    return cls(content=lbl, bgcolor=bgcolor, color=color, height=height, on_click=on_click), lbl


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
        "tab": "turbo",
        "turbo": False,
        "msg_mode": "single",          # single | multi
        "multi_msgs": ["سلام", "خوبی؟"],
        "selected_chat_id": "",
        "selected_chat_title": "",
        "selected_entity": None,
        "selected_msg_id": None,
        "selected_msg_preview": "",
        "chat_filter": "all",          # all | pv | group
        "dialogs": [],
        "opened_dialog": None,
        "recent_msgs": [],
        "ar_enabled": False,
        "ar_scope": "pv",              # pv | group | all | selected
        "ar_text": "سلام! پیام شما ثبت شد.",
        "ar_cooldown": 10,
        "replied": {},
    }
    logs = ft.Column(spacing=4, height=180, scroll=ft.ScrollMode.AUTO)

    def log(txt: str, col: str = "#94A3B8"):
        logs.controls.insert(0, ft.Text(f"[{time.strftime('%H:%M:%S')}] {txt}", size=12, color=col, selectable=True))
        logs.controls = logs.controls[:35]
        try:
            page.update()
        except Exception:
            pass

    def get_client():
        if st["client"] is None:
            st["client"] = create_splus_client()
        return st["client"]

    async def send_smart_message(c, target, text: str, reply_to_id=None):
        if reply_to_id is not None:
            try:
                await c.send_message(target, text, reply_to=int(reply_to_id))
                return
            except TypeError:
                try:
                    await c.send_message(target, text, reply_to_msg_id=int(reply_to_id))
                    return
                except Exception:
                    pass
        await c.send_message(target, text)

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

        btn, _ = make_btn("بررسی و ورود", verify, bgcolor="#2563EB", height=46)
        copy_btn, _ = make_btn("📋 کپی شناسه دستگاه", copy_id, color="#38BDF8", kind="outlined")
        page.add(ft.Container(bgcolor="#111827", padding=18, border_radius=12, content=ft.Column(
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[ft.Text("V3X SELFBOT", size=22, weight=ft.FontWeight.BOLD, color="#38BDF8"), dev_box, copy_btn, key_box, btn, info],
        )))
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
                info.value, info.color = "شماره موبایل معتبر وارد کنید.", "#EF4444"
                page.update()
                return

            btn.disabled = True
            info.value, info.color = "در حال ارسال کد تایید...", "#38BDF8"
            page.update()
            try:
                c = get_client()
                if not c.is_connected():
                    await c.connect()
                res, used_phone, last_err = None, p98, None
                for fmt in (p98, f"+{p98}", p09):
                    try:
                        res = await c.send_code_request(fmt)
                        used_phone, last_err = fmt, None
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

        btn, _ = make_btn("ارسال کد تایید", send_otp, bgcolor="#10B981", height=46)
        page.add(ft.Container(bgcolor="#111827", padding=18, border_radius=12, content=ft.Column(
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[ft.Text("ورود به سروش‌پلاس", size=20, weight=ft.FontWeight.BOLD), ph_box, btn, info],
        )))
        page.update()

    # ==========================================
    # صفحه ۳: کد تایید
    # ==========================================
    def show_otp():
        page.controls.clear()
        info = ft.Text(f"کد تایید به {st['phone']} ارسال شد.", size=13, color="#38BDF8")
        code_box = ft.TextField(label="کد تایید", hint_text="12345", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor="#1E293B")
        pwd_box = ft.TextField(label="رمز تایید دومرحله‌ای", password=True, can_reveal_password=True, visible=st["need_2fa"], text_align=ft.TextAlign.LEFT, bgcolor="#1E293B")

        async def confirm(e):
            code, pwd = (code_box.value or "").strip(), (pwd_box.value or "").strip()
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
                if any(w in str(ex).lower() for w in ("password", "2fa")):
                    st["need_2fa"] = True
                    pwd_box.visible = True
                    info.value, info.color = "رمز دومرحله‌ای را وارد و دوباره تایید کنید.", "#F59E0B"
                else:
                    info.value, info.color = f"خطا: {ex}", "#EF4444"
                page.update()

        btn, _ = make_btn("تایید و ورود", confirm, bgcolor="#2563EB", height=46)
        chg_btn, _ = make_btn("تغییر شماره", lambda e: show_phone(), color="#94A3B8", kind="text")
        page.add(ft.Container(bgcolor="#111827", padding=18, border_radius=12, content=ft.Column(
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[ft.Text("تایید کد", size=20, weight=ft.FontWeight.BOLD), code_box, pwd_box, btn, chg_btn, info],
        )))
        page.update()

    # ==========================================
    # صفحه ۴: پنل اصلی مدیریت
    # ==========================================
    def show_dashboard():
        page.controls.clear()
        c = get_client()
        log("سلف‌بات به سروش‌پلاس متصل شد ✅", "#10B981")

        def get_active_reply_pool() -> list[str]:
            if st["msg_mode"] == "multi":
                valid = [m.strip() for m in st["multi_msgs"] if m and m.strip()]
                if valid:
                    return valid
            single = (ar_box.value or "").strip() or st["ar_text"]
            return [single]

        ev_mod = get_events_module()
        if not st["listener_added"] and ev_mod is not None and hasattr(ev_mod, "NewMessage"):
            st["listener_added"] = True

            @c.on(ev_mod.NewMessage(incoming=True))
            async def on_new_msg(event):
                if not st["ar_enabled"] or getattr(event, "out", False):
                    return
                cid = str(getattr(event, "chat_id", "") or getattr(event, "sender_id", ""))
                if not cid:
                    return

                is_grp = bool(getattr(event, "is_group", False) or getattr(event, "is_channel", False))
                scope = st["ar_scope"]
                if scope == "pv" and is_grp:
                    return
                if scope == "group" and not is_grp:
                    return
                if scope == "selected" and cid != str(st["selected_chat_id"]):
                    return

                now = time.time()
                if now - st["replied"].get(cid, 0) < st["ar_cooldown"]:
                    return
                st["replied"][cid] = now

                reply_txt = random.choice(get_active_reply_pool())
                target_msg_id = st["selected_msg_id"] if (cid == str(st["selected_chat_id"]) and st["selected_msg_id"]) else getattr(event, "id", None)

                try:
                    await send_smart_message(c, event.chat_id, reply_txt, reply_to_id=target_msg_id)
                    log(f"ریپلای خودکار به {cid}: {reply_txt[:25]}", "#10B981")
                except Exception as ex:
                    log(f"خطای ریپلای: {ex}", "#EF4444")

        async def keep_alive():
            try:
                if callable(getattr(c, "run_until_disconnected", None)):
                    await c.run_until_disconnected()
            except Exception:
                pass

        asyncio.create_task(keep_alive())

        # --- کنترل‌های مشترک ---
        target_box = ft.TextField(label="شناسه چت/گپ یا @username", hint_text="از تب چت‌ها انتخاب کنید یا بنویسید", text_align=ft.TextAlign.LEFT, bgcolor="#1E293B")
        single_msg_box = ft.TextField(label="متن پیام (حالت تک‌پیام)", multiline=True, min_lines=2, bgcolor="#1E293B")
        cnt_box = ft.TextField(label="تعداد ارسال", value="20", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor="#1E293B", expand=True)
        dly_box = ft.TextField(label="تاخیر (ثانیه)", value="0.1", keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor="#1E293B", expand=True)
        t_stat = ft.Text("آماده ارسال", size=12, color="#94A3B8")

        ar_sw = ft.Switch(label="فعال‌سازی ریپلای خودکار روی پیام‌های جدید", value=st["ar_enabled"])
        ar_box = ft.TextField(label="متن ریپلای خودکار (اگر حالت قاطی خاموش باشد)", value=st["ar_text"], multiline=True, min_lines=2, bgcolor="#1E293B")
        cd_box = ft.TextField(label="تاخیر بین پاسخ‌های خودکار (ثانیه)", value=str(st["ar_cooldown"]), keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.LEFT, bgcolor="#1E293B")

        def pill(title: str, active: bool, on_tap):
            return ft.Container(
                content=ft.Text(title, size=12, weight=ft.FontWeight.W_600, color="#FFFFFF" if active else "#94A3B8", text_align=ft.TextAlign.CENTER),
                bgcolor="#2563EB" if active else "#1E293B",
                padding=ft.Padding(8, 8, 8, 8),
                border_radius=8,
                expand=True,
                on_click=on_tap,
            )

        # --- منطق ارسال توربو (تکی و قاطی + ریپلای روی پیام انتخابی) ---
        async def turbo_run():
            sent = 0
            try:
                total = max(1, int(cnt_box.value or 10))
                dly = max(0.0, float(dly_box.value or 0.1))
            except ValueError:
                total, dly = 10, 0.1

            raw_tgt = (target_box.value or "").strip()
            if st["selected_entity"] is not None and raw_tgt == str(st["selected_chat_id"]):
                tgt = st["selected_entity"]
            else:
                tgt = int(raw_tgt) if raw_tgt.lstrip("-").isdigit() else raw_tgt

            if st["msg_mode"] == "multi":
                pool = [m.strip() for m in st["multi_msgs"] if m and m.strip()]
            else:
                pool = [(single_msg_box.value or "").strip()]

            pool = [p for p in pool if p]
            if not pool:
                log("حداقل یک پیام وارد کنید!", "#EF4444")
                st["turbo"] = False
                return

            rep_id = st["selected_msg_id"]
            try:
                while st["turbo"] and sent < total:
                    chosen_txt = random.choice(pool)
                    await send_smart_message(c, tgt, chosen_txt, reply_to_id=rep_id)
                    sent += 1
                    t_stat.value = f"ارسال شد: {sent} از {total} | پیام: {chosen_txt[:18]}..."
                    t_stat.color = "#10B981"
                    page.update()
                    if dly > 0:
                        await asyncio.sleep(dly)
                log(f"عملیات ارسال تکمیل شد ({sent} پیام)", "#10B981")
            except Exception as ex:
                log(f"خطا در ارسال: {ex}", "#EF4444")
                t_stat.value, t_stat.color = f"خطا: {ex}", "#EF4444"
            finally:
                st["turbo"] = False
                t_lbl.value = "🚀 شروع ارسال توربو"
                t_btn.bgcolor = "#10B981"
                page.update()

        async def toggle_turbo(e):
            if st["turbo"]:
                st["turbo"] = False
                return
            if not (target_box.value or "").strip():
                log("ابتدا یک پی‌وی یا گپ انتخاب کنید.", "#EF4444")
                return
            st["turbo"] = True
            t_lbl.value = "⛔ توقف فوری"
            t_btn.bgcolor = "#EF4444"
            page.update()
            asyncio.create_task(turbo_run())

        t_btn, t_lbl = make_btn("🚀 شروع ارسال توربو", toggle_turbo, bgcolor="#10B981", height=44)

        def save_ar(e):
            st["ar_enabled"] = bool(ar_sw.value)
            st["ar_text"] = (ar_box.value or "").strip() or "پاسخ خودکار"
            try:
                st["ar_cooldown"] = max(1, int(cd_box.value or 10))
            except ValueError:
                st["ar_cooldown"] = 10
            log("تنظیمات ریپلای خودکار ذخیره شد ✅", "#10B981")

        # --- بخش جداگانه لیست پی‌وی‌ها، گپ‌ها و پیام‌های اخیر داخل آن‌ها ---
        chats_area = ft.Column(spacing=8)

        async def load_dialogs(e=None):
            st["opened_dialog"] = None
            chats_area.controls = [ft.Text("در حال دریافت لیست پی‌وی‌ها و گپ‌ها...", size=12, color="#38BDF8")]
            page.update()
            try:
                st["dialogs"] = await c.get_dialogs(limit=40)
                render_chats_section()
            except Exception as ex:
                chats_area.controls = [ft.Text(f"خطا در دریافت لیست: {ex}", size=12, color="#EF4444")]
                page.update()

        async def open_dialog_messages(dlg):
            st["opened_dialog"] = dlg
            title = str(getattr(dlg, "name", "") or getattr(dlg, "title", "چت"))
            did_val = str(getattr(dlg, "id", ""))
            ent = getattr(dlg, "entity", None) or (int(did_val) if did_val.lstrip("-").isdigit() else did_val)

            st["selected_chat_id"] = did_val
            st["selected_chat_title"] = title
            st["selected_entity"] = ent
            target_box.value = did_val

            chats_area.controls = [ft.Text(f"در حال بارگذاری چت‌های اخیر «{title}»...", size=12, color="#38BDF8")]
            page.update()

            try:
                msgs = await c.get_messages(ent, limit=25)
                st["recent_msgs"] = list(msgs) if msgs else []
                render_chats_section()
            except Exception as ex:
                chats_area.controls = [
                    ft.Text(f"خطا در دریافت پیام‌ها: {ex}", size=12, color="#EF4444"),
                    ft.TextButton(content=ft.Text("🔙 بازگشت به لیست چت‌ها", color="#38BDF8"), on_click=lambda e: back_to_dialogs()),
                ]
                page.update()

        def back_to_dialogs():
            st["opened_dialog"] = None
            render_chats_section()

        def render_chats_section():
            chats_area.controls.clear()

            # حالت ۲: نمایش پیام‌های اخیر داخل پی‌وی یا گپ انتخاب شده
            if st["opened_dialog"] is not None:
                dlg = st["opened_dialog"]
                title = str(getattr(dlg, "name", "") or getattr(dlg, "title", "چت"))

                back_btn, _ = make_btn("🔙 بازگشت به لیست پی‌وی و گپ‌ها", lambda e: back_to_dialogs(), color="#38BDF8", height=36, kind="outlined")
                use_chat_btn, _ = make_btn("🚀 رفتن به توربو (بدون ریپلای روی پیام خاص)", lambda e: go_turbo_with_selection(None, ""), bgcolor="#0284C7", height=38)

                chats_area.controls.extend([
                    back_btn,
                    ft.Text(f"💬 چت‌های اخیر در: {title}", size=14, weight=ft.FontWeight.BOLD, color="#F8FAFC"),
                    ft.Text("روی هر پیام زیر کلیک کنید تا ریپلای روی همان پیام تنظیم شود:", size=12, color="#94A3B8"),
                    use_chat_btn,
                ])

                if not st["recent_msgs"]:
                    chats_area.controls.append(ft.Text("پیامی در این چت یافت نشد.", size=12, color="#64748B"))
                else:
                    for m in st["recent_msgs"]:
                        mid = getattr(m, "id", None)
                        if mid is None:
                            continue
                        m_text = str(getattr(m, "raw_text", "") or getattr(m, "text", "") or getattr(m, "message", "") or "[رسانه / استیکر / فایل]").strip()
                        if len(m_text) > 90:
                            m_text = m_text[:90] + "..."
                        is_out = bool(getattr(m, "out", False))
                        sender_obj = getattr(m, "sender", None)
                        sender_name = "شما" if is_out else (getattr(sender_obj, "first_name", "") or "کاربر")
                        is_selected = (st["selected_msg_id"] == mid)

                        def make_pick_msg(msg_id, preview_txt):
                            def _pick(e):
                                go_turbo_with_selection(msg_id, preview_txt)
                            return _pick

                        chats_area.controls.append(ft.Container(
                            bgcolor="#1E3A8A" if is_selected else "#1E293B",
                            border=ft.border.all(1, "#38BDF8" if is_selected else "#334155"),
                            padding=10,
                            border_radius=8,
                            on_click=make_pick_msg(mid, m_text),
                            content=ft.Column(spacing=4, controls=[
                                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                                    ft.Text(f"👤 {sender_name}", size=11, weight=ft.FontWeight.BOLD, color="#38BDF8"),
                                    ft.Text(f"ID: {mid} {'✅ انتخاب شده' if is_selected else '👈 کلیک برای ریپلای'}", size=11, color="#10B981" if is_selected else "#94A3B8"),
                                ]),
                                ft.Text(m_text, size=13, color="#F8FAFC"),
                            ]),
                        ))
                page.update()
                return

            # حالت ۱: نمایش لیست پی‌وی‌ها و گپ‌ها با فیلتر
            reload_btn, _ = make_btn("🔄 دریافت / بروزرسانی لیست پی‌وی و گپ‌ها", load_dialogs, bgcolor="#0284C7", height=40)
            chats_area.controls.extend([
                reload_btn,
                ft.Row(spacing=6, controls=[
                    pill("همه", st["chat_filter"] == "all", lambda e: set_chat_filter("all")),
                    pill("👤 فقط پی‌وی‌ها", st["chat_filter"] == "pv", lambda e: set_chat_filter("pv")),
                    pill("👥 فقط گپ‌ها", st["chat_filter"] == "group", lambda e: set_chat_filter("group")),
                ]),
            ])

            if not st["dialogs"]:
                chats_area.controls.append(ft.Text("برای مشاهده لیست پی‌وی‌ها و گپ‌های اکانت، دکمه بالا را بزنید.", size=12, color="#94A3B8"))
                page.update()
                return

            shown = 0
            for d in st["dialogs"]:
                is_grp = bool(getattr(d, "is_group", False) or getattr(d, "is_channel", False))
                if st["chat_filter"] == "pv" and is_grp:
                    continue
                if st["chat_filter"] == "group" and not is_grp:
                    continue

                shown += 1
                title = str(getattr(d, "name", "") or getattr(d, "title", "بدون نام"))
                did_val = str(getattr(d, "id", ""))
                badge = "👥 گپ / کانال" if is_grp else "👤 پی‌وی"

                def make_open_handler(dialog_obj):
                    async def _open(e):
                        await open_dialog_messages(dialog_obj)
                    return _open

                chats_area.controls.append(ft.Container(
                    bgcolor="#1E293B",
                    padding=12,
                    border_radius=8,
                    on_click=make_open_handler(d),
                    content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                        ft.Column(spacing=2, expand=True, controls=[
                            ft.Text(title, size=14, weight=ft.FontWeight.BOLD, color="#F8FAFC"),
                            ft.Text(f"{badge} | شناسه: {did_val}", size=11, color="#94A3B8"),
                        ]),
                        ft.Text("مشاهده پیام‌ها ◀", size=12, color="#38BDF8", weight=ft.FontWeight.W_600),
                    ]),
                ))

            if shown == 0:
                chats_area.controls.append(ft.Text("موردی در این دسته‌بندی یافت نشد.", size=12, color="#94A3B8"))
            page.update()

        def set_chat_filter(flt: str):
            st["chat_filter"] = flt
            render_chats_section()

        def go_turbo_with_selection(msg_id, preview_txt: str):
            st["selected_msg_id"] = msg_id
            st["selected_msg_preview"] = preview_txt
            st["ar_scope"] = "selected"
            st["tab"] = "turbo"
            if msg_id:
                log(f"پیام #{msg_id} در «{st['selected_chat_title']}» برای ریپلای انتخاب شد 🎯", "#10B981")
            else:
                log(f"چت «{st['selected_chat_title']}» انتخاب شد 🎯", "#38BDF8")
            render_body()

        def clear_selected_reply(e):
            st["selected_msg_id"] = None
            st["selected_msg_preview"] = ""
            render_body()

        # --- بخش پیام‌های مختلف (قاطی) با دکمه + تا سقف ۵۰ عدد ---
        def build_multi_msg_widget():
            boxes_col = ft.Column(spacing=8)
            count_now = len(st["multi_msgs"])

            for idx, val in enumerate(st["multi_msgs"]):
                def make_on_change(i):
                    def _chg(e):
                        st["multi_msgs"][i] = e.control.value
                    return _chg

                def make_remove(i):
                    def _rem(e):
                        if len(st["multi_msgs"]) > 1:
                            st["multi_msgs"].pop(i)
                            render_body()
                    return _rem

                row_items = [
                    ft.TextField(
                        label=f"پیام شماره {idx + 1}",
                        value=val,
                        on_change=make_on_change(idx),
                        bgcolor="#1E293B",
                        expand=True,
                    )
                ]
                if len(st["multi_msgs"]) > 1:
                    row_items.append(
                        ft.TextButton(content=ft.Text("✖", color="#EF4444", size=14), on_click=make_remove(idx))
                    )
                boxes_col.controls.append(ft.Row(spacing=4, controls=row_items))

            def add_new_msg_box(e):
                if len(st["multi_msgs"]) < 50:
                    st["multi_msgs"].append("")
                    render_body()

            can_add = count_now < 50
            plus_btn, _ = make_btn(
                f"➕ افزودن پیام جدید ({count_now}/50)" if can_add else "⛔ سقف ۵۰ پیام تکمیل شد (50/50)",
                add_new_msg_box if can_add else None,
                bgcolor="#0284C7" if can_add else "#334155",
                height=40,
            )
            plus_btn.disabled = not can_add

            return ft.Container(
                bgcolor="#0F172A",
                padding=10,
                border_radius=10,
                border=ft.border.all(1, "#1E293B"),
                content=ft.Column(spacing=8, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[
                    ft.Text("پیام‌های زیر به‌صورت قاطی و تصادفی ارسال می‌شوند:", size=12, color="#38BDF8"),
                    boxes_col,
                    plus_btn,
                ]),
            )

        async def logout(e):
            st["turbo"] = False
            try:
                await c.log_out()
            except Exception:
                try:
                    await c.disconnect()
                except Exception:
                    pass
            st["client"], st["listener_added"] = None, False
            base = os.path.basename(SESSION_PATH)
            for f in os.listdir(STORAGE_DIR):
                if f.startswith(base):
                    try:
                        os.remove(os.path.join(STORAGE_DIR, f))
                    except Exception:
                        pass
            show_phone("از حساب خارج شدید.")

        body_holder = ft.Column(spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        nav_row = ft.Row(spacing=4)

        def switch_tab(t_name: str):
            def _h(e):
                st["tab"] = t_name
                render_body()
            return _h

        def set_msg_mode(m_name: str):
            def _h(e):
                st["msg_mode"] = m_name
                render_body()
            return _h

        def set_ar_scope(sc: str):
            def _h(e):
                st["ar_scope"] = sc
                render_body()
            return _h

        def render_body():
            nav_row.controls = [
                pill("🚀 توربو", st["tab"] == "turbo", switch_tab("turbo")),
                pill("💬 چت و پیام", st["tab"] == "chats", switch_tab("chats")),
                pill("🤖 ریپلای خودکار", st["tab"] == "autoreply", switch_tab("autoreply")),
                pill("📜 گزارش", st["tab"] == "logs", switch_tab("logs")),
            ]
            body_holder.controls.clear()

            # بنر نمایش پیام انتخاب‌شده برای ریپلای (در صورت انتخاب)
            reply_banner = None
            if st["selected_msg_id"] is not None:
                reply_banner = ft.Container(
                    bgcolor="#172554",
                    border=ft.border.all(1, "#3B82F6"),
                    padding=10,
                    border_radius=8,
                    content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                        ft.Column(spacing=2, expand=True, controls=[
                            ft.Text(f"🎯 ریپلای فعال روی پیام #{st['selected_msg_id']} ({st['selected_chat_title']})", size=12, weight=ft.FontWeight.BOLD, color="#60A5FA"),
                            ft.Text(st["selected_msg_preview"], size=11, color="#CBD5E1"),
                        ]),
                        ft.TextButton(content=ft.Text("لغو ریپلای", size=11, color="#EF4444"), on_click=clear_selected_reply),
                    ]),
                )

            if st["tab"] == "turbo":
                pick_btn, _ = make_btn("💬 انتخاب پی‌وی / گپ و پیام برای ریپلای", switch_tab("chats"), color="#38BDF8", height=38, kind="outlined")
                controls = [
                    ft.Text("🚀 ارسال سریع (توربو و ریپلای)", size=15, weight=ft.FontWeight.BOLD, color="#38BDF8"),
                    pick_btn,
                    target_box,
                ]
                if reply_banner:
                    controls.append(reply_banner)

                controls.extend([
                    ft.Text("حالت متن ارسالی:", size=12, color="#94A3B8"),
                    ft.Row(spacing=6, controls=[
                        pill("تک پیام", st["msg_mode"] == "single", set_msg_mode("single")),
                        pill("پیام‌های مختلف / قاطی (+)", st["msg_mode"] == "multi", set_msg_mode("multi")),
                    ]),
                ])

                if st["msg_mode"] == "single":
                    controls.append(single_msg_box)
                else:
                    controls.append(build_multi_msg_widget())

                controls.extend([
                    ft.Row(spacing=8, controls=[cnt_box, dly_box]),
                    t_btn,
                    t_stat,
                ])
                body_holder.controls.append(ft.Container(bgcolor="#111827", padding=14, border_radius=12, content=ft.Column(
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=controls,
                )))

            elif st["tab"] == "chats":
                render_chats_section()
                body_holder.controls.append(ft.Container(bgcolor="#111827", padding=14, border_radius=12, content=ft.Column(
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("💬 بخش انتخاب چت و پیام جهت ریپلای", size=15, weight=ft.FontWeight.BOLD, color="#38BDF8"),
                        chats_area,
                    ],
                )))

            elif st["tab"] == "autoreply":
                save_btn, _ = make_btn("💾 ذخیره تنظیمات ریپلای خودکار", save_ar, bgcolor="#2563EB", height=44)
                ar_controls = [
                    ft.Text("🤖 ریپلای خودکار هوشمند", size=15, weight=ft.FontWeight.BOLD, color="#38BDF8"),
                    ar_sw,
                    ft.Text("محدوده پاسخ‌دهی خودکار:", size=12, color="#94A3B8"),
                    ft.Row(spacing=4, controls=[
                        pill("فقط پی‌وی", st["ar_scope"] == "pv", set_ar_scope("pv")),
                        pill("فقط گپ", st["ar_scope"] == "group", set_ar_scope("group")),
                        pill("پی‌وی و گپ", st["ar_scope"] == "all", set_ar_scope("all")),
                        pill("چت انتخابی", st["ar_scope"] == "selected", set_ar_scope("selected")),
                    ]),
                ]
                if reply_banner:
                    ar_controls.append(reply_banner)

                ar_controls.extend([
                    ft.Text("حالت پاسخ‌دهی:", size=12, color="#94A3B8"),
                    ft.Row(spacing=6, controls=[
                        pill("متن ثابت", st["msg_mode"] == "single", set_msg_mode("single")),
                        pill("پیام‌های مختلف / قاطی (+)", st["msg_mode"] == "multi", set_msg_mode("multi")),
                    ]),
                ])

                if st["msg_mode"] == "single":
                    ar_controls.append(ar_box)
                else:
                    ar_controls.append(build_multi_msg_widget())

                ar_controls.extend([cd_box, save_btn])
                body_holder.controls.append(ft.Container(bgcolor="#111827", padding=14, border_radius=12, content=ft.Column(
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=ar_controls,
                )))

            else:
                body_holder.controls.append(ft.Container(bgcolor="#0F172A", padding=14, border_radius=12, content=ft.Column(
                    spacing=8,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("📜 گزارش زنده عملکرد سلف‌بات", size=14, weight=ft.FontWeight.BOLD, color="#38BDF8"),
                        logs,
                    ],
                )))

            page.update()

        out_btn, _ = make_btn("خروج از اکانت", logout, color="#EF4444", kind="text")
        page.add(
            ft.Container(bgcolor="#111827", padding=12, border_radius=12, content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[ft.Text("⚡ V3X SELFBOT", size=18, weight=ft.FontWeight.BOLD, color="#38BDF8"), out_btn],
            )),
            nav_row,
            body_holder,
        )
        render_body()

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
