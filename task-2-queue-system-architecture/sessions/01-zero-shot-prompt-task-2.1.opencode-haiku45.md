# New session - 2026-04-18T04:39:12.591Z

**Session ID:** ses_2611d4430ffeoy3hyAqHlR3np7
**Created:** 4/18/2026, 11:39:12 AM
**Updated:** 4/18/2026, 11:45:39 AM

---

## User

Ты solution architect. 
Задача: Нужно спроектировать распределённую систему обработки задач
требованиями: 50,000 RPS, гарантия доставки (at-least-once), latency < 100ms, горизонтальное масштабирование. 

---

## Assistant (Build · anthropic/claude-haiku-4.5 · 6.3s)

Я помогу вам спроектировать распределённую систему обработки задач. Давайте создадим детальную архитектуру, учитывая все требования.

**Tool: todowrite**

**Input:**
```json
{
  "todos": [
    {
      "content": "Определить компоненты архитектуры и технологический стек",
      "status": "in_progress",
      "priority": "high"
    },
    {
      "content": "Спроектировать схему обработки с гарантией доставки",
      "status": "pending",
      "priority": "high"
    },
    {
      "content": "Разработать стратегию масштабирования и балансировки",
      "status": "pending",
      "priority": "high"
    },
    {
      "content": "Спроектировать мониторинг и отказоустойчивость",
      "status": "pending",
      "priority": "medium"
    },
    {
      "content": "Создать примеры конфигурации и кода",
      "status": "pending",
      "priority": "medium"
    }
  ]
}
```

**Output:**
```
[
  {
    "content": "Определить компоненты архитектуры и технологический стек",
    "status": "in_progress",
    "priority": "high"
  },
  {
    "content": "Спроектировать схему обработки с гарантией доставки",
    "status": "pending",
    "priority": "high"
  },
  {
    "content": "Разработать стратегию масштабирования и балансировки",
    "status": "pending",
    "priority": "high"
  },
  {
    "content": "Спроектировать мониторинг и отказоустойчивость",
    "status": "pending",
    "priority": "medium"
  },
  {
    "content": "Создать примеры конфигурации и кода",
    "status": "pending",
    "priority": "medium"
  }
]
```

---

## Assistant (Build · anthropic/claude-haiku-4.5 · 26.2s)

## 📋 Архитектура распределённой системы обработки задач

### 1. **Технологический стек**

```
┌─────────────────────────────────────────────────────────────┐
│                         API Gateway                          │
│        (Kong/Ambassador + Load Balancer - Nginx)             │
└────────────┬────────────────────────────────────────────────┘
             │
    ┌────────┼────────┐
    ▼        ▼        ▼
┌────────┐┌────────┐┌────────┐
│Producer│Producer│Producer│  × N instances
└────┬───┘└────┬───┘└────┬───┘
     │         │         │
     └─────────┼─────────┘
               ▼
     ┌──────────────────────┐
     │  Message Broker      │
     │  (Kafka / RabbitMQ)  │
     │  - 50K RPS capacity  │
     │  - Partitioning      │
     └──────────┬───────────┘
                │
    ┌───────────┼───────────┐
    ▼           ▼           ▼
┌────────┐ ┌────────┐ ┌────────┐
│Worker 1│ │Worker 2│ │Worker N│  × M instances
│(Kafka  │ │(Kafka  │ │(Kafka  │
│Consumer)│ │Consumer)│ │Consumer)│
└────┬───┘ └────┬───┘ └────┬───┘
     │         │         │
     └─────────┼─────────┘
               ▼
     ┌──────────────────────┐
     │  State Store         │
     │  (PostgreSQL/Redis)  │
     │  - Task State        │
     │  - Idempotency Keys  │
     └──────────────────────┘
```

**Рекомендуемый стек:**
- **API Gateway:** Envoy Proxy / Kong (обработка коннекций)
- **Message Broker:** Apache Kafka (лучше для 50K RPS, гарантия доставки)
- **State Store:** PostgreSQL (для гарантии AT-LEAST-ONCE) + Redis (кеш)
- **Orchestration:** Kubernetes (горизонтальное масштабирование)
- **Monitoring:** Prometheus + Grafana + ELK

---

### 2. **Гарантия доставки (AT-LEAST-ONCE)**

```
Механизм обработки:

1. ПРИЁМ ЗАДАЧИ (Producer):
   ├─ Сохранить в DB (транзакция):
   │  ├─ Статус: PENDING
   │  ├─ Idempotency Key: UUID
   │  └─ Timestamp: NOW()
   └─ Отправить в Kafka (при успехе сохранения)

2. ОБРАБОТКА ЗАДАЧИ (Worker):
   ├─ Получить сообщение из Kafka
   ├─ Проверить Idempotency Key в DB
   ├─ Если обработано ✓ → вернуть результат (уже сохранён)
   ├─ Если обработано ✗ → обработать задачу
   ├─ Сохранить результат в DB (транзакция)
   │  ├─ Статус: COMPLETED
   │  └─ Result: {...}
   └─ Commit offset в Kafka

3. ГАРАНТИЯ:
   ├─ Если worker упадёт после Kafka commit → задача уже в DB ✓
   ├─ Если worker упадёт до DB сохранения → Kafka переотправит ✓
   └─ Если duplicate request → Idempotency Key предотвратит ✓
```

