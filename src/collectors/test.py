import asyncio
import sys
from pathlib import Path

# Add src to path if we're in collectors directory
current_dir = Path(__file__).parent
if current_dir.name == "collectors":
    sys.path.append(str(current_dir.parent))
    from record_collector import TheRecordCollector
    from models.news_item import NewsItem
else:
    # We're already in src
    from collectors.record_collector import TheRecordCollector
    from models.news_item import NewsItem

# Sample configuration
TEST_CONFIG = {
    "global": {
        "max_age_days": 7
    },
    "collectors": {
        "therecordcollector": {
            "max_age_days": 3  # Override global setting for this collector
        }
    }
}

async def main():
    # Initialize the collector
    collector = TheRecordCollector(TEST_CONFIG)
    
    print(f"Starting collection from The Record Media...")
    try:
        # Run the collector
        news_items = await collector.collect()
        
        # Print results
        print(f"\nFound {len(news_items)} articles:")
        for item in news_items:
            print(f"\nTitle: {item.title}")
            print(f"Date: {item.published_date}")
            print(f"URL: {item.url}")
            print(f"Categories: {', '.join(item.categories)}")
            print(f"Content preview: {item.content[:150]}...")
            print("-" * 80)
            
    except Exception as e:
        print(f"Error during collection: {e}")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())