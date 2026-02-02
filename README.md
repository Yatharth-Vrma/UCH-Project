# Tender Scraper POC

A clean, production-minded proof-of-concept for extracting tender data from `https://tender.nprocure.com/`.

**Status:** Completed & Ready for Review  
**Submission Date:** 03-Feb-2026

---

## 📖 Overview

This project implements a **Hybrid Headless Scraper** to robustly handle the client-side encryption (AES/PBKDF2) used by the target site. Instead of brittle reverse-engineering of cryptographic keys, the scraper uses **Playwright** to execute the site's native JavaScript handshake and intercepts the decrypted JSON data streams directly from the network layer.

### Key Features
- **🛡️ Encryption Bypass:** Seamlessly handles dynamic key generation and request signing.
- **🏗️ Structured Extraction:** Intercepts clean JSON API responses instead of parsing HTML tables.
- **⚙️ Configurable:** Full CLI support for rate limits, concurrency, timeouts, and headless mode.
- **🔍 Observability:** Tracks detailed run-level metadata (success rates, deduplication counts, error summaries).
- **📦 Data Quality:** Pydantic models ensure schema validation and data normalization (ISO 8601 dates).
- **♻️ Resilience:** Implements exponential backoff and retry logic via `tenacity`.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Pip

### Installation

1.  **Clone or Extract the Project:**
    ```bash
    cd tender-scraper-poc
    ```

2.  **Set up Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    playwright install chromium
    ```

### Running the Scraper

**Basic Run (Scrape 50 tenders):**
```bash
python main.py
```

**Production-Like Run:**
(200 tenders, visible browser, conservative rate limit)
```bash
python main.py --limit 200 --rate-limit 2.0 --no-headless
```

**CLI Help:**
```bash
python main.py --help
```

---

## ⚙️ Configuration

You can configure the scraper via CLI arguments or Environment Variables.

| Option | Env Variable | Default | Description |
|--------|--------------|---------|-------------|
| `--limit` | - | `50` | Maximum number of tenders to extract. |
| `--rate-limit` | `RATE_LIMIT` | `1.0` | Seconds to wait between page actions. |
| `--concurrency` | `CONCURRENCY` | `1` | (Simulated) Number of parallel contexts. |
| `--timeout-seconds`| `TIMEOUT_SECONDS` | `30` | Timeout for network/selector operations. |
| `--retries` | `RETRIES` | `3` | Max retry attempts for failed requests. |
| `--headless` | - | `True` | Run browser in background (pass `--no-headless` to see it). |
| `--output-path` | `OUTPUT_PATH` | `data/tenders.jsonl` | File path for scraping output. |

---

## 📂 Output & Artifacts

All data is saved to the `data/` directory by default.

1.  **Tender Records:** `data/tenders_{run_id}.jsonl`
    *   Contains the extracted tender data in JSON Lines format.
    *   See `sample-output.jsonl` for a preview.

2.  **Run Metadata:** `data/run_metadata.jsonl`
    *   An audit log of every execution.
    *   Tracks: `run_id`, `config`, `duration`, `tenders_parsed`, `deduped_count`, `error_summary`.

---

## 📚 Documentation

*   **[schema.md](schema.md)**: Detailed breakdown of the `Tender` data model and `RunMetadata` fields.
*   **[architecture.md](architecture.md)**: Technical justification for the Hybrid Headless approach vs. alternatives.
*   **[WORKFLOW_EXPLAINED.md](WORKFLOW_EXPLAINED.md)**: Step-by-step deep dive into the runtime execution flow.

---

## 🏗️ Project Structure

```text
tender-scraper-poc/
├── main.py                 # CLI Entrypoint
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── architecture.md         # Design decisions
├── schema.md               # Data models
├── sample-output.jsonl     # Sample data artifact
├── src/
│   ├── scraper.py          # Core logic (Playwright + Parsing)
│   ├── pipeline.py         # Data persistence & Metadata tracking
│   ├── models.py           # Pydantic data schemas
│   └── utils.py            # Logging setup
└── data/                   # Output directory (ignored in git)
```
