import os
from pathlib import Path
import logging

log = logging.getLogger(__name__)

def clean_demo_pdfs() -> None:
    """Delete all files in the demo PDF directory.

    The directory is defined by the SETTINGS.DEMO_DIR path (./data/demo_pdfs).
    This function is safe to run multiple times – if the directory does not exist
    it simply returns.
    """
    demo_dir = Path("./data/demo_pdfs")
    if not demo_dir.exists():
        log.info("Demo PDF directory does not exist – nothing to clean.")
        return

    for item in demo_dir.iterdir():
        if item.is_file():
            try:
                item.unlink()
                log.info("Deleted demo PDF: %s", item.name)
            except Exception as exc:
                log.warning("Failed to delete %s: %s", item, exc)

    demo_dir.mkdir(parents=True, exist_ok=True)
    log.info("Demo PDF directory is now clean.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    clean_demo_pdfs()
