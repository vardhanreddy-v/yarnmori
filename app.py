"""Yarnmori: small, real, self-hosted crochet shop.
Backend: FastAPI + SQLite; frontend: Jinja2, responsive CSS and vanilla JS.
"""
from __future__ import annotations

import io
import json
import os
import re
import secrets
import sqlite3
import time
import hmac
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Request, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.templating import Jinja2Templates
from PIL import Image, ImageOps, UnidentifiedImageError
Image.MAX_IMAGE_PIXELS = 25_000_000

BASE = Path(__file__).resolve().parent

# A small .env reader avoids a separate dependency. Never commit actual .env values.
env_file = BASE / '.env'
if env_file.exists():
    for line in env_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

DATA = Path(os.getenv('DATA_DIR', str(BASE / 'data')))
if not DATA.is_absolute():
    DATA = BASE / DATA
DATA = DATA.resolve()
DATA.mkdir(parents=True, exist_ok=True)
UPLOADS = DATA / 'uploads'
UPLOADS.mkdir(exist_ok=True)
DB_FILE = DATA / 'yarnmori.sqlite3'
ADMIN_USER = os.getenv('ADMIN_USER', 'owner')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '')
SECRET_KEY = os.getenv('SECRET_KEY', '')
PRODUCTION = os.getenv('PRODUCTION', '').lower() in ('1', 'true', 'yes')
if PRODUCTION and (not SECRET_KEY or len(SECRET_KEY) < 32 or len(ADMIN_PASSWORD) < 12 or SECRET_KEY.startswith('REPLACE_WITH_') or ADMIN_PASSWORD.startswith('REPLACE_WITH_')):
    raise RuntimeError('Production requires SECRET_KEY (32+ chars) and ADMIN_PASSWORD (12+ chars)')

app = FastAPI(title='Yarnmori | Handmade crochet gifts', docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY or 'LOCAL_DEV_ONLY_CHANGE_ME_BEFORE_DEPLOYMENT',
                   https_only=PRODUCTION, same_site='lax', session_cookie='yarnmori_session', max_age=12*3600)
app.mount('/static', StaticFiles(directory=str(BASE / 'static')), name='static')
templates = Jinja2Templates(directory=str(BASE / 'templates'))

SEED_PRODUCTS = [
    ('sunflower-keychain', 'Sunflower Keychain', 'Keychains', 299, 'A little pocket of sunshine, crocheted by hand. Finished with a secure silver-tone keyring.', 'sunflower.webp', 'Fresh pick', 1),
    ('lavender-octopus', 'Lavender Octopus Buddy', 'Tiny Friends', 349, 'Tiny, squishy and full of personality. A sweet handmade bag or key companion.', 'octopus.webp', 'Made with love', 2),
    ('heart-keychain', 'Sweetheart Keychain', 'Keychains', 229, 'A soft red crochet heart for your keys, bag, or someone special.', 'heart.webp', 'Giftable', 3),
    ('evil-eye-keychain', 'Blue Eye Keychain', 'Keychains', 319, 'A bold blue crochet eye motif, finished with a keyring for everyday carrying.', 'eye_keychain.webp', '', 4),
    ('watermelon-keychain', 'Watermelon Slice Charm', 'Keychains', 299, 'A little slice of summer, stitched in cheerful pink, green and white yarn.', 'watermelon.webp', 'Colour pop', 5),
    ('fish-keychain', 'Little Fish Keychain', 'Tiny Friends', 299, 'A bright, playful little fish with tiny stitched details.', 'fish.webp', '', 6),
    ('flower-collection', 'Build-Your-Own Crochet Bloom', 'Flowers', 399, 'Choose a handmade flower for a keepsake gift. Colours and style are confirmed after ordering.', 'flowers.webp', 'Customisable', 7),
    ('crochet-hair-clips', 'Crochet Hair Clip Set', 'Accessories', 249, 'A pair of crochet-detailed snap clips. Colour combination confirmed when we contact you.', 'clips.webp', '', 8),
    ('evil-eye-hanging', 'Blue Eye Hanging Charm', 'Home & Gifts', 449, 'A crochet hanging accent with a soft tassel, made for gifting or decorating.', 'eye_hanging.webp', '', 9),
]

