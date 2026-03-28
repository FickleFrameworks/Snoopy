#! /usr/bin/env python3
# Copyright (c) 2020 Snoopy <snoopproject@protonmail.com>
"Text_banner_logo_help"

import base64
import json
import locale
import platform
import sys
import time

from colorama import Fore, Style, init
from rich.panel import Panel
from rich.console import Console

locale.setlocale(locale.LC_ALL, '')
init(autoreset=True)
console = Console()


## Error logging.
def err_all(err_="low"):
    if err_ == "high":
        return "⚠️ [bold red]Attention! Critical error, please report it to the developer.\nhttps://github.com/snooppr/snoop/issues[/bold red]"
    elif err_ == "low":
        return "⚠️ [bold yellow]Error[/bold yellow]"


## DB.
def DB(db_base):
    try:
        with open(db_base, "r", encoding="utf8") as f_r:
            db = f_r.read()
            db = db.encode("UTF-8")
            db = base64.b64decode(db)
            db = db[::-1]
            db = base64.b64decode(db)
            trinity = json.loads(db.decode("UTF-8"))
            return trinity
    except Exception:
        print(Style.BRIGHT + Fore.RED + "Oops, something went wrong..." + Style.RESET_ALL)
        sys.exit()


## Logo.
def logo(text, color="\033[31;1m", exit=True):
    if sys.platform != 'win32' or (sys.platform == 'win32' and int(platform.version().split('.')[2]) >= 19045):
        with console.screen():
            console.print("""[cyan]
  ____
 / ___|_ __   ___   ___  _ __
 \\___ \\| '_ \\ / _ \\ / _ \\| '_ \\
  ___) | | | | (_) | (_) | |_) |
 |____/|_| |_|\\___/ \\___/| .__/
                          |_|
""")
            time.sleep(1.4)
    for i in text:
        time.sleep(0.04)
        print(f"{color}{i}", end='', flush=True)
    if exit:
        print("\033[31;1m\n\nExit")
        sys.exit()


# snoopy.py Help Modules 'if mod == 'help'.
def help_module_1():
    print("""\033[32;1m└──[Help]\033[0m

\033[32;1m======================
| Plugin GEO_IP/domain |
======================\033[0m \033[32m\n
1) Implements online single search of a target by IP/url/domain and provides analytical information: IPv4/v6; GEO-coordinates/link; location.
(Light limited search).

2) Implements online target search by list of data: and provides analytical and visualized information: IPv4/v6; GEO-coordinates/links; countries/cities; reports in CLI/txt/csv formats; provides a visualized report on OSM maps.
(Moderate non-fast search: limits requests to 15k/hour; does not provide information about providers).

3) Implements offline target search by list of data using the Database: and provides analytical and visualized information: IPv4/v6; GEO-coordinates/links; locations; providers; reports in CLI/txt/csv formats; provides a visualized report on OSM maps.
(Strong and fast search).

Results for method 1 and 2 may differ and be incomplete depending on users' personal DNS/IPv6 settings.
The data list is a text file (in utf-8 encoding), which the user specifies as the target, and which contains ip, domain or url (or combinations of them).

Purpose of the plugin - Education/Infosec.

\033[32;1m============================
| Plugin Reverse Vgeocoder |
============================\033[0m\n
\033[32mReverse impressive-geocoder from Snoopy to visualize coordinates on an OSM map with analytical data in html/csv/txt formats.

The plugin can extract and process coordinates from any noisy text files. The plugin implements offline target search by specified geo-coordinates and provides detailed analytical and visualized information.
Increased accuracy for objects in RU; EU; CIS zones relative to the rest of the world.

With this plugin, the user can extract, visualize, and analyze information about thousands of geo-coordinates in seconds.

Purpose of the plugin - CTF/Education.\033[0m

\033[32;1m======================
| Plugin Yandex_parser |
======================\033[0m\n
\033[32mThe plugin allows you to get information about users of Yandex services:
Ya_Reviews; Ya_Q; Ya_Market; Ya_Music; Ya_Zen; Ya_Disk; E-mail, Name.
And to link the received data together at high speed and scale.

The plugin was developed based on the materials of a vulnerability, reports were sent to Yandex under the "Bug Bounty" program in 2020-2021.

Purpose of the plugin - OSINT.

For more information about plugins, see 'Snoopy General Guide.pdf'.\033[0m""")
    console.rule("[bold red]End of help[/bold red]")


