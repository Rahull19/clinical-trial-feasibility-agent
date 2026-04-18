# Clinical Trial Feasibility & Site Selection Agent

A **production-grade FastAPI backend** built with **LangGraph** and **Clean Architecture** for evaluating clinical trial feasibility and selecting optimal sites using AI-driven orchestration with **multi-LLM provider support**, **async PostgreSQL**, and **RAG-powered insights**.

**Version:** 4.0.0  
**Architecture:** Clean Architecture with DDD principles  
**Database:** PostgreSQL (async via asyncpg)  
**Vector Store:** ChromaDB for RAG retrieval  

---

## 🎯 Overview

This system uses **LangGraph** as the orchestration engine and **FastAPI** as the web framework to evaluate clinical trial protocols through a multi-stage AI pipeline:

- **Protocol parsing** from PDF, DOCX, or JSON files with LLM-powered extraction
- **Data enrichment** from PostgreSQL + ChromaDB RAG + fallback defaults
- **Country-level feasibility** scoring with configurable weights
- **Site selection** and investigator matching (DB → RAG → fallback)
- **Risk assessment** and compliance validation
- **Human-in-the-loop** review (CLI or API modes)
- **Final recommendation** generation with structured output

### **Key Features**

✅ **Clean Architecture**: Strict layer separation (core → domain → application → infrastructure)  
✅ **Async-First**: Full async/await with asyncpg and SQLAlchemy 2.0  
✅ **Dependency Injection**: Centralized DI container managing all singletons  
✅ **Multi-LLM Provider Support**: OpenAI, Groq, Gemini, xAI (Grok)  
✅ **PostgreSQL + ChromaDB**: Structured data + vector search for historical trials  
✅ **File Ingestion**: PDF, DOCX, JSON with automatic parser routing  
✅ **Structured Logging**: Correlation IDs for end-to-end request tracing  
✅ **Type Safety**: Frozen dataclasses for domain entities, Pydantic for API/state  
✅ **Production-Ready**: Comprehensive error handling, retry mechanisms, graceful degradation  

---

## 🏗️ Architecture

### **Clean Architecture Layers**

```
┌─────────────────────────────────────────────────────────────┐
│  API Layer (FastAPI routes, Pydantic schemas)              │
├─────────────────────────────────────────────────────────────┤
│  Application Layer (Use Cases, Service Engines)            │
├─────────────────────────────────────────────────────────────┤
│  Domain Layer (Entities, Value Objects, Port Interfaces)   │
├─────────────────────────────────────────────────────────────┤
│  Infrastructure Layer (DB, RAG, LLM, Cache implementations) │
└─────────────────────────────────────────────────────────────┘
```

### **Core Principles**

- **Dependency Inversion**: Domain defines interfaces, infrastructure implements them
- **Single Responsibility**: Each service has one clear purpose
- **Separation of Concerns**: Graph orchestration decoupled from business logic
- **Immutability**: Domain entities are frozen dataclasses
- **Type Safety**: Pydantic models for validation, dataclasses for domain
- **Async-First**: All I/O operations are non-blocking

### **Folder Structure**

