# Yarnmori 🧶

A **working full-stack crochet store** with a minimal cream-and-sage storefront, real product photos, shopping bag, checkout order database, and password-protected owner dashboard.

## What works

- Responsive homepage featuring 9 products from the provided crochet photos
- Product pages, category filters, live search, persistent browser shopping bag
- Checkout with server-side price verification and a **real SQLite order database**
- Secure random order confirmation links
- Owner sign-in at `/admin/login`
- Orders dashboard with customer address, items, custom instructions and status updates
- Create, edit, show/hide products, update prices and upload product photos
- Edit shipping charges, Instagram link, WhatsApp number, banner message and production time
- India INR pricing, SEO metadata, shipping/returns/privacy pages, `robots.txt`, `sitemap.xml`

**Important payment detail:** This site takes **order requests**, not card or UPI payments. The buyer enters their details and their order is genuinely saved. You must contact them to confirm courier availability, exact turnaround and payment. No live payment gateway is represented as connected. To accept instant online payments, integrate a payment provider such as Razorpay later using your verified business account and API credentials.

## Run on your computer

1. Install Python 3.11+.
2. Extract this folder, then open a terminal in the `yarnmori_site` folder.
3. Create a virtual environment (optional, recommended):

   ```bash
   python -m venv .venv
   # macOS/Linux
   source .venv/bin/activate
   # Windows PowerShell
   # .venv\Scripts\Activate.ps1
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Create a `.env` file by copying `.env.example` and **replace `SECRET_KEY` and `ADMIN_PASSWORD` with your own strong secret values**. Example secret generation:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

6. Start the server:

   ```bash
   uvicorn app:app --reload --port 8000
   ```

7. Open **http://127.0.0.1:8000**. The owner login is **http://127.0.0.1:8000/admin/login**. Use the username and password from your `.env` file.

The database will be created automatically under `data/yarnmori.sqlite3` when the app starts. The first-run product catalog seeds itself from the included original user photos. After that you control everything through the dashboard.

## First things to configure as the owner

1. Visit `/admin/login`, sign in and open **Store settings**.
2. Add your WhatsApp Business number with India country code (`91`), Instagram URL and contact email if you have one.
3. Confirm your shipping fee, free-shipping threshold, and realistic making time.
4. Visit **Products** and verify all starter prices and descriptions. These are **illustrative prices**, not prices you have approved.
5. Place a test order from the shop, check it in the dashboard, and mark it Confirmed, Making or Shipped.
6. Publish the URL on your Instagram bio **only after** the shipping/contact information is accurate and you have successfully tested the full flow.

## Deploy to Railway with persistent orders

1. Create a private GitHub repository and upload these project files (do **not** upload `.env` or your local `data` folder).
2. On [Railway](https://railway.com/), create a project from the GitHub repository. Railway can build the included `Dockerfile`.
3. Attach a **persistent volume** at the mount path `/data`. This matters because SQLite orders and uploaded product images must survive redeployments.
4. Add these service environment variables in Railway:

   | Variable | Value |
   |---|---|
   | `DATA_DIR` | `/data` |
   | `PRODUCTION` | `1` |
   | `SECRET_KEY` | Your unique secret, at least 32 characters |
   | `ADMIN_USER` | An owner login name |
   | `ADMIN_PASSWORD` | Your unique private password, at least 12 characters |

   You do not need to manually set `PORT` if Railway injects it.

5. Deploy the service and configure a public HTTPS domain from Railway settings.
6. Visit `/health` and confirm it reports `{"status":"ok","site":"Yarnmori"}`; then load the storefront and `/admin/login`.
7. Upload a test product image and place a test order. Redeploy once to confirm the data remains available on the mounted volume.
8. Enable volume backups and protect your Railway/GitHub account with 2FA. Do not publicly share admin credentials.

Railway service/volume availability and pricing can change. Review their current docs: https://docs.railway.com/volumes

> **Persistence warning:** Without the `/data` volume, the app can start but orders and new uploaded images could disappear on redeployment. A domain/hosting account is not included in this ZIP.

## Simple architecture

- **Frontend:** Jinja2-rendered HTML templates, custom responsive CSS, vanilla JavaScript cart/filter UI
- **Backend:** FastAPI server with protected admin endpoints
- **Database:** SQLite on local or persistent volume
- **Images:** 9 optimized WebP photos from your provided handmade products + owner uploads to persistent volume
- **No third-party cookies, external analytics, or tracking scripts** (fonts optionally load from Google Fonts)

The SQLite approach is appropriate for a small launch. For a larger high-volume business, move to managed PostgreSQL + object storage, use a transactional email/WhatsApp messaging service, add delivery integrations and a verified checkout gateway, and set up monitoring.

## Admin and checkout safety

- HTTPS-only session cookies when `PRODUCTION=1`, 12-hour signed owner session
- CSRF protection on checkout, login and admin forms
- Server-derived cart prices so customers cannot submit lower amounts
- Input validation for Indian phone and PIN code, order quantity limits and a basic abuse throttle
- Product photo type/size check, random file names and protected admin upload route
- Order detail URLs are random bearer tokens and are excluded from search indexing

For public launch, restrict access to the owner dashboard, monitor for suspicious orders, keep customer details private and set up regular backups. For higher traffic, use a proper edge rate limiter and improve privacy/retention workflows.

## Test

With `pytest` and `httpx` installed in the development environment:

```bash
pytest -q
```

Tests cover public pages, order persistence, server-side prices, input and CSRF validation, owner login, status changes, settings and product edits.

## Notes

- These starter prices, making-time estimates, descriptions, shipping policy and image composition are examples to be approved or edited by the owner.
- Keychain parts or bead eyes can be unsafe for infants. Do not market these products as baby toys without the appropriate safety checks.
- A true live-payment checkout requires your verified payment provider account and integration; **do not ask buyers to pay through an unverified link**.
