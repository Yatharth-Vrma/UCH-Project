import json
import os
import subprocess
from datetime import datetime
from typing import List, Set, Dict, Any
from .models import Tender, RunMetadata
from .utils import logger

class DataPipeline:
    def __init__(self, output_dir: str, run_id: str):
        self.output_dir = output_dir
        self.run_id = run_id
        # Use config output_path if provided, else default
        self.tenders_file = os.path.join(output_dir, f"tenders_{run_id}.jsonl")
        self.metadata_file = os.path.join(output_dir, "run_metadata.jsonl")
        self.seen_ids: Set[str] = set()
        self.stats = {
            "saved": 0,
            "deduped": 0,
            "failures": 0
        }
        self.error_log: List[Dict[str, Any]] = []
        self.processed_types: Set[str] = set()
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def save_tender(self, tender: Tender):
        self.processed_types.add(tender.tender_type)
        
        if tender.tender_id in self.seen_ids:
            self.stats["deduped"] += 1
            logger.debug(f"Duplicate tender skipped: {tender.tender_id}")
            return False
        
        self.seen_ids.add(tender.tender_id)
        
        try:
            with open(self.tenders_file, "a", encoding="utf-8") as f:
                f.write(tender.model_dump_json() + "\n")
            self.stats["saved"] += 1
            return True
        except Exception as e:
            self.record_error("SaveError", str(e), tender.tender_id)
            return False

    def record_error(self, error_type: str, message: str, context: str = ""):
        self.stats["failures"] += 1
        self.error_log.append({
            "type": error_type,
            "message": message,
            "context": context,
            "timestamp": datetime.utcnow().isoformat()
        })
        logger.error(f"{error_type}: {message} ({context})")

    def _generate_error_summary(self) -> Dict[str, int]:
        summary = {}
        for error in self.error_log:
            etype = error.get("type", "Unknown")
            summary[etype] = summary.get(etype, 0) + 1
        return summary

    def _get_git_version(self) -> str:
        try:
            return subprocess.check_output(['git', 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL).decode('ascii').strip()
        except:
            return "unknown-no-git"

    def save_metadata(self, metadata: RunMetadata):
        # Update metadata with pipeline stats
        metadata.tenders_saved = self.stats["saved"]
        metadata.deduped_count = self.stats["deduped"]
        metadata.failures = self.stats["failures"]
        metadata.error_summary = self._generate_error_summary()
        metadata.tender_types_processed = list(self.processed_types)
        metadata.scraper_version = self._get_git_version()
        
        # Write run-level metadata
        with open(self.metadata_file, "a", encoding="utf-8") as f:
            f.write(metadata.model_dump_json() + "\n")
            
        logger.info(f"Metadata saved for run {self.run_id}")

    def load_existing_ids(self):
        # Basic check for existing file
        if os.path.exists(self.tenders_file):
            with open(self.tenders_file, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        self.seen_ids.add(data.get("tender_id"))
                    except:
                        pass