```
app/
├── core/                         # Foundation layer
│   ├── config.py                 # AppConfig with all magic numbers
│   ├── container.py              # DI container (singleton)
│   ├── logging.py                # Structured logging with correlation_id
│   └── exceptions.py             # Domain exception hierarchy
│
├── domain/                       # Pure business logic (no framework deps)
│   ├── models/                   # Immutable entities (frozen dataclasses)
│   │   ├── trial.py              # TrialEntity
│   │   ├── country.py            # CountryEntity
│   │   ├── site.py               # SiteEntity
│   │   └── investigator.py       # InvestigatorEntity
│   ├── value_objects/            # Score/risk types with invariants
│   │   ├── scores.py             # CountryScore, SiteScore, FeasibilityScore
│   │   └── risk.py               # RiskScore, RiskLevel
│   └── interfaces/               # Port interfaces (abstract contracts)
│       ├── repositories.py       # Trial/Country/Site/Investigator ports
│       ├── rag.py                # RAGPort
│       ├── llm.py                # LLMPort (async)
│       └── cache.py              # CachePort
│
├── application/                  # Use cases and service engines
│   ├── use_cases/
│   │   ├── analyze_trial.py      # Orchestrates full analysis pipeline
│   │   └── ingest_trial.py       # Orchestrates ingestion pipeline
│   └── services/                 # Stateless business logic
│       ├── protocol_parser.py
│       ├── enrichment_engine.py  # DataFetcher + RAGAugmenter + MetadataNormaliser
│       ├── scoring_engine.py     # CountryScorer + SiteScorer + FeasibilityScorer
│       ├── site_selector.py      # SiteFetcher + SiteSelector (3-tier)
│       ├── investigator_matcher.py
│       ├── risk_engine.py
│       ├── compliance_engine.py
│       └── report_generator.py
│
├── infrastructure/               # Framework implementations
│   ├── db/
│   │   ├── session.py            # Async + sync engines, session context manager
│   │   ├── models.py             # SQLAlchemy ORM models
│   │   └── repositories/         # Async repository implementations
│   │       ├── trial_repository.py
│   │       ├── country_repository.py
│   │       ├── site_repository.py
│   │       └── investigator_repository.py
│   ├── rag/
│   │   ├── embedding_service.py  # Async embeddings (OpenAI + sentence-transformers)
│   │   └── chroma_adapter.py     # Async ChromaDB wrapper
│   ├── llm/
│   │   └── adapter.py            # Wraps sync BaseLLM → async LLMPort
│   └── cache/
│       └── memory_cache.py       # In-memory cache with TTL (Redis-swappable)
│
├── graph/                        # LangGraph orchestration
│   ├── state.py                  # Lightweight Pydantic TrialState
│   └── builder.py                # DI-powered graph with inline thin nodes
│
├── api/                          # FastAPI layer
│   ├── routes/
│   │   ├── trial.py              # POST /analyze-trial (thin, delegates to use case)
│   │   └── ingestion.py          # POST /ingest-trial
│   └── schemas/
│       ├── request.py            # Pydantic request models
│       └── response.py           # Pydantic response models
│
├── llm/                          # LLM provider implementations (kept from v1)
│   ├── base_llm.py               # Abstract base class
│   ├── openai_provider.py
│   ├── groq_provider.py
│   ├── gemini_provider.py
│   └── xai_provider.py
│
├── parsing/                      # File parsers (kept from v1)
│   ├── base_parser.py
│   ├── pdf_parser_class.py
│   ├── docx_parser_class.py
│   ├── json_parser_class.py
│   ├── parser_factory.py
│   └── llm_extraction_service.py
│
├── human/                        # Human-in-the-loop (kept from v1)
│   └── reviewer.py               # CLI/API review modes
│
├── prompts/                      # Prompt templates (kept from v1)
│   ├── extraction_prompts.py
│   └── report_prompts.py
│
└── main.py                       # FastAPI entry point with DI container

.env                              # Environment variables (CTA_* prefix)
requirements.txt                  # Dependencies with async support
README.md
```

---

## 🔄 Graph Flow

```
protocol_parser
    ↓
data_enrichment ←──┐ (retry on missing data)
    ↓              │
country_feasibility
    ↓
site_selection ←───┐ (retry on low feasibility)
    ↓              │
investigator_matching
    ↓
risk_scoring
    ↓
compliance_validator
    ↓
feasibility_scoring
    ↓
human_review ←─────┘ (approve/reject/request_changes)
    ↓
report_generator
    ↓
END
```

### **Conditional Routing**

1. **After enrichment**: Retry if missing data (max 2 attempts) → human review if exhausted
2. **After country scoring**: Stop if no valid countries
3. **After risk scoring**: Route to human review if high-risk entities detected
4. **After compliance**: Retry country feasibility if issues found (max 1 attempt)
5. **After feasibility scoring**: Retry site selection if score below threshold
6. **After human review**:
   - `approve` → generate report
   - `reject` → re-run risk scoring
   - `request_changes` → re-run site selection

