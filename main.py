import re
import os
import json
import pandas as pd
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()  # Lit ANTHROPIC_API_KEY automatiquement

SHOPIFY_COLUMNS = [
    "Handle", "Title", "Body (HTML)", "Vendor", "Type",
    "Tags", "Published", "Variant Price", "Variant Weight Unit",
    "SEO Title", "SEO Description"
]

def transform_product(raw_product: dict) -> dict:
    prompt = f"""Tu es un expert en e-commerce Shopify et copywriting produit.
  
Voici les données brutes d'un produit fournisseur :
{json.dumps(raw_product, indent=2, ensure_ascii=False)}

Génère les champs Shopify suivants en JSON (et rien d'autre, pas de markdown) :
{{
  "handle": "slug-url-friendly-du-produit",
  "title": "Titre produit accrocheur et SEO (max 70 chars)",
  "body_html": "<p>Description premium 3-4 phrases, bénéfices centrés client, HTML valide</p>",
  "vendor": "déduit du contexte ou 'Premium Brand'",
  "type": "catégorie produit Shopify",
  "tags": "tag1, tag2, tag3, tag4, tag5 (séparés par virgules)",
  "seo_title": "Titre SEO optimisé (max 60 chars)",
  "seo_description": "Meta description (max 160 chars, bénéfice principal)"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()

    # 🔧 Fix : extrait le JSON même si Claude ajoute du markdown autour
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        raise ValueError(f"❌ Aucun JSON trouvé pour le produit : {raw_product.get('product_name')}\nRéponse brute : {text}")
    
    return json.loads(match.group())

def main():
    df = pd.read_csv("supplier.csv")
    products = df.to_dict(orient="records")

    print(f"📦 {len(products)} produits à transformer...\n")

    shopify_rows = []

    for product in products:
        print(f"⚙️  Traitement : {product.get('product_name', 'Inconnu')}")
        transformed = transform_product(product)
        shopify_rows.append({
            "Handle":               transformed["handle"],
            "Title":                transformed["title"],
            "Body (HTML)":          transformed["body_html"],
            "Vendor":               transformed["vendor"],
            "Type":                 transformed["type"],
            "Tags":                 transformed["tags"],
            "Published":            "true",
            "Variant Price":        product.get("price", ""),
            "Variant Weight Unit":  "kg",
            "SEO Title":            transformed["seo_title"],
            "SEO Description":      transformed["seo_description"],
        })

    output_df = pd.DataFrame(shopify_rows, columns=SHOPIFY_COLUMNS)
    output_df.to_csv("shopify_import.csv", index=False)

    print("\n✅ Fichier shopify_import.csv généré !")
    print(f"📊 {len(shopify_rows)} produits prêts à importer dans Shopify.")

if __name__ == "__main__":
    main()