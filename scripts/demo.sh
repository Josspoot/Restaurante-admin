#!/usr/bin/env bash
# Demo del flujo completo contra la API ya levantada.
# Uso:  ./scripts/demo.sh [puerto]
set -euo pipefail

PUERTO="${1:-8000}"
API="http://127.0.0.1:${PUERTO}/api/v1"
json() { python3 -c "import sys,json;print(json.load(sys.stdin)$1)"; }

echo "==> Salud"
curl -sf "$API/salud" || { echo "La API no responde en el puerto $PUERTO"; exit 1; }
echo

echo "==> Login como mesero"
TOKEN=$(curl -s -X POST "$API/auth/login-json" \
  -H 'Content-Type: application/json' \
  -d '{"email":"mesero@restaurante.com","password":"mesero123"}' | json "['access_token']")
AUTH=(-H "Authorization: Bearer $TOKEN")
echo "token obtenido"

echo "==> Menú disponible"
curl -s "$API/productos?disponible=true&limit=5" \
  | python3 -c "import sys,json;[print(' ',p['id'],p['nombre'],'\$'+p['precio']) for p in json.load(sys.stdin)]"

echo "==> Crear orden (mesa 7)"
ORDEN=$(curl -s -X POST "$API/ordenes" "${AUTH[@]}" -H 'Content-Type: application/json' \
  -d '{"tipo":"LOCAL","mesa":7,"items":[{"producto_id":4,"cantidad":2},{"producto_id":9,"cantidad":2,"notas":"sin hielo"}]}')
ID=$(echo "$ORDEN" | json "['id']")
TOTAL=$(echo "$ORDEN" | json "['total']")
echo "  orden $(echo "$ORDEN" | json "['numero']")  total \$$TOTAL"

echo "==> Avanzar en cocina"
for ESTADO in EN_PREPARACION LISTA ENTREGADA; do
  curl -s -X PATCH "$API/ordenes/$ID/estado" "${AUTH[@]}" -H 'Content-Type: application/json' \
    -d "{\"estado\":\"$ESTADO\"}" | json "['estado']" | sed 's/^/  /'
done

echo "==> Cobrar completo con propina"
curl -s -X POST "$API/ordenes/$ID/pagos" "${AUTH[@]}" -H 'Content-Type: application/json' \
  -d "{\"metodo\":\"TARJETA\",\"monto\":\"$TOTAL\",\"propina\":\"50.00\",\"referencia\":\"AUTH-0001\"}" \
  | json "['pagada']" | sed 's/^/  pagada: /'

echo "==> Factura"
curl -s "$API/ordenes/$ID/factura" "${AUTH[@]}" | python3 -m json.tool
