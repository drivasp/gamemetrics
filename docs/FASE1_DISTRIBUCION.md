# Fase 1 — Distribución digital (tipo Steam)

Objetivo: pasar de launcher **simulado** a **descarga + install + pago + cliente desktop** usable.

## Qué se implementó

| Pieza | Detalle |
|-------|---------|
| **MinIO** | Servicio `minio` en `docker-compose.yml` (API `:9002`, consola `:9001`) |
| **Builds reales** | `shared/storage.py` genera ZIP HTML jugable y lo guarda en MinIO o `/app/static/builds` |
| **Descarga** | `GET /launcher/download/{token}` entrega ZIP + header `X-Checksum-SHA256` |
| **Install real (web)** | Biblioteca descarga con progreso por bytes y verifica checksum (`POST .../verify`) |
| **Install real (desktop)** | Electron en `desktop/` escribe al disco, extrae ZIP y abre el juego |
| **Stripe en UI** | Opción “Stripe Checkout” en `/payment` (requiere `STRIPE_SECRET_KEY`) |
| **Idempotencia** | Header `Idempotency-Key` en checkout + clave determinista por carrito |

## Cómo probar

```powershell
cd C:\Users\USER\Documents\Game\gamemetrics
.\inicio.ps1
# o: docker compose up -d --build
```

1. Compra un juego (sandbox / wallet / Stripe).
2. Ve a **BIBLIOTECA** → **Instalar**.
3. Debe verse progreso real de descarga y mensaje de checksum OK.
4. **Jugar** inicia sesión en web; con Desktop abre `index.html` local.

### Desktop

```powershell
cd desktop
npm install
npm start
```

### Stripe

En `backend/.env`:

```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
FRONTEND_URL=http://localhost:4000
```

Luego reconstruye backend. En `/payment` elige **Stripe Checkout**.

MinIO console: http://localhost:9001 (user/pass: `gamemetrics` / `gamemetrics_secret`).

## Fuera de alcance (posteriores)

DRM fuerte, parches delta, anticheat.
