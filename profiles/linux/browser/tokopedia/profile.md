# Tokopedia (web)

Profile for shopping on Tokopedia (tokopedia.com), an Indonesian marketplace, in
Chrome. Inherits `profiles/linux/browser/profile.md` (and the linux base).

## Terms & Vocab
- Search box — the wide field at the TOP of every Tokopedia page, placeholder "Cari di Tokopedia" ("Search on Tokopedia").
- Product card — one item tile in the results grid: image, title, PRICE, shop name + city, rating, sold count.
- Results grid — the product cards laid out in rows; a "row" is one HORIZONTAL line of cards (leftmost to rightmost at the same vertical level).
- Price — the bold Rupiah amount on a card, formatted "Rp" + digits with DOT thousands separators, e.g. "Rp1.250.000" = 1,250,000 rupiah (the dots are NOT decimals).
- Ad / Iklan label — a small badge marking a SPONSORED product.

## Visual
- You are looking at Tokopedia, an Indonesian e-commerce site (mostly Bahasa Indonesia).
- Search results are a GRID of Product cards. The FIRST ROW = the topmost horizontal line of cards (typically 4-6 cards across).
- Read a card's PRICE as the bold "Rp..." amount. If a card shows TWO prices, the CURRENT price is the BOLD, non-struck one; the struck-through ORIGINAL price is HIGHER (it's a discount) — never report the struck-through original as the price.
- "Rp1.250.000" means 1,250,000 rupiah — the dots are thousands separators, not decimal points.

## Operating
- To search: click the Search box at the top, type the product name (type_into), press Enter. Then wait for the results grid to load.
- The first product row may include Ad/Iklan (sponsored) cards — they are still results; read them as part of the first row unless told otherwise.
- To read the first row: identify the topmost horizontal line of cards, left-to-right, and read each card's Rp price.
- Report prices as plain integers of rupiah (strip "Rp" and the dot separators): "Rp1.250.000" -> 1250000.
