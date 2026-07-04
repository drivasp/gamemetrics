# Fase 2 — Checklist de implementación (Tienda pro)

## Tablas nuevas (+8) → Acumulado 30

- [x] fact_user_wallets
- [x] fact_wallet_transactions
- [x] fact_gifts
- [x] fact_coupons
- [x] fact_coupon_redemptions
- [x] fact_wishlist_price_alerts
- [x] fact_review_votes
- [x] fact_user_events

## Backend
- [x] /wallet — saldo, recarga, historial
- [x] /coupons/validate — validar cupón
- [x] /checkout — payment_method wallet|sandbox|stripe + coupon_code
- [x] /gifts — enviar, inbox, sent, accept, decline
- [x] /alerts — alertas de precio wishlist
- [x] /reviews/votes/{id} — útil / no útil
- [x] /events — funnel analytics
- [x] Reembolsos acreditan cartera

## Frontend
- [x] /wallet — recarga y movimientos
- [x] /payment — cupón + método de pago (cartera / sandbox)
- [x] /gifts — recibidos / enviados
- [x] Detalle juego — regalo, alerta de precio, votos reseña
- [x] Navbar — saldo cartera + regalos

## ETL
- [x] 13_create_phase2_tables.py
- [x] 12_seed_coupons.py (STEAM10, GAME20, WELCOME5)
- [x] inicio.ps1 paso 5 bootstrap Fase 2

## Cupones demo
| Código | Tipo | Valor |
|--------|------|-------|
| STEAM10 | pct | 10% |
| GAME20 | pct | 20% |
| WELCOME5 | fixed | $5 |