---

## 🤖 Multi-LLM Provider Support

### **Supported Providers**

| Provider | Model | Status |
|----------|-------|--------|
| **OpenAI** | gpt-3.5-turbo | ✅ Working (free tier) |
| **Groq** | llama-3.3-70b-versatile | ✅ Working |
| **Gemini** | gemini-2.5-flash | ✅ Working |
| **xAI** | grok-beta | ⚠️ Requires credits |

### **Provider Architecture**

```python
class BaseLLM(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate completion from LLM."""
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and available."""
```

All providers implement this interface, making them **interchangeable** throughout the system.

### **Dynamic Provider Selection**

**Via API:**
```bash
curl -X POST http://localhost:8000/analyze-trial \
  -F "file=@protocol.json" \
  -F "llm_provider=groq"  # or openai, gemini, xai
```

**Via Environment:**
```bash
CTA_DEFAULT_LLM_PROVIDER=groq
```

---

## 📊 State Model

The lightweight `TrialState` Pydantic model flows through the entire pipeline:

```python
class TrialState(BaseModel):
    # ── Input ─────────────────────────────────────────────────────
    protocol_data: Dict[str, Any] = Field(default_factory=dict)
    
    # ── Parsed ────────────────────────────────────────────────────
    parsed_criteria: Dict[str, Any] = Field(default_factory=dict)
    
    # ── Entities ──────────────────────────────────────────────────
    countries: List[Dict[str, Any]] = Field(default_factory=list)
    sites: List[Dict[str, Any]] = Field(default_factory=list)
    investigators: List[Dict[str, Any]] = Field(default_factory=list)
    
    # ── Scores ────────────────────────────────────────────────────
    country_scores: Dict[str, float] = Field(default_factory=dict)
    site_scores: Dict[str, float] = Field(default_factory=dict)
    risk_scores: Dict[str, float] = Field(default_factory=dict)
    feasibility_score: float = 0.0
    
    # ── Flags ─────────────────────────────────────────────────────
    compliance_flags: List[str] = Field(default_factory=list)
    missing_data_flags: List[str] = Field(default_factory=list)
    
    # ── Human Review ──────────────────────────────────────────────
    human_feedback: Optional[str] = None
    approval_status: Optional[str] = None
    
    # ── Output ────────────────────────────────────────────────────
    final_recommendation: Optional[Dict[str, Any]] = None
    
    # ── Retry Counters ────────────────────────────────────────────
    enrichment_retry_count: int = 0
    compliance_retry_count: int = 0
    site_reselection_retry_count: int = 0
```

**Note:** LangGraph nodes return *partial* dicts with only the fields they update. The framework merges these into the state automatically.

---

## 🚀 Getting Started

### **Prerequisites**

- Python 3.11+
- pip
- API keys for LLM providers (see Configuration)

### **Installation**

```bash
# Clone the repository
cd clinical_trails_agent_langGraph

# Install dependencies
pip install -r requirements.txt
```

### **Configuration**

1. Create a `.env` file in the project root:

