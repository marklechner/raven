import feedparser
from datetime import datetime, timedelta
from typing import List
import httpx
import logging
from models.news_item import NewsItem
from collectors.base_collector import BaseCollector

logger = logging.getLogger(__name__)

class RiskyBizCollector(BaseCollector):
    def __init__(self, config: dict):
        super().__init__(config)
        collector_config = config.get('collectors', {}).get('riskybiz', {})
        self.feed_url = collector_config.get('feed_url', "https://risky.biz/feeds/risky-business/")
        # Use global max_age_days if not specified in collector config
        self.max_age_days = collector_config.get('max_age_days', config['global']['max_age_days'])

    async def collect(self) -> List[NewsItem]:
        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"Fetching feed from {self.feed_url}")
                response = await client.get(self.feed_url)
                response.raise_for_status()
                
                feed = feedparser.parse(response.text)
                logger.debug(f"Found {len(feed.entries)} total entries in feed")
                
                # Calculate cutoff date
                cutoff_date = datetime.now() - timedelta(days=self.max_age_days)
                logger.info(f"Filtering for items newer than {cutoff_date}")
                
                news_items = []
                for entry in feed.entries:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6])
                        
                        if pub_date < cutoff_date:
                            logger.debug(f"Skipping old item: {entry.title} from {pub_date}")
                            continue
                            
                        news_item = NewsItem(
                            source="risky.biz",
                            title=entry.title,
                            content=entry.description,
                            url=entry.link,
                            published_date=pub_date,
                            categories=entry.get("categories", [])
                        )
                        news_items.append(news_item)
                        
                    except Exception as e:
                        logger.error(f"Error processing feed entry: {str(e)}")
                
                logger.info(f"Collected {len(news_items)} items within the last {self.max_age_days} days")
                return news_items
                
        except Exception as e:
            logger.error(f"Error collecting from Risky.biz: {str(e)}")
            raise