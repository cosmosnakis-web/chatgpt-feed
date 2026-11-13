"""cosmosnakis.com -> ChatGPT ürün feed'i (JSONL.gz).

Kaynak: Shopify Storefront API (SHOPIFY_STOREFRONT_TOKEN, salt okuma);
yoksa herkese açık /products.json (429 sınırına takılabilir).
Çıktı: feed/products.jsonl.gz  (varyant başına bir satır)
       feed/meta.json          (son üretim zamanı, sayılar)
Spec: https://developers.openai.com/commerce/specs/file-upload/products
"""
import gzip
import html
import io
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

SITE = "https://cosmosnakis.com"
BRAND = "Cosmos Nakış"
CURRENCY = "TRY"
OUT = Path(__file__).parent / "feed"
UA = "Mozilla/5.0 (compatible; cosmosnakis-feed/1.0)"

CATEGORY = {
    "Hoodie": "Apparel & Accessories > Clothing > Activewear > Sweatshirts",
    "Sweatshirt": "Apparel & Accessories > Clothing > Activewear > Sweatshirts",
    "T-Shirt": "Apparel & Accessories > Clothing > Shirts & Tops",
    "Bere": "Apparel & Accessories > Clothing Accessories > Hats",
    "Şapka": "Apparel & Accessories > Clothing Accessories > Hats",
    "Yastık": "Home & Garden > Decor > Throw Pillows",
    "Çanta": "Apparel & Accessories > Handbags, Wallets & Cases > Handbags",
    "Pano": "Home & Garden > Decor > Artwork",
    "Patch": "Arts & Entertainment > Hobbies & Creative Arts > Arts & Crafts > Embellishments & Trims > Appliques & Patches",
}


