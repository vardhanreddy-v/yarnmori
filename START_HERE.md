# Yarnmori: run the complete shop

Requires Python 3.12 or newer. On Mac, you can run `bash start.command` from Terminal in this folder for guided setup and startup. Alternatively, use the commands below.

See BRAND_AND_VALIDATION.md for the colours, fonts and test results.

Open a terminal in this folder.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python setup.py
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

On Windows use `py -m venv .venv` and `.venv\Scripts\activate` instead of the first two lines.

Visit http://localhost:8000. Owner login: http://localhost:8000/admin, username `owner`, with the password you chose. Keep the terminal running.

## Try a complete order

1. Sign in as owner. Open Settings and enter your real WhatsApp number including 91, contact email, shipping fee and production time.
2. Review Products. Update prices and upload your own product photos.
3. In a private browser window, add a product to your bag and open checkout.
4. Enter test delivery details and submit. You receive a saved order reference and private receipt URL.
5. Open the owner dashboard. The order and its items appear there. Change its status from New through Making, Shipped and Delivered. Reload the private receipt URL to see the current status.
6. Restart the server. The order remains in SQLite under `data/`.

Checkout prices are calculated by the backend. Repeated submissions from the same checkout token reuse the saved order. Network and validation errors appear on the checkout page without discarding the filled form. Three.js is bundled locally and draws a decorative rotating yarn ball; real product photos remain visible if WebGL is unavailable or reduced motion is requested.

## What payment means here

This working flow collects order requests. It does not charge cards, verify UPI payments, send automatic email, buy shipping labels, or mark payments as paid. Owner confirmation and payment instructions are manual, with a WhatsApp link when configured. For automatic online payments, connect a merchant payment provider using your own credentials and verified server-side webhooks before accepting money.

## Hosting

This is a Python/FastAPI application. Use a Python host or Docker host with a persistent disk. It cannot run on static-only hosting. Run `python setup.py` first, then `docker compose up --build -d` for a local Docker installation.

For a public deployment: set PRODUCTION=true; use HTTPS through your host or reverse proxy; keep SECRET_KEY and ADMIN_PASSWORD private; bind DATA_DIR to persistent storage. Use one application worker with the built-in in-memory rate limits, or configure shared rate limiting at your reverse proxy before adding workers. Back up the database and uploaded images together using SQLite's backup API or stop the service while copying `data/`. Test restoration. The included compose file binds localhost for use behind a reverse proxy. Configure your domain and HTTPS on your chosen host.

## Verify code

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## Source map

- `app.py`: routes, owner access, CSRF, SQLite, orders, uploads and settings.
- `templates/`: server-rendered storefront, checkout, receipts and owner pages.
- `static/js/store.js`: cart, search, filters and checkout submission.
- `static/js/yarn-scene.js`: Three.js decorative yarn ball.
- `static/vendor/three.module.js`: locally bundled Three.js 0.170.0.
- `static/css/style.css`: responsive design.
- `data/`: runtime database and uploaded product photos, excluded from ZIP.
- `tests/test_app.py`: integration checks.

The 3D yarn ball is a decorative illustration, not a 3D model of the actual products.
