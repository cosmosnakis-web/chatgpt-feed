# chatgpt-feed — DURUM

## 13.11.2026
- Depo: github.com/cosmosnakis-web/chatgpt-feed (public; içinde yalnız herkese açık ürün verisi)
- Feed URL: https://raw.githubusercontent.com/cosmosnakis-web/chatgpt-feed/main/feed/products.jsonl.gz
- GitHub Actions saatte bir feed.py çalıştırır (Storefront API, secret SHOPIFY_STOREFRONT_TOKEN), değişiklik varsa commit.
  meta.json günlük tarih taşır → her gün en az 1 commit, 60 gün hareketsizlikte cron kapanması önlenir.
- Feed: 89 ürün / 9.061 varyant satırı; zorunlu alan eksiği 0.
- ChatGPT Business Hub > Ürünler > Feeds: "cosmosnakis-urunler" (Hosted URL) kayıtlı. Güncelleme sıklığı Daily.
- Anahtarlar kök .env: GITHUB_TOKEN (fine-grained, yalnız bu repo, bitiş 12.01.2027), GITHUB_FEED_REPO, SHOPIFY_STOREFRONT_TOKEN.

## Açık
- GITHUB_TOKEN 12.01.2027'de biter (yalnız yerelden push için; Actions etkilenmez).
- target_countries/store_country gönderilmiyor; ChatGPT TR'yi reddederse eklenecek.
