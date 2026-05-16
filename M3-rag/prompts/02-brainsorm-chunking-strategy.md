Подними локально Postgres с pgvector extension в Docker.

Готовый образ pgvector/pgvector:pg17 — единственная команда
docker run + он сразу включает extension. Самый быстрый путь.

После запуска подключись
через psql или DBeaver, проверь что extension доступен (\dx должен
показать vector). Логин/пароль положи в .env, connection string
тоже туда.
