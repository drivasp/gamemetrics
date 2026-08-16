FROM apache/airflow:2.10.4-python3.12

COPY requirements.txt /requirements.txt

# Pip resuelve dependencias contra el archivo de constraints oficial de Airflow
# para esta versión exacta: evita el clásico problema de incompatibilidad de
# versiones entre las libs propias del ETL (pandas/pyarrow/kafka-python) y las
# que ya trae Airflow instaladas internamente.
RUN pip install --no-cache-dir -r /requirements.txt \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.4/constraints-3.12.txt"
