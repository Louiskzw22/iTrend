# iTrend
Emerging Trends Tracker - Track and analyze podcasts and articles with AI-powered transcription

## Features

- 📊 **Podcast Ingestion**: Automatically fetch and process podcast episodes from iTunes
- 🎙️ **AI Transcription**: Transcribe audio content using OpenAI Whisper
- 🔍 **Full-Text Search**: Search across titles, descriptions, and transcripts
- 🏷️ **Tag Management**: Organize content with custom tags
- 🖥️ **Web UI**: Browse and explore content through a Streamlit interface
- 🐳 **Docker Support**: Easy deployment with Docker and GHCR

## Quick Start

### Prerequisites

- Python 3.10+
- FFmpeg (for audio processing)
- OpenAI API key (optional, for transcription)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Louiskzw22/iTrend.git
cd iTrend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the database:
```bash
python -c "from src.db import TrendDB; TrendDB('data/trends.db')"
```

### Configuration

Edit `config.yaml` to add podcasts:

```yaml
podcasts:
  - name: "Cleantech Forward"
    itunes_id: 1604425407
    tags: "cleantech, sustainability, climate, energy"
    enabled: true
```

### Running Ingestion

**Without transcription** (metadata and audio only):
```bash
python src/ingest/podcast_ingest.py
```

**With transcription** (requires OpenAI API key):
```bash
export OPENAI_API_KEY="sk-your-key-here"
python src/ingest/podcast_ingest.py
```

⚠️ **Important**: Never commit your API keys to version control!

### Running the UI

Start the Streamlit app:
```bash
streamlit run src/ui/streamlit_app.py
```

Access at: http://localhost:8501

## Deployment

### Streamlit Cloud

1. Fork this repository
2. Sign up at [Streamlit Cloud](https://streamlit.io/cloud)
3. Connect your GitHub repository
4. Set secrets in Streamlit Cloud dashboard:
   - `OPENAI_API_KEY`: Your OpenAI API key (if using transcription)
5. Deploy!

**Note**: You'll need to pre-populate the database or run ingestion separately, as Streamlit Cloud apps are typically read-only for data.

### Docker

#### Build locally:
```bash
docker build -t itrend .
```

#### Run locally:
```bash
docker run -p 8501:8501 \
  -e OPENAI_API_KEY="your-key" \
  -v $(pwd)/data:/app/data \
  itrend
```

#### Pull from GitHub Container Registry:
```bash
docker pull ghcr.io/louiskzw22/itrend:latest
docker run -p 8501:8501 \
  -e OPENAI_API_KEY="your-key" \
  -v $(pwd)/data:/app/data \
  ghcr.io/louiskzw22/itrend:latest
```

### Docker Compose (recommended)

Create `docker-compose.yml`:
```yaml
version: '3.8'
services:
  itrend:
    image: ghcr.io/louiskzw22/itrend:latest
    ports:
      - "8501:8501"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

Run with:
```bash
docker-compose up -d
```

## Environment Variables

- `OPENAI_API_KEY`: OpenAI API key for transcription (optional)
- `DB_PATH`: SQLite database path (default: `data/trends.db`)

## Security Notes

⚠️ **NEVER commit secrets or API keys to version control!**

- Use environment variables for API keys
- Use `.streamlit/secrets.toml` for Streamlit (not committed)
- The `.gitignore` file excludes sensitive files
- Copy `.streamlit/secrets.toml.template` to create your secrets file

## Project Structure

```
iTrend/
├── src/
│   ├── db.py                    # Database module with FTS support
│   ├── ingest/
│   │   └── podcast_ingest.py    # Podcast ingestion script
│   └── ui/
│       └── streamlit_app.py     # Streamlit web interface
├── .streamlit/
│   ├── config.toml              # Streamlit configuration
│   └── secrets.toml.template    # Template for secrets
├── .github/
│   └── workflows/
│       └── docker-publish.yml   # Docker build/publish workflow
├── data/                        # Data directory (not committed)
│   ├── trends.db               # SQLite database
│   └── audio/                  # Downloaded audio files
├── config.yaml                  # Podcast/feed configuration
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker image definition
└── README.md                    # This file
```

## Development

### Database Schema

The SQLite database includes:
- `articles` table: Stores article metadata, transcripts, and tags
- `articles_fts` table: Full-text search index (FTS5)
- Automatic triggers to keep FTS index synchronized

### Adding New Features

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Troubleshooting

### FFmpeg not found
Install FFmpeg:
- Ubuntu/Debian: `sudo apt-get install ffmpeg`
- macOS: `brew install ffmpeg`
- Windows: Download from [ffmpeg.org](https://ffmpeg.org)

### Database locked errors
Ensure only one process is writing to the database at a time. The Streamlit app uses `check_same_thread=False` for read operations.

### Transcription errors
- Verify your OpenAI API key is valid
- Check your API usage limits
- Ensure audio files are not corrupted

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
