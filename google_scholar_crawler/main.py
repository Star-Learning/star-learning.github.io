import json
from datetime import datetime, timezone
import os
from pathlib import Path
import sys

from scholarly import scholarly


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = Path(os.environ.get("GS_RESULTS_DIR", ROOT / "assets" / "data"))
DATA_FILE = RESULTS_DIR / "gs_data.json"
SHIELDS_FILE = RESULTS_DIR / "gs_data_shieldsio.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_cached_author() -> dict:
    if DATA_FILE.exists():
        with DATA_FILE.open(encoding="utf-8") as infile:
            return json.load(infile)
    return {
        "name": "Xing Xu",
        "citedby": None,
        "updated": None,
        "publications": {},
    }


def normalize_author(author: dict) -> dict:
    author["updated"] = utc_now()
    publications = author.get("publications", [])
    if isinstance(publications, list):
        author["publications"] = {
            publication["author_pub_id"]: publication
            for publication in publications
            if publication.get("author_pub_id")
        }
    return author


def write_outputs(author: dict) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as outfile:
        json.dump(author, outfile, ensure_ascii=False, indent=2)
        outfile.write("\n")

    citedby = author.get("citedby")
    shieldio_data = {
        "schemaVersion": 1,
        "label": "citations",
        "message": str(citedby) if citedby is not None else "unavailable",
    }
    with SHIELDS_FILE.open("w", encoding="utf-8") as outfile:
        json.dump(shieldio_data, outfile, ensure_ascii=False, indent=2)
        outfile.write("\n")


def fetch_author() -> dict:
    google_scholar_id = os.environ.get("GOOGLE_SCHOLAR_ID")
    if not google_scholar_id:
        raise RuntimeError("GOOGLE_SCHOLAR_ID is not set")

    author: dict = scholarly.search_author_id(google_scholar_id)
    author = scholarly.fill(author, sections=["basics", "indices", "counts", "publications"]) or author
    return normalize_author(author)


try:
    author_data = fetch_author()
except Exception as exc:
    cached_author = load_cached_author()
    write_outputs(cached_author)
    print(f"Could not refresh Google Scholar data; kept cached data. {type(exc).__name__}: {exc}", file=sys.stderr)
else:
    write_outputs(author_data)
    print(json.dumps(author_data, indent=2, ensure_ascii=False))
