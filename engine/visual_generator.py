import os
import random
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips, CompositeAudioClip

class VisualGenerator:
    def __init__(self, config):
        self.config = config
        self.width, self.height = self.config.TARGET_RESOLUTION

    def generate_thumbnail(self, title, output_path):
        """
        Generates a catchy YouTube Shorts thumbnail using Pillow.
        """
        print("Generating YouTube Thumbnail...")
        # Create a background with a random vibrant color gradient (simplified to solid for now)
        colors = [(255, 99, 71), (135, 206, 250), (60, 179, 113), (255, 165, 0), (147, 112, 219)]
        bg_color = random.choice(colors)
        
        img = Image.new('RGB', (self.width, self.height), color=bg_color)
        d = ImageDraw.Draw(img)
        
        # Load a default font (you can download a custom .ttf and point to it later)
        try:
            # Try to load a standard Windows font
            font = ImageFont.truetype("arialbd.ttf", 100)
        except:
            # Fallback to default
            font = ImageFont.load_default()

        # Add text to the center (basic text wrapping)
        text_color = (255, 255, 255)
        # We wrap text manually for a simple implementation
        words = title.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line + word) > 15: # Arbitrary wrap length
                lines.append(current_line)
                current_line = word + " "
            else:
                current_line += word + " "
        lines.append(current_line)
        
        y_text = self.height // 3
        for line in lines:
            # Calculate bounding box to center text
            bbox = d.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            d.text(((self.width - text_width) / 2, y_text), line, font=font, fill=text_color)
            y_text += 120

        img.save(output_path)
        print(f"Thumbnail saved to: {output_path}")
        return output_path

    def generate_slide(self, text, output_path, bg_color):
        """
        Generates a single cartoonish text slide for the video.
        """
        img = Image.new('RGB', (self.width, self.height), color=bg_color)
        d = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arialbd.ttf", 80)
        except:
            font = ImageFont.load_default()

        # Wrap text
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line + word) > 20:
                lines.append(current_line)
                current_line = word + " "
            else:
                current_line += word + " "
        lines.append(current_line)

        y_text = self.height // 2 - (len(lines) * 40)
        for line in lines:
            bbox = d.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            # Draw shadow
            d.text(((self.width - text_width) / 2 + 5, y_text + 5), line, font=font, fill=(0,0,0))
            # Draw text
            d.text(((self.width - text_width) / 2, y_text), line, font=font, fill=(255, 255, 255))
            y_text += 100

        img.save(output_path)
        return output_path

    def assemble_video(self, script_text, audio_path, output_video_path):
        """
        Assembles the generated slides and audio into a final MP4 video.
        """
        print("Assembling final video with visuals and audio...")
        
        # 1. Load Audio
        audio_clip = AudioFileClip(audio_path)
        total_duration = audio_clip.duration
        
        # 2. Split script into segments for slides
        segments = [s.strip() for s in script_text.split('|') if s.strip()]
        if len(segments) < 2:
            # If no pipe delimiters, just split roughly by sentences or chunks
            words = script_text.split()
            chunk_size = len(words) // 4 + 1
            segments = [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
            
        time_per_slide = total_duration / len(segments)
        
        # 3. Generate Slide Images and Clips
        video_clips = []
        colors = [(255, 105, 180), (70, 130, 180), (50, 205, 50), (218, 165, 32)]
        
        for i, segment in enumerate(segments):
            slide_path = os.path.join(self.config.OUTPUT_DIR, f"temp_slide_{i}.jpg")
            bg_color = colors[i % len(colors)]
            self.generate_slide(segment, slide_path, bg_color)
            
            # Create ImageClip for this slide
            img_clip = ImageClip(slide_path).set_duration(time_per_slide)
            video_clips.append(img_clip)
            
        # Concatenate slides
        final_visuals = concatenate_videoclips(video_clips, method="compose")
        final_visuals = final_visuals.set_audio(audio_clip)

        # 4. Add Background Music (if exists)
        if os.path.exists(self.config.BACKGROUND_MUSIC_PATH):
            bg_music = AudioFileClip(self.config.BACKGROUND_MUSIC_PATH).volumex(self.config.BACKGROUND_MUSIC_VOLUME)
            if bg_music.duration < total_duration:
                from moviepy.audio.fx.all import audio_loop
                bg_music = audio_loop(bg_music, duration=total_duration)
            else:
                bg_music = bg_music.subclip(0, total_duration)
            
            final_audio = CompositeAudioClip([audio_clip, bg_music])
            final_visuals = final_visuals.set_audio(final_audio)

        # 5. Export Video
        print(f"Exporting final MP4 to {output_video_path}...")
        final_visuals.write_videofile(
            output_video_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=os.path.join(self.config.OUTPUT_DIR, "temp-audio.m4a"),
            remove_temp=True
        )
        print("Video generation complete!")
        
        # Clean up temp slides
        for i in range(len(segments)):
            temp_path = os.path.join(self.config.OUTPUT_DIR, f"temp_slide_{i}.jpg")
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        return output_video_path