---

### 3. **Стратегия масштабирования для 50K RPS**

**Расчёты:**
```
50,000 RPS ÷ 1,000 RPS (per worker) = 50 workers минимум
Для redundancy/peaks: 100-150 workers

Kafka partitions:
├─ Партиции ≈ 50-100 (для параллелизма)
└─ Replication Factor = 3 (HA)

Throughput per partition:
├─ Kafka: 1-2 MB/s → ~10K msg/s (100 bytes/msg)
├─ Для 50K RPS: 5 партиций × 10K = 50K RPS ✓
```

**Конфигурация Kafka (docker-compose):**

```yaml
version: '3.8'

services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_SYNC_LIMIT: 2
      ZOOKEEPER_INIT_LIMIT: 5

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on:
      - zookeeper
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 3
      KAFKA_NUM_NETWORK_THREADS: 32
      KAFKA_NUM_IO_THREADS: 32
      KAFKA_SOCKET_RECEIVE_BUFFER_BYTES: 102400
      KAFKA_SOCKET_REQUEST_MAX_BYTES: 104857600
    ports:
      - "9092:9092"
```

---

### 4. **Реализация Producer (Node.js/Python)**

```python
# producer.py - Гарантированная отправка
import uuid
import json
from datetime import datetime
from kafka import KafkaProducer
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database model
Base = declarative_base()

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(String, primary_key=True)
    idempotency_key = Column(String, unique=True, index=True)
    status = Column(String)
    payload = Column(String)
    created_at = Column(DateTime)

# Producer setup
producer = KafkaProducer(
    bootstrap_servers=['kafka:9092'],
    acks='all',  # Все replicas должны подтвердить
    retries=3,
    max_in_flight_requests_per_connection=1,  # Порядок сохранения
    compression_type='snappy'
)

engine = create_engine('postgresql://user:pass@db:5432/tasks')
Session = sessionmaker(bind=engine)

def submit_task(task_data: dict) -> str:
    """
    Отправить задачу с гарантией доставки
    """
    session = Session()
    idempotency_key = str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    
    try:
        # 1. Сохранить в БД
        task = Task(
            id=task_id,
            idempotency_key=idempotency_key,
            status='PENDING',
            payload=json.dumps(task_data),
            created_at=datetime.utcnow()
        )
        session.add(task)
        session.commit()
        
        # 2. Отправить в Kafka
        message = {
            'task_id': task_id,
            'idempotency_key': idempotency_key,
            'payload': task_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        future = producer.send(
            'tasks-topic',
            key=task_id.encode(),
            value=json.dumps(message).encode(),
            partition=hash(task_id) % 50  # Consistent partitioning
        )
        
        # Ждём подтверждение
        record_metadata = future.get(timeout=10)
        print(f"Task sent to partition {record_metadata.partition}")
        
        return task_id
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
```

---

### 5. **Реализация Worker (Consumer)**

```python
# worker.py - Consumer с гарантией обработки
import json
from kafka import KafkaConsumer
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, and_
from datetime import datetime, timedelta

engine = create_engine('postgresql://user:pass@db:5432/tasks')
Session = sessionmaker(bind=engine)

consumer = KafkaConsumer(
    'tasks-topic',
    bootstrap_servers=['kafka:9092'],
    group_id='task-workers',
    auto_offset_reset='earliest',
    enable_auto_commit=False,  # Ручной commit после обработки
    max_poll_records=500,      # Batch processing
    session_timeout_ms=30000,
    heartbeat_interval_ms=3000
)

def process_task(message_data: dict) -> dict:
    """
    Обработка задачи (пример)
    """
    # Бизнес-логика
    result = {
        'processed_at': datetime.utcnow().isoformat(),
        'status': 'success',
        'data': f"Processed: {message_data.get('payload')}"
    }
    return result

def handle_message(message, session):
    """
    Обработка сообщения с AT-LEAST-ONCE гарантией
    """
    try:
        data = json.loads(message.value.decode())
        task_id = data['task_id']
        idempotency_key = data['idempotency_key']
        
        # 1. Проверить, не обработана ли уже
        existing_result = session.query(TaskResult).filter(
            TaskResult.idempotency_key == idempotency_key
        ).first()
        
        if existing_result:
            print(f"Task {task_id} already processed (idempotent)")
            return True
        
        # 2. Обработать задачу
        result = process_task(data['payload'])
        
        # 3. Сохранить результат (транзакция)
        task_result = TaskResult(
            task_id=task_id,
            idempotency_key=idempotency_key,
            result=json.dumps(result),
            status='COMPLETED',
            processed_at=datetime.utcnow()
        )
        session.add(task_result)
        
        # Обновить статус исходной задачи
        task = session.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = 'COMPLETED'
        
        session.commit()
        return True
        
    except Exception as e:
        session.rollback()
        print(f"Error processing message: {e}")
        # Dead letter queue для retry позже
        return False

# Main consumer loop
try:
    for message in consumer:
        session = Session()
        try:
            if handle_message(message, session):
                # Только после успешной обработки
                consumer.commit()
            else:
                # При ошибке не коммитим - переобработаем
                pass
        finally:
            session.close()
except KeyboardInterrupt:
    consumer.close()
```

