"""
Telegram avto-xabar boti (o'z akkauntingiz uchun).

Ishlashi:
  - Har kuni SEND_TIME (masalan 01:00) da TARGET ga MESSAGE yuboradi
    (IMAGE berilgan bo'lsa — rasm, tagida MESSAGE matni bilan).
  - Xabar o'qilishi bilan darhol sizga (Saved Messages) bildirishnoma keladi
    (va DESKTOP_NOTIFY=true bo'lsa desktop bildirishnoma ham).
  - Agar CLEANUP_TIME (masalan 05:00) gacha o'qilmasa, xabar ikkala tomondan
    o'chiriladi (revoke) va sizga "o'qilmadi, o'chirildi" xabari keladi.

Bu sizning O'Z akkauntingiz avtomatlashtiruvi (userbot). Telethon MTProto orqali.
"""

import asyncio
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from telethon import TelegramClient, events, functions

BASE_DIR = Path(__file__).parent
STATE_FILE = BASE_DIR / "state.json"

load_dotenv(BASE_DIR / ".env")

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
PHONE = os.environ["PHONE"]
TARGET = os.environ["TARGET"]
MESSAGE = os.environ.get("MESSAGE", "Xayrli tun ❤️")
IMAGE = os.environ.get("IMAGE", "").strip()
SEND_TIME = os.environ.get("SEND_TIME", "01:00")
CLEANUP_TIME = os.environ.get("CLEANUP_TIME", "05:00")
TIMEZONE = os.environ.get("TIMEZONE", "Asia/Tashkent")
DESKTOP_NOTIFY = os.environ.get("DESKTOP_NOTIFY", "false").lower() == "true"

TZ = ZoneInfo(TIMEZONE)

client = TelegramClient(str(BASE_DIR / "userbot.session"), API_ID, API_HASH)


# ---------- holatni saqlash (kunlik yuborilgan xabar) ----------
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def desktop_notify(text: str) -> None:
    if not DESKTOP_NOTIFY:
        return
    try:
        subprocess.run(["notify-send", "Telegram", text], check=False)
    except FileNotFoundError:
        pass  # notify-send o'rnatilmagan


async def notify_me(text: str) -> None:
    """O'zingizga (Saved Messages) xabar yuboradi."""
    await client.send_message("me", text)
    desktop_notify(text)


# ---------- o'qilganini tekshirish ----------
async def is_read(peer, message_id: int) -> bool:
    """Yuborilgan xabar o'qilganmi? read_outbox_max_id orqali tekshiradi."""
    result = await client(functions.messages.GetPeerDialogsRequest(peers=[peer]))
    for dialog in result.dialogs:
        if dialog.read_outbox_max_id >= message_id:
            return True
    return False


# ---------- vazifalar ----------
async def send_job() -> None:
    try:
        entity = await client.get_entity(TARGET)
        if IMAGE:
            image_path = Path(IMAGE)
            if not image_path.is_absolute():
                image_path = BASE_DIR / image_path
            # Rasm + tagida MESSAGE matni (caption)
            sent = await client.send_file(entity, image_path, caption=MESSAGE)
        else:
            sent = await client.send_message(entity, MESSAGE)
        state = load_state()
        state["message_id"] = sent.id
        state["peer_id"] = entity.id
        state["sent_at"] = datetime.now(TZ).isoformat()
        state["read"] = False
        state["notified"] = False
        save_state(state)
        print(f"[{datetime.now(TZ):%H:%M}] Xabar yuborildi (id={sent.id})")
    except Exception as e:  # noqa: BLE001
        print(f"Yuborishda xato: {e}")
        await notify_me(f"⚠️ Xabar yuborilmadi: {e}")


async def cleanup_job() -> None:
    state = load_state()
    msg_id = state.get("message_id")
    if not msg_id:
        return
    try:
        entity = await client.get_entity(TARGET)
        if await is_read(entity, msg_id):
            # o'qilgan -> o'chirmaymiz (agar hali bildirmagan bo'lsak, bildiramiz)
            if not state.get("notified"):
                await notify_me("✅ Xabaringiz o'qildi.")
                state["read"] = True
                state["notified"] = True
                save_state(state)
            print("O'qilgan — o'chirilmadi.")
        else:
            # o'qilmagan -> qarshi tomonda xabarlarni revoke qilamiz (iz qolmaydi)
            # va o'z tarafimizda dialogni butunlay o'chiramiz.
            await client.delete_dialog(entity, revoke=True)
            # Bildirishnoma FAQAT sizga (Saved Messages) — qarshi tomonga tegmaydi.
            await notify_me("🗑 Xabar o'qilmadi — chat tozalandi (qarshi tomonda iz qolmadi).")
            print("O'qilmadi — dialog o'chirildi, qarshi tomon revoke qilindi.")
        state["message_id"] = None
        save_state(state)
    except Exception as e:  # noqa: BLE001
        print(f"Tozalashda xato: {e}")
        await notify_me(f"⚠️ Tozalashda xato: {e}")


# ---------- o'qilganda darhol bildirish ----------
@client.on(events.MessageRead(inbox=False))  # inbox=False -> biz yuborgan xabarlar o'qilishi
async def on_read(event: events.MessageRead.Event) -> None:
    state = load_state()
    msg_id = state.get("message_id")
    if not msg_id or state.get("notified"):
        return
    # Faqat TARGET chatidagi o'qishni hisoblaymiz (boshqa chatlar -> yolg'on "o'qildi")
    if event.chat_id != state.get("peer_id"):
        return
    if event.max_id >= msg_id:
        await notify_me("✅ Xabaringiz hozirgina o'qildi.")
        state["read"] = True
        state["notified"] = True
        save_state(state)
        print("O'qildi — bildirishnoma yuborildi.")


def parse_hhmm(value: str) -> tuple[int, int]:
    hh, mm = value.split(":")
    return int(hh), int(mm)


async def main() -> None:
    await client.start(phone=PHONE)
    me = await client.get_me()
    print(f"Kirdingiz: {me.first_name} (@{me.username})")

    scheduler = AsyncIOScheduler(timezone=TZ)
    sh, sm = parse_hhmm(SEND_TIME)
    ch, cm = parse_hhmm(CLEANUP_TIME)
    scheduler.add_job(send_job, CronTrigger(hour=sh, minute=sm))
    scheduler.add_job(cleanup_job, CronTrigger(hour=ch, minute=cm))
    scheduler.start()

    print(f"Rejalashtirildi: yuborish {SEND_TIME}, tozalash {CLEANUP_TIME} ({TIMEZONE})")
    print("Ishlayapti... to'xtatish uchun Ctrl+C.")
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTo'xtatildi.")
