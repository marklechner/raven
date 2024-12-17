# src/collectors/base_collector.py
from abc import ABC, abstractmethod
from typing import List
from models.news_item import NewsItem

class BaseCollector(ABC):
    def __init__(self, config: dict):
        self.config = config
        # Use source-specific max_age if defined, otherwise fall back to global
        self.max_age_days = (
            config.get('collectors', {}).get(self.__class__.__name__.lower(), {}).get('max_age_days') 
            or config['global']['max_age_days']
        )

    @abstractmethod
    async def collect(self) -> List[NewsItem]:
        """Collect news items from the source"""
        pass