# Architecture Decision: Hybrid Headless Browser Approach

## Problem Statement
The target site (`https://tender.nprocure.com/`) uses client-side AES encryption via JavaScript:
- All AJAX requests are signed with cryptographic keys.
- Keys are generated dynamically from hidden DOM elements (`salt`, `iv`).
- Direct HTTP requests (e.g., via `curl` or `requests`) fail authentication.

## Approach Comparison

### Option A: Pure API/XHR Reverse Engineering
**Pros:**
- Fastest execution (no browser overhead).
- Minimal resource usage (CPU/RAM).

**Cons:**
- Requires fully reverse-engineering `AesUtil.js` encryption and key exchange logic.
- Keys or logic may rotate, breaking the scraper instantly.
- Estimated 2-3 weeks of cryptanalysis work.

**Verdict:** ❌ **Too brittle, high maintenance.**

### Option B: Pure Headless Browser (Selenium/Playwright)
**Pros:**
- Handles all JS execution natively.
- No encryption reverse-engineering required.

**Cons:**
- Slow (waits for full page renders, advertisements, trackers).
- High resource usage.
- Parsing HTML DOM is fragile and breaks with layout changes.

**Verdict:** ⚠️ **Works but inefficient.**

### Option C: Hybrid Interception (CHOSEN)
**Implementation:**
1.  **Launch** headless browser via Playwright.
2.  **Navigate** to the site, allowing native JS to handle the handshake and encryption.
3.  **Intercept** the decrypted JSON responses via the browser's network listener.
4.  **Extract** structured data directly from the JSON (bypassing HTML parsing).

**Pros:**
- ✅ **No encryption reverse-engineering needed.**
- ✅ **Gets clean JSON** instead of messy HTML.
- ✅ **Resilient** to DOM layout changes (API contracts change less often).
- ✅ **Reasonable performance** (only initial page load is heavy).

**Cons:**
- Heavier than pure API approach (requires Chromium binary).
- Browser dependency.

**Verdict:** ✅ **Best tradeoff for POC and production.**

## Production Considerations
- **Scalability:** Run multiple browser instances in parallel (supported via `--concurrency`).
- **Monitoring:** Network interception provides clean request/response logging.
- **Maintenance:** If the site changes encryption, browser auto-updates handle it.
- **Cost:** Headless browsers consume ~200MB RAM each; plan for 5-10 concurrent instances per node.

## Why This Beats Alternatives
If the site's encryption changes, our scraper keeps working because we're using the site's own code to generate signatures. A pure API approach would break and require significant re-engineering.