---

### 6. **Мониторинг и отказоустойчивость**

**Метрики (Prometheus):**

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'kafka'
    static_configs:
      - targets: ['kafka-exporter:9308']
  
  - job_name: 'workers'
    static_configs:
      - targets: ['worker-1:9090', 'worker-2:9090']

# Alerts for operational health
rules:
  - alert: HighLatency
    expr: histogram_quantile(0.99, latency_bucket) > 100
    for: 5m
    
  - alert: KafkaLagHigh
    expr: kafka_consumer_lag > 10000
    for: 10m
    
  - alert: WorkerDown
    expr: up{job="workers"} == 0
```

**Circuit Breaker (в worker):**

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
def call_external_service(data):
    """Обработка с circuit breaker"""
    return requests.post(url, json=data, timeout=5)

def safe_process_task(task_data):
    try:
        return call_external_service(task_data)
    except Exception:
        # Fallback: отправить в DLQ
        send_to_dlq(task_data)
```

---

### 7. **Горизонтальное масштабирование (Kubernetes)**

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: task-worker
spec:
  replicas: 100  # Начать с 100 workers
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 10
      maxUnavailable: 5
  selector:
    matchLabels:
      app: task-worker
  template:
    metadata:
      labels:
        app: task-worker
    spec:
      containers:
      - name: worker
        image: myregistry/task-worker:latest
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        env:
        - name: KAFKA_BROKERS
          value: "kafka:9092"
        - name: CONSUMER_GROUP
          value: "task-workers"
        - name: MAX_POLL_RECORDS
          value: "500"
        livenessProbe:
          httpGet:
            path: /health
            port: 9090
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 9090
          initialDelaySeconds: 10
          periodSeconds: 5

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
  minReplicas: 50
  maxReplicas: 200
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
        averageValue: "5000"
