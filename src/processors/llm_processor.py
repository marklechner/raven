import ollama
from typing import List, Tuple
from models.news_item import NewsItem
import yaml
import logging

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
        prompt = f"""You must respond ONLY with two values: a number between 0 and 1, and either RELEVANT or SKIP.
        Example correct response: "0.8 RELEVANT" or "0.2 SKIP"
        
        Based on this context:
        {self.company_context}

        Analyze this news item:
        Title: {news_item.title}
        Summary: {news_item.content[:500]}...

        Consider:
        1. Direct impact on our tech stack or infrastructure
        2. Vulnerabilities in our critical 3rd party providers
        3. Compliance and regulatory implications
        4. Industry-wide threats relevant to our sector
        5. Supply chain security concerns

        Respond with ONLY two values: score (0-1) and decision (RELEVANT/SKIP).
        """

        response = ollama.generate(
            model=self.model_name,
            prompt=prompt,
            #max_tokens=50
        )

        try:
            # Clean up the response and handle potential formatting issues
            cleaned_response = response['response'].strip().split('\n')[0]  # Take first line only
            parts = cleaned_response.split()
            
            # Look for a number and a decision word in the response
            score = 0.0
            decision = "SKIP"
            
            for part in parts:
                try:
                    # Try to convert to float
                    potential_score = float(part)
                    if 0 <= potential_score <= 1:
                        score = potential_score
                except ValueError:
                    # If not a number, check if it's a decision word
                    if part.upper() in ["RELEVANT", "SKIP"]:
                        decision = part.upper()

            logger.debug(f"Parsed relevance check: score={score}, decision={decision}")
            return (decision == "RELEVANT", score)
            
        except Exception as e:
            logger.error(f"Error parsing relevance check: {str(e)}\nRaw response: {response['response']}")
            return (False, 0.0)  # Default to not relevant on parsing errors
    

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