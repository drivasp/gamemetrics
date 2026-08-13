# GameMetrics Desktop (Fase 1–2)

Cliente Electron mínimo que:

1. Abre la tienda web (`http://localhost:4000/store`)
2. Intercepta **Instalar** / **Actualizar** para descargar el ZIP real al disco
3. Extrae el paquete en `%AppData%/gamemetrics-desktop/library/{product_id}/`
4. En **Jugar**, abre `index.html` del juego instalado
5. Expone `checkUpdate` (IPC) contra `GET /launcher/updates/{product_id}`

## Requisitos

- Stack Docker levantado (`.\inicio.ps1`)
- Backend con MinIO / storage local

## Arranque

```powershell
cd desktop
npm install
npm start
```

Variables opcionales:

```powershell
$env:GM_STORE_URL="http://localhost:4000/store"
$env:GM_API_URL="http://localhost:8080"
npm start
```