```

---

### 8. **Чеклист для вашей системы**

| Требование | Решение | Статус |
|-----------|---------|--------|
| 50K RPS | Kafka с 50+ партициями, 100+ workers | ✓ |
| AT-LEAST-ONCE | Idempotency keys + DB, ручной commit | ✓ |
| < 100ms latency | E2E: 10ms (API) + 20ms (Kafka) + 50ms (worker) + 15ms (DB) | ✓ |
| Горизонтальное масштабирование | Kafka partitions, K8s HPA | ✓ |
| Fault tolerance | Replication, Circuit breaker, DLQ | ✓ |

---

**Tool: todowrite**

**Input:**
```json
{}
```

**Error:**
```
Tool execution aborted
```

---

## User

Ты solution architect. 
Задача: Нужно спроектировать распределённую систему обработки задач
требованиями: 50,000 RPS, гарантия доставки (at-least-once), latency < 100ms, горизонтальное масштабирование. 

---

## Assistant (Plan · anthropic/claude-haiku-4.5 · 188.2s)

Спасибо за задачу! Я вижу, что вы в режиме планирования. Давайте разработаем детальный план архитектуры перед реализацией.

Прежде чем я представлю полный архитектурный план, у меня есть несколько уточняющих вопросов:

**Tool: question**

**Input:**
```json
{
  "questions": [
    {
      "header": "Характер задач",
      "question": "Какой тип задач будет обрабатываться? (например: трансформация данных, вызовы API, отправка email, аналитика)",
      "options": [
        {
          "label": "Легкие вычисления",
          "description": "Быстрые операции < 10ms (кеширование, валидация)"
        },
        {
          "label": "Средние операции",
          "description": "Операции 10-100ms (API вызовы, DB запросы)"
        },
        {
          "label": "Тяжелые процессы",
          "description": "Длительные операции > 100ms (ML, обработка файлов)"
        },
        {
          "label": "Смешанные",
          "description": "Разные типы задач в одной системе"
        }
      ]
    },
    {
      "header": "Приоритизация задач",
      "question": "Нужна ли приоритизация между задачами?",
      "options": [
        {
          "label": "Нет приоритетов",
          "description": "Все задачи обрабатываются FIFO"
        },
        {
          "label": "Несколько уровней",
          "description": "HIGH, MEDIUM, LOW приоритеты"
        },
        {
          "label": "Динамическая приоритизация",
          "description": "Приоритет может изменяться во времени"
        }
      ]
    },
    {
      "header": "Допустимые потери",
      "question": "Допустимо ли потеря задач при критических отказах?",
      "options": [
        {
          "label": "Ноль потерь",
          "description": "Все задачи должны быть обработаны (финансовые транзакции)"
        },
        {
          "label": "Минимальные потери",
          "description": "< 0.1% задач могут быть потеряны"
        },
        {
          "label": "Некритичные потери",
          "description": "До 1% потерь допустимо (аналитика, логирование)"
        }
      ]
    },
    {
      "header": "Инфраструктура",
      "question": "На какой инфраструктуре развёртываться?",
      "options": [
        {
          "label": "Kubernetes",
          "description": "K8s кластер в облаке (AWS/GCP/Azure)"
        },
        {
          "label": "Docker Compose",
          "description": "Локальная разработка или single-machine"
        },
        {
          "label": "On-premise",
          "description": "Собственные серверы в data center"
        },
        {
          "label": "Гибридная",
          "description": "Комбинация из нескольких вариантов"
        }
      ]
    },
    {
      "header": "Сложность обработки",
      "question": "Нужна ли обработка в несколько этапов (workflow)?",
      "options": [
        {
          "label": "Простая обработка",
          "description": "Одна стадия обработки для каждой задачи"
        },
        {
          "label": "Многоэтапные workflow",
          "description": "Задача должна пройти несколько стадий (Step 1 → Step 2 → Step 3)"
        },
        {
          "label": "Сложные зависимости",
          "description": "Некоторые задачи зависят от результатов других"
        }
      ]
    },
    {
      "header": "Стоимость vs надёжность",
      "question": "Какой баланс между стоимостью и надёжностью?",
      "options": [
        {
          "label": "Максимальная надёжность",
          "description": "99.99% uptime, не важна стоимость"
        },
        {
          "label": "Баланс",
          "description": "99.9% uptime, оптимальная стоимость"
        },
        {
          "label": "Минимальная стоимость",
          "description": "95% uptime приемлемо, минимизировать затраты"
        }
      ]
    }
  ]
}
```

**Output:**
```
User has answered your questions: "Какой тип задач будет обрабатываться? (например: трансформация данных, вызовы API, отправка email, аналитика)"="Средние операции", "Нужна ли приоритизация между задачами?"="Несколько уровней", "Допустимо ли потеря задач при критических отказах?"="Ноль потерь", "На какой инфраструктуре развёртываться?"="Kubernetes", "Нужна ли обработка в несколько этапов (workflow)?"="Сложные зависимости", "Какой баланс между стоимостью и надёжностью?"="Баланс". You can now continue with the user's answers in mind.
```

---

## Assistant (Plan · anthropic/claude-haiku-4.5 · 107.2s)

Отлично! Вы выбрали очень требовательный профиль: **критичные операции с нулевыми потерями, сложные workflow, приоритизация и динамическое масштабирование на K8s**. Это целевой профиль для финтеха или критичной обработки платежей.

Позвольте уточнить ещё несколько ключевых моментов перед финальным планом:

**Tool: question**

**Input:**
```json
{
  "questions": [
    {
      "header": "Распределение нагрузки",
      "question": "Как распределяется нагрузка в 50K RPS?",
      "options": [
        {
          "label": "Пиковая нагрузка 50K",
          "description": "Средняя ≈ 20K RPS, пики до 50K RPS"
        },
        {
          "label": "Постоянная 50K",
          "description": "Стабильные 50K RPS 24/7"
        },
        {
          "label": "Непредсказуемая",
          "description": "Может быть от 1K до 100K RPS нестабильно"
        }
      ]
    },
    {
      "header": "Хранение данных",
      "question": "Как долго хранить данные о выполненных задачах?",
      "options": [
        {
          "label": "7 дней",
          "description": "Для аудита и отладки"
        },
        {
          "label": "30 дней",
          "description": "Для анализа и compliance"
        },
        {
          "label": "Бесконечно",
          "description": "Полная история всех задач"
        }
      ]
    },
    {
      "header": "Гео-распределение",
      "question": "Нужна ли гео-репликация (multi-region)?",
      "options": [
        {
          "label": "Single region",
          "description": "Один дата-центр, простая архитектура"
        },
        {
          "label": "Active-Active",
          "description": "Несколько регионов, одновременная обработка везде"
        },
        {
          "label": "Active-Passive",
          "description": "Основной регион + failover регион"
        }
      ]
    },
    {
      "header": "Специальные требования",
      "question": "Есть ли специальные требования?",
      "options": [
        {
          "label": "Нет",
          "description": "Стандартная обработка"
        },
        {
          "label": "Требуется заказ выполнения (strict order)",
          "description": "Задачи для одного клиента должны обрабатываться по порядку"
        },
        {
          "label": "Требуется деградация (graceful degradation)",
          "description": "Система должна частично работать при сбоях"
        }
      ]
    }
  ]
}
```

**Output:**
```
User has answered your questions: "Как распределяется нагрузка в 50K RPS?"="Пиковая нагрузка 50K", "Как долго хранить данные о выполненных задачах?"="Глубина хранения должна настраиваться", "Нужна ли гео-репликация (multi-region)?"="Active-Passive", "Есть ли специальные требования?"="Нет". You can now continue with the user's answers in mind.
```

---

## Assistant (Plan · anthropic/claude-haiku-4.5 · 4.4s)

Отлично! Теперь я имею полную картину. Позвольте мне создать **детальный архитектурный план** для вашей системы:

**Tool: todowrite**

**Input:**
```json
{
  "todos": [
    {
      "content": "Создать полный архитектурный документ с диаграммами",
      "status": "in_progress",
      "priority": "high"
    },
    {
      "content": "Спроектировать уровни обработки и workflow",
      "status": "pending",
      "priority": "high"
    },
    {
      "content": "Разработать стратегию гарантии доставки (AT-LEAST-ONCE)",
      "status": "pending",
      "priority": "high"
    },
    {
      "content": "Спланировать K8s deployment и HPA",
      "status": "pending",
      "priority": "high"
    },
    {
      "content": "Определить мониторинг, логирование и алерты",
      "status": "pending",
      "priority": "high"
    },
    {
      "content": "Создать примеры конфигурации и кода",
      "status": "pending",
      "priority": "medium"
    }
  ]
}
```

**Output:**
```
[
  {
    "content": "Создать полный архитектурный документ с диаграммами",
    "status": "in_progress",
    "priority": "high"
  },
  {
    "content": "Спроектировать уровни обработки и workflow",
    "status": "pending",
    "priority": "high"
  },
  {
    "content": "Разработать стратегию гарантии доставки (AT-LEAST-ONCE)",
    "status": "pending",
    "priority": "high"
  },
  {
    "content": "Спланировать K8s deployment и HPA",
    "status": "pending",
    "priority": "high"
  },
  {
    "content": "Определить мониторинг, логирование и алерты",
    "status": "pending",
    "priority": "high"
  },
  {
    "content": "Создать примеры конфигурации и кода",
    "status": "pending",
    "priority": "medium"
  }
]
```

---

## Assistant (Plan · anthropic/claude-haiku-4.5 · 42.9s)

---

## 🏗️ **АРХИТЕКТУРНЫЙ ПЛАН: Распределённая система обработки задач**

### **📊 Общая архитектура (High-level)**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                    │
│  (REST API / gRPC Clients submitting tasks)                             │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                    ┌────────▼─────────┐
                    │  API Gateway     │
                    │  (Envoy/Kong)    │
                    │  Rate Limit      │
                    │  Auth & Logging  │
                    └────────┬─────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │   Producer   │  │   Producer   │  │   Producer   │
  │  Instance 1  │  │  Instance 2  │  │  Instance N  │
  │              │  │              │  │              │
  │ • Validate   │  │ • Validate   │  │ • Validate   │
  │ • Dedupe     │  │ • Dedupe     │  │ • Dedupe     │
  │ • Store DB   │  │ • Store DB   │  │ • Store DB   │
  │ • Kafka Send │  │ • Kafka Send │  │ • Kafka Send │
  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         │                 │                 │
         └─────────────────┼─────────────────┘
                           │
                ┌──────────▼──────────┐
                │   KAFKA CLUSTER     │
                │  (3 brokers, HA)    │
                │                     │
                │ Topics:             │
                │ • tasks-high        │ (Priority HIGH)
                │ • tasks-medium      │ (Priority MEDIUM)
                │ • tasks-priority    │ (Priority LOW)
                │ • tasks-dlq         │ (Dead Letter)
                │ • tasks-events      │ (Workflow events)
                │                     │
                │ Partitions: 100     │
                │ Replication: 3      │
                └──────────┬──────────┘
         ┌──────────────────┼──────────────────┐
         │                  │                  │
    ┌────▼───────┐ ┌────────▼──────┐ ┌────────▼──────┐
    │  Worker    │ │  Worker       │ │ Worker        │
    │  Pool HIGH │ │  Pool MEDIUM  │ │ Pool LOW      │
    │ (×20)      │ │ (×50)         │ │ (×30)         │
    │            │ │               │ │               │
    │ • Consume  │ │ • Consume     │ │ • Consume     │
    │ • Validate │ │ • Validate    │ │ • Validate    │
    │ • Idempotence Check         │ │ • Idempotence │
    │ • Execute  │ │ • Execute     │ │ • Execute     │
    │ • Store    │ │ • Store       │ │ • Store       │
    │ • Event    │ │ • Event emit  │ │ • Event emit  │
    └────┬───────┘ └────────┬──────┘ └────────┬──────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
        ┌───▼──┐      ┌────▼────┐     ┌───▼──┐
        │ Async│      │  State  │     │ Event│
        │Cache │      │  Store  │     │ Bus  │
        │(Redis)      │(PostgreSQL)   │(Kafka)
        └──────┘      └─────────┘     └──────┘
            │               │               │
            └───────────────┼───────────────┘
                            │
            ┌───────────────▼────────────┐
            │   Monitoring & Observability
            │   • Prometheus metrics
            │   • Jaeger tracing
            │   • ELK logging
            │   • Grafana dashboards
            └────────────────────────────┘
```