# snoopplugins.py Help Module Reverse Vgeocoder 'elif Vgeo == "help"'.
def help_vgeocoder_vgeo():
    print("""\033[32;1m└──[Help]\033[0m
\033[32m
In Snoopy, two geocoding modes are supported:
[*] Mode '\033[32;1mSimple\033[0m\033[32m':: Markers are placed by coordinates on the OSM map (reduced HTML report).
All markers are signed with geomarks.
Shortened reports with geomarks in html/txt formats are available for this method.

[*] Mode '\033[32;1mDetailed\033[0m\033[32m':: Markers are placed by coordinates on the OSM map (HTML report).
All markers are signed with geomarks, countries, counties, and cities. Charts by countries/regions, statistics, and filtering are available.
Additional reports (tables) are saved with details in [.txt.csv] formats.
This method precisely places markers with geomarks, signs them with addresses to the nearest settlements or natural objects.
Increased accuracy for objects in RU; EU; CIS zones relative to the rest of the world.

    For example, if the user uploads coordinates for processing pointing a kilometer from a city to the area near a lake, the marker on the OSM map will be exactly at the lake, and it will be signed with location details.

The method is based on the 'Euclidean tree'.

\033[32;1mPlugin Reverse Vgeocoder\033[0m \033[32m- works offline and is equipped with a specially developed geo-DB (some DBs are provided under a free license from download.geonames.org/export/dump/).

    To process data, specify a text file with coordinates in degrees in utf-8 encoding (with or without .txt extension) upon request. Every line with geo-coordinates (latitude, longitude) must be written in the file on a new line (highly recommended).
Snoopy is quite smart: it recognizes and selects geo-coordinates separated by commas, spaces, or makes an intelligent selection by clearing random strings.
    An example of a file with geo-coordinates (what the coordinate file might look like):

\"\"\"\033[36m
51.352,   -108.625
55.466,64.776
52.40662,66.77631
53.028 -104.680
54.505/73.773
CityA 55.75, 37.62 CityB 54.71, 20.51 CityC 47.23, 39.72
random_string1, which_will_be_processed CityD 55.7734/49.1436
random_string2, which_will_not_be_processed\033[0m\033[32m
\"\"\"

    After rendering is complete, a web browser with the visual result will open.
All results are saved in '~/.snoop/results/plugins/ReverseVgeocoder/*[.txt.html.csv]'.
For statistical data processing (sorting by countries/coordinates/raw_data, etc.), the user can study the report in csv format.
If charts do not appear in your HTML report, try opening the report in a different browser.
    This is a convenient plugin if the user needs, for example, not only to process geo-coordinates, but also to find chaotic data, or vice versa.""")


