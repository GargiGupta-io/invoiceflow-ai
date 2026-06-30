# Phase 15A: Floating Glass Header

> InvoiceFlow now has a ReactBits-inspired product header that stays available, shrinks on scroll, and makes the app feel more like a polished AI workflow product.

---

## In Plain English

The old header behaved like regular page text: it sat at the top, then disappeared once the user moved down the page. That made the product feel less guided because the main navigation was not always present.

This phase changes the header into a floating control bar. At the top of the page it feels open and quiet. Once the user scrolls, it tightens into a translucent glass pill with the brand, important tabs, and the AP/AR agent status. The effect is similar to the ReactBits reference: the navigation becomes part of the product personality instead of just a normal website header.

## What Changed

### Header Structure

Plain English: the top of the page now has a real product navigation bar.

`web/index.html` now wraps the brand, tabs, and system status in one `.site-header-inner` shell. The header includes:

- `Overview`
- `Cases`
- `Decision`
- `Evidence`
- `Review`
- `Evaluation`

The `Decision`, `Evidence`, `Review`, and `Evaluation` controls reuse the existing `data-tab-target` behavior, so they connect to the same workspace tabs already used by the app.

### Scroll State

Plain English: the page can now tell whether the viewer has scrolled far enough to make the header compact.

`web/app.js` adds:

```js
const siteHeader = document.querySelector(".site-header");
```

and:

```js
function syncHeaderState() {
  if (!siteHeader) {
    return;
  }
  siteHeader.classList.toggle("is-scrolled", window.scrollY > 28);
}
```

The header gets the `is-scrolled` class after a small amount of scroll. CSS then uses that class to shrink the header width, reduce padding, add a translucent background, and apply blur.

### Visual Styling

Plain English: the header now behaves like a soft floating control surface.

`web/styles.css` adds a final override block for:

- fixed centered positioning
- glass background after scroll
- smooth size and blur transitions
- pill-shaped section tabs
- soft hover highlights
- mobile wrapping behavior

The new styling keeps the existing InvoiceFlow palette instead of changing the brand direction.

## Why This Matters

The product now has a stronger first impression. The header makes the app feel like a real operator console because navigation is always available, section labels are clear, and the visual style is more intentional.

This also sets up the next creative UI phases. Once the header feels polished, the rest of the page can be organized around the same visual language: fewer scattered sentences, more intentional grouping, and a single product flow from upload to decision to audit.

## Verification

- `node --check web/app.js` passed.
- The local `/ui` endpoint served the updated header markup.
- Existing unrelated local files were left untouched.

