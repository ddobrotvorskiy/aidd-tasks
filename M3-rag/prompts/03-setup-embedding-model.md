Установи embedding-модель {МОДЕЛЬ_НА_ВЫБОР} для векторизации наших
чанков. Варианты:

- BGE-M3 локально через Ollama: ollama pull bge-m3 (или через
  sentence-transformers). Бесплатно, multilingual, ~1024 dim.
- Cohere multilingual v3: managed API, $0.10/1M токенов, ключ в .env.
- OpenAI text-embedding-3-small: managed API, $0.02/1M токенов.
- Voyage-3-large: managed API, лучшая на коде (если важен код-domain).
- Ollama nomic-embed-text / mxbai-embed-large: бесплатно локально.

Я выбрал {МОДЕЛЬ}, объясни setup для неё, какой клиент использовать,
куда писать ключ если managed.