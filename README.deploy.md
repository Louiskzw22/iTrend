# iTrend Deployment Guide

This guide provides detailed instructions for deploying iTrend in various environments.

## Prerequisites

- Python 3.10+
- FFmpeg (for audio processing)
- OpenAI API key (optional, for transcription)
- Git

## Local Development Setup

### 1. Clone and Install

```bash
git clone https://github.com/Louiskzw22/iTrend.git
cd iTrend
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
python -c "from src.db import TrendDB; TrendDB('data/trends.db')"
```

### 3. Configure Podcasts

Edit `config.yaml` to add or modify podcast sources:

```yaml
podcasts:
  - name: "Your Podcast Name"
    itunes_id: 1234567890
    tags: "tag1, tag2, tag3"
    enabled: true
```

### 4. Run Ingestion

**Without transcription:**
```bash
python src/ingest/podcast_ingest.py
```

**With transcription:**
```bash
export OPENAI_API_KEY="sk-your-api-key-here"
python src/ingest/podcast_ingest.py
```

### 5. Launch UI

```bash
streamlit run src/ui/streamlit_app.py
```

Visit http://localhost:8501

## Streamlit Cloud Deployment

### Steps

1. **Fork the Repository**
   - Fork https://github.com/Louiskzw22/iTrend to your GitHub account

2. **Sign Up for Streamlit Cloud**
   - Go to https://streamlit.io/cloud
   - Sign in with GitHub

3. **Connect Your Repository**
   - Click "New app"
   - Select your forked repository
   - Set main file path: `src/ui/streamlit_app.py`
   - Click "Advanced settings"

4. **Configure Secrets**
   - In Advanced settings, add secrets:
   ```toml
   OPENAI_API_KEY = "sk-your-key-here"
   ```

5. **Pre-populate Database**
   - **Important**: Streamlit Cloud apps have ephemeral storage
   - Option A: Include a pre-populated database in your repo (be careful about size)
   - Option B: Run ingestion locally, commit the database, then deploy
   - Option C: Use an external database service

6. **Deploy**
   - Click "Deploy"
   - Your app will be live at: `https://your-app.streamlit.app`

### Important Notes

- Streamlit Cloud has resource limits (CPU, memory, storage)
- The database and audio files will be lost on app restarts unless persisted
- Consider using volume mounts or external storage for production

## Docker Deployment

### Option 1: Build Locally

```bash
# Build image
docker build -t itrend:latest .

# Run container
docker run -d \
  -p 8501:8501 \
  -e OPENAI_API_KEY="your-key" \
  -v $(pwd)/data:/app/data \
  --name itrend \
  itrend:latest
```

### Option 2: Use Pre-built Image from GHCR

```bash
# Pull image
docker pull ghcr.io/louiskzw22/itrend:latest

# Run container
docker run -d \
  -p 8501:8501 \
  -e OPENAI_API_KEY="your-key" \
  -v $(pwd)/data:/app/data \
  --name itrend \
  ghcr.io/louiskzw22/itrend:latest
```

### Option 3: Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  itrend:
    image: ghcr.io/louiskzw22/itrend:latest
    container_name: itrend
    ports:
      - "8501:8501"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DB_PATH=/app/data/trends.db
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

Create `.env` file:
```
OPENAI_API_KEY=sk-your-key-here
```

Run:
```bash
docker-compose up -d
```

### Docker Volume Management

The Docker setup uses a volume mount for the `data/` directory. This ensures:
- Database persists across container restarts
- Audio files are preserved
- Ingestion can be run inside or outside the container

To run ingestion in Docker:
```bash
docker exec -it itrend python src/ingest/podcast_ingest.py
```

## Production Considerations

### Security

1. **Never commit secrets**
   - Use environment variables
   - Use secret management services
   - The `.gitignore` file protects you, but always double-check

2. **API Key Rotation**
   - Rotate OpenAI API keys regularly
   - Monitor API usage

3. **Network Security**
   - Use HTTPS in production
   - Consider adding authentication to Streamlit app
   - Use firewall rules to restrict access

### Performance

1. **Database Optimization**
   - SQLite works well for small to medium datasets
   - Consider PostgreSQL for large-scale deployments
   - Regular VACUUM operations for SQLite

2. **Caching**
   - Streamlit's `@st.cache_resource` is used for DB connections
   - Consider caching search results for frequently accessed queries

3. **Resource Limits**
   - Monitor memory usage during transcription
   - Large audio files can consume significant memory
   - Consider batch processing for many podcasts

### Monitoring

1. **Logs**
   - Docker logs: `docker logs -f itrend`
   - Streamlit logs show in the app console
   - Ingestion script outputs to stdout

2. **Health Checks**
   - Docker includes healthcheck endpoint
   - Monitor http://localhost:8501/_stcore/health

### Backup

1. **Database Backups**
   ```bash
   # Backup
   cp data/trends.db backups/trends-$(date +%Y%m%d).db
   
   # Restore
   cp backups/trends-20251111.db data/trends.db
   ```

2. **Audio File Backups**
   - Audio files can be large
   - Consider backing up only the database if audio can be re-downloaded

## Troubleshooting

### Common Issues

**Database locked errors**
- Ensure only one process writes to the database
- Check file permissions on data directory

**FFmpeg not found**
- Install: `apt-get install ffmpeg` (Debian/Ubuntu)
- Install: `brew install ffmpeg` (macOS)

**Transcription fails**
- Verify OpenAI API key is valid
- Check API usage limits and quotas
- Ensure audio file format is supported

**Streamlit app won't start**
- Check port 8501 is not already in use
- Verify database file exists and is readable
- Check Python and package versions

**Docker container exits immediately**
- Check logs: `docker logs itrend`
- Verify volume mounts are correct
- Ensure database directory has correct permissions

## GitHub Actions CI/CD

The repository includes a GitHub Actions workflow that automatically builds and publishes Docker images to GitHub Container Registry (GHCR) on pushes to `main`.

### Setup

1. **GitHub Secrets** (optional, for Docker Hub)
   - Go to repository Settings → Secrets and variables → Actions
   - Add secrets:
     - `DOCKERHUB_USERNAME`: Your Docker Hub username
     - `DOCKERHUB_TOKEN`: Docker Hub access token

2. **GHCR Access** (automatic)
   - GHCR publishing is enabled by default
   - Uses `GITHUB_TOKEN` automatically

### Tags

Images are tagged with:
- `latest` - Latest build from main branch
- `main-<sha>` - Specific commit SHA
- `v*` - Semantic version tags (if you create releases)

### Usage

Pull the latest image:
```bash
docker pull ghcr.io/louiskzw22/itrend:latest
```

Pull a specific version:
```bash
docker pull ghcr.io/louiskzw22/itrend:main-abc1234
```

## Support

For issues, questions, or contributions:
- Open an issue: https://github.com/Louiskzw22/iTrend/issues
- Submit a pull request: https://github.com/Louiskzw22/iTrend/pulls

## License

MIT License - See LICENSE file for details
