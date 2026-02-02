# Data Schema Documentation

## Tenders Collection/Table

| Field | Type | Description | Reasoning |
|-------|------|-------------|-----------|
| `tender_id` | String | Official tender ID from source | Business key for deduplication and official reference. |
| `tender_type` | Enum(Goods, Works, Services) | Category of tender | Required for filtering and domain-specific processing. |
| `title` | String | Tender title/brief | Primary searchable field for users. |
| `organization` | String | Issuing organization name | Required for vendor matching and analysis. |
| `publish_date` | Date (YYYY-MM-DD) | Publication date | Critical for timeline tracking. |
| `closing_date` | Date (YYYY-MM-DD) or NULL | Submission deadline | May be null for open-ended tenders; critical for alerts. |
| `description` | Text | Full tender description | Captured for deeper analysis (NLP), stripped of HTML. |
| `source_url` | String | Direct link to tender | Enables validation, updates, and deep linking. |
| `attachments` | JSON Array | List of document URLs | Structured format for accessing multiple files (PDFs, etc.). |
| `raw_html_snippet` | Text (optional) | Original HTML blob | Debugging and re-parsing fallback if regex fails. |
| `ingested_at` | Timestamp | When record was scraped | Audit trail and versioning of the data. |

## Run Metadata Collection

| Field | Type | Description | Reasoning |
|-------|------|-------------|-----------|
| `run_id` | String (UUID) | Unique identifier per run | Correlates logs, outputs, and debugging artifacts. |
| `start_time` | ISO Timestamp | Run start | Performance tracking and scheduling validation. |
| `end_time` | ISO Timestamp | Run end | Performance tracking. |
| `duration_seconds` | Float | Total runtime | SLA monitoring and cost estimation. |
| `scraper_version` | String (git SHA) | Code version used | Reproducibility and rollback capability. |
| `config` | JSON Object | All config used (rate_limit, concurrency, limit) | Exact reproduction of run conditions. |
| `tender_types_processed` | Array[String] | Which types were scraped | Domain coverage tracking. |
| `pages_visited` | Integer | Total pagination count | Progress indicator. |
| `tenders_parsed` | Integer | Total items extracted | Success metric (top of funnel). |
| `tenders_saved` | Integer | Valid records persisted | Data quality metric (bottom of funnel). |
| `failures` | Integer | Failed extractions | Error rate calculation. |
| `deduped_count` | Integer | Duplicates skipped | Data hygiene metric; signals need for incremental logic. |
| `error_summary` | JSON Object | Error types and counts | Prioritizes fixes (e.g., "45 date parsing errors"). |

### Why Each Metadata Key Matters

- **`run_id`**: Without this, you can't trace which log lines belong to which execution.
- **`scraper_version`**: If output quality degrades, you need to know which code version caused it.
- **`config`**: Debugging "why did this run behave differently?" requires knowing exact settings (e.g., was rate limit too high?).
- **`tender_types_processed`**: Proves coverage; if "Services" is always missing, the config or parsing logic is wrong.
- **`deduped_count`**: High values indicate re-scraping same data; signals efficiency improvements needed (incremental mode).
- **`error_summary`**: "50 failures" is useless; "45 date parsing errors, 5 network timeouts" is actionable.