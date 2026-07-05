# Índice de documentación — GameMetrics S.A.

Documentación para entrega académica (TA/GA), video demostrativo y evolución del repositorio.

**Repositorio:** https://github.com/drivasp/gamemetrics

---

## Documentos principales

| # | Archivo | Contenido | Uso |
|---|---------|-----------|-----|
| 1 | [DISENO_BASE_DATOS.md](./DISENO_BASE_DATOS.md) | Modelo de 50 tablas Pinot, diagramas, matriz ETL/Backend/UI | Video § BD · Word § Diseño |
| 2 | [DIAGRAMA_CASOS_DE_USO_GENERAL.md](./DIAGRAMA_CASOS_DE_USO_GENERAL.md) | Diagrama general por paquetes, catálogo CU-E/T/O | Word § UML general |
| 3 | [DOCUMENTO_CASOS_DE_USO_OPERATIVOS.md](./DOCUMENTO_CASOS_DE_USO_OPERATIVOS.md) | Especificación GA07 por paquete operativo | Word § Especificaciones |
| 4 | [CASOS_DE_USO.md](./CASOS_DE_USO.md) | Historias de usuario paso a paso (demo/video) | Guion del video |

---

## Referencias en el repo

| Ruta | Descripción |
|------|-------------|
| `specs/003-operativo/` | Specs detalladas auth, tienda, wishlist, carrito, biblioteca, reseñas |
| `specs/004-plataforma-pinot-steam/` | Diseño plataforma 50 tablas |
| `etl/pinot_schemas/` | Schemas JSON de las 50 tablas |
| `openspec/config.yaml` | Constitución y principios P1–P6 |

---

## Cómo pasar a Word

1. Abrir cada `.md` en GitHub o VS Code.
2. Copiar secciones a Word respetando títulos (`#` → Título 1, `##` → Título 2).
3. Exportar diagramas Mermaid desde [mermaid.live](https://mermaid.live) como PNG e insertarlos.
4. Complementar con capturas del sistema en `http://localhost:4200`.

---

## Autor

Rivas Piloso Dayver Yhair — GameMetrics S.A. · UTQ · Construcción de Software
