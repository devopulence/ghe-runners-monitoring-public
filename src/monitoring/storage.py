"""
JSON Storage Structure for Daily Stats Collection (Story 1)

Provides file-based JSON storage organized by org and date for GitHub Actions metrics.
Each org gets its own directory, and each day gets a subdirectory with separate files
for workflow runs, jobs, runner status, and computed metrics.

Directory structure:
    monitoring_data/
    ├── devopulence/
    │   ├── 2026-03-11/
    │   │   ├── local_2026-03-11_02-30-00pm/
    │   │   │   ├── workflow_runs.json
    │   │   │   ├── jobs.json
    │   │   │   └── collection_log.json
    │   │   └── workflow_2026-03-11_06-00-00pm/
    │   │       ├── workflow_runs.json
    │   │       ├── jobs.json
    │   │       └── collection_log.json
    │   └── 2026-03-12/
    │       └── ...
    ├── pnc-orange/
    │   └── 2026-03-24/
    │       └── ...
    └── index.json
"""

import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# File names within each daily directory
WORKFLOW_RUNS_FILE = "workflow_runs.json"
JOBS_FILE = "jobs.json"
RUNNER_STATUS_FILE = "runner_status.json"
COMPUTED_METRICS_FILE = "computed_metrics.json"
COLLECTION_LOG_FILE = "collection_log.json"
INDEX_FILE = "index.json"


@dataclass
class StatsRecord:
    """A single data record with timestamp and source metadata."""
    timestamp: str
    source: str  # "github_api", "arc_api", "computed"
    run_source: str = ""  # "local" or "workflow"
    collection_id: str = ""  # unique ID per collection run
    data: dict = field(default_factory=dict)

    @classmethod
    def now(cls, source: str, data: dict, run_source: str = "", collection_id: str = "") -> "StatsRecord":
        return cls(
            timestamp=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            source=source,
            run_source=run_source,
            collection_id=collection_id,
            data=data,
        )


