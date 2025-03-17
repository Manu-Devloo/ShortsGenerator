import os
import json
import requests
import edge_tts
import random
import asyncio
import pickle

from openai import OpenAI
from dotenv import load_dotenv
from datetime import timedelta
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip, concatenate_videoclips
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

class ConfigManager:
    def __init__(self):
        self.config = self.load_config()
        load_dotenv()
        
        # Set commonly used config values as properties
        self.background_dir = self.config["paths"]["background_dir"]
        self.temp_dir = self.config["paths"]["temp_dir"]
        self.output_dir = self.config["paths"]["output_dir"]
        
        # Ensure directories exist
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs("./chosen", exist_ok=True)
        
        # API settings
        self.openai_endpoint = os.getenv("OPENAI_ENDPOINT") or self.config["api"]["openai_endpoint"]
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = self.config["api"]["openai_model"]
        self.tts_voice = self.config["api"]["tts_voice"]
        self.pexels_api_key = os.getenv("PEXELS_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")

    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Create default config if not exists
            default_config = {
                "api": {
                    "openai_endpoint": "https://models.inference.ai.azure.com",
                    "openai_model": "Llama-3.3-70B-Instruct",
                    "tts_voice": "en-US-AvaNeural"
                },
                "video": {
                    "short_format": {"width": 1080, "height": 1920},
                    "long_format": {"width": 1920, "height": 1080},
                    "font": "./fonts/Lobster-Regular.ttf",
                    "font_size": 70
                },
                "paths": {
                    "background_dir": "./background",
                    "temp_dir": "./temp",
                    "output_dir": "./output"
                },
                "youtube": {
                    "default_tags": ["Shorts", "QuickClips", "FunFacts"],
                    "default_privacy": "public",
                    "channel_id": ""
                }
            }
            with open('config.json', 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config

class ChosenContentTracker:
    def __init__(self):
        self.chosen_facts = self._load_chosen_content("./chosen/chosen_facts.json")
        self.chosen_stories = self._load_chosen_content("./chosen/chosen_stories.json")
        self.chosen_topics = self._load_chosen_content("./chosen/chosen_topics.json")
        self.last_video_type = self._get_last_video_type()
        self.use_story_prompt = self.last_video_type != 'story'
        
        # Update last video type
        with open('last_video_type.txt', 'w') as file:
            file.write('story' if self.use_story_prompt else 'fact')

    def _load_chosen_content(self, file_path):
        if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
            chosen_content = []
            with open(file_path, 'w') as file:
                json.dump(chosen_content, file, indent=2)
        else:
            with open(file_path, 'r') as file:
                chosen_content = json.load(file)
                if not isinstance(chosen_content, list):
                    chosen_content = []
        return chosen_content

    def _get_last_video_type(self):
        last_video_type_file = 'last_video_type.txt'
        if os.path.exists(last_video_type_file):
            with open(last_video_type_file, 'r') as file:
                return file.read().strip()
        else:
            return 'story'  # Default to 'story' if the file does not exist
    
    def save_new_content(self, content_type, content):
        """Save new content to the appropriate tracking file"""
        if not content:
            return
            
        file_path = None
        content_list = None
        
        if content_type == 'fact':
            file_path = "./chosen/chosen_facts.json"
            content_list = self.chosen_facts
            # Append the new fact
            content_list.append(content)
        elif content_type == 'story':
            file_path = "./chosen/chosen_stories.json"
            content_list = self.chosen_stories
            # Append the new story
            content_list.append(content)
        elif content_type == 'topic':
            file_path = "./chosen/chosen_topics.json"
            content_list = self.chosen_topics
            # Append the new topic
            content_list.append(content)
        
        if file_path and content_list:
            try:
                with open(file_path, 'w') as file:
                    json.dump(content_list, file, indent=2)
                print(f"Added new {content_type} to tracking file")
                return True
            except Exception as e:
                print(f"Error saving to {file_path}: {e}")
                return False
        return False

class TextGenerator:
    def __init__(self, config_manager, content_tracker):
        self.config = config_manager
        self.content_tracker = content_tracker
        self.client = OpenAI(
            api_key=self.config.openai_api_key,
            base_url=self.config.openai_endpoint,
        )

    def generate_text(self, prompt, model=None, max_tokens=500):
        model = model or self.config.openai_model
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a content creating assistant and will follow the users requests exactly."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error: {e}")
            return None

    def get_short_video_prompt(self):
        return f"""
Generate a JSON object for a short-form video script. The script should include a fact, a hook to grab attention, and an engagement question to encourage viewer interaction. The script should be split into three or more parts to ensure frequent background video switches. Each part should include a portion of the script and one relevant stock video keyword. Avoid using any facts from the provided array of already chosen facts. Ensure the script does not always start with "Did you know that". Also, generate a description for the video. Format the response as follows without markdown:

{{
  "fact": "Your interesting fact here",
  "script": [
    {{
      "text": "First part of the script here",
      "keyword": ["keyword1"]
    }},
    {{
      "text": "Second part of the script here",
      "keyword": ["keyword4"]
    }},
    {{
      "text": "Third part of the script here",
      "keyword": ["keyword7"]
    }},
    {{
      "text": "Fourth part of the script here (if needed)",
      "keyword": ["keyword10"]
    }}
  ],
  "description": "Generated description here"
}}
Already Chosen Facts:

{json.dumps(self.content_tracker.chosen_facts, indent=2)}
"""

    def get_story_prompt(self):
        return f"""
Write a fast-paced, engaging short story (30 seconds long) with a shocking twist at the end. The story should have a mysterious or suspenseful tone, making the viewer want to keep watching. Keep the sentences snappy and engaging, with a strong hook at the start. Avoid excessive dialogue and focus on clear, vivid narration. Also, generate a description for the video.

Return the response in the following JSON format without markdown:

{{
  "title": "Short story title",
  "script": "The full story in a single string, formatted for easy narration.",
  "description": "Generated description here"
}}

Already Chosen Stories:

{json.dumps(self.content_tracker.chosen_stories, indent=2)}
"""

    def get_long_video_prompt(self):
        return f"""
Generate a JSON object for a long-form video script, approximately 10 minutes in length. The AI model should select an engaging topic suitable for a broad audience, ensuring the content is educational, entertaining, or thought-provoking. The script should be split into multiple sections to allow for seamless background video transitions, ensuring that each section aligns clearly with its corresponding visuals.

Each section should contain:

A portion of the script
One relevant stock video keyword that match the spoken content
The script should:

Begin with a strong hook to capture attention
Present a logical flow with well-structured points
End with a compelling conclusion and a call to action for viewer engagement
The final output should be formatted as follows without markdown:

{{
  "topic": "Chosen topic for the video",
  "script": [
    {{
      "text": "First part of the script here",
      "keyword": ["keyword1"]
    }},
    {{
      "text": "Second part of the script here",
      "keyword": ["keyword2"]
    }},
    {{
      "text": "Third part of the script here",
      "keyword": ["keyword3"]
    }},
    {{
      "text": "Fourth part of the script here",
      "keyword": ["keyword4"]
    }},
    {{
      "text": "Additional parts as needed to reach ~10 minutes",
      "keyword": ["keywordX"]
    }}
  ],
  "description": "Generated description summarizing the video"
}}
The AI should avoid selecting topics that have already been generated in past requests. The script should be engaging, informative, and structured for long-form content, ensuring a natural flow from introduction to conclusion.

Already choses topics:

{json.dumps(self.content_tracker.chosen_topics, indent=2)}
"""

    def extract_and_save_fact(self, script_data):
        """Extract and save a new fact from script data"""
        if not script_data or not isinstance(script_data, dict):
            return
            
        # Extract the main fact
        if "fact" in script_data and script_data["fact"]:
            fact = script_data["fact"]
            # Save to chosen facts
            self.content_tracker.save_new_content('fact', fact)
            
    def extract_and_save_story(self, script_data):
        """Extract and save a new story from script data"""
        if not script_data or not isinstance(script_data, dict):
            return
            
        # Extract the story title
        if "title" in script_data and script_data["title"]:
            story = script_data["title"]
            # Save to chosen stories
            self.content_tracker.save_new_content('story', story)
            
    def extract_and_save_topic(self, script_data):
        """Extract and save a new topic from script data"""
        if not script_data or not isinstance(script_data, dict):
            return
            
        # Extract the topic
        if "topic" in script_data and script_data["topic"]:
            topic = script_data["topic"]
            # Save to chosen topics
            self.content_tracker.save_new_content('topic', topic)

