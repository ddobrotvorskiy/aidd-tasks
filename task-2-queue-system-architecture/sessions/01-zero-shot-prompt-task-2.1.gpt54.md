Ниже — практичный high-level дизайн распределённой системы обработки задач под требования:

- **50,000 RPS**
- **гарантия доставки: at-least-once**
- **latency <100ms**
- **горизонтальное масштабирование**

---

#1. Сначала уточним, что именно проектируемПод “система обработки задач” обычно понимают такой pipeline:

1. Клиенты отправляют задачи в API2. Система принимает задачу и **надежно сохраняет**
3. Задача попадает в очередь/лог4. Воркеры обрабатывают задачу5. Результат сохраняется/отправляется дальше6. Если обработка не удалась — происходит **retry**
7. Из-за **at-least-once** возможны дубликаты, значит нужна **идемпотентность**

Если latency <100ms относится к **приему задачи**, это реалистично.Если latency <100ms относится к **полной обработке end-to-end**, то это сильно зависит от бизнес-логики задачи. Для тяжелых задач лучше разделять:

- **ingest latency** — принять и закоммитить задачу: <100ms- **processing latency** — зависит от типа задачи---

#2. Ключевые архитектурные принципыДля таких требований я бы строил систему вокруг следующих принципов:

##2.1. Разделение на два SLA**Не смешивать прием задачи и её выполнение**

- **Слой ingestion** отвечает за быстрое принятие и подтверждение- **Слой processing** — за асинхронную обработкуЭто позволит удержать **<100ms на приём**, даже если обработка может быть длиннее.

##2.2. Durable log / message broker как центральный буферДля50k RPS и горизонтального масштабирования нужен брокер с партиционированием:

Подходящие варианты:
- **Kafka**
- **Pulsar**
- реже: RabbitMQ, если нагрузка/масштаб прощеДля данного кейса я бы выбрал **Kafka**:
- высокая пропускная способность- партиции = горизонтальное масштабирование- хорошая модель consumer groups- удобна для retry/DLQ/event-driven обработки##2.3. At-least-once = дубликаты допустимыЭто значит:
- producer может отправить сообщение повторно- consumer может обработать сообщение повторно- задача может быть доставлена более одного разаСледовательно, система должна быть:
- **idempotent on consume**
- желательно **dedup-aware on ingest**

##2.4. Stateless compute + state outsideВсе API и воркеры — stateless:
- легко масштабируются горизонтально- состояние хранится в Kafka / DB / Redis / object store---

#3. Предлагаемая архитектура---

##3.1. Компоненты###1) API Gateway / Load BalancerФункции:
- TLS termination- rate limiting- auth- routing на ingestion-serviceПримеры:
- NGINX / Envoy / HAProxy- cloud LB---

###2) Ingestion ServiceПринимает запросы от клиентов.

Функции:
- валидация- присвоение `task_id`
- запись метаданных задачи- публикация в Kafka- быстрый ответ клиентуВажно: ingestion-service должен отвечать только после того, как задача **надежно принята**.

Варианты надежного приема:
1. **Сразу писать в Kafka** и отвечать после `acks=all`
2. Либо сначала писать в DB, потом через outbox публиковать в KafkaДля требования **latency <100ms** я бы выбрал:
- **синхронная запись в Kafka с replication**
- ответ клиенту после подтверждения брокераЕсли нужна ещё и сильная бизнес-аудитность, можно добавить DB + outbox, но это увеличит latency и сложность.

---

###3) Kafka ClusterЦентральный слой очередей.

Топики:
- `tasks.main`
- `tasks.retry.1m`
- `tasks.retry.5m`
- `tasks.retry.30m`
- `tasks.dlq`

Почему не одна очередь:
- retry лучше выносить в отдельные потоки- DLQ нужен для неразрешимых ошибок- партиции позволяют масштабировать consumer-ов---

###4) Task Metadata StoreХранилище статуса задач:

Храним:
- `task_id`
- `idempotency_key`
- статус (`accepted`, `processing`, `done`, `failed`, `retrying`)
- timestamps- attempt count- payload hash- result / error codeВарианты:
- **Cassandra / ScyllaDB** — если write-heavy и нужна масштабируемость- **PostgreSQL** — если объем умеренный и нужны транзакции- **DynamoDB / Bigtable / CosmosDB** — если managed cloudДля50k RPS и большой распределенной системы я бы рекомендовал:
- **ScyllaDB/Cassandra** для task stateили- **DynamoDB** если облако позволяет---

