import logging
from pathlib import Path

log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

log_file = log_dir / "page_index.log"

logger = logging.getLogger("page_index")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def reset_log():
    """Clear the log file at the start of each new API request."""
    for h in logger.handlers[:]:
        h.close()
        logger.removeHandler(h)
    open(log_file, 'w', encoding='utf-8').close()
    handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def log_node_start(node_name: str):
    logger.info(f"[NODE START] {node_name}")


def log_node_end(node_name: str, message: str = ""):
    logger.info(f"[NODE END] {node_name} | {message}")


def log_error(location: str, error: str):
    logger.error(f"[ERROR] {location} | {error}")


def log_request(operation: str, details: str = ""):
    logger.info(f"[REQUEST] operation={operation} | {details}")


def log_response(operation: str, details: str = ""):
    logger.info(f"[RESPONSE] operation={operation} | {details}")
