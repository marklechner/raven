import asyncio
import yaml
import logging
import sys
import argparse
from rich.console import Console
from collectors.riskybiz_collector import RiskyBizCollector
from collectors.record_collector import TheRecordCollector
from collectors.mock_collector import MockCollector
from processors.llm_processor import LLMProcessor
from processors.deduplication_processor import DeduplicationProcessor
from delivery.console_output import ConsoleOutput
from utils.config_validator import check_config, validate_config, RavenConfig

console = Console()
logger = logging.getLogger(__name__)

def setup_argparse():
    parser = argparse.ArgumentParser(description='Raven Security News Aggregator')
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set the logging level'
    )
    parser.add_argument(
        '--max-age',
        type=int,
        help='Override maximum age in days for news items (applies to all collectors)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without LLM processing, show what would be collected'
    )
    parser.add_argument(
        '--check-config',
        action='store_true',
        help='Validate configuration file and exit'
    )
    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--no-dedup',
        action='store_true',
        help='Disable deduplication between news sources'
    )
    return parser

def setup_logging(log_level: str):
    """Configure logging with specified level"""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(levelname)s:%(name)s:%(message)s'
    )


def load_config(config_path: str, max_age: int = None) -> dict:
    """Load and prepare configuration"""
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Initialize global section
    if 'global' not in config:
        config['global'] = {}
    
    # Override max_age if provided
    if max_age is not None:
        config['global']['max_age_days'] = max_age
    elif 'max_age_days' not in config['global']:
        config['global']['max_age_days'] = 7
    
    # Ensure required sections exist
    config.setdefault('collectors', {})
    config['collectors'].setdefault('riskybiz', {})
    
    return config


async def process_news_items(collectors, deduplicator, processor, output, dry_run: bool = False):
    """Collect and process news items from all collectors"""
    all_news_items = []
    
    # Collect from all sources
    for collector in collectors:
        try:
            news_items = await collector.collect()
            all_news_items.extend(news_items)
            logger.info(f"Collected {len(news_items)} items from {collector.__class__.__name__}")
        except Exception as e:
            logger.error(f"Error collecting from {collector.__class__.__name__}: {str(e)}")
    
    if not all_news_items:
        logger.info("No news items collected from any source")
        return

    # Deduplicate before processing
    unique_items = await deduplicator.deduplicate(all_news_items)
    
    if dry_run:
        display_dry_run_results(unique_items)
        return
    
    logger.info(f"Processing {len(unique_items)} unique news items")
    
    for item in unique_items:
        try:
            processed_item = await processor.process_news(item)
            output.deliver(processed_item)
        except Exception as e:
            logger.error(f"Error processing item: {str(e)}")


def display_dry_run_results(news_items):
    """Display detailed results in dry-run mode"""
    console.print("\n[bold]Would process these items:[/bold]")
    for item in news_items:
        console.print(f"\n[yellow]Source:[/yellow] {item.source}")
        console.print(f"[yellow]Title:[/yellow] {item.title}")
        console.print(f"[yellow]Date:[/yellow] {item.published_date}")
        console.print(f"[yellow]URL:[/yellow] {item.url}")
        console.print(f"[yellow]Categories:[/yellow] {', '.join(item.categories)}")
        console.print("[yellow]Content Preview:[/yellow]")
        # Show first 200 chars of content with word boundary
        preview = item.content[:200] + ("..." if len(item.content) > 200 else "")
        console.print(preview)
        console.print(f"[gray]Content length: {len(item.content)} characters[/gray]")
        console.print("─" * 80)  # Separator
    console.print(f"\nTotal items: {len(news_items)}")
    console.print("=== DRY RUN COMPLETE ===")


def initialize_components(config: dict):
    """Initialize all required components"""
    collectors = []
    
    if config['collectors'].get('riskybiz', {}).get('enabled', False):
        collectors.append(RiskyBizCollector(config))
    
    if config['collectors'].get('therecord', {}).get('enabled', False):
        collectors.append(TheRecordCollector(config))
        
    if config['collectors'].get('mock', {}).get('enabled', False):
        collectors.append(MockCollector(config))

    return (
        collectors,
        DeduplicationProcessor(),
        LLMProcessor(),
        ConsoleOutput()
    )


