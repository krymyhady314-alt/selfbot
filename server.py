import asyncio
import inspect
import json
import os
import urllib.request
import uuid
from datetime import datetime
import flet as ft
from splusthon import events
from splusthon.client import SoroushClient

# ================= تنظیمات اصلی =================
API_ID = 1030400
API_HASH = "6edb16cf88714a4e9a805e928c39c937"

# تنظیمات سرور لایسنس
DEMO_MODE = True
LICENSE_SERVER_URL = "https://your-server.com/api/verify"

# مسیر ذخیره‌سازی امن فایل سشن
STORAGE_DIR = os.getenv("FLET_APP_STORAGE_DATA") or os.path.expanduser("~")
SESSION_PATH = os.path.join(STORAGE_DIR, "soroush_self_session")
DEVICE_ID_FILE = os.path.join(STORAGE_DIR, "device_id.txt")

# پالت رنگی دارک و نئونی
BG_DARK = "#0B0F17"
CARD_BG = "#131A26"
ACCENT = "#00E5FF"
SUCCESS = "#00E676"
DANGER = "#FF2A5F"
TEXT_MAIN = "#FFFFFF"
TEXT_MUTED = "#8B949E"


def get_device_id() -> str:
    if os.path.exists(DEVICE_ID_FILE):
        with open(DEVICE_ID_FILE, "r", encoding="utf-8") as f:
            saved = f.read().strip()
            if saved:
                return saved
    new_id = f"DEV-{uuid.uuid4().hex[:12].upper()}"
    with open(DEVICE_ID_FILE, "w", encoding="utf-8") as f:
        f.write(new_id)
    return new_id


def check_license_sync(license_key: str, device_id: str) -> dict:
    if DEMO_MODE:
        if len(license_key.strip()) >= 4:
            return {"valid": True, "days_left": 30, "msg": "حالت تست فعال است"}
        return {"valid": False, "days_left": 0, "msg": "کد لایسنس نامعتبر است"}

    try:
        payload = json.dumps({"key": license_key, "device_id": device_id}).encode("utf-8")
        req = urllib.request.Request(
            LICENSE_SERVER_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"valid": False, "days_left": 0, "msg": f"خطا در اتصال به سرور: {e}"}


def create_soroush_client() -> SoroushClient:
    sig = inspect.signature(SoroushClient.__init__)
    if len(sig.parameters) >= 4:
        return SoroushClient(SESSION_PATH, API_ID, API_HASH)
    return SoroushClient(SESSION_PATH)


def make_btn(label: str, bgcolor=None, color=None, on_click=None, expand=False, height=None, disabled=False):
    BtnCls = getattr(ft, "Button", None) or getattr(ft, "ElevatedButton")
    kwargs = {"on_click": on_click, "disabled": disabled}
    if bgcolor:
        kwargs["bgcolor"] = bgcolor
    if color:
        kwargs["color"] = color
    if expand:
        kwargs["expand"] = expand
    if height:
        kwargs["height"] = height
    try:
        return BtnCls(label, **kwargs)
    except TypeError:
        return BtnCls(content=ft.Text(label, color=color), **kwargs)


def make_border(width: int, color: str):
    if hasattr(ft, "border") and hasattr(ft.border, "all"):
        return ft.border.all(width, color)
    if hasattr(ft, "Border") and hasattr(ft.Border, "all"):
        return ft.Border.all(width, color)
    return None