###5) Idempotency / Dedup StoreНужен для защиты от повторной отправки клиентом и повторной обработки.

Варианты:
- Redis — быстрый short-term dedup- основная DB — long-term dedup / authoritative stateТипичный подход:
- `idempotency_key -> task_id`
- TTL зависит от бизнес-требований---

###6) Worker ServiceГоризонтально масштабируемые воркеры.

Функции:
- читать из Kafka consumer group- выполнять бизнес-логику- обновлять статус задачи- коммитить offset только после успешной обработки/сохранения результата- при ошибке отправлять в retry или DLQ---

###7) Result Store / Downstream IntegrationsЗависит от задачи:
- DB- cache- object store- вызовы внешних сервисов- публикация в другой топик---

###8) Observability StackОбязательно:
- Prometheus / Grafana- OpenTelemetry- centralized logs- tracing- алерты по lag, retry-rate, DLQ-rate, p99 latency---

#4. Поток обработки##4.1. Приём задачи1. Клиент вызывает `POST /tasks`
2. API Gateway проксирует в ingestion-service3. Ingestion-service:
- валидирует payload - извлекает/создает `idempotency_key`
- генерирует `task_id`
- пишет событие в Kafka (`tasks.main`)
- при необходимости сохраняет metadata со статусом `accepted`
4. После подтверждения Kafka (`acks=all`) возвращает:
- `202 Accepted`
- `task_id`

### Почему `202 Accepted`?
Потому что задача принята в обработку, а не обязательно выполнена.

---

##4.2. Обработка воркером1. Worker читает сообщение из `tasks.main`
2. Пытается “захватить” обработку задачи3. Выполняет бизнес-логику4. Если успешно:
- пишет результат - обновляет статус `done`
- коммитит offset5. Если временная ошибка:
- увеличивает attempt count - публикует в retry topic - коммитит offset исходного сообщения6. Если постоянная ошибка:
- пишет в DLQ - статус `failed`
- коммитит offset---

#5. Как обеспечить at-least-onceAt-least-once в этой архитектуре обеспечивается так:

## На входе- Ingestion публикует в Kafka с `acks=all`
- replication factor >=3- producer retries enabled- idempotent producer желательно включить## На обработке- consumer **не коммитит offset**, пока обработка не завершена- если воркер упал после обработки, но до commit offset — сообщение будет прочитано повторно- значит дубликаты неизбежны## Вывод**Гарантия at-least-once достигается ценой потенциальных дублей.**

---

#6. Как бороться с дублямиЭто критично.

##6.1. Idempotency keyКлиент передает:
- `Idempotency-Key: <uuid>`

Или система генерирует ключ на основе payload.

Сценарий:
- если клиент повторно отправляет тот же запрос- ingestion проверяет `idempotency_key`
- если уже есть `task_id`, возвращает его же---

##6.2. Idempotent consumerWorker перед выполнением проверяет:
- обработана ли уже задача/attempt?
- есть ли финальный статус?

Если `done`, то просто коммитит offset и не делает повторную обработку.

---

##6.3. Idempotent side effectsСамое сложное — внешние вызовы.

Примеры:
- отправка email- списание денег- вызов партнерского APIНужно:
- использовать external idempotency keys- или таблицу “executed_operations”
- или transactional outbox/inbox pattern---

#7. Выбор технологии хранения статусаЗависит от паттерна чтения/записи.

## Если очень много writes, мало сложных запросовЛучше:
- Cassandra / ScyllaПлюсы:
- горизонтальное масштабирование- высокая write throughput- низкая latencyМинусы:
- сложнее модель данных- ограниченные ad-hoc queries## Если нужен сильный ACID и умеренная нагрузкаМожно:
- PostgreSQL + shardingНо для50k RPS как single primary — уже рискованно.

## Если облако- DynamoDB часто отличный выбор:
- managed - autoscaling - conditional writes для dedup/idempotency---

#8. ПартиционированиеДля50k RPS это обязательный элемент.

