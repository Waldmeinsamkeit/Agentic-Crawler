from __future__ import annotations

import logging
import sys
from contextvars import ContextVar, Token
from pathlib import Path

from config import settings

task_id_var: ContextVar[str] = ContextVar("task_id", default="SYSTEM")


class ThreadIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.thread_id = task_id_var.get()
        return True


def _resolve_log_level() -> int:
    value = (settings.LOG_LEVEL or "INFO").upper()
    return getattr(logging, value, logging.INFO)


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("AI-Crawler")
    logger.setLevel(_resolve_log_level())
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | [%(thread_id)s] | %(name)s : %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    thread_filter = ThreadIdFilter()
    logger.addFilter(thread_filter)
    logger.addHandler(console_handler)
    logger.propagate = False
    return logger


logger = setup_logger()

_task_file_handlers: dict[str, logging.Handler] = {}


def set_task_context(thread_id: str) -> Token:
    return task_id_var.set(thread_id or "SYSTEM")


def reset_task_context(token: Token) -> None:
    task_id_var.reset(token)


def add_task_file_handler(thread_id: str) -> Path:
    if not thread_id:
        thread_id = "SYSTEM"
    if thread_id in _task_file_handlers:
        return settings.log_dir / f"{thread_id}.log"

    log_path = settings.log_dir / f"{thread_id}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | [%(thread_id)s] | %(name)s : %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    _task_file_handlers[thread_id] = file_handler
    return log_path


def remove_task_file_handler(thread_id: str) -> None:
    handler = _task_file_handlers.pop(thread_id, None)
    if handler:
        logger.removeHandler(handler)
        handler.close()