class FileUtils:
    def __init__(self, config_manager):
        self.config = config_manager
    
    def decode_json(self, text):
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                return None
        return text
    
    def get_random_file(self, directory=None):
        directory = directory or self.config.background_dir
        try:
            files = os.listdir(directory)
            if not files:
                return None
            random_file = random.choice(files)
            return os.path.join(directory, random_file)
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def delete_temp_files(self, file_names=None):
        if not file_names:
            return
            
        for name in file_names:
            file_path = os.path.join(self.config.temp_dir, name)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Deleted temp file: {name}")
                except Exception as e:
                    print(f"Error deleting file {name}: {e}")


class VideoDownloader:
    def __init__(self, config_manager):
        self.config = config_manager
        self.pexels_endpoint = "https://api.pexels.com/videos/search"
    
    def get_video_urls(self, keywords=None, orientation="portrait", duration=5, aantal=None):
        if not keywords:
            keywords = []
            
        videoUrls = []
        
        for keyword in keywords:
            response = requests.get(
                self.pexels_endpoint,
                headers={"Authorization": self.config.pexels_api_key},
                params={"query": keyword, "per_page": 25, "size": "medium", "orientation": orientation},
            )
            
            totalVideoDuration = 0
            
            if response.status_code == 200:
                video_data = response.json()
                if video_data["videos"]:
                    i = 0
                    max_i = len(video_data["videos"])
                    
                    while ((aantal is None or len(videoUrls) < aantal) or totalVideoDuration < duration) and i < max_i:
                        if video_data["videos"][i]["duration"] == None:
                            i += 1
                            continue
                        
                        videoUrls.append(video_data["videos"][i]["video_files"][0]["link"])
                        totalVideoDuration += int(video_data["videos"][i]["duration"])
                        
                        i += 1
                    
        return videoUrls
        
    def download_video(self, url, filename):
        response = requests.get(url, stream=True)
        filename += ".mp4"
        
        file_utils = FileUtils(self.config)
        file_utils.delete_temp_files([filename])
        
        if response.status_code == 200:
            with open(os.path.join(self.config.temp_dir, filename), 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            print(f"Video downloaded successfully: {filename}")
        else:
            print(f"Failed to download video. Status code: {response.status_code}")
            
        return filename


class TTSProcessor:
    def __init__(self, config_manager):
        self.config = config_manager
        self.file_utils = FileUtils(config_manager)
    
    async def convert_text_to_speech_and_vtt(self, text, filename):
        os.makedirs(self.config.temp_dir, exist_ok=True)
        speech = edge_tts.Communicate(text, voice=self.config.tts_voice)
        
        subtitle_data = []
        filename += ".mp3"
        
        self.file_utils.delete_temp_files([filename])
        
        async for chunk in speech.stream():
            if chunk["type"] == "audio":
                if not os.path.exists(os.path.join(self.config.temp_dir, filename)):
                    with open(os.path.join(self.config.temp_dir, filename), "wb") as f:
                        f.write(chunk["data"])
                else:
                    with open(os.path.join(self.config.temp_dir, filename), "ab") as f:
                        f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start_time = str(timedelta(seconds=chunk["offset"] / 10000000))[:11]
                end_time = str(timedelta(seconds=(chunk["offset"] + chunk["duration"]) / 10000000))[:11]
                subtitle_data.append((start_time, end_time, chunk['text']))
        
        return filename, subtitle_data


class VideoProcessor:
    def __init__(self, config_manager):
        self.config = config_manager
        self.file_utils = FileUtils(config_manager)
        self.video_downloader = VideoDownloader(config_manager)
        self.tts_processor = TTSProcessor(config_manager)
    
    def generate_text_clips(self, subtitle_data, position='center', size=None):
        size = size or self.config.config["video"]["font_size"]
        text_clips = []

        for start_time, end_time, text in subtitle_data:
            start_time = sum(float(x) * 60 ** i for i, x in enumerate(reversed(start_time.split(":"))))
            end_time = sum(float(x) * 60 ** i for i, x in enumerate(reversed(end_time.split(":"))))
            duration = end_time - start_time

            text_clip = TextClip(
                text=text,
                font=self.config.config["video"]["font"],
                font_size=size,
                color='white',
                margin=(None, 5 if position != 'center' else None)
            ).with_start(start_time).with_duration(duration).with_position(position)

            text_clips.append(text_clip)

        return text_clips
    
    async def generate_story_video(self, script):
        script_data = self.file_utils.decode_json(script)
        if not script_data:
            return
            
        audioFile, subtitle_data = await self.tts_processor.convert_text_to_speech_and_vtt(script_data["script"], "story")
        textClips = self.generate_text_clips(subtitle_data)
        audioClip = AudioFileClip(os.path.join(self.config.temp_dir, audioFile))
        videoClip = VideoFileClip(self.file_utils.get_random_file()).with_duration(audioClip.duration)
        
        finalVideo = CompositeVideoClip([videoClip] + textClips)
        output_file = os.path.join(self.config.output_dir, "story.mp4")
        finalVideo.write_videofile(
            filename=output_file,
            threads=4,
            preset="ultrafast",
            audio=os.path.join(self.config.temp_dir, audioFile),
            temp_audiofile_path=self.config.temp_dir
        )
        
        self.file_utils.delete_temp_files([audioFile])

    async def generate_short_video(self, script):
        script_data = self.file_utils.decode_json(script)
        if not script_data:
            return None, None
        
        temp_files = []  # Track all temporary files
        segment_files = []  # Track intermediate video segments
        
        try:
            # Process script parts in batches to manage memory efficiently
            for i, part in enumerate(script_data["script"]):
                all_created_clips = []  # Track all clips for proper closing within this batch
                
                audioFile, subtitle_data = await self.tts_processor.convert_text_to_speech_and_vtt(part["text"], f"shortVideoPart-{i}")
                audioClip = AudioFileClip(os.path.join(self.config.temp_dir, audioFile))
                all_created_clips.append(audioClip)
                temp_files.append(audioFile)
                
                textClips = self.generate_text_clips(subtitle_data)
                all_created_clips.extend(textClips)
                
                videoUrls = self.video_downloader.get_video_urls(part["keyword"], duration=audioClip.duration, aantal=3)
                
                videoClips = []
                video_filenames = []
                
                for a, url in enumerate(videoUrls):
                    fileName = self.video_downloader.download_video(url, f"pexelsClip-{i}-{a}")
                    video_filenames.append(fileName)
                    try:
                        short_format = self.config.config["video"]["short_format"]
                        video_clip = VideoFileClip(os.path.join(self.config.temp_dir, fileName), target_resolution=(short_format["width"], short_format["height"]))
                        
                        if video_clip.duration < audioClip.duration / len(videoUrls):
                            video_clip = video_clip.loop(duration=audioClip.duration / len(videoUrls))
                        else:
                            video_clip = video_clip.with_duration(audioClip.duration / len(videoUrls))
                        
                        all_created_clips.append(video_clip)
                        videoClips.append(video_clip)
                    except Exception as e:
                        print(f"Error loading video clip {fileName}: {e}")
                        continue
                    
                # Track all downloaded video files
                temp_files.extend(video_filenames)
                
                if not videoClips:
                    # Fallback if no videos were successfully loaded
                    print(f"No valid video clips for part {i}, using a background video")
                    background = VideoFileClip(self.file_utils.get_random_file()).with_duration(audioClip.duration)
                    all_created_clips.append(background)
                    videoClips = [background]
                
                # Create the composite clip and save it as a segment
                try:
                    # Use compose method which is better for transitions
                    concatenated_video = concatenate_videoclips(videoClips, method="compose")
                    # Ensure the video duration matches the audio duration
                    concatenated_video = concatenated_video.with_duration(audioClip.duration)
                    composite_clip = CompositeVideoClip([concatenated_video] + textClips)
                    composite_clip = composite_clip.with_duration(audioClip.duration).with_audio(audioClip)
                    all_created_clips.append(composite_clip)
                    
                    # Save this segment to a temporary file
                    segment_filename = f"segment_{i}.mp4"
                    segment_path = os.path.join(self.config.temp_dir, segment_filename)
                    composite_clip.write_videofile(
                        filename=segment_path,
                        threads=4,
                        preset="ultrafast",
                        temp_audiofile_path=self.config.temp_dir
                    )
                    segment_files.append(segment_filename)
                except Exception as e:
                    print(f"Error creating composite clip for part {i}: {e}")
                    continue
                finally:
                    # Close all clips in this batch to release memory
                    for clip in all_created_clips:
                        try:
                            clip.close()
                        except Exception as e:
                            print(f"Error closing clip: {e}")
            
            # Combine all segments
            output_file = None
            if segment_files:
                try:
                    # Load segments as clips
                    segment_clips = []
                    for segment in segment_files:
                        segment_path = os.path.join(self.config.temp_dir, segment)
                        clip = VideoFileClip(segment_path)
                        segment_clips.append(clip)
                    
                    finalVideo = concatenate_videoclips(segment_clips, method="compose")
                    output_file = os.path.join(self.config.output_dir, "shortVideo.mp4")
                    finalVideo.write_videofile(
                        filename=output_file,
                        threads=4,                        
                        preset="ultrafast",
                        temp_audiofile_path=self.config.temp_dir
                    )
                    
                    # Close the segment clips
                    for clip in segment_clips:
                        clip.close()
                except Exception as e:
                    print(f"Error rendering final video: {e}")
            
            return output_file, script_data
        finally:
            # Delete temporary files
            self.file_utils.delete_temp_files(temp_files)
            self.file_utils.delete_temp_files(segment_files)
    
    async def generate_long_video(self, script):
        script_data = self.file_utils.decode_json(script)
        if not script_data:
            return None
        
        temp_files = []  # Track all temporary files
        segment_files = []  # Track intermediate video segments
        
        try:
            # Process script parts in batches to manage memory
            for i, part in enumerate(script_data["script"]):
                all_created_clips = []  # Track clips just for this batch
                
                audioFile, subtitle_data = await self.tts_processor.convert_text_to_speech_and_vtt(part["text"], f"longVideoPart-{i}")
                audioClip = AudioFileClip(os.path.join(self.config.temp_dir, audioFile))
                all_created_clips.append(audioClip)
                temp_files.append(audioFile)
                
                textClips = self.generate_text_clips(subtitle_data, 'bottom', 50)
                all_created_clips.extend(textClips)
                
                videoUrls = self.video_downloader.get_video_urls(part["keyword"], "landscape", audioClip.duration)
                
                videoClips = []
                video_filenames = []
                
                for a, url in enumerate(videoUrls):
                    fileName = self.video_downloader.download_video(url, f"pexelsClip-{i}-{a}")
                    video_filenames.append(fileName)
                    try:
                        long_format = self.config.config["video"]["long_format"]
                        video_clip = VideoFileClip(os.path.join(self.config.temp_dir, fileName), target_resolution=(long_format["width"], long_format["height"]))
                        # Ensure video clip is long enough or loop it if needed
                        if video_clip.duration < audioClip.duration / len(videoUrls):
                            video_clip = video_clip.loop(duration=audioClip.duration / len(videoUrls))
                        else:
                            video_clip = video_clip.with_duration(audioClip.duration / len(videoUrls))
                        videoClips.append(video_clip)
                        all_created_clips.append(video_clip)
                    except Exception as e:
                        print(f"Error loading video clip {fileName}: {e}")
                        continue
                    
                # Track all downloaded video files
                temp_files.extend(video_filenames)
                
                if not videoClips:
                    # Fallback if no videos were successfully loaded
                    print(f"No valid video clips for part {i}, using a background video")
                    background = VideoFileClip(self.file_utils.get_random_file()).with_duration(audioClip.duration)
                    all_created_clips.append(background)
                    videoClips = [background]
                
                # Create and save a segment for this part
                try:
                    concatenated_video = concatenate_videoclips(videoClips, method="compose")
                    # Ensure the concatenated video is exactly the audio duration
                    concatenated_video = concatenated_video.with_duration(audioClip.duration)
                    long_format = self.config.config["video"]["long_format"]
                    composite_clip = CompositeVideoClip([concatenated_video.resized(height=long_format["height"])] + textClips)
                    composite_clip = composite_clip.with_duration(audioClip.duration).with_audio(audioClip)
                    all_created_clips.append(composite_clip)
                    
                    # Save this segment to a temporary file
                    segment_filename = f"long_segment_{i}.mp4"
                    segment_path = os.path.join(self.config.temp_dir, segment_filename)
                    composite_clip.write_videofile(
                        filename=segment_path,
                        threads=4,
                        preset="ultrafast",
                        temp_audiofile_path=self.config.temp_dir
                    )
                    segment_files.append(segment_filename)
                except Exception as e:
                    print(f"Error creating composite clip for part {i}: {e}")
                    continue
                finally:
                    # Close all clips in this batch to release memory
                    for clip in all_created_clips:
                        try:
                            clip.close()
                        except Exception as e:
                            print(f"Error closing clip: {e}")
            
            # Combine all segments
            if segment_files:
                try:
                    # Load segments as clips
                    segment_clips = []
                    for segment in segment_files:
                        segment_path = os.path.join(self.config.temp_dir, segment)
                        clip = VideoFileClip(segment_path)
                        segment_clips.append(clip)
                    
                    finalVideo = concatenate_videoclips(segment_clips, method="compose")
                    output_file = os.path.join(self.config.output_dir, "longVideo.mp4")
                    finalVideo.write_videofile(
                        filename=output_file,
                        threads=4,
                        preset="ultrafast",
                        temp_audiofile_path=self.config.temp_dir                    
                    )
                    
                    # Close the segment clips
                    for clip in segment_clips:
                        clip.close()
                        
                    return output_file
                except Exception as e:
                    print(f"Error rendering final long video: {e}")
        finally:
            # Delete temporary files
            self.file_utils.delete_temp_files(temp_files)
            self.file_utils.delete_temp_files(segment_files)


class YouTubeUploader:
    def __init__(self, config_manager):
        self.config = config_manager
    
    def upload_to_youtube(self, video_file, title, description):
        SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
        creds = None

        if os.path.exists("token.pickle"):
            with open("token.pickle", "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
                creds = flow.run_local_server(port=0)

            with open("token.pickle", "wb") as token:
                pickle.dump(creds, token)

        youtube = build("youtube", "v3", credentials=creds, developerKey=self.config.google_api_key)

        # Append the default description to the generated description
        full_description = description
        if "default_description" in self.config.config["youtube"]:
            full_description += self.config.config["youtube"]["default_description"]

        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": full_description,
                    "tags": self.config.config["youtube"]["default_tags"],
                    "channelId": self.config.config["youtube"]["channel_id"]
                },
                "status": {
                    "privacyStatus": self.config.config["youtube"]["default_privacy"]
                }
            },
            media_body=MediaFileUpload(video_file)
        )
        response = request.execute()
        print(f"Video uploaded to YouTube with ID: {response['id']}")


