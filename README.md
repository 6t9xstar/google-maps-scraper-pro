# Google Maps Scraper Pro 🗺️

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/6t9xstar/google-maps-scraper-pro?style=social)

**🔥 Fast & Unlimited Google Maps Data Extraction** - Extract 100+ business leads per search with auto-scrolling, proxy rotation, and email discovery. Modern GUI + CLI. **100% Free & Open Source.**

## ✨ Features

- 🚀 **100+ Results Per Search** - Auto-scrolls to load ALL available businesses
- ⚡ **Blazing Fast** - Playwright-based with 7000+ proxy rotation
- 🎯 **Smart Extraction** - Company name, website, email, phone, address, category
- 🔒 **Anti-Detection** - Stealth mode, proxy rotation, human-like delays
- 💻 **Modern GUI** - Beautiful CustomTkinter interface with real-time progress
- 🖥️ **CLI Mode** - Command line interface for automation
- 📧 **Email Discovery** - Automatically extracts emails from business websites
- 📊 **CSV Export** - Professional UTF-8 CSV output
- 🆓 **100% Free** - Open source, no API keys needed

## 📋 Output Fields

| Field | Description | Example |
|-------|-------------|---------|
| `company_name` | Business name | "ACME Electric LLC" |
| `website` | Business website | "https://acmelectric.com" |
| `email` | Contact email | "contact@acmelectric.com" |
| `category` | Business type | "Electrical Contractor" |
| `phone` | Phone number | "(555) 123-4567" |
| `address` | Full address | "123 Main St, Dallas, TX" |

**Example Output:**
```csv
company_name,website,email,category,phone,address
"Clements Electric",https://clementselectric.com,info@clementselectric.com,"Electrician",(214) 555-0100,"Dallas, TX"
"Mr. Electric of Dallas",https://mrelectric.com,dallas@mrelectric.com,"Electrical Service",(972) 555-0200,"Dallas, TX"
```

## 🚀 Quick Start

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/google-maps-scraper.git
cd google-maps-scraper

# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

### 2. Run GUI Mode (Recommended) 💻
```bash
python gui.py
```

### 3. Run CLI Mode 🖥️
```bash
python orchestrator/main.py --query "restaurants" --location "New York"
```

### Windows Quick Launch
Double-click `run_gui.bat` or `run.bat`

## 📖 Usage Examples

### GUI Mode - Point & Click
Launch the modern desktop app and enter:
- **Search Query**: `Electric Contractor`
- **Location**: `Texas`
- Click **Start** → Watch 100+ results appear in real-time!

### CLI Mode - Automation Ready
```bash
# Basic search
python orchestrator/main.py --query "restaurants" --location "New York"

# With auto-proxy rotation (recommended for large batches)
python orchestrator/main.py \
  --query "plumbers" \
  --location "Chicago" \
  --fetch-proxies \
  --use-proxies \
  --max-results 200

# Full options
python orchestrator/main.py \
  --query "dentists" \
  --location "Miami FL" \
  --output dentists_miami.csv \
  --workers 100 \
  --use-proxies
```

## ⚙️ Command Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--query` | `-q` | Search term (e.g., "restaurants") | Prompt |
| `--location` | `-l` | Location (e.g., "New York") | Prompt |
| `--output` | `-o` | Output CSV filename | results.csv |
| `--workers` | `-w` | Concurrent workers | 50 |
| `--max-results` | `-m` | Max results (None=unlimited) | None |
| `--use-proxies` | | Enable proxy rotation | False |
| `--fetch-proxies` | | Auto-fetch 7000+ free proxies | False |

### Advanced Configuration
```python
# In orchestrator/config.py
DEFAULT_WORKERS = 50        # Increase for faster scraping
TIMEOUT = 30               # Request timeout in seconds
MAX_RETRIES = 3            # Retry failed requests
```

## 🌐 Proxy Configuration

### Auto-Fetch Proxies (Easiest)
Enable `--fetch-proxies` to automatically download 7000+ working proxies:
```bash
python orchestrator/main.py --query "hotels" --location "LA" --fetch-proxies --use-proxies
```

### Custom Proxies
Create `proxies.txt` in project root:
```
http://user:pass@proxy1.com:8080
http://proxy2.com:8080
socks5://proxy3.com:1080
http://user:password@host:port
```

