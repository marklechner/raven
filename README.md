# 🦅 Raven

Risk Analysis & Vulnerability Executive News (RAVEN) is an intelligent security news aggregator designed to help organizations stay informed about relevant security threats and updates. It uses LLMs to analyze and filter security news based on your organization's tech stack, compliance requirements, and critical dependencies.

## Key Features

- **Smart Filtering**: Uses LLMs to analyze news relevance based on your company profile
- **Context-Aware**: Considers your tech stack, third-party dependencies, and compliance requirements
- **Modular Design**: Easy to extend with new collectors and output formats
- **Efficient Processing**: Two-stage LLM analysis to minimize resource usage
- **Configuration Validation**: Robust config validation to ensure correct setup
- **Dry Run Mode**: Preview collection results without processing
- **Time-Based Filtering**: Configurable age-based news filtering

## Getting Started

### Prerequisites

- Python 3.12+
- [Ollama](https://ollama.ai/) with preferred/configured model installed

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/raven.git
cd raven

# Set up Python environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Pull required Ollama model
ollama pull <mistral-small/gemma2 or similar>
```

### Configuration

Create `config/config.yaml` with your organization's profile:

```yaml
global:
  max_age_days: 7  # Default for all collectors

collectors:
  riskybiz:
    enabled: true
    feed_url: "https://risky.biz/feeds/risky-business/"

llm:
  model: "mistral-small"
  relevance_threshold: 0.6
  max_tokens: 500

company:
  name: "Your Company"
  industry: "Your Industry"
  size: "startup|enterprise|..."
  region: "EU|US|APAC|..."
  
  tech_stack:
    cloud:
      - "AWS|GCP|Azure"
    languages:
      - "Python"
      - "Java"
    frameworks:
      - "Flask"
      - "React"
    infrastructure:
      - "Kubernetes"
      - "GitHub"
    
  security_concerns:
    high_priority:
      - "Cloud Security"
      - "API Security"
    compliance:
      - "SOC 2"
      - "GDPR"
    3rd_party_providers:
      - "Critical Provider 1"
      - "Critical Provider 2"
    
  assets:
    critical_systems:
      - "System 1"
      - "System 2"
```

### Usage

```bash
# Basic usage
python -m src.main

# Available commands:
python -m src.main --help                      # Show help
python -m src.main --check-config              # Validate config
python -m src.main --config custom-config.yaml  # Use custom config
python -m src.main --log-level DEBUG           # Set log level
python -m src.main --max-age 3                 # Override max age
python -m src.main --dry-run                   # Preview collection
```

## Project Structure

```
raven/
├── config/               # Configuration files
│   └── config.yaml
├── src/
│   ├── collectors/      # News source collectors
│   │   ├── base_collector.py
│   │   └── riskybiz_collector.py
│   ├── processors/      # LLM processing logic
│   │   └── llm_processor.py
│   ├── delivery/        # Output formatting
│   │   └── console_output.py
│   ├── models/         # Data models
│   │   └── news_item.py
│   ├── utils/          # Utility functions
│   │   └── config_validator.py
│   └── main.py
└── tests/              # Test suite
```

## Adding New Features

### Implementing a New Collector

1. Create a new collector class in `src/collectors/`:

```python
from collectors.base_collector import BaseCollector
from models.news_item import NewsItem
from typing import List

class MyNewCollector(BaseCollector):
    def __init__(self, config: dict):
        super().__init__(config)
        # Initialize collector-specific settings

    async def collect(self) -> List[NewsItem]:
        # Implement collection logic
        pass
```

2. Update `config.yaml` with collector settings:

```yaml
collectors:
  mynewcollector:
    enabled: true
    # collector-specific settings
```

### Adding New Output Formats

1. Create a new output handler in `src/delivery/`:

```python
from models.news_item import NewsItem

class MyOutputHandler:
    def __init__(self, config: dict):
        self.config = config

    def deliver(self, news_item: NewsItem):
        # Implement delivery logic
```

### Customizing LLM Processing

The `LLMProcessor` class in `src/processors/llm_processor.py` handles:
- Quick relevance checks
- Detailed analysis
- Company context integration

Modify the prompts and processing logic to adjust analysis behavior.

## Development Guidelines

- Use type hints for better code clarity
- Add logging for important operations
- Follow the existing modular architecture
- Write tests for new features
- Update documentation as needed
- Validate configurations using the built-in validator

## Future Improvements

- [ ] Additional news sources (X, Mastodon, etc.)
- [ ] Alternative LLM backends
- [ ] Advanced filtering options
- [ ] Web interface
- [ ] Alert system for critical news
- [ ] Historical data analysis
- [ ] Automated vulnerability correlation
- [ ] Enhanced third-party risk analysis
- [ ] Batch processing mode
- [ ] Export capabilities

## License

This project is licensed under the MIT License - see the LICENSE file for details.  