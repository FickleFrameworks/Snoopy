# Snoopy OSINT Tool

> **5,377 websites** · Async (aiohttp) · Cross-platform (Windows/Linux) · Fully unlocked

---

## Quickstart

```powershell
cd snoop_safe
pip install -r requirements.txt   # first time only
python snoopy.py username
```

---

## Usage Examples

```powershell
# Basic search (~2,500 sites after geo-skip, ~45 seconds)
python snoopy.py johndoe

# Search multiple users
python snoopy.py johndoe janedoe "space man"

# Print only found accounts (cleaner output)
python snoopy.py -f johndoe

# Quick mode — aggressive, fastest
python snoopy.py -q johndoe

# Set concurrency (1-300, default auto-tuned per platform)
python snoopy.py -p 80 johndoe

# Set per-site timeout in seconds (default: 9)
python snoopy.py -t 5 johndoe

# Route through HTTP proxy (http:// auto-added if omitted)
python snoopy.py --proxy 127.0.0.1:8080 johndoe
python snoopy.py --proxy http://user:pass@proxy.example.com:3128 johndoe

# Route through SOCKS5 / Tor
python snoopy.py --proxy socks5://127.0.0.1:9050 johndoe

# Include geolocked sites (RU, CN, UA, etc) — requires VPN/proxy
python snoopy.py --no-geo johndoe
python snoopy.py --no-geo --proxy 10.0.0.1:8080 johndoe

# Combine flags
python snoopy.py --proxy 10.0.0.1:8080 -p 80 -f -t 5 johndoe

# Search from a file of usernames (one per line, UTF-8)
python snoopy.py -u usernames.txt

# Search only specific site(s)
python snoopy.py -s Twitter -s GitHub johndoe

# Only search sites in specific countries
python snoopy.py -i US -i UK johndoe

# Exclude specific countries
python snoopy.py -e RU -e CN johndoe

# Save found pages locally as HTML
python snoopy.py -S johndoe

# Verbose mode (network diagnostics per site)
python snoopy.py -v johndoe

# View all 5,377 sites in the database
python snoopy.py -l
```

---

## All CLI Flags

### Search Flags

| Flag | Short | Example | Description |
|------|-------|---------|-------------|
| `nickname` | | `johndoe` | Username(s) to search. Wrap spaces in quotes. |
| `--proxy` | `-x` | `-x 10.0.0.1:8080` | Route requests through HTTP/SOCKS proxy. `http://` auto-added if omitted. |
| `--geo` | `-g` | | Skip geolocked non-US sites (default: **enabled**). |
| `--no-geo` | | | Include ALL regions including geolocked (RU, CN, UA, etc). Use with VPN/proxy. |
| `--quick` | `-q` | | Fast aggressive mode. Auto-optimized concurrency, skips retries. |
| `--pool` | `-p` | `-p 80` | Set concurrent requests manually (1-300). |
| `--found-print` | `-f` | | Print only found accounts (hide misses). |
| `--time-out` | `-t` | `-t 5` | Max seconds to wait per site (default: 9). |
| `--site` | `-s` | `-s Twitter` | Search only on specific site(s). Repeatable. |
| `--exclude` | `-e` | `-e RU -e CN` | Exclude countries by code. Repeatable. |
| `--include` | `-i` | `-i US -i UK` | Search ONLY in specified countries. Repeatable. |
| `--country-sort` | `-c` | | Sort results by country. |
| `--userlist` | `-u` | `-u users.txt` | Search nicknames from a UTF-8 file (one per line). |
| `--save-page` | `-S` | | Save found user pages as local HTML files. |
| `--verbose` | `-v` | | Show detailed network diagnostics during search. |
| `--no-func` | `-n` | | Monochrome mode: disable colors, flags, browser auto-open. |
| `--base` | `-b` | `-b mydb` | Use alternative local database file. |

### Service Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--version` | `-V` | Print software version and system info. |
| `--list-all` | `-l` | Print detailed info about the site database. |
| `--autoclean` | `-a` | Delete all reports and clear cache. |
| `--module` | `-m` | Open the plugins menu (GEO_IP, Yandex parser, Vgeocoder). |

---

## Geo-Skip (Default Behavior)

By default, Snoopy **skips ~2,855 geolocked sites** in regions that require a local IP address:

- **RU** (Russia) — 2,604 sites
- **UA** (Ukraine) — 200 sites
- **BY** (Belarus), **KZ** (Kazakhstan), **CN** (China), **IR** (Iran), **KP**, **CU**, **VN**

These sites will always timeout or fail from a US/EU IP without a VPN. Skipping them cuts search time from ~2 minutes to **~45 seconds**.

Use `--no-geo` to include them (pair with `--proxy` pointing to a VPN/proxy in that region).

---

## False Positive Filtering

Snoopy includes multi-layer false positive detection:

1. **DB error strings** — site-specific error messages from the database
2. **Generic phrase matching** — 25+ common "not found" phrases across all languages
3. **Redirect-to-homepage detection** — catches sites that redirect to index.php for missing users
4. **Broken page detection** — PHP source leaks, WAF challenges, server errors
5. **Username-presence verification** — for status_code type sites, verifies the username appears in page content
6. **Size-comparison heuristic** — compares against known-good user page sizes
7. **Tiny response filtering** — pages under 3KB/5KB flagged as empty shells

Some sites (GitHub, Twitch, Periscope) render 404 pages client-side with JavaScript, returning HTTP 200 for all URLs. These cannot be detected without a headless browser and may produce false positives.

---

## Output

Results are saved in three formats under `results/nicknames/`:

| Format | Location | Description |
|--------|----------|-------------|
| **HTML** | `html/username.html` | Self-contained interactive report (no server needed). |
| **TXT** | `txt/username.txt` | Plain text summary. |
| **CSV** | `csv/username.csv` | Spreadsheet-friendly data with response times. |

The HTML report opens automatically in your browser after the search completes.

---

## Performance

| Platform | Default Concurrency | Quick Mode (`-q`) | Typical Time (~2,500 sites with geo-skip) |
|----------|--------------------|--------------------|------------------------------------------|
| **Windows** | 60 | 80 | ~45-60 seconds |
| **Linux** | 200 | 300 | ~20-40 seconds |
| **Android** | 17 | 17 | ~5-10 minutes |

Use `-p` to override. Use `-t 3` to reduce per-site timeout for faster runs.
Use `-f` to suppress "Alas!" output and only print found accounts.

---

## Architecture

- **Fully async**: `asyncio` + `aiohttp` — no thread or process pools for HTTP requests.
- **ProactorEventLoop** on Windows (no 512 file descriptor limit).
- **Single shared session**: One `aiohttp.ClientSession` reused across all sites and usernames.
- **Semaphore-controlled concurrency**: Platform-tuned, user-overridable with `-p`.
- **Proxy support**: Per-request proxy via `--proxy` / `-x` — HTTP, HTTPS, SOCKS5.
- **Geo-skip**: Default skip of geolocked regions (RU, CN, UA, etc) — toggle with `--no-geo`.
- **Database**: 5,377 sites loaded from `BDfull_converted` (base64-encoded JSON).
- **Self-contained HTML reports**: All CSS/JS inlined — just open the file, no server needed.
- **Cross-platform**: Windows, Linux, macOS, Android (Termux).

---

## Required Files

```
snoop_safe/
├── snoopy.py              # Main search engine (async)
├── snoopbanner.py        # Banner, help text, DB loader
├── snoopplugins.py       # Plugins: GEO_IP, Vgeocoder, Yandex parser
├── snoopnetworktest.py   # Network speed test (used by -v flag)
├── BDfull_converted      # Site database (5,377 sites, base64-encoded JSON)
├── domainlist.txt        # Email domain list (username validation)
├── requirements.txt      # Python dependencies
└── web/
    ├── style.css          # HTML report stylesheet (inlined at build time)
    ├── app.js             # Particle network config (inlined at build time)
    └── particles.js       # Particles.js library (inlined at build time)
```

### Can be deleted (not needed):

| File/Dir | Reason |
|----------|--------|
| `BDflag` | Never read — `snoopy.py` loads `BDfull_converted` for both `BDdemo` and `BDflag` variables. |
| `BDdemo` | Old 330-site demo database. Replaced by `BDfull_converted`. |
| `__pycache__/` | Auto-generated Python bytecode cache. Regenerated on run. |
| `.claude/` | Claude Code config. Not part of the tool. |
| `results/` | Generated output. Safe to delete (recreated on search). |