async def run_raven(args):
    """Main execution logic"""
    config = load_config(args.config, args.max_age)
    validation_result = validate_config(config)
    
    if not isinstance(validation_result, RavenConfig):
        logger.error("Invalid configuration!")
        for error in validation_result:
            logger.error(f"- {error}")
        return False
    
    collectors, deduplicator, processor, output = initialize_components(config)
    
    try:
        if args.dry_run:
            console.print("[bold yellow]=== DRY RUN MODE ===[/bold yellow]")

        # Collection phase
        console.print("\n[bold blue]📥 Collecting news from sources...[/bold blue]")
        all_news_items = []
        source_stats = {}

        for collector in collectors:
            collector_name = collector.__class__.__name__.replace('Collector', '')
            try:
                console.print(f"[cyan]Fetching from {collector_name}...[/cyan]")
                news_items = await collector.collect()
                all_news_items.extend(news_items)
                source_stats[collector_name] = len(news_items)
            except Exception as e:
                logger.error(f"Error collecting from {collector_name}: {str(e)}")
                source_stats[collector_name] = 0

        # Display collection statistics
        console.print("\n[bold green]Collection Summary:[/bold green]")
        for source, count in source_stats.items():
            console.print(f"[green]- {source}: {count} items[/green]")
        console.print(f"[bold green]Total items collected: {len(all_news_items)}[/bold green]")

        if not all_news_items:
            console.print("[yellow]No news items collected from any source[/yellow]")
            return True

        # Deduplication phase
        if args.no_dedup:
            console.print("\n[bold yellow]Deduplication disabled[/bold yellow]")
            items_to_process = all_news_items
        else:
            console.print("\n[bold blue]🔄 Running deduplication...[/bold blue]")
            items_to_process = await deduplicator.deduplicate(all_news_items)
            console.print(f"[green]Deduplicated {len(all_news_items)} → {len(items_to_process)} items[/green]")

        if args.dry_run:
            display_dry_run_results(items_to_process)
            return True

        # Relevance check and processing phase
        console.print("\n[bold blue]🤖 Checking relevance and processing items...[/bold blue]")
        processed_count = 0
        relevant_count = 0

        for item in items_to_process:
            try:
                processed_item = await processor.process_news(item)
                if processed_item.relevance_score > config['llm']['relevance_threshold']:
                    relevant_count += 1
                    output.deliver(processed_item)
                processed_count += 1
            except Exception as e:
                logger.error(f"Error processing item: {str(e)}")

        # Final statistics
        console.print("\n[bold green]Processing Summary:[/bold green]")
        console.print(f"[green]- Items processed: {processed_count}[/green]")
        console.print(f"[green]- Relevant items: {relevant_count}[/green]")
        console.print(f"[green]- Items filtered out: {processed_count - relevant_count}[/green]")

        return True

    except Exception as e:
        logger.error(f"Error during processing: {str(e)}")
        return False
    

RAVEN_ASCII = """
[bold blue]
██████╗  █████╗ ██╗   ██╗███████╗███╗   ██╗
██╔══██╗██╔══██╗██║   ██║██╔════╝████╗  ██║
██████╔╝███████║██║   ██║█████╗  ██╔██╗ ██║
██╔══██╗██╔══██║╚██╗ ██╔╝██╔══╝  ██║╚██╗██║
██║  ██║██║  ██║ ╚████╔╝ ███████╗██║ ╚████║
╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚═╝  ╚═══╝
[/bold blue]
[bold yellow]Risk Analysis & Vulnerability Executive News[/bold yellow]
[italic cyan]Watching the skies for security threats...[/italic cyan]
"""

async def main():
    """Entry point with command handling"""
    parser = setup_argparse()
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    try:
        # Display ASCII art (except for --check-config)
        if not args.check_config:
            console.print(RAVEN_ASCII)
        
        # Handle config check command
        if args.check_config:
            sys.exit(0 if check_config(args.config) else 1)
        
        # Run main program
        logger.info("Starting Raven Security News Aggregator")
        success = await run_raven(args)
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())