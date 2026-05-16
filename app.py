import os
import json
import re
import io
import pandas as pd
import anthropic
from flask import Flask, request, render_template, send_file
from dotenv import load_dotenv

from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

app = Flask(__name__)
client = anthropic.Anthropic()

SHOPIFY_COLUMNS = [
    "Handle", "Title", "Body (HTML)", "Vendor", "Type",
    "Tags", "Published", "Variant Price", "Variant Weight Unit",
    "SEO Title", "SEO Description"
]

def transform_product(raw_product: dict) -> dict:
    prompt = f"""You are a Shopify e-commerce and product copywriting expert.

Here is the raw supplier product data:
{json.dumps(raw_product, indent=2, ensure_ascii=False)}

Generate the following Shopify fields as JSON (and nothing else, no markdown):
{{
  "handle": "url-friendly-product-slug",
  "title": "Catchy SEO product title (max 70 chars)",
  "body_html": "<p>Premium 3-4 sentence description, customer-focused benefits, valid HTML</p>",
  "vendor": "inferred from context or 'Premium Brand'",
  "type": "Shopify product category",
  "tags": "tag1, tag2, tag3, tag4, tag5 (comma-separated)",
  "seo_title": "Optimized SEO title (max 60 chars)",
  "seo_description": "Meta description (max 160 chars, main benefit)"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON found: {text}")
    return json.loads(match.group())


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    file = request.files.get("csv_file")
    if not file:
        return "No file received.", 400

    df = pd.read_csv(file)
    products = df.to_dict(orient="records")

    # Safety limit: 100 products max per upload
    if len(products) > 100:
        return "Maximum 100 products per upload.", 400

    shopify_rows = [None] * len(products)  # pre-allocates order

    def process_one(args):
        index, product = args
        transformed = transform_product(product)
        return index, {
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
        }

    # 5 simultaneous Claude calls — respects Anthropic rate limits
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_one, (i, p)) for i, p in enumerate(products)]
        for future in as_completed(futures):
            index, row = future.result()
            shopify_rows[index] = row  # preserves original order

    output_df = pd.DataFrame(shopify_rows, columns=SHOPIFY_COLUMNS)
    output = io.StringIO()
    output_df.to_csv(output, index=False)
    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="shopify_import.csv"
    )


if __name__ == "__main__":
    app.run(debug=True)