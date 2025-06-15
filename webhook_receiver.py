from flask import Flask, request
import json
import requests
import os
from woocommerce import API

app = Flask(__name__)

# === WooCommerce config ===
wcapi = API(
    url="https://imperiopatitas.cl/",
    consumer_key="ck_417fa06639ffd13c3af85797d0ab5835dc708c1c",
    consumer_secret="cs_6f077418b4a0be3f4c3108ca275d7541fed1313f",
    version="wc/v3",
    timeout=20
)

# === Bsale config ===
BSALE_TOKEN = "f33bc19ae54eb12d58050f79ca22f105edd6bc32"
HEADERS = {"access_token": BSALE_TOKEN}
BASE_URL = "https://api.bsale.cl"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        print("📥 Webhook recibido:")
        print(json.dumps(data, indent=2))
    except Exception as err:
        print("❌ Error al leer JSON del webhook:", str(err))
        return {"status": "invalid json"}, 400

    with open("ultimo_webhook.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    try:
        doc_id = data.get("resourceId")
        if not doc_id:
            raise Exception("❌ resourceId no encontrado en el webhook")

        # Obtener el documento completo
        doc_url = "{}/v1/documents/{}.json".format(BASE_URL, doc_id)
        doc_data = requests.get(doc_url, headers=HEADERS).json()

        detalles_url = doc_data.get("details", {}).get("href")
        if not detalles_url:
            raise Exception("❌ No se encontró 'details.href' en el documento")

        detalles = requests.get(detalles_url, headers=HEADERS).json().get("items", [])

    except Exception as e:
        print("❌ Error al procesar el webhook:", str(e))
        return {"status": "error", "message": str(e)}, 500

    for item in detalles:
        variant_info = item.get("variant", {})
        sku = variant_info.get("code")

        # Si no viene el código, hacer una segunda llamada
        if not sku and "href" in variant_info:
            variant_url = variant_info["href"]
            variant_resp = requests.get(variant_url, headers=HEADERS).json()
            sku = variant_resp.get("code")

        qty_vendida = item.get("quantity", 0)

        if not sku:
            print("⚠️ Variante sin código. Saltando...")
            continue

        productos = wcapi.get("products", params={"sku": sku}).json()
        if not productos or isinstance(productos, dict) and productos.get("code") == "rest_product_invalid_sku":
            print("⚠️ SKU no encontrado en WooCommerce:", sku)
            continue

        producto = productos[0]
        stock_actual = producto.get("stock_quantity") or 0
        nuevo_stock = max(0, stock_actual - qty_vendida)

        update_data = {
            "stock_quantity": nuevo_stock,
            "manage_stock": True
        }

        wcapi.put("products/{}".format(producto["id"]), update_data)
        print("✅ Stock actualizado: SKU {} | {} → {}".format(sku, stock_actual, nuevo_stock))

    return {"status": "ok"}, 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
