from rich.console import Console
from rich.panel import Panel
from models.news_item import NewsItem

class ConsoleOutput:
    def __init__(self):
        self.console = Console()

    def deliver(self, news_item: NewsItem):
        self.console.print(Panel.fit(
            f"[bold blue]{news_item.title}[/bold blue]\n\n"
            f"[yellow]Source:[/yellow] {news_item.source}\n"
            f"[yellow]Published:[/yellow] {news_item.published_date}\n\n"
            f"[green]Analysis:[/green]\n{news_item.analysis}\n\n"
            f"[yellow]Relevance Score:[/yellow] {news_item.relevance_score}",
            title="Security News Alert"
        ))