---

### **🔀 Workflow обработки задач (с приоритизацией)**

```
ФАЗА 1: ПРИЁМ ЗАДАЧИ (Producer)
┌────────────────────────────────────────────────┐
│ 1. Получить HTTP POST /tasks                   │
│ 2. Валидация схемы (OpenAPI spec)              │
│ 3. Проверить rate limit по client_id           │
│ 4. Сохранить в PostgreSQL:                     │
│    ├─ tasks table                              │
│    ├─ status = PENDING                         │
│    ├─ priority = (HIGH/MEDIUM/LOW)             │
│    └─ idempotency_key = UUID                   │
│ 5. Отправить в соответствующий Kafka topic:   │
│    ├─ HIGH priority → tasks-high               │
│    ├─ MEDIUM priority → tasks-medium           │
│    └─ LOW priority → tasks-priority            │
│ 6. Вернуть task_id клиенту (202 Accepted)     │
│ 7. Emit event: task.created                    │
└────────────────────────────────────────────────┘

ФАЗА 2: ОБРАБОТКА В WORKERS (Consumer)
┌────────────────────────────────────────────────┐
│ 1. Worker получает сообщение из Kafka          │
│    └─ Max batch size: 500 records              │
│ 2. Проверить idempotency_key в DB              │
│    └─ Если уже обработана → вернуть результат │
│ 3. Проверить блокировки (互斥/mutex)           │
│    └─ Для зависимых задач (workflow)           │
│ 4. Выполнить Step 1:                           │
│    ├─ Валидация входных данных                 │
│    ├─ Загрузить зависимые ресурсы              │
│    ├─ Обновить task status = IN_PROGRESS      │
│    └─ Emit: task.step1_started                 │
│ 5. Выполнить Step 2:                           │
│    ├─ Основная бизнес-логика                   │
│    ├─ Вызовы внешних API (с retry)             │
│    └─ Кеширование результатов (Redis)          │
│ 6. Выполнить Step 3:                           │
│    ├─ Финализация обработки                    │
│    ├─ Сохранить результат в DB                 │
│    └─ Обновить task status = COMPLETED        │
│ 7. Commit Kafka offset только после сохранения │
│ 8. Emit event: task.completed                  │
└────────────────────────────────────────────────┘

ФАЗА 3: ОБРАБОТКА ОШИБОК
┌────────────────────────────────────────────────┐
│ Попытка 1: Обработать обычно                   │
│ Попытка 2-5: Retry с exponential backoff       │
│          ├─ Delay: 1s, 2s, 4s, 8s              │
│          └─ Jitter: ±30%                       │
│ После 5 попыток: Переместить в Dead Letter Queue
│ DLQ: Хранить 30 дней для анализа               │
│ Emit: task.failed / task.dlq                   │
└────────────────────────────────────────────────┘

ФАЗА 4: ЗАВИСИМОСТИ (Workflow)
┌────────────────────────────────────────────────┐
│ Task A (независимая)  ─────┐                   │
│                            ├─→ Task C (зависит)
│ Task B (независимая)  ─────┘                   │
│                                                 │
│ Worker:                                         │
│ 1. Проверить Task A и B завершены ✓            │
│ 2. Если нет → поместить Task C обратно в очередь
│ 3. Если да → обработать Task C                 │
│ 4. Timeout: если зависимость > 1h → fail       │
└────────────────────────────────────────────────┘
```

