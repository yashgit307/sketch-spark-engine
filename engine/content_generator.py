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

    def generate_script(self, topic):
        """
        Generates a short educational script in Hindi using the Gemini API.
        """
        print(f"Generating Hindi script for topic: {topic}...")
        prompt = f"""
        Write a very short, engaging educational script for 5th to 6th-grade students about '{topic}'.
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

    def generate_seo_metadata(self, script_text):
        """
        Generates optimized Title, Description, and Tags for YouTube Shorts.
        """
        print("Generating SEO metadata...")
        prompt = f"""
        Based on the following Hindi educational script for a YouTube Short, generate the following in English:
        1. A catchy YouTube Short Title (under 60 characters).
        2. A short description including 3 relevant hashtags.
        3. A comma-separated list of 10 relevant tags for SEO.
        
        Script:
        {script_text}
        
        Format the output EXACTLY like this:
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
