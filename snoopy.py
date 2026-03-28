#! /usr/bin/env python3
# Copyright (c) 2020 Snoopy <snoopproject@protonmail.com>

import argparse
import asyncio
import certifi
import csv
import glob
import itertools
import json
import locale
import os
import platform
import psutil
import random
import re
import requests
import shutil
import signal
import ssl
import subprocess
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import textwrap
import time
import webbrowser

import aiohttp
from charset_normalizer import detect as char_detect
from collections import Counter
from datetime import timedelta
from colorama import Fore, init, Style
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TimeElapsedColumn
from rich.style import Style as STL
from rich.table import Table

import snoopbanner
import snoopnetworktest
import snoopplugins

if int(platform.python_version_tuple()[1]) >= 8:
    from importlib.metadata import version as version_lib
    PYTHON_3_8_PLUS = True
else:
    PYTHON_3_8_PLUS = False


locale.setlocale(locale.LC_ALL, '')
init(autoreset=True)
console = Console()


## Banner and software version.
def version_snoop(vers, vers_code, demo_full):
    print(f"""\033[36m
  ____
 / ___|_ __   ___   ___  _ __
 \\___ \\| '_ \\ / _ \\ / _ \\| '_ \\
  ___) | | | | (_) | (_) | |_) |
 |____/|_| |_|\\___/ \\___/| .__/
                          |_|   \033[0m \033[37m\033[44m{vers}\033[0m
""")

    sb = "build" if vers_code == 'b' else "source"
    _sb = "demo" if demo_full == 'd' else "full"

    if WINDOWS: OS_ = f"en Snoopy for Windows {sb} {_sb}"
    elif ANDROID: OS_ = f"en Snoopy for Termux {sb} {_sb}"
    elif LINUX: OS_ = f"en Snoopy for GNU/Linux {sb} {_sb}"

    console.print(f"[dim cyan]Examples:\n $ [/dim cyan]" + \
                  f"[cyan]{'cd C:' + chr(92) + 'path' + chr(92) + 'snoop' if WINDOWS else 'cd ~/snoop'}[/cyan]")
    console.print(f"[dim cyan] $ [/dim cyan][cyan]{'python' if WINDOWS else 'python3'} snoopy.py --help[/cyan] #help")
    console.print(f"[dim cyan] $ [/dim cyan][cyan]{'python' if WINDOWS else 'python3'} snoopy.py --module[/cyan] #plugins")
    console.print(f"[dim cyan] $ [/dim cyan][cyan]{'python' if WINDOWS else 'python3'} snoopy.py nickname[/cyan] #search user")
    console.rule(characters="=", style="cyan")
    print("")

    return f"{vers}_{OS_}"


## Create results directories.
def mkdir_path():
    try:
        if not WINDOWS and "build" in VERSION:
            replace_snoop_dir = os.path.join(os.environ["HOME"], 'snoop')
            if os.path.exists(replace_snoop_dir):
                shutil.move(replace_snoop_dir, os.path.join(os.environ["HOME"], '.snoop'))
    except Exception:
        pass

    dirhome = os.path.join(os.environ["LOCALAPPDATA" if WINDOWS else "HOME"], "snoop" if WINDOWS else '.snoop')

    if ANDROID:
        if not os.access("/data/data/com.termux/files/home/storage/shared", os.W_OK):
            console.print("[bold yellow]Agree to the one-time, standard operation in Termux by providing access to " + \
                          "storage, otherwise search results cannot be saved in the public directory on Android OS, " + \
                          "for more info see Termux Wiki: https://wiki.termux.com/wiki/Termux-setup-storage[/bold yellow]\n")
            code = subprocess.run("termux-setup-storage", shell=True)
            if code.returncode == 1:
                console.print("\n[bold red]search results directory: '/storage/emulated/0/snoop' not created, " + \
                              "rejected by user.[bold red]\n")
        else:
            dirhome = "/data/data/com.termux/files/home/storage/shared/snoop"

    dirpath = os.getcwd() if 'source' in VERSION and not ANDROID else dirhome

    os.makedirs(f"{dirpath}/results", exist_ok=True)
    os.makedirs(f"{dirpath}/results/nicknames/html", exist_ok=True)
    os.makedirs(f"{dirpath}/results/nicknames/txt", exist_ok=True)
    os.makedirs(f"{dirpath}/results/nicknames/csv", exist_ok=True)
    os.makedirs(f"{dirpath}/results/nicknames/save reports", exist_ok=True)
    os.makedirs(f"{dirpath}/results/plugins/ReverseVgeocoder", exist_ok=True)
    os.makedirs(f"{dirpath}/results/plugins/Yandex_parser", exist_ok=True)
    os.makedirs(f"{dirpath}/results/plugins/domain", exist_ok=True)

    return dirpath


## Constants.
ANDROID = True if hasattr(sys, 'getandroidapilevel') else False
WINDOWS = True if sys.platform == 'win32' else False
LINUX = True if ANDROID is False and WINDOWS is False else False
MACOS = True if platform.system() == "Darwin" else False #macOS support (experimental).

VERSION = version_snoop('v1.4.3', "s", "f")
DIRPATH = mkdir_path()
TIME_START = time.time()
TIME_DATE = time.localtime()


dic_binding = {"badraw": [], "badzone": [],
               "censors": 0, "android_lame_workhorse": False}


## Create web directory and check it, but not the files inside + give correct "-x -R" permissions after compiling binary data [.mp3].
def web_path_copy():
    try:
        if "build" in VERSION and os.path.exists(f"{DIRPATH}/web") is False:
            shutil.copytree(web_path, f"{DIRPATH}/web")
            if LINUX: #and 'build' in 'VERSION'
                os.chmod(f"{DIRPATH}/web", 0o755)
                for total_file_path in glob.iglob(f"{DIRPATH}/web/**/*", recursive=True):
                    if os.path.isfile(total_file_path) == True:
                        os.chmod(total_file_path, 0o644)
                    else:
                        os.chmod(total_file_path, 0o755)
        elif "source" in VERSION and ANDROID and os.path.exists("/data/data/com.termux/files/home/storage/shared/snoop/web") is False:
            shutil.copytree(f"{os.getcwd()}/web", "/data/data/com.termux/files/home/storage/shared/snoop/web")
    except Exception as e:
        print(f"ERR: {e}")


## Memory usage.
def mem_test():
    try:
        return round(psutil.virtual_memory().available / 1024 / 1024)
    except Exception:
        if not WINDOWS:
            console.print(f"{' ' * 17} [bold red]ERR Psutil lib[/bold red]")
            return int(subprocess.check_output("free -m", shell=True, text=True).splitlines()[1].split()[-1])
        else:
            return -1


## Print info string.
def info_str(infostr, nick, color=True):
    if color is True:
        print(f"{Fore.GREEN}[{Fore.YELLOW}*{Fore.GREEN}] {infostr}{Fore.RED} <{Fore.WHITE} {nick} {Fore.RED}>{Style.RESET_ALL}")
    else:
        print(f"\n[*] {infostr} < {nick} >")


## Check usernames.
with open('domainlist.txt', 'r', encoding="utf-8") as err:
    ERMAIL_SET = set(line.strip() for line in err if line.strip())
def check_invalid_username(username, symbol_bad_username=None, phone=None, dot=None, email=None):
    if symbol_bad_username: #check username for special characters
        symbol_bad = re.compile(r"[^a-zA-Zа-яА-Я\_\s\d\%\@\-\.\+]")
        err_nick = re.findall(symbol_bad, username)

        if err_nick:
            print(Style.BRIGHT + Fore.RED + format_txt("⛔️ invalid characters in nickname: " + \
                                                       "{0}{1}{2}{3}{4}".format(Style.RESET_ALL, Fore.RED, err_nick,
                                                                                Style.RESET_ALL, Style.BRIGHT + Fore.RED),
                                                       k=True, m=True) + "\n   skip\n")
            return False

    if phone: #check username for phone number
        patterns = {'Russia/Kazakhstan': r'^(?:\+7|7|8)\d{10}$', 'Belarus': r'^(?:\+375|375|80)\d{9}$',
                    'Ukraine': r'^(?:\+380|380)\d{9}$', 'EU/CIS/AU/ZA': r'^(?:0)\d{9}$',
                    'Uzbekistan': r'^(?:\+998|998)\d{9}$', 'Tajikistan': r'^(?:\+992|992)\d{9}$',
                    'Kyrgyzstan': r'^(?:\+996|996|0)\d{9}$', 'Armenia': r'^(?:\+374|374)\d{8}$',
                    'Azerbaijan': r'^(?:\+994|994)\d{9}$', 'Moldova': r'^(?:\+373|373)\d{8}$',
                    'Georgia': r'^(?:\+995|995)\d{9}$', 'Turkmenistan': r'^(?:\+993|993)\d{8}$',
                    'United Kingdom': r'^(?:\+44|44)\d{10}$', 'Hungary': r'^\+36\d{9}$',
                    'Cyprus': r'^(?:\+357|357)\d{8}$', 'Latvia': r'^(?:\+371|371)\d{8}$',
                    'Lithuania': r'^(?:\+370|370)\d{8}$', 'Netherlands': r'^(?:\+31|31)\d{9}$',
                    'Norway': r'^(?:\+47|47)\d{8}$', 'Poland': r'^(?:\+48|48)\d{9}$',
                    'Portugal': r'^(?:\+351|351)\d{9}$', 'Romania': r'^(?:\+40|40)\d{9}$',
                    'Slovakia': r'^(?:\+421|421)\d{9}$', 'Slovenia': r'^(?:\+386|386)\d{8}$',
                    'Turkey': r'^(?:\+90|90)\d{10}$', 'France': r'^(?:\+33|33)\d{9}$',
                    'Czech Republic': r'^(?:\+420|420)\d{9}$', 'Switzerland': r'^(?:\+41|41)\d{9}$',
                    'USA/Canada': r'^(?:\+1|1)\d{10}$', 'Australia': r'^(?:\+61|61)\d{9}$',
                    'India': r'^(?:\+91|91)\d{10}$', 'China': r'^(?:\+86|86)?\d{11}$',
                    'Japan': r'^(?:\+81|81)\d{10}$', 'Mexico': r'^(?:\+52|52)?\d{10}$',
                    'South Africa': r'^(?:\+27|27)\d{9}$'}
        
        for country, pattern in patterns.items():
            if re.match(pattern, username):
                print(Style.BRIGHT + Fore.RED + format_txt("⛔️ snoop tracks user accounts, " + \
                                                           "but not phone numbers, determined phone number from location: '{0}'"
                                                           .format(country), k=True, m=True) + "\n   skip\n")
                return False

    if dot: #check username for dot/email
        if '.' in username and '@' not in username or username.count(".") > 1:
            print(Style.BRIGHT + Fore.RED + format_txt("⛔️ nickname containing special character [.] is limited for search, " + \
                                                       "reason: multiple complexity of DB support...",
                                                       k=True, m=True) + "\n   skip\n")
            return False

    if email: #check username for e_mail
        username_bad = username.rsplit(sep='@', maxsplit=1)
        username_bad = '@bro'.join(username_bad).lower()

        for ermail_iter in ERMAIL_SET:
            if ermail_iter.lower() == username.lower():
                print("\n" + Style.BRIGHT + Fore.RED + format_txt("⛔️ bad nickname: '{0}' (pure domain detected)"
                                                                  .format(ermail_iter), k=True, m=True) + "\n   skip\n")
                return False
            elif ermail_iter.lower() in username.lower():
                usernameR = username.rsplit(sep=ermail_iter.lower(), maxsplit=1)[1]
                username = username.rsplit(sep='@', maxsplit=1)[0]

                if len(username) == 0:
                    username = usernameR
                print(f"\n{Fore.CYAN}E-mail address detected, extracting nickname: " + \
                      f"'{Style.BRIGHT}{Fore.CYAN}{username}{Style.RESET_ALL}" + \
                      f"{Fore.CYAN}'\nSnoopy can distinguish e-mail from login, for example, search '{username_bad}'\n" + \
                      f"is not valid email, but may exist as a nickname, therefore — it will not be truncated\n")

                if len(username) != 0 and len(username) < 3:
                    print(Style.BRIGHT + Fore.RED + format_txt("⛔️ nickname cannot be shorter than 3 characters",
                                                               k=True, m=True) + "\n   skip\n")
                    return False

    return username


## Bad_raw, bad_zone.
def bad_raw(flagBS_err, bad_zone, nick, lst_options):
    print(f"{Fore.CYAN}├───Search Date:{Style.RESET_ALL} {time.strftime('%Y-%m-%d__%H:%M:%S', TIME_DATE)}")

    if any(lst_options):
        print(f"{Fore.CYAN}└────\033[31;1mBad_raw: {flagBS_err}% DB, bad_zone {bad_zone}\033[0m\n")
    else:
        if 4 >= flagBS_err >= 2:
            print(f"{Fore.CYAN}└────\033[33;1mWarning! Bad_raw: {flagBS_err}% DB, bad_zone {bad_zone}\033[0m")
        elif 12 >= flagBS_err > 4:
            print(f"{Fore.CYAN}└────\033[31;1mWarning!! Bad_raw: {flagBS_err}% DB, bad_zone {bad_zone}\033[0m")
        elif flagBS_err > 12:
            print(f"{Fore.CYAN}└────\033[30m\033[41mWarning!!! Bad_raw: {flagBS_err}% DB, critical level, " + \
                  f"bad_zone {bad_zone}\033[0m")

    if not any(lst_options):
        print(Fore.CYAN + "     └─unstable connection or I_Censorship")
        print(f"       \033[36m{'├' if 'full' in VERSION else '└'}─use \033[36;1mVPN\033[0m\033[36m/'\033[0m" + \
              f"\033[36;1m--web-base\033[0m\033[36m'\033[0m ", end='' if 'full' in VERSION else '\n\n')
        if "full" in VERSION:
            nick = f"'{nick}'" if nick.count(" ") > 0 else nick
            print(f"\033[36m\n       └─or exclude bad_zone from search: '\033[36;1m" + \
                  f"{bad_zone.split('/')[0].replace('~', '')}\033[0m" + \
                  f"\033[36m'\n         └─$ {os.path.basename(sys.argv[0])} -w --exclude " + \
                  f"{bad_zone.split('/')[0].replace('~', '')} {nick}\033[0m\n")