---

### **🔐 Гарантия доставки (AT-LEAST-ONCE)**

```
DATABASE SCHEMA:
┌─────────────────────────────────────────────────┐
│ TABLE: tasks                                    │
├─────────────────────────────────────────────────┤
│ id (UUID, PK)                                   │
│ idempotency_key (UUID, UNIQUE, INDEX)           │
│ client_id (VARCHAR)                             │
│ priority (ENUM: HIGH, MEDIUM, LOW)              │
│ status (ENUM: PENDING, IN_PROGRESS, COMPLETED, │
│              FAILED, DLQ)                       │
│ payload (JSONB)                                 │
│ result (JSONB)                                  │
│ error_message (TEXT)                            │
│ retry_count (INT, DEFAULT 0)                    │
│ created_at (TIMESTAMP)                          │
│ started_at (TIMESTAMP)                          │
│ completed_at (TIMESTAMP)                        │
│ created_at_idx, status_idx                      │
└─────────────────────────────────────────────────┘

ГАРАНТИЯ МЕХАНИЗМА:

1. PRODUCER SIDE:
   ┌─────────────────────────────────────┐
   │ BEGIN TRANSACTION                   │
   │   INSERT INTO tasks (                │
   │     idempotency_key,                 │
   │     status = 'PENDING',              │
   │     payload,                         │
   │     created_at                       │
   │   ) VALUES (...)                     │
   │   RETURNING id                       │
   │                                      │
   │   kafka_producer.send(               │
   │     key = task_id,                   │
   │     acks = 'all',                    │
   │     timeout = 10s                    │
   │   )                                  │
   │ COMMIT                               │
   └─────────────────────────────────────┘
   
   Результат:
   ✓ Если оба успеха → RETURN 202 Accepted
   ✗ Если Kafka fail → ROLLBACK + RETRY (max 3)
   ✗ Если DB fail → RETURN 500 (клиент может retry)

2. WORKER SIDE:
   ┌─────────────────────────────────────┐
   │ kafka_consumer.poll(                 │
   │   max_records = 500,                 │
   │   timeout = 30s                      │
   │ )                                    │
   │                                      │
   │ FOR EACH message:                    │
   │   - Проверить идемпотентность        │
   │   - Обработать задачу (транзакция)   │
   │   - Сохранить результат              │
   │                                      │
   │ COMMIT OFFSET (только после DB)      │
   │ kafka_consumer.commit_sync()         │
   └─────────────────────────────────────┘

   Результат:
   ✓ Graceful: процесс завершился → все сохранено
   ✗ Crash до commit: Kafka переотправит → идемпотентность спасает
   ✗ Crash после commit: OK, задача в DB

3. IDEMPOTENCY KEY CHECK:
   ┌─────────────────────────────────────┐
   │ SELECT * FROM tasks_results         │
   │ WHERE idempotency_key = ?            │
   │ LIMIT 1                              │
   │                                      │
   │ IF exists:                           │
   │   RETURN cached_result               │
   │ ELSE:                                │
   │   INSERT new result                  │
   │   RETURN new_result                  │
   └─────────────────────────────────────┘

ГАРАНТИИ:
• 0% потерь: DB + Kafka replication
• Ровно один раз логики (exactly-once semantics)
  благодаря idempotency_key
```

