# Ganjavores DC — Product Catalog Update Pattern

## CSV → SQL Workflow

When the user provides an updated product spreadsheet (e.g., `Cannabis_Product_Descriptions(Product Summary).csv`):

### Step 1: Parse the XLSX (September 2026 — XLSX replaces CSV)
- The user may provide either CSV or XLSX (`Cannabis_Product_Descriptions*.xlsx`).
- Use Python `openpyxl` to parse: `wb = openpyxl.load_workbook(path, data_only=True)`, `ws = wb['Product Summary']`.
- **Read raw cell values, not formulas** — `data_only=True` is critical.
- Columns (1-indexed): A=Product Name, B=Brand, C=Genetics, D=Strain Type, E=THC%, F=CBD, G=CBG, H=Terpene, I=Effects, J=Flavors, K=Aromas, L=Medical Benefits, M=Size, N=Category/Subtype, O=Price, P=Image URL, Q=Image File Name.
- **Price parsing**: Split by `|` into weight segments (e.g., `3.5g: $45 | 7g: $80`), then within each segment split by `:` to get weight and price. Strip `$` and whitespace.
- **XLSX brand names may differ from DB slugs**: "Cookies" brand has slug `cookies-dispensary`, "SKITTLEZ" is case-sensitive. See the Brand Slug Mapping table below. Always normalize brand names before lookup.
- **Some XLSX rows have duplicate product names** (e.g., "Blueberry Banana" appears twice). Deduplicate by checking the DB first.
- **Products with no image file name** will get a placeholder — skip insertion and log for manual review.
- **Edible THC values** may be total mg (e.g., 1500) not a percentage — handle accordingly.

### Step 2: Map XLSX Products to DB (Critical — XLSX IDs differ from seed SQL IDs)
- **DO NOT assume XLSX product IDs/slug values match existing SQL seed slugs.** The XLSX products may be entirely different entries.
- Map by **normalizing product names** (lowercase, strip parentheses, collapse spaces) and **brand name → DB slug**.
- For XLSX images: The "Image File Name" column gives a filename like `duct-tape.png` — map this to a storage path `flower/duct-tape.png` or `vapes/...png` based on the product's category.
- **Download images from XLSX "Image URL" column** to `public/products/{category}/` locally first, then upload to Supabase Storage.

### Step 3: Wipe and Re-insert from XLSX
- Since XLSX products may be entirely different from seed SQL products, **wipe the slate clean**:
  ```python
  supabase.table('product_images').delete().neq('id', '00000000-0000-0000-0000-000000000001').execute()
  supabase.table('product_variants').delete().neq('id', '00000000-0000-0000-0000-000000000001').execute()
  supabase.table('products').delete().neq('id', '00000000-0000-0000-0000-000000000001').execute()
  ```
- Then **insert all XLSX products as new rows**. This avoids slug-matching complexity entirely.
- Handle brand/category lookups inline: query `brands` and `categories` tables once, build slug→UUID dicts, use in insert.

### Step 4: Run Against Supabase

**CRITICAL: Cannot use `supabase db execute` on Windows — Docker is not available.**

Use these methods instead:

#### Method 1: Supabase Python REST Client (for scripted updates)
```python
from supabase import create_client
supabase = create_client(url, service_role_key)

# Delete ALL variants first (critical — FK constraints!)
supabase.table('product_variants').delete().neq('id', '00000000-0000-0000-0000-000000000001').execute()

# Delete variants for specific product
supabase.table('product_variants').delete().eq('product_id', pid).execute()

# Insert variants
supabase.table('product_variants').insert(variant_data).execute()

# Update products
supabase.table('products').update(fields).eq('id', pid).execute()
```

#### Method 2: Supabase Dashboard SQL Editor (for complex SQL)
- User opens Supabase Dashboard → SQL Editor → paste SQL → Run
- Most reliable for transactions and complex statements

#### Method 3: psycopg2 direct connection (usually fails with Supabase)
- Supabase uses certificate-based auth, not password auth
- `postgresql://postgres:{key}@db.{project}.supabase.co:5432/postgres` will fail with auth error

### Step 5: Verify
- Query product counts: `supabase.table('products').select('count', count='exact').execute()`
- Check variant counts per product
- Verify new products exist

## Brand Slug Mapping (Ganjavores DC)

| CSV Brand | DB Slug |
|-----------|---------|
| Ganjavores | ganjavores-by-lee-farms |
| Cookies | cookies-dispensary |
| Cookies Premium Flower | cookies-premium-flower |
| Muha Meds | muha-meds |
| Jeeter Juice | jeeter |
| Exotic Genetix | exotic-genetix |
| Gas Boys | gas-boys |
| Premium Flower | premium-flower |
| Jungle Boys | jungle-boys |
| Rythm | rythm |
| Loud Flower | loud-flower |
| Cultivation Labs | cultivation-labs |
| Faded Fruits | faded-fruits |
| Devour | devour |
| Friendly Farms | friendly-farms |
| Lemonnade | lemonnade |
| White Runtz | white-runtz |
| SKITTLEZ | skittlez |
| Wiz Khalifa | khalifa-kush |
| Cultivar Collection by Trulieve | cultivar-collection-by-trulieve |
| Khalifa Kush | khalifa-kush |
| Bargain Budd | bargain-budd |

