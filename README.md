# Shorts Generator

An automated tool for generating and uploading short-form and long-form videos to YouTube using AI-generated content, text-to-speech, and stock videos.

## Features

- Generates engaging short stories with twist endings
- Creates informative fact-based short videos
- Produces longer educational content videos
- Automatically uploads videos to YouTube
- Alternates between story and fact videos
- Tracks already used content to avoid repetition

## Requirements

- Python 3.8 or higher
- OpenAI API key
- Azure or Edge TTS access
- Pexels API key (for stock videos)
- Google API key (for YouTube uploads)
- FFmpeg installed and available in your system PATH

## Setup

1. Clone this repository:
   ```
   git clone https://github.com/Manu-Devloo/ShortsGenerator.git
   cd ShortsGenerator
   ```

2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with the following variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_ENDPOINT=your_openai_endpoint  # Optional, default in config.json
   PEXELS_API_KEY=your_pexels_api_key
   GOOGLE_API_KEY=your_google_api_key
   ```

4. Set up Google OAuth credentials:
   - Create a project in the [Google Developer Console](https://console.developers.google.com/)
   - Enable the YouTube Data API v3
   - Create OAuth 2.0 credentials
   - Download the credentials as `client_secrets.json` and place in the project root

5. Create required directories:
   - `/background` - Place background videos here (used as fallbacks)
   - `/fonts` - Store custom fonts here (default: Lobster-Regular.ttf)

6. Configure `config.json` with your preferred settings

7. Run `python main.py` to generate and upload videos

## Configuration

The program uses a `config.json` file with the following sections:

### API Configuration
- OpenAI API settings for content generation
- Text-to-speech voice selection

### Video Formatting
- Dimensions for short-form (vertical) and long-form (horizontal) videos
- Font settings for on-screen text

### File Paths
- Directories for background videos, temporary files, and output videos

### YouTube Settings
- Default tags for uploaded videos
- Privacy status setting
- Channel ID
- Default description - appended to all AI-generated descriptions

## Default Description Feature

The program automatically appends a default signature description to all AI-generated descriptions when uploading videos to YouTube. This helps maintain consistency in your video descriptions and can include:

- Call-to-action messages (subscribe, like, etc.)
- Channel branding
- Hashtags for better discoverability
- Contact information
- Copyright notices

To customize the default description, modify the `default_description` field in the `youtube` section of `config.json`:

```json
"youtube": {
  "default_description": "\n\n👋 Thanks for watching! Don't forget to like, subscribe, and hit the notification bell for more content like this!\n\n#shorts #viral #trending"
}
```

