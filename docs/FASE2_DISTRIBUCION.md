# Fase 2 — Distribución (post-Fase 1)

Extiende la Fase 1 con **updates**, **cloud saves**, **presence** de amigos y **publisher upload** de builds. Sin DRM fuerte.

## Qué se implementó

| Pieza | Detalle |
|-------|---------|
| **Updates** | `GET /launcher/updates/{id}` · `POST /launcher/install/{id}/update` · botón **Actualizar** en biblioteca |
| **Cloud saves** | Tabla `fact_cloud_saves` + MinIO `saves/{user}/{product}/slot_n.json` · API `/saves` · panel en Detalles |
| **Presence** | `POST /friends/presence` · puntos online/away/offline en Amigos · heartbeat navbar cada 45s |
| **Publisher upload** | `POST /partners/games/{id}/builds` (ZIP multipart) · UI en `/my-partner` |
| **Desktop** | IPC `checkUpdate` en Electron |

## Cómo probar

```powershell
cd C:\Users\USER\Documents\Game\gamemetrics
docker compose up -d --build backend frontend etl-api
# crear tabla cloud saves (una vez):
docker compose exec etl-api python 17_create_cloud_saves_table.py
# o:
# Invoke-RestMethod -Method Post http://localhost:5000/etl/create-cloud-saves-table
```

1. **Update:** Publisher sube ZIP nuevo en `/my-partner` → en Biblioteca aparece **Actualizar**.
2. **Cloud save:** Detalles del juego → Guardar/Cargar slots 0–2.
3. **Presence:** Dos cuentas amigas → el amigo con sesión abierta muestra punto verde **En línea**.
4. **Upload:** Registrar publisher → añadir `product_id` → Subir ZIP + versión.

### E2E

```powershell
cd e2e
npm run test:fase2
```

## Fuera de alcance

DRM fuerte, actualizaciones delta, sync en tiempo real tipo Steam Cloud completo.
