# GifteWin RANDOM — Haunted Edition

Telegram Mini App interface and aiogram 3 bot for giveaway management. The web interface is a **static client-side prototype**: user balances, tasks, wheel results, chat, promo codes and demo giveaways are stored in the browser's `localStorage`. They are not real Telegram Stars and are not synchronized with the SQLite bot database. Do not use browser-side balances or the wheel as proof of payment or as a production prize draw.

## Included

- Responsive dark Halloween interface with animated loader and reduced-motion support.
- Browser-side demo screens for giveaways, tasks, profile, wheel and chat.
- Telegram WebApp initialization when opened inside Telegram.
- aiogram 3 bot with SQLite persistence, referral tracking, giveaway participation and scheduled winner selection.
- Admin bot commands restricted by Telegram numeric IDs from `ADMIN_IDS`.

## Run the bot

Python 3.10+ is recommended.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set a real BotFather token and numeric Telegram admin IDs. Never commit `.env` or share your token. Then run:

```bash
python -m bot.main
```

Bot commands: `/start`, `/menu`, `/help`, `/channel`; admins can use `/stats` and `/addballs USER_ID AMOUNT`.

## Publish the Mini App

Upload `webapp/index.html` to GitHub Pages or another HTTPS static host and configure its URL in BotFather's Web App / Menu Button settings. Set the correct channel URL in the HTML if your channel is not `@GifteWin`.

## Production limitations — read before launch

The static Mini App currently does **not** call a backend API. Browser storage can be edited by the user, and client-side wheel outcomes, Stars-like points, task completion, promo codes and admin UI are not secure or authoritative. The Telegram `initDataUnsafe` object is used only for display; it is not server-validated. The bot database and Mini App local demo data are separate systems.

Before handling real users, payments, Telegram Stars, withdrawals, or valuable prizes, implement an authenticated HTTPS API, validate Telegram `initData` on the server, move all balances and draw logic to the server, enforce admin permissions server-side, and use Telegram Stars payment flows. Do not put bot tokens or admin passwords in frontend code.

## Configuration

See `.env.example`. Times are entered in the configured timezone (`Europe/Kyiv` by default) and stored as UTC by the bot.
