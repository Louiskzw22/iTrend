"""Podcast ingestion script - downloads podcast episodes and optionally transcribes them."""
import os
import sys
import json
import subprocess
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
import requests
import feedparser
import yaml

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.db import TrendDB


def get_podcast_feed_url(itunes_id: int) -> Optional[str]:
    """Resolve iTunes feed URL from iTunes ID.
    
    Args:
        itunes_id: iTunes podcast ID
        
    Returns:
        Feed URL or None if not found
    """
    lookup_url = f"https://itunes.apple.com/lookup?id={itunes_id}"
    try:
        response = requests.get(lookup_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get('resultCount', 0) > 0:
            return data['results'][0].get('feedUrl')
    except Exception as e:
        print(f"Error resolving iTunes feed: {e}")
    
    return None


def download_file(url: str, dest_path: str) -> bool:
    """Download a file from URL to destination path.
    
    Args:
        url: Source URL
        dest_path: Destination file path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False


def convert_to_wav(audio_path: str, wav_path: str) -> bool:
    """Convert audio file to WAV format using ffmpeg.
    
    Args:
        audio_path: Input audio file path
        wav_path: Output WAV file path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Use ffmpeg to convert to WAV (mono, 16kHz for better transcription)
        cmd = [
            'ffmpeg', '-i', audio_path,
            '-ar', '16000',  # 16kHz sample rate
            '-ac', '1',      # mono
            '-y',            # overwrite output
            wav_path
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300
        )
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error converting audio to WAV: {e}")
        return False


def transcribe_audio(audio_path: str, api_key: str) -> Optional[str]:
    """Transcribe audio file using OpenAI Whisper.
    
    Args:
        audio_path: Path to audio file (WAV format)
        api_key: OpenAI API key
        
    Returns:
        Transcript text or None if failed
    """
    try:
        import openai
        openai.api_key = api_key
        
        with open(audio_path, 'rb') as audio_file:
            transcript = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file
            )
        
        return transcript.get('text', '')
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return None


def generate_filename(url: str, extension: str = '') -> str:
    """Generate a safe filename from URL using hash.
    
    Args:
        url: Source URL
        extension: File extension to append
        
    Returns:
        Safe filename
    """
    url_hash = hashlib.md5(url.encode()).hexdigest()
    if extension and not extension.startswith('.'):
        extension = '.' + extension
    return f"{url_hash}{extension}"


def ingest_podcast(podcast_config: Dict[str, Any], db: TrendDB, 
                  audio_dir: str, openai_api_key: Optional[str] = None):
    """Ingest podcast episodes from iTunes feed.
    
    Args:
        podcast_config: Podcast configuration dict
        db: Database instance
        audio_dir: Directory to store audio files
        openai_api_key: OpenAI API key for transcription (optional)
    """
    name = podcast_config.get('name', 'Unknown Podcast')
    itunes_id = podcast_config.get('itunes_id')
    tags = podcast_config.get('tags', '')
    
    print(f"\n{'='*60}")
    print(f"Ingesting podcast: {name}")
    print(f"{'='*60}")
    
    if not itunes_id:
        print(f"Error: No iTunes ID for podcast '{name}'")
        return
    
    # Resolve feed URL
    print(f"Resolving feed URL for iTunes ID: {itunes_id}")
    feed_url = get_podcast_feed_url(itunes_id)
    
    if not feed_url:
        print(f"Error: Could not resolve feed URL for podcast '{name}'")
        return
    
    print(f"Feed URL: {feed_url}")
    
    # Parse feed
    print("Parsing podcast feed...")
    feed = feedparser.parse(feed_url)
    
    if not feed.entries:
        print("No episodes found in feed")
        return
    
    print(f"Found {len(feed.entries)} episodes")
    
    # Process each episode
    for idx, entry in enumerate(feed.entries, 1):
        print(f"\n[{idx}/{len(feed.entries)}] Processing: {entry.get('title', 'Untitled')}")
        
        title = entry.get('title', 'Untitled Episode')
        url = entry.get('link', entry.get('id', ''))
        description = entry.get('summary', '')
        published = entry.get('published', '')
        
        if not url:
            print("  Skipping: No URL found")
            continue
        
        # Check if episode already exists with transcript
        existing = db.search_articles(url)
        has_transcript = False
        if existing:
            for article in existing:
                if article.get('url') == url and article.get('transcript'):
                    has_transcript = True
                    break
        
        if has_transcript:
            print("  Already exists with transcript, skipping")
            continue
        
        # Find audio enclosure
        audio_url = None
        for enclosure in entry.get('enclosures', []):
            if enclosure.get('type', '').startswith('audio/'):
                audio_url = enclosure.get('href')
                break
        
        if not audio_url:
            print("  No audio enclosure found, storing metadata only")
            db.upsert_article(
                title=title,
                url=url,
                description=description,
                published_date=published,
                source=name,
                tags=tags
            )
            continue
        
        # Download audio
        audio_filename = generate_filename(audio_url, '.mp3')
        audio_path = os.path.join(audio_dir, audio_filename)
        
        print(f"  Downloading audio...")
        if not download_file(audio_url, audio_path):
            print("  Failed to download audio, storing metadata only")
            db.upsert_article(
                title=title,
                url=url,
                description=description,
                published_date=published,
                source=name,
                tags=tags
            )
            continue
        
        print(f"  Audio saved: {audio_path}")
        
        # Transcribe if API key provided
        transcript = None
        if openai_api_key:
            print("  Converting to WAV...")
            wav_path = audio_path.replace('.mp3', '.wav')
            
            if convert_to_wav(audio_path, wav_path):
                print("  Transcribing with Whisper...")
                transcript = transcribe_audio(wav_path, openai_api_key)
                
                if transcript:
                    print(f"  Transcript length: {len(transcript)} characters")
                else:
                    print("  Transcription failed")
                
                # Clean up WAV file
                try:
                    os.remove(wav_path)
                except:
                    pass
            else:
                print("  Audio conversion failed")
        else:
            print("  Skipping transcription (no OPENAI_API_KEY)")
        
        # Store in database
        metadata = json.dumps({
            'audio_file': audio_path,
            'audio_url': audio_url
        })
        
        db.upsert_article(
            title=title,
            url=url,
            description=description,
            published_date=published,
            source=name,
            tags=tags,
            transcript=transcript,
            metadata=metadata
        )
        
        print("  ✓ Stored in database")


def main():
    """Main ingestion script."""
    # Get OpenAI API key from environment
    openai_api_key = os.environ.get('OPENAI_API_KEY')
    
    if openai_api_key:
        print("OpenAI API key found - transcription enabled")
    else:
        print("No OpenAI API key - transcription disabled")
    
    # Load configuration
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.yaml')
    
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize database
    db_path = os.environ.get('DB_PATH', 'data/trends.db')
    db = TrendDB(db_path)
    
    # Create audio directory
    audio_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'audio')
    os.makedirs(audio_dir, exist_ok=True)
    
    # Process podcasts
    podcasts = config.get('podcasts', [])
    
    if not podcasts:
        print("No podcasts configured")
        sys.exit(0)
    
    for podcast in podcasts:
        if podcast.get('enabled', True):
            try:
                ingest_podcast(podcast, db, audio_dir, openai_api_key)
            except Exception as e:
                print(f"Error processing podcast {podcast.get('name', 'Unknown')}: {e}")
                import traceback
                traceback.print_exc()
    
    db.close()
    print("\n" + "="*60)
    print("Ingestion complete!")
    print("="*60)


if __name__ == '__main__':
    main()
