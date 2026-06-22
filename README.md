# Tech Intelligence Agent

Automated daily intelligence gathering and reporting system for AI and technology trends. Collects, analyzes, and delivers curated insights from Twitter, GitHub, Product Hunt, Hacker News, and RSS feeds — powered by Google Gemini for AI-driven analysis.

## Features

- **Multi-source Collection** — Aggregates posts from Twitter/X, GitHub trending, Product Hunt, Hacker News, and RSS blogs
- **AI-Powered Analysis** — Uses Google Gemini to analyze content, generate summaries, and produce executive reports
- **Engagement Scoring** — Weighted scoring system to surface the most relevant content
- **Trend Detection** — Identifies emerging topics and patterns across sources
- **Deduplication** — Removes duplicate or overlapping content automatically
- **Report Generation** — Produces daily, weekly, and monthly reports in HTML, Markdown, and PDF
- **Multi-channel Delivery** — Sends reports via Telegram and Email
- **Dashboard API** — FastAPI-based dashboard for viewing collected data and reports
- **Scheduler** — Configurable cron-based scheduling for automated runs
- **Export** — JSON, CSV, and PDF export capabilities

## Architecture

```
┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  ┌───────────┐
│  Twitter/X   │  │    GitHub    │  │ Product Hunt  │  │ Hacker News  │  │ RSS News  │
│  Collector   │  │  Collector   │  │  Collector    │  │  Collector   │  │ Collector │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘  └─────┬─────┘
       │                 │                 │                 │               │
       └─────────────────┴─────────────────┴─────────────────┴───────────────┘
                                      │
                              ┌───────▼────────┐
                              │  Deduplication  │
                              └───────┬─────────┘
                                      │
                              ┌───────▼─────────┐
                              │ Engagement Score │
                              └───────┬──────────┘
                                      │
                              ┌───────▼────────┐
                              │  AI Analysis    │
                              │  (Gemini)       │
                              └───────┬─────────┘
                                      │
                ┌─────────────────────┼─────────────────────┐
                │                     │                     │
        ┌───────▼───────┐   ┌────────▼────────┐   ┌───────▼────────┐
        │ Trend Detector │   │ Report Generator│   │  DB & Storage  │
        └───────┬───────┘   └────────┬────────┘   └───────┬────────┘
                │                    │                     │
                └────────────────────┼─────────────────────┘
                                     │
                ┌────────────────────┼────────────────────┐
                │                    │                    │
        ┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
        │   Telegram    │   │    Email      │   │   Dashboard   │
        │   Delivery    │   │   Delivery    │   │  API (FastAPI)│
        └───────────────┘   └───────────────┘   └───────────────┘
```

## Prerequisites

- Python 3.12+
- Google Gemini API key
- Telegram Bot Token (optional, for Telegram delivery)
- SMTP credentials (optional, for email delivery)
- Twitter/X API credentials (optional)
- Product Hunt API token (optional)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/tech-intel-agent.git
   cd tech-intel-agent
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your API keys and credentials.

## Configuration

All configuration is managed through `config.yaml`:

| Section | Description |
|---------|-------------|
| `schedule` | Cron schedule time and timezone |
| `twitter` | Twitter/X accounts to monitor |
| `github` | GitHub trending topics and languages |
| `producthunt` | Product Hunt topics to track |
| `hackernews` | Hacker News topics |
| `news` | RSS feed sources |
| `engagement` | Scoring weights and minimum thresholds |
| `filtering` | Content filtering rules |
| `ai_analysis` | Gemini model and settings |
| `reporting` | Report structure and limits |
| `delivery` | Telegram and email delivery settings |

Environment variables are loaded from `.env` and override `config.yaml` values for sensitive fields (API keys, tokens).

## Usage

### Run once (manual collection)
```bash
python main.py --run-once
```

### Run as scheduled daemon
```bash
python main.py --daemon
```

### Start dashboard API
```bash
python main.py --dashboard --port 8000
```

### CLI options
| Flag | Description |
|------|-------------|
| `-c, --config PATH` | Path to config.yaml |
| `-r, --run-once` | Run collection once and exit |
| `-d, --daemon` | Run as scheduled daemon |
| `--dashboard` | Start dashboard API |
| `--host HOST` | Dashboard host (default: 0.0.0.0) |
| `--port PORT` | Dashboard port (default: 8000) |

## Deployment

### Railway

The project includes `railway.toml` and `Procfile` for one-click deployment on Railway. Environment variables can be set in the Railway dashboard.

```bash
# Deploy via Railway CLI
railway up
```

### Docker

Build and run using Docker:

```bash
docker build -t tech-intel-agent .
docker run -d --env-file .env tech-intel-agent
```

## Project Structure

```
tech_intel_agent/
├── config/              # Configuration management
│   ├── settings.py
│   └── __init__.py
├── collectors/          # Data source collectors
│   ├── github.py
│   ├── hackernews.py
│   ├── news.py
│   ├── producthunt.py
│   └── twitter.py
├── analyzers/           # Data processing pipeline
│   ├── ai_analyzer.py
│   ├── dedup.py
│   ├── engagement.py
│   └── trends.py
├── database/            # SQLite storage
│   └── storage.py
├── reporting/           # Report generation
│   └── report_generator.py
├── delivery/            # Output delivery channels
│   ├── email.py
│   ├── export.py
│   └── telegram.py
├── dashboard/           # FastAPI dashboard
│   └── api.py
├── utils/               # Shared utilities
│   └── logger.py
├── data/                # SQLite database files
├── exports/             # Exported reports (JSON, CSV, PDF)
├── logs/                # Application logs
├── .env.example         # Environment variable template
├── config.yaml          # Main configuration file
├── main.py              # Application entry point
├── requirements.txt     # Python dependencies
├── start.sh             # Startup script (Railway)
├── Procfile             # Railway process definition
├── railway.toml         # Railway deployment config
└── runtime.txt          # Python version
```

## Tech Stack

- **Python 3.12** — Core runtime
- **Google Gemini API** — AI analysis and report summarization
- **SQLAlchemy** — Database ORM (SQLite)
- **APScheduler** — Task scheduling
- **FastAPI** — Dashboard API
- **Jinja2** — HTML report templates
- **WeasyPrint** — PDF generation
- **Pydantic** — Configuration validation
- **httpx / BeautifulSoup** — HTTP requests and RSS parsing

## License

MIT
