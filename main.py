import typer
import asyncio
import os
import uuid
from src.scraper import TenderScraper
from src.pipeline import DataPipeline
from src.models import ScraperConfig
from src.utils import logger

app = typer.Typer()

@app.callback()
def main():
    """
    Tender Scraper CLI
    """

@app.command()
def scrape(
    limit: int = typer.Option(50, help="Max number of tenders to scrape"),
    concurrency: int = typer.Option(1, help="Number of concurrent pages (simulated)"),
    rate_limit: float = typer.Option(1.0, help="Delay between requests in seconds"),
    output_path: str = typer.Option("data/tenders.jsonl", help="Path to output file"),
    headless: bool = typer.Option(True, help="Run in headless mode"),
    timeout_seconds: int = typer.Option(30, help="Request timeout in seconds"),
    retries: int = typer.Option(3, help="Max retry attempts"),
    dry_run: bool = typer.Option(False, help="Validate without saving (not fully implemented)"),
):
    """
    Run the Tender Scraper POC.
    Environment variables are supported: RATE_LIMIT, CONCURRENCY, TIMEOUT_SECONDS, RETRIES, OUTPUT_PATH.
    """
    # Load from Env Vars if CLI not explicitly overriding (Typer defaults handle this if we set defaults to None, 
    # but here we prioritize CLI args, then Env, then Defaults. 
    # Since Typer has defaults, we can just check if Env exists and user didn't change default? 
    # Simpler approach: Use os.getenv as default in Typer? No, that's messy.
    # We will override with Env if CLI is default value. 
    
    # Actually, simpler is to just read env vars if not provided? 
    # Typer handles this best by `envvar` argument in Option but I'll do manual fallback for clarity.
    
    final_limit = limit
    final_rate = float(os.getenv("RATE_LIMIT", rate_limit))
    final_conc = int(os.getenv("CONCURRENCY", concurrency))
    final_timeout = int(os.getenv("TIMEOUT_SECONDS", timeout_seconds))
    final_retries = int(os.getenv("RETRIES", retries))
    final_output = os.getenv("OUTPUT_PATH", output_path)

    run_id = str(uuid.uuid4())[:8]
    logger.info(f"Starting Scraper Run ID: {run_id}")
    logger.info(f"Config: Limit={final_limit}, RateLimit={final_rate}, Timeout={final_timeout}")

    # Extract directory from output_path
    output_dir = os.path.dirname(final_output) or "data"

    config = ScraperConfig(
        rate_limit=final_rate,
        concurrency=final_conc,
        limit=final_limit,
        headless=headless,
        timeout_seconds=final_timeout,
        retries=final_retries,
        output_path=final_output,
        dry_run=dry_run
    )

    pipeline = DataPipeline(output_dir=output_dir, run_id=run_id)
    scraper = TenderScraper(config=config, pipeline=pipeline)

    try:
        asyncio.run(scraper.run())
        logger.info("Scraping completed successfully.")
    except KeyboardInterrupt:
        logger.warning("Scraping interrupted by user.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    app()