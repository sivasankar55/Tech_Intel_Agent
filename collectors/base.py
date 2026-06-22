from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from utils.logger import setup_logger


class BaseCollector(ABC):
    def __init__(self, config: Any, db: Any):
        self.config = config
        self.db = db
        self.logger = setup_logger(self.__class__.__name__)

    @abstractmethod
    def collect(self) -> list[dict[str, Any]]:
        pass

    def run(self) -> list[dict[str, Any]]:
        self.logger.info(f"Starting collection: {self.__class__.__name__}")
        try:
            results = self.collect()
            self.logger.info(f"Collected {len(results)} items from {self.__class__.__name__}")
            return results
        except Exception as e:
            self.logger.error(f"Collection failed: {e}", exc_info=True)
            return []
