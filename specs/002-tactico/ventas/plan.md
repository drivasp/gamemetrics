# Plan Técnico — Ventas y Marketing

## Tablas Pinot utilizadas
- **emp_records** (REALTIME): colecciones `campanas_marketing`, `catalogo_distribucion`, `evaluaciones_analiticas`
- **fact_videogames** (OFFLINE): fuente de `rating` y `metacritic` para cálculo de precio

## Implementación de precio
Archivo: `backend/store/calcular_precio.py`
```python
def calc_price(rating: float, metacritic: float) -> float:
    if rating == 0.0 and metacritic == 0.0:
        return 0.0
    return round(max(1.99, (rating * 8) + (metacritic * 0.4)), 2)
```

## Endpoints relevantes
- Heredados de `empresa/endpoints.py` para colecciones: `campanas_marketing`, `catalogo_distribucion`, `evaluaciones_analiticas`
- `store/listar_juegos.py` y `store/detalle_juego.py` aplican `calc_price()` a cada juego

## Componentes Angular
- `EmpresaComponent` — gestiona todas las colecciones incluyendo las de ventas
