FROM python:3.11-slim
WORKDIR /etl
ENV PINOT_CONTROLLER=http://pinot-controller:9000 \
    PINOT_BROKER_URL=http://pinot-broker:8099 \
    KAFKA_BOOTSTRAP_SERVERS=kafka:9092
RUN pip install --no-cache-dir flask pandas pyarrow requests numpy kafka-python
COPY . .
EXPOSE 5000
CMD ["python", "etl_server.py"]
