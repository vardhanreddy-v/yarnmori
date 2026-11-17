"""Integration tests cover public pages, persistent orders, price trust, and owner actions."""
import os
import re
import tempfile
from pathlib import Path

os.environ['DATA_DIR'] = tempfile.mkdtemp(prefix='yarnmori_test_')
os.environ['ADMIN_USER'] = 'studio'
os.environ['ADMIN_PASSWORD'] = 'correct-horse-staple-battery'
os.environ['SECRET_KEY'] = 'unit-test-secret-must-be-more-than-32-chars'

from fastapi.testclient import TestClient
from app import app, db

client = TestClient(app, follow_redirects=False)

def csrf_from(page):
    match = re.search(r'<meta name="csrf-token" content="([^"]+)"', page.text)
    if not match:
        match = re.search(r'name="csrf" value="([^"]+)"', page.text)
    assert match, page.text[:500]
    return match.group(1)

def test_public_site():
    response = client.get('/')
    assert response.status_code == 200
    assert 'yarnmori' in response.text
    assert 'Sunflower Keychain' in response.text
    assert 'Lavender Octopus Buddy' in response.text
    assert '/static/products/sunflower.webp' in response.text
    product = client.get('/product/sunflower-keychain')
    assert product.status_code == 200
    assert '₹299' in product.text
    assert client.get('/health').json()['status'] == 'ok'
    assert client.get('/admin').status_code == 303


def test_checkout_and_admin_flow():
    page = client.get('/checkout')
    token = csrf_from(page)
    order = dict(submission_token=re.search(r'name="submission_token" value="([^"]+)"', page.text).group(1), csrf=token, customer_name='Anjali Reddy', phone='9876543210',
                 email='anjali@example.com', line1='Plot 12, Main Bazaar near school',
                 city='Gadwal', state='Telangana', pincode='509125',
                 note='Please make it in pastel yellow', company_website='',
                 cart_json='[{"id":1,"qty":2,"price":1}]')  # malicious price must be ignored
    res = client.post('/checkout', data=order)
    assert res.status_code == 303, res.text
    assert res.headers['location'].startswith('/order/')
    duplicate = client.post('/checkout', data=order)
    assert duplicate.headers['location'] == res.headers['location']
    receipt = client.get(res.headers['location'])
    assert receipt.status_code == 200
    assert 'YM-00001' in receipt.text
    assert '₹598' in receipt.text
    assert '₹677' in receipt.text  # 2*299 + 79 shipping, calculated by server
    assert 'No payment has been collected' in receipt.text
    assert receipt.headers['X-Robots-Tag'] == 'noindex, nofollow'
    with db() as c:
        row=c.execute('SELECT * FROM orders').fetchone()
        assert row['subtotal'] == 598 and row['shipping'] == 79
        assert row['pincode'] == '509125'
        assert c.execute('SELECT COUNT(*) FROM order_items').fetchone()[0] == 1
    bad=client.post('/checkout',data={**order,'csrf':'broken'})
    assert bad.status_code == 403
    fresh=client.get('/checkout')
    order['submission_token']=re.search(r'name="submission_token" value="([^"]+)"',fresh.text).group(1)
    badprice=client.post('/checkout',data={**order,'cart_json':'[{"id":1000,"qty":1}]'})
    assert badprice.status_code == 400
    badphone=client.post('/checkout',data={**order,'phone':'11111'})
    assert badphone.status_code == 400

    login_page=client.get('/admin/login')
    signin=client.post('/admin/login',data=dict(csrf=csrf_from(login_page),username='studio',password='correct-horse-staple-battery'))
    assert signin.status_code == 303
    assert signin.headers['location']=='/admin'
    dashboard=client.get('/admin')
    assert dashboard.status_code==200
    assert 'Anjali Reddy' in dashboard.text
    assert 'YM-00001' in dashboard.text
    admin_csrf=csrf_from(dashboard)
    update=client.post('/admin/orders/1/status',data={'csrf':admin_csrf,'status':'Making'})
    assert update.status_code==303
    with db() as c:
        assert c.execute('SELECT status FROM orders WHERE id=1').fetchone()[0]=='Making'

    settings_page=client.get('/admin/settings')
    assert settings_page.status_code == 200
    settings_update=client.post('/admin/settings',data={
      'csrf':csrf_from(settings_page),'whatsapp':'919876543210',
      'instagram':'https://instagram.com/yarnmori.studio','contact_email':'',
      'shipping_fee':'55','free_shipping_at':'1200','processing_days':'4-8',
      'announcement':'Yarnmori test banner'})
    assert settings_update.status_code==303
    assert 'Yarnmori test banner' in client.get('/').text

    product_page=client.get('/admin/products/1/edit')
    new_product = client.post('/admin/products/save',data={
      'csrf':csrf_from(product_page),'id':'1','name':'Sunflower Keychain','slug':'sunflower-keychain',
      'category':'Keychains','price':'329','description':'Updated description',
      'position':'1','badge':'New','active':'on'},follow_redirects=False)
    assert new_product.status_code==303, new_product.text
    assert '₹329' in client.get('/product/sunflower-keychain').text

    logout=client.post('/admin/logout',data={'csrf':csrf_from(client.get('/admin'))})
    assert logout.status_code == 303
    assert client.get('/admin').status_code == 303


def test_policy_and_unknown():
    assert client.get('/policy/privacy').status_code==200
    assert client.get('/policy/shipping').status_code==200
    assert client.get('/policy/missing').status_code==404
    assert client.get('/product/no-such-item').status_code==404
    assert client.get('/sitemap.xml').status_code==200


def test_owner_can_upload_new_product_photo():
    import io
    from PIL import Image
    login_page=client.get('/admin/login')
    res=client.post('/admin/login',data={'csrf':csrf_from(login_page),'username':'studio','password':'correct-horse-staple-battery'})
    assert res.status_code==303
    page=client.get('/admin/products/new')
    photo=io.BytesIO()
    Image.new('RGB',(40,40),'lavender').save(photo,format='PNG')
    res=client.post('/admin/products/save',data={
       'csrf':csrf_from(page),'id':'','name':'Pink Daisy Clip','slug':'pink-daisy-clip',
       'category':'Accessories','price':'189','description':'Handmade floral hair clip',
       'position':'30','badge':'New design','active':'on'},
       files={'image_file':('clip.png',photo.getvalue(),'image/png')})
    assert res.status_code==303, res.text
    with db() as c:
        product=c.execute("SELECT * FROM products WHERE slug='pink-daisy-clip'").fetchone()
        assert product['image'].startswith('/media/')
    image=client.get(product['image'])
    assert image.status_code==200
    assert image.headers['content-type']=='image/webp'
    assert 'Pink Daisy Clip' in client.get('/').text
    bad=client.post('/admin/products/save',data={
       'csrf':csrf_from(client.get('/admin/products/new')),'name':'Invalid Upload','slug':'invalid-upload',
       'category':'Accessories','price':'200','description':'bad photo','active':'on'},
       files={'image_file':('bad.png',b'not an image','image/png')})
    assert bad.status_code==400
