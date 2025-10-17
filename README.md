# Video Downloader

Standalone tool for downloading videos from conferences and platforms that require authentication via browser cookies.

## Features

- Download videos from conference websites (JPoint, Heisenbug, HolyJS, Mobius)
- Use Chrome browser cookies for authentication
- Automatic Chrome profile detection
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

3. Install browsers for Playwright (optional):
```bash
playwright install chromium
```

## Configuration

Edit `config.toml`:

```toml
# Chrome profile (e.g., "Default", "Profile 1")
browser_profile = "Default"

# Root directory for downloads
output_root = "downloads"

# File with links (one URL per line)
links_file = "links.txt"

# Optional: path to cookies.txt (Netscape format)
# cookies_file = "cookies.txt"
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
python main.py https://example.com/video/ --browser-profile "Default"

# Via Python module
python -m src.cli https://example.com/video/
```

### CLI parameters

```bash
python main.py [URLs...] --browser-profile "Default" --output-root downloads/
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

The project uses CI/CD with automatic test and linting checks.

### Project structure

```
video_downloader/
├── main.py             # Main entry point
├── config.toml         # Configuration
├── links.txt          # List of URLs to download
├── requirements.txt   # Dependencies
├── src/               # Source code
│   ├── config.py      # Configuration management
│   ├── browser.py     # Browser profiles
│   ├── downloader.py  # Main download logic
│   ├── file_manager.py # File management
│   ├── playwright_capture.py # Browser download
│   ├── utils.py       # Utility functions
│   └── cli.py         # CLI interface
├── tests/             # Tests
│   ├── test_config.py
│   ├── test_file_manager.py
│   └── test_utils.py
├── .github/           # GitHub workflows
├── debug/             # Debug files (ignored by git)
└── README.md         # Documentation
```

## Algorithm

1. **Trial download**: Attempt via yt-dlp with browser cookies
2. **Manifest capture**: If not supported, use Playwright to capture HLS/DASH manifest
3. **DRM detection**: Heuristic detection of content protection
4. **Official download**: When DRM is detected - switch to official download stream via browser
5. **Processing**: FFmpeg for final processing and optimization

## Troubleshooting

### Cookie issues
- Make sure you're logged in to Chrome on the target site
- Check the Chrome profile correctness in `config.toml`
- Try exporting cookies via "Get cookies.txt" extension

### DRM issues
- The tool automatically switches to official download
- Make sure you have download access on the site
- Some videos may be unavailable for download

### Playwright issues
- Install browsers: `playwright install chromium`
- Check Chrome profile access permissions

## License

MIT License
