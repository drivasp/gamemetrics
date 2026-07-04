# Fase 3 — Checklist (Distribución digital)

## Tablas (+6) → Acumulado 36
- [x] fact_builds
- [x] fact_download_tokens
- [x] fact_install_states
- [x] fact_play_sessions
- [x] fact_achievements
- [x] fact_user_achievements

## Backend `/launcher`
- [x] GET /library-status
- [x] GET /game/{product_id}
- [x] POST /install/{product_id}
- [x] PATCH /install/{product_id}/progress
- [x] POST /uninstall/{product_id}
- [x] GET /download/{token_id}
- [x] POST /play/start
- [x] POST /play/end

## Frontend biblioteca
- [x] Instalar con barra de progreso animada
- [x] Overlay de sesión en juego + reloj
- [x] Panel de detalles y logros
- [x] Toast de logros desbloqueados
- [x] Desinstalar / reembolso conservado

## ETL
- [x] 14_create_phase3_tables.py
- [x] inicio.ps1 paso 6
