import logging

_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level.upper(), format=_FORMAT)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