---

### **📈 Масштабирование: 50K RPS → 100+ Workers**

```
РАСЧЁТЫ:
┌────────────────────────────────────────────┐
│ Target: 50K RPS                            │
│ Avg latency per task: 50ms                 │
│                                            │
│ Kafka throughput per partition:            │
│   1-2 MB/s ≈ 100 bytes/msg × 10-20K msg/s │
│                                            │
│ Partitions needed: 50K RPS ÷ 10K = 5      │
│ Partitions recommended: 50-100 (headroom)  │
│                                            │
│ Workers per partition: 1-2 (避免rebalance) │
│ Min workers: 50 × 2 = 100                  │
│ Max workers (peaks): 150-200               │
│                                            │
│ Resource per worker (1 CPU, 512MB RAM):    │
│   50K RPS × 1 CPU = 50 CPU cores           │
│   150K jobs max = 30-50 GB RAM             │
└────────────────────────────────────────────┘

K8S DEPLOYMENT:
┌────────────────────────────────────────────┐
│ HPA (Horizontal Pod Autoscaler)             │
│                                            │
│ MinReplicas: 50                            │
│ MaxReplicas: 200                           │
│                                            │
│ Scaling Metrics:                           │
│ 1. CPU Utilization: 70%                    │
│    → Scale up if avg CPU > 70%             │
│    → Scale down if avg CPU < 30%           │
│                                            │
│ 2. Kafka Consumer Lag:                     │
│    → Scale up if lag > 50K messages        │
│    → Scale down if lag < 10K messages      │
│                                            │
│ 3. Custom Metric (queue_depth):            │
│    → Scale up if depth > 100K              │
│    → Scale down if depth < 20K             │
│                                            │
│ Scaling Policy:                            │
│ • Cooldown: 5 minutes                      │
│ • Max change per scale: ±10 pods           │
│ • Spread across availability zones         │
└────────────────────────────────────────────┘

KAFKA CONFIGURATION:
┌────────────────────────────────────────────┐
│ Broker Config (3 brokers):                  │
│                                            │
│ num.io.threads: 32                         │
│ num.network.threads: 32                    │
│ socket.receive.buffer.bytes: 102400        │
│ socket.request.max.bytes: 104857600        │
│ replica.socket.receive.buffer.bytes: 102400
│                                            │
│ Topic Config:                              │
│ partitions: 100                            │
│ replication.factor: 3                      │
│ min.insync.replicas: 2                     │
│ retention.ms: 604800000 (7 days)           │
│ compression.type: snappy                   │
│                                            │
│ Consumer Config:                           │
│ group.id: task-workers-{priority}          │
│ max.poll.records: 500                      │
│ session.timeout.ms: 30000                  │
│ heartbeat.interval.ms: 3000                │
│ auto.commit.interval.ms: -1 (manual)       │
└────────────────────────────────────────────┘
```

---

### **📊 Мониторинг, логирование, алерты**

```
KEY METRICS:
┌──────────────────────────────────────────────┐
│ Latency Metrics:                             │
│ • task.latency_p50 (target: < 50ms)          │
│ • task.latency_p95 (target: < 80ms)          │
│ • task.latency_p99 (target: < 100ms)         │
│                                              │
│ Throughput Metrics:                          │
│ • tasks.processed_per_sec (target: 50K)      │
│ • tasks.failed_per_sec (target: < 10)        │
│ • tasks.retry_rate (target: < 1%)            │
│                                              │
│ Queue Health:                                │
│ • kafka.consumer_lag (alert: > 50K)          │
│ • kafka.partition_lag (alert: > 10K)         │
│ • producer_queue_depth (alert: > 100K)       │
│                                              │
│ Resource Utilization:                        │
│ • pod.cpu_utilization (target: 50-70%)       │
│ • pod.memory_utilization (target: 60-75%)    │
│ • db.connection_pool (target: < 80%)         │
│                                              │
│ Error Rates:                                 │
│ • tasks.error_rate (alert: > 0.1%)           │
│ • external_api.error_rate (alert: > 5%)      │
│ • db.query_errors (alert: any)               │
│                                              │
│ Business Metrics:                            │
│ • tasks.dlq_count (alert: > 100/hour)        │
│ • tasks.stuck_duration (alert: > 1 hour)     │
│ • tasks.dependency_timeout (alert: > 1 hour) │
└──────────────────────────────────────────────┘

ALERTING RULES (Prometheus):
┌──────────────────────────────────────────────┐
│ CRITICAL:                                    │
│ • Kafka lag > 100K (tasks stuck)             │
│ • Pod CPU > 95% × 5min                       │
│ • Worker restart loop (> 5 restarts/hour)    │
│ • Task failure rate > 1%                     │
│ • Database connection pool exhausted         │
│                                              │
│ WARNING:                                     │
│ • Latency p99 > 100ms × 10min                │
│ • Kafka lag > 50K × 5min                     │
│ • Memory utilization > 85% × 3min            │
│ • Task retry rate > 2%                       │
│ • DLQ receiving > 50 msg/min                 │
│                                              │
│ PERFORMANCE:                                 │
│ • Latency p50 trending up > 20%              │
│ • GC pause > 100ms (Java workers)            │
│ • Worker pod startup time > 30s              │
└──────────────────────────────────────────────┘

DISTRIBUTED TRACING:
┌──────────────────────────────────────────────┐
│ Jaeger spans per task:                       │
│                                              │
│ task:create                                  │
│   ├─ validate (5-10ms)                       │
│   ├─ db:insert (10-20ms)                     │
│   ├─ kafka:produce (5-15ms)                  │
│   └─ response (1-2ms)                        │
│                                              │
│ task:process                                 │
│   ├─ kafka:poll (10-30ms)                    │
│   ├─ idempotence:check (5-10ms)              │
│   ├─ execute (20-50ms)                       │
│   ├─ db:update (10-20ms)                     │
│   └─ kafka:commit (5-10ms)                   │
│                                              │
│ Trace correlation:                           │
│ request_id → task_id → trace_id              │
└──────────────────────────────────────────────┘

LOGGING:
┌──────────────────────────────────────────────┐
│ Structured logging (JSON):                   │
│ {                                            │
│   "timestamp": "2024-01-15T10:30:45.123Z",  │
│   "level": "INFO",                           │
│   "service": "task-worker",                  │
│   "pod": "worker-123",                       │
│   "task_id": "uuid-xxx",                     │
│   "client_id": "client-123",                 │
│   "priority": "HIGH",                        │
│   "event": "task:started",                   │
│   "status": "IN_PROGRESS",                   │
│   "trace_id": "trace-xxx",                   │
│   "duration_ms": 45,                         │
│   "retry_count": 0,                          │
│   "external_api": "payment_service",         │
│   "api_latency_ms": 25                       │
│ }                                            │
│                                              │
│ ELK (Elasticsearch, Logstash, Kibana):       │
│ • Retention: 30 days (per requirements)      │
│ • Parsing: Grok + JSON                       │
│ • Dashboards: By priority, by client, by SLA │
│ • Alerts: Via PagerDuty integration           │
└──────────────────────────────────────────────┘
```

