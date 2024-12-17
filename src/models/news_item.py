from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List

class NewsItem(BaseModel):
    source: str
    title: str
    content: str
    url: Optional[str]  
    published_date: datetime
    categories: List[str] = []
    analysis: Optional[str] = None
    relevance_score: Optional[float] = None