## Formatting, indentation.
def format_txt(text, k=False, m=False):
    """
    Some Windows consoles do not support the "•" symbol, 'subprocess.run' — on some Windows versions
    runs in a different encoding/font than default. A more reliable solution would be to check characters
    via temporary 'io' stream change, but then console colors break. The rest of the code regulates indentations.
    """
    if WINDOWS:
        try:
            for symbol in ["•", "·", "*", "-", "+"]:
                check_symbol = subprocess.run(['cmd.exe', '/c', 'echo', symbol], capture_output=True, text=True).stdout.strip()
                if symbol in check_symbol:
                    break
        except Exception:
            symbol = "+"

    gal = f" {symbol} " if WINDOWS else " ✔ "
    indent_end = "" if k else " " * 3
    gal = gal if k and not m else ""

    try:
        width = os.get_terminal_size()[0]
    except OSError:
        width = 80
    return textwrap.fill(f"{gal}{text}", width=width, subsequent_indent=" " * 3, initial_indent=indent_end)


## Print errors.
def print_error(websites_names, errstr, country_code, errX, verbose=False, color=True):
    """Print various network errors."""
    if color is True:
        print(f"{Style.RESET_ALL}{Fore.RED}[{Style.BRIGHT}{Fore.RED}-{Style.RESET_ALL}{Fore.RED}]{Style.BRIGHT}" \
              f"{Fore.GREEN} {websites_names}: {Style.BRIGHT}{Fore.RED}{errstr}{country_code}" \
              f"{Fore.YELLOW} {errX if verbose else ''} {Style.RESET_ALL}")
    else:
        print(f"[!] {websites_names}: {errstr}{country_code} {errX if verbose else ''}")


## Cross-platform printing, indication.
def print_found_country(websites_names, url, country_Emoj_Code, verbose=False, color=True):
    """Print account found."""
    if color is True and WINDOWS:
        print(f"{Style.RESET_ALL}{Style.BRIGHT}{Fore.CYAN}{country_Emoj_Code}" \
              f"{Fore.GREEN}  {websites_names}:{Style.RESET_ALL}{Fore.GREEN} {url}{Style.RESET_ALL}")
    elif color is True and not WINDOWS:
        print(f"{Style.RESET_ALL}{country_Emoj_Code}{Style.BRIGHT}{Fore.GREEN}  {websites_names}: " \
              f"{Style.RESET_ALL}{Style.DIM}{Fore.GREEN}{url}{Style.RESET_ALL}")
    else:
        print(f"[+] {websites_names}: {url}")


def print_not_found(websites_names, verbose=False, color=True):
    """Print account not found."""
    if color is True:
        print(f"{Style.RESET_ALL}{Fore.CYAN}[{Style.BRIGHT}{Fore.RED}-{Style.RESET_ALL}{Fore.CYAN}]" \
              f"{Style.BRIGHT}{Fore.GREEN} {websites_names}: {Style.BRIGHT}{Fore.YELLOW}Alas!{Style.RESET_ALL}")
    else:
        print(f"[-] {websites_names}: Alas!")


## Print skipping sites by block mask in username, gray_list.
def print_invalid(websites_names, message, color=True):
    if color is True:
        return f"{Style.RESET_ALL}{Fore.RED}[{Style.BRIGHT}{Fore.RED}-{Style.RESET_ALL}{Fore.RED}]" \
               f"{Style.BRIGHT}{Fore.GREEN} {websites_names}: {Style.RESET_ALL}{Fore.YELLOW}{message}{Style.RESET_ALL}\n"
    else:
        return f"[-] {websites_names}: {message}\n"


## Print warning about outdated library versions.
def warning_lib():
    if int(requests.urllib3.__version__.split(".")[0]) < 2 or int("".join(requests.__version__.split("."))) < 2282:
        console.log("[yellow]Warning! \n\nIn Requests > v2.28.2 / Urllib3 v2 developers dropped support for old ciphers. " + \
                    "Some, few, outdated sites from DB working on old technology will continue " + \
                    "to connect without errors (Snoopy will strive to maintain compatibility mode with any old versions of " + \
                    "Requests / Urllib3).[/yellow]\n\n[bold green]Still, it is recommended to update dependencies: \n" + \
                    "$ python -m pip install requests urllib3 -U[/bold green]", highlight=False)
        console.rule(characters="=", style="cyan")


## Async response wrapper — drop-in replacement for requests.Response interface.
class AsyncResponse:
    __slots__ = ('status_code', 'content', '_encoding', '_text', 'headers', 'elapsed', 'url')

    def __init__(self, status_code, content, headers, elapsed, encoding=None, url=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers
        self.elapsed = elapsed
        self.url = url or ""
        self._text = None
        if encoding:
            self._encoding = encoding
        else:
            ct = headers.get('Content-Type', '')
            if 'charset=' in ct.lower():
                self._encoding = ct.lower().split('charset=')[-1].split(';')[0].strip()
            else:
                self._encoding = 'ISO-8859-1'

    @property
    def encoding(self):
        return self._encoding

    @encoding.setter
    def encoding(self, value):
        self._encoding = value
        self._text = None

    @property
    def text(self):
        if self._text is None:
            try:
                self._text = self.content.decode(self._encoding or 'utf-8')
            except (UnicodeDecodeError, LookupError):
                self._text = self.content.decode('utf-8', errors='replace')
        return self._text


## Async network — single aiohttp session shared across all requests.
_aio_session = None
_aio_connector = None

async def get_aio_session(cert=False, concurrency_limit=100):
    """Create or return cached aiohttp.ClientSession with platform-tuned connector."""
    global _aio_session, _aio_connector
    if _aio_session is not None and not _aio_session.closed:
        return _aio_session

    if cert is False:
        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
    else:
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())

    try:
        ciphers = ('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:ECDH+AESGCM:DH+AESGCM'
                   ':ECDH+AES:DH+AES:RSA+AESGCM:RSA+AES:!aNULL:!eNULL:!MD5:!DSS:HIGH:!DH')
        ssl_ctx.set_ciphers(ciphers)
        try:
            ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        except Exception:
            pass
    except Exception:
        pass

    _aio_connector = aiohttp.TCPConnector(
        limit=concurrency_limit,
        limit_per_host=20,
        ssl=ssl_ctx,
        enable_cleanup_closed=True,
        ttl_dns_cache=300,
        force_close=False,
    )
    _aio_session = aiohttp.ClientSession(
        connector=_aio_connector,
        cookie_jar=aiohttp.CookieJar(unsafe=True),
    )
    return _aio_session


async def close_aio_session():
    """Gracefully close the shared aiohttp session."""
    global _aio_session, _aio_connector
    if _aio_session is not None and not _aio_session.closed:
        await _aio_session.close()
        await asyncio.sleep(0.25)  # allow SSL transports to close gracefully
    _aio_session = None
    _aio_connector = None


async def a_request(cert=False, method="get", url=None, headers=None, allow_redirects=True,
                    timeout=9, concurrency_limit=100, proxy=None):
    """Async HTTP request returning an AsyncResponse (compatible with requests.Response interface)."""
    session = await get_aio_session(cert=cert, concurrency_limit=concurrency_limit)
    aio_timeout = aiohttp.ClientTimeout(total=timeout, connect=timeout)
    t0 = time.monotonic()

    max_redirects = 6 if ANDROID else 9
    req_method = session.get if method == "get" else session.head

    async with req_method(url, headers=headers or {}, allow_redirects=allow_redirects,
                          timeout=aio_timeout, max_redirects=max_redirects, proxy=proxy) as resp:
        content = await resp.read()
        elapsed_sec = time.monotonic() - t0
        return AsyncResponse(
            status_code=resp.status,
            content=content,
            headers=dict(resp.headers),
            elapsed=timedelta(seconds=elapsed_sec),
            url=str(resp.url),
        )


## Sync r_session kept for sreports/new_session (report saving uses requests).
def r_session(url=None, headers="", allow_redirects=True, timeout=9):
    """Synchronous request for report saving only."""
    session = requests.Session()
    session.verify = False
    session.max_redirects = 9
    requests.packages.urllib3.disable_warnings()
    return session.get(url=url, headers=headers, allow_redirects=allow_redirects, timeout=timeout)


## Async fetch with error handling (replaces r_results + executor pattern).
async def fetch_site(url, method, headers, allow_redirects, timeout, cert, concurrency_limit,
                     websites_names="", error_type="", norm=False, print_found_only=False,
                     verbose=False, color=True, country_code='', proxy=None):
    """Fetch a single site, handling all error types. Returns (response, error_type, elapsed_str)."""
    try:
        res = await a_request(cert=cert, method=method, url=url, headers=headers,
                              allow_redirects=allow_redirects, timeout=timeout,
                              concurrency_limit=concurrency_limit, proxy=proxy)
        if res.status_code:
            return res, error_type, str(round(res.elapsed.total_seconds(), 2))
    except aiohttp.ClientConnectorError as err2:
        err_str = str(err2)
        if 'aborted' in err_str or 'None' in err_str or 'SSL' in err_str or 'Failed' in err_str:
            dic_binding["censors"] += 1
            if norm is False and print_found_only is False:
                print_error(websites_names, "Connection error ", country_code, err2, verbose, color)
            return "FakeNone", "", "-"
        else:
            if norm is False and print_found_only is False:
                print_error(websites_names, "Censorship | TLS ", country_code, err2, verbose, color)
    except asyncio.TimeoutError as err3:
        if norm is False and print_found_only is False:
            print_error(websites_names, "Timeout error ", country_code, err3, verbose, color)
        dic_binding["censors"] += 1
        return "FakeStuck", "", "-"
    except aiohttp.ClientError as err4:
        if norm is False and print_found_only is False:
            print_error(websites_names, "Unexpected error ", country_code, err4, verbose, color)
    except Exception as err5:
        if norm is False and print_found_only is False:
            print_error(websites_names, "Network Pool Crash ", country_code, err5, verbose, color)

    dic_binding["censors"] += 1
    return None, "Great Snoopy returns None", "-"


## Save reports, option (-S).
def new_session(url, headers, error_type, username, websites_names, r, t):
    """
    If nickname is found, but the actual html-page is further down the redirect,
    we bring up a new connection and move along the redirect to grab and save it.
    """

    response = r_session(url=url, headers=headers, allow_redirects=True, timeout=t)

# Trap on some sites (if response.content is not None ≠ if response.content).
    if response.content is not None and response.encoding == 'ISO-8859-1':
        try:
            response.encoding = char_detect(response.content[:4096]).get("encoding")
            if response.encoding is None:
                response.encoding = "utf-8"
        except Exception:
            response.encoding = "utf-8"

    try:
        session_size = len(response.content) #count extracted data
    except UnicodeEncodeError:
        session_size = None
    return response, session_size


def sreports(url, headers, error_type, username, websites_names, r):
    os.makedirs(f"{DIRPATH}/results/nicknames/save reports/{username}", exist_ok=True)
# Save reports for method: redirection.
    if error_type == "redirection":
        try:
            response, session_size = new_session(url, headers, error_type,
                                                 username, websites_names, r, t=6)
        except requests.exceptions.ConnectionError:
            time.sleep(0.02)
            try:
                response, session_size = new_session(url, error_type, username,
                                                     websites_names, r, headers="", t=3)
            except Exception:
                session_size = 'Err' #count extracted data
        except Exception:
            session_size = 'Err'
# Save reports for all other methods: status; response; message with standard parameters.
    try:
        with open(f"{DIRPATH}/results/nicknames/save reports/{username}/{websites_names}.html", 'w', encoding=r.encoding) as rep:
            if 'response' in locals():
                rep.write(response.text)
            elif error_type == "redirection" and 'response' not in locals():
                rep.write("❌ Snoopy bad_save, timeout")
            else:
                rep.write(r.text)
    except Exception:
        console.log(snoopbanner.err_all(err_="low"), f"\nlog --> [{websites_names}:[bold red] {r.encoding} | response?[/bold red]]")

    if error_type == "redirection":
        return session_size


## Snoop function (async).
async def snoop(username, BDdemo_new, verbose=False, norm=False, reports=False, user=False, country=False, lst_username=None,
                speed=False, print_found_only=False, timeout=None, color=True, cert=False, header_custom=None, proxy=None):
