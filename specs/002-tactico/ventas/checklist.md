# Checklist de Validación — Ventas y Marketing

## Fórmula de precio
- [ ] `calc_price(0, 0)` retorna `0.0`
- [ ] `calc_price(4.5, 92)` retorna `72.8`
- [ ] `calc_price(0.1, 0)` retorna `1.99` (precio mínimo)
- [ ] `is_free` es `True` solo cuando `price == 0.0`

## Colecciones empresariales
- [ ] `campanas_marketing` está en VALID_COLLECTIONS
- [ ] `catalogo_distribucion` está en VALID_COLLECTIONS
- [ ] `evaluaciones_analiticas` está en VALID_COLLECTIONS
- [ ] CRUD funciona para las 3 colecciones

## UI
- [ ] Juegos con precio $0.00 muestran etiqueta "GRATIS"
- [ ] El filtro `price_filter=free` filtra correctamente
