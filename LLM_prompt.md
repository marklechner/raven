## LLM template

I'm working on the Raven project - an open source security news aggregator using Python 3.12.4. Key details:

Architecture:
- Collectors (currently RiskyBiz RSS)
- LLM Processor (Ollama with mistral-small)
- Output handlers (currently console)
- YAML configuration for company profile and settings

Current config structure:
collectors:
  riskybiz:
    enabled: true
    feed_url: "https://risky.biz/feeds/risky-business/"
    max_age_days: 7
    update_interval: 3600

llm:
  model: "mistral-small"
  relevance_threshold: 0.6

company:
  [company profile with tech stack, 3rd party providers, compliance needs]

Key features:
- Age-based filtering of news
- Two-stage LLM processing (quick relevance check, then detailed analysis)
- Company context-aware analysis
- Focus on third-party provider risks

[Specific question or feature request here]