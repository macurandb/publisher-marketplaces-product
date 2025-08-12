"""
AI services using LangChain
"""

from django.conf import settings
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import OpenAI


class AIProductEnhancer:
    """
    Service for enhancing products using AI
    """

    def __init__(self):
        self.llm = OpenAI(openai_api_key=settings.OPENAI_API_KEY, temperature=0.7)

    def enhance_description(self, title, description, category):
        """
        Enhance product description
        """
        prompt = PromptTemplate(
            input_variables=["title", "description", "category"],
            template="""
            Enhance the following product description for marketplace:
            
            Title: {title}
            Category: {category}
            Current description: {description}
            
            Create an attractive, detailed and sales-optimized description.
            Include key benefits and important features.
            Maximum 500 words.
            """,
        )

        chain = LLMChain(llm=self.llm, prompt=prompt)

        try:
            result = chain.run(title=title, description=description, category=category)
            return result.strip()
        except Exception as e:
            return description  # Fallback to original description

    def generate_keywords(self, title, description, category):
        """
        Generate keywords for SEO
        """
        prompt = PromptTemplate(
            input_variables=["title", "description", "category"],
            template="""
            Generate 10 relevant keywords for this product:
            
            Title: {title}
            Category: {category}
            Description: {description}
            
            Return only the keywords separated by commas.
            """,
        )

        chain = LLMChain(llm=self.llm, prompt=prompt)

        try:
            result = chain.run(title=title, description=description, category=category)
            keywords = [kw.strip() for kw in result.split(",")]
            return keywords[:10]  # Maximum 10 keywords
        except Exception as e:
            return [title.lower()]  # Basic fallback