```bash
# ── LLM Provider API Keys ────────────────────────────────────────
CTA_OPENAI_API_KEY=your_openai_key_here
CTA_GROQ_API_KEY=your_groq_key_here
CTA_GEMINI_API_KEY=your_gemini_key_here
CTA_XAI_API_KEY=your_xai_key_here

# ── Application Settings ─────────────────────────────────────────
CTA_DEFAULT_LLM_PROVIDER=groq
CTA_LOG_LEVEL=INFO

# ── Scoring Thresholds ───────────────────────────────────────────
CTA_COUNTRY_SCORE_THRESHOLD=0.5
CTA_SITE_SCORE_THRESHOLD=0.4
CTA_RISK_SCORE_THRESHOLD=0.7
CTA_FEASIBILITY_SCORE_THRESHOLD=0.6

# ── Retry Limits ─────────────────────────────────────────────────
CTA_MAX_ENRICHMENT_RETRIES=2
CTA_MAX_COMPLIANCE_RETRIES=1
CTA_MAX_SITE_RESELECTION_RETRIES=1

# ── PostgreSQL (Async) ───────────────────────────────────────────
CTA_DATABASE_URL=postgresql+asyncpg://postgres:1234@localhost:5432/clinical_trials
CTA_DATABASE_URL_SYNC=postgresql://postgres:1234@localhost:5432/clinical_trials
CTA_DB_POOL_SIZE=5
CTA_DB_MAX_OVERFLOW=10

# ── RAG / Vector DB ──────────────────────────────────────────────
CTA_RAG_PROVIDER=chroma
CTA_CHROMA_PERSIST_DIRECTORY=./chroma_data

# ── Embedding ────────────────────────────────────────────────────
CTA_EMBEDDING_PROVIDER=sentence_transformers
CTA_EMBEDDING_MODEL=all-MiniLM-L6-v2
CTA_EMBEDDING_DIMENSION=1536

# ── Cache ────────────────────────────────────────────────────────
CTA_CACHE_TTL_SECONDS=300
CTA_CACHE_MAX_SIZE=1000

# ── Server Configuration ─────────────────────────────────────────
CTA_HOST=0.0.0.0
CTA_PORT=8000
```

2. Get your API keys:
   - **OpenAI**: https://platform.openai.com/api-keys
   - **Groq**: https://console.groq.com/keys
   - **Gemini**: https://aistudio.google.com/app/apikey
   - **xAI**: https://console.x.ai

3. Create the PostgreSQL database:

```sql
CREATE DATABASE clinical_trials;
```

The application will create the required tables automatically on startup via `init_db()`.

### **Run the Application**

**FastAPI Server (API Mode):**
```bash
python -m app.main
# Server runs on http://0.0.0.0:8000
```

**CLI Mode (Interactive):**
```bash
python -m app.main --cli
# Prompts for human review via terminal
```

### **Test the API**

```bash
# Health check
curl http://localhost:8000/health

# Analyze trial with file upload
python scripts/test_api.py
```

---

## 🌐 API Endpoints

### **POST /analyze-trial**

Analyze a clinical trial protocol with file upload.

**Request:**
```bash
curl -X POST http://localhost:8000/analyze-trial \
  -F "file=@protocol.json" \
  -F "llm_provider=groq"
```

**Parameters:**
- `file` (required): Protocol file (PDF, DOCX, or JSON)
- `llm_provider` (optional): LLM provider to use (openai, groq, gemini, xai)
  - Defaults to `CTA_DEFAULT_LLM_PROVIDER` from config

**Response:**
```json
{
  "status": "success",
  "llm_provider": "Groq",
  "filename": "protocol.json",
  "recommendation": {
    "protocol_id": "TEST-001",
    "feasibility_score": 0.7018,
    "recommendation": "FEASIBLE",
    "summary": {
      "total_countries": 3,
      "total_sites": 5,
      "total_investigators": 5,
      "compliance_issues": 0
    },
    "country_details": [...],
    "site_details": [...],
    "investigator_details": [...]
  }
}
```

### **POST /ingest-trial**

Ingest a historical trial document into PostgreSQL and ChromaDB.

**Request:**
```bash
curl -X POST http://localhost:8000/ingest-trial \
  -F "file=@historical_trial.pdf" \
  -F "llm_provider=groq"
```

**What it does:**

- Parses the uploaded PDF/DOCX/JSON
- Extracts structured metadata using the existing parsing pipeline
- Stores structured entities in PostgreSQL
- Indexes the raw text in ChromaDB under the `trials` collection

**Response:**
```json
{
  "status": "success",
  "data": {
    "protocol_id": "CTA-2024-ONCO-101",
    "status": "ingested",
    "title": "Phase III Study in NSCLC",
    "therapeutic_area": "Oncology",
    "phase": "Phase III",
    "countries_stored": 4,
    "sites_stored": 2,
    "investigators_stored": 2,
    "rag_documents_indexed": 1
  }
}
```