## Print info lines.
    easteregg = ['snoopy', 'snoop', 'snoop_project', 'snoop-project', 'snooppr']

    nick = username.replace("%20", " ")
    info_str("searching for:", nick, color)

    if len(username) < 3:
        print(Style.BRIGHT + Fore.RED + format_txt("⛔️ nickname cannot be shorter than 3 characters",
                                                   k=True, m=True) + "\n   skip\n")
        return False, False, nick
    elif username.lower() in easteregg:
        with console.status("[bold blue] 💡 Easter egg detected...", spinner='noise'):
            try:
                r_east = r_session(url="https://raw.githubusercontent.com/snooppr/snoop/master/changelog.txt", timeout=timeout)
                r_repo = r_session(url='https://api.github.com/repos/snooppr/snoop', timeout=timeout).json()
                r_latestvers = r_session(url='https://api.github.com/repos/snooppr/snoop/tags', timeout=timeout).json()

                console.print(Panel(Markdown(r_east.text.replace("=" * 83, "")),
                                    subtitle="[bold blue]snoop version log[/bold blue]", style=STL(color="cyan")))
                console.print(Panel(f"[bold cyan]Project creation date:[/bold cyan] 2020-02-14 " + \
                                    f"({round((time.time() - 1581638400) / 86400)}_days).\n" + \
                                    f"[bold cyan]Last repository update:[/bold cyan] " + \
                                    f"{'_'.join(r_repo.get('pushed_at')[0:-4].split('T'))} (UTC).\n" + \
                                    f"[bold cyan]Repository compression:[/bold cyan] 2024-12-11.\n" + \
                                    f"[bold cyan]Repository size:[/bold cyan] {round(int(r_repo.get('size')) / 1024, 1)} MB.\n" + \
                                    f"[bold cyan]Github rating:[/bold cyan] {r_repo.get('watchers')} stars.\n" + \
                                    f"[bold cyan]Hidden options:[/bold cyan]\n'--headers/-H':: Manually set user-agent, agent " + \
                                                              f"is enclosed in quotes, by default for each site " + \
                                                              f"a random or redefined user-agent from snoop DB is set.\n" + \
                                                              f"'--cert-on/-C':: Enable certificate verification on servers, " + \
                                                              f"by default certificate verification on servers " + \
                                                              f"is disabled, which allows processing problematic sites without errors.\n"
                                    f"[bold cyan]Latest snoop version:[/bold cyan] {r_latestvers[0].get('name')}.",
                                    style=STL(color="cyan"), subtitle="[bold blue]key metrics[/bold blue]", expand=False))
            except Exception:
                console.log(snoopbanner.err_all(err_="high"))
        sys.exit()

    username = re.sub(" ", "%20", username)


## Prevention 'DoS' due to invalid logins; phone numbers, search errors, special characters.
    username = check_invalid_username(username, symbol_bad_username=True, phone=True, dot=True, email=True)
    if username is False:
        return False, False, nick


## Determine concurrency limit for async semaphore (replaces ThreadPool/ProcessPool sizing).
    if speed:
        concurrency = speed
    elif ANDROID:
        concurrency = min(len(BDdemo_new), 17)
    elif WINDOWS or MACOS:
        cpu = 1 if psutil.cpu_count(logical=False) is None else psutil.cpu_count(logical=False)
        concurrency = min(len(BDdemo_new), 80 if cpu >= 4 else 40) if norm else min(len(BDdemo_new), 60 if cpu >= 4 else 30)
    elif LINUX:
        try:
            cpus = len(os.sched_getaffinity(0))
        except Exception:
            cpus = os.cpu_count() or 4
        concurrency = min(len(BDdemo_new), 300 if cpus >= 4 else 120) if norm else min(len(BDdemo_new), 200 if cpus >= 4 else 80)

    sem = asyncio.Semaphore(concurrency)
    concurrency_limit = 200 if LINUX else (100 if WINDOWS else 40)

    if reports is True:
        executor_req_save = ThreadPoolExecutor(max_workers=2)


## Analysis of all sites.
    dic_snoop_full = {}
    async_tasks = {}  # {task: (websites_names, param_websites, url, allow_redirects)}
    lst_invalid = []

## Create async tasks for all requests.
    for websites_names, param_websites in BDdemo_new.items():
        results_site = {}
        results_site['flagcountry'] = param_websites.get("country")
        results_site['flagcountryklas'] = param_websites.get("country_klas")
        results_site['url_main'] = param_websites.get("urlMain")

