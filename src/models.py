from typing import List, Optional, Literal, Dict, Any
from datetime import datetime, date
from enum import Enum
from pydantic import BaseModel, Field

class TenderType(str, Enum):
    GOODS = "Goods"
    WORKS = "Works"
    SERVICES = "Services"
    UNKNOWN = "Unknown"

class Tender(BaseModel):
    tender_id: str = Field(..., description="Official tender ID from source")
    tender_type: TenderType = Field(..., description="Category of tender")
    title: str = Field(..., min_length=1, description="Tender title/brief")
    organization: str = Field(..., description="Issuing organization name")
    publish_date: Optional[str] = Field(None, description="YYYY-MM-DD format")
    closing_date: Optional[str] = Field(None, description="YYYY-MM-DD format or null")
    description: str = Field(default="", description="Full tender description")
    source_url: str = Field(..., description="Direct link to tender")
    attachments: List[str] = Field(default_factory=list, description="List of document URLs")
    raw_html_snippet: Optional[str] = Field(None, description="Original HTML blob for debugging")
    ingested_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        use_enum_values = True

class ScraperConfig(BaseModel):
    rate_limit: float
    concurrency: int
    limit: int
    headless: bool = True
    timeout_seconds: int = 30
    retries: int = 3
    user_agent: Optional[str] = None
    output_path: str = "data/tenders.jsonl"
    dry_run: bool = False

class RunMetadata(BaseModel):
    run_id: str
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    scraper_version: str
    config: ScraperConfig
    tender_types_processed: List[str] = Field(default_factory=list)
    pages_visited: int = 0
    tenders_parsed: int = 0
    tenders_saved: int = 0
    failures: int = 0
    deduped_count: int = 0
    error_summary: Dict[str, int] = Field(default_factory=dict)