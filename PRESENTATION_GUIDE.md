# Evaluation Presentation Guide

**Role:** Principal Software Architect
**Duration:** 5-10 Minutes

---

## 1. Introduction & Technology Stack (1 Minute)

"Good [morning/afternoon]. I’ve built a production-minded Tender Scraper POC designed for reliability and observability."

**Technology Stack:**
*   **Language:** Python 3.10+ (Selected for rich ecosystem and typing support).
*   **Core Engine:** **Playwright** (Hybrid Headless Browser).
*   **Data Validation:** **Pydantic** (Strict schema enforcement and serialization).
*   **CLI Interface:** **Typer** (User-friendly command-line arguments).
*   **Resilience:** **Tenacity** (Exponential backoff and retry logic).
*   **Storage:** **JSON Lines** (Append-only, crash-safe data persistence).

---

## 2. Architecture & Flow (2 Minutes)

**Key Concept:** "Hybrid Headless Interception"

"I chose a **Hybrid approach** rather than pure API reverse-engineering or pure DOM parsing. Here's why:"

1.  **The Challenge:** The site uses client-side AES encryption (`AesUtil.js`) to sign every API request. Reverse-engineering this is brittle; if they rotate keys, the scraper breaks.
2.  **The Solution:** We launch a headless browser to act as a 'Trojan Horse'.
    *   It executes the site's native JavaScript to generate valid security keys.
    *   We attach a **Network Listener** (`page.on('response')`) to the browser.
    *   Instead of parsing HTML tables (which break easily), we intercept the **decrypted JSON data** directly from the server response.

**The Workflow:**
1.  **Init:** Scraper launches, spoofing a real user agent.
2.  **Handshake:** Browser navigates to the site, generating encryption keys automatically.
3.  **Interception:** We silently capture the JSON traffic (`/beforeLoginTenderTableList`).
4.  **Pipeline:** Data is validated, cleaned, deduped, and saved.

---

## 3. Code Walkthrough (3 Minutes)

*Navigate to these files in your IDE during the demo.*

**A. `src/scraper.py` (The Engine)**
*   Show `handle_response`: "This is where we intercept the JSON packet."
*   Show `parse_item`: "We extract structured fields. Note the Regex used to pull the 'Organization' and 'Dates' out of the HTML blobs."

**B. `src/models.py` (The Contract)**
*   Show `Tender` class: "I use Pydantic to enforce data quality. We define Enums for 'TenderType' and normalize dates to ISO format here."

**C. `src/pipeline.py` (Persistence)**
*   Show `save_metadata`: "This ensures every run is auditable. We track versioning, config, and error counts."

---

## 4. Metadata Design (1 Minute)

"I designed the metadata schema to answer 'Who, What, When, and How' for debugging."

*   **`run_id`**: Essential for tracing logs to specific executions.
*   **`scraper_version`**: Captures the Git SHA. If data quality drops, we know exactly which code change caused it.
*   **`config`**: Stores the rate limit and timeouts used, so we can reproduce bugs.
*   **`deduped_count`**: Tells us if we are wasting resources scraping known data (signals a need for incremental scraping).
*   **`error_summary`**: Aggregates failure types (e.g., "5 Parsing Errors") so we know what to fix first.

---

## 5. Live Demonstration (1-2 Minutes)

**Command to run:**
```bash
python main.py --limit 20 --no-headless
```

**What to highlight:**
1.  The browser opens (proving it handles the JS encryption).
2.  The logs in the terminal show "Navigating...", "Intercepted...", "Saved...".
3.  Open `data/tenders_{run_id}.jsonl` to show the clean output.
4.  Open `data/run_metadata.jsonl` to show the audit trail.

---

## 6. Future Improvements (1 Minute)

"To take this from POC to Production, I would add:"

1.  **Incremental Scraping:** Query the DB for existing IDs before scraping to only fetch *new* tenders.
2.  **Distributed Infrastructure:** Run the containerized scraper on AWS Lambda or Kubernetes with a rotated proxy pool.
3.  **Alerting:** Hook the `failures` count into Slack/PagerDuty.
4.  **Document Downloading:** Add a pipeline step to actually download and OCR the attached PDF documents.

---

## 7. Method & References

**Methodology:**
*   **Analysis:** Inspected Network tab in Chrome DevTools to identify the hidden API (`beforeLoginTenderTableList`) and the encryption payload (`salt`, `iv`).
*   **Prototyping:** Validated that Python's `requests` library failed (403 Forbidden) due to missing signatures.
*   **Implementation:** Adopted Playwright for its robust network interception capabilities (`response.json()`).

**References:**
*   Playwright Documentation (Network Events)
*   Pydantic V2 Documentation (Schema Validation)
*   Tenacity Documentation (Retry Patterns)
