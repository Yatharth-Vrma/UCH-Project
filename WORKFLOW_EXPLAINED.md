# Deep Dive: How the Scraper Works (Workflow Explained)

This document explains the exact technical workflow of the Tender Scraper POC, step-by-step, from the moment you press Enter to when the data is saved to disk.

It answers the question: *"How exactly are we getting data from a secure, encrypted website without getting blocked?"*

---

## The High-Level Strategy: "Hybrid Headless"

The core challenge of `tender.nprocure.com` is that it uses **client-side encryption**.
1.  When a user browses the site, their browser runs JavaScript (`AesUtil.js`).
2.  This JS generates a cryptographic key using a "salt" and "IV" (Initialization Vector) hidden in the HTML.
3.  Every request for data (like clicking "Next Page") is signed with this key.

**If we tried to just use `curl` or standard Python `requests`, the server would reject us immediately because we wouldn't have the correct signature.**

Instead of spending weeks reverse-engineering the encryption, we cheat. We use a **Headless Browser (Playwright)** to act as a legitimate user, let the site run its own encryption code, and then we "eavesdrop" on the results.

---

## Step-by-Step Runtime Workflow

### Phase 1: Initialization & Configuration
**Trigger:** You run `python main.py --limit 100`

1.  **CLI Parsing (`main.py`)**:
    *   The `typer` library parses your command line arguments (`limit`, `rate_limit`, `headless`).
    *   A `ScraperConfig` object is created.
    *   A unique `run_id` (e.g., `b9cc4f02`) is generated to track this specific execution.

2.  **Pipeline Setup (`pipeline.py`)**:
    *   The `DataPipeline` initializes.
    *   It checks the `data/` directory.
    *   It loads a "memory" of previously seen Tender IDs (to prevent duplicates).

### Phase 2: The "Trojan Horse" Launch
**Component:** `TenderScraper.run()` in `src/scraper.py`

1.  **Browser Start**: Playwright launches a Chromium instance.
    *   *Headless Mode:* It runs visibly if you used `--no-headless`, otherwise it runs in the background.
    *   *User Agent:* It spoofs a real Linux/Windows user agent so the server thinks it's a standard PC.

2.  **Network Spy Setup (CRITICAL STEP)**:
    *   Before navigating anywhere, we attach a **Network Listener**:
        ```python
        page.on("response", self.handle_response)
        ```
    *   This tells Playwright: *"I don't care about what you show on the screen. I want you to silently pass me a copy of every single data packet the server sends back."*

### Phase 3: Navigation & The "Handshake"
**Action:** `await page.goto("https://tender.nprocure.com/")`

1.  **Loading the Page**: The browser loads the HTML.
2.  **Key Generation**: The site's `onload` JavaScript fires. It finds the hidden `<input id="salt">` and `<input id="iv">` elements in the DOM and generates the session keys.
    *   *Note:* We don't have to do anything here. The browser handles the security handshake automatically.
3.  **Table Load**: The site performs an AJAX request (XHR) to fetch the first 50 tenders.

### Phase 4: Data Interception (The Magic)
**Component:** `handle_response()`

1.  **The Trigger**: When the site fetches the tender list (endpoint: `/beforeLoginTenderTableList`), our listener wakes up.
2.  **Capture**: We intercept the response *after* the browser has decrypted it (or received it as standard JSON).
3.  **Validation**: We check if the JSON contains the `data` key.
4.  **Extraction**: We pull the raw list of tenders directly from this JSON packet.
    *   *Why is this better than parsing HTML?* parsing HTML is messy. The JSON gives us structured data instantly.

### Phase 5: Parsing & Cleaning
**Component:** `parse_item()`

For every raw item captured from the JSON:
1.  **Regex Extraction**: We use Regular Expressions to extract:
    *   **Title**: Extracted from the HTML blob in the "Tender Brief" column.
    *   **Dates**: We look for patterns like `dd-MMM-yyyy` (e.g., `20-Feb-2026`).
    *   **Links**: We construct the full URL. If it's a hidden form link, we construct a deep link like `view-nit-home?tenderid=123`.
2.  **Normalization**: Dates are converted to ISO format (`YYYY-MM-DD`). Text is stripped of whitespace and HTML tags.
3.  **Validation**: The data is passed into a **Pydantic Model** (`Tender`). If any required field is missing or invalid, it's flagged.

### Phase 6: Persistence & Pagination
**Component:** `pipeline.py`

1.  **Deduplication**: We check if `tender_id` has been seen before in this run. If yes, we skip it.
2.  **Write to Disk**: Valid, unique tenders are appended to `data/tenders_{run_id}.jsonl`.
    *   *Format:* JSON Lines (one JSON object per line). This is crash-safe; if the scraper stops halfway, you still have the data collected so far.
3.  **Next Page**:
    *   The scraper checks if we have reached the `--limit`.
    *   If not, it finds the "Next" button in the browser DOM and clicks it.
    *   **Loop:** This triggers a new network request -> Phase 4 (Interception) happens again.

### Phase 7: Shutdown & Metadata
**Component:** `finish_run()`

1.  **Cleanup**: The browser is closed to free up memory.
2.  **Metadata Save**: A summary is written to `data/run_metadata.jsonl`.
    *   It records: How long it took, how many pages were visited, success/failure counts, and the config used.

---

## Summary Diagram

```
[Start CLI]
    │
    ▼
[Launch Headless Browser] ───(User Agent Spoofing)──▶ [Website]
    │                                                     │
    │ (Listens silently)                                  │ (Executes JS Encryption)
    ▼                                                     ▼
[Network Interceptor] ◀──(Intercept JSON Response)── [AJAX Data Stream]
    │
    ▼
[Parser Engine] ──(Regex & Cleaning)──▶ [Pydantic Model]
    │
    ▼
[Deduplication] ──(Check IDs)──▶ [Save to JSONL File]
```
