# System Architecture

This document describes the architectural design and component interactions of the Tender Scraper POC.

## Architectural Overview

The system follows a modular architecture with a clear separation of concerns between web automation, data extraction, and persistence. It utilizes a **Hybrid Headless Scraper** approach to overcome client-side security measures.

### Core Components

1.  **CLI Entrypoint (`main.py`)**:
    - Handles command-line arguments and environment variable parsing.
    - Orchestrates the initialization of the configuration, data pipeline, and scraper.
    - Manages the asynchronous execution loop.

2.  **Scraper Engine (`src/scraper.py`)**:
    - **Playwright Integration**: Orchestrates a headless Chromium instance to navigate the target site and execute native JavaScript.
    - **Network Interception**: Attaches listeners to the browser context to capture XHR/Fetch responses directly from the network layer.
    - **Resilience**: Implements exponential backoff and retry logic for robust navigation and page interactions.

3.  **Data Models (`src/models.py`)**:
    - Defines structured schemas using **Pydantic** for both Tender records and Run Metadata.
    - Ensures type safety, data validation, and consistent normalization across the application.

4.  **Data Pipeline (`src/pipeline.py`)**:
    - **Persistence**: Manages writing records to disk in JSON Lines (`.jsonl`) format for crash-resiliency.
    - **Deduplication**: Maintains an in-memory set of processed IDs to prevent duplicate entries within a run.
    - **Metadata Tracking**: Aggregates statistics (successes, failures, durations) and saves a final audit document for every run.

5.  **Utilities (`src/utils.py`)**:
    - Provides centralized logging configuration and shared helper functions.

## Technical Design Decisions

### 1. Hybrid Interception vs. HTML Parsing
Instead of parsing complex and potentially volatile HTML tables, the scraper intercepts the raw JSON responses sent by the server to the browser. 
- **Benefit**: More stable, higher data fidelity, and bypasses client-side decryption complexity by capturing data after the browser has processed it.

### 2. JSON Lines (NDJSON) Storage
Data is stored in `.jsonl` format.
- **Benefit**: Allows for incremental writes. If the process is interrupted, all records processed up to that point are preserved. It also allows for efficient reading of large datasets without loading the entire file into memory.

### 3. Separation of Concerns
The `TenderScraper` is responsible only for navigation and raw data capture. It delegates the persistence and state management to the `DataPipeline`.
- **Benefit**: Easier to test and allows for swapping out the persistence layer (e.g., to a database) without modifying the scraper logic.

### 4. Resilience and Observability
- **Tenacity**: Used for retrying network-sensitive operations.
- **Rich Logging**: Provides human-readable, colored logs with clear indicators of progress and errors.
- **Run Metadata**: Every execution produces a machine-readable summary, enabling long-term monitoring of scraper health and data coverage.

## Data Flow Diagram

```text
[User Command]
      │
      ▼
[main.py: CLI] ───▶ [ScraperConfig]
      │
      ▼
[src/scraper.py: TenderScraper] ◀───▶ [Chromium Browser]
      │                                   │
      │ (Interception)                    │ (Decryption/Rendering)
      ▼                                   ▼
[Raw Data Capture] ◀────────────────── [Network Layer]
      │
      ▼
[src/models.py: Pydantic Validation]
      │
      ▼
[src/pipeline.py: DataPipeline] ───▶ [data/tenders_*.jsonl]
      │                         └───▶ [data/run_metadata.jsonl]
```
