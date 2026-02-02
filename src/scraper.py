import asyncio
import json
import uuid
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from playwright.async_api import async_playwright, Page, Response, Request
from .models import Tender, RunMetadata, ScraperConfig, TenderType
from .pipeline import DataPipeline
from .utils import logger
import re
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class TenderScraper:
    def __init__(self, config: ScraperConfig, pipeline: DataPipeline):
        self.config = config
        self.pipeline = pipeline
        self.run_metadata = RunMetadata(
            run_id=pipeline.run_id,
            start_time=datetime.utcnow().isoformat(),
            scraper_version="1.0.0", # Will be updated by pipeline on save
            config=config
        )
        self.extracted_count = 0
        self.start_time = time.time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def goto_page(self, page: Page, url: str):
        await page.goto(url, timeout=self.config.timeout_seconds * 1000)

    async def run(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.config.headless,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            
            context = await browser.new_context(
                user_agent=self.config.user_agent or "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            page.on("response", self.handle_response)
            
            try:
                logger.info("Navigating to https://tender.nprocure.com/")
                await self.goto_page(page, "https://tender.nprocure.com/")
                self.run_metadata.pages_visited += 1

                logger.info("Waiting for tender table...")
                await page.wait_for_selector("table.dataTable", timeout=self.config.timeout_seconds * 1000)
                
                try:
                    logger.info("Attempting to increase page size...")
                    await page.select_option("select[name*='length']", "100") 
                    await page.wait_for_timeout(2000)
                except Exception as e:
                    logger.warning(f"Could not change page size: {e}")

                while self.extracted_count < self.config.limit:
                    logger.info(f"Extracted {self.extracted_count} / {self.config.limit} tenders. Processing page...")
                    
                    await asyncio.sleep(self.config.rate_limit)
                    
                    next_button = page.locator(".paginate_button.next")
                    
                    if self.extracted_count >= self.config.limit:
                        break

                    if await next_button.count() > 0 and not await next_button.get_attribute("class").then(lambda cls: "disabled" in cls):
                        logger.info("Clicking Next page...")
                        await next_button.click()
                        self.run_metadata.pages_visited += 1
                        await page.wait_for_timeout(3000) 
                    else:
                        logger.info("No more pages or limit reached.")
                        break
                        
            except Exception as e:
                logger.error(f"Scraping error: {e}")
                self.pipeline.record_error("FatalScraperError", str(e))
            finally:
                await browser.close()
                self.finish_run()

    async def handle_response(self, response: Response):
        if "beforeLoginTenderTableList" in response.url and response.status == 200:
            try:
                json_data = await response.json()
                if "data" in json_data:
                    tenders_list = json_data["data"]
                    self.run_metadata.tenders_parsed += len(tenders_list)
                    
                    for item in tenders_list:
                        if self.extracted_count >= self.config.limit:
                            break
                        
                        tender = self.parse_item(item)
                        if tender:
                            saved = self.pipeline.save_tender(tender)
                            if saved:
                                self.extracted_count += 1
            except Exception as e:
                logger.error(f"Failed to parse response JSON: {e}")
                self.pipeline.record_error("ResponseParseError", str(e))

    def parse_item(self, item: Dict[str, Any]) -> Optional[Tender]:
        try:
            tender_id = str(item.get("1", "unknown")).strip()
            raw_html_brief = str(item.get("2", ""))
            text_brief = self.clean_text(raw_html_brief)
            
            org = self._extract_organization(text_brief)
            title = self._extract_title(text_brief)
            
            closing_match = re.search(r'Last Date.*?(\d{2}-\d{2}-\d{4})', text_brief, re.IGNORECASE)
            closing_date = self.normalize_date(closing_match.group(1)) if closing_match else None
            
            raw_link_html = str(item.get("3", ""))
            source_url = self.extract_url(raw_link_html)
            attachments = self._extract_attachments(raw_link_html)
            
            tender_type = self._infer_tender_type(title, text_brief)
            
            return Tender(
                tender_id=tender_id,
                tender_type=tender_type,
                title=title,
                organization=org,
                publish_date=None, 
                closing_date=closing_date,
                description=text_brief, 
                source_url=source_url or "https://tender.nprocure.com/",
                attachments=attachments,
                raw_html_snippet=str(item)[:500]
            )
            
        except Exception as e:
            logger.warning(f"Error parsing item: {e}")
            self.pipeline.record_error("ParseError", str(e), item.get("1", "unknown"))
            return None

    def clean_text(self, text: str) -> str:
        if not text: return ""
        clean = re.sub(r'<[^>]+>', ' ', text)
        return " ".join(clean.split())

    def _extract_organization(self, text: str) -> str:
        # Example: "DICDL-Dholera ... Tender Id"
        match = re.search(r'^(.*?)Tender Id\s*:', text)
        return match.group(1).strip() if match else "Unknown Organization"

    def _extract_title(self, text: str) -> str:
        match = re.search(r'Name Of Work\s*:\s*(.*?)(?:Corrigendum|Estimated Contract Value|Last Date)', text, re.IGNORECASE)
        return match.group(1).strip() if match else text

    def _infer_tender_type(self, title: str, description: str) -> TenderType:
        text = (title + " " + description).lower()
        if any(kw in text for kw in ['supply', 'purchase', 'procurement', 'goods']):
            return TenderType.GOODS
        elif any(kw in text for kw in ['construction', 'civil work', 'building', 'works', 'road']):
            return TenderType.WORKS
        elif any(kw in text for kw in ['consultancy', 'service', 'maintenance', 'advisory', 'hiring']):
            return TenderType.SERVICES
        return TenderType.SERVICES # Default per POC observation

    def _extract_attachments(self, html: str) -> List[str]:
        # Basic extraction of hrefs that look like docs
        # Note: In the list view, docs are usually main links, but we return list as requested
        urls = []
        matches = re.findall(r'href=["\'](.*?)["\']', html)
        for url in matches:
            if url and url != "#":
                if url.startswith("/"):
                    urls.append(f"https://tender.nprocure.com{url}")
                else:
                    urls.append(url)
        return urls

    def extract_url(self, html: str) -> Optional[str]:
        match = re.search(r'href=["\'](.*?)["\']', html)
        if match:
            url = match.group(1)
            if url and url != "#":
                if url.startswith("/"):
                    return f"https://tender.nprocure.com{url}"
                return url
        
        id_match = re.search(r"name=['\"]tenderid['\"].*?value=['\"](\d+)['\"]", html)
        if id_match:
            return f"https://tender.nprocure.com/view-nit-home?tenderid={id_match.group(1)}"
            
        return None

    def normalize_date(self, date_str: str) -> Optional[str]:
        if not date_str: return None
        for fmt in ("%d-%b-%Y", "%d-%m-%Y"):
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    def finish_run(self):
        self.run_metadata.end_time = datetime.utcnow().isoformat()
        self.run_metadata.duration_seconds = time.time() - self.start_time
        self.pipeline.save_metadata(self.run_metadata)
