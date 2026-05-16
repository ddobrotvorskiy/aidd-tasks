# Solution Architecture: Распределённая система обработки задач

## 1. Обзор архитектуры

```
┌─────────────┐
│   Clients   │ (50k RPS)
└──────┬──────┘│
┌──────▼──────────────────┐
│  API Gateway (LB)       │← Rate limiting, routing
├─────────────────────────┤
│  - Nginx/HAProxy        │
│  - Circuit breaker      │
└──────┬──────────────────┘
       │
┌──────▼──────────────────────────┐
│  Message Queue (Event Bus)      │ ← At-least-once guarantee
├─────────────────────────────────┤
│  - Apache Kafka/RabbitMQ│
│  - Partitioned by task type     │
│  - Replication factor: 3        │
└──────┬──────────────────────────┘
       │
┌──────▼──────────────────────────────────────┐
│  Task Processing Workers (Horizontal)      │
├─────────────────────────────────────────────┤
│  - Worker Pool1, 2, 3... N │
│  - Consumer groups в Kafka                │
│  - Graceful shutdown, idempotency           │
└──────┬──────────────────────────────────────┘
       │
┌──────▼──────────────────────┐
│  Result Store│
├─────────────────────────────┤
│  - Redis (cache)│
│  - PostgreSQL (persistence) │
│  - TTL для результатов      │
└─────────────────────────────┘
```

## 2. Компоненты решения

### **API Gateway**
```yaml
Load Balancer:
  - Nginx/HAProxy (active-active)
  - Health checks каждые 5 сек
  - Timeout: 95ms (buffer для обработки)
  
Rate Limiting:
  - Token bucket: 50k RPS / количество инстансов
  - Per-client quotas
```

### **Message Queue (Kafka)**
```yaml
Конфигурация:
  partitions: 10-20 (scalability)
  replication_factor: 3 (reliability)
  min_insync_replicas: 2 (durability)
  
Topic settings:
  acks: all (гарантия доставки)
  compression: snappy
  retention: 24 hours
```

### **Worker Nodes**
```python
# Пример worker'а
from kafka import KafkaConsumer
import json
import logging

class TaskWorker:
    def __init__(self):
        self.consumer = KafkaConsumer(
            'tasks',
            group_id='workers',
            bootstrap_servers=['kafka:9092'],
            max_poll_records=100,
            session_timeout_ms=30000,
            heartbeat_interval_ms=10000
        )
        self.redis = Redis(host='redis', port=6379)
        
    def process(self):
        for message in self.consumer:
            try:
                task = json.loads(message.value)
                task_id = task['id']
                
                # Идемпотентность: проверяем дубликат
                if self.redis.exists(f"processed:{task_id}"):
                    logging.info(f"Task {task_id} already processed")
                    continue
                
                # Обработка задачи (< 100ms)
                result = self.execute_task(task)
                
                # Сохранение результата
                self.redis.setex(
                    f"result:{task_id}",
                    3600,  # TTL1 час
                    json.dumps(result)
                )# Отметить как обработано
                self.redis.setex(
                    f"processed:{task_id}",
                    86400,  # 24 часа для дедупликации
                    "1"
                )
                # Commit offset после успеха
                self.consumer.commit()
                
            except Exception as e:
                logging.error(f"Error processing task: {e}")
                # Retry логика или DLQ
                self.send_to_dlq(message)
    
    def execute_task(self, task):
        # Ваша бизнес-логика
        start = time.time()
        result = process_business_logic(task)
        elapsed = time.time() - start
        
        if elapsed > 100:
            logging.warning(f"Slow task: {elapsed*1000}ms")
        
        return result
```

## 3. Гарантии доставки (At-least-once)

```yaml
Producer side:
  acks: all                    # Ждём подтверждения от всех replicas
  retries: 3
  max_in_flight_requests: 5
  
Consumer side:
  enable_auto_commit: false   # Ручной commit
  isolation_level: read_committed
  
Идемпотентность:
  - Уникальный task_id
  - Redis для отслеживания обработанных
  - Версионирование результатов
```

## 4. Оптимизация latency < 100ms

```yaml
Сетевой уровень:
  - CDN для API Gateway
  - Connection pooling
  - Keep-alive connections
  - Compression (gzip)

Обработка:
  - Async I/O (asyncio/tokio)
  - Batch processing (макс 100 задач)
  - Кеширование (Redis)
  - Database indexing

Мониторинг:
  - P50:< 20ms
  - P95: < 80ms
  - P99: < 100ms
```

## 5. Горизонтальное масштабирование

```yaml
Auto-scaling:
  Metrics:
    - Queue lag (Kafka consumer lag)
    - CPU usage > 70%
    - Memory > 80%
  
  Actions:
    - Добавить worker nodes
    - Увеличить partitions в Kafka
    - Scale API Gateway

Kubernetes deployment:
  ---
  apiVersion: apps/v1
  kind: Deployment
  metadata:
    name: task-worker
  spec:
    replicas: 10# стартовое количество
    selector:
      matchLabels:
        app: task-worker
    template:
      spec:
        containers:
        - name: worker
          image: task-worker:latest
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 1000m
              memory: 1Gi
        
        # Graceful shutdown
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 15"]
  
  ---
  apiVersion: autoscaling/v2
  kind: HorizontalPodAutoscaler
  metadata:
    name: task-worker-hpa
  spec:
    scaleTargetRef:
      apiVersion: apps/v1
      kind: Deployment
      name: task-worker
    minReplicas: 10
    maxReplicas: 100
    metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: kafka_consumer_lag
        target:
          type: AverageValue
          averageValue: "1000"
```

## 6. Мониторинг и наблюдаемость

```yaml
Метрики:
  - Prometheus + Grafana
  - Kafka metrics (lag, throughput)
  - Worker metrics (processing time, errors)
  
Логирование:
  - ELK Stack (Elasticsearch, Logstash, Kibana)
  - Structured logging (JSON)
  
Трейсинг:
  - Jaeger для распределённого трейсинга
  - Trace ID через всю систему
```

## 7. Ключевые риски и решения

| Риск | Решение |
|------|---------|
| Потеря сообщений | Replication factor 3, acks=all |
| Дублирование обработки | Идемпотентные операции + Redis |
| Задержка > 100ms | Async processing, кеширование |
| Worker crashes | Graceful shutdown, rebalancing |
| Kafka bottleneck | Partitioning, увеличение replicas |

---

**Это production-ready архитектура**, готовая к 50k RPS с гарантиями. Нужны детали по конкретным компонентам?