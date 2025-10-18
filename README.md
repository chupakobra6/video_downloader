# Video Downloader

Standalone tool for downloading videos from conferences and platforms that require authentication via browser cookies.

## Features

- Download videos from conference websites (JPoint, Heisenbug, HolyJS, Mobius)
- Use Chrome browser cookies for authentication
- DRM bypass through official download links
- HLS/DASH stream support
- Resume interrupted downloads

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd video_downloader
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```


## Configuration

Edit `config.toml`:

```toml
# Root directory for downloads
output_root = "downloads"

# File with links (one URL per line)
links_file = "links.txt"
```

## Usage

### Preparing links

Add URLs to `links.txt` file (one per line):
```
https://jpoint.ru/talks/example-talk-id/
https://heisenbug.ru/archive/2025%20Spring/talks/example-id/
```

### Running

```bash
# Main method
python main.py

# With command line arguments
python main.py https://example.com/video/

# Via Python module
python -m src.cli https://example.com/video/
```

### CLI parameters

```bash
python main.py [URLs...] --output-root downloads/
```

## Supported platforms

- **JPoint** (jpoint.ru)
- **Heisenbug** (heisenbug.ru)
- **HolyJS** (holyjs.ru)
- **Mobius** (mobiusconf.com)
- Other sites with HLS/DASH streams

## Requirements

- Python 3.8+
- Chrome browser with installed cookies
- FFmpeg (for video processing)

## Development

The project uses CI/CD with automatic linting checks.

### Project structure

```
video_downloader/
├── main.py             # Main entry point
├── config.toml         # Configuration
├── links.txt          # List of URLs to download
├── requirements.txt   # Dependencies
├── src/               # Source code
│   ├── config.py      # Configuration management
│   ├── downloader.py  # Main download logic
│   ├── file_manager.py # File management
│   ├── utils.py       # Utility functions
│   └── cli.py         # CLI interface
├── .github/           # GitHub workflows
├── debug/             # Debug files (ignored by git)
└── README.md         # Documentation
```

## Algorithm

1. **Download**: Attempt via yt-dlp with browser cookies
2. **Processing**: FFmpeg for final processing and optimization

## Troubleshooting

### Cookie issues
- Make sure you're logged in to Chrome on the target site
- The tool uses Chrome cookies for authentication

### DRM issues
- Some videos may be unavailable for download
- Make sure you have download access on the site

## License

MIT License
