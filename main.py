import os
import sys
import argparse

# Force UTF-8 encoding for Windows console to support emojis
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from config import settings
from engine.content_generator import ContentGenerator
from engine.visual_generator import VisualGenerator
from engine.video_editor import VideoEditor
from engine.youtube_uploader import YouTubeUploader
from engine.analytics_ml import AnalyticsMLFeedback

def generate_workflow(topic, platform="youtube"):
    print(f"--- Starting Full Automation Pipeline for [{platform.upper()}] Topic: {topic} ---")
    
    # 1. Generate Script, Audio, and SEO
    generator = ContentGenerator(settings)
    script = generator.generate_script(topic, platform=platform)
    if not script:
        return
    
    seo_metadata = generator.generate_seo_metadata(script, platform=platform)
    print("\n--- SEO METADATA ---")
    print(f"Title: {seo_metadata['title']}")
    print(f"Description: {seo_metadata['description']}")
    print(f"Tags: {seo_metadata['tags']}\n")
    
    base_name = topic.replace(' ', '_').lower()
    audio_path = os.path.join(settings.OUTPUT_DIR, f"{base_name}_audio.mp3")
    generator.generate_hindi_audio(script, audio_path)
    
    # Configure resolution based on platform
    if platform in ["shorts", "instagram"]:
        settings.TARGET_RESOLUTION = (1080, 1920)
    elif platform == "pinterest":
        settings.TARGET_RESOLUTION = (1000, 1500)
    else:
        settings.TARGET_RESOLUTION = (1920, 1080)

    # 2. Generate Thumbnail and Video
    visuals = VisualGenerator(settings)
    
    thumb_path = os.path.join(settings.OUTPUT_DIR, f"{base_name}_{platform}_thumbnail.jpg")
    visuals.generate_thumbnail(seo_metadata['title'], thumb_path)
    
    video_path = os.path.join(settings.OUTPUT_DIR, f"{base_name}_{platform}_final.mp4")
    
    if platform == "pinterest":
        # Pinterest only needs an infographic
        visuals.generate_slide(seo_metadata['title'] + "\n\n" + script, thumb_path, (255, 105, 180))
        print(f"\n--- PINTEREST WORKFLOW COMPLETE ---")
        print(f"Infographic: {thumb_path}")
        return

    visuals.assemble_video(script, audio_path, video_path)
    
    print("\n--- WORKFLOW COMPLETE ---")
    print(f"Final Video: {video_path}")
    print(f"Thumbnail: {thumb_path}")
    print("Run the 'upload' command manually to push to YouTube once you verify the output!")

def process_and_upload(input_path, title, description, tags):
    if not os.path.exists(input_path):
        print(f"Error: Input video not found at {input_path}")
        return

    # Generate output path
    filename = os.path.basename(input_path)
    output_path = os.path.join(settings.OUTPUT_DIR, f"processed_{filename}")

    # 1. Video Processing
    editor = VideoEditor(settings)
    processed_video_path = editor.process_video(input_path, output_path)
    
    if not processed_video_path:
        print("Video processing failed. Aborting upload.")
        return

    # 2. YouTube Upload
    uploader = YouTubeUploader(settings)
    tags_list = [tag.strip() for tag in tags.split(",")] if tags else []
    
    uploader.upload_video(
        file_path=processed_video_path,
        title=title,
        description=description,
        tags=tags_list
    )

def upload_command(video_path, thumb_path, title, description, tags):
    uploader = YouTubeUploader(settings)
    tags_list = [tag.strip() for tag in tags.split(",")] if tags else []
    
    # In a production script, you'd add thumbnail_path to upload_video signature in youtube_uploader.py
    # But for now, we upload the video.
    uploader.upload_video(
        file_path=video_path,
        title=title,
        description=description,
        tags=tags_list
    )
    print(f"Uploaded! Custom Thumbnail is ready at {thumb_path} for manual setting (or future API integration).")

def auto_pilot_workflow(niche, platform="youtube"):
    print(f"--- Starting AUTO-PILOT AI Loop for Niche: {niche} ({platform}) ---")
    
    analytics = AnalyticsMLFeedback(settings)
    
    print("1. Fetching real analytics and predicting next viral topic...")
    # The ML model analyzes past API data and predicts a highly specific topic
    predicted_topic_raw = analytics.analyze_real_trends_and_predict(niche)
    
    # We take the first topic suggested
    predicted_topics = [t.strip() for t in predicted_topic_raw.split('\n') if t.strip()]
    if not predicted_topics:
        print("Failed to predict topics.")
        return
        
    chosen_topic = predicted_topics[0].replace('1. ', '').replace('1.', '').replace('*', '').strip()
    print(f"\n[ML DECISION] Chosen Viral Topic: {chosen_topic}\n")
    
    print("2. Passing topic to Content Generator Pipeline...")
    generate_workflow(chosen_topic, platform=platform)

def main():
    parser = argparse.ArgumentParser(description="Spark Engine: Automated Video Upload YT Workflow")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Command: generate (New AI Workflow)
    generate_parser = subparsers.add_parser("generate", help="Generate AI script, audio, visuals, and SEO")
    generate_parser.add_argument("--topic", help="The tech topic to generate content for (e.g. 'Cloud Computing')", required=True)
    generate_parser.add_argument("--platform", help="Target platform (youtube, shorts, instagram, pinterest)", choices=['youtube', 'shorts', 'instagram', 'pinterest'], default='youtube')
    
    # Command: process (Old NotebookLM manual workflow)
    process_parser = subparsers.add_parser("process", help="Process and upload an existing NotebookLM video")
    process_parser.add_argument("input_video", help="Path to the raw video downloaded from NotebookLM")
    process_parser.add_argument("--title", help="Title for the YouTube video", required=True)
    process_parser.add_argument("--description", help="Description for the YouTube video", required=True)
    process_parser.add_argument("--tags", help="Comma-separated tags for the YouTube video", default="")

    # Command: upload (Upload the generated final video)
    upload_parser = subparsers.add_parser("upload", help="Upload a generated final video to YouTube")
    upload_parser.add_argument("--video", help="Path to the final .mp4", required=True)
    upload_parser.add_argument("--thumb", help="Path to the generated .jpg thumbnail", required=True)
    upload_parser.add_argument("--title", help="Title", required=True)
    upload_parser.add_argument("--description", help="Description", required=True)
    upload_parser.add_argument("--tags", help="Tags", required=True)
    
    # Command: auto-pilot (ML Driven Workflow)
    auto_parser = subparsers.add_parser("auto-pilot", help="Run the ML loop to fetch real analytics, pick a topic, and generate video")
    auto_parser.add_argument("--niche", help="Your channel niche (e.g. 'Tech for Kids')", required=True)
    auto_parser.add_argument("--platform", help="Target platform (youtube, shorts, instagram, pinterest)", choices=['youtube', 'shorts', 'instagram', 'pinterest'], default='youtube')
    
    args = parser.parse_args()
    
    if args.command == "generate":
        generate_workflow(args.topic, platform=args.platform)
    elif args.command == "process":
        process_and_upload(args.input_video, args.title, args.description, args.tags)
    elif args.command == "upload":
        upload_command(args.video, args.thumb, args.title, args.description, args.tags)
    elif args.command == "auto-pilot":
        auto_pilot_workflow(args.niche, platform=args.platform)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
