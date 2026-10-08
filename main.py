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

def generate_workflow(topic):
    print(f"--- Starting Full Automation Pipeline for Topic: {topic} ---")
    
    # 1. Generate Script, Audio, and SEO
    generator = ContentGenerator(settings)
    script = generator.generate_script(topic)
    if not script:
        return
    
    seo_metadata = generator.generate_seo_metadata(script)
    print("\n--- SEO METADATA ---")
    print(f"Title: {seo_metadata['title']}")
    print(f"Description: {seo_metadata['description']}")
    print(f"Tags: {seo_metadata['tags']}\n")
    
    base_name = topic.replace(' ', '_').lower()
    audio_path = os.path.join(settings.OUTPUT_DIR, f"{base_name}_audio.mp3")
    generator.generate_hindi_audio(script, audio_path)
    
    # 2. Generate Thumbnail and Video
    visuals = VisualGenerator(settings)
    
    thumb_path = os.path.join(settings.OUTPUT_DIR, f"{base_name}_thumbnail.jpg")
    visuals.generate_thumbnail(seo_metadata['title'], thumb_path)
    
    video_path = os.path.join(settings.OUTPUT_DIR, f"{base_name}_final.mp4")
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

def main():
    parser = argparse.ArgumentParser(description="Spark Engine: Automated Video Upload YT Workflow")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Command: generate (New AI Workflow)
    generate_parser = subparsers.add_parser("generate", help="Generate AI script, audio, visuals, and SEO")
    generate_parser.add_argument("--topic", help="The tech topic to generate content for (e.g. 'Cloud Computing')", required=True)
    
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
    
    args = parser.parse_args()
    
    if args.command == "generate":
        generate_workflow(args.topic)
    elif args.command == "process":
        process_and_upload(args.input_video, args.title, args.description, args.tags)
    elif args.command == "upload":
        upload_command(args.video, args.thumb, args.title, args.description, args.tags)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
