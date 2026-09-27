import logging
from logging.config import dictConfig
from config import settings

def configure_logging() -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": { 
                "standard": {
                    "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "stream": "ext://sys.stdout"
                }
            },
            "root": {
                "handlers" : ["console"],
                "level": settings.log_level
            },
            "loggers":{ # Special behavior for uvicorn: CODE THAT SENDS A MESSAGE
                "uvicorn.access": {
                    "handlers" : ["console"],
                    "level": "WARNING",
                    "propagate": False
                },
                "uvicorn.error": {
                    "handlers" : ["console"],
                    "level": "INFO",
                    "propagate": False
                },
            }
        }
    )

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)