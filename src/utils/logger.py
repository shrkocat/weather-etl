"""
Centralized logging setup.

Every module in the pipeline calls get_logger(__name__) instead of
configuring its own handlers. This keeps log format consistent and means
changing the logging behavior (level, rotation, destinations) happens in
one place: config/logging.yaml.
"""

import logging
import logging.config
import os
from pathlib import Path

import yaml

_CONFIGURED = False


def _configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    project_root = Path(__file__).resolve().parents[2]
    config_path = project_root / "config" / "logging.yaml"
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)

    if config_path.exists():
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Make the filename path absolute + relative to project root so this
        # works no matter what directory the script is invoked from.
        file_handler = config.get("handlers", {}).get("file")
        if file_handler and "filename" in file_handler:
            file_handler["filename"] = str(project_root / file_handler["filename"])

        logging.config.dictConfig(config)
    else:
        # Fallback if the config file is missing, so the pipeline never
        # crashes just because of a logging misconfiguration.
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        )

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    _configure_logging()
    return logging.getLogger(name)