### **GET /health**

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "4.0.0"
}
```

---

## 📝 Application Layer

### **Use Cases** (Top-level orchestrators)

- **AnalyzeTrialUseCase**: Orchestrates full analysis pipeline (parse → build graph → invoke → return)
- **IngestTrialUseCase**: Orchestrates ingestion (parse → DB store → RAG index)

### **Service Engines** (Stateless business logic)

Each service is **independent of LangGraph** and can be tested/used standalone:

- **ProtocolParser**: Parses and validates protocol documents, extracts criteria
- **EnrichmentEngine**: 3-tier enrichment (DB → RAG → fallback defaults)
  - `DataFetcher`: Queries PostgreSQL for country data
  - `RAGAugmenter`: Finds similar trials via ChromaDB
  - `MetadataNormaliser`: Normalizes country names to codes
- **CountryScorer**: Scores countries based on patient pools, regulations, startup time
- **SiteSelector**: Multi-tier site selection (DB → RAG → fallback catalogue)
  - `SiteFetcher`: 3-tier fetching strategy
  - `SiteScorer`: Scores sites on performance, capacity, enrollment fit
- **InvestigatorMatcher**: Multi-tier investigator matching (DB → RAG → fallback)
  - `InvestigatorFetcher`: 3-tier fetching strategy
  - `InvestigatorScorer`: Scores on experience and publications
- **RiskEngine**: Computes risk scores across countries and sites
- **ComplianceEngine**: Validates regulatory compliance with rule-based checks
- **FeasibilityScorer**: Aggregates weighted feasibility score
- **ReportGenerator**: Generates final structured recommendation report

---

## 🔍 Logging

All nodes and services log execution details:

```
2026-04-09 12:52:40 | INFO | app.graph.nodes | [protocol_parser_node] START
2026-04-09 12:52:40 | INFO | app.services.protocol_service | Protocol parsed — id=CTA-2025-ONCO-0042
2026-04-09 12:52:40 | INFO | app.graph.nodes | [protocol_parser_node] END — missing_flags=0
```

---

## 🛡️ Error Handling

- **Custom exception hierarchy** in `app/utils/exceptions.py`
- **Graceful degradation**: Nodes return partial updates on failure
- **Retry mechanisms**: Automatic retries for transient failures
- **Validation**: Pydantic models enforce data integrity

---

## 🔄 Extending the System

### **Add a New Service**

1. Create service class in `app/application/services/`
2. Inject dependencies via `__init__` (config, db_session, rag, etc.)
3. Implement async business logic methods
4. Add service instantiation in `app/graph/builder.py`
5. Call from appropriate inline node function

### **Add a New Repository**

1. Define port interface in `app/domain/interfaces/repositories.py`
2. Create implementation in `app/infrastructure/db/repositories/`
3. Map between ORM models and domain entities
4. Use async SQLAlchemy session from `DatabaseSession`

### **Add a New LLM Provider**

1. Create provider class in `app/llm/` implementing `BaseLLM`
2. Add factory method in `app/core/container.py` → `_build_llm()`
3. Register in `_REGISTRY` dict with provider name
4. Add API key to `.env` with `CTA_` prefix

### **Modify State**

1. Update `TrialState` in `app/graph/state.py`
2. Update inline node functions in `app/graph/builder.py` to return new fields
3. Update conditional routing functions if needed

### **Swap Infrastructure**

All infrastructure is swappable via ports:
- **Cache**: Implement `CachePort` (e.g., Redis adapter)
- **RAG**: Implement `RAGPort` (e.g., Milvus adapter)
- **Database**: Swap `asyncpg` for another async driver
- Update `app/core/container.py` to instantiate new implementations

---

## 📦 Dependencies

### **Core Framework**
- **langgraph** >= 0.2.0 — Graph orchestration
- **langchain-core** >= 0.3.0 — Core abstractions
- **pydantic** >= 2.0.0 — Data validation
- **pydantic-settings** >= 2.0.0 — Configuration management
- **fastapi** >= 0.115.0 — REST API framework
- **uvicorn** >= 0.30.0 — ASGI server
- **python-multipart** >= 0.0.9 — File upload support
- **python-dotenv** >= 1.0.0 — Environment variable management

### **LLM Providers**
- **openai** >= 1.0.0 — OpenAI SDK
- **groq** >= 0.4.0 — Groq SDK
- **google-generativeai** >= 0.3.0 — Google Gemini SDK

### **Document Parsing**
- **pdfplumber** >= 0.10.0 — PDF text extraction
- **python-docx** >= 1.1.0 — DOCX parsing
- **requests** >= 2.31.0 — HTTP client

### **Database (Async)**
- **sqlalchemy[asyncio]** >= 2.0.0 — Async ORM
- **asyncpg** >= 0.29.0 — Async PostgreSQL driver
- **psycopg2-binary** >= 2.9.0 — Sync PostgreSQL driver (for DDL)

### **RAG / Embeddings**
- **chromadb** >= 0.4.0 — Vector store for RAG retrieval
- **sentence-transformers** >= 2.0.0 — Local embeddings

---

## 🎯 Production Considerations

### **Current State (v4.0.0)**
✅ **Clean Architecture** with strict layer separation  
✅ **Async-first** with asyncpg and SQLAlchemy 2.0  
✅ **Dependency Injection** via centralized container  
✅ **Multi-LLM providers** (OpenAI, Groq, Gemini, xAI)  
✅ **PostgreSQL** for structured data with async repositories  
✅ **ChromaDB RAG** for historical trial similarity search  
✅ **Structured logging** with correlation IDs  
✅ **Type-safe** domain entities (frozen dataclasses)  
✅ **File parsers** (PDF, DOCX, JSON) with LLM extraction  
✅ **Historical trial ingestion** (`POST /ingest-trial`)  
✅ **Multi-tier data fetching** (DB → RAG → fallback)  
✅ **Comprehensive error handling** with domain exceptions  
✅ **In-memory cache** with TTL (Redis-swappable)  
⚠️ Risk and compliance are rule-based (not ML-driven)  
⚠️ Human review is CLI/auto-approve (no webhook integration)  

### **Production Enhancements**

**Data Integration:**
- Expand DB-seeded country, site, and investigator coverage
- Replace fallback catalogues with complete operational data
- Implement Milvus backend for large-scale vector workloads
- Connect to ClinicalTrials.gov API for real-time data
- Integrate regulatory databases (FDA, EMA, PMDA)

**Performance:**
- Swap `MemoryCache` for Redis with distributed caching
- Implement request queuing for long-running analyses (Celery/RQ)
- Add database connection pooling optimization
- Implement result caching for repeated protocol analyses

**Security:**
- Add JWT authentication for API endpoints
- Implement API key management and rotation
- Add rate limiting (per-user, per-endpoint)
- Secure file upload validation (virus scanning, size limits)
- Implement RBAC for multi-tenant deployments

**Observability:**
- Distributed tracing (OpenTelemetry) across all layers
- Metrics and monitoring (Prometheus, Grafana)
- Alerting on high-risk trials or compliance failures
- Performance profiling and bottleneck detection

**Deployment:**
- Containerize with Docker (multi-stage builds)
- Deploy on Kubernetes with auto-scaling
- Add CI/CD pipeline (GitHub Actions, GitLab CI)
- Implement blue-green deployments for zero-downtime updates
- Add health checks and readiness probes

---

## 📄 License

This is a demonstration project. Adapt as needed for your use case.

---

## 🤝 Contributing

This system is designed to be extended. Key extension points:

- Service layer implementations
- Custom routing logic in edges
- Additional validation rules
- New scoring algorithms
- Alternative state models

---

## 📞 Support

For questions or issues, review the code documentation in each module. All functions include comprehensive docstrings.

## 🔧 Troubleshooting

### **Database Connection Errors**
If you see `asyncpg.exceptions.InvalidCatalogNameError`:
```sql
-- Create the database first
CREATE DATABASE clinical_trials;
```

If you see connection refused:
- Ensure PostgreSQL is running on `localhost:5432`
- Check credentials in `.env` match your PostgreSQL setup
- Update `CTA_DATABASE_URL` and `CTA_DATABASE_URL_SYNC` accordingly

### **OpenAI Quota Exceeded**
If you see `insufficient_quota` error:
- Add billing credits at https://platform.openai.com/account/billing
- Or use free tier with `gpt-3.5-turbo` (default)

### **xAI No Credits**
If you see `no credits` error:
- Purchase credits at https://console.x.ai
- Or use Groq/Gemini which have generous free tiers

### **Import Errors**
If you see module import errors:
```bash
pip install -r requirements.txt --upgrade
```

### **File Upload Errors**
Ensure file is in correct format:
- JSON: Valid JSON with protocol data
- PDF: Text-based PDF (not scanned images)
- DOCX: Standard Word document

### **ChromaDB Errors**
If you see ChromaDB initialization errors:
- Ensure `./chroma_data` directory is writable
- Or update `CTA_CHROMA_PERSIST_DIRECTORY` in `.env`

---

## 📚 Documentation

All modules include comprehensive docstrings. Key files to understand the architecture:

**Core Layer:**
- `app/core/config.py` — All configurable parameters (weights, thresholds, caps)
- `app/core/container.py` — Dependency injection container (singleton)
- `app/core/logging.py` — Structured logging with correlation IDs
- `app/core/exceptions.py` — Domain exception hierarchy

**Domain Layer:**
- `app/domain/models/` — Immutable entities (TrialEntity, CountryEntity, etc.)
- `app/domain/interfaces/` — Port interfaces (abstract contracts)
- `app/domain/value_objects/` — Score and risk types with invariants

**Application Layer:**
- `app/application/use_cases/` — Top-level orchestrators
- `app/application/services/` — Stateless business logic engines

**Infrastructure Layer:**
- `app/infrastructure/db/session.py` — Async database session management
- `app/infrastructure/db/repositories/` — Async repository implementations
- `app/infrastructure/rag/chroma_adapter.py` — Async ChromaDB wrapper
- `app/infrastructure/llm/adapter.py` — Sync-to-async LLM adapter

**Graph Layer:**
- `app/graph/builder.py` — DI-powered graph construction with inline nodes
- `app/graph/state.py` — Lightweight Pydantic state model

**API Layer:**
- `app/api/routes/trial.py` — Thin route delegating to use case
- `app/main.py` — FastAPI entry point with lifespan and DI

---

## 🙏 Acknowledgments

- **LangGraph** — Graph-based AI orchestration
- **FastAPI** — Modern Python web framework
- **OpenAI, Groq, Google, xAI** — LLM providers

---

---

## 🏆 Architecture Highlights

**Clean Architecture Benefits:**
- **Testability**: Domain logic has zero framework dependencies
- **Maintainability**: Clear boundaries between layers
- **Flexibility**: Swap infrastructure without touching business logic
- **Scalability**: Async-first design handles concurrent requests efficiently

**Key Design Patterns:**
- **Dependency Injection**: Container manages all object lifecycles
- **Repository Pattern**: Abstract data access behind ports
- **Adapter Pattern**: Wraps sync providers to async interfaces
- **Factory Pattern**: Dynamic LLM provider resolution
- **Strategy Pattern**: Multi-tier data fetching (DB → RAG → fallback)

---

**Built with LangGraph, FastAPI & Clean Architecture** — Production-grade AI orchestration for clinical trial feasibility assessment.

**Version 4.0.0** | **Clean Architecture** | **Async PostgreSQL** | **ChromaDB RAG** | **Multi-LLM Support**
