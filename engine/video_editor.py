from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
import os

class VideoEditor:
    def __init__(self, config):
        self.config = config

    def process_video(self, input_video_path, output_video_path):
        """
        Processes the input video by cropping the watermark and adding background music.
        """
        print(f"Processing video: {input_video_path}")
        try:
            # 1. Load Video
            video = VideoFileClip(input_video_path)

            # 2. Crop Watermark (Bottom right corner)
            w, h = video.size
            # Crop to remove the bottom 50 pixels (adjustable in settings)
            cropped_video = video.crop(x1=0, y1=0, x2=w, y2=h - self.config.WATERMARK_CROP_PIXELS)

            # 3. Add Background Music
            if os.path.exists(self.config.BACKGROUND_MUSIC_PATH):
                bg_music = AudioFileClip(self.config.BACKGROUND_MUSIC_PATH).volumex(self.config.BACKGROUND_MUSIC_VOLUME)
                
                # Loop background music if it's shorter than video, or trim if longer
                if bg_music.duration < cropped_video.duration:
                    from moviepy.audio.fx.all import audio_loop
                    bg_music = audio_loop(bg_music, duration=cropped_video.duration)
                else:
                    bg_music = bg_music.subclip(0, cropped_video.duration)
                
                # Combine original audio and background music
                original_audio = cropped_video.audio
                if original_audio:
                    final_audio = CompositeAudioClip([original_audio, bg_music])
                else:
                    final_audio = bg_music
                
                cropped_video = cropped_video.set_audio(final_audio)
            else:
                print(f"Warning: Background music file not found at {self.config.BACKGROUND_MUSIC_PATH}")

            # 4. Export Video
            print(f"Exporting processed video to {output_video_path}...")
            cropped_video.write_videofile(
                output_video_path,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile="temp-audio.m4a",
                remove_temp=True,
                fps=24
            )
            print("Video processing complete!")
            return output_video_path
        
        except Exception as e:
            print(f"Error during video processing: {e}")
            return None
        finally:
            if 'video' in locals():
                video.close()
