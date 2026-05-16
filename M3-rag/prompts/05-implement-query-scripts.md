Напиши query script: функция search(query, top_k=5) которая:
1. Эмбеддирует запрос той же моделью что использовалась для ingestion .
2. Cosine similarity поиск в Vector DB.
3. Опционально: pre-filter по type / source_file из payload
4. Возвращает top-K результатов с метаданными.

Прогони через этот script 3 тестовых запроса и покажи мне результаты
текстом (без агента, прямой вызов script через CLI):

1. "Какая БД используется в proshop_mern и почему именно она?"
   (factual single-hop, ожидаем chunk из adrs/adr-001-mongodb...)
2. "Какие фичи зависят от search_v2?"
   (multi-hop dependency, ожидаем `semantic_search` через
   feature-flags-spec.md / features/catalog.md / dev-history.md)
3. "Что случилось во время последнего incident с checkout?"
   (filter by type + retrieval, ожидаем из incidents/)

Покажи top-3 chunks по каждому запросу с score и source_file. Если
какие-то результаты странные — обсудим, может починим chunking или
параметры запроса.