### Why Use Proxies?
- ✅ Avoid rate limits
- ✅ Faster scraping with rotation
- ✅ Bypass geo-restrictions
- ✅ 10x more results per hour

## 📦 Requirements

- **Python 3.8+** ([Download](https://python.org))
- **Windows 10/11** (Linux/Mac support coming soon)
- **4GB RAM** minimum (8GB recommended for large batches)
- **Playwright** (auto-installed with `playwright install chromium`)

### Tested On
- ✅ Windows 11 + Python 3.11
- ✅ Windows 10 + Python 3.10
- ✅ Works with/without proxies

## 🏗️ Project Structure

```
google-maps-scraper/
├── 📁 orchestrator/          # Python scraping engine
│   ├── gmaps_robust_scraper.py  # Main scraper (Playwright)
│   ├── email_finder.py          # Email extraction
│   ├── csv_writer.py            # CSV export
│   ├── proxy_scraper.py         # 7000+ proxy fetcher
│   ├── models.py                # Data models
│   └── main.py                  # CLI entry
├── 📁 agents/               # Go agents (optional)
│   ├── scraper.go
│   └── proxy.go
├── 📁 output/               # Generated CSV files
├── 🖥️ gui.py               # Modern GUI app
├── 📋 requirements.txt      # Dependencies
├── ▶️ run_gui.bat         # GUI launcher
├── ▶️ run.bat             # CLI launcher
└── 📖 README.md           # This file
```

## 🎨 GUI Features

Beautiful CustomTkinter interface with:

| Feature | Description |
|---------|-------------|
| 🔍 **Smart Search** | Auto-suggest locations, query validation |
| 📊 **Live Dashboard** | Results count, progress bar, elapsed time |
| 📝 **Activity Log** | Color-coded real-time logging |
| ⚙️ **Settings Panel** | Workers, timeouts, max results |
| 🌐 **Proxy Manager** | Auto-fetch or load custom proxies |
| ⏯️ **Controls** | Start, stop, clear with one click |
| 🌙 **Dark Theme** | Professional modern UI |
| 💾 **Auto-Save** | CSV export with timestamps |

![GUI Preview](https://via.placeholder.com/800x500/2d2d2d/ffffff?text=GUI+Preview+-+Modern+Dark+Theme)

## ⚡ Performance Benchmarks

| Metric | Value |
|--------|-------|
| **Results/Search** | 100-120 businesses |
| **Scrape Speed** | 30-50 businesses/minute |
| **Proxy Pool** | 7000+ auto-rotated |
| **Success Rate** | 95%+ with proxies |
| **Memory Usage** | ~200MB |

### Speed Tips
1. **Use proxies** `--fetch-proxies` for best results
2. **Increase workers** `--workers 100` for faster scraping
3. **Use CLI mode** for batch processing
4. **Run multiple instances** for parallel searches

## ⚠️ Legal Notice

**This tool is for educational and legitimate business research purposes only.**

By using this software, you agree to:
- ✅ Respect [Google Terms of Service](https://policies.google.com/terms)
- ✅ Comply with local data laws (GDPR, CCPA, etc.)
- ✅ Only scrape publicly available data
- ✅ Use scraped data ethically
- ✅ Not use for spam or harassment

**The authors are not responsible for misuse of this tool.**

## 📄 License

This project is licensed under the **MIT License** - see [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2024 Google Maps Scraper Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions...
```

## 🤝 Contributing

Contributions are welcome! Here's how:

1. **Fork** the repository
2. **Create branch** `git checkout -b feature/amazing-feature`
3. **Commit** `git commit -m 'Add amazing feature'`
4. **Push** `git push origin feature/amazing-feature`
5. **Open Pull Request**

### Ideas for Contributions
- [ ] Linux/Mac support
- [ ] JSON/Excel export
- [ ] Search history
- [ ] Duplicate detection
- [ ] Email verification
- [ ] API mode


## ⭐ Star History


[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/google-maps-scraper&type=Date)](https://star-history.com/#yourusername/google-maps-scraper&Date)


## 🙏 Acknowledgments

- [Playwright](https://playwright.dev) - Browser automation
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - Modern GUI
- [gosom/google-maps-scraper](https://github.com/gosom/google-maps-scraper) - Inspiration


---

**Made with ❤️ for the open source community**

If this tool helped you, please ⭐ **Star** this repository!
