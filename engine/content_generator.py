import os
from google import genai
from gtts import gTTS
from tenacity import retry, stop_after_attempt, wait_exponential

class ContentGenerator:
    def __init__(self, config):
        self.config = config
        # Configure Gemini API using modern SDK
        self.client = genai.Client(api_key=self.config.GEMINI_API_KEY)
        self.model = 'gemini-3.8-flash'

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=4, max=30))
    def _call_gemini(self, prompt):
        return self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )

    def generate_script(self, topic, platform="youtube"):
        """
        Generates educational content depending on the platform.
        """
        print(f"Generating content for platform [{platform}] - Topic: {topic}...")
        
        if platform == "pinterest":
            prompt = f"""
            Write 3-4 bullet points summarizing '{topic}' for 5th-6th grade students.
            The text should be written in Hindi (using Devanagari script).
            Keep it extremely brief and punchy. This will be printed on an infographic image.
            Do not include introductions or conclusions, just the facts.
            """
        elif platform in ["shorts", "instagram"]:
            prompt = f"""
            Write a high-energy, fast-paced educational script for 5th to 6th-grade students about '{topic}'.
            The script should be written in Hindi (using Devanagari script).
            Start with a strong hook. Keep it under 45 seconds when read aloud (around 80-100 words).
            Do not include any visual instructions or brackets like [Scene 1], just the spoken text.
            """
        else: # Standard youtube
            prompt = f"""
            Write an engaging educational script for 5th to 6th-grade students about '{topic}'.
            The script should be written in Hindi (using Devanagari script).
            It should explain the concept using a fun cartoonish analogy.
            Keep it under 60 seconds when read aloud (around 100-150 words).
            Do not include any visual instructions or brackets like [Scene 1], just the spoken text.
            """
        
        try:
            response = self._call_gemini(prompt)
            script_text = response.text.strip()
            print("Script generated successfully!")
            return script_text
        except Exception as e:
            print(f"Error generating script with Gemini: {e}")
            return None

    def generate_seo_metadata(self, script_text, platform="youtube"):
        """
        Generates optimized Title, Description, and Tags.
        """
        print(f"Generating SEO metadata for [{platform}]...")
        
        platform_instructions = ""
        if platform == "pinterest":
            platform_instructions = "1. A catchy Pinterest Pin Title.\n2. A short description with 3 hashtags.\n3. 10 relevant tags."
        elif platform in ["shorts", "instagram"]:
            platform_instructions = "1. A catchy Reel/Short Title (under 60 chars).\n2. A short description with 5 trending hashtags.\n3. 10 relevant tags."
        else:
            platform_instructions = "1. A catchy YouTube Title.\n2. A short description including 3 relevant hashtags.\n3. 10 relevant tags for SEO."
            
        prompt = f"""
        Based on the following Hindi educational content, generate the following in English:
        {platform_instructions}
        
        Content:
        {script_text}
        
        Format the output EXACTLY like this (use these exact labels):
        TITLE: [Your Title]
        DESCRIPTION: [Your Description]
        TAGS: [tag1, tag2, tag3]
        """
        
        try:
            response = self._call_gemini(prompt)
            metadata = response.text.strip()
            
            # Parse the output
            lines = metadata.split('\n')
            title = lines[0].replace("TITLE:", "").strip() if len(lines) > 0 else ""
            description = lines[1].replace("DESCRIPTION:", "").strip() if len(lines) > 1 else ""
            tags = lines[2].replace("TAGS:", "").strip() if len(lines) > 2 else ""
            
            return {
                "title": title,
                "description": description,
                "tags": tags
            }
        except Exception as e:
            print(f"Error generating SEO metadata: {e}")
            return None

    def generate_hindi_audio(self, text, output_path):
        """
        Converts the Hindi text to Speech using gTTS and saves it as an MP3.
        """
        print("Generating Hindi voiceover...")
        try:
            # gTTS (Google Text-to-Speech) - language 'hi' for Hindi
            tts = gTTS(text=text, lang='hi', slow=False)
            tts.save(output_path)
            print(f"Audio saved to: {output_path}")
            return output_path
        except Exception as e:
            print(f"Error generating audio: {e}")
            return None
