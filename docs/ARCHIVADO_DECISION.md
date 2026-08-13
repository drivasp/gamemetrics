# `_archivado` — decisión operativa

Tras la auditoría y el blindaje financiero:

| Paquete | Decisión |
|---------|----------|
| wallet (Pinot SoT) | **NO reactivar** — peligroso vs ledger SQLite |
| checkout viejo | **BORRAR** en limpieza futura (activo es superset) |
| dashboard/games Java | **DEJAR** hasta migrar cortes faltantes a reports |
| pom.xml / cliente_pocketbase | **BORRAR** en limpieza futura |
| resto de copias | **BORRAR** tras `diff` puntual |

No se borró código en esta ejecución para evitar pérdida accidental.
