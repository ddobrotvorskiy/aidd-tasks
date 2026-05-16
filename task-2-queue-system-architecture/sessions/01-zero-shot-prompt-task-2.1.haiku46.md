# Distributed Task Processing System

## 1. Анализ требований

```
50,000 RPS → ~4.3 млрд задач/день
At-least-once → нужен acknowledgment + retry механизм  
Latency < 100ms → P99, end-to-end
Horizontal scaling → stateless workers + partitioned storage
```

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENTS│
└──────────────────┬──────────────────────────────────────────┘│┌─────────▼─────────┐
         │   API Gateway      │  ← Rate limiting, auth
         │   (Nginx/Envoy)    │    10instances
         └─────────┬─────────┘
                   │
    ┌──────────────▼──────────────┐
    │      Intake Service│  ← Stateless, 20 instances
    │   (Task Validation +│    Go/Rust для низкой latency
    │    Deduplication)           │
    └──────────────┬──────────────┘
                   │
    ┌──────────────▼──────────────┐
    │         Kafka Cluster        │  ← 50 partitions
    │   (Message Broker)           │    Replication factor: 3
    │                              │    Retention: 24h
    └──────────────┬──────────────┘
                   │
    ┌──────────────▼──────────────┐
    │Worker Pool│  ← Auto-scaling
    │   (Task Processors)          │    Consumer groups
    └──────────────┬──────────────┘
                   │
    ┌──────────────▼──────────────┐
    │      Result Store            │
    │   PostgreSQL + Redis         │
    └─────────────────────────────┘
```

---

## 3. Детальный дизайн компонентов

### 3.1 Intake Service

```go
// Критичный путь — должен быть максимально быстрым
type TaskIngester struct {
    kafka*kafka.Producer
    redis     *redis.Client// dedup cache
    validator *Validator
}

func (t *TaskIngester) Submit(ctx context.Context, task Task) error {
    // 1. Валидация — sync,< 1ms
    if err := t.validator.Validate(task); err != nil {
        return ErrInvalidTask
    }

    // 2. Deduplication через Redis (TTL = 24h)
    // Bloom filter для снижения нагрузки на Redis
    isDup, err := t.checkDuplicate(ctx, task.ID)
    if isDup {
        return nil // idempotent
    }

    // 3. Async publish в Kafka
    // НЕ ждём подтверждения от Kafka — отвечаем клиенту сразу
    // Durability обеспечивается WAL на стороне Kafka
    return t.kafka.ProduceAsync(task, t.onDelivery)
}
```

### 3.2 Kafka Configuration

```yaml
# broker config
num.partitions: 50
replication.factor: 3
min.insync.replicas: 2

# producer config (Intake Service)
acks: all              # Гарантия записи на2+ реплики
enable.idempotence: true
compression.type: lz4  # CPU vs network tradeoff
linger.ms: 5# Batching для throughput
batch.size: 65536

# consumer config (Workers)
max.poll.records: 500
enable.auto.commit: false# Manual commit после обработки!
fetch.min.bytes: 1024
```

### 3.3 Worker Service

```go
type Worker struct {
    consumer *kafka.Consumer
    store    *ResultStore
    metrics  *prometheus.Registry
}

func (w *Worker) ProcessLoop(ctx context.Context) {
    for {
        messages := w.consumer.Poll(ctx, 100*time.Millisecond)
        // Параллельная обработка batch
        var wg sync.WaitGroup
        results := make(chan Result, len(messages))
        
        for _, msg := range messages {
            wg.Add(1)
            go func(m Message) {
                defer wg.Done()
                
                result, err := w.processWithTimeout(m,80*time.Millisecond)
                if err != nil {
                    // Отправляем в Dead Letter Queue
                    w.sendToDLQ(m, err)
                    return
                }
                results <- result
            }(msg)
        }
        
        wg.Wait()
        close(results)
        
        // Сохраняем результаты batch
        w.store.BatchSave(ctx, results)
        
        // Commit ТОЛЬКО после успешного сохранения
        // Это обеспечивает at-least-once
        w.consumer.CommitOffsets()
    }
}
```

### 3.4 Гарантия At-Least-Once

```
Сценарий сбоя:

