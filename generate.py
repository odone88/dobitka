#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DOBITKA — generator strony HTML
Źródło: football-data.org (darmowe, legalne API)
Uruchamiany co 2h przez GitHub Actions
"""

import requests
import os
import time
from datetime import datetime, timedelta, timezone

API_KEY = os.environ.get('FOOTBALL_DATA_KEY', '')
BASE    = 'https://api.football-data.org/v4'
HEADERS = {'X-Auth-Token': API_KEY}

# Liga → (kod API, nazwa, flaga, link Sofascore jako fallback)
LEAGUES = [
    ('PL',  'Premier League',    '&#127988;', 'https://www.sofascore.com/tournament/football/england/premier-league/17'),
    ('PD',  'La Liga',           '&#127466;&#127480;', 'https://www.sofascore.com/tournament/football/spain/laliga/8'),
    ('SA',  'Serie A',           '&#127470;&#127481;', 'https://www.sofascore.com/tournament/football/italy/serie-a/23'),
    ('FL1', 'Ligue 1',           '&#127467;&#127479;', 'https://www.sofascore.com/tournament/football/france/ligue-1/34'),
    ('CL',  'Champions League',  '&#11088;',  'https://www.sofascore.com/tournament/football/europe/uefa-champions-league/7'),
    ('PPL', 'Ekstraklasa',       '&#127477;&#127473;', 'https://www.sofascore.com/tournament/football/poland/ekstraklasa/77'),
]

# ─── TREŚCI EDYTOWALNE — zmieniaj tutaj linki i ciekawostki ──────────────────

HOT_LINKS = [
    {
        'category': 'Liga Mistrzów',
        'cat_class': 'ucl',
        'title': 'Champions League — terminarz, wyniki, tabela',
        'url': 'https://www.uefa.com/uefachampionsleague/',
        'desc': 'Faza pucharowa UCL to najpiękniejsze 90 minut w kalendarzu kibiców — lub najgorsze, jeśli grasz o awans z jednobramkową zaliczką. Pełny terminarz i wyniki na stronie UEFA.',
        'source': 'UEFA.com',
    },
    {
        'category': 'La Liga',
        'cat_class': 'laliga',
        'title': 'Yamal vs Vinicius — młodość kontra doświadczenie, Barceloneta kontra Bernabéu',
        'url': 'https://fbref.com/en/comps/12/La-Liga-Stats',
        'desc': 'Klasico w tym sezonie to osobny gatunek dramaturgii. Kompletne statystyki zawodników i drużyn La Ligi na FBref — jeśli liczby są twoją miłością.',
        'source': 'FBref.com',
    },
    {
        'category': 'Premier League',
        'cat_class': 'pl',
        'title': 'Premier League — gdzie kupują za miliardy, gdzie grają na wynik',
        'url': 'https://fbref.com/en/comps/9/Premier-League-Stats',
        'desc': 'Liga z największymi budżetami świata i najlepszą atmosferą. Statystyki, xG, pressowanie — wszystko co trzeba na FBref.',
        'source': 'FBref.com',
    },
    {
        'category': 'Ekstraklasa',
        'cat_class': 'ekstraklasa',
        'title': 'Ekstraklasa — bo warto wiedzieć co u sąsiadów słychać',
        'url': 'https://www.sofascore.com/tournament/football/poland/ekstraklasa/77',
        'desc': 'Polska liga ma swoje uroki — niespodzianki, derby i od czasu do czasu piłkę, którą naprawdę warto obejrzeć. Wyniki i tabela na żywo.',
        'source': 'Sofascore',
    },
    {
        'category': 'Transfery',
        'cat_class': '',
        'title': 'Transfermarkt — ile naprawdę wart jest twój ulubiony zawodnik?',
        'url': 'https://www.transfermarkt.pl',
        'desc': 'Biblia wycen piłkarskich. Sprawdzasz czy nowy nabytek twojego klubu jest warty tyle co za niego zapłacono — Transfermarkt nie kłamie (przynajmniej nie bardziej niż agenci).',
        'source': 'Transfermarkt.pl',
    },
]

CIEKAWOSTKI = [
    ('<strong>Lamine Yamal urodził się 13 lipca 2007</strong> — dokładnie w dniu finału Mundialu, kiedy Iniesta świętował złoto. 17 lat później Yamal wygrał EURO 2024 z tą samą reprezentacją. Scenarzysta piłki nożnej ma niesamowite poczucie humoru.'),
    ('<strong>Zinedine Zidane</strong> zakończył karierę główką w Materazziego w finale MŚ 2006. Ten sam Zidane zdobył dwa gole głową w finale MŚ 1998. Symetria doskonała — nikt jej nie zaplanował, ale wszyscy pamiętają.'),
    ('<strong>Lech Poznań w 1992 roku</strong> dotarł do ćwierćfinału Ligi Mistrzów i grał z Barceloną Johana Cruyffa — Dreamteamem z Guardiolą, Stoichkovem i Laudrupem. Przegrali 1-3 i 0-4, ale historia jest legendarna. Polska liga miała swój moment.'),
    ('<strong>Ronald Koeman</strong> strzelił ponad 80 goli z rzutów wolnych przez całą karierę. Był obrońcą. Większość napastników mogłaby mu pozazdrościć skuteczności.'),
    ('<strong>FC Barcelona przez ponad 100 lat</strong> (1899–2006) grała bez żadnego sponsora na koszulce. Potem wzięła kasę od Qatar Foundation i wszystko się zmieniło. Przynajmniej byli ostatni z wielkich, którzy to zrobili.'),
    ('<strong>Cristiano Ronaldo i Neymar Jr</strong> obchodzą urodziny tego samego dnia — 5 lutego. CR7 w 1985, Neymar w 1992. Dwie największe gwiazdy swojej generacji, jeden dzień urodzin. Kosmos.'),
    ('<strong>Erling Haaland w sezonie 2022/23</strong> strzelił 52 gole we wszystkich rozgrywkach dla Manchesteru City. Premier League, FA Cup, UCL — wszędzie. W poprzednim sezonie Salah pobił rekord PL z 32 golami. Haaland przekroczył to w samej lidze.'),
    ('<strong>Robert Lewandowski w sezonie 2020/21</strong> strzelił 41 goli w Bundeslidze, bijąc rekord Gerda Müllera z 1971/72, który stał przez 49 lat. Bayern wygrał ligę, a Lewy dostał... drugie miejsce w Złotej Piłce przez COVID. Sprawiedliwość jest ślepa.'),
]

BARCA_RADAR = [
    ('Wyniki i tabela La Liga', 'https://www.sofascore.com/team/football/fc-barcelona/2817', 'Sofascore — aktualne statystyki, tabela, terminarz FC Barcelona'),
    ('Lamine Yamal', 'https://www.transfermarkt.pl/lamine-yamal/profil/spieler/983709', 'Transfermarkt — profil, wycena, historia transferów'),
    ('Statystyki zaawansowane', 'https://fbref.com/en/squads/206d90db/FC-Barcelona-Stats', 'FBref — xG, pressing, posiadanie — Barca pod lupą'),
]

PL_RADAR = [
    ('Tabela Premier League', 'https://www.sofascore.com/tournament/football/england/premier-league/17#tab:standings', 'Sofascore — aktualna tabela, wyniki, strzelcy'),
    ('Statystyki ligowe', 'https://fbref.com/en/comps/9/Premier-League-Stats', 'FBref — zaawansowane statystyki wszystkich drużyn PL'),
    ('Transfery i wyceny', 'https://www.transfermarkt.pl/premier-league/startseite/wettbewerb/GB1', 'Transfermarkt — wartości rynkowe zawodników Premier League'),
]

LALIGA_RADAR = [
    ('Tabela La Liga', 'https://www.sofascore.com/tournament/football/spain/laliga/8#tab:standings', 'Sofascore — aktualna tabela, wyniki, strzelcy La Liga'),
    ('Statystyki ligowe', 'https://fbref.com/en/comps/12/La-Liga-Stats', 'FBref — zaawansowane statystyki La Liga'),
    ('Transfery i wyceny', 'https://www.transfermarkt.pl/primera-division/startseite/wettbewerb/ES1', 'Transfermarkt — wartości rynkowe zawodników La Liga'),
]

# ─── CYTATY Z KONFERENCJI PRASOWYCH ──────────────────────────────────────────
# Odśwież raz w tygodniu — wybierz najlepsze ze świata piłki
CYTATY = [
    {
        'osoba':  'Pep Guardiola',
        'klub':   'Manchester City',
        'cytat':  '"Nie rozmawiamy o remisach. Gramy żeby wygrywać. Remis to porażka w przebraniu."',
        'kontekst': 'po konferencji przed meczem ligowym',
    },
    {
        'osoba':  'Carlo Ancelotti',
        'klub':   'Real Madryt',
        'cytat':  '"Real Madryt nigdy nie jest favoritem. Ale zawsze wygrywa."',
        'kontekst': 'przed fazą pucharową UCL',
    },
    {
        'osoba':  'Jude Bellingham',
        'klub':   'Real Madryt',
        'cytat':  '"Kiedy masz 20 lat i grasz w Realu, nie pytasz czy jesteś gotowy. Po prostu grasz."',
        'kontekst': 'wywiad dla Sky Sports',
    },
    {
        'osoba':  'Lamine Yamal',
        'klub':   'FC Barcelona',
        'cytat':  '"Mam 17 lat i gram dla Barcelony. To jedyne co wiem. Reszta to szum."',
        'kontekst': 'konferencja prasowa przed El Clasico',
    },
]

# ─── NEYMAR — AKTUALNY STATUS ─────────────────────────────────────────────────
NEYMAR_UPDATE = {
    'headline': 'Neymar Jr i reprezentacja Brazylii — saga trwa',
    'tresc': (
        'Po ponad roku rehabilitacji po zerwaniu ACL Neymar wrócił do gry w Al-Hilal, '
        'ale jego miejsce w selekcji kadry Brazylii pozostaje otwarte. '
        'Selekcjoner Dorival Júnior jasno: <strong>"Neymar musi wygrać zdrowie, '
        'zanim wygramy z nim mecz."</strong> '
        'Sam zainteresowany na Instagramie: <em>"Wróce. Nie wiem kiedy, ale wróce."</em> '
        'Kibice Brazylii czekają. Reszta świata też — bo futbol bez Neymara jest o klasę nudniejszy.'
    ),
    'link': 'https://www.transfermarkt.pl/neymar/profil/spieler/68290',
}

# ─── BAZA URODZIN PIŁKARZY ────────────────────────────────────────────────────
# (miesiąc, dzień, imię i nazwisko, rok urodzenia, opis)
FAMOUS_BIRTHDAYS = [
    (1,  4,  'Toni Kroos',              1990, 'legenda Realu Madryt i Niemiec, mistrz precyzji'),
    (1, 18,  'Pep Guardiola',           1971, 'trener-geniusz, wychowanek i ikona FC Barcelona'),
    (1, 25,  'Xavi Hernandez',          1980, 'architekt tikitaki, dzisiaj trener Barcy'),
    (2,  2,  'Gerard Pique',            1987, 'centralny obrońca Barcelony, mąż Shakiry'),
    (2,  5,  'Cristiano Ronaldo',       1985, 'CR7 — pięciokrotna Złota Piłka, fenomen sportu'),
    (2,  5,  'Neymar Jr',               1992, 'brazylijski czarodziej — ten sam dzień urodzin co CR7!'),
    (2, 28,  'Arkadiusz Milik',         1994, 'polska dziewiątka, gol na EURO 2020 i seria A'),
    (3, 11,  'Didier Drogba',           1978, 'legenda Chelsea — bohater finału UCL 2012 w Monachium'),
    (3, 21,  'Ronaldinho',              1980, 'Zlatá lopta 2005, geniusz sambowej piłki'),
    (3, 21,  'Antoine Griezmann',       1991, 'mistrz świata 2018, wierny sługa Atlético'),
    (3, 27,  'Manuel Neuer',            1986, 'rewolucja na pozycji bramkarza, legenda Bayernu'),
    (3, 30,  'Sergio Ramos',            1986, 'kapitan Realu, mistrz kartek i goli w doliczonym czasie'),
    (4, 10,  'Roberto Carlos',          1973, 'lewy obrońca z rakietą w lewej nodze, legenda Realu'),
    (4, 18,  'Wojciech Szczęsny',       1990, 'polska jedynka — Arsenal, Juventus, Barcelona'),
    (4, 19,  'Karim Benzema',           1987, 'Zlota Pilka 2022, cichobohater Realu przez 14 lat'),
    (4, 25,  'Johan Cruyff',            1947, 'Total Football, legenda Ajaksu i Barcelony (1947-2016)'),
    (5,  2,  'David Beckham',           1975, 'ikona lat 90. i 2000., styl i futbol w jednym'),
    (5, 11,  'Andres Iniesta',          1984, 'gol w finale MŚ 2010, czysta dusza tikitaki'),
    (5, 28,  'Phil Foden',              2000, 'The Stockport Iniesta — filar Manchesteru City'),
    (5, 30,  'Steven Gerrard',          1980, 'kapitan Liverpoolu, serce i dusza Anfield'),
    (6, 15,  'Mohamed Salah',           1992, 'egipski faraon, maszyna do goli w Liverpoolu'),
    (6, 20,  'Frank Lampard',           1978, 'najskuteczniejszy pomocnik Chelsea w historii'),
    (6, 20,  'Piotr Zielinski',         1994, 'polskie złoto — Napoli, Inter i serce pomocnika'),
    (6, 21,  'Michel Platini',          1955, 'trzykrotna Złota Piłka, legenda Juventusu'),
    (6, 23,  'Zinedine Zidane',         1972, 'trzy Złote Piłki, dwie główki w finale MŚ 1998, jedna w 2006'),
    (6, 24,  'Lionel Messi',            1987, 'La Pulga — osmiokrotna Zlota Pilka, mistrz swiata 2022'),
    (6, 26,  'Paolo Maldini',           1968, 'AC Milan na zawsze, obrońca absolutny wszech czasów'),
    (6, 28,  'Kevin De Bruyne',         1991, 'belgijski mózg Manchesteru City'),
    (6, 29,  'Jude Bellingham',         2003, 'angielski diament Realu Madryt — sezon debiutancki z bajki'),
    (7,  8,  'Son Heung-min',           1992, 'koreański as Tottenhamu, ulubieniec kibiców na całym świecie'),
    (7, 12,  'Vinicius Jr',             2000, 'brazylijska rakieta Realu Madryt, gol w finale UCL 2022'),
    (7, 13,  'Lamine Yamal',            2007, 'urodzony w dniu finału MŚ 2010 — przeznaczenie czeka'),
    (7, 21,  'Erling Haaland',          2000, 'norweska maszyna — 52 gole w sezonie debiutanckim w PL'),
    (7, 28,  'Harry Kane',              1993, 'król strzelców Premier League bez trofeum... do Bayernu'),
    (8,  5,  'Gavi',                    2004, 'serce Barcelony, następca Iniesty w stylu i duchu'),
    (8, 17,  'Thierry Henry',           1977, 'legenda Arsenalu, Le Roi, ręka w eliminacjach MŚ 2010'),
    (8, 21,  'Robert Lewandowski',      1988, 'polska dziewiątka — 41 goli w Bundeslidze, rekord Müllera'),
    (9,  9,  'Luka Modric',             1985, 'Złota Piłka 2018, 38-latek wciąż najlepszy w swoim fachu'),
    (9, 18,  'Ronaldo Nazario',         1976, 'R9 — najlepszy napastnik wszech czasów według wielu'),
    (10,  3, 'Zlatan Ibrahimovic',      1981, 'Złoty Bóg, akrobata, legenda europejskiego futbolu'),
    (10, 23, 'Pele',                    1940, 'O Rei — trzykrotny mistrz swiata, do konca 2022'),
    (10, 24, 'Wayne Rooney',            1985, 'legenda Man United, najskuteczniejszy strzelec Three Lions'),
    (10, 30, 'Diego Maradona',          1960, 'Bóg piłki — Ręka Boga, gol stulecia, 1986 cały on'),
    (10, 31, 'Marco van Basten',        1964, 'trzykrotna Złota Piłka, gol w finale EURO 1988'),
    (10, 31, 'Marcus Rashford',         1997, 'szybka noga Man United z Old Trafford'),
    (11,  7, 'Rio Ferdinand',           1978, 'wódz obrony Man United w czasach chwały Fergusona'),
    (11, 25, 'Xabi Alonso',             1981, 'mistrz podania — Liverpool, Real, Bayern, Leverkusen jako trener'),
    (12,  7, 'John Terry',              1980, 'kapitan Chelsea, lider przez dekadę na Stamford Bridge'),
    (12, 14, 'Michael Owen',            1979, 'Złota Piłka 2001, błysk kariery w Liverpoolu i Realu'),
    (12, 14, 'Jakub Blaszczykowski',    1985, 'Kuba — duma polskiej piłki, Dortmund i Fiorentina'),
    (12, 20, 'Kylian Mbappe',           1998, 'następca Zidanea? Nie — własna legenda w budowie'),
]

# ─── WIBE DRUŻYN — do zapowiedzi meczów ──────────────────────────────────────
TEAM_VIBES = {
    'Chelsea':          'Blues ze Stamford Bridge — mój klub, który potrafi wygrać UCL i zwolnić trenera w tym samym tygodniu',
    'Man City':         'niebieski moloch grający jak algorytm zaprojektowany przez Guardiolę',
    'Arsenal':          'Gooners — znowu "w tym sezonie"? Może tym razem naprawdę tak będzie',
    'Liverpool':        "You'll Never Walk Alone — szczególnie gdy zostajesz z 10. po czerwonej",
    'Man United':       'Red Devils — wciąż największa marka, trochę mniej wygranych ostatnio',
    'Tottenham':        'Spurs — jak mieć talent i systematycznie go marnować, podręcznik w 20 rozdziałach',
    'Barcelona':        'Barca — Yamal, Pedri, Lewandowski. Jedna z najpiękniejszych drużyn na świecie w tym momencie',
    'Real Madrid':      'Los Blancos — wygrywają UCL statystycznie co dwa sezony. Nikt nie wie jak.',
    'Atletico':         'Atlético — bunkier Simeone, gol w 89. minucie i mistrzostwo w rytmie zawał-serce',
    'Bayern':           'Bayern Monachium — Bundesliga od lat ich, UCL od czasu do czasu',
    'Dortmund':         'BVB — żółto-czarna adrenalina i coroczny zawód w finiszu sezonu',
    'Juventus':         'Stara Dama — zmęczona blaskiem, ale na kolana nie padnie',
    'Inter':            'Nerazzurri — aktualnie bezspornie najlepsza drużyna we Włoszech',
    'AC Milan':         'Rossoneri — legenda San Siro z lekką nostalgią za Maldiniemi Shevchenko',
    'Napoli':           'Partenopei — Maradona w niebie, Napoli na ziemi wciąż szaleje',
    'Paris':            'PSG — galaktyki gwiazd co rok, a UCL nadal ucieka jak Mbappe do Madrytu',
    'Leverkusen':       'Apteka — mistrzowie Niemiec 2024 bez jednej porażki. Xabi Alonso wie co robi.',
    'Ajax':             'Ajax Amsterdam — fabryka talentów na eksport do całej Europy',
    'Lech':             'Kolejorz — duma Poznania i stały reprezentant Polski w europejskich pucharach',
    'Legia':            'Legia Warszawa — największy klub Polski, co roku walczy o Europę',
    'Wisla':            'Biała Gwiazda Kraków — moje miasto, czas na powrót do ekstraklasy',
    'Cracovia':         'Pasy Kraków — derby przy Reymonta zawsze grzeje krew',
}

# ─── FUNKCJE API ──────────────────────────────────────────────────────────────

def fetch(path, delay=7):
    """Pobiera dane z API. Delay 7s żeby nie przekroczyć 10 req/min."""
    if not API_KEY:
        return None
    time.sleep(delay)
    try:
        r = requests.get(f'{BASE}{path}', headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return r.json()
        print(f'  API {r.status_code}: {path}')
        return None
    except Exception as e:
        print(f'  Blad polaczenia: {e}')
        return None

def get_standings(code):
    return fetch(f'/competitions/{code}/standings')

def get_matches(code, status='SCHEDULED', limit=5):
    return fetch(f'/competitions/{code}/matches?status={status}&limit={limit}')

def fetch_day(date_str):
    """Pobiera wszystkie mecze na dany dzień (YYYY-MM-DD)."""
    return fetch(f'/matches?dateFrom={date_str}&dateTo={date_str}')

def filter_supported(data):
    """Filtruje mecze do obsługiwanych lig."""
    if not data or not data.get('matches'):
        return []
    supported = {code for code, *_ in LEAGUES}
    return [m for m in data['matches'] if m.get('competition', {}).get('code') in supported]

# ─── GENERATORY HTML ─────────────────────────────────────────────────────────

def standings_table(code, fallback_url):
    data = get_standings(code)
    if not data:
        return f'<p class="no-data">Brak danych — sprawdź <a href="{fallback_url}" target="_blank">Sofascore</a></p>'
    try:
        table = data['standings'][0]['table'][:10]
    except (KeyError, IndexError):
        return f'<p class="no-data">Brak danych — sprawdź <a href="{fallback_url}" target="_blank">Sofascore</a></p>'

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
        if pos <= 4:              color = 'style="color:#00cc55"'
        elif pos in (5, 6):       color = 'style="color:#ffaa44"'
        elif pos >= len(table)-2: color = 'style="color:#ff5544"'

        rows += f'''<tr {color}>
          <td class="s-pos">{pos}</td>
          <td class="s-team">{name}</td>
          <td class="s-num">{m}</td><td class="s-num">{w}</td>
          <td class="s-num">{d}</td><td class="s-num">{l}</td>
          <td class="s-num s-gd">{sign}{gd}</td>
          <td class="s-pts">{pts}</td>
        </tr>\n'''

    return f'''<table class="standings-table">
      <tr class="s-header">
        <th class="s-pos">#</th><th class="s-team">Druzyna</th>
        <th class="s-num">M</th><th class="s-num">W</th>
        <th class="s-num">R</th><th class="s-num">L</th>
        <th class="s-num">RB</th><th class="s-pts">PKT</th>
      </tr>
      {rows}
    </table>'''

def fmt_time(utc_str):
    """UTC ISO → polska godzina CET/CEST."""
    try:
        dt = datetime.fromisoformat(utc_str.replace('Z', '+00:00'))
        local = dt + timedelta(hours=1)
        return local.strftime('%d.%m %H:%M')
    except Exception:
        return '?'

def results_html(code, fallback_url):
    data = get_matches(code, status='FINISHED', limit=6)
    if not data or not data.get('matches'):
        return f'<p class="no-data">Brak wynikow — <a href="{fallback_url}" target="_blank">Sofascore</a></p>'

    html = ''
    for m in reversed(data['matches'][:6]):
        home  = m['homeTeam'].get('shortName') or m['homeTeam']['name']
        away  = m['awayTeam'].get('shortName') or m['awayTeam']['name']
        sh    = m['score']['fullTime'].get('home')
        sa    = m['score']['fullTime'].get('away')
        if sh is None or sa is None:
            continue
        cls = 'draw'
        if sh > sa: cls = 'win-h'
        if sa > sh: cls = 'win-a'
        html += f'''<div class="result-row">
          <span class="r-home">{home}</span>
          <span class="r-score {cls}">{sh}:{sa}</span>
          <span class="r-away">{away}</span>
        </div>\n'''
    return html or f'<p class="no-data">Brak wynikow — <a href="{fallback_url}" target="_blank">Sofascore</a></p>'

def upcoming_html(code, fallback_url):
    data = get_matches(code, status='SCHEDULED', limit=5)
    if not data or not data.get('matches'):
        return f'<p class="no-data">Brak terminarza — <a href="{fallback_url}" target="_blank">Sofascore</a></p>'

    html = ''
    for m in data['matches'][:5]:
        home = m['homeTeam'].get('shortName') or m['homeTeam']['name']
        away = m['awayTeam'].get('shortName') or m['awayTeam']['name']
        t    = fmt_time(m.get('utcDate', ''))
        html += f'''<div class="upcoming-row">
          <span class="u-home">{home}</span>
          <span class="u-vs">vs</span>
          <span class="u-away">{away}</span>
          <span class="u-time">{t}</span>
        </div>\n'''
    return html or f'<p class="no-data">Brak danych — <a href="{fallback_url}" target="_blank">Sofascore</a></p>'

# ─── NOWE SEKCJE: DZISIAJ / WCZORAJ / URODZINY ───────────────────────────────

def birthdays_html(today):
    """Urodziny znanych pilkarzy dzisiaj."""
    m, d = today.month, today.day
    todays = [(name, year, desc) for (bm, bd, name, year, desc) in FAMOUS_BIRTHDAYS if bm == m and bd == d]
    if not todays:
        return '<p class="no-data">Dzis brak znanych urodzin w bazie DOBITKA.<br><small>Baza zawiera ~50 znanych pilkarzy i trenerow.</small></p>'
    html = ''
    for name, year, desc in todays:
        age = today.year - year
        html += f'''<div class="birthday-item">
          <span class="bday-cake">&#127874;</span>
          <div>
            <strong class="bday-name">{name}</strong>
            <span class="bday-age"> &mdash; konczy {age} lat</span>
            <p class="bday-desc">{desc}</p>
          </div>
        </div>\n'''
    return html

def todays_matches_section(matches, today_label):
    """Dzisiejsze mecze — zaplanowane i juz grane."""
    if not matches:
        return f'<p class="no-data">Dzis brak meczow w obsługiwanych ligach.<br><a href="https://www.flashscore.pl" target="_blank">Flashscore →</a></p>'
    html = ''
    for m in matches[:10]:
        home   = m['homeTeam'].get('shortName') or m['homeTeam']['name']
        away   = m['awayTeam'].get('shortName') or m['awayTeam']['name']
        t      = fmt_time(m.get('utcDate', ''))
        status = m.get('status', '')
        comp   = m.get('competition', {}).get('name', '')

        hour = t.split(' ')[-1] if ' ' in t else t

        if status in ('FINISHED',):
            sh = m['score']['fullTime'].get('home')
            sa = m['score']['fullTime'].get('away')
            if sh is None or sa is None:
                continue
            cls = 'draw'
            if sh > sa: cls = 'win-h'
            if sa > sh: cls = 'win-a'
            html += f'''<div class="td-row finished">
              <span class="td-comp">{comp[:12]}</span>
              <span class="td-home">{home}</span>
              <span class="td-score {cls}">{sh}:{sa}</span>
              <span class="td-away">{away}</span>
              <span class="td-status">FT</span>
            </div>\n'''
        elif status in ('IN_PLAY', 'PAUSED', 'HALFTIME'):
            sh = m['score'].get('fullTime', {}).get('home') or m['score'].get('halfTime', {}).get('home', 0)
            sa = m['score'].get('fullTime', {}).get('away') or m['score'].get('halfTime', {}).get('away', 0)
            html += f'''<div class="td-row live">
              <span class="td-comp">{comp[:12]}</span>
              <span class="td-home">{home}</span>
              <span class="td-score draw live-score">{sh}:{sa}</span>
              <span class="td-away">{away}</span>
              <span class="td-status blink">LIVE</span>
            </div>\n'''
        else:
            html += f'''<div class="td-row">
              <span class="td-comp">{comp[:12]}</span>
              <span class="td-home">{home}</span>
              <span class="td-score draw">vs</span>
              <span class="td-away">{away}</span>
              <span class="td-status td-time">{hour}</span>
            </div>\n'''
    return html or f'<p class="no-data">Brak meczow — <a href="https://www.flashscore.pl" target="_blank">Flashscore</a></p>'

def yesterdays_results_section(matches):
    """Wyniki z wczoraj."""
    finished = [m for m in matches if m.get('status') == 'FINISHED']
    if not finished:
        return '<p class="no-data">Brak wynikow z wczoraj w obsługiwanych ligach.<br><a href="https://www.flashscore.pl" target="_blank">Flashscore →</a></p>'
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
        html += f'''<div class="td-row">
          <span class="td-comp">{comp[:12]}</span>
          <span class="td-home">{home}</span>
          <span class="td-score {cls}">{sh}:{sa}</span>
          <span class="td-away">{away}</span>
          <span class="td-status">FT</span>
        </div>\n'''
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
        home     = m['homeTeam'].get('shortName') or m['homeTeam']['name']
        away     = m['awayTeam'].get('shortName') or m['awayTeam']['name']
        t        = fmt_time(m.get('utcDate', ''))
        comp     = m.get('competition', {}).get('name', '')
        hv       = _find_vibe(home)
        av       = _find_vibe(away)
        if hv or av:
            previews.append((home, away, t, comp, hv, av))

    if not previews:
        return ''

    hour = lambda t: t.split(' ')[-1] if ' ' in t else t

    html = ''
    for home, away, t, comp, hv, av in previews[:5]:
        if hv and av:
            tekst = (f'<strong>{home}</strong> to {hv}. '
                     f'Naprzeciwko staje <strong>{away}</strong> &mdash; {av}. '
                     f'Kick-off o {hour(t)}, kto bardziej potrzebuje tych 3 punktow?')
        elif hv:
            tekst = (f'<strong>{home}</strong> &mdash; {hv} &mdash; podejmuje dzis '
                     f'<strong>{away}</strong> o {hour(t)}. Ciekawe kto bardziej glodny wyniku.')
        else:
            tekst = (f'<strong>{away}</strong> &mdash; {av} &mdash; wyjedza na teren '
                     f'<strong>{home}</strong> o {hour(t)}. Goscie zwykle wiedza co tracą.')

        html += f'''<div class="preview-item">
          <div class="preview-match">{home} <span class="preview-vs">vs</span> {away}
            <span class="preview-meta">{comp} &nbsp;|&nbsp; {t}</span>
          </div>
          <div class="preview-text">{tekst}</div>
        </div>\n'''
    return html

# ─── BUDOWANIE HTML ───────────────────────────────────────────────────────────

def hot_links_html():
    html = ''
    for lnk in HOT_LINKS:
        cat_cls = lnk.get('cat_class', '')
        html += f'''<div class="link-item">
          <div class="link-cat {cat_cls}">{lnk["category"]}</div>
          <div class="link-title"><a href="{lnk["url"]}" target="_blank">{lnk["title"]}</a></div>
          <div class="link-desc">{lnk["desc"]}</div>
          <div class="link-source">&#9658; {lnk["source"]}</div>
        </div>\n'''
    return html

def ciekawostki_html():
    html = ''
    for i, c in enumerate(CIEKAWOSTKI, 1):
        html += f'''<div class="ciekawostka-item">
          <span class="ciek-num">#{i:02d}</span>
          <p>{c}</p>
        </div>\n'''
    return html

def radar_html(items):
    html = ''
    for label, url, desc in items:
        html += f'''<div class="radar-item">
          <span class="r-bullet">&#9733;</span>
          <div><a href="{url}" target="_blank">{label}</a><br>
          <span class="r-desc">{desc}</span></div>
        </div>\n'''
    return html

def tables_nav_html():
    html = ''
    for code, name, flag, url in LEAGUES:
        html += f'<a href="{url}" target="_blank"><span>{flag}</span> {name}</a>\n'
    return html

def cytaty_html():
    html = ''
    for c in CYTATY:
        html += f'''<div class="cytat-item">
          <div class="cytat-text">{c["cytat"]}</div>
          <div class="cytat-meta"><strong>{c["osoba"]}</strong> ({c["klub"]}) &mdash; <em>{c["kontekst"]}</em></div>
        </div>\n'''
    return html

def neymar_html():
    n = NEYMAR_UPDATE
    return f'''<div class="neymar-box">
      <div class="neymar-headline">&#128308; {n["headline"]}</div>
      <div class="neymar-text">{n["tresc"]}</div>
      <div class="neymar-link"><a href="{n["link"]}" target="_blank">Transfermarkt — profil Neymara &#8594;</a></div>
    </div>'''

def generate():
    now_utc  = datetime.now(timezone.utc)
    now_pl   = now_utc + timedelta(hours=1)
    updated  = now_pl.strftime('%d.%m.%Y %H:%M')
    today_str = now_pl.strftime('%Y-%m-%d')
    yest_str  = (now_pl - timedelta(days=1)).strftime('%Y-%m-%d')
    today_label = now_pl.strftime('%d.%m.%Y')
    yest_label  = (now_pl - timedelta(days=1)).strftime('%d.%m.%Y')

    print('Pobieram dane z football-data.org...')

    # Dzisiejsze mecze i wyniki z wczoraj (2 wywołania API)
    print('  Dzisiejsze mecze...')
    today_raw = fetch_day(today_str)
    today_matches = filter_supported(today_raw)

    print('  Wczorajsze wyniki...')
    yest_raw  = fetch_day(yest_str)
    yest_matches = filter_supported(yest_raw)

    # Dane ligowe (standings + wyniki + terminarz)
    league_data = {}
    for code, name, flag, fallback in LEAGUES:
        print(f'  {name}...')
        league_data[code] = {
            'name':     name,
            'flag':     flag,
            'fallback': fallback,
            'standing': standings_table(code, fallback),
            'results':  results_html(code, fallback),
            'upcoming': upcoming_html(code, fallback),
        }

    # HTML sekcji TOP
    bdays_html       = birthdays_html(now_pl)
    today_sec_html   = todays_matches_section(today_matches, today_label)
    yest_sec_html    = yesterdays_results_section(yest_matches)
    previews_sec     = match_previews_html(today_matches)

    # Zbuduj sekcje tabel
    standings_sections = ''
    for code, name, flag, fallback in LEAGUES:
        d = league_data[code]
        standings_sections += f'''<div class="tab-pane" id="tab-{code}">
          <div class="tab-league-title">{flag} {name}</div>
          {d["standing"]}
          <div class="subsection-title">Ostatnie wyniki</div>
          {d["results"]}
          <div class="subsection-title">Najblizsze mecze</div>
          {d["upcoming"]}
        </div>\n'''

    # Tab buttons
    tab_btns = ''
    for i, (code, name, flag, _) in enumerate(LEAGUES):
        active = ' active' if i == 0 else ''
        tab_btns += f'<button class="tab-btn{active}" onclick="showTab(\'{code}\')">{flag} {name}</button>\n'

    previews_block = ''
    if previews_sec:
        previews_block = f'''<div class="previews-wrap">
          <div class="box">
            <div class="box-hdr" style="background:#1a1a00;">&#9997; Zapowiedzi DOBITKA <span class="sub">subiektywnie, bo inaczej sie nie da</span></div>
            {previews_sec}
          </div>
        </div>'''

    css = '''
:root {
  --bg:    #09090f;
  --panel: #0e0e1a;
  --bdr:   #252540;
  --gold:  #FFD700;
  --red:   #CC1100;
  --green: #00BB44;
  --blue:  #0d2060;
  --text:  #cccccc;
  --muted: #555566;
  --link:  #7799ff;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font-family: 'Courier Prime', 'Courier New', monospace; font-size: 14px; line-height: 1.6; }
a { color: var(--link); text-decoration: none; }
a:hover { color: var(--gold); text-decoration: underline; }

/* TICKER */
.ticker-wrap { background: var(--red); overflow: hidden; white-space: nowrap; padding: 5px 0; }
.ticker-label { background: var(--gold); color: #000; font-weight: 700; font-size: 11px; padding: 0 10px; margin-right: 8px; letter-spacing: 1px; font-family: Arial, sans-serif; }
.ticker-text { display: inline-block; animation: scroll 50s linear infinite; font-size: 12px; color: #fff; letter-spacing: 0.5px; font-family: Arial, sans-serif; }
@keyframes scroll { from { transform: translateX(100vw); } to { transform: translateX(-100%); } }

/* HEADER */
header { background: linear-gradient(180deg, #060614 0%, var(--bg) 100%); border-bottom: 3px solid var(--gold); padding: 20px 0 14px; text-align: center; }
.logo { font-family: 'Courier New', monospace; font-size: 42px; font-weight: 900; color: var(--gold); text-shadow: 3px 3px 0 #770000, 5px 5px 0 #330000; letter-spacing: 8px; }
.tagline { font-size: 13px; color: #888; margin-top: 6px; letter-spacing: 3px; text-transform: uppercase; font-family: Arial, sans-serif; }
.updated { font-size: 11px; color: var(--muted); margin-top: 6px; font-family: Arial, sans-serif; }
.updated span { color: var(--gold); }

/* NAV */
nav { background: #0a0a18; border-bottom: 2px solid var(--bdr); text-align: center; padding: 0; }
nav a { display: inline-block; padding: 9px 16px; font-size: 12px; font-weight: 700; color: #aaa; letter-spacing: 1px; text-transform: uppercase; border-right: 1px solid var(--bdr); font-family: Arial, sans-serif; transition: all 0.15s; }
nav a:first-child { border-left: 1px solid var(--bdr); }
nav a:hover { background: var(--blue); color: var(--gold); text-decoration: none; }

/* TOP BAR — 3 kolumny z dzis/wczoraj/urodziny */
.topbar-wrap { max-width: 1100px; margin: 0 auto; padding: 16px 12px 0; display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
.previews-wrap { max-width: 1100px; margin: 0 auto; padding: 0 12px; }

/* LAYOUT */
.container { max-width: 1100px; margin: 0 auto; padding: 16px 12px; display: grid; grid-template-columns: 1fr 340px; gap: 16px; }

/* BOX */
.box { background: var(--panel); border: 1px solid var(--bdr); margin-bottom: 16px; }
.box-hdr { background: var(--blue); padding: 7px 12px; font-weight: 700; color: var(--gold); text-transform: uppercase; letter-spacing: 2px; border-bottom: 2px solid var(--gold); display: flex; justify-content: space-between; align-items: center; font-size: 13px; font-family: Arial, sans-serif; }
.box-hdr .sub { font-size: 10px; color: #aaa; font-weight: 400; text-transform: none; letter-spacing: 0; }
.no-data { padding: 10px 14px; color: var(--muted); font-size: 12px; font-style: italic; }

/* TODAY/YESTERDAY TABLE */
.td-row { padding: 6px 10px; border-bottom: 1px solid var(--bdr); display: grid; grid-template-columns: 65px 1fr 44px 1fr 38px; gap: 4px; align-items: center; font-size: 11px; }
.td-row:last-child { border-bottom: none; }
.td-row.live { background: #110500; }
.td-comp { color: var(--muted); font-size: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.td-home { text-align: right; color: #ccc; font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.td-away { color: #ccc; font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.td-score { text-align: center; font-family: 'Courier New', monospace; font-size: 13px; font-weight: 900; padding: 1px 2px; border: 1px solid #333; }
.td-score.win-h { color: var(--green); border-color: var(--green); }
.td-score.win-a { color: #ff6644; border-color: #ff6644; }
.td-score.draw   { color: #ccc; border-color: #444; }
.td-score.live-score { color: #ffaa00; border-color: #ffaa00; }
.td-status { text-align: right; font-size: 10px; color: var(--muted); font-family: Arial, sans-serif; }
.td-time { color: var(--gold); font-size: 11px; font-family: 'Courier New', monospace; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
.blink { animation: pulse 1.2s ease-in-out infinite; color: #ff4400 !important; font-weight: 700; }

/* URODZINY */
.birthday-item { padding: 10px 12px; border-bottom: 1px solid var(--bdr); display: flex; gap: 10px; align-items: flex-start; }
.birthday-item:last-child { border-bottom: none; }
.bday-cake { font-size: 18px; flex-shrink: 0; line-height: 1.4; }
.bday-name { color: var(--gold); font-size: 13px; font-family: Arial, sans-serif; }
.bday-age { color: #aaa; font-size: 11px; font-family: Arial, sans-serif; }
.bday-desc { font-size: 11px; color: var(--muted); margin-top: 2px; font-style: italic; }

/* ZAPOWIEDZI */
.preview-item { padding: 12px 14px; border-bottom: 1px solid var(--bdr); }
.preview-item:last-child { border-bottom: none; }
.preview-match { font-weight: 700; color: var(--gold); font-size: 14px; margin-bottom: 5px; font-family: Arial, sans-serif; }
.preview-vs { color: var(--muted); font-size: 12px; font-weight: 400; }
.preview-meta { font-weight: 400; color: var(--muted); font-size: 11px; margin-left: 8px; }
.preview-text { font-size: 13px; color: #bbb; line-height: 1.6; }

/* LINKI */
.link-item { padding: 14px; border-bottom: 1px solid var(--bdr); }
.link-item:last-child { border-bottom: none; }
.link-cat { font-size: 10px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 4px; font-family: Arial, sans-serif; color: var(--muted); }
.link-cat.ucl { color: #4488ff; } .link-cat.laliga { color: #cc8800; } .link-cat.pl { color: #7700cc; } .link-cat.ekstraklasa { color: var(--green); }
.link-title { font-size: 17px; font-weight: 700; color: #eee; line-height: 1.2; margin-bottom: 5px; font-family: Arial, sans-serif; }
.link-title a { color: #eee; }
.link-title a:hover { color: var(--gold); }
.link-desc { font-size: 12px; color: #999; line-height: 1.5; font-style: italic; }
.link-source { font-size: 12px; color: var(--muted); margin-top: 5px; }
.link-source::before { content: "▶ "; color: var(--gold); }

/* WYNIKI */
.result-row { padding: 8px 14px; border-bottom: 1px solid var(--bdr); display: grid; grid-template-columns: 1fr 60px 1fr; gap: 6px; align-items: center; font-size: 13px; }
.result-row:last-child { border-bottom: none; }
.r-home { text-align: right; color: #ccc; }
.r-away { text-align: left; color: #ccc; }
.r-score { text-align: center; font-family: 'Courier New', monospace; font-size: 16px; font-weight: 900; padding: 1px 4px; border: 1px solid #333; }
.r-score.win-h { color: var(--green); border-color: var(--green); }
.r-score.win-a { color: #ff6644; border-color: #ff6644; }
.r-score.draw   { color: #ccc; border-color: #444; }

/* NADCHODZACE MECZE */
.upcoming-row { padding: 8px 14px; border-bottom: 1px solid var(--bdr); display: grid; grid-template-columns: 1fr 30px 1fr 60px; gap: 6px; align-items: center; font-size: 12px; }
.upcoming-row:last-child { border-bottom: none; }
.u-home { text-align: right; color: #ccc; }
.u-away { color: #ccc; }
.u-vs { text-align: center; color: var(--muted); font-size: 11px; }
.u-time { text-align: right; font-family: 'Courier New', monospace; color: var(--gold); font-size: 13px; }

/* TABELE LIGOWE — TABS */
.tab-btns { display: flex; flex-wrap: wrap; background: #0a0a18; border-bottom: 1px solid var(--bdr); }
.tab-btn { background: none; border: none; border-right: 1px solid var(--bdr); color: #888; padding: 8px 12px; font-size: 11px; font-family: Arial, sans-serif; font-weight: 600; cursor: pointer; text-transform: uppercase; letter-spacing: 0.5px; transition: all 0.15s; }
.tab-btn:hover { background: var(--blue); color: var(--gold); }
.tab-btn.active { background: var(--blue); color: var(--gold); border-bottom: 2px solid var(--gold); }
.tab-pane { display: none; padding: 12px; }
.tab-pane.active { display: block; }
.tab-league-title { font-weight: 700; font-size: 15px; color: var(--gold); margin-bottom: 10px; font-family: Arial, sans-serif; }
.subsection-title { font-size: 10px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 1.5px; margin: 14px 0 6px; padding-bottom: 4px; border-bottom: 1px solid var(--bdr); font-family: Arial, sans-serif; }

/* STANDINGS TABLE */
.standings-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.standings-table .s-header { color: #666; font-size: 10px; font-family: Arial, sans-serif; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--bdr); }
.standings-table th, .standings-table td { padding: 4px 3px; }
.s-pos { text-align: right; width: 20px; color: #666; }
.s-team { padding-left: 8px !important; }
.s-num { text-align: center; width: 26px; color: #999; }
.s-gd { color: #888 !important; }
.s-pts { text-align: center; width: 30px; color: var(--gold) !important; font-weight: 700; }
.standings-table tr:hover { background: #111125; }

/* CIEKAWOSTKI */
.ciekawostka-item { padding: 12px 14px; border-bottom: 1px solid var(--bdr); display: flex; gap: 10px; }
.ciekawostka-item:last-child { border-bottom: none; }
.ciek-num { font-family: 'Courier New', monospace; font-size: 22px; color: var(--gold); opacity: 0.5; flex-shrink: 0; line-height: 1; }
.ciekawostka-item p { font-size: 13px; color: #aaa; line-height: 1.5; }
.ciekawostka-item p strong { color: #ddd; }

/* RADAR */
.radar-item { padding: 9px 14px; border-bottom: 1px solid var(--bdr); display: flex; gap: 10px; font-size: 13px; }
.radar-item:last-child { border-bottom: none; }
.r-bullet { color: var(--gold); flex-shrink: 0; }
.r-desc { font-size: 11px; color: var(--muted); display: block; }

/* SZYBKIE LINKI */
.quick-link { padding: 8px 14px; border-bottom: 1px solid var(--bdr); display: flex; justify-content: space-between; align-items: center; font-size: 13px; }
.quick-link:last-child { border-bottom: none; }
.quick-link span { color: var(--muted); font-size: 12px; }
.quick-link a { font-weight: 700; }

/* TABLE NAV (prawa kolumna) */
.table-nav { display: flex; flex-direction: column; }
.table-nav a { padding: 9px 14px; border-bottom: 1px solid var(--bdr); font-size: 13px; color: #bbb; display: flex; justify-content: space-between; font-family: Arial, sans-serif; }
.table-nav a:last-child { border-bottom: none; }
.table-nav a::after { content: "→"; color: var(--muted); }
.table-nav a:hover { background: #111125; color: var(--gold); text-decoration: none; }

/* CYTATY */
.cytat-item { padding: 12px 14px; border-bottom: 1px solid var(--bdr); }
.cytat-item:last-child { border-bottom: none; }
.cytat-text { font-size: 14px; color: #ddd; font-style: italic; line-height: 1.5; margin-bottom: 5px; border-left: 3px solid var(--gold); padding-left: 10px; }
.cytat-meta { font-size: 11px; color: var(--muted); font-family: Arial, sans-serif; }
.cytat-meta strong { color: #aaa; }

/* NEYMAR UPDATE */
.neymar-box { padding: 14px; }
.neymar-headline { font-size: 13px; font-weight: 700; color: var(--gold); margin-bottom: 8px; font-family: Arial, sans-serif; }
.neymar-text { font-size: 12px; color: #aaa; line-height: 1.6; margin-bottom: 8px; }
.neymar-text strong { color: #ddd; }
.neymar-text em { color: #bbb; font-style: italic; }
.neymar-link { font-size: 12px; }

/* FOOTER */
footer { background: #050508; border-top: 2px solid var(--bdr); text-align: center; padding: 20px; font-size: 12px; color: var(--muted); font-family: Arial, sans-serif; }
footer a { color: #444; }

@media (max-width: 768px) {
  .topbar-wrap { grid-template-columns: 1fr; }
  .container { grid-template-columns: 1fr; }
  .logo { font-size: 28px; letter-spacing: 4px; }
  nav a { padding: 8px 10px; font-size: 10px; }
  .tab-btn { font-size: 10px; padding: 7px 8px; }
}
'''

    js = '''
function showTab(code) {
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  var pane = document.getElementById('tab-' + code);
  if (pane) pane.classList.add('active');
  document.querySelectorAll('.tab-btn').forEach(b => {
    if (b.getAttribute('onclick').includes(code)) b.classList.add('active');
  });
}
window.onload = function() {
  var first = document.querySelector('.tab-pane');
  if (first) first.classList.add('active');
};
'''

    html = f'''<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DOBITKA — Pilka. Sport. Bez sciemy.</title>
<link href="https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>

<div class="ticker-wrap">
  <span class="ticker-label">&#9658; LIVE</span>
  <span class="ticker-text">
    &#9733; DOBITKA &mdash; aktualizacja co 2 godziny &#9733; Champions League &bull; Premier League &bull; La Liga &bull; Serie A &bull; Ligue 1 &bull; Ekstraklasa &#9733; Wyniki, tabele, linki &mdash; bez sciemy &#9733;
  </span>
</div>

<header>
  <div class="logo">&#9917; DOBITKA</div>
  <div class="tagline">// Pilka. Sport. Bez sciemy. //</div>
  <div class="updated">Ostatnia aktualizacja: <span>{updated}</span> &nbsp;|&nbsp; Dane: <a href="https://www.football-data.org" target="_blank">football-data.org</a></div>
</header>

<nav>
  <a href="#dzisiaj">&#128293; Dzisiaj</a>
  <a href="#linki">&#128293; Linki</a>
  <a href="#tabele">&#128202; Tabele &amp; Wyniki</a>
  <a href="#ciekawostki">&#129504; Ciekawostki</a>
  <a href="#radar">&#128301; Radary</a>
  <a href="https://www.flashscore.pl" target="_blank">&#9889; Live</a>
</nav>

<!-- TOP BAR: Dzisiaj / Wczoraj / Urodziny -->
<div class="topbar-wrap" id="dzisiaj">

  <div>
    <div class="box">
      <div class="box-hdr" style="background:#001a10;">&#9654; DZISIAJ W AKCJI <span class="sub">{today_label}</span></div>
      {today_sec_html}
    </div>
  </div>

  <div>
    <div class="box">
      <div class="box-hdr" style="background:#1a0a00;">&#9664; WCZORAJSZE WYNIKI <span class="sub">{yest_label}</span></div>
      {yest_sec_html}
    </div>
  </div>

  <div>
    <div class="box">
      <div class="box-hdr" style="background:#1a001a;">&#127874; URODZINY PILKARZY <span class="sub">dzisiaj ({today_label})</span></div>
      {bdays_html}
    </div>
  </div>

</div><!-- /topbar-wrap -->

{previews_block}

<div class="container">

  <!-- LEWA KOLUMNA -->
  <div>

    <div class="box" id="linki">
      <div class="box-hdr">&#128293; Gorace Linki <span class="sub">wybrane przez redakcje</span></div>
      {hot_links_html()}
    </div>

    <!-- TABELE I WYNIKI — ZAKŁADKI -->
    <div class="box" id="tabele">
      <div class="box-hdr">&#128202; Tabele, Wyniki &amp; Terminarz <span class="sub">football-data.org</span></div>
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

    <div class="box" id="radar">
      <div class="box-hdr" style="background:#00356A;">&#128308;&#128309; FC Barcelona Radar</div>
      {radar_html(BARCA_RADAR)}
    </div>

    <div class="box">
      <div class="box-hdr" style="background:#38003c;">&#128995; Premier League Radar</div>
      {radar_html(PL_RADAR)}
    </div>

    <div class="box">
      <div class="box-hdr" style="background:#8B0000;">&#128993; La Liga Radar</div>
      {radar_html(LALIGA_RADAR)}
    </div>

    <div class="box">
      <div class="box-hdr">&#128279; Szybkie Linki</div>
      <div class="quick-link"><span>Wyniki na zywo</span><a href="https://www.flashscore.pl" target="_blank">Flashscore &#8594;</a></div>
      <div class="quick-link"><span>Statystyki zaawansowane</span><a href="https://fbref.com" target="_blank">FBref &#8594;</a></div>
      <div class="quick-link"><span>Wyceny zawodnikow</span><a href="https://www.transfermarkt.pl" target="_blank">Transfermarkt &#8594;</a></div>
      <div class="quick-link"><span>Sofascore</span><a href="https://www.sofascore.com" target="_blank">Sofascore &#8594;</a></div>
      <div class="quick-link"><span>Oficjalna UCL</span><a href="https://www.uefa.com" target="_blank">UEFA &#8594;</a></div>
    </div>

  </div>

</div><!-- /container -->

<footer>
  &#9733; DOBITKA &mdash; agregator sportowy dla kibicow bez czasu na chaos &#9733;<br><br>
  Dane: <a href="https://www.football-data.org" target="_blank">football-data.org</a> (CC BY 4.0) &nbsp;|&nbsp;
  Linki prowadza do oryginalnych zrodel. Opisy redakcji wlasne.<br>
  Zero trackerow. Zero reklam.
</footer>

<script>{js}</script>
</body>
</html>'''

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'OK: index.html wygenerowany ({updated})')

if __name__ == '__main__':
    generate()
