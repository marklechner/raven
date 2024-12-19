from datetime import datetime, timezone, timedelta
from typing import List
import json
import logging
from zoneinfo import ZoneInfo
import httpx
from bs4 import BeautifulSoup
from collectors.base_collector import BaseCollector
from models.news_item import NewsItem

logger = logging.getLogger(__name__)

class TheRecordCollector(BaseCollector):
    BASE_URL = "https://therecord.media/news"
    SOURCE_NAME = "The Record Media"
    TIMEZONE = ZoneInfo("Europe/Paris")  # CET/CEST timezone
    
    async def collect(self) -> List[NewsItem]:
        async with httpx.AsyncClient() as client:
            logger.info(f"Fetching news from {self.BASE_URL}")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            try:
                response = await client.get(
                    self.BASE_URL,
                    headers=headers,
                    follow_redirects=True
                )
                response.raise_for_status()
                
                logger.debug(f"Response status code: {response.status_code}")
                soup = BeautifulSoup(response.text, 'html.parser')
                
                next_data = soup.find('script', {'id': '__NEXT_DATA__'})
                if not next_data:
                    logger.error("Could not find Next.js data")
                    return []
                
                data = json.loads(next_data.string)
                latest_news_items = data.get('props', {}).get('pageProps', {}).get('latestNewsItems', [])
                logger.debug(f"Found {len(latest_news_items)} articles in Next.js data")
                
                # Get current time in CET and calculate cutoff time
                now = datetime.now(self.TIMEZONE)
                cutoff_time = now - timedelta(days=self.max_age_days)
                logger.debug(f"Current time (CET): {now}")
                logger.debug(f"Cutoff time (CET): {cutoff_time}")
                
                articles = []
                
                for article_data in latest_news_items:
                    try:
                        attrs = article_data.get('attributes', {})
                        
                        # Parse UTC date and convert to CET
                        published_date_utc = datetime.fromisoformat(attrs.get('date').replace('Z', '+00:00'))
                        published_date_cet = published_date_utc.astimezone(self.TIMEZONE)
                        
                        # Check if article is within the time window
                        if published_date_cet < cutoff_time:
                            logger.debug(f"Skipping article from {published_date_cet} - before cutoff {cutoff_time}")
                            continue
                        
                        # Log time difference for debugging
                        time_diff = now - published_date_cet
                        hours_old = time_diff.total_seconds() / 3600
                        logger.debug(f"Article age: {hours_old:.2f} hours")
                        
                        slug = attrs.get('page', {}).get('data', {}).get('attributes', {}).get('slug')
                        if not slug:
                            logger.warning("Missing slug for article")
                            continue
                            
                        url = f"https://therecord.media{slug}"
                        logger.debug(f"Processing article: {url}")
                        
                        article_response = await client.get(url, headers=headers)
                        article_soup = BeautifulSoup(article_response.text, 'html.parser')
                        
                        content_element = article_soup.find('div', {'class': 'article__content'})
                        if not content_element:
                            content_element = article_soup.find('div', {'class': 'wysiwyg'})
                        
                        content = content_element.get_text(separator=' ', strip=True) if content_element else ""
                        
                        categories = [part for part in slug.split('/') if part and part != 'news']
                        
                        news_item = NewsItem(
                            source=self.SOURCE_NAME,
                            title=attrs.get('title', ''),
                            content=content,
                            url=url,
                            published_date=published_date_cet,
                            categories=categories,
                            analysis=None,
                            relevance_score=None
                        )
                        
                        articles.append(news_item)
                        logger.debug(f"Successfully processed article: {news_item.title} (published {published_date_cet})")
                        
                    except Exception as e:
                        logger.error(f"Error processing article: {str(e)}")
                        continue
                
                logger.info(f"Successfully collected {len(articles)} articles from {self.SOURCE_NAME}")
                return articles
                
            except Exception as e:
                logger.error(f"Error fetching articles: {str(e)}")
                return []