┌──────────┐┌───────┐     ┌────────┐     ┌────────┐
│  Worker  │────▶│Process│────▶│  Save  │────▶│ Commit │
└──────────┘     └───────┘     └────────┘     └────────┘↑Crash здесь →
                              Kafka переотправит сообщение
                              Worker должен быть idempotent!

Решение: task_id как idempotency key в БД
INSERT INTO results (task_id, ...) 
ON CONFLICT (task_id) DO NOTHING;
```

---

## 4. Latency Breakdown

```
Бюджет 100ms распределяем:

[Client → API GW]~5ms   (network)
[API GW → Intake]        ~2ms   (internal)
[Validation + Dedup]     ~3ms   (Redis lookup)
[Kafka Produce]          ~10ms  (async, не блокирует ответ!)
[Ответ клиенту]         ~20ms  TOTAL✓

──────────────────────────────────────────
[Kafka → Worker]         ~15ms  (polling interval)
[Task Processing]        ~50ms  (бизнес-логика)
[Save Result]            ~10ms  (DB write)
[Kafka Commit]           ~5ms         ~80ms  async processing
```

---

## 5. Масштабирование

```
Horizontal Scaling Strategy:

RPS Growth:
10K→ 4Intake pods+ 10 Worker pods
50K  → 20 Intake pods + 50 Worker pods  
100K → 40 Intake pods + 100 Worker pods

Kafka Partitions = max(Worker pods) → 50 partitions
1 partition = 1 worker consumer (ordering guarantee)

Auto-scaling triggers:
- CPU > 70%→ +2 pods
- Lag > 10K messages → +5 worker pods
- Latency P99 > 80ms → +2 intake pods
```

---

## 6. Data Layer

```
┌─────────────────────────────────────────────┐
│              Redis Cluster                   │
│- Dedup cache (Bloom Filter + exact check) │
│  - Task status cache (TTL 1h)               │
│  - Rate limiting counters                   │
│  6 nodes, 3 shards × 2 replicas            │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│           PostgreSQL (Citus)                │
│  - Task results (sharded by task_id)        │
│  - Audit log                │
│  - DLQ metadata                             │
│  Sharding key: task_id % 16                 │
└─────────────────────────────────────────────┘
```

---

## 7. Observability

```yaml
Metrics (Prometheus + Grafana):
  - tasks_submitted_total (counter)
  - tasks_processed_total (counter, labels: status)
  - kafka_consumer_lag (gauge, alert > 50K)
  - processing_duration_p99 (histogram)
  - dlq_messages_total (counter, alert > 0)

Tracing (Jaeger):
  - trace_id propagation через все сервисы
  - Sample rate: 1% normal, 100% errors

Alerts:
  - Consumer lag > 50K → PagerDuty
  - DLQ rate > 0.1% → Slack
  - P99 latency > 90ms → PagerDuty
```

---

## 8. Failure Modes & Mitigations

| Сценарий | Поведение | Решение |
|---|---|---|
| Kafka broker down | Producer retry | min.insync.replicas=2 |
| Worker crash | Uncommitted offset → retry | Idempotent processing |
| Redis down | Dedup отключается | Graceful degradation |
| DB overload | Backpressure | Circuit breaker + queue |
| Poison pill message | Бесконечный retry | DLQ после3 попыток |

---

## 9. Итоговая оценка

```
ТребованиеРешение                Статус
─────────────────────────────────────────────────────
50K RPS             20 stateless pods           ✅    + Kafka buffering

At-least-once       Manual Kafka commit         ✅
                    + Idempotent writes

Latency < 100ms     Async Kafka produce         ✅
                    Response до commit

Horizontal scale    Stateless services          ✅
                    + Kafka partitions
```

> **Главный архитектурный принцип:** Intake отвечает клиенту **до** Kafka commit, но **после** того как данные приняты в память брокера. Workers коммитят оффсет **только после** успешного сохранения результата. Это даёт нам и низкую latency, и at-least-once гарантию.