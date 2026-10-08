import os
from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential

class SocialMediaManagerAI:
    def __init__(self, config):
        self.config = config
        self.client = genai.Client(api_key=self.config.GEMINI_API_KEY)
        self.model = 'gemini-3.8-flash'

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=4, max=30))
    def _call_gemini(self, prompt, system_instruction):
        return self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )

    def brainstorm_viral_topics(self, niche, count=5):
        """
        Acts as a Marketing Manager to determine what content will go viral today.
        """
        system_instruction = "You are a ruthless, data-driven Social Media Marketing Manager. Your goal is maximum virality, engagement, and retention."
        prompt = f"Give me {count} highly viral, highly clickable video topics in the '{niche}' niche targeting 5th graders to college students. Return ONLY the topics, one per line."
        
        response = self._call_gemini(prompt, system_instruction)
        return [line.strip() for line in response.text.strip().split('\n') if line.strip()]

class SEOExpertAI:
    def __init__(self, config):
        self.config = config
        self.client = genai.Client(api_key=self.config.GEMINI_API_KEY)
        self.model = 'gemini-3.8-flash'

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=4, max=30))
    def _call_gemini(self, prompt, system_instruction):
        return self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )

    def optimize_metadata(self, script_text, platform):
        """
        Acts as a master SEO Analyst to optimize tags, titles, and descriptions.
        """
        system_instruction = "You are an elite SEO Expert who understands YouTube/Instagram/Pinterest algorithms better than anyone. You optimize metadata for maximum click-through rate (CTR) and search visibility."
        prompt = f"""
        Optimize metadata for {platform} based on this content:
        {script_text}
        
        Format exactly as:
        TITLE: [Clickable Title]
        DESCRIPTION: [SEO Heavy Description]
        TAGS: [tag1, tag2, tag3]
        """
        
        response = self._call_gemini(prompt, system_instruction)
        return response.text.strip()
