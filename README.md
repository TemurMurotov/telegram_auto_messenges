# Telegram avto-xabar boti

O'z Telegram akkauntingiz uchun avtomatlashtirish:

- Har kuni **01:00** da tanlangan insonga rasm va uning tagida xabar yuboradi
  (`IMAGE` bo'sh bo'lsa — faqat matn).
- Xabar **o'qilishi bilan** sizga bildirishnoma keladi (Saved Messages + desktop).
- Agar **05:00** gacha o'qilmasa, xabar ikkala tomondan o'chiriladi (tozalanadi).

Barcha vaqtlar `.env` faylida sozlanadi.

## 1. API kalitlarini olish

1. https://my.telegram.org saytiga o'z raqamingiz bilan kiring.
2. **API development tools** → yangi app yarating.
3. `api_id` va `api_hash` ni oling.

## 2. O'rnatish

```bash
cd telegram-auto
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Sozlash

```bash
cp .env.example .env
```

`.env` faylini oching va to'ldiring: `API_ID`, `API_HASH`, `PHONE`, `TARGET`
(kimga), `MESSAGE` (matn), `IMAGE` (rasm fayli), vaqtlar va `TIMEZONE`.

## 4. Ishga tushirish

```bash
python main.py
```

Birinchi ishga tushirishda Telegram sizga kod yuboradi — uni kiritasiz
(2FA parolingiz bo'lsa, uni ham). Keyin sessiya `userbot.session` faylida
saqlanadi, qayta so'ramaydi.

Dastur ochiq turishi kerak (kompyuter yoki server yoqiq bo'lsin).
Doim ishlashi uchun `systemd`, `tmux` yoki `screen` ishlatish mumkin.

## Muhim eslatmalar

- Bu **sizning o'z akkauntingiz** avtomatlashtiruvi. Faqat o'zingizga tegishli
  akkaunt bilan foydalaning.
- `.session` va `.env` fayllarini **hech kimga bermang** — ular akkauntingizga
  to'liq kirish beradi. `.gitignore` allaqachon ularni himoya qiladi.
- "O'qildi" holati faqat qarshi tomon o'qishni yoqib qo'ygan bo'lsa aniqlanadi.