## Kafka partitionsНапример:
- `tasks.main` =128–512 partitions на старте- количество зависит от throughput, message size, числа consumers, retentionКлюч партиционирования:
- `task_id`
  или- `customer_id`, если важен порядок внутри клиента### Если нужен порядокЕсли важно, чтобы задачи одного клиента шли последовательно:
- partition key = `customer_id`

Но это ухудшает равномерность распределения при hot keys.

---

## Хранилище статусаPartition key:
- `task_id`
  или- `(tenant_id, task_id)`

Если multi-tenant — лучше включать tenant в ключ.

---

#9. Retry strategyНельзя делать retry “в лоб” мгновенно, иначе получите retry storm.

## Нужны:
- exponential backoff- jitter- ограничение max attempts- DLQПример:
  -1-я ошибка → retry через1 мин-2-я → через5 мин-3-я → через30 мин- затем DLQ## Важное разделение ошибок- **Transient**: timeout,503, network issue → retry- **Permanent**: validation error, malformed payload, business rejection → DLQ / fail---

#10. Как уложиться в latency <100msЕсли речь про прием задачи:

## Критический путь:
1. LB2. Ingestion service3. Kafka produce `acks=all`
4. Ответ клиентуЧтобы это было <100ms p95/p99, нужно:

- держать ingestion stateless и легким- не делать тяжелых синхронных операций- не писать синхронно в несколько систем на критическом пути- использовать локальный регион / AZ-aware deployment- держать payload небольшим- использовать connection pooling- batch/linger в Kafka очень аккуратно, чтобы не ухудшить latency- replication factor3, быстрые SSD, хорошая сеть### Что не стоит делать на sync path:
- тяжелые JOIN в БД- внешние HTTP calls- сложную бизнес-логику- антивирус/архив/большие трансформации---

#11. Масштабирование## Горизонтально масштабируются:
- API Gateway- Ingestion Service- Worker Service- Kafka brokers- DB nodes- Redis nodes## Как масштабировать:
- ingestion — по CPU / request rate / p95 latency- workers — по consumer lag / processing latency- Kafka — через увеличение partitions и brokers- DB — через добавление нод, шардирование## Автоскейлинг сигналы:
- RPS- p95 latency- queue lag- CPU/memory- error rate---

#12. Отказоустойчивость## Нужно заложить:
- deployment минимум в3 AZ- Kafka replication factor =3- `min.insync.replicas =2`
- DB replication- rolling deployments- graceful shutdown у воркеров- readiness/liveness probes- backpressure## Graceful shutdown для worker:
- перестать брать новые сообщения- завершить текущие- коммитнуть offsets- затем выключиться---

#13. Backpressure и защита системыНа50k RPS это обязательно.

## На входе:
- rate limiting на tenant/client- quotas- admission control## На обработке:
- ограничение concurrency в worker- circuit breaker на downstream- bulkhead isolation- bounded retry- queue lag based throttlingЕсли downstream начинает тормозить:
- лучше замедлить intake для части клиентов- чем положить всю систему---

#14. API контракт## POST /tasksHeaders:
- `Idempotency-Key`

Body:
```json{
 "type": "generate_report",
 "tenant_id": "t1",
 "payload": {
 "report_id":123 }
}
```

Response:
```json{
 "task_id": "01HXYZ...",
 "status": "accepted"
}
```

## GET /tasks/{task_id}
Response:
```json{
 "task_id": "01HXYZ...",
 "status": "processing",
 "attempt":2,
 "created_at": "2026-04-18T13:00:00Z"
}
```

---

#15. Модель данных статуса задачиПример:

```json{
 "task_id": "uuid",
 "tenant_id": "t1",
 "idempotency_key": "uuid",
 "status": "accepted|processing|done|failed|retrying",
 "attempt_count":2,
 "payload_hash": "sha256...",
 "result_ref": "s3://bucket/result/...",
 "error_code": "TIMEOUT",
 "created_at": "...",
 "updated_at": "...",
 "next_retry_at": "..."
}
```

---