# Custom browser user-agent (random for each site).
        majR = random.randint(101, 123)
        ua_platform = random.choice([
            f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{majR}.0.0.0 Safari/537.36",
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{majR}.0.0.0 Safari/537.36"])
        headers = {"User-Agent": ua_platform}

# Override/add any additional headers required for the site from DB, or set U-A from CLI.
        if header_custom is not None:
            headers.update({"User-Agent": ''.join(header_custom)})
        elif "headers" in param_websites:
            headers.update(param_websites["headers"])

# Skip temporarily disabled site, do not make request if username doesn't fit the site.
        exclusionYES = param_websites.get("exclusion")
        if exclusionYES and re.search(exclusionYES, username) or param_websites.get("bad_site") == 1:
            if exclusionYES and re.search(exclusionYES, username) and not print_found_only and not norm:
                lst_invalid.append(print_invalid(websites_names, f"#invalid nick '{nick}' for this site", color))
            results_site["exists"] = "invalid_nick"
            results_site["url_user"] = '*' * 56
            results_site['countryCSV'] = "****"
            results_site['http_status'] = '*' * 10
            results_site['session_size'] = ""
            results_site['check_time_ms'] = '*' * 15
            results_site['response_time_ms'] = '*' * 15
            results_site['response_time_site_ms'] = '*' * 25
            if param_websites.get("bad_site") == 1 and verbose and not print_found_only and not norm:
                lst_invalid.append(print_invalid(websites_names, f"*SKIP. DYNAMIC GRAY_LIST", color))
            if param_websites.get("bad_site") == 1:
                dic_binding.get("badraw").append(websites_names)
                results_site["exists"] = "gray_list"
        else:
# User URL on the site (if it exists).
            url = param_websites["url"].format(username)
            results_site["url_user"] = url
            url_API = param_websites.get("urlProbe")
            url_API = url if url_API is None else url_API.format(username)
# If only status code is needed, do not load page body, saves memory, and many protected sites prefer Head.
            if param_websites["errorTypе"] != 'status_code' or reports:
                method = "get"
            else:
                method = "head"
# Site redirects request.
            if param_websites["errorTypе"] == "response_url" or param_websites["errorTypе"] == "redirection":
                allow_redirects = False
            else:
                allow_redirects = True

# Create async task with semaphore for concurrency control.
            async def _fetch(sem=sem, cert=cert, method=method, url_API=url_API, headers=headers,
                             allow_redirects=allow_redirects, timeout=timeout, concurrency_limit=concurrency_limit,
                             _wn=websites_names, _pw=param_websites, _url=url, _ar=allow_redirects,
                             error_type=param_websites["errorTypе"],
                             norm=norm, print_found_only=print_found_only, verbose=verbose, color=color,
                             country_code=param_websites.get("country_klas", ""), proxy=proxy):
                async with sem:
                    result = await fetch_site(url=url_API, method=method, headers=headers,
                                              allow_redirects=allow_redirects, timeout=timeout, cert=cert,
                                              concurrency_limit=concurrency_limit, websites_names=_wn,
                                              error_type=error_type, norm=norm, print_found_only=print_found_only,
                                              verbose=verbose, color=color, country_code=f" ~{country_code}",
                                              proxy=proxy)
                    return (_wn, _pw, _url, _ar, result)

            task = asyncio.ensure_future(_fetch())
            async_tasks[task] = websites_names

# Add to nested dictionary with all other results.
        dic_snoop_full[websites_names] = results_site


# Print invalid_data.
    if bool(lst_invalid) is True:
        print("".join(lst_invalid))


## Progress_description.
    if not verbose:
        refresh = False
        refresh_per_second = 2.0 if not WINDOWS else 1.0
        if not WINDOWS:
            spin_emoj = 'arrow3' if norm else random.choice(["dots", "dots12"])
            progress = Progress(TimeElapsedColumn(), SpinnerColumn(spinner_name=spin_emoj),
                                "[progress.percentage]{task.percentage:>1.0f}%", BarColumn(bar_width=None, complete_style='cyan',
                                finished_style='cyan bold'), refresh_per_second=refresh_per_second)
        else:
            progress = Progress(TimeElapsedColumn(), "[progress.percentage]{task.percentage:>1.0f}%", BarColumn(bar_width=None,
                                complete_style='cyan', finished_style='cyan bold'), refresh_per_second=refresh_per_second)
    else:
        refresh = True
        progress = Progress(TimeElapsedColumn(), "[progress.percentage]{task.percentage:>1.0f}%", auto_refresh=False)

## Verbalization panel.
        if not ANDROID:
            if color:
                console.print(Panel("[yellow]time[/yellow] | [magenta]perc.[/magenta] | [bold cyan]response (t=s)[/bold cyan] " + \
                                    "| [bold red]total [bold cyan]time (T=s)[/bold cyan][/bold red] | " + \
                                    "[bold cyan]data[/bold cyan] | [bold cyan]avail.ram[/bold cyan]",
                                    title="[cyan]Designation[/cyan]", style=STL(color="cyan")))
            else:
                console.print(Panel("response (t=s) | total time (T=s) | data | avail.ram", title="Designation"))
        else:
            if color:
                console.print(Panel("[yellow]time[/yellow] | [magenta]perc.[/magenta] | [bold cyan]response (t=s)[/bold cyan] " + \
                                    "| [bold red]total [bold cyan]time (T=s)[/bold cyan][/bold red] | [bold cyan]data [/bold cyan]" + \
                                    "| [bold cyan]avail.ram[/bold cyan]",
                                    title="[cyan]Designation[/cyan]", style=STL(color="cyan")))
            else:
                console.print(Panel("time | perc. | response (t=s) | total time (T=s) | data | avail.ram", title="Designation"))


## Walk through async results — all tasks run concurrently via as_completed.
    li_time = [0]
    completed_count = 0
    with progress:
        if color is True:
            task0 = progress.add_task("", total=len(BDdemo_new))

# Count skipped sites toward progress immediately.
        skipped = len(BDdemo_new) - len(async_tasks)
        if skipped > 0 and color is True:
            progress.update(task0, advance=skipped, refresh=refresh)

# Estimate and display expected search time.
        active_count = len(async_tasks)
        if active_count > 100:
            est_secs = int(active_count * (timeout + 2) / concurrency)
            print(f"{Fore.CYAN}  checking {active_count} sites ({skipped} skipped), "
                  f"~{est_secs // 60}m{est_secs % 60:02d}s estimated{Style.RESET_ALL}", flush=True)

# Process ALL results as they complete (true concurrency for both modes).
# Each task returns (websites_names, param_websites, url, allow_redirects, (r, error_type, response_time)).
        for coro in asyncio.as_completed(async_tasks.keys()):
            try:
                websites_names, param_websites, url, allow_redirects, (r, error_type, response_time) = await coro
            except Exception:
                if color is True:
                    progress.update(task0, advance=1, refresh=refresh)
                continue
            if color is True:
                progress.update(task0, advance=1, refresh=refresh)
            if dic_snoop_full.get(websites_names, {}).get("exists") is not None:
                continue
            country_emojis = dic_snoop_full.get(websites_names, {}).get("flagcountry", "")
            country_code = dic_snoop_full.get(websites_names, {}).get("flagcountryklas", "")
            country_Emoj_Code = country_emojis if not WINDOWS else country_code

            try:
                await _process_result(r, error_type, response_time, websites_names, param_websites, url,
                                      allow_redirects, country_code, country_Emoj_Code, dic_snoop_full, li_time,
                                      norm, verbose, color, print_found_only, cert, concurrency_limit,
                                      reports, executor_req_save if reports else None, username, headers,
                                      progress if verbose else None, refresh, proxy=proxy)
            except Exception:
                pass

# Free resources.
        try:
            if 'executor_req_save' in locals(): executor_req_save.shutdown()
        except Exception:
            console.log(snoopbanner.err_all(err_="low"))
        return dic_snoop_full, None, nick


## Process a single site result (shared between quick and sequential modes).
async def _process_result(r, error_type, response_time, websites_names, param_websites, url,
                          allow_redirects, country_code, country_Emoj_Code, dic_snoop_full, li_time,
                          norm, verbose, color, print_found_only, cert, concurrency_limit,
                          reports, executor_req_save, username, headers, progress, refresh, proxy=None):

# Retry request on failed connection — but skip retries for geoblocked country zones
# (sites that require a local IP will always fail from outside that country).
    _geo_skip = country_code.strip() in ("RU", "CN", "UA", "KZ", "BY", "IR", "KP", "CU", "VN", "TH", "TR")
    if norm is False and r == "FakeNone" and not _geo_skip:
        head_duble = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                      'Accept-Language': 'en-US,en;q=0.9',
                      'Sec-Fetch-Mode': 'navigate',
                      'Sec-Fetch-Site': 'none',
                      'Sec-Fetch-User': '?1',
                      'Sec-GPC': '1',
                      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'}

        dic_binding["censors"] -= 1
        if color is True and print_found_only is False:
            print(f"{Style.RESET_ALL}{Fore.CYAN}[{Style.BRIGHT}{Fore.RED}-{Style.RESET_ALL}{Fore.CYAN}]"
                  f"{Style.DIM}{Fore.GREEN} ┌──└──reconnection{Style.RESET_ALL}")
        elif print_found_only is False:
            print("    ┌──└──reconnection")

        r, error_type, response_time = await fetch_site(
            url=url, method="get", headers=head_duble, allow_redirects=allow_redirects,
            timeout=3, cert=cert, concurrency_limit=concurrency_limit,
            websites_names=websites_names, error_type=param_websites.get("errorTypе"),
            norm=norm, print_found_only=print_found_only, verbose=verbose, color=color,
            country_code=f" ~{country_code}", proxy=proxy)

# Collecting failing location bad_zone.
    if r is None or r == "FakeNone" or r == "FakeStuck":
        dic_binding.get("badzone").append(country_code)

## Check, 4 methods; #1.
# Autodetect encoding for outdated specifics of requests lib/ISO-8859-1.
    try:
        if r is not None and r != "FakeNone" and r != "FakeStuck":
            if r.content and r.encoding == 'ISO-8859-1':
                r.encoding = char_detect(r.content[:4096]).get("encoding")
                if r.encoding is None: r.encoding = "utf-8"
            elif r.content and r.encoding != 'ISO-8859-1' and r.encoding.lower() != 'utf-8':
                if r.encoding == "cp-1251": r.encoding = "cp1251"
                elif r.encoding == "cp-1252": r.encoding = "cp1252"
                elif r.encoding == "windows1251": r.encoding = "windows-1251"
                elif r.encoding == "windows1252": r.encoding = "windows-1252"
    except Exception:
        r.encoding = "utf-8"

# Message responses (different locations).
    if error_type == "message":
        try:
            if param_websites.get("encoding") is not None:
                r.encoding = param_websites.get("encoding")
        except Exception:
            console.log(snoopbanner.err_all(err_="high"))
        error = param_websites.get("errorMsg")
        # BDfull_converted uses Latin 'errorMsg2', BDdemo used Cyrillic 'errоrMsg2' — check both.
        error2 = param_websites.get("errorMsg2") or param_websites.get("errоrMsg2")
        error3 = param_websites.get("errorMsg3") if param_websites.get("errorMsg3") is not None else "FakeNoneNoneNone"

        # Generic false-positive phrases — catch "not found" pages that return 200 OK.
        _generic_notfound = (
            "can\u2019t find that page", "can't find that page",
            "page not found", "page was not found", "the page you requested was not found",
            "user not found", "profile not found", "account not found",
            "does not exist", "doesn\u2019t exist", "doesn't exist",
            "no user named", "no such user", "could not be found",
            "is not registered", "no results found", "nothing here",
            "this page is no longer available", "404 not found",
            "isn\u2019t available right now", "isn't available right now",
            "content isn\u2019t available", "content isn't available",
            "was not found on this server", "the requested url was not found",
            "critical error", "error creating new session",  # phpBB errors
            "<title>404</title>", ">404<", "\"httpstatus\":404", '"statuscode":404',
            "no user by that name", "this account doesn\u2019t exist",
            "this account doesn't exist",
            "we couldn\u2019t find", "we couldn't find",
        )
        try:
            _body = r.text.lower() if r.text else ""
            _db_match = (error and error in r.text) or (error2 and error2 in r.text) or (error3 and error3 in r.text)
            _generic_match = any(phrase in _body for phrase in _generic_notfound)
            # JS SPA shells / broken sites return tiny HTML with no real content.
            _tiny_response = len(r.text) < 5000 and error_type == "message" and not _db_match
            # Raw PHP source, WAF challenges, or empty shells — not real profiles.
            _broken_page = (r.text.strip().startswith("<?php") or
                            "aliyun_waf" in _body or "captcha-bypass" in _body or
                            "challenge-platform" in _body)
            # Redirect-to-homepage detection: if the final URL is the site root/index, user doesn't exist.
            _redir_home = False
            try:
                _final_url = str(r.url).rstrip("/").lower()
                _main_url = param_websites.get("urlMain", "").rstrip("/").lower()
                if _main_url and (_final_url == _main_url or _final_url.endswith("/index.php")
                                  or _final_url.endswith("/index.html")):
                    _redir_home = True
            except Exception:
                pass

            if r.status_code > 200 and param_websites.get("ignore_status_code") is None \
                                                         or _db_match or _generic_match or _tiny_response or _broken_page or _redir_home:
                if not print_found_only and not norm:
                    print_not_found(websites_names, verbose, color)
                exists = "alas"
            else:
                if not norm:
                    print_found_country(websites_names, url, country_Emoj_Code, verbose, color)
                exists = "found!"
                if reports and executor_req_save:
                    executor_req_save.submit(sreports, url, headers, error_type, username, websites_names, r)
        except UnicodeEncodeError:
            exists = "alas"
## Check, 4 methods; #2.
    elif error_type == "redirection":
        if r.status_code == 301 or r.status_code == 303:
            # Follow the redirect and check if the final page is a "not found" page.
            try:
                _redir_body = r.text.lower() if r.text else ""
                _redir_notfound = ("not found", "was not found", "does not exist", "404",
                                   "no such user", "page not found", "user not found")
                _redir_fp = any(p in _redir_body for p in _redir_notfound) or len(r.content) < 600
            except Exception:
                _redir_fp = False

            if _redir_fp:
                if not print_found_only and not norm:
                    print_not_found(websites_names, verbose, color)
                exists = "alas"
            else:
                if not norm:
                    print_found_country(websites_names, url, country_Emoj_Code, verbose, color)
                exists = "found!"
                if reports and executor_req_save:
                    session_size = executor_req_save.submit(sreports, url, headers, error_type, username, websites_names, r)
        else:
            if not print_found_only and not norm:
                print_not_found(websites_names, verbose, color)
                session_size = len(str(r.content))
            exists = "alas"
## Check, 4 methods; #3.
    elif error_type == "status_code":
        if not r.status_code >= 300 or r.status_code < 200:
            # HEAD returned 200 — do a quick GET to verify body isn't a "not found" page.
            _sc_fp = False
            if r.status_code == 200:
                try:
                    verify_r = await a_request(cert=cert, method="get", url=url, headers=headers,
                                               allow_redirects=True, timeout=8,
                                               concurrency_limit=concurrency_limit, proxy=proxy)
                    _vb = verify_r.text.lower() if verify_r.text else ""
                    _vlen = len(verify_r.text)
                    _sc_phrases = ("<title>404</title>", ">404<", "\"404\"",
                                   "page not found", "page was not found",
                                   "\"httpstatus\":404", '"statuscode":404',
                                   "user not found", "profile not found", "does not exist",
                                   "this page could not be found", "critical error",
                                   "the page you requested was not found",
                                   "isn\u2019t available", "isn't available",
                                   "we couldn\u2019t find", "we couldn't find",
                                   "no such user", "account not found")
                    _phrase_match = any(p in _vb for p in _sc_phrases)
                    _broken = (verify_r.text.strip().startswith("<?php")
                               or _vlen < 3000
                               or "out for lunch" in _vb
                               or "under maintenance" in _vb
                               or "coming soon" in _vb
                               or verify_r.status_code >= 400)

                    # Username-presence heuristic: if the page body doesn't contain the
                    # searched username (case-insensitive), it's likely a generic/error page.
                    # Exclude very short usernames (<4 chars) to avoid false matches.
                    _uname_lower = username.lower() if username else ""
                    _has_username = (len(_uname_lower) >= 4 and _uname_lower in _vb) if _uname_lower else True

                    # OG-title verification: many JS-rendered sites (Twitch, etc) put the
                    # username in og:title for real users but encrypted/random text for fakes.
                    # If og:title exists and does NOT contain the username, it's a false positive.
                    _og_fp = False
                    if _has_username and len(_uname_lower) >= 4:
                        import re as _re
                        _og_match = _re.search(r'og:title["\']?\s*content=["\']([^"\']{5,})["\']', _vb)
                        if _og_match:
                            _og_text = _og_match.group(1)
                            if _uname_lower not in _og_text:
                                _og_fp = True

                    # Size-comparison heuristic: fetch known-good user's page, compare sizes.
                    # If target page is >10% smaller than known-good, likely a "not found" shell.
                    _size_fp = False
                    if _has_username and not _phrase_match and not _broken and not _og_fp:
                        _known_user = param_websites.get("usernameON", "")
                        if _known_user and _known_user.lower() != _uname_lower:
                            try:
                                _known_url = param_websites.get("url", "").format(_known_user)
                                _kr = await a_request(cert=cert, method="get", url=_known_url, headers=headers,
                                                      allow_redirects=True, timeout=8,
                                                      concurrency_limit=concurrency_limit, proxy=proxy)
                                _klen = len(_kr.text) if _kr.text else 0
                                if _klen > 0 and _vlen < _klen * 0.85:
                                    _size_fp = True
                            except Exception:
                                pass

                    _sc_fp = _phrase_match or _broken or (not _has_username) or _og_fp or _size_fp
                except Exception:
                    pass

            if _sc_fp:
                if not print_found_only and not norm:
                    print_not_found(websites_names, verbose, color)
                exists = "alas"
            else:
                if not norm:
                    print_found_country(websites_names, url, country_Emoj_Code, verbose, color)
                if reports and executor_req_save:
                    executor_req_save.submit(sreports, url, headers, error_type, username, websites_names, r)
                exists = "found!"
        else:
            if not print_found_only and not norm:
                print_not_found(websites_names, verbose, color)
            exists = "alas"
## Check, 4 methods; #4.
    elif error_type == "response_url":
        # Secondary check: even if status=200, look for "not found" text in body.
        _body4 = r.text.lower() if r.text else ""
        _generic_notfound4 = (
            "page not found", "user not found", "profile not found",
            "does not exist", "doesn\u2019t exist", "doesn't exist",
            "isn\u2019t available", "isn't available",
            "content isn\u2019t available", "content isn't available",
            "was not found on this server", "could not be found",
            "no results found", "404 not found", "<title>404</title>", ">404<",
            "critical error", "we couldn\u2019t find", "we couldn't find",
            "\"httpstatus\":404", '"statuscode":404',
        )
        _false_positive4 = (any(phrase in _body4 for phrase in _generic_notfound4)
                            or r.text.strip().startswith("<?php")
                            or (len(r.text) < 5000 and "aliyun_waf" in _body4))

        if 200 <= r.status_code < 300 and not _false_positive4:
            if not norm:
                print_found_country(websites_names, url, country_Emoj_Code, verbose, color)
            if reports and executor_req_save:
                executor_req_save.submit(sreports, url, headers, error_type, username, websites_names, r)
            exists = "found!"
        else:
            if not print_found_only and not norm:
                print_not_found(websites_names, verbose, color)
            exists = "alas"
## If all 4 methods failed.
    else:
        exists = "block"

## Attempting to get info from request, writing to csv.
    try:
        http_status = r.status_code
    except Exception:
        http_status = "fail" if r != "FakeStuck" else "stuck"

    if r is None or r == "FakeNone" or r == "FakeStuck":
        session_size = "Err"
    else:
        try:
            if reports is True:
                session_size = session_size if (error_type == 'redirection' and 'session_size' in dir()) else len(r.content)
            else:
                session_size = len(r.content)

            if session_size >= 555:
                session_size = round(session_size / 1024)
            elif session_size < 555:
                session_size = round((session_size / 1024), 2)
        except Exception:
            session_size = "Err"

## Count website response timings.
    ello_time = round(float(time.time() - TIME_START), 2)
    li_time.append(ello_time)
    dif_time = round(li_time[-1] - li_time[-2], 2)

## Option '-v'.
    if verbose is True:
        ram_free = mem_test()
        ram_free_color = "[cyan]" if ram_free > 100 else "[red]"
        R = "[red]" if dif_time > 2.7 and dif_time != ello_time else "[cyan]"
        R1 = "bold red" if dif_time > 2.7 and dif_time != ello_time else "bold blue"

        if session_size == 0 or session_size is None:
            Ssession_size = "Head"
        elif session_size == "Err":
            Ssession_size = "No"
        else:
            Ssession_size = str(session_size) + " Kb"

        if color is True:
            console.print(f"[cyan] [*{response_time} s] {R}[*{ello_time} s] [cyan][*{Ssession_size}]",
                          f"{ram_free_color}[*{ram_free} MB]")
            console.rule("", style=R1)
        else:
            console.print(f" [*{response_time} s T] >>", f"[*{ello_time} s t]", f"[*{Ssession_size}]",
                          f"[*{ram_free} MB]", highlight=False)
            console.rule(style="color")

## System information/CSV, updating dictionary with final results.
    if dif_time > 2.7 and dif_time != ello_time:
        dic_snoop_full.get(websites_names)['response_time_site_ms'] = str(dif_time)
    else:
        dic_snoop_full.get(websites_names)['response_time_site_ms'] = "no"
    dic_snoop_full.get(websites_names)['exists'] = exists
    dic_snoop_full.get(websites_names)['session_size'] = session_size
    dic_snoop_full.get(websites_names)['countryCSV'] = country_code
    dic_snoop_full.get(websites_names)['http_status'] = http_status
    dic_snoop_full.get(websites_names)['check_time_ms'] = response_time
    dic_snoop_full.get(websites_names)['response_time_ms'] = str(ello_time)


## Option '-t'.
def set_timeout(value):
    try:
        timeout = int(value)
    except Exception:
        raise argparse.ArgumentTypeError(f"\n\033[31;1mTimeout '{value}' Err,\033[0m \033[36m" + \
                                         f"specify time as an integer in seconds.\n \033[0m")
    if timeout <= 0:
        raise argparse.ArgumentTypeError(f"\n\033[31;1mTimeout '{value}' Err,\033[0m \033[36m" + \
                                         f"specify time > 0 sec.\n \033[0m")
    return timeout


## Option '-p'.
def speed_snoop(speed):
    try:
        speed = int(speed)
        if WINDOWS and (speed <= 0 or speed > 300):
            raise Exception("")
        elif speed <= 0 or speed > 300:
            raise Exception("")
        return speed
    except Exception:
        if not WINDOWS:
            raise argparse.ArgumentTypeError(f"\n\033[31;1mPool = '{speed}' error,\033[0m" + \
                                              " \033[36m valid range from '1' to '300' as an integer.\n \033[0m")
        else:
            snoopbanner.logo(text=format_txt(f" ! Pool value '{speed}' is out of range, " + \
                                             f"use '--pool/-p' with a value from 1 to 300.",
                                             k=True, m=True) + "\n\n", exit=False)
            sys.exit()


## Update Snoopyy source code (DISABLED for security).
def update_snoop():
    print("\n\033[31;1m[!] Update functionality has been DISABLED for security.\033[0m")
    print("\033[36mTo update manually, review changes at: https://github.com/snooppr/snoop\033[0m")
    sys.exit()


## Deleting reports.
def autoclean():
    print("""
\033[36mDo you really want to:\033[0m \033[31;1m
               _                _  
 _| _ |  _.|| |_) _ ._  _ .-_|_  ) 
(_|(/_| (_||| | \\(/_|_)(_)|  |_ o  
                    |             \033[0m""")

    while True:
        print("\033[36mChoose action:\033[0m [y/n] ", end='')
        del_all = input().lower()
        if del_all == "y":
            try:
                total_size = 0
                delfiles = []
                for total_file in glob.iglob(os.path.join(DIRPATH, "results") + '/**/*', recursive=True):
                    total_size += os.path.getsize(total_file)
                    if os.path.isfile(total_file): delfiles.append(total_file)

                rm = os.path.join(DIRPATH, "results") if 'source' in VERSION and not ANDROID else DIRPATH
                shutil.rmtree(rm, ignore_errors=True)

                print(f"\n\033[31;1mdeleted --> '{rm}'\033[0m\033[36m {len(delfiles)} files, " + \
                      f"{round(total_size/1024/1024, 2)} MB\033[0m")
            except Exception:
                console.log("[red]Error")
            break
        elif del_all == "n":
            print(Style.BRIGHT + Fore.RED + "\nAction cancelled\nExit")
            break
        else:
            print(Style.BRIGHT + Fore.RED + format_txt("{0}└──False, [Y/N] ?", k=True, m=True).format(' ' * 25))
    sys.exit()


## License/system information.
def version_info():
    with open('COPYRIGHT', 'r', encoding="utf8") as copyright:
        wl = 5 if WINDOWS and int(platform.win32_ver()[0]) < 10 else 4
        cop = copyright.read().replace('=' * 80, "~" * (os.get_terminal_size()[0] - wl)).strip()
        console.print(Panel(cop, title='[bold white]COPYRIGHT[/bold white]',
                            style=STL(color="white", bgcolor="blue"),
                            border_style=STL(color="white", bgcolor="blue")))

    if not ANDROID:
        cpu = 2 if psutil.cpu_count(logical=False) == None else psutil.cpu_count(logical=False)
        pool_ = str(cpu * 7 if WINDOWS else (os.cpu_count() * 40)) + \
                " concurrent requests (async)"

        if WINDOWS:
            ram_av = 800
        elif LINUX:
            ram_av = 3000 if os.cpu_count() > 4 else 700

        try:
            ram = int(psutil.virtual_memory().total / 1024 / 1024)
            ram_free = int(psutil.virtual_memory().available / 1024 / 1024)
            if ram_free < ram_av:
                ram_free = f"[bold red]{ram_free}[/bold red]"
            else:
                ram_free = f"[dim cyan]{ram_free}[/dim cyan]"
            os_ver = platform.platform(aliased=True, terse=0)
            threadS = f"thread(s) per core: [dim cyan]{int(psutil.cpu_count() / psutil.cpu_count(logical=False))}[/dim cyan]"
        except Exception:
            console.print(f"\n[bold red]Used Snoopy version: '{VERSION}' is developed for Android platform, " + \
                          f"but it seems something else is used 💻\n\nExit")
            sys.exit()
    elif ANDROID:
        pool_ = str(os.cpu_count() * 3) + f" process, (~300_MB_Ram = 25_Process = 4_Mbit/s)"

        try:
            ram = subprocess.check_output("free -m", shell=True, text=True).splitlines()[1].split()[1]
            ram_free = int(subprocess.check_output("free -m", shell=True, text=True).splitlines()[1].split()[-1])
            if ram_free <= 200:
                ram_free = f"[bold red]{ram_free}[/bold red]"
            else:
                ram_free = f"[dim cyan]{ram_free}[/dim cyan]"
            os_ver = 'Android ' + subprocess.check_output("getprop ro.build.version.release", shell=True, text=True).strip()
            threadS = f'model: [dim cyan]{subprocess.check_output("getprop ro.product.cpu.abi", shell=True, text=True).strip()}' + \
                      f'[/dim cyan]'
            T_v = dict(os.environ).get("TERMUX_VERSION")
        except Exception:
            T_v, ram_free, os_ver, threadS = "Not Termux?!", "?", "?", "?"
            ram = "please 'pkg install procps' ... |"

    termux = f"\nTermux: [dim cyan]{T_v}[/dim cyan]\n" if ANDROID else "\n"

    light_v = True if not 'snoopplugins' in globals() else False
    if PYTHON_3_8_PLUS:
        colorama_v = f", (colorama::{version_lib('colorama')})"
        rich_v = f", (rich::{version_lib('rich')})"
        urllib3_v = f", (urllib3::{version_lib('urllib3')})"
        psutil_v = f", (psutil::{version_lib('psutil')})"
        char_v = f", (charset_normalizer::{version_lib('charset_normalizer')})"
    else:
        urllib3_v = f", (urllib3::{requests.urllib3.__version__})"
        colorama_v = ""
        rich_v = ""
        psutil_v = f", (psutil::{psutil.__version__})"
        char_v = ""

    console.print('\n', Panel(f"Program: [blue bold]{'light ' if light_v else ''}[/blue bold][dim cyan]{VERSION}" + \
                                       f"{str(platform.architecture(executable=sys.executable, bits='', linkage=''))}[/dim cyan]\n" + \
                              f"OS: [dim cyan]{os_ver}[/dim cyan]" + termux + \
                              f"Locale: [dim cyan]{locale.setlocale(locale.LC_ALL)}[/dim cyan]\n" + \
                              f"Python: [dim cyan]{platform.python_version()}[/dim cyan]\n" + \
                              f"Key libraries: [dim cyan](aiohttp::{aiohttp.__version__}), (requests::{requests.__version__}), (certifi::{certifi.__version__}), " + \
                                             f"(speedtest::{snoopnetworktest.speedtest.__version__}){rich_v}{psutil_v}" + \
                                             f"{colorama_v}{urllib3_v}{char_v}[/dim cyan]\n" + \
                              f"CPU(s): [dim cyan]{os.cpu_count()},[/dim cyan] {threadS}\n" + \
                              f"Ram: [dim cyan]{ram} MB,[/dim cyan] available: {ram_free} [dim cyan]MB[/dim cyan]\n" + \
                              f"Recommended pool: [dim cyan]{pool_}[/dim cyan]",
                              title='[bold cyan]snoop info[/bold cyan]', style=STL(color="cyan")))
    sys.exit()


## Async event loop management.
_loop = None

def get_loop():
    """Get or create a persistent event loop for reusing aiohttp sessions across usernames."""
    global _loop
    if _loop is None or _loop.is_closed():
        # Use default ProactorEventLoop on Windows — no 512 FD limit.
        # SelectorEventLoop crashes with 'too many file descriptors in select()'.
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop


## MAIN.
def main_cli():
    web_path_copy()

    # NOTE: DB keys 'errorTypе' and 'errоrMsg2' use Cyrillic lookalike chars (legacy encoding).
    # Code lookups must match these exact key names from the database files.
    BDdemo = snoopbanner.DB('BDfull_converted')
    BDflag = snoopbanner.DB('BDfull_converted')
    flagBS = len(BDdemo)
    web_sites = f"{len(BDflag) // 100}00+"


# Assignment of Snoopy options.
    class SnoopArgumentParser(argparse.ArgumentParser):
        def __init__(self, *args, color=None, **kwargs): #'color' appeared by default in python3.14+, do not cause an error in python < 3.14.
            if color is not None:
                try:
                    argparse.ArgumentParser(color=color)
                    kwargs['color'] = color
                except Exception:
                    pass
            super().__init__(*args, **kwargs)

        def print_help(self, out_help = sys.stdout): #remove "--help" from help.
            del_str_help = self.format_help()
            del_str_help = re.sub(r'-h, --help.*\n|this.*|mess.*\n|opti.*\n|and.*\n|sho.*|exit.*', '', del_str_help)
            out_help.write(del_str_help)


    parser = SnoopArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, color=False,
                                 usage="python3 snoopy.py [search arguments...] nickname\nor\n" + \
                                       "usage: python3 snoopy.py [service arguments | plugins arguments]\n",
                                 epilog=(f"{Fore.CYAN}Snoop support: \033[36;1m{flagBS}\033[0m \033[36mWebsites\033[0m\n\n"))
# Service arguments.
    service_group = parser.add_argument_group('\033[36mservice arguments\033[0m')
    service_group.add_argument("--version", "-V", action="store_true",
                               help="\033[36mA\033[0mbout: print software version, snoop info and License.")
    service_group.add_argument("--list-all", "-l", action="store_true", dest="listing",
                               help="\033[36mP\033[0mrint detailed information about the Snoopy database.")
    service_group.add_argument("--autoclean", "-a", action="store_true", dest="autoclean", default=False,
                               help="\033[36mD\033[0melete all reports, clear cache.")
    service_group.add_argument("--update", "-U", action="store_true", dest="update",
                               help="\033[36mU\033[0mpdate Snoop.")
# Plugins arguments.
    plugins_group = parser.add_argument_group('\033[36mplugins arguments\033[0m')
    plugins_group.add_argument("--module", "-m", action="store_true", dest="module", default=False,
                               help="\033[36mO\033[0mSINT search: use various Snoopy plugins:: IP/GEO/YANDEX.")
# Search arguments.
    search_group = parser.add_argument_group('\033[36msearch arguments\033[0m')
    search_group.add_argument("username", nargs='*', metavar='nickname', action="store", default=None,
                              help="\033[36mN\033[0mickname of the sought user. \
                                    Searching for multiple names simultaneously is supported.\
                                    A nickname containing a space must be enclosed in quotes.")
    search_group.add_argument("--base", "-b <file>", dest="json_file", default="BDfull_converted", metavar='',
                              help="\033[36mS\033[0mpecify another DB for 'nickname' search (Locally).")
    search_group.add_argument("--web-base", "-w", action="store_true", dest="web", default=False,
                              help=f"\033[36mC\033[0monnect to dynamically updated web_DB for 'nickname' search \
                                    ({web_sites} sites).")
    search_group.add_argument("--site", "-s <site_name>", action="append", metavar='', dest="site_list", default=None,
                              help="\033[36mS\033[0mpecify site name from '--list-all' DB. Search 'nickname' on one specified resource, \
                                    it's acceptable to use the '-s' option multiple times.")
    search_group.add_argument("--exclude", "-e <country_code>", action="append", metavar='', dest="exclude_country", default=None,
                              help="\033[36mE\033[0mxclude the selected region from the search, it's acceptable to use the '-e' option \
                                    multiple times, e.g., '-e RU -e WR' exclude Russia and the World.")
    search_group.add_argument("--include", "-i <country_code>", action="append", metavar='', dest="one_level", default=None,
                              help="\033[36mI\033[0mnclude only the selected region in the search, \
                                    it's acceptable to use the '-i' option multiple times, e.g., '-i US -i UA' search in US and Ukraine.")
    search_group.add_argument("--time-out", "-t <digit>", action="store", metavar='', dest="timeout", type=set_timeout, default=8.9,
                              help="\033[36mS\033[0met max server response waiting time (seconds).\n"
                                   "Affects search duration and 'timeout errors' (default is 9 sec).")
    search_group.add_argument("--country-sort", "-c", action="store_true", dest="country", default=False,
                              help="\033[36mP\033[0mrint and save results by countries, not alphabetically.")
    search_group.add_argument("--no-func", "-n", action="store_true", dest="no_func", default=False,
                              help="\033[36m✓\033[0mMonochrome terminal, no colors in url \
                                    ✓Disable opening web browser\
                                    ✓Disable printing country flags\
                                    ✓Disable progress status and indication.")
    search_group.add_argument("--found-print", "-f", action="store_true", dest="print_found_only", default=False,
                              help="\033[36mP\033[0mrint only found accounts.")
    search_group.add_argument("--verbose", "-v", action="store_true", dest="verbose", default=False,
                              help="\033[36mD\033[0muring 'nickname' search print detailed verbalization.")
    search_group.add_argument("--userlist", "-u <file>", metavar='', action="store", dest="user", default=False,
                              help="\033[36mS\033[0mpecify a file with a list of users. Snoopy will intelligently process \
                                    the data and provide additional reports.")
    search_group.add_argument("--save-page", "-S", action="store_true", dest="reports", default=False,
                              help="\033[36mS\033[0mave found user pages into local html files,\
                                    slow mode.")
    search_group.add_argument("--proxy", "-x", metavar='', dest="proxy", default=None,
                              help="\033[36mR\033[0moute all requests through an HTTP proxy. "
                                   "Example: --proxy 127.0.0.1:8080 or --proxy http://user:pass@host:port")
    search_group.add_argument("--geo", "-g", action="store_true", dest="geo_skip", default=True,
                              help="\033[36mS\033[0mkip geolocked non-US sites (RU, CN, UA, etc) that require a local IP. "
                                   "Enabled by default. Use --no-geo to include all regions.")
    search_group.add_argument("--no-geo", action="store_false", dest="geo_skip",
                              help="\033[36mD\033[0misable geo-skip: include ALL regions including geolocked sites "
                                   "(RU, CN, UA, etc). Useful with VPN or proxy.")
    search_group.add_argument("--cert-on", "-C", default=False, action="store_true", dest="cert",
                              help=argparse.SUPPRESS)
    search_group.add_argument("--headers", "-H <User-Agent>", metavar='', dest="header_custom", nargs=1, default=None,
                              help=argparse.SUPPRESS)
    _val = "300 max concurrent requests."
    search_group.add_argument("--pool", "-p <digit>", metavar='', dest="speed", type=speed_snoop, default=False,
                              help=
                              f"""
                               \033[36mD\033[0misable auto-optimization and manually set search speed from 1 to {_val}
                               By default, high computer resource load is used in Quick mode, in other modes
                               moderate power consumption is used. Too low or high value can significantly
                               slow down the software. ~Estimated optimal value for this device is shown in 'snoop info',
                               parameter 'Recommended pool', option [--version/-V]. This option is proposed to be used
                               1) if the user has a multi-core PC and spare RAM or conversely a weak, rented VPS 
                               2) speeding up, slowing down search is recommended in tandem with [--found-print/-f'] option.
                               """)
    search_group.add_argument("--quick", "-q", action="store_true", dest="norm", default=False,
                              help=
                              """
                              \033[36mF\033[0mast and aggressive search mode.
                              Does not re-process failed resources, which speeds up the search,
                              but also slightly increases Bad_raw. Quick-mode adapts to PC power,
                              does not print intermediate results to CLI,
                              effective and intended for Snoopy.
                              """)

    args = parser.parse_args()

## Normalize proxy URL — auto-prepend http:// if user omits the scheme.
    if args.proxy:
        proxy = args.proxy.strip()
        if not proxy.startswith(("http://", "https://", "socks4://", "socks5://", "socks5h://")):
            proxy = f"http://{proxy}"
        args.proxy = proxy
        print(Fore.CYAN + format_txt(f"proxy enabled: {args.proxy}", k=True))

## Options '-csei' are mutually incompatible and quick-mode.
    if args.norm and 'full' in VERSION:
        print(Fore.CYAN + format_txt("activated option '-q': «fast search mode»", k=True))
        args.version, args.listing, args.timeout = False, False, 8
        args.update, args.module, args.autoclean = False, False, False

        options = []
        options.extend([args.site_list, args.country, args.verbose, args.print_found_only,
                        args.no_func, args.reports, args.cert, args.header_custom, args.speed])

        if any(options) or args.timeout != 8:
            snoopbanner.logo(text=format_txt("⛔️ with quick-mode ['-q'] only options ['-w', '-u', '-e', '-i'] are compatible",
                                             k=True, m=True))
    elif args.norm is False and args.listing is False and args.speed is False and 'full' in VERSION:
        if LINUX:
            print(Fore.CYAN + format_txt("default search '--' activated: «mode SNOOPninja»", k=True))

    if [args.country, bool(args.site_list), bool(args.exclude_country), bool(args.one_level)].count(True) >= 2:
        snoopbanner.logo(text=format_txt("⛔️ options ['-c', '-e' '-i', '-s'] are mutually incompatible", k=True, m=True))


## Option '-p'.
    if args.speed:
        print(Fore.CYAN + format_txt(f"activated option '-p': «max concurrent requests =" + \
                                     "{0}{1} {2}{3}{4}» {5}".format(Style.BRIGHT, Fore.CYAN, args.speed,
                                                                    Style.RESET_ALL, Fore.CYAN,
                                                                    Style.RESET_ALL), k=True))


## Option '-V' do not confuse with option '-v'.
    if args.version:
        version_info()


## Option '-a'.
    if args.autoclean:
        print(Fore.CYAN + format_txt("option '-a' activated: «deleting accumulated reports»", k=True))
        autoclean()


## Option '-H'.
    if args.header_custom:
        print(Fore.CYAN + format_txt("hidden option '-H' activated: «override user-agent(s)»", k=True), '\n',
              Fore.CYAN + format_txt("User-Agent: '{0}{1}{2}{3}{4}'".format(Style.BRIGHT, Fore.CYAN, ''.join(args.header_custom),
                                                                            Style.RESET_ALL, Fore.CYAN)), sep='')


## Option '-m'.
# Informative output.
    if args.module:
        if not 'snoopplugins' in globals():
            snoopbanner.logo(text=f"\nPLUGINS NOT AVAILABLE IN THIS BUILD\n$ " + \
                                  f"{os.path.basename(sys.argv[0])} --version/-V")
            sys.exit()
        print(Fore.CYAN + format_txt("option '-m' activated: «modular search»", k=True))

        def module():
            print(f"\n" + \
                  f"\033[36m╭Choose plugin or action from the list\033[0m\n" + \
                  f"\033[36m├──\033[0m\033[36;1m[1] --> GEO_IP/domain\033[0m\n" + \
                  f"\033[36m├──\033[0m\033[36;1m[2] --> Reverse Vgeocoder\033[0m\n" + \
                  f"\033[36m├──\033[0m\033[36;1m[3] --> \033[30;1mYandex_parser\033[0m\n" + \
                  f"\033[36m├──\033[0m\033[32;1m[help] --> Help\033[0m\n" + \
                  f"\033[36m└──\033[0m\033[31;1m[q] --> Exit\033[0m\n")

            mod = console.input("[cyan]input --->  [/cyan]")

            if mod == 'help':
                snoopbanner.help_module_1()
                return module()
            elif mod == '1':
                table = Table(title=Style.BRIGHT + Fore.GREEN + "Plugin selected" + Style.RESET_ALL, style="green", header_style='green')
                table.add_column("GEO_IP/domain_v0.6", style="green", justify="center")
                table.add_row('Getting info about target\'s ip/domain/url or via list of this data')
                console.print(table)

                snoopplugins.module1()
            elif mod == '2':
                table = Table(title=Style.BRIGHT + Fore.GREEN + "Plugin selected" + Style.RESET_ALL, style="green", header_style='green')
                table.add_column("Reverse Vgeocoder_v0.6", style="green", justify="center")
                table.add_row('Visualization of Geographic coordinates')
                console.print(table)

                snoopplugins.module2()
            elif mod == '3':
                table = Table(title=Style.BRIGHT + Fore.GREEN + "Plugin selected" + Style.RESET_ALL, style="green", header_style='green')
                table.add_column("Yandex_parser_v0.5", style="green", justify="center")
                table.add_row('Yandex parser: Ya_Reviews; Ya_Q; Ya_Market; Ya_Music; Ya_Zen; Ya_Disk; E-mail; Name.')
                console.print(table)

                snoopplugins.module3()
            elif mod == 'q':
                print(Style.BRIGHT + Fore.RED + "└──Exit")
                sys.exit()
            else:
                print(Style.BRIGHT + Fore.RED + "└──Invalid choice\n" + Style.RESET_ALL)
                return module()

        module()
        sys.exit()


## Options '-f' + "-v".
    if args.verbose is True and args.print_found_only is True:
        snoopbanner.logo(text=format_txt("⛔️ detailed verbalization mode [option '-v'] displays detailed info " + \
                                         "[option '-f'] is inappropriate", k=True, m=True))


## Option '-C'.
    if args.cert:
        print(Fore.CYAN + format_txt("hidden option '-C' activated: «certificate verification on servers enabled»", k=True))


## Option '-w'.
    if args.web:
        print(Fore.CYAN + format_txt("option '-w' activated: «connecting to external web_database»", k=True))


## Option '-S'.
    if args.reports:
        print(Fore.CYAN + format_txt("option '-S' activated: «save pages of found accounts»", k=True))


## Option '-n'.
    if args.no_func:
        print(Fore.CYAN + format_txt("option '-n' activated: «disabled:: colors; flags; browser; progress»", k=True))


## Option '-t'.
    if args.timeout != 8.9 and args.norm is False:
        print(Fore.CYAN + format_txt("option '-t' activated: wait for response from " + \
                                     "site up to{0}{1} {2} {3}{4}s.» {5}".format(Style.BRIGHT, Fore.CYAN, args.timeout,
                                                                               Style.RESET_ALL, Fore.CYAN,
                                                                               Style.RESET_ALL), k=True))
    if args.timeout == 8.9:
        args.timeout = 9


## Option '-f'.
    if args.print_found_only:
        print(Fore.CYAN + format_txt("option '-f' activated: «print only found accounts»", k=True))


## Option '-s'.
    if args.site_list:
        print(Fore.CYAN + format_txt(f"option '-s' activated: «search{Style.BRIGHT}{Fore.CYAN} {', '.join(args.username)}" + \
                                     f"{Style.RESET_ALL} {Fore.CYAN}on selected website(s)»", k=True), '\n',
              Fore.CYAN + format_txt("it is allowed to use option '-s' multiple times"), "\n",
              Fore.CYAN + format_txt("[option '-s'] is incompatible with [options '-c', '-e', '-i']"), sep="")


## Option '--list-all'.
    if args.listing:
        print(Fore.CYAN + format_txt("option '-l' activated: «detailed information about Snoopy DB»", k=True))
        print("\033[36m\nSort Snoopy DB by countries, by site name, or aggregated ?\n" + \
              "by countries —\033[0m 1 \033[36mby name —\033[0m 2 \033[36mall —\033[0m 3\n")

# Total output of countries (3!).
# Output for database listing.
        def sort_list_all(DB, fore, version, line=False):
            listfull = []
            if sortY == "3":
                if line:
                    console.rule("[cyan]Ok, print All Country", style="cyan bold")
                print("")
                li = [DB.get(con).get("country_klas") if WINDOWS else DB.get(con).get("country") for con in DB]
                cnt = str(Counter(li))
                try:
                    flag_str_sum = (cnt.split('{')[1]).replace("'", "").replace("}", "").replace(")", "")
                    all_ = str(len(DB))
                except Exception:
                    flag_str_sum = str("DB corrupted.")
                    all_ = "-1"
                table = Table(title=Style.BRIGHT + fore + version + Style.RESET_ALL, header_style='green', style="green")
                table.add_column("Geolocation: Num of websites", style="magenta", justify='full')
                table.add_column("All", style="cyan", justify='full')
                table.add_row(flag_str_sum, all_)
                console.print(table)

# Sort alphabetically (2!).
            elif sortY == "2":
                if line:
                    console.rule("[cyan]Ok, sorting alphabetically", style="cyan bold")
                if version == "__never_match__":
                    console.print('\n', Panel.fit("++Database++", title=version,
                    style=STL(color="cyan", bgcolor="red"), border_style=STL(color="cyan", bgcolor="red")))
                else:
                    console.print('\n', Panel.fit("++Database++", title=version,
                    style=STL(color="cyan"), border_style=STL(color="cyan")))
                i = 0
                sorted_dict_v_listtuple = sorted(DB.items(), key=lambda x: x[0].lower()) #sort dict by main key without case sensitivity
                datajson_sort = dict(sorted_dict_v_listtuple) #convert back to dict (sorted)

                for con in datajson_sort:
                    S = datajson_sort.get(con).get("country_klas") if WINDOWS else datajson_sort.get(con).get("country")
                    i += 1
                    listfull.append(f"\033[36;2m{i}.\033[0m \033[36m{S}  {con}")
                print("\n~~~~~~~~~~~~~~~~\n".join(listfull), "\n")

# Sort by countries (1!).
            elif sortY == "1":
                listwindows = []

                if line:
                    console.rule("[cyan]Ok, sorting by countries", style="cyan bold")

                for con in DB:
                    S = DB.get(con).get("country_klas") if WINDOWS else DB.get(con).get("country")
                    listwindows.append(f"{S}  {con}\n")

                if version == "__never_match__":
                    console.print('\n', Panel.fit("++Database++", title=version,
                    style=STL(color="cyan", bgcolor="red"), border_style=STL(color="cyan", bgcolor="red")))
                else:
                    console.print('\n', Panel.fit("++Database++",
                    title=version, style=STL(color="cyan"), border_style=STL(color="cyan")))

                for i in enumerate(sorted(listwindows, key=str.lower), 1):
                    listfull.append(f"\033[36;2m{i[0]}. \033[0m\033[36m{i[1]}")
                print("~~~~~~~~~~~~~~~~\n".join(listfull))

# Start function '--list-all'.
        while True:
            sortY = console.input("[cyan]Choose action: [/cyan]")
            if sortY == "1" or sortY == "2":
                sort_list_all(BDflag, Fore.GREEN, "database", line=True)
                sort_list_all(BDdemo, Fore.CYAN, "local database")
                break
            elif sortY == "3":
                sort_list_all(BDdemo, Fore.CYAN, "local database", line=True)
                sort_list_all(BDflag, Fore.GREEN, "database")
                break
# Action not selected '--list-all'.
            else:
                print(Style.BRIGHT + Fore.RED + format_txt("{0}└──False, [1/2/3] ?", k=True, m=True).format(' ' * 19))
        sys.exit()




## Option '-u' specify file-list of wanted users.
    if args.user:
        userlists, userlists_bad, duble, _duble, short_user = [], [], [], [], []
        flipped, d = {}, {}

        try:
            patchuserlist = ("{}".format(args.user))
            userfile = os.path.basename(patchuserlist)
            print(Fore.CYAN + format_txt("option '-u' activated: «search nickname(s) from file:: {0}{1}{2}{3}{4}» {5}",
                                         k=True).format(Style.BRIGHT, Fore.CYAN, userfile,
                                                        Style.RESET_ALL, Fore.CYAN, Style.RESET_ALL))

            with open(patchuserlist, "r", encoding="utf8") as u1:
                userlist = [(line[0], line[1].strip()) for line in enumerate(u1.read().replace("\ufeff", "").splitlines(), 1)]

                for num, user in userlist:
                    i_for = (num, user)
                    if check_invalid_username(user, symbol_bad_username=True, phone=True, dot=True, email=True) is False:
                        if all(i_for[1] != x[1] for x in userlists_bad):
                            userlists_bad.append(i_for)
                        else:
                            duble.append(i_for)
                        continue
                    elif user == "":
                        continue
                    elif len(user) <= 2:
                        short_user.append(i_for)
                        continue
                    else:
                        if all(i_for[1] != x[1] for x in userlists):
                            userlists.append(i_for)
                        else:
                            duble.append(i_for)

        except Exception as e:
            print(f"\n\033[31;1mCannot find_read file: '{userfile}'.\033[0m \033[36m\n " + \
                  f"\nPlease specify text file in encoding —\033[0m \033[36;1mutf-8.\033[0m\n" + \
                  f"\033[36mBy default, for instance, notepad in Windows OS saves text in encoding — ANSI.\033[0m\n" + \
                  f"\033[36mOpen your file '{userfile}' and change encoding [file ---> save as ---> utf-8].\n" + \
                  f"\033[36mOr remove unreadable special characters from the file.")
            sys.exit()

        console.rule("[green]Data analysis[/green]")

# good user.
        if userlists:
            _userlists = [f"[dim cyan]{num}.[/dim cyan] {v} [{k}]".replace("", "") for num, (k, v) in enumerate(userlists, 1)]
            console.print(Panel.fit("\n".join(_userlists).replace("%20", " "),
                                    title=f"[cyan]valid ({len(userlists)})[/cyan]", style=STL(color="cyan")))

# duplicate user.
        if duble:
            dict_duble = dict(duble)
            for key, value in dict_duble.items():
                if value not in flipped:
                    flipped[value] = [key]
                else:
                    flipped[value].append(key)

            for k,v in flipped.items():
                k = f"{k} ({len(v)})"
                d[k] = v

            for num, (k, v) in enumerate(d.items(), 1):
                str_1 = f"[dim yellow]{num}.[/dim yellow] {k} {v}".replace(" (", " ——> ").replace(")", " pcs.")
                str_2 = str_1.replace("——> ", "——> [bold yellow]").replace(" pcs.", " pcs.[/bold yellow]")
                _duble.append(str_2)

            print(f"\n\033[36mthe following nickname(s) from '\033[36;1m{userfile}\033[0m\033[36m' contain " + \
                  f"\033[33mduplicates\033[0m\033[36m and will be skipped:\033[0m")
            console.print(Panel.fit("\n".join(_duble), title=f"[yellow]duplicate ({len(duble)})[/yellow]",
                                    style=STL(color="yellow")))

# bad user.
        if userlists_bad:
            _userlists_bad = [f"[dim red]{num}.[/dim red] {v} [{k}]" for num, (k, v) in enumerate(userlists_bad, 1)]
            print(f"\n\033[36mthe following nickname(s) from '\033[36;1m{userfile}\033[0m\033[36m' contain " + \
                  f"\033[31;1mN/A-characters\033[0m\033[36m and will be skipped:\033[0m")
            console.print(Panel.fit("\n".join(_userlists_bad),
                                    title=f"[bold red]invalid_data ({len(userlists_bad)})[/bold red]",
                                    style=STL(color="bright_red")))

# Short user.
        if short_user:
            _short_user = [f"[dim red]{num}.[/dim red] {v} [{k}]" for num, (k, v) in enumerate(short_user, 1)]
            print(f"\n\033[36mthe following nickname(s) from '\033[36;1m{userfile}\033[0m\033[36m'\033[0m " + \
                  f"\033[31;1mshorter than 3 characters\033[0m\033[36m and will be skipped:\033[0m")
            console.print(Panel.fit("\n".join(_short_user).replace("%20", " "),
                                    title=f"[bold red]short nickname ({len(short_user)})[/bold red]",
                                    style=STL(color="bright_red")))

# Saving bad_nickname(s) in a separate txt file.
        if short_user or userlists_bad:
            for bad_user1, bad_user2 in itertools.zip_longest(short_user, userlists_bad):
                with open (f"{DIRPATH}/results/nicknames/bad_nicknames.txt", "a", encoding="utf-8") as bad_nick:
                    if bad_user1:
                        bad_nick.write(f"{time.strftime('%Y-%m-%d_%H:%M:%S', TIME_DATE)}  <FILE: {userfile}>  '{bad_user1[1]}'\n")
                    if bad_user2:
                        bad_nick.write(f"{time.strftime('%Y-%m-%d_%H:%M:%S', TIME_DATE)}  <FILE: {userfile}>  '{bad_user2[1]}'\n")


        user_list = [i[1] for i in userlists]

        del userlists, duble, userlists_bad, _duble, short_user, flipped, d

        if bool(user_list) is False:
            print("\n", Style.BRIGHT + Fore.RED + format_txt("⛔️ File '{0}' does not contain any valid nickname".format(userfile),
                                                             k=True, m=True), "\n\n\033[31;1mExit\033[0m\n", sep="")
            sys.exit()


## Checking rest (incl. repeat) options.
## Option '--update' update Snoop.
    if args.update:
        print(Fore.CYAN + format_txt("option '-U' activated: «update snoop»", k=True))
        update_snoop()


## Option '-w'.
    if args.web:
        print("")
        snoopbanner.logo("Function '-w' (web database) is not available in this build...",
                         color="\033[37m\033[44m", exit=False)


## Option '-b'. Check if alternative database exists, otherwise default.
    if not os.path.exists(str(args.json_file)):
        print(f"\n\033[31;1mError! Invalid file path: '{str(args.json_file)}'.\033[0m")
        sys.exit()


## Option '-c'. Sorting by countries.
    if args.country is True and args.web is False:
        print(Fore.CYAN + format_txt("option '-c' activated: «sorting/saving results by countries»", k=True))
        country_sites = sorted(BDdemo, key=lambda k: ("country" not in k, BDdemo[k].get("country", sys.maxsize)))
        sort_web_BDdemo_new = {}
        for site in country_sites:
            sort_web_BDdemo_new[site] = BDdemo.get(site)


## Function for options '-ei'.
    def one_exl(one_exl_, bool_):
        lap = []
        bd_flag = []

        for k, v in BDdemo.items():
            bd_flag.append(v.get('country_klas').lower())
            if all(item.lower() != v.get('country_klas').lower() for item in one_exl_) is bool_:
                BDdemo_new[k] = v

        enter_coun_u = [x.lower() for x in one_exl_]
        lap = list(set(bd_flag) & set(enter_coun_u))
        diff_list = list(set(enter_coun_u) - set(bd_flag)) #output unique elem from enter_coun_u else set(enter_coun_u)^set(bd_flag)

        if bool(BDdemo_new) is False:
            print('\n', format_txt(f"⛔️ \033[31;1m[{str(diff_list).strip('[]')}] please check input, " + \
                                   f"because all specified regions for search are invalid.\033[0m", k=True, m=True), sep='')
            sys.exit()
# Return correct and bad lists of user input in CLI.
        return lap, diff_list


## If options '-sei' are not specified, we use DB as is.
    BDdemo_new = {}
    if args.site_list is None and args.exclude_country is None and args.one_level is None:
        BDdemo_new = BDdemo


## Option '-s'.
    elif args.site_list is not None:
# Make sure sites exist in database, create shortened site database for verification.
        for site in args.site_list:
            for site_yes in BDdemo:
                if site.lower() == site_yes.lower():
                    BDdemo_new[site_yes] = BDdemo[site_yes] #select found sites from DB to dict
            try:
                diff_k_bd = set(BDflag) ^ set(BDdemo)
            except Exception:
                snoopbanner.logo(text="\nnickname(s) not specified")
            for site_yes_full_diff in diff_k_bd:
                if site.lower() == site_yes_full_diff.lower(): #if site (-s) in Full DB
                    print(format_txt("{0}⛔️ skip:{2} {3}site '{11}{1}{12}{13}' {6}not in local DB{14}",
                                     k=True, m=True).format(Style.BRIGHT + Fore.RED, site_yes_full_diff,
                                                            Style.RESET_ALL, Fore.CYAN, Style.BRIGHT + Fore.CYAN,
                                                            Style.RESET_ALL, Fore.CYAN, Style.RESET_ALL,
                                                            Style.BRIGHT + Fore.YELLOW, Style.RESET_ALL,
                                                            Fore.CYAN, Style.BRIGHT + Fore.BLACK,
                                                            Style.RESET_ALL, Fore.CYAN, Style.RESET_ALL))

            if not any(site.lower() == site_yes_full.lower() for site_yes_full in BDflag): #if no match by site
                print(format_txt("{0}⛔️ skip:{1} {2}desired site is missing in Snoopy DB:: '" + \
                                 "{3}{4}{5}' {6}", k=True, m=True).format(Style.BRIGHT + Fore.RED, Style.RESET_ALL, Fore.CYAN,
                                                                          Style.BRIGHT + Fore.RED, site,
                                                                          Style.RESET_ALL + Fore.CYAN, Style.RESET_ALL))
# Cancel search if no matches by DB and '-s'.
        if not BDdemo_new:
            sys.exit()


## Option '-e'.
# Create shortened database of site(s) for checking.
# Create and add sites to new DB whose arguments (-e) != country letter codes (country_klas).
    elif args.exclude_country is not None:
        lap, diff_list = one_exl(one_exl_=args.exclude_country, bool_=True)
        str_e = "option '-e' activated: «exclude selected regions from search»::" + \
                                     "{0} {1} {2} {3} {4} {5}".format(Fore.CYAN, str(lap).strip('[]').upper(),
                                                                      Style.RESET_ALL, Style.BRIGHT + Fore.RED,
                                                                      str(diff_list).strip('[]'), Style.RESET_ALL)
        print(Fore.CYAN + format_txt(str_e, k=True), '\n',
              Fore.CYAN + format_txt("it is allowed to use option '-e' multiple times", m=True), '\n',
              Fore.CYAN + format_txt("[option '-e'] is incompatible with [options '-s', '-c', '-i']", m=True), sep='')


## Option '-i'.
# Create shortened database of site(s) for checking.
# Create and add sites to new DB whose arguments (-e) != country letter codes (country_klas).
    elif args.one_level is not None:
        lap, diff_list = one_exl(one_exl_=args.one_level, bool_=False)
        str_i = "option '-i' activated: «include only selected regions in search»::" + \
                                     "{0} {1} {2} {3} {4} {5}".format(Fore.CYAN, str(lap).strip('[]').upper(),
                                                                      Style.RESET_ALL, Style.BRIGHT + Fore.RED,
                                                                      str(diff_list).strip('[]'), Style.RESET_ALL)
        print(Fore.CYAN + format_txt(str_i, k=True), '\n',
              Fore.CYAN + format_txt("it is allowed to use option '-i' multiple times", m=True), '\n',
              Fore.CYAN + format_txt("[option '-i'] is incompatible with [options '-s', '-c', '-e']", m=True), sep='')


## Geo-skip: filter out geolocked non-US sites by default.
    _GEO_BLOCKED = {"RU", "CN", "UA", "KZ", "BY", "IR", "KP", "CU", "VN"}
    if args.geo_skip and BDdemo_new:
        _before = len(BDdemo_new)
        BDdemo_new = {k: v for k, v in BDdemo_new.items()
                      if v.get("country_klas", "US") not in _GEO_BLOCKED}
        _skipped = _before - len(BDdemo_new)
        if _skipped > 0:
            print(f"{Fore.CYAN}Geo-skip: excluded {Style.BRIGHT}{_skipped}{Style.RESET_ALL}{Fore.CYAN} "
                  f"geolocked sites (RU/CN/UA/etc). Use --no-geo to include them.{Style.RESET_ALL}")

## Nickname not specified or conflicting options.
    if bool(args.username) is False and bool(args.user) is False:
        snoopbanner.logo(text="\nparameters or nickname(s) not specified")
    if bool(args.username) is True and bool(args.user) is True:
        print('\n⛔️' + format_txt("\033[31;1m choose nickname(s) for search from file or specify in CLI,\n" + \
              "but not both nickname(s): from file and CLI together", k=True, m=True), "\033[31;1m\n\nExit\033[0m")
        sys.exit()


## Option '-v'.
    if args.verbose and bool(args.username) or args.verbose and bool(user_list):
        print(Fore.CYAN + format_txt("option '-v' activated: «detailed verbalization in CLI»\n", k=True))
        snoopnetworktest.nettest()


## Option '-w' active/inactive.
    try:
        if args.web is False:
            _DB = f"_[_{len(BDdemo_new)}_]" if len(BDdemo_new) != len(BDdemo) else ""
            print(f"\n{Fore.CYAN}local database loaded: {Style.BRIGHT}{Fore.CYAN}{len(BDdemo)}_Websites{_DB}{Style.RESET_ALL}")
    except Exception:
        print("\033[31;1mInvalid loading database.\033[0m")


## Checking lib versions: 'requests/urllib3'.
    warning_lib()


## Circling user's.
    def starts(SQ):
# Choosing correct encoding for CSV considering OS/geolocation.
        try:
            if "ru" in os.getenv("LANG", ""): #if os.environ.get('LANG') is not None and 'ru' in os.environ.get('LANG'):
                rus_unix = True
            else:
                rus_unix = False
            if WINDOWS and "1251" in locale.setlocale(locale.LC_ALL):
                rus_windows = True
            else:
                rus_windows = False
        except Exception:
            rus_unix = False
            rus_windows = False

        kef_user = 0
        ungzip, ungzip_all, find_url_lst, el = [], [], [], []
        exl = "/".join(lap).upper() if args.exclude_country is not None else "no" #excl.regions_valid
        one = "/".join(lap).upper() if args.one_level is not None else "no" #incl.regions_valid
        for username in SQ:
            kef_user += 1
            sort_sites = sort_web_BDdemo_new if args.country is True else BDdemo_new

            # Global timeout: per-site timeout × 3 gives plenty of headroom for retries + processing.
            _global_timeout = max(300, args.timeout * len(sort_sites) // max(1, args.speed or 40) * 3)
            try:
                FULL, hardware, nick = get_loop().run_until_complete(asyncio.wait_for(
                    snoop(username, sort_sites, country=args.country, user=args.user, verbose=args.verbose,
                          cert=args.cert, norm=args.norm, reports=args.reports, lst_username=args.username,
                          print_found_only=args.print_found_only, timeout=args.timeout,
                          color=not args.no_func, header_custom=args.header_custom, speed=args.speed,
                      proxy=args.proxy),
                    timeout=_global_timeout))
            except asyncio.TimeoutError:
                print(f"\n{Fore.RED}Search timed out after {_global_timeout}s — partial results saved.{Style.RESET_ALL}")
                FULL, hardware, nick = {}, None, username

            exists_counter = 0

            if bool(FULL) is False:
                kef_user -= 1
                cli_file = " <CLI>       " if args.user is False else f" <FILE: {userfile}>"
                with open (f"{DIRPATH}/results/nicknames/bad_nicknames.txt", "a", encoding="utf-8") as bad_nick:
                    bad_nick.write(f"{time.strftime('%Y-%m-%d_%H:%M:%S', TIME_DATE)} {cli_file}  '{username}'\n")

                continue


## Writing to txt report.
            file_txt = open(f"{DIRPATH}/results/nicknames/txt/{username}.txt", "w", encoding="utf-8")

            file_txt.write(f"GEO | RESOURCE {' ' * 16} | URL" + "\n\n")

            for website_name in FULL:
                dictionary = FULL[website_name]
                if type(dictionary.get("session_size")) != str:
                    ungzip.append(dictionary.get("session_size")), ungzip_all.append(dictionary.get("session_size"))
                if dictionary.get("exists") == "found!":
                    exists_counter += 1
                    find_url_lst.append(exists_counter)
                    txt_str = f"{dictionary['flagcountryklas']}  |  {(website_name)}"
                    kef_indent = 30 - (len(txt_str))
                    file_txt.write(f"{txt_str} {' ' * kef_indent} |  {dictionary['url_user']}\n")
# Session size personal and total, except CSV.
            try:
                sess_size = round(sum(ungzip) / 1024, 2) #in MB
                s_size_all = round(sum(ungzip_all) / 1024, 2) #in MB
            except Exception:
                sess_size = 0.000_000_000_1
                s_size_all = "Err"

            timefinish = time.time() - TIME_START - sum(el)
            el.append(timefinish)
            time_all = str(round(time.time() - TIME_START))
            

            file_txt.write("\n" f"Requested object: <{nick}> found: {exists_counter} time(s).")
            file_txt.write("\n" f"Session: {str(round(timefinish))}sec {str(sess_size)}MB.")
            file_txt.write("\n" f"Snoopy DB: {flagBS} Websites.")
            file_txt.write("\n" f"Excluded regions: {exl}.")
            file_txt.write("\n" f"Specific regions selected: {one}.")
            file_txt.write("\n" f"Updated: {time.strftime('%Y-%m-%d_%H:%M:%S', TIME_DATE)}.\n")
            file_txt.write("\n" f"©2020-{time.localtime().tm_year} «Snoopy».")
            file_txt.close()


## Writing to html report.
            if ANDROID and re.search("[^\\W \\da-zA-Z]+", nick):
                username = f"nickname_{time.strftime('%Y-%m-%d_%H-%M-%S')}"

            file_html = open(f"{DIRPATH}/results/nicknames/html/{username}.html", "w", encoding="utf-8")

            path_ = DIRPATH if not ANDROID else "/storage/emulated/0/snoop"
# Load web assets for inline embedding (self-contained HTML).
            web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
            try:
                with open(os.path.join(web_dir, "style.css"), "r", encoding="utf-8") as _f:
                    _inline_css = _f.read()
            except Exception:
                _inline_css = ""
            try:
                with open(os.path.join(web_dir, "particles.js"), "r", encoding="utf-8") as _f:
                    _inline_particles_js = _f.read()
            except Exception:
                _inline_particles_js = ""
            try:
                with open(os.path.join(web_dir, "app.js"), "r", encoding="utf-8") as _f:
                    _inline_app_js = _f.read()
            except Exception:
                _inline_app_js = ""

            file_html.write("<!DOCTYPE html>\n<html lang='en'>\n\n<head>\n<title>◕ Snoopy HTML-report</title>\n" + \
                            "<meta charset='utf-8'>\n<meta name='viewport' content='width=device-width, initial-scale=1.0'>\n" + \
                            "<style>\n" + _inline_css + "\n</style>\n</head>\n\n<body>\n\n" + \
                            "<div id='particles-js'></div>\n\n" + \
                            "<div class='container'>\n" + \
                            "<header class='glass-card header-card'>\n" + \
                            "<h1 class='logo'>Snoopy</h1>\n" + \
                            "<p class='subtitle'>OSINT Username Search Report</p>\n" + \
                            "</header>\n\n")
            file_html.write("<div class='glass-card report-card'>\n" + \
                            "<div class='card-header'><h2>Results</h2>" + \
                            "<button onclick='sortList()'>Sort by countries ↓↑</button></div>\n" + \
                            "<ol id='id777'>\n")

            li = []
            for website_name in FULL:
                dictionary = FULL[website_name]
                flag_sum = dictionary["flagcountry"]
                if dictionary.get("exists") == "found!":
                    li.append(flag_sum)
                    file_html.write("<li><span class='result-flag'>" + dictionary["flagcountry"] + "</span>" + \
                                    "<a class='result-link' target='_blank' href='" + dictionary["url_user"] + "'>" + \
                                    (website_name) + "</a></li>\n")
            try:
                cnt = []
                for k, v in sorted(Counter(li).items(), key=lambda x: x[1], reverse=True):
                    cnt.append(f"【{k} ⇔ {v}】")
                flag_str_sum = "; ".join(cnt)
            except Exception:
                flag_str_sum = "-1"

            file_html.write("</ol>\n</div>\n\n")
            file_html.write("<div class='glass-card meta-card'>\n" + \
                            "<div class='card-header'><h2>Session Info</h2></div>\n" + \
                            "<div class='meta-grid'>\n")
            file_html.write("<div class='meta-item'><span class='meta-label'>Target</span><span class='meta-value'>" + str(nick) + "</span></div>\n")
            file_html.write("<div class='meta-item'><span class='meta-label'>Found</span><span class='meta-value accent'>" + str(exists_counter) + " accounts</span></div>\n")
            file_html.write("<div class='meta-item'><span class='meta-label'>Duration</span><span class='meta-value'>" + str(round(timefinish)) + "s</span></div>\n")
            file_html.write("<div class='meta-item'><span class='meta-label'>Data</span><span class='meta-value'>" + str(sess_size) + " MB</span></div>\n")
            file_html.write("<div class='meta-item'><span class='meta-label'>Database</span><span class='meta-value'>" + str(flagBS) + " sites</span></div>\n")
            file_html.write("<div class='meta-item'><span class='meta-label'>Excluded</span><span class='meta-value'>" + str(exl) + "</span></div>\n")
            file_html.write("<div class='meta-item'><span class='meta-label'>Regions</span><span class='meta-value'>" + str(one) + "</span></div>\n")
            file_html.write("<div class='meta-item'><span class='meta-label'>Updated</span><span class='meta-value'>" + time.strftime("%Y-%m-%d %H:%M:%S", TIME_DATE) + "</span></div>\n")
            file_html.write("</div>\n<div class='geo-bar'>" + flag_str_sum + "</div>\n</div>\n\n")
            file_html.write("""
<div class='glass-card footer-card'>
<div class='footer-links'>
<a target='_blank' href='https://github.com/snooppr/snoop' class='footer-btn'>Source Code</a>
<a target='_blank' href='https://drive.google.com/file/d/12DzAQMgTcgeG-zJrfDxpUbFjlXcBq5ih/view' class='footer-btn'>Documentation</a>
</div>
</div>

""" + f"""<p class='copyright'>Report generated by Snoopy &copy; 2020-{time.localtime().tm_year}</p>
</div>

<script>
function sortList() {{
    var list = document.getElementById('id777');
    if (!list) return;
    var items = Array.from(list.getElementsByTagName('LI'));
    if (items.length === 0) return;
    var itemsWithKeys = items.map(function(item) {{
        var sortElement = item.querySelector('.result-link');
        var sortKey = sortElement ? sortElement.innerText : '';
        return {{ element: item, key: sortKey }};
    }});
    itemsWithKeys.sort(function(a, b) {{
        return a.key.localeCompare(b.key, 'en', {{ sensitivity: 'base' }});
    }});
    var fragment = document.createDocumentFragment();
    itemsWithKeys.forEach(function(itemData) {{
        fragment.appendChild(itemData.element);
    }});
    list.innerHTML = '';
    list.appendChild(fragment);
}}
</script>
<script>
""" + _inline_particles_js + """
</script>
<script>
""" + _inline_app_js + """
</script>
</body>
</html>""")
            file_html.close()


## Writing to csv report.
            file_csv = open(f"{DIRPATH}/results/nicknames/csv/{username}.csv", "w", newline='', encoding="utf-8-sig")

            usernamCSV = re.sub(" ", "_", nick)

            try:
                err_all = dic_binding.get('censors') / kef_user #err_connection_all
                flagBS_err = round(err_all * 100 / (len(BDdemo_new) - len(dic_binding.get("badraw"))), 2)
            except ZeroDivisionError:
                flagBS_err = 0

            try:
                bad_zone = f"~{Counter(dic_binding.get('badzone')).most_common(2)[0][0]}/" + \
                           f"{Counter(dic_binding.get('badzone')).most_common(2)[1][0]}"
            except IndexError:
                try:
                    bad_zone = f"~{Counter(dic_binding.get('badzone')).most_common(2)[0][0]}"
                except IndexError:
                    bad_zone = "ERR"

            writer = csv.writer(file_csv, delimiter=';' if rus_windows else ",")
            writer.writerow(['Resource', 'Geo', 'Url', 'Url_username', 'Status', 'Http_code',
                             'Deceleration/s', 'Response/s', 'Time/s', 'Session/kB'])

            for site in FULL:
                if FULL[site]['session_size'] == 0:
                    Ssession = "Head"
                elif type(FULL[site]['session_size']) != str:
                    Ssession = str(FULL.get(site).get("session_size")).replace('.', locale.localeconv()['decimal_point'])
                else:
                    Ssession = "Bad"

                writer.writerow([site, FULL[site]['countryCSV'], FULL[site]['url_main'], FULL[site]['url_user'],
                                 FULL[site]['exists'], FULL[site]['http_status'],
                                 FULL[site]['response_time_site_ms'].replace('.', locale.localeconv()['decimal_point']),
                                 FULL[site]['check_time_ms'].replace('.', locale.localeconv()['decimal_point']),
                                 FULL[site]['response_time_ms'].replace('.', locale.localeconv()['decimal_point']),
                                 Ssession])

            writer.writerow(['«' + '-'*35, '-'*4, '-'*35, '-'*56, '-'*13, '-'*17, '-'*37, '-'*17, '-'*28, '-'*15 + '»'])
            writer.writerow([f'DB={flagBS}_Websites'])
            writer.writerow([f"Nick={usernamCSV}"])
            writer.writerow('')
            writer.writerow([f'Excluded_regions={exl}'])
            writer.writerow([f'Specific_regions_selected={one}'])
            writer.writerow([f"Bad_raw:_{flagBS_err}%_DB,_bad_zone_{bad_zone}" if flagBS_err >= 2 else ''])
            writer.writerow('')
            writer.writerow(['Date'])
            writer.writerow([time.strftime("%Y-%m-%d_%H:%M:%S", TIME_DATE)])
            writer.writerow([f'©2020-{time.localtime().tm_year} «Snoopy».'])

            file_csv.close()

            ungzip.clear()
            dic_binding.get("badraw").clear()


## Final output in CLI.
        if bool(FULL) is True:
            direct_results = os.path.join(DIRPATH, "results", "nicknames", "*")
            print(f"{Fore.CYAN}├─Results:{Style.RESET_ALL} found --> {len(find_url_lst)} " + \
                  f"url (session: {time_all}_sec__{s_size_all}_MB)")
            print(f"{Fore.CYAN}├──Saved in:{Style.RESET_ALL} {direct_results}")

            if flagBS_err >= 2: #perc_%
                bad_raw(flagBS_err, bad_zone, nick, [args.exclude_country, args.one_level, args.site_list])
            else:
                print(f"{Fore.CYAN}└───Search date:{Style.RESET_ALL} {time.strftime('%Y-%m-%d__%H:%M:%S', TIME_DATE)}\n")



## Open / do not open the browser with the search results.
            if args.no_func is False and exists_counter >= 1:
                try:
                    if not ANDROID:
                        try:
                            webbrowser.open(f"file://{DIRPATH}/results/nicknames/html/{username}.html")
                        except Exception:
                            console.print("[bold red]Impossible to open web browser, OS problems.")
                    else:
                        install_service = Style.DIM + Fore.CYAN + \
                                              "\nFor auto-opening results in an external browser on Android, the user " + \
                                              "must have the environment configured, code:" + Style.RESET_ALL + Fore.CYAN + \
                                              "\ncd && pkg install termux-tools; echo 'allow-external-apps=true' >>" + \
                                              ".termux/termux.properties" + Style.RESET_ALL + \
                                              Style.DIM + Fore.CYAN + "\n\nAnd restart the terminal."

                        termux_sv = False
                        if os.path.exists("/data/data/com.termux/files/usr/bin/termux-open"):
                            with open("/data/data/com.termux/files/home/.termux/termux.properties", "r", encoding="utf-8") as f:
                                for line in f:
                                    if ("allow-external-apps" in line and "#" not in line) and line.split("=")[1]\
                                                                                                   .strip()\
                                                                                                   .lower() == "true":
                                        termux_sv = True

                            if termux_sv is True:
                                subprocess.run(f"termux-open {DIRPATH}/results/nicknames/html/{username}.html", shell=True)
                            else:
                                print(install_service)

                        else:
                            print(install_service)
                except Exception:
                    print(f"\n\033[31;1mFailed to open results\033[0m")
        # Clean up async session after all usernames processed.
        try:
            get_loop().run_until_complete(close_aio_session())
            get_loop().close()
        except Exception:
            pass


## Search by selected users: either from CLI or from file.
    starts(args.username) if args.user is False else starts(user_list)


## Arbeiten...
if __name__ == '__main__':
    try:
        main_cli()
    except KeyboardInterrupt:
        console.print(f"\n[bold red]Interrupt [italic](Ctrl + c)[/italic][/bold red]")
        # Force-close aiohttp connector on interrupt.
        if _aio_connector is not None:
            try:
                _aio_connector.close()
            except Exception:
                pass
        sys.exit(1)
    except Exception as fatal_err:
        # Catch-all: print error and wait so user can read it before window closes.
        print(f"\n\033[31;1mFatal error: {fatal_err}\033[0m", flush=True)
        import traceback
        traceback.print_exc()
        if _aio_connector is not None:
            try:
                _aio_connector.close()
            except Exception:
                pass
        if WINDOWS:
            input("\nPress Enter to exit...")
        sys.exit(1)