def get(url, tries=7):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # 429/ağ hatasında bekleyip yeniden dene
            if i == tries - 1:
                raise
            wait = 20 * (i + 1)
            ra = getattr(e, "headers", None) and e.headers.get("Retry-After")
            if ra and ra.isdigit():
                wait = max(wait, int(ra))
            print(f"tekrar {wait}s ({e})", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError("ulaşılamadı")


SF_QUERY = """query($after:String){ products(first:25, after:$after){
  pageInfo{ hasNextPage endCursor }
  nodes{ id handle title descriptionHtml productType
    options{ name } images(first:20){ nodes{ id url } }
    variants(first:250){ nodes{ id availableForSale price{amount} compareAtPrice{amount}
      selectedOptions{ name value } image{ id url } } } } } }"""


def num(gid):
    return gid.rsplit("/", 1)[-1]


def fetch_storefront(token):
    """Storefront API (salt okuma) -> /products.json ile aynı biçim."""
    out, after = [], None
    while True:
        body = json.dumps({"query": SF_QUERY, "variables": {"after": after}}).encode()
        for i in range(5):
            try:
                req = urllib.request.Request(f"{SITE}/api/2026-07/graphql.json", data=body, headers={
                    "X-Shopify-Storefront-Access-Token": token, "Content-Type": "application/json", "User-Agent": UA})
                with urllib.request.urlopen(req, timeout=60) as r:
                    d = json.loads(r.read().decode("utf-8"))
                if d.get("errors"):
                    raise RuntimeError(d["errors"])
                break
            except Exception as e:
                if i == 4:
                    raise
                print(f"tekrar ({e})", file=sys.stderr)
                time.sleep(15 * (i + 1))
        conn = d["data"]["products"]
        for n in conn["nodes"]:
            names = [o["name"] for o in n["options"]]
            variants = []
            for v in n["variants"]["nodes"]:
                sel = {o["name"]: o["value"] for o in v["selectedOptions"]}
                vals = [sel.get(nm) for nm in names] + [None] * 3
                variants.append({
                    "id": num(v["id"]), "available": v["availableForSale"],
                    "price": v["price"]["amount"],
                    "compare_at_price": (v.get("compareAtPrice") or {}).get("amount"),
                    "option1": vals[0], "option2": vals[1], "option3": vals[2],
                    "featured_image": {"src": v["image"]["url"]} if v.get("image") else None,
                })
            out.append({
                "id": num(n["id"]), "handle": n["handle"], "title": n["title"],
                "body_html": n["descriptionHtml"], "product_type": n["productType"],
                "options": [{"name": nm} for nm in names],
                "images": [{"id": num(i["id"]), "src": i["url"]} for i in n["images"]["nodes"]],
                "variants": variants,
            })
        if not conn["pageInfo"]["hasNextPage"]:
            return out
        after = conn["pageInfo"]["endCursor"]


def fetch_products():
    token = os.environ.get("SHOPIFY_STOREFRONT_TOKEN", "").strip()
    if token:
        return fetch_storefront(token)
    out, page = [], 1
    while True:
        batch = get(f"{SITE}/products.json?limit=250&page={page}")["products"]
        if not batch:
            return out
        out += batch
        page += 1
        time.sleep(3)


def plain(text, limit=5000):
    text = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", text or "", flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text).strip()
    return text[:limit]


def category(ptype, variant_text=""):
    for text in (variant_text, ptype):  # önce varyant (T-Shirt/Hoodie seçeneği), sonra ürün tipi
        for key, cat in CATEGORY.items():
            if key.lower() in (text or "").lower():
                return cat
    return "Apparel & Accessories > Clothing"


def money(v):
    return f"{float(v):.2f} {CURRENCY}"


def rows(products):
    for p in products:
        images = [i["src"] for i in p.get("images", [])]
        if not images:
            continue
        img_by_id = {i["id"]: i["src"] for i in p["images"]}
        desc = plain(p.get("body_html")) or p["title"]
        opt_names = [o["name"] for o in p["options"]]
        single = len(p["variants"]) == 1 and opt_names == ["Title"]
        for v in p["variants"]:
            vals = [v.get(f"option{i}") for i in (1, 2, 3)]
            vdict = {n: val for n, val in zip(opt_names, vals) if val and n != "Title"}
            img = (v.get("featured_image") or {}).get("src") or img_by_id.get(v.get("image_id")) or images[0]
            title = p["title"] if single or not vdict else f"{p['title']} - {' / '.join(vdict.values())}"
            r = {
                "item_id": str(v["id"]),
                "title": title[:150],
                "description": desc,
                "url": f"{SITE}/products/{p['handle']}" + ("" if single else f"?variant={v['id']}"),
                "brand": BRAND,
                "seller_name": BRAND,
                "seller_url": SITE,
                "image_url": img,
                "availability": "in_stock" if v.get("available") else "out_of_stock",
                "condition": "new",
                "product_category": category(p.get("product_type"), " ".join(vdict.values())),
                "return_policy": f"{SITE}/policies/refund-policy",
                "is_eligible_search": True,
            }
            extra = [i for i in images if i != img][:10]
            if extra:
                r["additional_image_urls"] = extra
            cap = v.get("compare_at_price")
            if cap and float(cap) > float(v["price"]) > 0:
                r["price"], r["sale_price"] = money(cap), money(v["price"])
            else:
                r["price"] = money(v["price"])
            if not single:
                r["group_id"] = f"g{p['id']}"
                r["listing_has_variations"] = True
                r["variant_dict"] = vdict
                for n, val in vdict.items():
                    low = n.lower()
                    if "renk" in low:
                        r["color"] = val
                    elif "beden" in low or "boyut" in low:
                        r["size"] = val
            yield r


def per_product(rows_iter):
    """Varyant satırlarını ürün başına teke indir (ChatGPT 9 bin satırda 500 veriyordu, 13.11).
    İlk stoktaki varyant (sayfanın varsayılanı) temsilci olur; renk/beden seçenekleri açıklamaya eklenir."""
    groups = {}
    for r in rows_iter:
        groups.setdefault(r.get("group_id") or r["item_id"], []).append(r)
    for gid, rs in groups.items():
        live = [r for r in rs if r["availability"] == "in_stock"] or rs
        pick = live[0]  # ürün sayfasının varsayılan gösterdiği (ilk stoktaki) varyant → fiyat sayfayla aynı
        r = {k: v for k, v in pick.items()
             if k not in ("group_id", "listing_has_variations", "variant_dict", "color", "size")}
        r["item_id"] = gid.lstrip("g")
        r["url"] = r["url"].split("?")[0]
        r["title"] = r["title"].split(" - ")[0][:150] if len(rs) > 1 else r["title"]
        opts = {}
        for x in rs:
            for k, v in (x.get("variant_dict") or {}).items():
                opts.setdefault(k, [])
                if v not in opts[k]:
                    opts[k].append(v)
        if opts:
            extra = "\n".join(f"{k}: {', '.join(v)}" for k, v in opts.items())
            r["description"] = (r["description"] + "\nSeçenekler:\n" + extra)[:5000]
        yield r


def main():
    products = fetch_products()
    if len(products) < 10:  # Shopify geçici boş/eksik dönerse eski feed'i bozma
        sys.exit(f"Şüpheli az ürün ({len(products)}), feed güncellenmedi.")
    lines = [json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in per_product(rows(products))]
    ids = [json.loads(l)["item_id"] for l in lines]
    if len(set(ids)) != len(ids):
        sys.exit("Tekrarlanan item_id var, feed güncellenmedi.")
    data = ("\n".join(lines) + "\n").encode("utf-8")
    OUT.mkdir(exist_ok=True)
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:  # mtime=0: içerik aynıysa dosya da aynı
        gz.write(data)
    (OUT / "products.jsonl.gz").write_bytes(buf.getvalue())
    now = datetime.now(timezone(timedelta(hours=3)))
    meta = {"date": now.strftime("%Y-%m-%d"), "products": len(products), "rows": len(lines)}
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(meta)


if __name__ == "__main__":
    main()
