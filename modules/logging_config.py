import os
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _resolve_log_file_path() -> Path:
    raw_path = os.getenv("APP_LOG_PATH")
    
    if raw_path:
        log_dir = Path(raw_path).expanduser()
    else:
        log_dir = Path.home() / "logs"
    
    project_name = "sports_calendar" 
    return log_dir / f"{project_name}.log"


LOG_FILE_PATH = _resolve_log_file_path()


def configure_logging() -> None:
    root_logger = logging.getLogger()

    if getattr(configure_logging, "_configured", False):
        return

    LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()

    console_handler = None
    if sys.stdout.isatty():
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(
            logging.Formatter("%(levelname)s | %(message)s")
        )

    file_handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    if console_handler is not None:
        root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logging.getLogger("googleapiclient").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient.discovery").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient.http").setLevel(logging.WARNING)
    logging.getLogger("httplib2").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)

    configure_logging._configured = True
