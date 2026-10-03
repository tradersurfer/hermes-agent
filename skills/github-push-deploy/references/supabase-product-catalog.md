# Supabase Product Catalog Operations

## Overview

Bulk-updating a Next.js + Supabase product catalog from an XLSX spreadsheet. Used for cannabis dispensary product imports.

## Setup

```python
from supabase import create_client
import openpyxl, re

env_content = open('.env.local').read()
env_vars = {}
for line in env_content.strip().split('\n'):
    if '=' in line:
        k, v = line.split('=', 1)
        env_vars[k] = v.replace('\r', '')

supabase = create_client(env_vars['NEXT_PUBLIC_SUPABASE_URL'], env_vars['SUPABASE_SERVICE_ROLE_KEY'])
```

## Critical Constraints

### `products_strain_type_check`
- `strain_type` CANNOT be NULL
- Must be one of: `'Indica'`, `'Sativa'`, `'Hybrid'`
- Always set explicitly, even as a default fallback
- If XLSX has `strain_type = ''` or `None`, default to `'Hybrid'` or infer from product name

### `thc_percent` Precision
- Column has precision 5,2 (max value < 1000)
- Values like 1500 (from "1500mg" THC in edibles) cause `numeric field overflow`
- Edibles/vapes: store THC as NULL, not the mg value
- Flower products: store actual THC percentage (e.g., 25.0)

### UUID Fields
- `brand_id`, `category_id`, `product_id` must be passed as **strings**
- Passing dicts or objects causes `invalid input syntax for type uuid` errors
- Always do: `str(brand_id)`, `str(category_id)`, `str(product_id)`

## Brand Slug Mapping

XLSX brand names differ from DB brand slugs. Map them:

```python
brand_mappings = {
    'ganjavores': 'ganjavores-by-lee-farms',
    'exotic genetix': 'exotic-genetix',
    'cookies': 'cookies-dispensary',
    'cookies premium flower': 'cookies-dispensary',
    'muha meds': 'muha-meds',
    'jeeter juice': 'jeeter',
    'rythm': 'rythm',
    'devour': 'devour',
    'friendly farms': 'friendly-farms',
    'faded fruits': 'faded-fruits',
    'loud flower': 'loud-flower',
    'jungle boys': 'jungle-boys',
    'cultivation labs': 'cultivation-labs',
    'cultivar collection by trulieve': 'cultivar-collection-by-trulieve',
    'bargain budd': 'bargain-budd',
    'white runtz': 'white-runtz',
    'skittlez': 'skittlez',
    'lemonnade': 'lemonnade',
    'premium flower': 'premium-flower',
    'archive seed bank': 'archive-seed-bank',
    'puff palace': 'puff-palace',
    'connected cannabis co': 'connected-cannabis-co',
    'wiz khalifa': 'wiz-khalifa',
}
```

## Variant Parsing

XLSX price format varies:
- **Multi-variant:** `"3.5g: $45 | 7g: $80 | 14g: $140 | 28g: $190"`
- **Single price:** `"$55.00"` → becomes `{"each": 55.0}`
- **Number:** `"65"` → becomes `{"each": 65.0}`

```python
variants = {}
if ':' in price_str:
    for part in price_str.split('|'):
        part = part.strip()
        if ':' in part:
            label, price = part.split(':', 1)
            label = label.strip()
            try:
                price_val = float(price.strip().replace('$', '').strip())
                if label not in variants:
                    variants[label] = price_val
            except:
                pass
elif price_str.startswith('$'):
    try:
        variants['each'] = float(price_str.replace('$', '').strip())
    except:
        pass
elif price_str.replace('.', '').isdigit():
    try:
        variants['each'] = float(price_str)
    except:
        pass
```

## Upsert Pattern

```python
# Check if product exists
existing = supabase.table('products').select('id').eq('slug', slug).execute()
if existing.data:
    pid = existing.data[0]['id']
    supabase.table('products').update(update_data).eq('id', pid).execute()
else:
    supabase.table('products').insert(insert_data).execute()
```

## Variant Management

Delete all variants then re-insert to avoid duplicates:
```python
all_vars = supabase.table('product_variants').select('id').execute()
for v in all_vars.data:
    supabase.table('product_variants').delete().eq('id', v['id']).execute()
```

## Google Drive Image Download

```python
file_id = url.split('/d/')[1].split('/')[0]
download_url = f"https://drive.google.com/uc?id={file_id}"
req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, timeout=15)
with open(save_path, 'wb') as f:
    f.write(resp.read())
```

## Category Determination

```python
cat_slug = 'flower'
cat_lower = str(category).lower()
if 'vape' in cat_lower:
    cat_slug = 'vapes'
elif 'edible' in cat_lower:
    cat_slug = 'edibles'
elif 'pre-roll' in cat_lower:
    cat_slug = 'pre-rolls'
```