#16. Важный architectural decision: Kafka-first vs DB-first## Вариант A: Kafka-firstКлиентский запрос -> Kafka -> ответ### Плюсы:
- минимальный latency- высокая throughput- проще ingest path### Минусы:
- статус задачи нужно потом материализовать отдельно- сложнее query-by-task если не сохраняете metadata сразу## Вариант B: DB + OutboxКлиентский запрос -> DB transaction -> outbox -> Kafka### Плюсы:
- сильнее консистентность бизнес-состояния- удобно хранить статус и дедуп прямо в DB### Минусы:
- выше latency- выше нагрузка на DB- сложнее держать50k RPS### Мой выборДля ваших требований:
- **Kafka-first для ingest**
- **асинхронная материализация статуса**
- при необходимости — быстрый metadata write в scalable KV store---

#17. Рекомендуемый стекОдин из практичных стеков:

- **LB/API Gateway**: Envoy / NGINX- **Ingestion Service**: Go / Java / Kotlin- **Broker**: Kafka- **Schema**: Avro / Protobuf + Schema Registry- **Workers**: Go / Java- **Task State Store**: ScyllaDB / Cassandra / DynamoDB- **Cache / short dedup**: Redis- **Observability**: Prometheus, Grafana, Loki/ELK, Jaeger/Tempo, OpenTelemetry- **Orchestration**: KubernetesПочему Go/Java:
- хорошие Kafka клиенты- predictable performance- удобно держать high concurrency---

#18. Минимальная схема развертывания## По регионамЕсли один регион:
-3 AZ- Kafka cluster3–5 brokers- DB cluster3+ nodes- ingestion replicas10–50+
- worker replicas по нагрузке## Если multi-regionНужно решить:
- active-passiveили- active-activeДля начала я бы рекомендовал:
- **single region, multi-AZ**
- multi-region DR как следующий этапПотому что active-active сильно усложняет idempotency, ordering и dedup.

---

#19. Основные риски##1. Exactly-once хотят “на словах”, а пишут at-least-onceНужно явно зафиксировать:
- дубликаты возможны- downstream должен быть идемпотентен##2. Синхронные тяжелые операции на ingest pathЭто убьет <100ms.

##3. Hot partitionsЕсли partition key выбран плохо, часть брокеров/воркеров будет перегружена.

##4. Retry stormБез backoff + jitter система сама себя положит.

##5. Отсутствие backpressureПри деградации downstream нагрузка накопится и выбьет все слои.

---

#20. Предлагаемый финальный дизайн## High-level architecture```textClient -> API Gateway / LB -> Ingestion Service -> Kafka (tasks.main)
-> Task Metadata Store (optional sync/lightweight or async materialization)

Kafka -> Worker Group -> Business Processing -> Result Store / Downstream APIs -> Task Metadata Store -> Retry Topics / DLQ```

---

#21. Ключевые решения## Я бы предложил так:

### Ingest- stateless ingestion-service- publish в Kafka с `acks=all`
- response `202 Accepted` после durable append- idempotency key обязателен### Queue/Broker- Kafka- replication factor3- много partitions- producer idempotence enabled### Processing- consumer groups- manual offset commit only after processing- retry topics + DLQ- exponential backoff### State- отдельное хранилище статусов задач- Scylla/Cassandra/DynamoDB- idempotent writes / conditional updates### Reliability- multi-AZ- backpressure- rate limits- observability- autoscaling by lag and latency---

#22. Если нужно сформулировать коротко “архитектурный ответ на интервью”

Можно ответить так:

> Я бы построил систему как асинхронный pipeline: stateless ingestion layer принимает задачи через LB, валидирует и публикует их в Kafka с `acks=all`, что дает durable acceptance и позволяет удерживать latency приема <100ms. Далее горизонтально масштабируемые worker'ы читают сообщения через consumer groups, обрабатывают их и коммитят offset только после успешного завершения, что обеспечивает at-least-once delivery. Для борьбы с дублями вводится idempotency key на уровне API и idempotent processing на уровне worker'ов. Статусы задач и attempt counters хранятся в масштабируемом KV/wide-column store вроде ScyllaDB/Cassandra или DynamoDB. Для ошибок используются retry topics с exponential backoff и DLQ. Вся система разворачивается stateless + partitioned, с autoscaling по RPS и consumer lag, и с полной observability по latency, lag, retries и DLQ.

---

Если хочешь, я могу следующим сообщением дать еще **3 артефакта**:
1. **C4/текстовую схему компонентов**,2. **список нефункциональных требований и trade-offs**,3. **пример ответа в формате system design interview на5–7 минут**.