# src/collectors/record_collector.py
from datetime import datetime, timezone
from typing import List
import json
import logging
import httpx
from bs4 import BeautifulSoup
from collectors.base_collector import BaseCollector
from models.news_item import NewsItem

logger = logging.getLogger(__name__)

class TheRecordCollector(BaseCollector):
    BASE_URL = "https://therecord.media/news"
    SOURCE_NAME = "The Record Media"
    
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
                
                articles = []
                
                for article_data in latest_news_items:
                    try:
                        attrs = article_data.get('attributes', {})
                        published_date = datetime.fromisoformat(attrs.get('date').replace('Z', '+00:00'))
                        
                        age_days = (datetime.now(timezone.utc) - published_date).days
                        if age_days > self.max_age_days:
                            logger.debug(f"Skipping article from {published_date} (too old)")
                            continue
                        
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
                            published_date=published_date,
                            categories=categories,
                            analysis=None,
                            relevance_score=None
                        )
                        
                        articles.append(news_item)
                        logger.debug(f"Successfully processed article: {news_item.title}")
                        
                    except Exception as e:
                        logger.error(f"Error processing article: {str(e)}")
                        continue
                
                logger.info(f"Successfully collected {len(articles)} articles from {self.SOURCE_NAME}")
                return articles
                
            except Exception as e:
                logger.error(f"Error fetching articles: {str(e)}")
                return []