SCHEMA = '''
CREATE TABLE IF NOT EXISTS checkout_submissions (token TEXT PRIMARY KEY, order_token TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
  category TEXT NOT NULL, price INTEGER NOT NULL CHECK(price > 0),
  description TEXT NOT NULL, image TEXT NOT NULL, badge TEXT NOT NULL DEFAULT '',
  position INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS orders (
 id INTEGER PRIMARY KEY AUTOINCREMENT, reference TEXT UNIQUE, token TEXT UNIQUE NOT NULL,
 customer_name TEXT NOT NULL, phone TEXT NOT NULL, email TEXT NOT NULL DEFAULT '',
 line1 TEXT NOT NULL, city TEXT NOT NULL, state TEXT NOT NULL, pincode TEXT NOT NULL,
 note TEXT NOT NULL DEFAULT '', subtotal INTEGER NOT NULL, shipping INTEGER NOT NULL,
 total INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'New',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS order_items (
 id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, product_id INTEGER NOT NULL,
 product_name TEXT NOT NULL, quantity INTEGER NOT NULL, unit_price INTEGER NOT NULL,
 FOREIGN KEY(order_id) REFERENCES orders(id)
);
'''
DEFAULT_SETTINGS = {
 'whatsapp': '', 'instagram': '', 'contact_email': '',
 'shipping_fee': '79', 'free_shipping_at': '999',
 'announcement': 'Small-batch crochet gifts, made with care in Telangana ✿',
 'processing_days': '3–7',
}

