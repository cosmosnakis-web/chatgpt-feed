# chatgpt-feed

cosmosnakis.com ürünlerini ChatGPT Business Hub için JSONL.gz feed'ine çevirir.

- Feed URL: https://raw.githubusercontent.com/cosmosnakis-web/chatgpt-feed/main/feed/products.jsonl.gz
- GitHub Actions saatte bir (`:17`) `feed.py` çalıştırır; değişiklik varsa commit eder.
- Kaynak: Shopify Storefront API (`SHOPIFY_STOREFRONT_TOKEN` repo secret'ı, salt okuma).
- Spec: https://developers.openai.com/commerce/specs/file-upload/products
