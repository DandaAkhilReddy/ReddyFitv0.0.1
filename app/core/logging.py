import logging
import sys


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
        handler.setFormatter(formatter)
        root.addHandler(handler)
    root.setLevel(level)

