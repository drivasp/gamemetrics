FROM python:3.11-slim
WORKDIR /etl
RUN pip install --no-cache-dir flask pandas pyarrow requests numpy kafka-python
COPY . .
EXPOSE 5000
CMD ["python", "etl_server.py"]