@contextmanager
def db():
    conn = sqlite3.connect(str(DB_FILE), timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=20000')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with db() as c:
        c.executescript(SCHEMA)
        if c.execute('SELECT COUNT(*) FROM products').fetchone()[0] == 0:
            c.executemany('''INSERT INTO products (slug,name,category,price,description,image,badge,position)
                             VALUES (?,?,?,?,?,?,?,?)''', [(*p[:5], '/static/products/'+p[5], *p[6:]) for p in SEED_PRODUCTS])
        for k,v in DEFAULT_SETTINGS.items():
            c.execute('INSERT OR IGNORE INTO settings (key,value) VALUES (?,?)', (k,v))

init_db()


def settings_dict():
    with db() as c:
        return {r['key']: r['value'] for r in c.execute('SELECT * FROM settings')}


def csrf_token(request: Request):
    if 'csrf' not in request.session:
        request.session['csrf'] = secrets.token_urlsafe(32)
    return request.session['csrf']


def require_csrf(request: Request, supplied: str):
    if not supplied or not hmac.compare_digest(supplied, request.session.get('csrf','')):
        raise HTTPException(403, 'Invalid form token; reload the page and try again.')


def base_context(request: Request, **kw):
    s = settings_dict()
    whatsapp = re.sub(r'\D', '', s.get('whatsapp',''))
    with db() as c:
        catalog = [dict(r) for r in c.execute('SELECT id,name,price,image FROM products WHERE active=1')]
    return {'request': request, 'settings': s, 'catalog': catalog, 'whatsapp_number': whatsapp,
            'csrf': csrf_token(request), 'admin_logged': bool(request.session.get('admin')),
            'year': datetime.now().year, **kw}


def render(request, name, status_code=200, **context):
    return templates.TemplateResponse(request=request, name=name, context=base_context(request, **context),status_code=status_code)


def admin_only(request: Request):
    if not request.session.get('admin'):
        raise HTTPException(303, headers={'Location':'/admin/login'})


@app.middleware('http')
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    if request.url.path.startswith('/admin') or request.url.path.startswith('/order/') or request.url.path == '/checkout':
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    return response


@app.get('/', response_class=HTMLResponse)
def home(request: Request):
    with db() as c:
        products = [dict(r) for r in c.execute('SELECT * FROM products WHERE active=1 ORDER BY position,id')]
    categories = ['All'] + list(dict.fromkeys(p['category'] for p in products))
    return render(request, 'home.html', products=products, categories=categories, products_json=products, title='Yarnmori | Little joys, handmade')


@app.get('/product/{slug}', response_class=HTMLResponse)
def product_detail(request: Request, slug: str):
    with db() as c:
        p = c.execute('SELECT * FROM products WHERE slug=? AND active=1', (slug,)).fetchone()
        if not p: raise HTTPException(404)
        related = [dict(r) for r in c.execute('SELECT * FROM products WHERE active=1 AND id!=? ORDER BY position LIMIT 4', (p['id'],))]
    return render(request, 'product.html', product=dict(p), related=related, title=f"{p['name']} | Yarnmori")


@app.get('/checkout', response_class=HTMLResponse)
def checkout_page(request: Request):
    with db() as c:
        completed = c.execute('SELECT 1 FROM checkout_submissions WHERE token=?', (request.session.get('submission_token', ''),)).fetchone()
    if completed or not request.session.get('submission_token'):
        request.session['submission_token'] = secrets.token_urlsafe(32)
    with db() as c:
        p = [dict(r) for r in c.execute('SELECT id,slug,name,category,price,image,active FROM products WHERE active=1')]
    return render(request, 'checkout.html', products_json=p, title='Checkout | Yarnmori', submission_token=request.session['submission_token'])


# Checkout writes a real database order, with server-calculated pricing.
_recent_orders = {}
@app.post('/checkout')
async def place_order(request: Request):
    form = await request.form()
    require_csrf(request, str(form.get('csrf','')))
    if form.get('company_website'):  # honeypot
        raise HTTPException(400, 'Invalid submission')
    fields = {k: str(form.get(k,'')).strip() for k in ('customer_name','phone','email','line1','city','state','pincode','note')}
    name, phone, email, line1, city, state, pincode, note = [fields[k] for k in fields]
    if not (2 <= len(name) <= 100 and len(line1) >= 8 and len(line1) <= 350 and
            2 <= len(city) <= 90 and 2 <= len(state) <= 90 and len(note) <= 600):
        raise HTTPException(400, 'Please enter complete address and contact details.')
    mobile = re.sub(r'\D', '', phone)
    if mobile.startswith('91') and len(mobile) == 12:
        mobile = mobile[2:]
    if not re.fullmatch(r'[6-9]\d{9}', mobile) or not re.fullmatch(r'\d{6}', pincode):
        raise HTTPException(400, 'Enter a valid Indian mobile number and six-digit PIN code.')
    if email and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):
        raise HTTPException(400, 'Invalid email address.')
    if len(email) > 180:
        raise HTTPException(400, 'Email is too long.')
    try:
        cart = json.loads(str(form.get('cart_json','')))
    except (ValueError, TypeError):
        raise HTTPException(400, 'The cart could not be read. Please try again.')
    if not isinstance(cart,list) or not (1<=len(cart)<=15):
        raise HTTPException(400, 'Your cart must contain at least one product.')
    counts = {}
    for item in cart:
        if not isinstance(item,dict) or not isinstance(item.get('id'),int) or isinstance(item.get('id'),bool) or not isinstance(item.get('qty'),int) or isinstance(item.get('qty'),bool):
            raise HTTPException(400, 'Invalid cart data.')
        id_, qty = item['id'], item['qty']
        if not 1 <= qty <= 10 or id_ in counts:
            raise HTTPException(400, 'Invalid item quantity or duplicate item.')
        counts[id_] = qty
    if sum(counts.values()) > 25:
        raise HTTPException(400, 'Please contact us directly for bulk orders.')

    submission = str(form.get('submission_token', ''))
    if not submission or not hmac.compare_digest(submission, request.session.get('submission_token', '')):
        raise HTTPException(400, 'Your checkout has expired. Reload checkout and try again.')
    with db() as c:
        prior = c.execute('SELECT order_token FROM checkout_submissions WHERE token=?', (submission,)).fetchone()
        if prior:
            return RedirectResponse('/order/' + prior['order_token'], status_code=303)

    # Small rate limit. Use dedicated reverse proxy limits for large deployments.
    client_ip = request.client.host if request.client else 'unknown'
    now = time.monotonic()
    history = [t for t in _recent_orders.get(client_ip,[]) if now-t < 1800]
    if len(history) >= 4:
        raise HTTPException(429, 'Too many orders recently. Please contact us instead.')

    s = settings_dict()
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        prior = c.execute('SELECT order_token FROM checkout_submissions WHERE token=?', (submission,)).fetchone()
        if prior:
            return RedirectResponse('/order/' + prior['order_token'], status_code=303)
        product_rows = [c.execute('SELECT id,name,price,active FROM products WHERE id=?',(id_,)).fetchone() for id_ in counts]
        if any(p is None or not p['active'] for p in product_rows):
            raise HTTPException(400, 'One of your items is no longer available. Refresh and try again.')
        subtotal = sum(p['price'] * counts[p['id']] for p in product_rows)
        shipping = 0 if subtotal >= int(s['free_shipping_at']) else int(s['shipping_fee'])
        total = subtotal + shipping
        token = secrets.token_urlsafe(24)
        cur = c.execute('''INSERT INTO orders(token,customer_name,phone,email,line1,city,state,pincode,note,subtotal,shipping,total)
                          VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (token,name,mobile,email,line1,city,state,pincode,note,subtotal,shipping,total))
        oid = cur.lastrowid
        ref = f'YM-{oid:05d}'
        c.execute('UPDATE orders SET reference=? WHERE id=?', (ref,oid))
        for p in product_rows:
            c.execute('INSERT INTO order_items(order_id,product_id,product_name,quantity,unit_price) VALUES(?,?,?,?,?)',
                      (oid,p['id'],p['name'],counts[p['id']],p['price']))
        c.execute('INSERT INTO checkout_submissions(token, order_token) VALUES (?,?)', (submission, token))
    history.append(now)
    _recent_orders[client_ip] = history
    return RedirectResponse(f'/order/{token}', status_code=303)


@app.get('/order/{token}', response_class=HTMLResponse)
def order_success(request: Request, token: str):
    with db() as c:
        order = c.execute('SELECT * FROM orders WHERE token=?',(token,)).fetchone()
        if not order: raise HTTPException(404)
        items = [dict(r) for r in c.execute('SELECT * FROM order_items WHERE order_id=?',(order['id'],))]
    s = settings_dict()
    mobile = re.sub(r'\D','',s.get('whatsapp',''))
    message = f"Hi Yarnmori! I placed order {order['reference']}. Please confirm the details and payment instructions."
    wa = f'https://wa.me/{mobile}?text={quote(message)}' if mobile else ''
    return render(request, 'success.html', order=dict(order), items=items, whatsapp_link=wa, title='Order received | Yarnmori')


@app.get('/policy/{kind}', response_class=HTMLResponse)
def policy(request: Request, kind: str):
    if kind not in ('shipping','returns','privacy'):
        raise HTTPException(404)
    return render(request, 'policy.html', kind=kind, title=kind.title()+' | Yarnmori')


_login_attempts = {}
@app.get('/admin/login', response_class=HTMLResponse)
def admin_login(request: Request):
    if request.session.get('admin'):
        return RedirectResponse('/admin',303)
    return render(request,'admin_login.html', title='Owner sign in | Yarnmori', error='')


@app.post('/admin/login')
async def admin_login_post(request: Request):
    form = await request.form()
    require_csrf(request,str(form.get('csrf','')))
    ip = request.client.host if request.client else 'unknown'
    now = time.monotonic()
    attempts = [x for x in _login_attempts.get(ip,[]) if now-x < 900]
    if len(attempts) >= 10:
        raise HTTPException(429, 'Too many sign-in attempts. Try again later.')
    username, password = str(form.get('username','')),str(form.get('password',''))
    if ADMIN_PASSWORD and hmac.compare_digest(username, ADMIN_USER) and hmac.compare_digest(password,ADMIN_PASSWORD):
        request.session.clear()
        request.session['admin'] = True
        request.session['csrf'] = secrets.token_urlsafe(32)
        _login_attempts.pop(ip,None)
        return RedirectResponse('/admin',303)
    attempts.append(now)
    _login_attempts[ip] = attempts
    return render(request,'admin_login.html',title='Owner sign in | Yarnmori',error='Invalid credentials or owner password not set.',status_code=401)


@app.post('/admin/logout')
async def admin_logout(request: Request):
    admin_only(request)
    form = await request.form()
    require_csrf(request,str(form.get('csrf','')))
    request.session.clear()
    return RedirectResponse('/admin/login',303)


STATUSES = ['New','Contacted','Confirmed','Making','Shipped','Delivered','Cancelled']
@app.get('/admin', response_class=HTMLResponse)
def dashboard(request: Request):
    admin_only(request)
    with db() as c:
        orders = [dict(r) for r in c.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 100')]
        for o in orders:
            o['items'] = [dict(r) for r in c.execute('SELECT * FROM order_items WHERE order_id=?',(o['id'],))]
        stats = {
            'orders': c.execute('SELECT COUNT(*) FROM orders').fetchone()[0],
            'new': c.execute("SELECT COUNT(*) FROM orders WHERE status='New'").fetchone()[0],
            'gross': c.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE status NOT IN ('Cancelled')").fetchone()[0],
            'active_products': c.execute('SELECT COUNT(*) FROM products WHERE active=1').fetchone()[0],
        }
    return render(request,'admin.html',title='Dashboard | Yarnmori',orders=orders,stats=stats,statuses=STATUSES)


@app.post('/admin/orders/{id_}/status')
async def update_order(request: Request,id_:int):
    admin_only(request)
    form = await request.form()
    require_csrf(request,str(form.get('csrf','')))
    status = str(form.get('status',''))
    if status not in STATUSES: raise HTTPException(400)
    with db() as c:
        changed = c.execute('UPDATE orders SET status=? WHERE id=?',(status,id_))
        if not changed.rowcount:
            raise HTTPException(404, 'Order not found.')
    return RedirectResponse('/admin#orders',303)


@app.get('/admin/products',response_class=HTMLResponse)
def admin_products(request: Request):
    admin_only(request)
    with db() as c:
        products = [dict(r) for r in c.execute('SELECT * FROM products ORDER BY position,id')]
    return render(request,'admin_products.html',title='Manage products | Yarnmori',products=products)


def product_form_page(request, product=None, error=''):
    return render(request,'admin_product_form.html',title='Edit product | Yarnmori',product=product,error=error)

@app.get('/admin/products/new',response_class=HTMLResponse)
def new_product(request: Request):
    admin_only(request)
    return product_form_page(request)

@app.get('/admin/products/{id_}/edit',response_class=HTMLResponse)
def edit_product(request: Request,id_:int):
    admin_only(request)
    with db() as c:
        p = c.execute('SELECT * FROM products WHERE id=?',(id_,)).fetchone()
    if not p: raise HTTPException(404)
    return product_form_page(request,dict(p))


def save_uploaded_photo(file: UploadFile | None):
    if not file or not file.filename: return None
    raw = file.file.read(5*1024*1024+1)
    if len(raw)>5*1024*1024: raise HTTPException(400,'Image must be under 5 MB.')
    try:
        with Image.open(io.BytesIO(raw)) as src:
            if src.format not in ('JPEG','PNG','WEBP'):
                raise HTTPException(400,'Use JPG, PNG or WebP images.')
            src.load()
            im = ImageOps.exif_transpose(src).convert('RGB')
            im.thumbnail((1600,1600))
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(400,'The uploaded file is not a valid image.')
    filename = secrets.token_hex(12)+'.webp'
    im.save(UPLOADS / filename,'WEBP',quality=85,method=5)
    return '/media/'+filename


@app.post('/admin/products/save')
async def save_product(request: Request):
    admin_only(request)
    form = await request.form()
    require_csrf(request,str(form.get('csrf','')))
    try:
        id_ = int(form.get('id') or 0)
        name = str(form.get('name','')).strip()[:100]
        category = str(form.get('category','')).strip()[:50]
        description = str(form.get('description','')).strip()[:1000]
        price = int(form.get('price') or 0)
        position = int(form.get('position') or 0)
        badge = str(form.get('badge','')).strip()[:40]
        active = 1 if form.get('active') == 'on' else 0
        slug = re.sub(r'[^a-z0-9]+','-',str(form.get('slug','')).strip().lower()).strip('-')[:90]
        if not slug: slug = re.sub(r'[^a-z0-9]+','-',name.lower()).strip('-')[:90]
        if not (2<=len(name)<=100 and category and description and 20<=price<=100000 and slug):
            raise ValueError('Complete the product details and choose a price between ₹20 and ₹100,000.')
    except (TypeError,ValueError) as exc:
        raise HTTPException(400,str(exc))
    upload = form.get('image_file')
    image = save_uploaded_photo(upload) if getattr(upload, 'file', None) is not None else None
    with db() as c:
        if id_:
            prior = c.execute('SELECT image FROM products WHERE id=?',(id_,)).fetchone()
            if not prior: raise HTTPException(404)
            image = image or prior['image']
            try:
                c.execute('''UPDATE products SET slug=?,name=?,category=?,price=?,description=?,image=?,badge=?,position=?,active=? WHERE id=?''',
                         (slug,name,category,price,description,image,badge,position,active,id_))
            except sqlite3.IntegrityError:
                raise HTTPException(400,'This product URL slug already exists.')
        else:
            if not image: raise HTTPException(400,'Upload a photo for a new product.')
            try:
                c.execute('''INSERT INTO products(slug,name,category,price,description,image,badge,position,active) VALUES (?,?,?,?,?,?,?,?,?)''',
                         (slug,name,category,price,description,image,badge,position,active))
            except sqlite3.IntegrityError:
                raise HTTPException(400,'This product URL slug already exists.')
    return RedirectResponse('/admin/products',303)


@app.get('/admin/settings',response_class=HTMLResponse)
def admin_settings(request: Request):
    admin_only(request)
    return render(request,'admin_settings.html',title='Store settings | Yarnmori')


@app.post('/admin/settings')
async def admin_settings_post(request: Request):
    admin_only(request)
    form = await request.form()
    require_csrf(request,str(form.get('csrf','')))
    whatsapp = re.sub(r'\D','',str(form.get('whatsapp','')))
    if whatsapp and not (10<=len(whatsapp)<=15): raise HTTPException(400,'Use WhatsApp number with country code, e.g. 91XXXXXXXXXX.')
    instagram = str(form.get('instagram','')).strip()[:250]
    if instagram and not re.fullmatch(r'https://(www\.)?instagram\.com/[A-Za-z0-9._/?=&-]+',instagram):
        raise HTTPException(400,'Enter a valid https://instagram.com/... URL.')
    email = str(form.get('contact_email','')).strip()[:180]
    if email and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email): raise HTTPException(400,'Invalid email.')
    try:
        fee,threshold = int(form.get('shipping_fee','')),int(form.get('free_shipping_at',''))
    except ValueError:
        raise HTTPException(400,'Invalid shipping price.')
    if not (0<=fee<=3000 and 0<=threshold<=100000): raise HTTPException(400,'Invalid shipping price.')
    days = str(form.get('processing_days','')).strip()[:40]
    if not days: raise HTTPException(400,'Enter your estimated production days.')
    notice = str(form.get('announcement','')).strip()[:140]
    changes = {'whatsapp':whatsapp,'instagram':instagram,'contact_email':email,
               'shipping_fee':str(fee),'free_shipping_at':str(threshold),
               'processing_days':days,'announcement':notice}
    with db() as c:
        for k,v in changes.items():
            c.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(k,v))
    return RedirectResponse('/admin/settings?saved=1',303)


@app.get('/media/{filename}')
def media(filename: str):
    if not re.fullmatch(r'[a-f0-9]{24}\.webp',filename): raise HTTPException(404)
    file_path = UPLOADS / filename
    if not file_path.exists(): raise HTTPException(404)
    return FileResponse(file_path,media_type='image/webp')


@app.get('/health')
def health():
    return {'status':'ok','site':'Yarnmori'}


@app.get('/robots.txt')
def robots():
    return PlainTextResponse('User-agent: *\nDisallow: /admin\nDisallow: /checkout\nDisallow: /order/\n')


@app.get('/sitemap.xml')
def sitemap(request:Request):
    with db() as c:
        slugs = [r['slug'] for r in c.execute('SELECT slug FROM products WHERE active=1')]
    base = str(request.base_url).rstrip('/')
    urls = [base+'/'] + [base+'/product/'+quote(x) for x in slugs]
    body = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{x}</loc></url>' for x in urls)+'</urlset>'
    return PlainTextResponse(body,media_type='application/xml')