class DailyStatsStore:
    """
    File-based JSON storage organized by org and date.

    Each org gets its own directory, and each day gets a subdirectory.
    Data is appended as new records within each file type.
    Files are created on first write.

    Usage:
        store = DailyStatsStore("/path/to/monitoring_data", org="devopulence", run_source="local")
        store.append_workflow_runs([{...}, {...}])
        store.append_jobs([{...}])
        runs = store.get_workflow_runs()
        runs_for_date = store.get_workflow_runs(date="2026-03-11")
    """

    def __init__(self, base_dir: str = "monitoring_data", org: str = None,
                 run_source: str = "local", collection_id: str = None):
        self.base_dir = Path(base_dir)
        self.org = org
        self.run_source = run_source  # "local" or "workflow"
        if collection_id:
            self.collection_id = collection_id
        else:
            ny_now = datetime.now(ZoneInfo("America/New_York"))
            self.collection_id = f"{run_source}_{ny_now.strftime('%Y-%m-%d_%I-%M-%S%p').lower()}"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    # --- Write operations ---

    def append_workflow_runs(self, runs: list[dict], collection_date: Optional[str] = None) -> int:
        """Append workflow run records for a given date. Returns count of records added."""
        return self._append_records(WORKFLOW_RUNS_FILE, "github_api", runs, collection_date)

    def append_jobs(self, jobs: list[dict], collection_date: Optional[str] = None) -> int:
        """Append job records for a given date. Returns count of records added."""
        return self._append_records(JOBS_FILE, "github_api", jobs, collection_date)

    def append_runner_status(self, snapshots: list[dict], collection_date: Optional[str] = None) -> int:
        """Append runner status snapshots for a given date. Returns count of records added."""
        return self._append_records(RUNNER_STATUS_FILE, "arc_api", snapshots, collection_date)

    def save_computed_metrics(self, metrics: dict, collection_date: Optional[str] = None) -> None:
        """Save computed metrics for a given date. Overwrites previous computation."""
        day_dir = self._day_dir(collection_date)
        filepath = day_dir / COMPUTED_METRICS_FILE
        record = StatsRecord.now(source="computed", data=metrics)
        self._write_json(filepath, asdict(record))
        logger.info("Saved computed metrics to %s", filepath)

    def log_collection(self, entry: dict, collection_date: Optional[str] = None) -> None:
        """Append an entry to the collection log for a given date."""
        day_dir = self._day_dir(collection_date)
        filepath = day_dir / COLLECTION_LOG_FILE
        existing = self._read_json(filepath, default=[])
        entry["timestamp"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        entry["run_source"] = self.run_source
        entry["collection_id"] = self.collection_id
        existing.append(entry)
        self._write_json(filepath, existing)

    # --- Read operations ---

    def get_workflow_runs(self, collection_date: Optional[str] = None) -> list[dict]:
        """Get all workflow run records for a given date."""
        return self._read_records(WORKFLOW_RUNS_FILE, collection_date)

    def get_jobs(self, collection_date: Optional[str] = None) -> list[dict]:
        """Get all job records for a given date."""
        return self._read_records(JOBS_FILE, collection_date)

    def get_runner_status(self, collection_date: Optional[str] = None) -> list[dict]:
        """Get all runner status snapshots for a given date."""
        return self._read_records(RUNNER_STATUS_FILE, collection_date)

    def get_computed_metrics(self, collection_date: Optional[str] = None) -> Optional[dict]:
        """Get computed metrics for a given date (returns latest across runs)."""
        date_dir = self._date_dir(collection_date)
        if not date_dir.exists():
            return None
        latest = None
        for run_dir in sorted(date_dir.iterdir()):
            if run_dir.is_dir():
                filepath = run_dir / COMPUTED_METRICS_FILE
                if filepath.exists():
                    latest = self._read_json(filepath)
        return latest

    def get_collection_log(self, collection_date: Optional[str] = None) -> list[dict]:
        """Get collection log entries for a given date, aggregated across runs."""
        date_dir = self._date_dir(collection_date)
        if not date_dir.exists():
            return []
        all_logs = []
        for run_dir in sorted(date_dir.iterdir()):
            if run_dir.is_dir():
                filepath = run_dir / COLLECTION_LOG_FILE
                logs = self._read_json(filepath, default=[])
                if isinstance(logs, list):
                    all_logs.extend(logs)
        return all_logs

    def list_dates(self) -> list[str]:
        """List all dates that have collected data, sorted ascending."""
        dates = []
        search_dir = self.base_dir / self.org if self.org else self.base_dir
        if not search_dir.exists():
            return dates
        for child in search_dir.iterdir():
            if child.is_dir() and self._is_date_dir(child.name):
                dates.append(child.name)
        return sorted(dates)

    def list_orgs(self) -> list[str]:
        """List all orgs that have collected data."""
        orgs = []
        if not self.base_dir.exists():
            return orgs
        for child in self.base_dir.iterdir():
            if child.is_dir() and not self._is_date_dir(child.name) and child.name != "index.json":
                orgs.append(child.name)
        return sorted(orgs)

    def get_date_summary(self, collection_date: Optional[str] = None) -> dict:
        """Get a summary of data available for a given date, aggregated across runs."""
        day = collection_date or self._today()
        date_dir = self._date_dir(collection_date)
        if not date_dir.exists():
            return {"date": day, "exists": False}

        # List run directories
        run_dirs = [d for d in sorted(date_dir.iterdir()) if d.is_dir()]

        summary = {
            "date": day,
            "exists": True,
            "runs": [d.name for d in run_dirs],
            "files": {},
        }
        for filename in [WORKFLOW_RUNS_FILE, JOBS_FILE, RUNNER_STATUS_FILE,
                         COMPUTED_METRICS_FILE, COLLECTION_LOG_FILE]:
            total_count = 0
            total_size = 0
            for run_dir in run_dirs:
                filepath = run_dir / filename
                if filepath.exists():
                    data = self._read_json(filepath)
                    total_count += len(data) if isinstance(data, list) else 1
                    total_size += filepath.stat().st_size
            if total_count > 0:
                summary["files"][filename] = {
                    "record_count": total_count,
                    "size_bytes": total_size,
                }
        return summary

    def get_index(self) -> dict:
        """Get or build the index of all collection dates with summaries."""
        index = {"last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "dates": {}}
        for d in self.list_dates():
            index["dates"][d] = self.get_date_summary(d)
        index_path = self.base_dir / INDEX_FILE
        self._write_json(index_path, index)
        return index

    # --- Cleanup ---

    def purge_before(self, cutoff_date: str) -> list[str]:
        """Remove daily directories older than cutoff_date. Returns list of removed dates."""
        import shutil
        removed = []
        search_dir = self.base_dir / self.org if self.org else self.base_dir
        for d in self.list_dates():
            if d < cutoff_date:
                shutil.rmtree(search_dir / d)
                removed.append(d)
                logger.info("Purged monitoring data for %s", d)
        return removed

    # --- Internal helpers ---

    def _today(self) -> str:
        return date.today().strftime("%Y-%m-%d")

    def _day_dir(self, collection_date: Optional[str] = None) -> Path:
        day = collection_date or self._today()
        if self.org:
            day_dir = self.base_dir / self.org / day / self.collection_id
        else:
            day_dir = self.base_dir / day / self.collection_id
        day_dir.mkdir(parents=True, exist_ok=True)
        return day_dir

    def _is_date_dir(self, name: str) -> bool:
        try:
            datetime.strptime(name, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def _append_records(self, filename: str, source: str, items: list[dict],
                        collection_date: Optional[str] = None) -> int:
        day_dir = self._day_dir(collection_date)
        filepath = day_dir / filename
        existing = self._read_json(filepath, default=[])
        for item in items:
            record = StatsRecord.now(
                source=source,
                data=item,
                run_source=self.run_source,
                collection_id=self.collection_id,
            )
            existing.append(asdict(record))
        self._write_json(filepath, existing)
        logger.info("Appended %d records to %s", len(items), filepath)
        return len(items)

    def _date_dir(self, collection_date: Optional[str] = None) -> Path:
        """Return the date-level directory (without collection_id), for reading across runs."""
        day = collection_date or self._today()
        if self.org:
            return self.base_dir / self.org / day
        return self.base_dir / day

    def _read_records(self, filename: str, collection_date: Optional[str] = None) -> list[dict]:
        """Read records from all run directories within a date, aggregated."""
        date_dir = self._date_dir(collection_date)
        if not date_dir.exists():
            return []
        all_records = []
        for run_dir in sorted(date_dir.iterdir()):
            if run_dir.is_dir():
                filepath = run_dir / filename
                records = self._read_json(filepath, default=[])
                if isinstance(records, list):
                    all_records.extend(records)
        return all_records

    def _read_json(self, filepath: Path, default: Any = None) -> Any:
        if not filepath.exists():
            return default if default is not None else {}
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to read %s: %s", filepath, e)
            return default if default is not None else {}

    def _write_json(self, filepath: Path, data: Any) -> None:
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except OSError as e:
            logger.error("Failed to write %s: %s", filepath, e)
            raise