# snoopplugins.py Help Module Yandex_parser 'elif Ya == "help"'.
def help_yandex_parser():
    print("""\033[32;1m└──[Help]

Single-user mode\033[0m
\033[32m[*] Login - the left part before the '@' symbol, for example, bobbimonov@ya.ru, login
'\033[36mbobbimonov\033[0m\033[32m'.
[*] Public link to Yandex.Disk - this is a link to download/view materials that the user made publicly available, for example,
'\033[36mhttps://yadi.sk/d/7C6Z9q_Ds1wXkw\033[0m\033[32m' or '\033[36mhttps://disk.yandex.ru/d/7C6Z9q_Ds1wXkw\033[0m\033[32m'.
[*] Identifier - a hash specified in the URL on the user's page, for example, in the Ya.Rayon service: 'https://local.yandex.ru/users/tr6r2c8ea4tvdt3xmpy5atuwg0/' the identifier is '\033[36mtr6r2c8ea4tvdt3xmpy5atuwg0\033[0m\033[32m'.
    After a successful search, a CLI report is displayed, and the user's Yandex pages are opened in the browser.
    The Yandex_parser plugin produces less information by user ID (compared to other methods), the reason is a vulnerability fix from Yandex.

\033[32;1mMulti-user mode\033[0m
\033[32m[*] File with usernames - a file (in UTF-8 encoding with or without a .txt extension) in which logins are recorded.
Each login in the file must be written on a new line, for example:

\"\"\"
\033[36mbobbimonov
username
username2
username3
random string
bobbimonov@ya.ru
bobbimonov@ya.ru
bobbimonov@ya.ru\033[0m
\033[32m\"\"\"

    When using multi-user mode, after the search is complete (quickly), an extended CLI report is printed, a txt report on Yandex users is saved (with extended, structured data), and a browser is opened with a mini-report (grouped data).
    The plugin generates, but does not verify the 'availability' of users' personal pages because pages are often protected by Ya.captcha.
All results are saved in '\033[36m~/.snoop/results/plugins/Yandex_parser/*\033[0m\033[32m'\033[0m
    \033[31;1mAt the end of November 2022, Yandex closed its public api, and this plugin might not work anymore...\033[0m""")


# snoopplugins.py Help Module GEO_IP/domain 'elif dipbaza'.
def geo_ip_domain():
    print("\033[32;1m└──Help\033[0m\n")
    print("""\033[32m[*] Mode '\033[32;1mOnline search\033[0m\033[32m'. The GEO_IP/domain module from Snoopy uses public api and creates statistical and visualized information based on the target's ip/url/domain (data array).
    Limitations: queries ~15k/hour, low data processing speed, lack of information about ISPs.
    Advantages of using 'Online search': not only ip-addresses but also domain/url can be used as input data.
    Example of a data file (list.txt):

\"\"\"
\033[36m1.1.1.1
2606:2800:220:1:248:1893:25c8:1946
google.com
https://example.org/fo/bar/7564
random string\033[0m
\033[32m\"\"\"\033[0m

\033[32m[*] Mode '\033[32;1mOffline search\033[0m\033[32m'. The GEO_IP/domain module from Snoopy uses special databases and creates statistical and visualized information based on the target's ip (data array, i.e., ip addresses).
Advantages of using 'Offline search': speed (processing thousands of ip without delays), stability (lack of dependence on internet connection and users' personal DNS/IPv6 settings), massive coverage (information about internet providers is provided).

[*] Mode '\033[32;1mOffline_quiet search\033[0m\033[32m'. The same mode as the 'Offline' mode, but does not print intermediate data tables to the CLI. The mode gives a performance boost of several times.
    Example of a data file (list.txt):

\"\"\"
\033[36m8.8.8.8
93.184.216.34
2606:2800:220:1:248:1893:25c8:1946
random string\033[0m
\033[32m\"\"\"

    Snoopy is quite smart and capable of identifying and distinguishing between: IPv4/v6/domain/url in the input data, clearing out errors and random strings.
    After data processing is complete, the user is provided with:
statistical reports in [txt/csv/html and visualized data on the OSM map]. If the charts do not display in your HTML report, try opening the report in a different browser.
    Examples of what the GEO_IP/domain module from Snoopy can be used for.
For example, if the user has a list of IP addresses from a DDoS attack,
they can analyze where the max/min attack came from and from whom (providers).
Solving CTF quests where GPS/IPv4/v6 are used.
Ultimately using the plugin for educational purposes or out of natural curiosity (to check any IP addresses and their affiliation with the provider and locality).\033[0m""")
