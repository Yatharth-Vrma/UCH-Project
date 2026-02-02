from rich.console import Console
from rich.logging import RichHandler
import logging

console = Console()

def setup_logger(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)]
    )
    return logging.getLogger("tender_scraper")

logger = setup_logger()