## Product Category Mapping

| CSV Category | DB Slug |
|-------------|---------|
| Flower variants | flower |
| Pre-Rolls, Multi-Pack | pre-rolls |
| Vapes, Cartridge, Live Resin | vapes |
| Edibles, Gummies | edibles |
| Accessories, Grinder, Battery | accessories |
| Concentrates | concentrates |

## Key Pitfalls

1. **CSV product names ≠ DB slugs**: NEVER assume CSV names match DB slugs. The CSV has display names like "Duct Tape" but DB has slugs like "money-kush". Always map by comparing normalized product names against existing DB product names.

2. **DB slugs are authoritative**: The seed SQL files define the correct slugs. When generating SQL updates, use the DB slugs from seed files, not CSV-derived slugs. The pattern `('slug', 'Name', ...)` in seed files gives the authoritative mapping.

3. **Deleting variants first is critical**: Always `DELETE FROM product_variants` for a product before inserting new variants. Supabase foreign key constraints will cause errors if you try to insert without deleting first.

4. **Use `neq('id', '00000000-0000-0000-0000-000000000001')` to delete all variants**: This pattern works with Supabase REST client to clear all variant records before re-inserting. Do NOT use `eq('id', 0)` — UUID type errors will occur.

5. **The Supabase Python client CANNOT execute raw SQL**: Unlike pgAdmin or the SQL Editor, the Python REST client only supports CRUD operations on tables. For complex SQL (transactions, CREATE TABLE, etc.), use the SQL Editor or REST-based operations.

6. **Brand slugs differ from brand names**: "Cookies" brand has slug `cookies-dispensary`, not `cookies`. Always check the actual slug in the DB before referencing.

7. **New products need brand/category lookups**: When inserting new products, use `(SELECT id FROM brands WHERE slug = '{slug}')` to get brand IDs, and verify the brand exists first. If the brand doesn't exist, insert it first.

8. **Product variants must use product IDs, not slugs**: After inserting a new product, query `SELECT id FROM products WHERE slug = '...'` to get the UUID before inserting variants.

9. **The `execute_code` tool is essential for Python-based DB operations**: Use it to run Python scripts that interact with Supabase via the REST client. Avoid `terminal` for Python scripts that need environment variables.

10. **Check `.env.local` location**: Project may have `.env.local` in a sibling directory (e.g., `/c/Users/jorda/Downloads/ganjavores-dc/.env.local`). Copy it to the working project directory if needed.

11. **CSV price parsing is fragile**: Pipe-separated prices like `3.5g: $45 | 7g: $80` need careful splitting. Split by `|` first, then by `:` within each part. Strip `$` and whitespace from price values. Some rows have empty or "Not specified" prices.

12. **Product names in CSV vs DB don't match by slug**: The SQL seed file uses display names as slugs in some cases. Always map by comparing normalized product names, not slugs. Use a `normalize()` function that lowercases, strips parens, and collapses spaces.

13. **Duplicate product names across brands**: Products like "Blueberry Banana" can exist under different brands. Use distinct slugs (`blueberry-banana-cookies-premium-flower` vs `blueberry-banana`) to differentiate. Always check which brand variant already exists before inserting.

14. **Jeeter Juice multi-product brands**: Brands like Jeeter Juice have many products (flavors) sharing slug patterns (`jeeter-juice-live-resin-{flavor}`). When CSV names differ from SQL names, the SQL slug structure is authoritative.

15. **Edible products may have non-numeric THC**: Store as `thc_percent = 1500` (total mg) for edibles with high mg counts. Skip or use NULL for "Not specified" THC values.

16. **Deleting all products then re-inserting is the cleanest approach**: When the XLSX contains entirely different products from the seed SQL, wipe `product_images`, `product_variants`, and `products` in order (FK cascade), then insert all XLSX products fresh. Avoids slug-matching complexity.

17. **The `execute_code` tool has a 5-minute timeout**: Large SQL operations may timeout. Break operations into smaller batches if needed.

18. **Count queries with `.select('count')` return None unexpectedly**: The Supabase Python client's count feature is unreliable. Use `.select('id')` and `len(result.data)` to count rows instead:
   ```python
   products = supabase.table('products').select('id').execute()
   count = len(products.data)  # NOT .count
   ```

19. **Supabase Storage upload via REST API POST returns 400**: The `/storage/v1/object/public/{bucket}/` POST endpoint fails with "Bucket not found" even when the bucket exists. Use `bucket.create_signed_upload_url()` + `urllib.request` PUT to the returned `signedUrl` instead. The signed URL approach works reliably with status 200.

20. **The `product-card.tsx` uses `product.images[0]?.url` for display**: If images aren't linked to `product_images` table, the card shows placeholder. Verify images are in Supabase Storage AND linked via `product_images` records.