async def main(page: ft.Page):
    page.title = "Soroush+ SelfBot Pro"
    page.bgcolor = BG_DARK
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 16
    page.scroll = ft.ScrollMode.AUTO

    device_id = get_device_id()
    client = create_soroush_client()

    state = {
        "is_running": False,
        "sent_count": 0,
        "license_key": "",
        "days_left": 0,
        "licensed": False,
        "listener_started": False,
        "my_id": None,
        "fetched_messages": [],
        "selected_reply_msg_id": None,
        "selected_reply_info": "",
    }

    def show_snack(text: str, color: str = ACCENT):
        sb = ft.SnackBar(
            content=ft.Text(
                text,
                color="#000000" if color in [ACCENT, SUCCESS] else "#FFFFFF",
                weight=ft.FontWeight.BOLD,
            ),
            bgcolor=color,
        )
        if hasattr(page, "show_dialog"):
            page.show_dialog(sb)
        elif hasattr(page, "open"):
            page.open(sb)
        else:
            page.overlay.append(sb)
            sb.open = True
            page.update()

    # ==========================================================
    # بخش ۳: داشبورد کنترل سلف‌بات
    # ==========================================================
    log_column = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=130)

    def add_log(msg: str, color: str = TEXT_MUTED):
        now = datetime.now().strftime("%H:%M:%S")
        log_column.controls.insert(
            0,
            ft.Text(f"[{now}] {msg}", size=12, color=color, selectable=True),
        )
        if len(log_column.controls) > 40:
            log_column.controls.pop()
        page.update()

    OptCls = getattr(ft, "DropdownOption", None) or ft.dropdown.Option

    messages_list_column = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, height=195)
    selected_reply_banner = ft.Text(
        "حالت ارسال: عادی (برای ریپلای، روی یکی از پیام‌های زیر کلیک کنید)",
        size=12,
        color=TEXT_MUTED,
        weight=ft.FontWeight.BOLD,
    )

    def clear_reply_selection(e=None):
        state["selected_reply_msg_id"] = None
        state["selected_reply_info"] = ""
        selected_reply_banner.value = "حالت ارسال: عادی (برای ریپلای، روی یکی از پیام‌های زیر کلیک کنید)"
        selected_reply_banner.color = TEXT_MUTED
        render_message_cards()
        page.update()

    def select_message_for_reply(msg_item: dict):
        state["selected_reply_msg_id"] = msg_item["id"]
        short_txt = msg_item["text"].replace("\n", " ")
        if len(short_txt) > 38:
            short_txt = short_txt[:38] + "..."
        state["selected_reply_info"] = f"{msg_item['sender']}: {short_txt}"
        selected_reply_banner.value = f"🎯 ریپلای روی پیام [{msg_item['sender']}]: «{short_txt}»"
        selected_reply_banner.color = SUCCESS
        render_message_cards()
        show_snack(f"پیام {msg_item['sender']} برای ریپلای انتخاب شد!", SUCCESS)

    def render_message_cards():
        messages_list_column.controls.clear()
        if not state["fetched_messages"]:
            messages_list_column.controls.append(
                ft.Text(
                    "پیامی از کاربران دیگر در این گفتگو پیدا نشد.",
                    size=12,
                    color=TEXT_MUTED,
                )
            )
            return

        for item in state["fetched_messages"]:
            is_selected = state["selected_reply_msg_id"] == item["id"]
            card = ft.Container(
                bgcolor="#122B22" if is_selected else BG_DARK,
                border=make_border(2 if is_selected else 1, SUCCESS if is_selected else "#263040"),
                border_radius=8,
                padding=10,
                ink=True,
                on_click=lambda e, m=item: select_message_for_reply(m),
                content=ft.Column(
                    spacing=3,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(
                                    f"👤 {item['sender']}",
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    color=SUCCESS if is_selected else ACCENT,
                                ),
                                ft.Text(
                                    "✅ انتخاب‌شده برای ریپلای" if is_selected else item["time"],
                                    size=11,
                                    color=SUCCESS if is_selected else TEXT_MUTED,
                                ),
                            ],
                        ),
                        ft.Text(
                            item["text"],
                            size=13,
                            color=TEXT_MAIN,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                ),
            )
            messages_list_column.controls.append(card)

    async def load_chat_messages(e=None):
        target = manual_chat_input.value.strip() or chat_dropdown.value
        if not target:
            return
        if str(target).lstrip("-").isdigit():
            target = int(target)

        messages_list_column.controls.clear()
        messages_list_column.controls.append(
            ft.Text("در حال دریافت پیام‌های این گفتگو...", size=12, color=ACCENT)
        )
        page.update()

        try:
            if state["my_id"] is None:
                try:
                    me = await client.get_me()
                    state["my_id"] = getattr(me, "id", None)
                except Exception:
                    pass

            raw_msgs = await client.get_messages(target, limit=35)
            filtered = []
            for m in raw_msgs:
                if not m:
                    continue
                if getattr(m, "out", False):
                    continue
                sender_id = getattr(m, "sender_id", None)
                if state["my_id"] is not None and sender_id == state["my_id"]:
                    continue

                txt = (
                    getattr(m, "text", None)
                    or getattr(m, "raw_text", None)
                    or getattr(m, "message", None)
                )
                if not txt:
                    if getattr(m, "media", None):
                        txt = "[فایل / رسانه]"
                    else:
                        continue

                sender_name = "کاربر"
                try:
                    sender = getattr(m, "sender", None)
                    if sender is None and hasattr(m, "get_sender"):
                        sender = await m.get_sender()
                    if sender:
                        fname = getattr(sender, "first_name", "") or ""
                        lname = getattr(sender, "last_name", "") or ""
                        title = getattr(sender, "title", "") or ""
                        uname = getattr(sender, "username", "") or ""
                        full = f"{fname} {lname}".strip() or title or uname
                        if full:
                            sender_name = full
                except Exception:
                    if sender_id:
                        sender_name = f"کاربر {sender_id}"

                msg_date = getattr(m, "date", None)
                time_str = msg_date.strftime("%H:%M") if msg_date else ""

                filtered.append(
                    {
                        "id": m.id,
                        "sender": sender_name,
                        "text": str(txt).strip(),
                        "time": time_str,
                    }
                )
                if len(filtered) >= 20:
                    break

            state["fetched_messages"] = filtered
            render_message_cards()
            add_log(f"{len(filtered)} پیام از اعضای چت بارگذاری شد.", SUCCESS)
        except Exception as ex:
            messages_list_column.controls.clear()
            messages_list_column.controls.append(
                ft.Text(f"خطا در دریافت پیام‌ها: {ex}", size=12, color=DANGER)
            )
            add_log(f"خطا در دریافت پیام‌ها: {ex}", DANGER)
        page.update()

    async def on_chat_dropdown_change(e):
        val = getattr(e.control, "value", None) or getattr(e, "data", None)
        if val:
            chat_dropdown.value = str(val)
        manual_chat_input.value = ""
        clear_reply_selection()
        await load_chat_messages()

    dd_sig = inspect.signature(ft.Dropdown.__init__).parameters
    dd_kwargs = {
        "label": "انتخاب پی‌وی / گروه هدف",
        "hint_text": "یک گفتگو را انتخاب کنید...",
        "border_color": ACCENT,
        "bgcolor": BG_DARK,
        "options": [],
    }
    if "on_select" in dd_sig:
        dd_kwargs["on_select"] = on_chat_dropdown_change
    elif "on_change" in dd_sig:
        dd_kwargs["on_change"] = on_chat_dropdown_change

    chat_dropdown = ft.Dropdown(**dd_kwargs)
    if "on_select" not in dd_sig and "on_change" not in dd_sig:
        if hasattr(chat_dropdown, "on_select"):
            chat_dropdown.on_select = on_chat_dropdown_change
        elif hasattr(chat_dropdown, "on_change"):
            chat_dropdown.on_change = on_chat_dropdown_change

    manual_chat_input = ft.TextField(
        label="آیدی عددی / یوزرنیم چت (اختیاری)",
        hint_text="مثال: @username یا آیدی عددی",
        border_color="#30363D",
        bgcolor=BG_DARK,
        expand=True,
    )

    message_input = ft.TextField(
        label="متن پیام جهت ارسال خودکار",
        multiline=True,
        min_lines=2,
        max_lines=4,
        border_color=ACCENT,
        bgcolor=BG_DARK,
    )

    delay_input = ft.TextField(
        label="فاصله ارسال (ثانیه)",
        value="5",
        hint_text="مثال: 0.5 یا 2 یا 5",
        keyboard_type=ft.KeyboardType.NUMBER,
        border_color=ACCENT,
        bgcolor=BG_DARK,
        expand=True,
    )

    burst_input = ft.TextField(
        label="تعداد پیام در هر نوبت",
        value="1",
        hint_text="مثال: 1 یا 3",
        keyboard_type=ft.KeyboardType.NUMBER,
        border_color=ACCENT,
        bgcolor=BG_DARK,
        expand=True,
    )

    count_input = ft.TextField(
        label="سقف کل ارسال (0 = نامحدود تا زمان توقف)",
        value="0",
        keyboard_type=ft.KeyboardType.NUMBER,
        border_color="#30363D",
        bgcolor=BG_DARK,
    )

    status_badge = ft.Text("وضعیت: متوقف", color=DANGER, weight=ft.FontWeight.BOLD)
    license_badge = ft.Text("اعتبار: -- روز", color=SUCCESS, size=12, weight=ft.FontWeight.BOLD)

    def get_delay_seconds() -> float:
        try:
            raw = (delay_input.value or "5").strip().replace("/", ".")
            val = float(raw)
            return max(0.1, val)
        except ValueError:
            return 5.0

    def get_burst_count() -> int:
        try:
            val = int((burst_input.value or "1").strip())
            return max(1, val)
        except ValueError:
            return 1

    async def send_soroush_msg(target, text: str, reply_to_id: int | None = None):
        if reply_to_id:
            try:
                await client.send_message(target, text, reply_to=reply_to_id)
            except TypeError:
                await client.send_message(target, text, reply_to_msg_id=reply_to_id)
        else:
            await client.send_message(target, text)

    async def load_dialogs(e=None):
        add_log("در حال دریافت لیست چت‌ها و گروه‌ها...", ACCENT)
        try:
            if state["my_id"] is None:
                try:
                    me = await client.get_me()
                    state["my_id"] = getattr(me, "id", None)
                except Exception:
                    pass

            dialogs = await client.get_dialogs(limit=25)
            opts = []
            for d in dialogs:
                title = getattr(d, "name", None) or getattr(d, "title", None) or str(d.id)
                opts.append(OptCls(key=str(d.id), text=f"{title} ({d.id})"))
            chat_dropdown.options = opts
            if opts and not chat_dropdown.value:
                chat_dropdown.value = opts[0].key
            add_log(f"{len(opts)} گفتگو بارگذاری شد.", SUCCESS)
            page.update()
            if chat_dropdown.value:
                await load_chat_messages()
        except Exception as ex:
            add_log(f"خطا در دریافت چت‌ها: {ex}", DANGER)
            page.update()

    async def sender_loop():
        target = manual_chat_input.value.strip() or chat_dropdown.value
        if target and str(target).lstrip("-").isdigit():
            target = int(target)

        reply_to_id = state["selected_reply_msg_id"]
        msg_text = message_input.value.strip()
        try:
            max_count = int((count_input.value or "0").strip())
        except ValueError:
            max_count = 0

        state["sent_count"] = 0
        status_badge.value = (
            f"وضعیت: ریپلای روی ({state['selected_reply_info']})"
            if reply_to_id
            else "وضعیت: در حال ارسال عادی..."
        )
        status_badge.color = SUCCESS
        start_btn.disabled = True
        stop_btn.disabled = False
        page.update()

        current_delay = get_delay_seconds()
        mode_txt = f"ریپلای به {state['selected_reply_info']}" if reply_to_id else "ارسال عادی"
        add_log(f"شروع {mode_txt} | هر {current_delay} ثانیه", SUCCESS)

        while state["is_running"]:
            burst = get_burst_count()
            active_reply_id = state["selected_reply_msg_id"]
            for _ in range(burst):
                if not state["is_running"]:
                    break
                try:
                    await send_soroush_msg(target, msg_text, reply_to_id=active_reply_id)
                    state["sent_count"] += 1
                    add_log(f"ارسال شد (#{state['sent_count']})", TEXT_MAIN)

                    if max_count > 0 and state["sent_count"] >= max_count:
                        add_log("تعداد ارسال مشخص‌شده به پایان رسید.", ACCENT)
                        state["is_running"] = False
                        break

                    if not DEMO_MODE and state["sent_count"] % 20 == 0:
                        res = await asyncio.to_thread(
                            check_license_sync, state["license_key"], device_id
                        )
                        if not res.get("valid"):
                            add_log("اعتبار لایسنس شما به پایان رسید!", DANGER)
                            state["is_running"] = False
                            break

                except Exception as ex:
                    add_log(f"خطا در ارسال: {ex}", DANGER)
                    break

            if not state["is_running"]:
                break

            delay_sec = get_delay_seconds()
            if delay_sec <= 1.0:
                await asyncio.sleep(delay_sec)
            else:
                whole_secs = int(delay_sec)
                rem_sec = delay_sec - whole_secs
                for _ in range(whole_secs):
                    if not state["is_running"]:
                        break
                    await asyncio.sleep(1)
                if state["is_running"] and rem_sec > 0:
                    await asyncio.sleep(rem_sec)

        state["is_running"] = False
        status_badge.value = "وضعیت: متوقف"
        status_badge.color = DANGER
        start_btn.disabled = False
        stop_btn.disabled = True
        page.update()

    def register_chat_listener():
        if state["listener_started"]:
            return
        state["listener_started"] = True

        @client.on(events.NewMessage(outgoing=True))
        async def on_outgoing_cmd(event):
            if not state["licensed"]:
                return

            text = (getattr(event, "raw_text", None) or "").strip()
            if not text:
                return

            if text.lower() == "!stop":
                try:
                    await event.delete()
                except Exception:
                    pass
                if state["is_running"]:
                    state["is_running"] = False
                    add_log("توقف از طریق دستور !stop در چت انجام شد.", DANGER)
                return

            if text.lower().startswith("!r ") or text.lower().startswith("!reply "):
                parts = text.split(" ", 2)
                if len(parts) < 2:
                    return

                target_reply_id = getattr(event, "reply_to_msg_id", None)
                if not target_reply_id and getattr(event, "is_reply", False):
                    try:
                        replied_msg = await event.get_reply_message()
                        if replied_msg:
                            target_reply_id = replied_msg.id
                    except Exception:
                        pass

                try:
                    await event.delete()
                except Exception:
                    pass

                raw_delay = parts[1].strip().replace("/", ".")
                try:
                    parsed_delay = max(0.1, float(raw_delay))
                    custom_text = parts[2].strip() if len(parts) >= 3 else ""
                except ValueError:
                    parsed_delay = get_delay_seconds()
                    custom_text = " ".join(parts[1:]).strip()

                final_text = custom_text or message_input.value.strip()
                if not final_text:
                    add_log("خطا: متنی برای ارسال وارد نشده است.", DANGER)
                    return

                if state["is_running"]:
                    state["is_running"] = False
                    await asyncio.sleep(0.3)

                manual_chat_input.value = str(event.chat_id)
                state["selected_reply_msg_id"] = target_reply_id
                state["selected_reply_info"] = f"پیام #{target_reply_id}" if target_reply_id else ""
                delay_input.value = str(parsed_delay)
                message_input.value = final_text
                page.update()

                state["is_running"] = True
                asyncio.create_task(sender_loop())

    def on_start_click(e):
        target = manual_chat_input.value.strip() or chat_dropdown.value
        if not target:
            show_snack("لطفاً یک پی‌وی یا گروه انتخاب کنید!", DANGER)
            return
        if not message_input.value.strip():
            show_snack("متن پیام نمی‌تواند خالی باشد!", DANGER)
            return

        state["is_running"] = True
        asyncio.create_task(sender_loop())

    def on_stop_click(e):
        state["is_running"] = False
        add_log("دستور توقف صادر شد...", DANGER)

    start_btn = make_btn(
        "شروع ارسال",
        bgcolor=SUCCESS,
        color="#000000",
        expand=True,
        height=48,
        on_click=on_start_click,
    )

    stop_btn = make_btn(
        "توقف",
        bgcolor=DANGER,
        color="#FFFFFF",
        expand=True,
        height=48,
        disabled=True,
        on_click=on_stop_click,
    )

    refresh_chats_btn = make_btn("بروزرسانی چت‌ها", bgcolor="#1F2937", color=ACCENT, on_click=load_dialogs)
    fetch_msgs_btn = make_btn("دریافت پیام‌ها", bgcolor="#1F2937", color=ACCENT, on_click=load_chat_messages)
    clear_reply_btn = make_btn("لغو ریپلای", bgcolor="#2B1820", color=DANGER, on_click=clear_reply_selection)

    dashboard_view = ft.Column(
        visible=False,
        spacing=12,
        controls=[
            ft.Container(
                bgcolor=CARD_BG,
                padding=14,
                border_radius=12,
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            spacing=2,
                            controls=[
                                ft.Text("پنل سلف‌بات سروش‌پلاس", size=18, weight=ft.FontWeight.BOLD, color=ACCENT),
                                status_badge,
                            ],
                        ),
                        license_badge,
                    ],
                ),
            ),
            ft.Container(
                bgcolor=CARD_BG,
                padding=14,
                border_radius=12,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Container(content=chat_dropdown, expand=True),
                                refresh_chats_btn,
                            ]
                        ),
                        ft.Row(
                            controls=[
                                manual_chat_input,
                                fetch_msgs_btn,
                            ],
                            spacing=8,
                        ),
                        ft.Divider(height=1, color="#30363D"),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text("پیام‌های اعضای گفتگو (برای ریپلای کلیک کنید):", size=12, color=ACCENT, weight=ft.FontWeight.BOLD),
                                clear_reply_btn,
                            ],
                        ),
                        selected_reply_banner,
                        ft.Container(
                            bgcolor="#080B11",
                            padding=8,
                            border_radius=10,
                            border=make_border(1, "#263040"),
                            content=messages_list_column,
                        ),
                        message_input,
                        ft.Row(controls=[delay_input, burst_input], spacing=10),
                        count_input,
                        ft.Row(controls=[start_btn, stop_btn], spacing=10),
                    ],
                ),
            ),
            ft.Container(
                bgcolor=CARD_BG,
                padding=12,
                border_radius=12,
                content=ft.Column(
                    spacing=6,
                    controls=[
                        ft.Text("گزارش عملکرد زنده:", size=13, weight=ft.FontWeight.BOLD, color=ACCENT),
                        ft.Divider(height=1, color="#30363D"),
                        log_column,
                    ],
                ),
            ),
        ],
    )

    # ==========================================================
    # بخش ۲: صفحه ورود به اکانت سروش‌پلاس
    # ==========================================================
    phone_input = ft.TextField(
        label="شماره موبایل سروش‌پلاس",
        hint_text="09123456789",
        keyboard_type=ft.KeyboardType.PHONE,
        border_color=ACCENT,
        bgcolor=BG_DARK,
    )

    code_input = ft.TextField(
        label="کد تایید ارسال‌شده",
        hint_text="کد ۵ یا ۶ رقمی",
        keyboard_type=ft.KeyboardType.NUMBER,
        border_color=SUCCESS,
        bgcolor=BG_DARK,
        visible=False,
    )

    verify_code_btn = make_btn(
        "تایید کد و ورود به پنل",
        bgcolor=SUCCESS,
        color="#000000",
        height=46,
    )
    verify_code_btn.visible = False

    send_code_btn = make_btn(
        "ارسال کد تایید",
        bgcolor=ACCENT,
        color="#000000",
        height=46,
    )

    async def on_send_code(e):
        phone = phone_input.value.strip()
        if not phone:
            show_snack("شماره تلفن را وارد کنید!", DANGER)
            return
        send_code_btn.disabled = True
        page.update()
        try:
            if not client.is_connected():
                await client.connect()
            await client.send_code_request(phone)
            code_input.visible = True
            verify_code_btn.visible = True
            show_snack("کد تایید ارسال شد (پیامک یا داخل سروش را چک کنید).", SUCCESS)
        except Exception as ex:
            show_snack(f"خطا در ارسال کد: {ex}", DANGER)
        finally:
            send_code_btn.disabled = False
            page.update()

    async def on_verify_code(e):
        phone = phone_input.value.strip()
        code = code_input.value.strip()
        if not code:
            show_snack("کد تایید را وارد کنید!", DANGER)
            return
        verify_code_btn.disabled = True
        page.update()
        try:
            await client.sign_in(phone, code)
            login_view.visible = False
            dashboard_view.visible = True
            register_chat_listener()
            show_snack("با موفقیت وارد اکانت شدید!", SUCCESS)
            await load_dialogs()
        except Exception as ex:
            show_snack(f"خطا در تایید کد: {ex}", DANGER)
        finally:
            verify_code_btn.disabled = False
            page.update()

    send_code_btn.on_click = on_send_code
    verify_code_btn.on_click = on_verify_code

    login_view = ft.Container(
        visible=False,
        bgcolor=CARD_BG,
        padding=20,
        border_radius=14,
        content=ft.Column(
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Text("اتصال به اکانت سروش‌پلاس", size=20, weight=ft.FontWeight.BOLD, color=ACCENT),
                ft.Text("شماره خود را وارد کنید تا کد تایید ارسال شود:", size=13, color=TEXT_MUTED),
                phone_input,
                send_code_btn,
                code_input,
                verify_code_btn,
            ],
        ),
    )

    # ==========================================================
    # بخش ۱: صفحه قفل لایسنس
    # ==========================================================
    license_input = ft.TextField(
        label="کد لایسنس (License Key)",
        hint_text="مثال تست: TEST-1234",
        border_color=ACCENT,
        bgcolor=BG_DARK,
    )

    async def copy_device_id(e):
        try:
            if hasattr(ft, "Clipboard"):
                res = ft.Clipboard().set(device_id)
                if inspect.isawaitable(res):
                    await res
            elif hasattr(page, "set_clipboard"):
                res = page.set_clipboard(device_id)
                if inspect.isawaitable(res):
                    await res
        except Exception:
            pass
        show_snack("شناسه دستگاه کپی شد!", SUCCESS)

    activate_btn = make_btn(
        "بررسی و فعال‌سازی لایسنس",
        bgcolor=ACCENT,
        color="#000000",
        height=48,
    )

    async def on_activate_license(e):
        key = license_input.value.strip()
        if not key:
            show_snack("لطفاً کد لایسنس را وارد کنید!", DANGER)
            return

        activate_btn.disabled = True
        page.update()

        res = await asyncio.to_thread(check_license_sync, key, device_id)
        activate_btn.disabled = False

        if res.get("valid"):
            state["licensed"] = True
            state["license_key"] = key
            state["days_left"] = res.get("days_left", 0)
            license_badge.value = f"اعتبار: {state['days_left']} روز"
            license_view.visible = False

            try:
                if not client.is_connected():
                    await client.connect()
                if await client.is_user_authorized():
                    dashboard_view.visible = True
                    register_chat_listener()
                    show_snack("لایسنس تایید شد!", SUCCESS)
                    await load_dialogs()
                else:
                    login_view.visible = True
            except Exception:
                login_view.visible = True
        else:
            show_snack(res.get("msg", "لایسنس نامعتبر است!"), DANGER)

        page.update()

    activate_btn.on_click = on_activate_license

    copy_btn = make_btn("کپی", bgcolor="#1F2937", color=ACCENT, on_click=copy_device_id)

    license_view = ft.Container(
        visible=True,
        bgcolor=CARD_BG,
        padding=20,
        border_radius=14,
        content=ft.Column(
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Text("فعال‌سازی اشتراک", size=22, weight=ft.FontWeight.BOLD, color=ACCENT),
                ft.Text(
                    "برای استفاده از اپلیکیشن، کد لایسنس خود را وارد کنید. این لایسنس روی دستگاه شما قفل می‌شود.",
                    size=13,
                    color=TEXT_MUTED,
                ),
                ft.Container(
                    bgcolor=BG_DARK,
                    padding=10,
                    border_radius=8,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(f"شناسه گوشی: {device_id}", size=12, color=ACCENT),
                            copy_btn,
                        ],
                    ),
                ),
                license_input,
                activate_btn,
            ],
        ),
    )

    page.add(license_view, login_view, dashboard_view)


if __name__ == "__main__":
    if hasattr(ft, "run"):
        ft.run(main)
    else:
        ft.app(target=main)
