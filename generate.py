#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DOBITKA — generator strony HTML (v2.0)
Zrodla danych:
  - football-data.org  (tabele, wyniki, terminarz, strzelcy)
  - TheSportsDB free   (druzyna dnia, zdjecia zawodnikow)
Uruchamiany co 2h przez GitHub Actions
"""

import requests
import os
import time
from datetime import datetime, timedelta, timezone
import re
import json as json_mod
import xml.etree.ElementTree as ET

# ─── CONFIG ───────────────────────────────────────────────────────────────────

API_KEY  = os.environ.get('FOOTBALL_DATA_KEY', '')
BASE     = 'https://api.football-data.org/v4'
FD_HDR   = {'X-Auth-Token': API_KEY}

TSDB_BASE = 'https://www.thesportsdb.com/api/v1/json/3'

# ─── LIGI (BL1 zamiast PPL — Bundesliga, nie Ekstraklasa) ─────────────────────
LEAGUES = [
    ('CL',  'Champions League', 'https://www.sofascore.com/tournament/football/europe/uefa-champions-league/7'),
    ('PL',  'Premier League',   'https://www.sofascore.com/tournament/football/england/premier-league/17'),
    ('PD',  'La Liga',          'https://www.sofascore.com/tournament/football/spain/laliga/8'),
    ('SA',  'Serie A',          'https://www.sofascore.com/tournament/football/italy/serie-a/23'),
    ('BL1', 'Bundesliga',       'https://www.sofascore.com/tournament/football/germany/bundesliga/35'),
    ('FL1', 'Ligue 1',          'https://www.sofascore.com/tournament/football/france/ligue-1/34'),
]

# Kolory per liga (uzyte w CSS zmiennych i zakładkach)
LEAGUE_COLORS = {
    'CL':  '#0a1e6e',
    'PL':  '#2e0040',
    'PD':  '#a83c00',
    'SA':  '#00337a',
    'BL1': '#8a0010',
    'FL1': '#001250',
}

# ─── TREŚCI EDYTOWALNE ────────────────────────────────────────────────────────

HOT_LINKS = [
    {
        'category': 'Liga Mistrzow',
        'cat_class': 'ucl',
        'title': 'Champions League — terminarz, wyniki, tabela',
        'url': 'https://www.uefa.com/uefachampionsleague/',
        'desc': 'Faza pucharowa UCL to najpiękniejsze 90 minut w kalendarzu kibicow — lub najgorsze, jesli grasz o awans z jednobramkowa zaliczka. Pelny terminarz i wyniki na stronie UEFA.',
        'source': 'UEFA.com',
    },
    {
        'category': 'La Liga',
        'cat_class': 'laliga',
        'title': 'Yamal vs Vinicius — mlodosc kontra doswiadczenie',
        'url': 'https://fbref.com/en/comps/12/La-Liga-Stats',
        'desc': 'Klasico w tym sezonie to osobny gatunek dramaturgii. Kompletne statystyki zawodnikow i druzyn La Ligi na FBref — jesli liczby sa twoja miloscia.',
        'source': 'FBref.com',
    },
    {
        'category': 'Premier League',
        'cat_class': 'pl',
        'title': 'Premier League — gdzie kupuja za miliardy, gdzie graja na wynik',
        'url': 'https://fbref.com/en/comps/9/Premier-League-Stats',
        'desc': 'Liga z najwiekszymi budzetami swiata i najlepsza atmosfera. Statystyki, xG, pressowanie — wszystko co trzeba na FBref.',
        'source': 'FBref.com',
    },
    {
        'category': 'Bundesliga',
        'cat_class': 'bundesliga',
        'title': 'Bundesliga — Bayern wciaz gora, reszta goni',
        'url': 'https://fbref.com/en/comps/20/Bundesliga-Stats',
        'desc': 'Rekord Lewandowskiego (41 goli), Xabi Alonso i Leverkusen bez porazki — Bundesliga potrafi zaskoczyc. Pelne statystyki na FBref.',
        'source': 'FBref.com',
    },
    {
        'category': 'Transfery',
        'cat_class': '',
        'title': 'Transfermarkt — ile naprawde wart jest twoj ulubiony zawodnik?',
        'url': 'https://www.transfermarkt.pl',
        'desc': 'Biblia wycen pilkarskich. Sprawdzasz czy nowy nabytek twojego klubu jest wart tyle co za niego zaplacono.',
        'source': 'Transfermarkt.pl',
    },
]

CIEKAWOSTKI = [
    ('<strong>Lamine Yamal urodzil sie 13 lipca 2007</strong> — dokladnie w dniu finalu Mundialu, kiedy Iniesta swietowal zloto. 17 lat pozniej Yamal wygral EURO 2024 z ta sama reprezentacja. Scenarzysta pilki noznej ma niesamowite poczucie humoru.'),
    ('<strong>Zinedine Zidane</strong> zakonczyl kariere glowka w Materazzim w finale MS 2006. Ten sam Zidane zdobyl dwa gole glowa w finale MS 1998. Symetria doskonala — nikt jej nie zaplanowal, ale wszyscy pamietaja.'),
    ('<strong>Lech Poznan w 1992 roku</strong> dotarl do cwierc finalu Ligi Mistrzow i gral z Barcelona Johana Cruyffa — Dreamteamem z Guardiolą, Stoichkovem i Laudrupem. Przegrali 1:3 i 0:4, ale historia jest legendarna.'),
    ('<strong>Ronald Koeman</strong> strzeli ponad 80 goli z rzutow wolnych przez cala kariere. Byl obronca. Wiekszosc napastnikow moglaby mu pozazdroscic skutecznosci.'),
    ('<strong>FC Barcelona przez ponad 100 lat</strong> (1899–2006) grala bez zadnego sponsora na koszulce. Potem wziela kase od Qatar Foundation. Przynajmniej byli ostatni z wielkich, ktorzy to zrobili.'),
    ('<strong>Cristiano Ronaldo i Neymar Jr</strong> obchodza urodziny tego samego dnia — 5 lutego. CR7 w 1985, Neymar w 1992. Dwie najwieksze gwiazdy swojej generacji, jeden dzien urodzin. Kosmos.'),
    ('<strong>Erling Haaland w sezonie 2022/23</strong> strzeli 52 gole we wszystkich rozgrywkach dla Manchesteru City. W samej PL przekroczyl rekord Salaha z 32 golami. Norweg gra w innym wymiarze.'),
    ('<strong>Robert Lewandowski w sezonie 2020/21</strong> strzeli 41 goli w Bundeslidze, bijac rekord Gerda Mullera z 1971/72, ktory stal przez 49 lat. Lewy dostal... drugie miejsce w Zlotej Pilce przez COVID.'),
]

BARCA_RADAR = [
    ('Wyniki i tabela La Liga', 'https://www.sofascore.com/team/football/fc-barcelona/2817', 'Sofascore — aktualne statystyki, tabela, terminarz FC Barcelona'),
    ('Lamine Yamal', 'https://www.transfermarkt.pl/lamine-yamal/profil/spieler/983709', 'Transfermarkt — profil, wycena, historia transferow'),
    ('Statystyki zaawansowane', 'https://fbref.com/en/squads/206d90db/FC-Barcelona-Stats', 'FBref — xG, pressing, posiadanie — Barca pod lupa'),
]

PL_RADAR = [
    ('Tabela Premier League', 'https://www.sofascore.com/tournament/football/england/premier-league/17#tab:standings', 'Sofascore — aktualna tabela, wyniki, strzelcy'),
    ('Statystyki ligowe', 'https://fbref.com/en/comps/9/Premier-League-Stats', 'FBref — zaawansowane statystyki wszystkich druzyn PL'),
    ('Transfery i wyceny', 'https://www.transfermarkt.pl/premier-league/startseite/wettbewerb/GB1', 'Transfermarkt — wartosci rynkowe zawodnikow Premier League'),
]

LALIGA_RADAR = [
    ('Tabela La Liga', 'https://www.sofascore.com/tournament/football/spain/laliga/8#tab:standings', 'Sofascore — aktualna tabela, wyniki, strzelcy La Liga'),
    ('Statystyki ligowe', 'https://fbref.com/en/comps/12/La-Liga-Stats', 'FBref — zaawansowane statystyki La Liga'),
    ('Transfery i wyceny', 'https://www.transfermarkt.pl/primera-division/startseite/wettbewerb/ES1', 'Transfermarkt — wartosci rynkowe zawodnikow La Liga'),
]

# ─── NOWE ZRODLA DANYCH (darmowe, bez kluczy) ─────────────────────────────────

# YouTube RSS — Tifo Football (bez klucza API, publiczny Atom feed)
TIFO_CHANNEL_ID = 'UCNAf1k0yIjyGu3k9BwAg3lg'

# Weszlo.com RSS
WESZLO_RSS_URL = 'https://weszlo.com/feed/'

# Understat — slownik kod ligi (slug, czytelna nazwa)
UNDERSTAT_LEAGUES = {
    'PL':  ('EPL',        'Premier League'),
    'PD':  ('La_liga',    'La Liga'),
    'SA':  ('Serie_A',    'Serie A'),
    'BL1': ('Bundesliga', 'Bundesliga'),
    'FL1': ('Ligue_1',    'Ligue 1'),
}

CYTATY = [
    {
        'osoba':    'Pep Guardiola',
        'klub':     'Manchester City',
        'cytat':    '"Nie rozmawiamy o remisach. Gramy zeby wygrywaC. Remis to porazka w przebraniu."',
        'kontekst': 'po konferencji przed meczem ligowym',
    },
    {
        'osoba':    'Carlo Ancelotti',
        'klub':     'Real Madryt',
        'cytat':    '"Real Madryt nigdy nie jest faworytem. Ale zawsze wygrywa."',
        'kontekst': 'przed faza pucharowa UCL',
    },
    {
        'osoba':    'Jude Bellingham',
        'klub':     'Real Madryt',
        'cytat':    '"Kiedy masz 20 lat i grasz w Realu, nie pytasz czy jestes gotowy. Po prostu grasz."',
        'kontekst': 'wywiad dla Sky Sports',
    },
    {
        'osoba':    'Lamine Yamal',
        'klub':     'FC Barcelona',
        'cytat':    '"Mam 17 lat i gram dla Barcelony. To jedyne co wiem. Reszta to szum."',
        'kontekst': 'konferencja prasowa przed El Clasico',
    },
]

NEYMAR_UPDATE = {
    'headline': 'Neymar Jr i reprezentacja Brazylii — saga trwa',
    'tresc': (
        'Po ponad roku rehabilitacji po zerwaniu ACL Neymar wrocil do gry w Al-Hilal, '
        'ale jego miejsce w selekcji kadry Brazylii pozostaje otwarte. '
        'Selekcjoner Dorival Junior jasno: <strong>"Neymar musi wygraC zdrowie, '
        'zanim wygramy z nim mecz."</strong> '
        'Sam zainteresowany na Instagramie: <em>"Wroce. Nie wiem kiedy, ale wroce."</em> '
        'Kibice Brazylii czekaja. Reszta swiata tez — bo futbol bez Neymara jest o klase nudniejszy.'
    ),
    'link': 'https://www.transfermarkt.pl/neymar/profil/spieler/68290',
}

# ─── URODZINY (miesiac, dzien, imie, rok, opis) ───────────────────────────────
FAMOUS_BIRTHDAYS = [
    (1,  4,  'Toni Kroos',              1990, 'legenda Realu Madryt i Niemiec, mistrz precyzji'),
    (1, 18,  'Pep Guardiola',           1971, 'trener-geniusz, wychowanek i ikona FC Barcelona'),
    (1, 25,  'Xavi Hernandez',          1980, 'architekt tikitaki, dzisiaj trener Barcy'),
    (2,  2,  'Gerard Pique',            1987, 'centralny obronca Barcelony, maz Shakiry'),
    (2,  5,  'Cristiano Ronaldo',       1985, 'CR7 — pięciokrotna Złota Pilka, fenomen sportu'),
    (2,  5,  'Neymar Jr',               1992, 'brazylijski czarodziej — ten sam dzien urodzin co CR7!'),
    (2, 28,  'Arkadiusz Milik',         1994, 'polska dziewiatka, gol na EURO 2020 i seria A'),
    (3, 11,  'Didier Drogba',           1978, 'legenda Chelsea — bohater finalu UCL 2012 w Monachium'),
    (3, 21,  'Ronaldinho',              1980, 'Zlota pilka 2005, geniusz sambowej pilki'),
    (3, 21,  'Antoine Griezmann',       1991, 'mistrz swiata 2018, wierny sluga Atletico'),
    (3, 27,  'Manuel Neuer',            1986, 'rewolucja na pozycji bramkarza, legenda Bayernu'),
    (3, 30,  'Sergio Ramos',            1986, 'kapitan Realu, mistrz kartek i goli w doliczonym czasie'),
    (4, 10,  'Roberto Carlos',          1973, 'lewy obronca z rakieta w lewej nodze, legenda Realu'),
    (4, 18,  'Wojciech Szczęsny',       1990, 'polska jedynka — Arsenal, Juventus, Barcelona'),
    (4, 19,  'Karim Benzema',           1987, 'Zlota Pilka 2022, cichobohater Realu przez 14 lat'),
    (4, 25,  'Johan Cruyff',            1947, 'Total Football, legenda Ajaksu i Barcelony (1947-2016)'),
    (5,  2,  'David Beckham',           1975, 'ikona lat 90. i 2000., styl i futbol w jednym'),
    (5, 11,  'Andres Iniesta',          1984, 'gol w finale MS 2010, czysta dusza tikitaki'),
    (5, 28,  'Phil Foden',              2000, 'The Stockport Iniesta — filar Manchesteru City'),
    (5, 30,  'Steven Gerrard',          1980, 'kapitan Liverpoolu, serce i dusza Anfield'),
    (6, 15,  'Mohamed Salah',           1992, 'egipski faraon, maszyna do goli w Liverpoolu'),
    (6, 20,  'Frank Lampard',           1978, 'najskuteczniejszy pomocnik Chelsea w historii'),
    (6, 20,  'Piotr Zielinski',         1994, 'polskie zloto — Napoli, Inter i serce pomocnika'),
    (6, 21,  'Michel Platini',          1955, 'trzykrotna Zlota Pilka, legenda Juventusu'),
    (6, 23,  'Zinedine Zidane',         1972, 'trzy Zlote Pilki, dwie glowki w finale MS 1998, jedna w 2006'),
    (6, 24,  'Lionel Messi',            1987, 'La Pulga — osmiokrotna Zlota Pilka, mistrz swiata 2022'),
    (6, 26,  'Paolo Maldini',           1968, 'AC Milan na zawsze, obronca absolutny wszech czasow'),
    (6, 28,  'Kevin De Bruyne',         1991, 'belgijski mozg Manchesteru City'),
    (6, 29,  'Jude Bellingham',         2003, 'angielski diament Realu Madryt — sezon debiutancki z bajki'),
    (7,  8,  'Son Heung-min',           1992, 'koreanki as Tottenhamu, ulubieniec kibicow na calym swiecie'),
    (7, 12,  'Vinicius Jr',             2000, 'brazylijska rakieta Realu Madryt, gol w finale UCL 2022'),
    (7, 13,  'Lamine Yamal',            2007, 'urodzony w dniu finalu MS 2010 — przeznaczenie czeka'),
    (7, 21,  'Erling Haaland',          2000, 'norweska maszyna — 52 gole w sezonie debiutanckim w PL'),
    (7, 28,  'Harry Kane',              1993, 'krol strzelcow Premier League, teraz Bayern'),
    (8,  5,  'Gavi',                    2004, 'serce Barcelony, nastepca Iniesty w stylu i duchu'),
    (8, 17,  'Thierry Henry',           1977, 'legenda Arsenalu, Le Roi, reka w eliminacjach MS 2010'),
    (8, 21,  'Robert Lewandowski',      1988, 'polska dziewiatka — 41 goli w Bundeslidze, rekord Mullera'),
    (9,  9,  'Luka Modric',             1985, 'Zlota Pilka 2018, 38-latek wciaz najlepszy w swoim fachu'),
    (9, 18,  'Ronaldo Nazario',         1976, 'R9 — najlepszy napastnik wszech czasow wedlug wielu'),
    (10,  3, 'Zlatan Ibrahimovic',      1981, 'Zloty Bog, akrobata, legenda europejskiego futbolu'),
    (10, 23, 'Pele',                    1940, 'O Rei — trzykrotny mistrz swiata, do konca 2022'),
    (10, 24, 'Wayne Rooney',            1985, 'legenda Man United, najskuteczniejszy strzelec Three Lions'),
    (10, 30, 'Diego Maradona',          1960, 'Bog pilki — Reka Boga, gol stulecia, 1986 caly on'),
    (10, 31, 'Marco van Basten',        1964, 'trzykrotna Zlota Pilka, gol w finale EURO 1988'),
    (10, 31, 'Marcus Rashford',         1997, 'szybka noga Man United z Old Trafford'),
    (11,  7, 'Rio Ferdinand',           1978, 'wodz obrony Man United w czasach chwaly Fergusona'),
    (11, 25, 'Xabi Alonso',             1981, 'mistrz podania — Liverpool, Real, Bayern, Leverkusen jako trener'),
    (12,  7, 'John Terry',              1980, 'kapitan Chelsea, lider przez dekade na Stamford Bridge'),
    (12, 14, 'Michael Owen',            1979, 'Zlota Pilka 2001, blysk kariery w Liverpoolu i Realu'),
    (12, 14, 'Jakub Blaszczykowski',    1985, 'Kuba — duma polskiej pilki, Dortmund i Fiorentina'),
    (12, 20, 'Kylian Mbappe',           1998, 'nastepca Zidanea? Nie — wlasna legenda w budowie'),
]

# ─── WIBE DRUZYN ──────────────────────────────────────────────────────────────
TEAM_VIBES = {
    'Chelsea':    'Blues ze Stamford Bridge — potrafi wygrac UCL i zwolnic trenera w tym samym tygodniu',
    'Man City':   'niebieski moloch grajacy jak algorytm zaprojektowany przez Guardiole',
    'Arsenal':    'Gooners — znowu "w tym sezonie"? Moze tym razem naprawde tak bedzie',
    'Liverpool':  "You'll Never Walk Alone — szczegolnie gdy zostajesz z 10. po czerwonej",
    'Man United': 'Red Devils — wciaz najwieksza marka, troche mniej wygranych ostatnio',
    'Tottenham':  'Spurs — jak miec talent i systematycznie go marnowac, podrecznik w 20 rozdzialach',
    'Barcelona':  'Barca — Yamal, Pedri, Lewandowski. Jedna z najladniejszych druzyn na swiecie',
    'Real Madrid':'Los Blancos — wygrywaja UCL statystycznie co dwa sezony. Nikt nie wie jak.',
    'Atletico':   'Atletico — bunkier Simeone, gol w 89. minucie i mistrzostwo w rytmie zawal-serce',
    'Bayern':     'Bayern Monachium — Bundesliga od lat ich, UCL od czasu do czasu',
    'Dortmund':   'BVB — zolto-czarna adrenalina i coroczny zawod w finiszu sezonu',
    'Juventus':   'Stara Dama — zmeczona blaskiem, ale na kolana nie padnie',
    'Inter':      'Nerazzurri — aktualnie bezspornnie najlepsza druzyna we Wloszech',
    'AC Milan':   'Rossoneri — legenda San Siro z lekka nostalgia za Maldiniemi Shevchenko',
    'Napoli':     'Partenopei — Maradona w niebie, Napoli na ziemi wciaz szaleje',
    'Paris':      'PSG — galaktyki gwiazd co rok, a UCL nadal ucieka jak Mbappe do Madrytu',
    'Leverkusen': 'Apteka — mistrzowie Niemiec 2024 bez jednej porazki. Xabi Alonso wie co robi.',
    'Ajax':       'Ajax Amsterdam — fabryka talentow na eksport do calej Europy',
    'Lech':       'Kolejorz — duma Poznania i staly reprezentant Polski w europejskich pucharach',
    'Legia':      'Legia Warszawa — najwiekszy klub Polski, co roku walczy o Europe',
    'Wisla':      'Biala Gwiazda Krakow — moje miasto, czas na powrot do ekstraklasy',
    'Cracovia':   'Pasy Krakow — derby przy Reymonta zawsze grzeje krew',
}

# ─── TheSportsDB: 14 klubow rotowanych wg dnia miesiaca ──────────────────────
FEATURED_TEAMS = [
    'FC Barcelona',
    'Real Madrid',
    'Manchester City',
    'Liverpool',
    'Arsenal',
    'Chelsea',
    'Bayern Munich',
    'Borussia Dortmund',
    'Juventus',
    'AC Milan',
    'Inter Milan',
    'PSG',
    'Atletico Madrid',
    'Ajax',
]

# ─── FUNKCJE API: football-data.org ──────────────────────────────────────────

def fd_fetch(path, delay=7):
    """Pobiera dane z football-data.org. Delay 7s — max 10 req/min."""
    if not API_KEY:
        return None
    time.sleep(delay)
    try:
        r = requests.get(f'{BASE}{path}', headers=FD_HDR, timeout=20)
        if r.status_code == 200:
            return r.json()
        print(f'  FD API {r.status_code}: {path}')
        return None
    except Exception as e:
        print(f'  FD blad: {e}')
        return None


def get_standings(code):
    return fd_fetch(f'/competitions/{code}/standings')


def get_results(code, limit=6):
    """Ostatnie zakonczone mecze danej ligi."""
    return fd_fetch(f'/competitions/{code}/matches?status=FINISHED&limit={limit}')


def get_upcoming(code, limit=5):
    """Nadchodzace mecze danej ligi."""
    return fd_fetch(f'/competitions/{code}/matches?status=SCHEDULED&limit={limit}')


def get_scorers(code, limit=8):
    """Top strzelcy danej ligi."""
    return fd_fetch(f'/competitions/{code}/scorers?limit={limit}')


def get_day_matches(date_str):
    """Wszystkie mecze w danym dniu (YYYY-MM-DD)."""
    return fd_fetch(f'/matches?dateFrom={date_str}&dateTo={date_str}')


def filter_supported(data):
    """Filtruje mecze do obsługiwanych lig."""
    if not data or not data.get('matches'):
        return []
    supported = {code for code, *_ in LEAGUES}
    return [m for m in data['matches'] if m.get('competition', {}).get('code') in supported]


# ─── FUNKCJE API: TheSportsDB ─────────────────────────────────────────────────

def tsdb_fetch(endpoint, params):
    """Pobiera dane z TheSportsDB (brak klucza, brak delay)."""
    try:
        r = requests.get(f'{TSDB_BASE}/{endpoint}', params=params, timeout=6)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f'  TSDB blad: {e}')
    return None


def tsdb_featured_team(day_of_month):
    """Zwraca dane druzyny dnia rotowanej wg dnia miesiaca (mod 14)."""
    idx  = (day_of_month - 1) % len(FEATURED_TEAMS)
    name = FEATURED_TEAMS[idx]
    data = tsdb_fetch('searchteams.php', {'t': name})
    if not data or not data.get('teams'):
        return {'name': name, 'badge': None, 'formed': '?', 'stadium': '?', 'desc': ''}
    team = data['teams'][0]
    desc_raw = team.get('strDescriptionPL') or team.get('strDescriptionEN') or ''
    desc = (desc_raw[:350] + '...') if len(desc_raw) > 350 else desc_raw
    return {
        'name':    team.get('strTeam', name),
        'badge':   team.get('strBadge'),
        'formed':  team.get('intFormedYear', '?'),
        'stadium': team.get('strStadium', '?'),
        'desc':    desc,
    }


def tsdb_player_photo(name):
    """Zwraca URL zdjecia/cutout zawodnika z TheSportsDB lub None."""
    data = tsdb_fetch('searchplayers.php', {'p': name})
    if not data or not data.get('player'):
        return None
    p = data['player'][0]
    return p.get('strCutout') or p.get('strThumb') or None


# ─── REDDIT API (bez klucza — publiczny JSON endpoint) ────────────────────────

def reddit_fetch(subreddit, limit=12):
    """Pobiera hot posty z Reddit bez klucza API."""
    try:
        r = requests.get(
            f'https://www.reddit.com/r/{subreddit}/hot.json',
            params={'limit': limit},
            headers={'User-Agent': 'dobitka-bot/2.0'},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json().get('data', {}).get('children', [])
    except Exception as e:
        print(f'  Reddit blad ({subreddit}): {e}')
    return []


def reddit_html(subreddit, max_items=6, min_score=50):
    """HTML lista hot postow z wybranego subreddita."""
    posts = reddit_fetch(subreddit, limit=20)
    if not posts:
        return '<p class="no-data">Brak danych z Reddit.</p>'

    html = ''
    count = 0
    for child in posts:
        d = child.get('data', {})
        if d.get('stickied'):
            continue
        title = (d.get('title') or '')[:100]
        url   = d.get('url') or d.get('permalink') or '#'
        if url.startswith('/r/'):
            url = 'https://www.reddit.com' + url
        score   = d.get('score', 0) or 0
        comments = d.get('num_comments', 0) or 0
        flair   = (d.get('link_flair_text') or '')[:30]

        if score < min_score:
            continue

        flair_html = f'<div class="rp-flair">{flair}</div>' if flair else ''
        html += (
            f'<div class="reddit-post">'
            f'{flair_html}'
            f'<div class="rp-title"><a href="{url}" target="_blank" rel="noopener">{title}</a></div>'
            f'<div class="rp-meta">&#11014; {score:,} &nbsp;&#128172; {comments}</div>'
            f'</div>\n'
        )
        count += 1
        if count >= max_items:
            break

    return html or '<p class="no-data">Brak postow spelniajacych kryteria.</p>'


# ─── YOUTUBE RSS — TIFO FOOTBALL (bez klucza, publiczny Atom) ─────────────────

def tifo_videos_html(max_items=4):
    """Najnowsze filmy Tifo Football z publicznego RSS YouTube."""
    try:
        r = requests.get(
            f'https://www.youtube.com/feeds/videos.xml?channel_id={TIFO_CHANNEL_ID}',
            timeout=10,
            headers={'User-Agent': 'dobitka-bot/2.0'},
        )
        if r.status_code != 200:
            return '<p class="no-data">Brak RSS z YouTube.</p>'

        ns = {
            'atom':  'http://www.w3.org/2005/Atom',
            'media': 'http://search.yahoo.com/mrss/',
        }
        root    = ET.fromstring(r.text)
        entries = root.findall('atom:entry', ns)[:max_items]

        html = ''
        for entry in entries:
            title_el = entry.find('atom:title',     ns)
            link_el  = entry.find('atom:link',      ns)
            pub_el   = entry.find('atom:published', ns)
            thumb_el = entry.find('.//media:thumbnail', ns)

            t   = title_el.text if title_el is not None else '?'
            url = link_el.get('href', '#') if link_el is not None else '#'
            pub = (pub_el.text or '')[:10]
            img = thumb_el.get('url', '') if thumb_el is not None else ''

            t_safe = t[:40]
            img_html = f'<img class="video-thumb" src="{img}" alt="{t_safe}" loading="lazy">' if img else ''
            html += (
                f'<div class="video-item">'
                f'{img_html}'
                f'<div class="video-info">'
                f'<div class="video-title"><a href="{url}" target="_blank" rel="noopener">{t}</a></div>'
                f'<div class="video-date">Tifo Football &nbsp;|&nbsp; {pub}</div>'
                f'</div></div>\n'
            )

        return html or '<p class="no-data">Brak filmow.</p>'
    except Exception as e:
        print(f'  Tifo RSS blad: {e}')
        return '<p class="no-data">Blad parsowania RSS.</p>'


# ─── WESZLO.COM RSS ────────────────────────────────────────────────────────────

def weszlo_html(max_items=6):
    """Najnowsze artykuly z Weszlo.com (RSS)."""
    try:
        r = requests.get(
            WESZLO_RSS_URL,
            timeout=10,
            headers={'User-Agent': 'dobitka-bot/2.0'},
        )
        if r.status_code != 200:
            return '<p class="no-data">Brak RSS z Weszlo.com.</p>'

        root  = ET.fromstring(r.text)
        items = root.findall('.//item')[:max_items]

        html = ''
        for item in items:
            title_el = item.find('title')
            link_el  = item.find('link')
            pub_el   = item.find('pubDate')
            cat_el   = item.find('category')

            t   = (title_el.text or '?')[:90]
            url = (link_el.text or '#') if link_el is not None else '#'
            pub = (pub_el.text or '')
            cat = (cat_el.text or '') if cat_el is not None else ''

            # Skroc date
            try:
                dt  = datetime.strptime(pub[:16], '%a, %d %b %Y')
                pub = dt.strftime('%d.%m')
            except Exception:
                pub = pub[:10]

            cat_html = f'<div class="news-cat">{cat[:25]}</div>' if cat else ''
            html += (
                f'<div class="news-item">'
                f'{cat_html}'
                f'<div class="news-title"><a href="{url}" target="_blank" rel="noopener">{t}</a></div>'
                f'<div class="news-date">{pub}</div>'
                f'</div>\n'
            )

        return html or '<p class="no-data">Brak artykulow.</p>'
    except Exception as e:
        print(f'  Weszlo RSS blad: {e}')
        return '<p class="no-data">Blad pobierania RSS.</p>'


# ─── UNDERSTAT — xG (scraping publicznych danych) ─────────────────────────────

def understat_xg(league_code):
    """Parsuje dane xG z Understat (publiczne, osadzone jako JSON w HTML)."""
    if league_code not in UNDERSTAT_LEAGUES:
        return None
    slug, _ = UNDERSTAT_LEAGUES[league_code]
    try:
        r = requests.get(
            f'https://understat.com/league/{slug}',
            timeout=15,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
        )
        if r.status_code != 200:
            return None
        m = re.search(r"var teamsData\s*=\s*JSON\.parse\('(.+?)'\)", r.text)
        if not m:
            return None
        raw  = m.group(1).encode('utf-8').decode('unicode_escape')
        return json_mod.loads(raw)
    except Exception as e:
        print(f'  Understat blad ({league_code}): {e}')
        return None


def xg_table_html(league_code, fallback_url):
    """Justice Table — xPTS vs rzeczywiste punkty per druzyna."""
    teams = understat_xg(league_code)
    if not teams:
        return (
            f'<p class="no-data">Brak danych xG &mdash; '
            f'<a href="https://understat.com" target="_blank">Understat &#8594;</a></p>'
        )

    sorted_teams = sorted(
        teams.values(),
        key=lambda t: -float(t.get('xpts', 0)),
    )

    rows = ''
    for i, t in enumerate(sorted_teams[:10], 1):
        name = (t.get('title') or '?')[:18]
        xg   = round(float(t.get('xG',   0)), 1)
        xga  = round(float(t.get('xGA',  0)), 1)
        xpts = round(float(t.get('xpts', 0)), 1)
        pts  = int(t.get('pts', 0))
        diff = pts - round(xpts)
        diff_cls = 'xg-plus' if diff > 2 else ('xg-minus' if diff < -2 else '')
        sign = '+' if diff > 0 else ''
        rows += (
            f'<tr><td class="s-pos">{i}</td>'
            f'<td class="s-team">{name}</td>'
            f'<td class="xg-col">{xg}</td>'
            f'<td class="xg-col">{xga}</td>'
            f'<td class="xg-col xg-pts">{xpts}</td>'
            f'<td class="xg-col">{pts}</td>'
            f'<td class="xg-col {diff_cls}">{sign}{diff}</td></tr>\n'
        )

    return (
        '<table class="xg-table">'
        '<tr class="s-header">'
        '<th class="s-pos">#</th><th class="s-team">Druzyna</th>'
        '<th class="xg-col">xG</th><th class="xg-col">xGA</th>'
        '<th class="xg-col xg-pts">xPTS</th><th class="xg-col">PKT</th>'
        '<th class="xg-col">diff</th>'
        '</tr>'
        f'{rows}'
        '</table>'
        '<p class="xg-note">diff = PKT &minus; xPTS &nbsp;|&nbsp; + szczesciarze, &minus; pechowcy &nbsp;|&nbsp; '
        '<a href="https://understat.com" target="_blank">understat.com</a></p>'
    )


# ─── GENERATORY HTML ─────────────────────────────────────────────────────────

def fmt_time(utc_str):
    """UTC ISO string → CET +1h, format dd.mm HH:MM."""
    try:
        dt    = datetime.fromisoformat(utc_str.replace('Z', '+00:00'))
        local = dt + timedelta(hours=1)
        return local.strftime('%d.%m %H:%M')
    except Exception:
        return '?'


def standings_table(code, fallback_url):
    """Tabela ligowa — top 10 druzyn."""
    data = get_standings(code)
    if not data:
        return f'<p class="no-data">Brak danych — <a href="{fallback_url}" target="_blank">Sofascore &#8594;</a></p>'
    try:
        table = data['standings'][0]['table'][:10]
    except (KeyError, IndexError):
        return f'<p class="no-data">Brak danych — <a href="{fallback_url}" target="_blank">Sofascore &#8594;</a></p>'

    rows = ''
    for e in table:
        pos  = e['position']
        name = e['team'].get('shortName') or e['team']['name']
        pts  = e['points']
        m    = e['playedGames']
        w    = e['won']
        d    = e['draw']
        l    = e['lost']
        gd   = e.get('goalDifference', 0)
        sign = '+' if gd > 0 else ''

        color = ''
        if pos <= 4:
            color = 'style="color:#00cc55"'
        elif pos in (5, 6):
            color = 'style="color:#ffaa44"'
        elif pos >= len(table) - 2:
            color = 'style="color:#ff5544"'

        rows += (
            f'<tr {color}>'
            f'<td class="s-pos">{pos}</td>'
            f'<td class="s-team">{name}</td>'
            f'<td class="s-num">{m}</td><td class="s-num">{w}</td>'
            f'<td class="s-num">{d}</td><td class="s-num">{l}</td>'
            f'<td class="s-num s-gd">{sign}{gd}</td>'
            f'<td class="s-pts">{pts}</td>'
            f'</tr>\n'
        )

    return (
        '<table class="standings-table">'
        '<tr class="s-header">'
        '<th class="s-pos">#</th><th class="s-team">Druzyna</th>'
        '<th class="s-num">M</th><th class="s-num">W</th>'
        '<th class="s-num">R</th><th class="s-num">L</th>'
        '<th class="s-num">RB</th><th class="s-pts">PKT</th>'
        '</tr>'
        f'{rows}'
        '</table>'
    )


def scorers_html(code, fallback_url):
    """Top strzelcy ligi."""
    data = get_scorers(code, limit=8)
    if not data or not data.get('scorers'):
        return f'<p class="no-data">Brak strzelcow — <a href="{fallback_url}" target="_blank">Sofascore &#8594;</a></p>'

    html = '<div class="scorers-list">'
    for i, s in enumerate(data['scorers'], 1):
        player   = s.get('player', {})
        team     = s.get('team', {})
        pname    = player.get('name', '?')
        tname    = (team.get('shortName') or team.get('name') or '?')
        goals    = s.get('goals', 0) or 0
        assists  = s.get('assists', 0) or 0
        html += (
            f'<div class="scorer-row">'
            f'<span class="sc-rank">{i}</span>'
            f'<span class="sc-name">{pname}</span>'
            f'<span class="sc-team">{tname}</span>'
            f'<span class="sc-goals">{goals}</span>'
            f'<span class="sc-assists">+{assists}a</span>'
            f'</div>\n'
        )
    html += '</div>'
    return html


def results_html(code, fallback_url):
    """Ostatnie wyniki ligi."""
    data = get_results(code, limit=6)
    if not data or not data.get('matches'):
        return f'<p class="no-data">Brak wynikow — <a href="{fallback_url}" target="_blank">Sofascore &#8594;</a></p>'

    html = ''
    for m in reversed(data['matches'][:6]):
        home = m['homeTeam'].get('shortName') or m['homeTeam']['name']
        away = m['awayTeam'].get('shortName') or m['awayTeam']['name']
        sh   = m['score']['fullTime'].get('home')
        sa   = m['score']['fullTime'].get('away')
        if sh is None or sa is None:
            continue
        cls = 'draw'
        if sh > sa: cls = 'win-h'
        if sa > sh: cls = 'win-a'
        html += (
            f'<div class="result-row">'
            f'<span class="r-home">{home}</span>'
            f'<span class="r-score {cls}">{sh}:{sa}</span>'
            f'<span class="r-away">{away}</span>'
            f'</div>\n'
        )
    return html or f'<p class="no-data">Brak wynikow — <a href="{fallback_url}" target="_blank">Sofascore &#8594;</a></p>'


def upcoming_html(code, fallback_url):
    """Nadchodzace mecze ligi."""
    data = get_upcoming(code, limit=5)
    if not data or not data.get('matches'):
        return f'<p class="no-data">Brak terminarza — <a href="{fallback_url}" target="_blank">Sofascore &#8594;</a></p>'

    html = ''
    for m in data['matches'][:5]:
        home = m['homeTeam'].get('shortName') or m['homeTeam']['name']
        away = m['awayTeam'].get('shortName') or m['awayTeam']['name']
        t    = fmt_time(m.get('utcDate', ''))
        html += (
            f'<div class="upcoming-row">'
            f'<span class="u-home">{home}</span>'
            f'<span class="u-vs">vs</span>'
            f'<span class="u-away">{away}</span>'
            f'<span class="u-time">{t}</span>'
            f'</div>\n'
        )
    return html or f'<p class="no-data">Brak danych — <a href="{fallback_url}" target="_blank">Sofascore &#8594;</a></p>'


def birthdays_html(now_pl):
    """Urodziny znanych pilkarzy dzisiaj z opcjonalnym zdjeciem z TheSportsDB."""
    m, d = now_pl.month, now_pl.day
    todays = [(name, year, desc) for (bm, bd, name, year, desc) in FAMOUS_BIRTHDAYS if bm == m and bd == d]
    if not todays:
        return '<p class="no-data">Dzis brak znanych urodzin w bazie DOBITKA.<br><small>Baza zawiera ~50 pilkarzy i trenerow.</small></p>'

    html = ''
    for name, year, desc in todays:
        age   = now_pl.year - year
        photo = tsdb_player_photo(name)
        if photo:
            img_html = f'<img src="{photo}" alt="{name}" class="bday-photo">'
        else:
            img_html = '<span class="bday-cake">&#127874;</span>'

        html += (
            f'<div class="birthday-item">'
            f'{img_html}'
            f'<div>'
            f'<strong class="bday-name">{name}</strong>'
            f'<span class="bday-age"> &mdash; konczy {age} lat</span>'
            f'<p class="bday-desc">{desc}</p>'
            f'</div>'
            f'</div>\n'
        )
    return html


def todays_matches_html(matches, today_label):
    """Dzisiejsze mecze — zaplanowane i juz grane."""
    if not matches:
        return (
            f'<p class="no-data">Dzis brak meczow w obsługiwanych ligach.<br>'
            f'<a href="https://www.flashscore.pl" target="_blank">Flashscore &#8594;</a></p>'
        )
    html = ''
    for m in matches[:10]:
        home   = m['homeTeam'].get('shortName') or m['homeTeam']['name']
        away   = m['awayTeam'].get('shortName') or m['awayTeam']['name']
        t      = fmt_time(m.get('utcDate', ''))
        status = m.get('status', '')
        comp   = m.get('competition', {}).get('name', '')
        hour   = t.split(' ')[-1] if ' ' in t else t

        if status == 'FINISHED':
            sh  = m['score']['fullTime'].get('home')
            sa  = m['score']['fullTime'].get('away')
            if sh is None or sa is None:
                continue
            cls = 'draw'
            if sh > sa: cls = 'win-h'
            if sa > sh: cls = 'win-a'
            html += (
                f'<div class="td-row finished">'
                f'<span class="td-comp">{comp[:12]}</span>'
                f'<span class="td-home">{home}</span>'
                f'<span class="td-score {cls}">{sh}:{sa}</span>'
                f'<span class="td-away">{away}</span>'
                f'<span class="td-status">FT</span>'
                f'</div>\n'
            )
        elif status in ('IN_PLAY', 'PAUSED', 'HALFTIME'):
            sh = (m['score'].get('fullTime', {}).get('home')
                  or m['score'].get('halfTime', {}).get('home', 0))
            sa = (m['score'].get('fullTime', {}).get('away')
                  or m['score'].get('halfTime', {}).get('away', 0))
            html += (
                f'<div class="td-row live">'
                f'<span class="td-comp">{comp[:12]}</span>'
                f'<span class="td-home">{home}</span>'
                f'<span class="td-score draw live-score">{sh}:{sa}</span>'
                f'<span class="td-away">{away}</span>'
                f'<span class="td-status blink">LIVE</span>'
                f'</div>\n'
            )
        else:
            html += (
                f'<div class="td-row">'
                f'<span class="td-comp">{comp[:12]}</span>'
                f'<span class="td-home">{home}</span>'
                f'<span class="td-score draw">vs</span>'
                f'<span class="td-away">{away}</span>'
                f'<span class="td-status td-time">{hour}</span>'
                f'</div>\n'
            )
    return html or '<p class="no-data">Brak meczow — <a href="https://www.flashscore.pl" target="_blank">Flashscore</a></p>'


def yesterdays_results_html(matches):
    """Wyniki z wczoraj."""
    finished = [m for m in matches if m.get('status') == 'FINISHED']
    if not finished:
        return (
            '<p class="no-data">Brak wynikow z wczoraj.<br>'
            '<a href="https://www.flashscore.pl" target="_blank">Flashscore &#8594;</a></p>'
        )
    html = ''
    for m in finished[:10]:
        home = m['homeTeam'].get('shortName') or m['homeTeam']['name']
        away = m['awayTeam'].get('shortName') or m['awayTeam']['name']
        sh   = m['score']['fullTime'].get('home')
        sa   = m['score']['fullTime'].get('away')
        if sh is None or sa is None:
            continue
        comp = m.get('competition', {}).get('name', '')
        cls  = 'draw'
        if sh > sa: cls = 'win-h'
        if sa > sh: cls = 'win-a'
        html += (
            f'<div class="td-row">'
            f'<span class="td-comp">{comp[:12]}</span>'
            f'<span class="td-home">{home}</span>'
            f'<span class="td-score {cls}">{sh}:{sa}</span>'
            f'<span class="td-away">{away}</span>'
            f'<span class="td-status">FT</span>'
            f'</div>\n'
        )
    return html or '<p class="no-data">Brak wynikow z wczoraj.</p>'


def _find_vibe(team_name):
    tl = team_name.lower()
    for key, vibe in TEAM_VIBES.items():
        if key.lower() in tl or tl in key.lower():
            return vibe
    return None


def match_previews_html(matches):
    """Zapowiedzi meczow w stylu redakcji DOBITKA."""
    previews = []
    for m in matches:
        if m.get('status') not in ('SCHEDULED', 'TIMED'):
            continue
        home = m['homeTeam'].get('shortName') or m['homeTeam']['name']
        away = m['awayTeam'].get('shortName') or m['awayTeam']['name']
        t    = fmt_time(m.get('utcDate', ''))
        comp = m.get('competition', {}).get('name', '')
        hv   = _find_vibe(home)
        av   = _find_vibe(away)
        if hv or av:
            previews.append((home, away, t, comp, hv, av))

    if not previews:
        return ''

    html = ''
    for home, away, t, comp, hv, av in previews[:5]:
        hour = t.split(' ')[-1] if ' ' in t else t
        if hv and av:
            tekst = (f'<strong>{home}</strong> to {hv}. '
                     f'Naprzeciwko staje <strong>{away}</strong> &mdash; {av}. '
                     f'Kick-off o {hour}, kto bardziej potrzebuje tych 3 punktow?')
        elif hv:
            tekst = (f'<strong>{home}</strong> &mdash; {hv} &mdash; podejmuje dzis '
                     f'<strong>{away}</strong> o {hour}. Ciekawe kto bardziej glodny wyniku.')
        else:
            tekst = (f'<strong>{away}</strong> &mdash; {av} &mdash; wyjedza na teren '
                     f'<strong>{home}</strong> o {hour}. Goscie zwykle wiedza co traca.')

        html += (
            f'<div class="preview-item">'
            f'<div class="preview-match">{home} <span class="preview-vs">vs</span> {away}'
            f'<span class="preview-meta">{comp} &nbsp;|&nbsp; {t}</span></div>'
            f'<div class="preview-text">{tekst}</div>'
            f'</div>\n'
        )
    return html


def featured_team_html(team_data):
    """Druzyna dnia z TheSportsDB."""
    badge_html = ''
    if team_data.get('badge'):
        badge_html = f'<img src="{team_data["badge"]}" alt="{team_data["name"]}" class="ft-badge">'
    else:
        badge_html = '<span class="ft-no-badge">&#9917;</span>'

    desc_html = f'<p class="ft-desc">{team_data["desc"]}</p>' if team_data.get('desc') else ''

    return (
        f'<div class="featured-team">'
        f'{badge_html}'
        f'<div class="ft-info">'
        f'<div class="ft-name">{team_data["name"]}</div>'
        f'<div class="ft-meta">'
        f'<span>Zalozony: <strong>{team_data["formed"]}</strong></span>'
        f' &nbsp;|&nbsp; '
        f'<span>Stadion: <strong>{team_data["stadium"]}</strong></span>'
        f'</div>'
        f'{desc_html}'
        f'</div>'
        f'</div>'
    )


def hot_links_html():
    html = ''
    for lnk in HOT_LINKS:
        cat_cls = lnk.get('cat_class', '')
        html += (
            f'<div class="link-item">'
            f'<div class="link-cat {cat_cls}">{lnk["category"]}</div>'
            f'<div class="link-title"><a href="{lnk["url"]}" target="_blank">{lnk["title"]}</a></div>'
            f'<div class="link-desc">{lnk["desc"]}</div>'
            f'<div class="link-source">&#9658; {lnk["source"]}</div>'
            f'</div>\n'
        )
    return html


def ciekawostki_html():
    html = ''
    for i, c in enumerate(CIEKAWOSTKI, 1):
        html += (
            f'<div class="ciekawostka-item">'
            f'<span class="ciek-num">#{i:02d}</span>'
            f'<p>{c}</p>'
            f'</div>\n'
        )
    return html


def radar_html(items):
    html = ''
    for label, url, desc in items:
        html += (
            f'<div class="radar-item">'
            f'<span class="r-bullet">&#9733;</span>'
            f'<div><a href="{url}" target="_blank">{label}</a><br>'
            f'<span class="r-desc">{desc}</span></div>'
            f'</div>\n'
        )
    return html


def cytaty_html():
    html = ''
    for c in CYTATY:
        html += (
            f'<div class="cytat-item">'
            f'<div class="cytat-text">{c["cytat"]}</div>'
            f'<div class="cytat-meta"><strong>{c["osoba"]}</strong> ({c["klub"]}) &mdash; <em>{c["kontekst"]}</em></div>'
            f'</div>\n'
        )
    return html


def neymar_html():
    n = NEYMAR_UPDATE
    return (
        f'<div class="neymar-box">'
        f'<div class="neymar-headline">&#128308; {n["headline"]}</div>'
        f'<div class="neymar-text">{n["tresc"]}</div>'
        f'<div class="neymar-link"><a href="{n["link"]}" target="_blank">Transfermarkt — profil Neymara &#8594;</a></div>'
        f'</div>'
    )


# ─── CSS ──────────────────────────────────────────────────────────────────────

CSS = '''
:root {
  --bg:      #07070f;
  --panel:   #0f0f1d;
  --bdr:     #1e1e38;
  --gold:    #ffd700;
  --red:     #cc1100;
  --green:   #00bb44;
  --text:    #cccccc;
  --muted:   #55556a;
  --link:    #7799ff;
  --radius:  6px;
  /* Per-liga kolory */
  --cl-color:  #0a1e6e;
  --pl-color:  #2e0040;
  --pd-color:  #a83c00;
  --sa-color:  #00337a;
  --bl1-color: #8a0010;
  --fl1-color: #001250;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
  font-size: 14px;
  line-height: 1.6;
}
a { color: var(--link); text-decoration: none; }
a:hover { color: var(--gold); text-decoration: underline; }

/* ── TICKER ── */
.ticker-wrap {
  background: var(--red);
  overflow: hidden;
  white-space: nowrap;
  padding: 5px 0;
}
.ticker-label {
  background: var(--gold);
  color: #000;
  font-weight: 700;
  font-size: 11px;
  padding: 0 10px;
  margin-right: 8px;
  letter-spacing: 1px;
}
.ticker-text {
  display: inline-block;
  animation: scroll 55s linear infinite;
  font-size: 12px;
  color: #fff;
  letter-spacing: 0.4px;
}
@keyframes scroll { from { transform: translateX(100vw); } to { transform: translateX(-100%); } }

/* ── HEADER ── */
header {
  background: radial-gradient(ellipse at 50% 0%, #131340 0%, var(--bg) 70%);
  border-bottom: 3px solid var(--gold);
  padding: 24px 0 16px;
  text-align: center;
}
.logo {
  font-family: 'Courier New', monospace;
  font-size: clamp(28px, 5vw, 52px);
  font-weight: 900;
  color: var(--gold);
  text-shadow: 3px 3px 0 #770000, 6px 6px 0 #330000;
  letter-spacing: clamp(4px, 1vw, 10px);
}
.tagline { font-size: 12px; color: #666; margin-top: 6px; letter-spacing: 3px; text-transform: uppercase; }
.updated { font-size: 11px; color: var(--muted); margin-top: 6px; }
.updated span { color: var(--gold); }

/* ── NAV (sticky) ── */
nav {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(7, 7, 15, 0.92);
  backdrop-filter: blur(8px);
  border-bottom: 2px solid var(--bdr);
  text-align: center;
  padding: 0;
}
nav a {
  display: inline-block;
  padding: 9px 15px;
  font-size: 11px;
  font-weight: 700;
  color: #999;
  letter-spacing: 1px;
  text-transform: uppercase;
  border-right: 1px solid var(--bdr);
  transition: background 0.15s, color 0.15s;
}
nav a:first-child { border-left: 1px solid var(--bdr); }
nav a:hover { background: #111130; color: var(--gold); text-decoration: none; }

/* ── LIVE SECTION ── */
#live-section {
  max-width: 1100px;
  margin: 0 auto;
  padding: 14px 12px 0;
}
#live-section.hidden { display: none; }
.live-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 10px 0;
}
.live-card {
  background: #120500;
  border: 1px solid #442200;
  border-radius: var(--radius);
  padding: 8px 14px;
  min-width: 200px;
  flex: 1 1 200px;
}
.live-card .lc-comp { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
.live-card .lc-teams { font-size: 13px; color: #ccc; display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.live-card .lc-score { font-family: 'Courier New', monospace; font-size: 20px; font-weight: 900; color: #ffaa00; }
.live-card .lc-min { font-size: 10px; color: #ff6600; font-weight: 700; }
.live-no-match { padding: 8px 0; font-size: 12px; color: var(--muted); font-style: italic; }

/* ── TOPBAR (3 kolumny) ── */
.topbar-wrap {
  max-width: 1100px;
  margin: 0 auto;
  padding: 16px 12px 0;
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16px;
}
.previews-wrap { max-width: 1100px; margin: 0 auto; padding: 0 12px; }

/* ── CONTAINER (2 kolumny) ── */
.container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 16px 12px;
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 16px;
}

/* ── BOX ── */
.box {
  background: var(--panel);
  border: 1px solid var(--bdr);
  border-radius: var(--radius);
  margin-bottom: 16px;
  overflow: hidden;
}
.box-hdr {
  background: #111130;
  padding: 8px 14px;
  font-weight: 700;
  color: var(--gold);
  text-transform: uppercase;
  letter-spacing: 1.5px;
  border-bottom: 2px solid var(--gold);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}
.box-hdr .sub { font-size: 10px; color: #888; font-weight: 400; text-transform: none; letter-spacing: 0; }
.no-data { padding: 10px 14px; color: var(--muted); font-size: 12px; font-style: italic; }

/* ── FEATURED TEAM ── */
.featured-team {
  padding: 14px;
  display: flex;
  gap: 14px;
  align-items: flex-start;
}
.ft-badge {
  width: 60px;
  height: 60px;
  object-fit: contain;
  flex-shrink: 0;
}
.ft-no-badge { font-size: 40px; flex-shrink: 0; }
.ft-name { font-size: 16px; font-weight: 700; color: var(--gold); margin-bottom: 4px; }
.ft-meta { font-size: 11px; color: #888; margin-bottom: 6px; }
.ft-desc { font-size: 12px; color: #aaa; line-height: 1.5; font-style: italic; }

/* ── TODAY / YESTERDAY TABLE ── */
.td-row {
  padding: 6px 10px;
  border-bottom: 1px solid var(--bdr);
  display: grid;
  grid-template-columns: 65px 1fr 44px 1fr 38px;
  gap: 4px;
  align-items: center;
  font-size: 11px;
  transition: background 0.1s;
}
.td-row:last-child { border-bottom: none; }
.td-row:hover { background: #111128; }
.td-row.live { background: #110500; }
.td-comp { color: var(--muted); font-size: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.td-home { text-align: right; color: #ccc; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.td-away { color: #ccc; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.td-score {
  text-align: center;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  font-weight: 900;
  padding: 1px 3px;
  border: 1px solid #333;
  border-radius: 3px;
}
.td-score.win-h { background: rgba(0,187,68,0.12); color: var(--green); border-color: var(--green); }
.td-score.win-a { background: rgba(255,86,68,0.12); color: #ff6644; border-color: #ff6644; }
.td-score.draw  { color: #ccc; border-color: #444; }
.td-score.live-score { color: #ffaa00; border-color: #ffaa00; background: rgba(255,170,0,0.08); }
.td-status { text-align: right; font-size: 10px; color: var(--muted); }
.td-time { color: var(--gold); font-size: 11px; font-family: 'Courier New', monospace; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.25} }
.blink { animation: pulse 1.2s ease-in-out infinite; color: #ff4400 !important; font-weight: 700; }

/* ── URODZINY ── */
.birthday-item {
  padding: 10px 12px;
  border-bottom: 1px solid var(--bdr);
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.birthday-item:last-child { border-bottom: none; }
.bday-cake { font-size: 20px; flex-shrink: 0; line-height: 1.4; }
.bday-photo { width: 42px; height: 42px; object-fit: cover; border-radius: 50%; flex-shrink: 0; border: 2px solid var(--gold); }
.bday-name { color: var(--gold); font-size: 13px; font-weight: 700; }
.bday-age { color: #aaa; font-size: 11px; }
.bday-desc { font-size: 11px; color: var(--muted); margin-top: 2px; font-style: italic; }

/* ── ZAPOWIEDZI ── */
.preview-item { padding: 12px 14px; border-bottom: 1px solid var(--bdr); }
.preview-item:last-child { border-bottom: none; }
.preview-match { font-weight: 700; color: var(--gold); font-size: 13px; margin-bottom: 4px; }
.preview-vs { color: var(--muted); font-size: 11px; font-weight: 400; }
.preview-meta { font-weight: 400; color: var(--muted); font-size: 10px; margin-left: 8px; }
.preview-text { font-size: 12px; color: #bbb; line-height: 1.6; }

/* ── LINKI ── */
.link-item { padding: 14px; border-bottom: 1px solid var(--bdr); transition: background 0.1s; }
.link-item:last-child { border-bottom: none; }
.link-item:hover { background: #111128; }
.link-cat { font-size: 10px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 4px; color: var(--muted); }
.link-cat.ucl        { color: #4488ff; }
.link-cat.laliga     { color: #cc8800; }
.link-cat.pl         { color: #aa44ff; }
.link-cat.bundesliga { color: #ff4444; }
.link-cat.ekstraklasa{ color: var(--green); }
.link-title { font-size: 15px; font-weight: 700; color: #eee; line-height: 1.2; margin-bottom: 5px; }
.link-title a { color: #eee; }
.link-title a:hover { color: var(--gold); text-decoration: none; }
.link-desc { font-size: 12px; color: #888; line-height: 1.5; font-style: italic; }
.link-source { font-size: 11px; color: var(--muted); margin-top: 5px; }
.link-source::before { content: "\\25B6  "; color: var(--gold); }

/* ── WYNIKI ── */
.result-row {
  padding: 8px 14px;
  border-bottom: 1px solid var(--bdr);
  display: grid;
  grid-template-columns: 1fr 60px 1fr;
  gap: 6px;
  align-items: center;
  font-size: 13px;
  transition: background 0.1s;
}
.result-row:last-child { border-bottom: none; }
.result-row:hover { background: #111128; }
.r-home { text-align: right; color: #ccc; }
.r-away { color: #ccc; }
.r-score {
  text-align: center;
  font-family: 'Courier New', monospace;
  font-size: 16px;
  font-weight: 900;
  padding: 1px 4px;
  border: 1px solid #333;
  border-radius: 3px;
}
.r-score.win-h { background: rgba(0,187,68,0.12); color: var(--green); border-color: var(--green); }
.r-score.win-a { background: rgba(255,86,68,0.12); color: #ff6644; border-color: #ff6644; }
.r-score.draw  { color: #ccc; border-color: #444; }

/* ── UPCOMING ── */
.upcoming-row {
  padding: 8px 14px;
  border-bottom: 1px solid var(--bdr);
  display: grid;
  grid-template-columns: 1fr 30px 1fr 65px;
  gap: 6px;
  align-items: center;
  font-size: 12px;
}
.upcoming-row:last-child { border-bottom: none; }
.u-home { text-align: right; color: #ccc; }
.u-away { color: #ccc; }
.u-vs   { text-align: center; color: var(--muted); font-size: 11px; }
.u-time { text-align: right; font-family: 'Courier New', monospace; color: var(--gold); font-size: 12px; }

/* ── STRZELCY ── */
.scorers-list { padding: 6px 0; }
.scorer-row {
  padding: 6px 14px;
  border-bottom: 1px solid var(--bdr);
  display: grid;
  grid-template-columns: 22px 1fr 90px 32px 36px;
  gap: 6px;
  align-items: center;
  font-size: 12px;
}
.scorer-row:last-child { border-bottom: none; }
.sc-rank  { color: var(--muted); font-size: 11px; text-align: right; }
.sc-name  { color: #ddd; font-weight: 600; }
.sc-team  { color: #888; font-size: 11px; }
.sc-goals { text-align: right; font-family: 'Courier New', monospace; font-size: 20px; font-weight: 900; color: var(--gold); }
.sc-assists { font-size: 10px; color: var(--muted); text-align: right; }

/* ── TABS LIGOWE ── */
.tab-btns { display: flex; flex-wrap: wrap; background: #0a0a1a; border-bottom: 1px solid var(--bdr); }
.tab-btn {
  background: none;
  border: none;
  border-right: 1px solid var(--bdr);
  color: #777;
  padding: 8px 12px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transition: background 0.15s, color 0.15s;
}
.tab-btn:hover { background: #111130; color: var(--gold); }
.tab-btn.active { color: var(--gold); border-bottom: 2px solid var(--gold); }
.tab-btn[data-code="CL"].active  { background: var(--cl-color); }
.tab-btn[data-code="PL"].active  { background: var(--pl-color); }
.tab-btn[data-code="PD"].active  { background: var(--pd-color); }
.tab-btn[data-code="SA"].active  { background: var(--sa-color); }
.tab-btn[data-code="BL1"].active { background: var(--bl1-color); }
.tab-btn[data-code="FL1"].active { background: var(--fl1-color); }
.tab-pane { display: none; padding: 12px; }
.tab-pane.active { display: block; }
.tab-league-title { font-weight: 700; font-size: 15px; color: var(--gold); margin-bottom: 10px; }
.subsection-title {
  font-size: 10px;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 1.5px;
  margin: 14px 0 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--bdr);
}

/* ── STANDINGS TABLE ── */
.standings-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.standings-table .s-header { color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--bdr); }
.standings-table th, .standings-table td { padding: 4px 3px; }
.s-pos  { text-align: right; width: 20px; color: #555; }
.s-team { padding-left: 8px !important; }
.s-num  { text-align: center; width: 26px; color: #888; }
.s-gd   { color: #777 !important; }
.s-pts  { text-align: center; width: 30px; color: var(--gold) !important; font-weight: 700; font-family: 'Courier New', monospace; }
.standings-table tr:hover { background: #111128; }

/* ── CIEKAWOSTKI ── */
.ciekawostka-item { padding: 12px 14px; border-bottom: 1px solid var(--bdr); display: flex; gap: 10px; }
.ciekawostka-item:last-child { border-bottom: none; }
.ciek-num { font-family: 'Courier New', monospace; font-size: 22px; color: var(--gold); opacity: 0.4; flex-shrink: 0; line-height: 1; }
.ciekawostka-item p { font-size: 12px; color: #aaa; line-height: 1.55; }
.ciekawostka-item p strong { color: #ddd; }

/* ── RADAR ── */
.radar-item { padding: 9px 14px; border-bottom: 1px solid var(--bdr); display: flex; gap: 10px; font-size: 13px; }
.radar-item:last-child { border-bottom: none; }
.r-bullet { color: var(--gold); flex-shrink: 0; }
.r-desc { font-size: 11px; color: var(--muted); display: block; }

/* ── CYTATY ── */
.cytat-item { padding: 12px 14px; border-bottom: 1px solid var(--bdr); }
.cytat-item:last-child { border-bottom: none; }
.cytat-text { font-size: 13px; color: #ddd; font-style: italic; line-height: 1.55; margin-bottom: 5px; border-left: 3px solid var(--gold); padding-left: 10px; }
.cytat-meta { font-size: 11px; color: var(--muted); }
.cytat-meta strong { color: #aaa; }

/* ── NEYMAR ── */
.neymar-box { padding: 14px; }
.neymar-headline { font-size: 13px; font-weight: 700; color: var(--gold); margin-bottom: 8px; }
.neymar-text { font-size: 12px; color: #aaa; line-height: 1.6; margin-bottom: 8px; }
.neymar-text strong { color: #ddd; }
.neymar-text em { color: #bbb; font-style: italic; }
.neymar-link { font-size: 12px; }

/* ── SZYBKIE LINKI ── */
.quick-link {
  padding: 8px 14px;
  border-bottom: 1px solid var(--bdr);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  transition: background 0.1s;
}
.quick-link:last-child { border-bottom: none; }
.quick-link:hover { background: #111128; }
.quick-link span { color: var(--muted); font-size: 12px; }
.quick-link a { font-weight: 700; }

/* ── EKSTRAKLASA MANUAL LINKS ── */
.ekstra-item {
  padding: 8px 14px;
  border-bottom: 1px solid var(--bdr);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  transition: background 0.1s;
}
.ekstra-item:last-child { border-bottom: none; }
.ekstra-item:hover { background: #111128; }
.ekstra-item span { color: var(--muted); font-size: 11px; }

/* ── FOOTER ── */
footer {
  background: #040408;
  border-top: 2px solid var(--bdr);
  text-align: center;
  padding: 24px;
  font-size: 12px;
  color: var(--muted);
}
footer a { color: #444; }
footer a:hover { color: var(--gold); }

/* ── REDDIT POSTY ── */
.reddit-post { padding: 10px 14px; border-bottom: 1px solid var(--bdr); transition: background 0.1s; }
.reddit-post:last-child { border-bottom: none; }
.reddit-post:hover { background: rgba(255,255,255,0.02); }
.rp-flair { font-size: 10px; color: #ff7744; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 2px; }
.rp-title a { color: #ddd; font-size: 13px; line-height: 1.4; display: block; }
.rp-title a:hover { color: var(--gold); text-decoration: none; }
.rp-meta { font-size: 11px; color: var(--muted); margin-top: 4px; }

/* ── TIFO VIDEOS ── */
.video-item { padding: 10px 12px; border-bottom: 1px solid var(--bdr); display: flex; gap: 10px; align-items: flex-start; transition: background 0.1s; }
.video-item:last-child { border-bottom: none; }
.video-item:hover { background: rgba(255,255,255,0.02); }
.video-thumb { width: 80px; height: 45px; object-fit: cover; border-radius: 4px; flex-shrink: 0; border: 1px solid var(--bdr); }
.video-info { flex: 1; min-width: 0; }
.video-title a { color: #ddd; font-size: 12px; line-height: 1.4; display: block; }
.video-title a:hover { color: var(--gold); text-decoration: none; }
.video-date { font-size: 10px; color: var(--muted); margin-top: 3px; }

/* ── WESZLO NEWS ── */
.news-item { padding: 10px 14px; border-bottom: 1px solid var(--bdr); transition: background 0.1s; }
.news-item:last-child { border-bottom: none; }
.news-item:hover { background: rgba(255,255,255,0.02); }
.news-cat { font-size: 10px; color: var(--green); font-weight: 700; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 2px; }
.news-title { display: flex; justify-content: space-between; gap: 8px; align-items: flex-start; }
.news-title a { color: #ddd; font-size: 13px; line-height: 1.4; flex: 1; }
.news-title a:hover { color: var(--gold); text-decoration: none; }
.news-date { font-size: 11px; color: var(--muted); flex-shrink: 0; }

/* ── XG TABLE ── */
.xg-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.xg-table .s-header { color: #555; font-size: 10px; text-transform: uppercase; border-bottom: 1px solid var(--bdr); }
.xg-table th, .xg-table td { padding: 4px 3px; }
.xg-col { text-align: center; width: 38px; color: #888; font-family: 'Courier New', monospace; font-size: 11px; }
.xg-pts { color: #88aaff !important; font-weight: 700; }
.xg-plus { color: var(--green) !important; font-weight: 700; }
.xg-minus { color: #ff5544 !important; font-weight: 700; }
.xg-note { font-size: 10px; color: var(--muted); padding: 6px 14px; font-style: italic; border-top: 1px solid var(--bdr); }
.xg-table tr:hover td { background: rgba(255,255,255,0.03); }

/* ── RESPONSIVE ── */
@media (max-width: 900px) {
  .topbar-wrap { grid-template-columns: 1fr 1fr; }
  .container   { grid-template-columns: 1fr; }
}
@media (max-width: 600px) {
  .topbar-wrap { grid-template-columns: 1fr; }
  .logo { letter-spacing: 4px; }
  nav a { padding: 8px 10px; font-size: 10px; }
  .tab-btn { font-size: 10px; padding: 7px 8px; }
  .scorer-row { grid-template-columns: 20px 1fr 32px; }
  .sc-team, .sc-assists { display: none; }
}
'''

# ─── JS (live refresh + tab switching) ───────────────────────────────────────

JS_TEMPLATE = '''
const FDAPI = '{API_KEY_PLACEHOLDER}';
const SUPPORTED_CODES = new Set(['CL','PL','PD','SA','BL1','FL1']);

const LEAGUE_NAMES = {
  CL:'Champions League', PL:'Premier League', PD:'La Liga',
  SA:'Serie A', BL1:'Bundesliga', FL1:'Ligue 1'
};

// Tab switching
function showTab(code) {
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  const pane = document.getElementById('tab-' + code);
  if (pane) pane.classList.add('active');
  document.querySelectorAll('.tab-btn').forEach(b => {
    if (b.dataset.code === code) b.classList.add('active');
  });
}

// Live scores auto-refresh
async function refreshLive() {
  const section = document.getElementById('live-section');
  const container = document.getElementById('live-container');
  if (!container || !FDAPI) return;

  try {
    const resp = await fetch('https://api.football-data.org/v4/matches?status=IN_PLAY', {
      headers: { 'X-Auth-Token': FDAPI }
    });
    if (!resp.ok) throw new Error('status ' + resp.status);
    const data = await resp.json();
    const matches = (data.matches ?? []).filter(m =>
      SUPPORTED_CODES.has(m.competition?.code ?? '')
    );

    if (matches.length === 0) {
      if (section) section.classList.add('hidden');
      return;
    }
    if (section) section.classList.remove('hidden');

    container.innerHTML = matches.map(m => {
      const comp   = LEAGUE_NAMES[m.competition?.code] ?? m.competition?.name ?? '';
      const home   = m.homeTeam?.shortName ?? m.homeTeam?.name ?? '?';
      const away   = m.awayTeam?.shortName ?? m.awayTeam?.name ?? '?';
      const scoreH = m.score?.fullTime?.home ?? m.score?.halfTime?.home ?? 0;
      const scoreA = m.score?.fullTime?.away ?? m.score?.halfTime?.away ?? 0;
      const minute = m.minute ? m.minute + "'" : 'LIVE';
      return `<div class="live-card">
        <div class="lc-comp">${comp}</div>
        <div class="lc-teams">
          <span>${home}</span>
          <span class="lc-score">${scoreH}:${scoreA}</span>
          <span>${away}</span>
        </div>
        <div class="lc-min blink">${minute}</div>
      </div>`;
    }).join('');
  } catch(e) {
    console.warn('Live refresh error:', e);
  }
}

// Init
window.addEventListener('DOMContentLoaded', () => {
  // Activate first tab
  const firstBtn = document.querySelector('.tab-btn');
  if (firstBtn) showTab(firstBtn.dataset.code);
  // Live refresh
  refreshLive();
  setInterval(refreshLive, 90000);
});
'''

# ─── GLOWNA FUNKCJA GENERATE ──────────────────────────────────────────────────

def generate():
    now_utc     = datetime.now(timezone.utc)
    now_pl      = now_utc + timedelta(hours=1)
    updated     = now_pl.strftime('%d.%m.%Y %H:%M')
    today_str   = now_pl.strftime('%Y-%m-%d')
    yest_str    = (now_pl - timedelta(days=1)).strftime('%Y-%m-%d')
    today_label = now_pl.strftime('%d.%m.%Y')
    yest_label  = (now_pl - timedelta(days=1)).strftime('%d.%m.%Y')

    print('DOBITKA generator v2.0')
    print(f'Data: {today_label}')

    # TheSportsDB: druzyna dnia (bez delay, szybkie)
    print('  TheSportsDB: druzyna dnia...')
    featured = tsdb_featured_team(now_pl.day)
    print(f'  Druzyna dnia: {featured["name"]}')

    # football-data.org: dzis i wczoraj (2 wywolania)
    print('  Dzisiejsze mecze...')
    today_matches = filter_supported(get_day_matches(today_str))

    print('  Wczorajsze wyniki...')
    yest_matches = filter_supported(get_day_matches(yest_str))

    # Per liga: standings + scorers + results + upcoming (4 x 6 = 24 wywolania, ~3 min)
    league_data = {}
    for code, name, fallback in LEAGUES:
        print(f'  {name}: tabela...')
        standing = standings_table(code, fallback)
        print(f'  {name}: strzelcy...')
        scorers  = scorers_html(code, fallback)
        print(f'  {name}: wyniki...')
        results  = results_html(code, fallback)
        print(f'  {name}: terminarz...')
        upcoming = upcoming_html(code, fallback)
        league_data[code] = {
            'name':     name,
            'fallback': fallback,
            'standing': standing,
            'scorers':  scorers,
            'results':  results,
            'upcoming': upcoming,
        }

    # Understat xG — pobierz przed budowaniem tabel (uzywane w standings_sections)
    print('  Understat xG (5 lig)...')
    xg_data = {}
    for code, name, fallback in LEAGUES:
        if code in UNDERSTAT_LEAGUES:
            xg_data[code] = xg_table_html(code, fallback)

    # Buduj sekcje zakładek ligowych
    tab_btns = ''
    for i, (code, name, _) in enumerate(LEAGUES):
        active = ' active' if i == 0 else ''
        tab_btns += f'<button class="tab-btn{active}" data-code="{code}" onclick="showTab(\'{code}\')">{name}</button>\n'

    standings_sections = ''
    for code, name, fallback in LEAGUES:
        d = league_data[code]
        xg_section = (
            '<div class="subsection-title">&#128200; xG Tabela (Understat)</div>'
            + xg_data.get(code, '<p class="no-data">Brak danych xG dla tej ligi.</p>')
        ) if code in UNDERSTAT_LEAGUES else ''
        standings_sections += (
            f'<div class="tab-pane" id="tab-{code}">'
            f'<div class="tab-league-title">{name}</div>'
            f'{d["standing"]}'
            f'<div class="subsection-title">&#9917; Top Strzelcy</div>'
            f'{d["scorers"]}'
            f'{xg_section}'
            f'<div class="subsection-title">Ostatnie Wyniki</div>'
            f'{d["results"]}'
            f'<div class="subsection-title">Najblizsze Mecze</div>'
            f'{d["upcoming"]}'
            f'</div>\n'
        )

    # HTML sekcji
    bdays_html_str   = birthdays_html(now_pl)
    today_html_str   = todays_matches_html(today_matches, today_label)
    yest_html_str    = yesterdays_results_html(yest_matches)
    previews_sec     = match_previews_html(today_matches)
    featured_html    = featured_team_html(featured)

    # ── Nowe zrodla danych (bez kluczy API) ────────────────────────────────
    print('  Reddit r/soccer...')
    reddit_soccer_html = reddit_html('soccer', max_items=6, min_score=100)

    print('  Reddit r/ekstraklasa...')
    reddit_ekstra_html = reddit_html('ekstraklasa', max_items=5, min_score=5)

    print('  Weszlo.com RSS...')
    weszlo_news = weszlo_html(max_items=6)

    print('  Tifo Football YouTube RSS...')
    tifo_html = tifo_videos_html(max_items=4)

    previews_block = ''
    if previews_sec:
        previews_block = (
            f'<div class="previews-wrap">'
            f'<div class="box">'
            f'<div class="box-hdr" style="background:#1a1a00;">&#9997; Zapowiedzi DOBITKA '
            f'<span class="sub">subiektywnie, bo inaczej sie nie da</span></div>'
            f'{previews_sec}'
            f'</div>'
            f'</div>'
        )

    # JS z podmienianym kluczem
    js_code = JS_TEMPLATE.replace('{API_KEY_PLACEHOLDER}', API_KEY)

    html = f'''<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DOBITKA &#9917; Pilka. Sport. Bez sciemy.</title>
<meta name="description" content="Agregator pilkarski — tabele, wyniki, terminarz, strzelcy. Champions League, Premier League, La Liga, Serie A, Bundesliga, Ligue 1.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>

<div class="ticker-wrap">
  <span class="ticker-label">&#9658; DOBITKA</span>
  <span class="ticker-text">
    &#9733; Aktualizacja co 2 godziny &#9733;
    Champions League &bull; Premier League &bull; La Liga &bull; Serie A &bull; Bundesliga &bull; Ligue 1 &#9733;
    Wyniki &bull; Tabele &bull; Strzelcy &bull; Terminarz &mdash; bez sciemy &#9733;
  </span>
</div>

<header>
  <div class="logo">&#9917; DOBITKA</div>
  <div class="tagline">// Pilka. Sport. Bez sciemy. //</div>
  <div class="updated">Ostatnia aktualizacja: <span>{updated}</span> &nbsp;|&nbsp;
    Dane: <a href="https://www.football-data.org" target="_blank">football-data.org</a>
    &nbsp;+&nbsp; <a href="https://www.thesportsdb.com" target="_blank">TheSportsDB</a>
  </div>
</header>

<nav>
  <a href="#live">&#128308; Live</a>
  <a href="#dzisiaj">&#9654; Dzisiaj</a>
  <a href="#linki">&#128293; Linki</a>
  <a href="#tabele">&#128202; Tabele</a>
  <a href="#ciekawostki">&#129504; Ciekawostki</a>
  <a href="#radar">&#128301; Radar</a>
  <a href="https://www.flashscore.pl" target="_blank">&#9889; Flashscore</a>
</nav>

<!-- LIVE SECTION (aktualizowany przez JS co 90s) -->
<div id="live-section" class="hidden" id="live">
  <div class="box">
    <div class="box-hdr" style="background:#1a0400;">&#128308; Mecze LIVE <span class="sub">auto-refresh co 90s</span></div>
    <div class="live-cards" id="live-container">
      <p class="live-no-match">Ladowanie wynikow live...</p>
    </div>
  </div>
</div>

<!-- TOP BAR: Dzisiaj / Wczoraj / Urodziny -->
<div class="topbar-wrap" id="dzisiaj">

  <div>
    <div class="box">
      <div class="box-hdr" style="background:#001a10;">&#9654; DZISIAJ W AKCJI <span class="sub">{today_label}</span></div>
      {today_html_str}
    </div>
  </div>

  <div>
    <div class="box">
      <div class="box-hdr" style="background:#1a0a00;">&#9664; WCZORAJSZE WYNIKI <span class="sub">{yest_label}</span></div>
      {yest_html_str}
    </div>
  </div>

  <div>
    <div class="box">
      <div class="box-hdr" style="background:#1a001a;">&#127874; URODZINY <span class="sub">dzisiaj ({today_label})</span></div>
      {bdays_html_str}
    </div>
  </div>

</div>

{previews_block}

<div class="container">

  <!-- LEWA KOLUMNA -->
  <div>

    <!-- Druzyna dnia (TheSportsDB) -->
    <div class="box">
      <div class="box-hdr" style="background:#0d1a0d;">&#127942; DRUZYNA DNIA <span class="sub">TheSportsDB</span></div>
      {featured_html}
    </div>

    <!-- Reddit r/soccer — swieze newsy ze spolecznosci -->
    <div class="box">
      <div class="box-hdr" style="background:#1a0800;">&#128172; Z Internetu &#8212; r/soccer <span class="sub">Reddit</span></div>
      {reddit_soccer_html}
      <div style="text-align:right;padding:6px 14px;font-size:11px;color:var(--muted);">
        <a href="https://reddit.com/r/soccer" target="_blank">r/soccer &#8594;</a>
      </div>
    </div>

    <!-- Gorace linki -->
    <div class="box" id="linki">
      <div class="box-hdr">&#128293; Gorace Linki <span class="sub">wybrane przez redakcje</span></div>
      {hot_links_html()}
    </div>

    <!-- Tabele, strzelcy, wyniki — zakładki ligowe -->
    <div class="box" id="tabele">
      <div class="box-hdr">&#128202; Tabele &amp; Wyniki <span class="sub">football-data.org</span></div>
      <div class="tab-btns">
        {tab_btns}
      </div>
      {standings_sections}
    </div>

  </div>

  <!-- PRAWA KOLUMNA -->
  <div>

    <div class="box">
      <div class="box-hdr" style="background:#1a0030;">&#128483; Neymar Jr &mdash; aktualny status</div>
      {neymar_html()}
    </div>

    <div class="box">
      <div class="box-hdr" style="background:#001830;">&#128172; Z konferencji prasowych</div>
      {cytaty_html()}
    </div>

    <div class="box" id="ciekawostki">
      <div class="box-hdr">&#129504; Ciekawostki</div>
      {ciekawostki_html()}
    </div>

    <!-- Weszlo.com — polska pilka -->
    <div class="box">
      <div class="box-hdr" style="background:#003010;">&#127477;&#127473; Weszlo.com <span class="sub">polska pilka</span></div>
      {weszlo_news}
      <div style="text-align:right;padding:6px 14px;font-size:11px;color:var(--muted);">
        <a href="https://weszlo.com" target="_blank">weszlo.com &#8594;</a>
      </div>
    </div>

    <!-- Tifo Football — filmy taktyczne -->
    <div class="box">
      <div class="box-hdr" style="background:#0a0018;">&#127910; Tifo Football <span class="sub">YouTube</span></div>
      {tifo_html}
      <div style="text-align:right;padding:6px 14px;font-size:11px;color:var(--muted);">
        <a href="https://www.youtube.com/@TifoFootball" target="_blank">YouTube &#8594;</a>
      </div>
    </div>

    <!-- Reddit r/ekstraklasa -->
    <div class="box">
      <div class="box-hdr" style="background:#003310;">&#128172; r/ekstraklasa <span class="sub">Reddit</span></div>
      {reddit_ekstra_html}
      <div style="text-align:right;padding:6px 14px;font-size:11px;color:var(--muted);">
        <a href="https://reddit.com/r/ekstraklasa" target="_blank">r/ekstraklasa &#8594;</a>
      </div>
    </div>

    <div class="box" id="radar">
      <div class="box-hdr" style="background:#00356a;">&#128308;&#128309; FC Barcelona Radar</div>
      {radar_html(BARCA_RADAR)}
    </div>

    <div class="box">
      <div class="box-hdr" style="background:#38003c;">&#128995; Premier League Radar</div>
      {radar_html(PL_RADAR)}
    </div>

    <div class="box">
      <div class="box-hdr" style="background:#8b0000;">&#128993; La Liga Radar</div>
      {radar_html(LALIGA_RADAR)}
    </div>

    <!-- Ekstraklasa — linki reczne (nie w API) -->
    <div class="box">
      <div class="box-hdr" style="background:#003310;">&#127477;&#127473; Ekstraklasa <span class="sub">linki zewnetrzne</span></div>
      <div class="ekstra-item">
        <a href="https://www.sofascore.com/tournament/football/poland/ekstraklasa/77" target="_blank">Tabela i wyniki &#8594;</a>
        <span>Sofascore</span>
      </div>
      <div class="ekstra-item">
        <a href="https://fbref.com/en/comps/36/Ekstraklasa-Stats" target="_blank">Statystyki zaawansowane &#8594;</a>
        <span>FBref</span>
      </div>
      <div class="ekstra-item">
        <a href="https://www.transfermarkt.pl/ekstraklasa/startseite/wettbewerb/PL1" target="_blank">Wyceny zawodnikow &#8594;</a>
        <span>Transfermarkt</span>
      </div>
      <div class="ekstra-item">
        <a href="https://www.90minut.pl" target="_blank">Wyniki i archiwum &#8594;</a>
        <span>90minut.pl</span>
      </div>
    </div>

    <!-- Szybkie linki -->
    <div class="box">
      <div class="box-hdr">&#128279; Szybkie Linki</div>
      <div class="quick-link"><span>Wyniki na zywo</span><a href="https://www.flashscore.pl" target="_blank">Flashscore &#8594;</a></div>
      <div class="quick-link"><span>Statystyki zaawansowane</span><a href="https://fbref.com" target="_blank">FBref &#8594;</a></div>
      <div class="quick-link"><span>Wyceny zawodnikow</span><a href="https://www.transfermarkt.pl" target="_blank">Transfermarkt &#8594;</a></div>
      <div class="quick-link"><span>Live i tabele</span><a href="https://www.sofascore.com" target="_blank">Sofascore &#8594;</a></div>
      <div class="quick-link"><span>Oficjalna UCL</span><a href="https://www.uefa.com" target="_blank">UEFA &#8594;</a></div>
      <div class="quick-link"><span>Polska pilka</span><a href="https://www.90minut.pl" target="_blank">90minut.pl &#8594;</a></div>
    </div>

  </div>

</div>

<footer>
  &#9733; DOBITKA v2.0 &mdash; agregator sportowy dla kibicow bez czasu na chaos &#9733;<br><br>
  Dane: <a href="https://www.football-data.org" target="_blank">football-data.org</a> (CC BY 4.0)
  &nbsp;|&nbsp; <a href="https://www.thesportsdb.com" target="_blank">TheSportsDB</a>
  &nbsp;|&nbsp; <a href="https://understat.com" target="_blank">Understat</a> (xG)
  &nbsp;|&nbsp; <a href="https://reddit.com/r/soccer" target="_blank">Reddit</a>
  &nbsp;|&nbsp; <a href="https://weszlo.com" target="_blank">Weszlo.com</a>
  &nbsp;|&nbsp;
  Linki prowadza do oryginalnych zrodel. Opisy redakcji wlasne.<br>
  Zero trackerow. Zero reklam.
</footer>

<script>{js_code}</script>
</body>
</html>'''

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'OK: index.html wygenerowany ({updated})')


if __name__ == '__main__':
    generate()
