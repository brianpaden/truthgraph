# V1 Tool Stack Ideas

Great question. Here’s a pragmatic menu of **stacks & languages** that work well for an automated fact-checker—organized by component, with a “mainstream & fast to ship” pick and an “alternative/high-perf” option.

## Core languages (rule of thumb)

* **Python** — ML/NLP/CV, rapid prototyping, rich ecosystem.
* **TypeScript** — front-end (React/Next.js) + some back-end (Node/NestJS) for product polish.
* **Go or Rust** — high-throughput microservices (retrieval, streaming, parsers) once you need speed.
* **Java** — if you’re embedding deeply in Lucene/Elasticsearch/OpenSearch plugins.

## Ingestion & preprocessing

* **HTML/PDF**: `trafilatura`, `readability-lxml`, `pdfminer.six` / `PyMuPDF`; alt: Apache Tika.
* **OCR**: `Tesseract` or Microsoft **TrOCR** (HF); alt: PaddleOCR.
* **Doc layout**: `layoutparser`, `detectron2`, LayoutLMv3.
* **ASR (audio/video)**: OpenAI **Whisper**; alt: Vosk, NVIDIA NeMo.
* **Vision utils**: OpenCV; chart/table: ChartOCR, DePlot, ChartQA baselines.

## NLP (claims, NER, normalization)

* **Tokenization & NER**: spaCy; alt: Stanza.
* **Transformers**: Hugging Face **Transformers/Datasets** (PyTorch first; TF optional).
* **Claim detection/NLI**: HF models (DeBERTa/RoBERTa); alt: AllenNLP stacks.
* **Entity linking**: `blink`/`REL` to Wikidata; alt: spaCy + custom candidate gen.

## Retrieval (hybrid RAG)

* **Sparse**: **OpenSearch/Elasticsearch** (BM25 + ANN plugins).
  Alt: **Vespa** (built-in ranking/ANN), or **Lucene** custom.
* **Dense vectors**: **FAISS** (Python/C++), **Milvus** or **Qdrant** if you want a DB server; alt: **pgvector** in Postgres.
* **Reranking**: cross-encoder (HF); production rerank: Jina Rerankers or ColBERT-v2.

## Temporal & versioned corpora

* **Snapshotting**: object store (S3/MinIO) + Parquet/Delta Lake; **DuckDB** for local analytics.
* **Temporal filters**: store `published_at` and index in OpenSearch;
  optional: temporal KGs (HyTE/T-TransE) via **PyKEEN**.

## Reasoning (symbolic + neural)

* **Symbolic**: Python rules + `sympy` (math), `dateutil` (time), `json-logic`/custom DSL; alt: **SWI-Prolog** or **Logtalk** for serious logic.
* **Neural**: NLI for entailment (DeBERTa-v3-large), shallow CoT verifier.
* **Hybrid**: **DeepProbLog** / `lark` parser for claims → logical forms.

## Knowledge graph & provenance

* **Graph DB**: **Neo4j** (property graph) for dev speed; alt: RDF stores (GraphDB, Blazegraph, Apache Jena, AWS Neptune) if you want **PROV-O/Nanopub** compatibility out of the box.
* **Ontology**: **PROV-O**, OWL-Time, schema.org **ClaimReview**; **RDFLib** (Python) to emit JSON-LD.

## Multimodal verification

* **Image/text alignment**: CLIP (OpenCLIP); alt: SigLIP.
* **Captioning/VQA**: LLaVA / Qwen-VL for hints (never sole ground truth).
* **Reverse-image**: integrate third-party APIs or your own CLIP index.

## Evaluation & QA

* **Metrics**: FEVER score, Macro-F1, Recall@k/MRR, FActScore;
  **RAGAS** for RAG faithfulness; **SelfCheckGPT** style self-consistency.
* **Experiment tracking**: **Weights & Biases** or **MLflow**.
* **Testing**: `pytest`, **Hypothesis** (property-based), Great Expectations for data.

## Orchestration, pipelines, and serving

* **API**: **FastAPI** (Python); alt: **Falcon** or **Litestar**; in TS: **NestJS**.
* **Batch/flows**: **Prefect** (friendly) or **Airflow** (enterprise).
* **Distributed**: **Ray** for parallel eval/finetunes; alt: Dask.
* **Streaming bus**: **Kafka** or **NATS** for the “Fact Reasoning Bus”.

## Storage & indexing

* **Object store**: S3/MinIO (raw docs, OCR, models).
* **Warehouse**: **Parquet** + **DuckDB** (dev) / **Delta Lake** on S3 (prod).
* **Relational**: Postgres (+ **pgvector**) for metadata and small vectors.
* **Cache**: Redis.

## MLOps, deployment & observability

* **Containers**: Docker; **Kubernetes** + **Helm** for prod.
* **CI/CD**: GitHub Actions; alt: GitLab CI.
* **Observability**: **Prometheus + Grafana**, **OpenTelemetry**, **Loki** (logs), **Sentry** (errors).
* **Security**: OAuth2/OIDC (Auth0/Keycloak), **OPA** for policy; secrets via **Vault**/KMS.

## Front-end (editor & public UI)

* **Djanjo**

---

## Suggested “v1” stack (fastest path that still scales)

* **Langs**: Python (all services) + TypeScript (UI).
* **Retrieval**: OpenSearch (BM25) + FAISS (dense) with Contriever-class embeddings; cross-encoder rerank.
* **Models**: HF Transformers (DeBERTa-v3 for NLI; MiniLM for embed baseline).
* **Pipelines**: FastAPI microservices; Prefect flows; Kafka as event bus when needed.
* **Data**: Parquet/Delta on S3; Postgres (+pgvector) for metadata; Neo4j for provenance.
* **Multimodal**: Whisper (ASR), Tesseract/TrOCR (OCR), CLIP index for images; chart parser (ChartQA baseline).
* **Ops**: Docker + k8s; Prometheus/Grafana; W&B for experiments.
* **Standards**: PROV-O/JSON-LD emission; ClaimReview publishing.

## When to introduce Go/Rust

* You hit **>1000 RPS** on retrieval/rerank or need **low-latency** stream processing (claim firehose). Port hot paths (query planners, converters) to Go; keep ML in Python.
