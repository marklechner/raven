from typing import Dict, List, Union
import logging
from pydantic import BaseModel, Field, validator
from datetime import datetime

logger = logging.getLogger(__name__)

class CollectorConfig(BaseModel):
    enabled: bool = True
    feed_url: str = ""
    max_age_days: int = None  # Optional, falls back to global

    @validator('max_age_days')
    def validate_max_age(cls, v):
        if v is not None and (v < 1 or v > 90):
            raise ValueError('max_age_days must be between 1 and 90')
        return v

class LLMConfig(BaseModel):
    model: str
    relevance_threshold: float = Field(ge=0.0, le=1.0)
    max_tokens: int = Field(gt=0)

class TechStack(BaseModel):
    cloud: List[str] = []
    languages: List[str] = []
    frameworks: List[str] = []
    infrastructure: List[str] = []

class SecurityConcerns(BaseModel):
    high_priority: List[str] = []
    compliance: List[str] = []
    third_party_providers: List[str] = Field(alias='3rd_party_providers', default=[])

class Assets(BaseModel):
    critical_systems: List[str]

class CompanyProfile(BaseModel):
    name: str
    industry: str
    size: str
    region: str
    tech_stack: TechStack
    security_concerns: SecurityConcerns
    assets: Assets

class GlobalConfig(BaseModel):
    max_age_days: int = Field(ge=1, le=90, default=7)

class RavenConfig(BaseModel):
    global_: GlobalConfig = Field(alias='global')
    collectors: Dict[str, CollectorConfig]
    llm: LLMConfig
    company: CompanyProfile

def validate_config(config: Dict) -> Union[RavenConfig, List[str]]:
    """
    Validate the configuration and return either a validated config object
    or a list of validation errors.
    """
    try:
        validated_config = RavenConfig(**config)
        return validated_config
    except Exception as e:
        logger.error(f"Configuration validation failed: {str(e)}")
        return str(e).split('\n')

# Add config check command
def check_config(config_path: str) -> bool:
    """
    Check if a configuration file is valid.
    Returns True if valid, False if invalid.
    """
    import yaml
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        result = validate_config(config)
        
        if isinstance(result, RavenConfig):
            logger.info("Configuration is valid!")
            logger.info("\nConfiguration summary:")
            logger.info(f"- Company: {result.company.name}")
            logger.info(f"- Industry: {result.company.industry}")
            logger.info(f"- Collectors: {', '.join(result.collectors.keys())}")
            logger.info(f"- LLM Model: {result.llm.model}")
            return True
        else:
            logger.error("Configuration validation failed!")
            logger.error("\nValidation errors:")
            for error in result:
                logger.error(f"- {error}")
            return False
            
    except Exception as e:
        logger.error(f"Error reading or parsing configuration: {str(e)}")
        return False