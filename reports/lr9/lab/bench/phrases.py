# (spoken text, expected action)
EN_COMMANDS = [
    ("search for machine learning applications", "navigate_search"),
    ("clear search", "clear_query"),
    ("read this", "read_document"),
    ("stop reading", "stop_speaking"),
    ("go to crawling", "navigate_to_crawl"),
    ("go to collections", "navigate_to_collections"),
    ("go to search", "navigate_to_search"),
    ("go to metrics", "navigate_to_metrics"),
    ("go to language identification", "navigate_to_lang_id"),
    ("go to summarization", "navigate_to_summarization"),
    ("go to translation", "navigate_to_translation"),
    ("go to settings", "navigate_to_settings"),
    ("go to help", "navigate_to_help"),
]
RU_COMMANDS = [
    ("найди нейронные сети для машинного перевода", "navigate_search"),
    ("очисти запрос", "clear_query"),
    ("прочитай это", "read_document"),
    ("хватит читать", "stop_speaking"),
    ("перейди к краулингу", "navigate_to_crawl"),
    ("перейди к коллекциям", "navigate_to_collections"),
    ("перейди к поиску", "navigate_to_search"),
    ("перейди к метрикам", "navigate_to_metrics"),
    ("перейди к определению языка", "navigate_to_lang_id"),
    ("перейди к реферированию", "navigate_to_summarization"),
    ("перейди к переводу", "navigate_to_translation"),
    ("перейди к настройкам", "navigate_to_settings"),
    ("перейди к справке", "navigate_to_help"),
]
# Non-command sentences (CS domain); last two are deliberate hard negatives containing a command phrase.
EN_NEGATIVES = [
    "The model converges after ten epochs of training.",
    "We evaluate the algorithm on three public benchmarks.",
    "Neural networks learn distributed representations of words.",
    "The crawler downloads pages and stores them in a database.",
    "Precision and recall are computed for every query.",
    "The search for optimal hyperparameters is expensive.",
    "Please go to the next section of the article.",
]
RU_NEGATIVES = [
    "Модель сходится после десяти эпох обучения.",
    "Алгоритм проверен на трёх открытых наборах данных.",
    "Нейронные сети обучают векторные представления слов.",
    "Полнота и точность вычисляются для каждого запроса.",
    "Мы искали оптимальные гиперпараметры несколько дней.",
]
# Scientific-domain sentences for WER (reference text = what was synthesized).
EN_SENTENCES = [
    "Recent advances in deep learning have transformed natural language processing.",
    "We represent each document as a weighted vector of terms.",
    "Documents are ranked by the cosine similarity to the query vector.",
    "The proposed indexing module updates the vocabulary incrementally.",
    "Experiments show that the vector model outperforms boolean retrieval.",
    "Term frequency and inverse document frequency are combined into one weight.",
    "The transformer architecture relies entirely on self-attention mechanisms.",
    "Stemming and lemmatization reduce inflected words to a common base form.",
    "A support vector machine finds the hyperplane that separates the two classes.",
    "Cross-lingual embeddings allow searching documents in several languages at once.",
]
RU_SENTENCES = [
    "Развитие глубокого обучения изменило обработку естественного языка.",
    "Каждый документ представляется взвешенным вектором термов.",
    "Документы ранжируются по косинусной мере сходства с запросом.",
    "Предложенный модуль индексирования обновляет словарь инкрементально.",
    "Эксперименты показывают, что векторная модель превосходит булев поиск.",
]
