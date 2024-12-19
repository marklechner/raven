# src/collectors/mock_collector.py
from datetime import datetime
from typing import List
import yaml
import logging
from pathlib import Path
from collectors.base_collector import BaseCollector
from models.news_item import NewsItem

logger = logging.getLogger(__name__)

class MockCollector(BaseCollector):
    SOURCE_NAME = "Mock News"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.mock_data_dir = Path(config.get('collectors', {})
                                .get('mock', {})
                                .get('data_dir', 'data/mock_news'))

    async def collect(self) -> List[NewsItem]:
        try:
            mock_items = []
            
            # Create directory if it doesn't exist
            self.mock_data_dir.mkdir(parents=True, exist_ok=True)
            
            # Read all .yaml files in the mock data directory
            for file_path in self.mock_data_dir.glob('*.yaml'):
                try:
                    with open(file_path, 'r') as f:
                        items = yaml.safe_load(f)
                        
                        for item in items:
                            # Parse the date
                            published_date = datetime.fromisoformat(item['published_date'])
                            
                            # Skip if too old
                            age_days = (datetime.now() - published_date).days
                            if age_days > self.max_age_days:
                                logger.debug(f"Skipping mock item from {published_date} (too old)")
                                continue
                            
                            news_item = NewsItem(
                                source=self.SOURCE_NAME,
                                title=item['title'],
                                content=item['content'],
                                url=item.get('url', 'mock://news'),
                                published_date=published_date,
                                categories=item.get('categories', []),
                                analysis=None,
                                relevance_score=None
                            )
                            mock_items.append(news_item)
                            
                except Exception as e:
                    logger.error(f"Error processing mock file {file_path}: {str(e)}")
                    continue
            
            logger.info(f"Collected {len(mock_items)} mock news items")
            return mock_items
            
        except Exception as e:
            logger.error(f"Error collecting mock news: {str(e)}")
            return []