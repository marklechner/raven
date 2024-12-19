import ollama
from typing import List, Tuple
from models.news_item import NewsItem
import yaml
import logging
import re

logger = logging.getLogger(__name__)

class LLMProcessor:
    def __init__(self, model_name: str = "mistral-small"):
        self.model_name = model_name
        with open("config/config.yaml", "r") as f:
            self.config = yaml.safe_load(f)
        
        # Pre-construct company context once
        self.company_context = self._build_company_context()

    def _build_company_context(self) -> str:
        company = self.config['company']
        context = f"""
        Company Profile:
        - {company['name']} is a {company['size']} {company['industry']} company in {company['region']}
        
        Technical Environment:
        - Cloud Platforms: {', '.join(company['tech_stack']['cloud'])}
        - Development: {', '.join(company['tech_stack']['languages'])} with {', '.join(company['tech_stack']['frameworks'])}
        - Infrastructure: {', '.join(company['tech_stack']['infrastructure'])}
        
        Security & Compliance:
        - Key Security Focus: {', '.join(company['security_concerns']['high_priority'])}
        - Compliance Requirements: {', '.join(company['security_concerns']['compliance'])}
        
        Critical Dependencies:
        - Core Systems: {', '.join(company['assets']['critical_systems'])}
        - Critical 3rd Party Providers: {', '.join(company['security_concerns']['3rd_party_providers'])}
        """
        return context


    async def check_relevance(self, news_item: NewsItem) -> Tuple[bool, float]:
        """Quick relevance check before full analysis"""
        prompt = f"""Given this company context and news item, analyze its relevance.

        Company Context:
        {self.company_context}

        News Item:
        Title: {news_item.title}
        Summary: {news_item.content[:500]}

        Consider specifically:
        1. Does it affect our tech stack (GCP, Azure, Python, Java, etc.)?
        2. Does it impact our critical 3rd party providers (Vercel, Okta)?
        3. Does it relate to our compliance requirements (NIS2, ISO 27001, SOC 2, GDPR)?
        4. Could it affect our critical systems (OCR, LLM)?
        5. Is it relevant to our security concerns (Cloud Security, API Security, Identity Management)?

        After your analysis, provide your final decision in the format:
        <number between 0 and 1> <RELEVANT or SKIP>

        Example correct format:
        0.8 RELEVANT
        """

        response = ollama.generate(
            model=self.model_name,
            prompt=prompt
        )

        logger.debug(f"\nRelevance analysis for: {news_item.title}")
        logger.debug(f"LLM Response:\n{response['response']}")

        try:
            # Use regex to find a float followed by RELEVANT or SKIP
            # This will work even with markdown formatting or if LLM misbehaves with output format
            pattern = r'(\d*\.?\d+)\s*(RELEVANT|SKIP)'
            matches = re.findall(pattern, response['response'])
            
            if not matches:
                raise ValueError("No valid score/decision pair found in response")
                
            # Take the last match if multiple exist
            score_str, decision = matches[-1]
            score = float(score_str)
            
            if not (0 <= score <= 1):
                raise ValueError(f"Score {score} out of valid range [0,1]")
            
            logger.info(f"Relevance decision for '{news_item.title}': {score} ({decision})")
            return (decision == 'RELEVANT', score)
        except Exception as e:
            logger.error(f"Error parsing relevance check: {str(e)}\nFull response: {response['response']}")
            return (False, 0.0)

    async def process_news(self, news_item: NewsItem) -> NewsItem:
        """Full analysis for relevant items"""
        is_relevant, score = await self.check_relevance(news_item)
        
        if not is_relevant:
            news_item.relevance_score = score
            news_item.analysis = "Item deemed not relevant to company context"
            return news_item

        prompt = f"""Analyze this security news item for {self.config['company']['name']}:

        {self.company_context}

        News Item:
        Title: {news_item.title}
        Content: {news_item.content}

        Provide analysis in the following format:

        IMPACT SUMMARY:
        [Brief summary of direct impact to our organization]

        AFFECTED AREAS:
        - Third Party Risk: [Any impact on our critical providers]
        - Technical Stack: [Affected components]
        - Compliance: [Regulatory implications]

        RISK ASSESSMENT:
        - Severity: [Low/Medium/High]
        - Urgency: [Low/Medium/High]
        - Exposure: [Direct/Indirect/Potential]

        RECOMMENDED ACTIONS:
        [Bullet points of specific actions needed]
        """

        response = ollama.generate(
            model=self.model_name,
            prompt=prompt
        )

        news_item.analysis = response['response']
        news_item.relevance_score = score
        
        return news_item