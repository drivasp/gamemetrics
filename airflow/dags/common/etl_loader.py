"""
Carga módulos del ETL existente (etl/00…25_*.py) sin duplicar su código.

Los archivos empiezan con dígitos ("04_ingest_pinot.py"), así que no se
pueden `import` como identificador normal de Python -- se cargan por ruta
con importlib. Los DAGs llaman a las funciones ya factorizadas dentro de
esos scripts (prepare_dataframe, apply_variation, ingest_dataframe, etc.)
en vez de reescribir su lógica.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from types import ModuleType

ETL_SRC_DIR = os.getenv("ETL_SRC_DIR", "/opt/airflow/etl_src")

_cache: dict[str, ModuleType] = {}


def load_etl_module(filename: str) -> ModuleType:
    """Ej.: load_etl_module("04_ingest_pinot.py") -> módulo importado, con
    __file__ apuntando dentro de ETL_SRC_DIR. Cachea por nombre de archivo."""
    if filename in _cache:
        return _cache[filename]

    path = os.path.join(ETL_SRC_DIR, filename)
    modname = "etl_" + filename[:-3].replace(".", "_")
    spec = importlib.util.spec_from_file_location(modname, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar módulo ETL: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[modname] = module
    spec.loader.exec_module(module)
    _cache[filename] = module
    return module