class ShortsGenerator:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.content_tracker = ChosenContentTracker()
        self.text_generator = TextGenerator(self.config_manager, self.content_tracker)
        self.video_processor = VideoProcessor(self.config_manager)
        self.youtube_uploader = YouTubeUploader(self.config_manager)
        self.file_utils = FileUtils(self.config_manager)
    
    async def generate_story(self):
        script = self.text_generator.generate_text(self.text_generator.get_story_prompt())
        script_data = self.file_utils.decode_json(script)
        if script_data and "title" in script_data:
            await self.video_processor.generate_story_video(script)
            self.content_tracker.save_new_content('story', script_data["title"])
            
            output_file = os.path.join(self.config_manager.output_dir, "story.mp4")
            if os.path.exists(output_file):
                self.youtube_uploader.upload_to_youtube(
                    output_file, 
                    script_data["title"], 
                    script_data.get("description", "Short story video")
                )
    
    async def generate_short_video(self):
        script = self.text_generator.generate_text(self.text_generator.get_short_video_prompt())
        output_file, script_data = await self.video_processor.generate_short_video(script)
        if output_file and script_data and "fact" in script_data:
            self.youtube_uploader.upload_to_youtube(output_file, script_data["fact"], script_data["description"])
            self.content_tracker.save_new_content('fact', script_data["fact"])
    
    async def generate_long_video(self):
        script = self.text_generator.generate_text(self.text_generator.get_long_video_prompt(), max_tokens=4096)
        script_data = self.file_utils.decode_json(script)
        if script_data and "topic" in script_data:
            await self.video_processor.generate_long_video(script)
            self.content_tracker.save_new_content('topic', script_data["topic"])
            
            output_file = os.path.join(self.config_manager.output_dir, "longVideo.mp4")
            if os.path.exists(output_file):
                self.youtube_uploader.upload_to_youtube(
                    output_file, 
                    script_data["topic"], 
                    script_data.get("description", "Educational video about " + script_data["topic"])
                )
    
    async def run(self):
        # if self.content_tracker.use_story_prompt:
        #     await self.generate_story()
        # else:
        #     await self.generate_short_video()
            
        await self.generate_long_video()


def main():
    generator = ShortsGenerator()
    asyncio.run(generator.run())

if __name__ == "__main__":
    main()