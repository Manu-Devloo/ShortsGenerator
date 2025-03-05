import os
import subprocess
import sys
import json
import shutil
from pathlib import Path

def print_header(title):
    """Print a formatted header for better readability"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def install_dependencies():
    """Install required Python packages"""
    print_header("Installing Dependencies")
    
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("Error: requirements.txt file not found.")
        return False
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def setup_env_file():
    """Create a .env file template for environment variables"""
    print_header("Setting Up Environment Variables")
    
    env_file = Path(".env")
    if env_file.exists():
        overwrite = input(".env file already exists. Overwrite? (y/n): ").lower()
        if overwrite != 'y':
            print("Keeping existing .env file.")
            return
    
    env_content = """# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_ENDPOINT=https://models.inference.ai.azure.com

# Pexels API for stock videos
PEXELS_API_KEY=your_pexels_api_key_here

# Google/YouTube API
GOOGLE_API_KEY=your_google_api_key_here
"""
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print("✅ Created .env template file.")
    print("\nIMPORTANT: Edit the .env file with your actual API keys.")

def create_directories():
    """Create required directories"""
    print_header("Setting Up Directory Structure")
    
    # Create directories
    directories = [
        "background",
        "temp",
        "output",
        "chosen",
        "fonts"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Created or verified directory: {directory}")
    
    # Create placeholder files in the chosen directory
    chosen_files = ["chosen_facts.json", "chosen_stories.json", "chosen_topics.json"]
    for file in chosen_files:
        file_path = Path("chosen") / file
        if not file_path.exists():
            with open(file_path, 'w') as f:
                f.write('[]')
            print(f"✅ Created empty tracking file: {file_path}")

def download_test_font():
    """Download a test font file if needed"""
    print_header("Setting Up Font")
    
    font_path = Path("fonts/Lobster-Regular.ttf")
    if font_path.exists():
        print("✅ Font file already exists.")
        return
    
    try:
        import requests
        print("Downloading test font (Lobster-Regular)...")
        font_url = "https://github.com/google/fonts/raw/refs/heads/main/ofl/lobster/Lobster-Regular.ttf"
        response = requests.get(font_url)
        
        if response.status_code == 200:
            with open(font_path, 'wb') as f:
                f.write(response.content)
            print("✅ Downloaded font successfully.")
        else:
            print(f"❌ Failed to download font: {response.status_code}")
            print("You'll need to manually add a font file to the fonts directory.")
    except Exception as e:
        print(f"❌ Error downloading font: {e}")
        print("You'll need to manually add a font file to the fonts directory.")

def create_config_if_not_exists():
    """Create default configuration file if it doesn't exist"""
    print_header("Setting Up Configuration")
    
    config_path = Path("config.json")
    if config_path.exists():
        print("✅ Configuration file already exists.")
        return
    
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
    
    with open(config_path, 'w') as f:
        json.dump(default_config, f, indent=2)
    
    print("✅ Created default configuration file.")

def provide_setup_instructions():
    """Provide user with final setup instructions"""
    print_header("Setup Instructions")
    
    print("""
To complete your setup:

1. Edit the .env file with your API keys:
   - OPENAI_API_KEY: Get from OpenAI (https://platform.openai.com/api-keys)
   - PEXELS_API_KEY: Get from Pexels (https://www.pexels.com/api/)
   - GOOGLE_API_KEY: Get from Google Cloud Console

2. For YouTube uploads, create OAuth credentials:
   - Go to Google Cloud Console
   - Create OAuth 2.0 Client ID
   - Download JSON and save as 'client_secrets.json' in this directory

3. Add background videos to the 'background' directory
   - These are used as fallback videos when Pexels videos fail to download

4. Review and update config.json if needed

5. Run the generator with: python main.py
""")

def main():
    print_header("ShortsGenerator Setup")
    
    print("This script will set up your environment for ShortsGenerator.")
    print("It will install required dependencies and create configuration files.")
    
    proceed = input("Do you want to proceed? (y/n): ").lower()
    if proceed != 'y':
        print("Setup cancelled.")
        return
    
    # Run setup steps
    if install_dependencies():
        create_directories()
        setup_env_file()
        download_test_font()
        create_config_if_not_exists()
        provide_setup_instructions()
        
        print_header("Setup Complete")
        print("Your ShortsGenerator environment is now set up!")
    else:
        print("\n❌ Setup incomplete due to errors. Please fix the issues and try again.")

if __name__ == "__main__":
    main()
