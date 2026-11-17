# Yarnmori brand and validation

## Your palette

| Colour | Hex | Purpose |
| --- | --- | --- |
| Cream | #FAF6EF | Main page background |
| Lilac | #D6CAE7 | Hero shape, value strip, footer, cart badges |
| Honey | #E8B955 | Decorative accents and gift labels |
| Sage | #A5B8A0 | Announcement, status labels, closing section |
| Charcoal | #33302F | Text, buttons, navigation |

Pale brand colours use charcoal text for legibility. Neutral shades support form borders and secondary text. Error messages retain a distinct red treatment.

## Fonts

DM Serif Display regular and italic: brand, hero text and headings. Its rounded shapes and expressive italics suit a small handmade gift shop.

DM Sans 400, 500, 600 and 700: product information, prices, navigation, forms and owner dashboard. It keeps the practical parts easy to read.

Font files and SIL Open Font License notices are bundled in `static/fonts/`. No Google Fonts request is required at runtime. Three.js is bundled in `static/vendor/`.

## Verified

Eight integration tests pass, covering storefront routes, order creation with server-side pricing, duplicate retries, product availability, malformed carts, owner sign-in, CSRF protection, status updates, settings, product edits and image uploads.

Browser checks completed: desktop homepage appearance, add to cart, quantity change, checkout totals, category filtering, sample order submission, receipt reference and cleared cart. The sample order total was ₹677 for two ₹299 items plus ₹79 shipping. No money was collected.

JavaScript syntax checks passed. Responsive CSS remains in place; this run did not test every mobile device or browser. No claim of zero defects or production load testing is made.

## Improvements

- Reconcile stored cart data with current database prices and available products on page load.
- Reject duplicate or invalid stored cart entries and clamp quantities.
- Align frontend quantity limits with backend order limits.
- Keep background content out of the tab order while the shopping bag is open; trap focus inside it and return focus when it closes.
- Report mobile menu state to assistive technology.
- Prevent repeated checkout submissions, time out slow requests and support retry without creating another order.
- Retain a completed checkout token for safe retries and issue a new one when starting the next checkout.
- Stop revisiting a receipt from clearing a newly created cart in the same tab.
- Resolve relative data paths consistently from the app folder.
- Return 404 when an owner tries to update an order that does not exist.

## Before taking live orders

Set your own owner password and session secret with `python setup.py`; then set business contacts and shipping in the owner dashboard. Review prices, images and store policies. Host the Python application with HTTPS and persistent storage, and back up the database and uploads.

This version takes order requests with manual payment confirmation. Automatic payments, email notifications, tracking integrations and shipping-label purchases are not connected. They require merchant/service accounts and additional integration. Do not use the decorative 3D yarn ball as a product representation.