---

### **🔄 Active-Passive Failover (Multi-Region)**

```
PRIMARY REGION (us-east-1):
┌─────────────────────────────────┐
│ K8s Cluster (active)             │
│ ├─ Producer (write active)       │
│ ├─ Workers (processing)          │
│ ├─ PostgreSQL (primary)          │
│ └─ Kafka (leader)                │
└────────────────────┬─────────────┘
                     │
        ┌────────────▼─────────────┐
        │ CDC (Change Data Capture)│
        │ (Postgres WAL streaming) │
        └────────────┬─────────────┘
                     │
        ┌────────────▼──────────────────┐
        │ Binary replication lag < 100ms │
        └────────────┬──────────────────┘
                     │
SECONDARY REGION (us-west-2):
┌────────────────────▼──────────────┐
│ K8s Cluster (standby)             │
│ ├─ Producer (read-only standby)   │
│ ├─ Workers (stopped)               │
│ ├─ PostgreSQL (replica)            │
│ └─ Kafka (follower)                │
└──────────────────────────────────┘

FAILOVER PROCESS (< 60 seconds):
1. Health check failed (3× probe failures)
2. Detect primary down
3. Promote secondary:
   a. Promote PostgreSQL replica → primary
   b. Activate Kafka followers
   c. Scale up workers in secondary
   d. Update DNS/LB to point to secondary
4. Resume processing from last commit offset
5. Alert ops team
6. DNS TTL: 5 seconds (для быстрого переключения)

RPO (Recovery Point Objective): ~100ms
RTO (Recovery Time Objective): ~60 seconds
```

---

### **✅ Чеклист реализации**

| Компонент | Технология | Требование | Статус |
|-----------|-----------|-----------|--------|
| **API Gateway** | Envoy Proxy / Kong | Rate limiting, auth | ⏳ |
| **Message Broker** | Apache Kafka | 100 partitions, HA | ⏳ |
| **Primary DB** | PostgreSQL 14+ | ACID, replication | ⏳ |
| **Cache** | Redis 6+ | Session, idempotency | ⏳ |
| **Orchestration** | Kubernetes 1.24+ | HPA, resource limits | ⏳ |
| **Worker Runtime** | Python/Go/Node.js | Consumer group, retry | ⏳ |
| **Monitoring** | Prometheus | Metrics collection | ⏳ |
| **Tracing** | Jaeger | Distributed traces | ⏳ |
| **Logging** | ELK Stack | Structured JSON logs | ⏳ |
| **Alerting** | AlertManager | PagerDuty integration | ⏳ |
| **DC Recovery** | PostgreSQL CDC | WAL streaming | ⏳ |

---

## 📋 **Что дальше?**

Данный план готов к реализации. Я готов помочь вам с:

1. **Кодировкой Producer** (с идемпотентностью)
2. **Кодировкой Worker** (с retry logic, graceful shutdown)
3. **K8s YAML конфигурациями** (deployment, HPA, service mesh)
4. **Docker Compose** для локальной разработки
5. **Мониторинг Setup** (Prometheus + Grafana)
6. **Тестами** (unit, integration, chaos engineering)

Хотите начать с какого-то конкретного компонента? 🚀

---

