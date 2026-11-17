(() => {
  'use strict';
  const KEY = 'yarnmori_cart_v1';
  const money = n => '₹' + Number(n || 0).toLocaleString('en-IN');
  const $ = s => document.querySelector(s);
  const $$ = s => Array.from(document.querySelectorAll(s));
  const drawer = $('[data-cart-drawer]');
  const backdrop = $('[data-cart-backdrop]');
  let cart = [];
  const catalog = new Map((window.YARNMORI_PRODUCTS || []).map(p => [p.id, p]));
  let previousFocus = null;
  const backgroundNodes = Array.from(document.body.children).filter(el => ![drawer, backdrop].includes(el) && el.tagName !== 'SCRIPT' && !el.hasAttribute('data-toast'));
  let placing = false;
  try {
    const stored = JSON.parse(localStorage.getItem(KEY) || '[]');
    if (Array.isArray(stored)) {
      const seen = new Set();
      cart = stored.filter(x => x && Number.isInteger(x.id) && Number.isInteger(x.qty) && x.qty > 0 && catalog.has(x.id) && !seen.has(x.id) && seen.add(x.id))
        .slice(0,15).map(x => ({...catalog.get(x.id), qty: Math.min(10,x.qty)}));
    }
  } catch (_) {}
  try { localStorage.setItem(KEY, JSON.stringify(cart)); } catch (_) {}


  function save() { try { localStorage.setItem(KEY, JSON.stringify(cart)); } catch (_) {} renderCart(); if (window.YARNMORI_CHECKOUT_PRODUCTS) renderCheckout(); }
  function toast(msg) { const el=$('[data-toast]'); if (!el) return; el.textContent=msg; el.classList.add('show'); clearTimeout(window._yarnmoriToast); window._yarnmoriToast=setTimeout(()=>el.classList.remove('show'),2500); }
  function open() {
    if (!drawer) return;
    previousFocus=document.activeElement;
    drawer.inert=false;
    drawer.classList.add('is-open'); backdrop?.classList.add('is-open');
    drawer.setAttribute('aria-hidden','false'); document.body.classList.add('cart-visible');
    backgroundNodes.forEach(el=>el.inert=true);
    $('[data-close-cart]')?.focus();
  }
  function close() {
    if (!drawer || !drawer.classList.contains('is-open')) return;
    backgroundNodes.forEach(el=>el.inert=false);
    drawer.classList.remove('is-open'); backdrop?.classList.remove('is-open');
    drawer.setAttribute('aria-hidden','true'); drawer.inert=true;
    document.body.classList.remove('cart-visible'); previousFocus?.focus();
  }
  drawer?.addEventListener('keydown', e=>{
    if(e.key!=='Tab') return;
    const focusable=Array.from(drawer.querySelectorAll('button:not([disabled]), a[href]:not([aria-disabled="true"])')).filter(el=>el.getClientRects().length);
    const first=focusable[0], last=focusable[focusable.length-1];
    if(e.shiftKey && document.activeElement===first){e.preventDefault();last?.focus();}
    else if(!e.shiftKey && document.activeElement===last){e.preventDefault();first?.focus();}
  });
  $$('[data-open-cart]').forEach(el=>el.addEventListener('click',open));
  $$('[data-close-cart]').forEach(el=>el.addEventListener('click',close));
  backdrop?.addEventListener('click',close);
  document.addEventListener('keydown',e=>{if(e.key==='Escape')close()});

  function add(product) {
    if(placing)return;
    if(cart.reduce((n,x)=>n+x.qty,0)>=25){toast('Maximum 25 items per order. Contact us for bulk orders.');return;}
    const existing=cart.find(x=>x.id===product.id);
    if(existing){ if(existing.qty>=10){toast('Maximum 10 of one design per order');return;} existing.qty+=1; }
    else { if(cart.length>=15){toast('Maximum 15 designs per order');return;} cart.push({...product,qty:1}); }
    save(); toast('Added to your little bag ♡'); open();
  }
  $$('[data-add]').forEach(btn=>btn.addEventListener('click',()=>add({id:Number(btn.dataset.add), name:btn.dataset.name,price:Number(btn.dataset.price),image:btn.dataset.image})));
  function changeQty(id,delta) { if(placing)return; if(delta>0 && cart.reduce((n,x)=>n+x.qty,0)>=25){toast('Maximum 25 items per order');return;} const item=cart.find(x=>x.id===id); if (!item) return; item.qty+=delta; if (item.qty>10)item.qty=10; if(item.qty<1)cart=cart.filter(x=>x.id!==id); save(); }
  function node(tag,cls,text) {const el=document.createElement(tag); if(cls)el.className=cls; if(text!==undefined)el.textContent=text; return el;}
  function renderCart() {
    const count=cart.reduce((n,x)=>n+x.qty,0);
    $$('[data-cart-count]').forEach(el=>el.textContent=count);
    const root=$('[data-cart-items]'); if(!root)return; root.replaceChildren();
    if(!cart.length){const empty=node('div','cart-empty');empty.append(node('div','empty-icon','♡'),node('h3','', 'Your bag is feeling a little empty'),node('p','', 'A tiny treat is waiting for you.'));const link=node('a','btn btn-outline','Explore the shop ↗');link.href='/#shop';empty.append(link);root.append(empty);}
    for (const item of cart) {
      const row=node('div','cart-item');
      const im=node('img','cart-item-image');im.src=item.image;im.alt=item.name;
      const content=node('div','cart-item-info');
      content.append(node('h3','',item.name),node('p','',money(item.price)));
      const controls=node('div','qty-controls');
      const minus=node('button','','−');minus.type='button';minus.setAttribute('aria-label','Remove one '+item.name);minus.addEventListener('click',()=>changeQty(item.id,-1));
      const plus=node('button','','+');plus.type='button';plus.setAttribute('aria-label','Add one '+item.name);plus.addEventListener('click',()=>changeQty(item.id,1));
      plus.disabled=item.qty>=10;
      controls.append(minus,node('span','',String(item.qty)),plus);content.append(controls);row.append(im,content);root.append(row);
    }
    const subtotal=cart.reduce((n,x)=>n+x.price*x.qty,0);
    const total=$('[data-cart-subtotal]');if(total) total.textContent=money(subtotal);
    const checkoutLink=$('[data-checkout-link]');if(checkoutLink){checkoutLink.classList.toggle('disabled',!cart.length);checkoutLink.setAttribute('aria-disabled',String(!cart.length));}
  }
  renderCart();
  document.addEventListener('click',e=>{const link=e.target.closest?.('[data-checkout-link]'); if(link&&!cart.length)e.preventDefault();});
  const filterButtons=$$('[data-filter]'),search=$('#product-search'),cards=$$('.product-card');
  let activeFilter='All';
  function filterProducts(){const q=(search?.value||'').trim().toLowerCase();let visible=0;cards.forEach(c=>{const matchCategory=activeFilter==='All'||c.dataset.category===activeFilter;const matchQuery=!q||c.dataset.productName.includes(q)||c.dataset.category.toLowerCase().includes(q);c.hidden=!(matchCategory&&matchQuery);if(!c.hidden)visible++});const empty=$('#empty-results');if(empty)empty.hidden=visible!==0;}
  filterButtons.forEach(btn=>btn.addEventListener('click',()=>{activeFilter=btn.dataset.filter;filterButtons.forEach(b=>b.classList.toggle('active',b===btn));filterProducts()}));
  search?.addEventListener('input',filterProducts);
  const menu=$('[data-mobile-nav]'), menuToggle=$('[data-menu-toggle]');
  function toggleMenu(expanded){menu?.classList.toggle('visible',expanded);menuToggle?.setAttribute('aria-expanded',String(expanded));}
  menuToggle?.addEventListener('click',()=>toggleMenu(!menu.classList.contains('visible')));
  menu?.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>toggleMenu(false)));
  document.addEventListener('keydown',e=>{if(e.key==='Escape')toggleMenu(false)});


  function renderCheckout(){
    const products=window.YARNMORI_CHECKOUT_PRODUCTS||[];
    const byId=new Map(products.filter(p=>p.active===undefined||p.active).map(p=>[p.id,p]));
    const valid=cart.filter(x=>byId.has(x.id));
    const root=$('#checkout-items');if(!root)return;root.replaceChildren();
    if(!valid.length){root.append(node('p','cart-checkout-empty','Your bag is empty. Visit the shop to add a little something.'));}
    for(const item of valid){const product=byId.get(item.id);const row=node('div','checkout-line');const im=node('img');im.src=product.image;im.alt=product.name;const info=node('div');info.append(node('strong','',product.name),node('span','',`Qty ${item.qty}`));row.append(im,info,node('b','',money(item.qty*product.price)));root.append(row);}
    const subtotal=valid.reduce((n,item)=>n+(byId.get(item.id).price*item.qty),0);
    const shipping=subtotal>=Number(window.YARNMORI_FREE_SHIPPING)?0:Number(window.YARNMORI_SHIPPING);
    if($('#checkout-subtotal'))$('#checkout-subtotal').textContent=money(subtotal);
    if($('#checkout-shipping'))$('#checkout-shipping').textContent=subtotal?money(shipping):'—';
    if($('#checkout-total'))$('#checkout-total').textContent=money(subtotal?subtotal+shipping:0);
    if($('#place-order'))$('#place-order').disabled=placing||!valid.length||valid.reduce((n,x)=>n+x.qty,0)>25;
    const hidden=$('#cart-json');if(hidden)hidden.value=JSON.stringify(valid.map(x=>({id:x.id,qty:x.qty})));
  }
  if(window.YARNMORI_CHECKOUT_PRODUCTS){renderCheckout();const form=$('#checkout-form');form?.addEventListener('submit',async e=>{
      e.preventDefault();
      const button=$('#place-order'), error=$('#checkout-error');
      if(!cart.length) { toast('Your bag is empty.'); return; }
      if(placing)return; placing=true;
      button.disabled=true; button.textContent='Saving your order…'; error.hidden=true;
      try {
        const controller=new AbortController();
        const timer=setTimeout(()=>controller.abort(),20000);
        let response;
        try { response=await fetch(form.action,{method:'POST',body:new FormData(form),signal:controller.signal}); }
        finally { clearTimeout(timer); }
        if(response.ok && response.redirected && new URL(response.url).pathname.startsWith('/order/')) {
          location.assign(response.url); return;
        }
        let message='Unable to save your order. Please try again.';
        try { const body=await response.json(); if(typeof body.detail==='string') message=body.detail; } catch(_) {}
        throw new Error(message);
      } catch(err) {
        placing=false;
        error.textContent=err.name==='AbortError' ? 'This is taking longer than expected. Please retry; your order will not be duplicated.' : (err.message || 'Connection lost. Please try again.'); error.hidden=false;
        button.disabled=false; button.textContent='Place my order request ↗';
      }
    });}
})();
