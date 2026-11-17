"""Regression checks for checkout retries, stale products and private owner actions."""
import json
import re
from test_app import client, csrf_from
from app import db, _recent_orders

def checkout():
    page=client.get('/checkout')
    return dict(csrf=csrf_from(page),submission_token=re.search(r'name="submission_token" value="([^"]+)"',page.text).group(1),
        customer_name='Test Customer',phone='9876543210',email='',line1='12 Example Street',city='Gadwal',state='Telangana',pincode='509125',note='',cart_json='[{"id":1,"qty":1}]')

def test_retry_after_receipt_does_not_duplicate_order():
    _recent_orders.clear()
    order=checkout()
    response=client.post('/checkout',data=order)
    assert response.status_code==303
    client.get(response.headers['location'])
    with db() as c: before=c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
    retry=client.post('/checkout',data=order)
    assert retry.status_code==303
    assert retry.headers['location']==response.headers['location']
    with db() as c: assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==before
    assert checkout()['submission_token']!=order['submission_token']

def test_catalog_contains_authoritative_prices():
    page=client.get('/')
    catalog=json.loads(re.search(r'window.YARNMORI_PRODUCTS=(.*?);</script>',page.text).group(1))
    with db() as c:
        product=c.execute('SELECT * FROM products WHERE id=1').fetchone()
    assert next(p for p in catalog if p['id']==1)['price']==product['price']
    assert 'inert data-cart-drawer' in page.text
    assert 'fonts.googleapis.com' not in page.text

def test_unavailable_product_and_invalid_cart_are_rejected():
    _recent_orders.clear()
    order=checkout()
    for cart in ('[]','[{"id":1,"qty":11}]','[{"id":true,"qty":1}]','[{"id":1,"qty":1},{"id":1,"qty":1}]'):
        assert client.post('/checkout',data={**order,'cart_json':cart}).status_code==400
    with db() as c: c.execute('UPDATE products SET active=0 WHERE id=1')
    try:
        assert client.post('/checkout',data=order).status_code==400
    finally:
        with db() as c: c.execute('UPDATE products SET active=1 WHERE id=1')

def test_owner_settings_reject_invalid_links_and_missing_order():
    page=client.get('/admin/login')
    if page.status_code==303:
        page=client.get('/admin')
    else:
        assert client.post('/admin/login',data={'csrf':csrf_from(page),'username':'studio','password':'correct-horse-staple-battery'}).status_code==303
        page=client.get('/admin')
    token=csrf_from(page)
    assert client.post('/admin/orders/999999/status',data={'csrf':token,'status':'Making'}).status_code==404
    assert client.post('/admin/orders/1/status',data={'csrf':'wrong','status':'Making'}).status_code==403
