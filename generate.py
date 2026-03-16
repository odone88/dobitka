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
    ('PL',  'Premier League',    '🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'https://www.sofascore.com/tournament/football/england/premier-league/17'),
    ('PD',  'La Liga',           '🇪🇸',          'https://www.sofascore.com/tournament/football/spain/laliga/8'),
    ('SA',  'Serie A',           '🇮🇹',          'https://www.sofascore.com/tournament/football/italy/serie-a/23'),
    ('FL1', 'Ligue 1',           '🇫🇷',          'https://www.sofascore.com/tournament/football/france/ligue-1/34'),
    ('CL',  'Champions League',  '⭐',           'https://www.sofascore.com/tournament/football/europe/uefa-champions-league/7'),
    ('PPL', 'Ekstraklasa',       '🇵🇱',          'https://www.sofascore.com/tournament/football/poland/ekstraklasa/77'),
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

# ─── FUNKCJE API ──────────────────────────────────────────────────────────────

def fetch(path, delay=7):
    """Pobiera dane z API. Delay 7s żeby nie przekroczyć 10 req/min."""
    time.sleep(delay)
    try:
        r = requests.get(f'{BASE}{path}', headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return r.json()
        print(f'  API {r.status_code}: {path}')
        return None
    except Exception as e:
        print(f'  Błąd połączenia: {e}')
        return None

def get_standings(code):
    return fetch(f'/competitions/{code}/standings')

def get_matches(code, status='SCHEDULED', limit=5):
    return fetch(f'/competitions/{code}/matches?status={status}&limit={limit}')

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
        <th class="s-pos">#</th><th class="s-team">Drużyna</th>
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
        return f'<p class="no-data">Brak wyników — <a href="{fallback_url}" target="_blank">Sofascore</a></p>'

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
    return html or f'<p class="no-data">Brak wyników — <a href="{fallback_url}" target="_blank">Sofascore</a></p>'

def upcoming_html(code, fallback_url):
    data = get_matches(code, status='SCHEDULED', limit=5)
    if not data or not data.get('matches'):
        return f'<p class="no-data">Brak terminarzа — <a href="{fallback_url}" target="_blank">Sofascore</a></p>'

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

# ─── BUDOWANIE HTML ───────────────────────────────────────────────────────────

def hot_links_html():
    html = ''
    for lnk in HOT_LINKS:
        cat_cls = lnk.get('cat_class', '')
        html += f'''<div class="link-item">
          <div class="link-cat {cat_cls}">{lnk["category"]}</div>
          <div class="link-title"><a href="{lnk["url"]}" target="_blank">{lnk["title"]}</a></div>
          <div class="link-desc">{lnk["desc"]}</div>
          <div class="link-source">▶ {lnk["source"]}</div>
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
          <span class="r-bullet">★</span>
          <div><a href="{url}" target="_blank">{label}</a><br>
          <span class="r-desc">{desc}</span></div>
        </div>\n'''
    return html

def tables_nav_html():
    html = ''
    for code, name, flag, url in LEAGUES:
        html += f'<a href="{url}" target="_blank"><span>{flag}</span> {name}</a>\n'
    return html

def generate():
    now_utc = datetime.now(timezone.utc)
    now_pl  = now_utc + timedelta(hours=1)
    updated = now_pl.strftime('%d.%m.%Y %H:%M')

    print('Pobieram dane z football-data.org...')

    # Zbierz dane dla każdej ligi
    league_data = {}
    for code, name, flag, fallback in LEAGUES:
        print(f'  {flag} {name}...')
        league_data[code] = {
            'name':     name,
            'flag':     flag,
            'fallback': fallback,
            'standing': standings_table(code, fallback),
            'results':  results_html(code, fallback),
            'upcoming': upcoming_html(code, fallback),
        }

    # Zbuduj sekcje tabel
    standings_sections = ''
    for code, name, flag, fallback in LEAGUES:
        d = league_data[code]
        standings_sections += f'''<div class="tab-pane" id="tab-{code}">
          <div class="tab-league-title">{flag} {name}</div>
          {d["standing"]}
          <div class="subsection-title">Ostatnie wyniki</div>
          {d["results"]}
          <div class="subsection-title">Najbliższe mecze</div>
          {d["upcoming"]}
        </div>\n'''

    # Tab buttons
    tab_btns = ''
    for i, (code, name, flag, _) in enumerate(LEAGUES):
        active = ' active' if i == 0 else ''
        tab_btns += f'<button class="tab-btn{active}" onclick="showTab(\'{code}\')">{flag} {name}</button>\n'

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

/* LAYOUT */
.container { max-width: 1100px; margin: 0 auto; padding: 16px 12px; display: grid; grid-template-columns: 1fr 340px; gap: 16px; }

/* BOX */
.box { background: var(--panel); border: 1px solid var(--bdr); margin-bottom: 16px; }
.box-hdr { background: var(--blue); padding: 7px 12px; font-weight: 700; color: var(--gold); text-transform: uppercase; letter-spacing: 2px; border-bottom: 2px solid var(--gold); display: flex; justify-content: space-between; align-items: center; font-size: 13px; font-family: Arial, sans-serif; }
.box-hdr .sub { font-size: 10px; color: #aaa; font-weight: 400; text-transform: none; letter-spacing: 0; }
.no-data { padding: 10px 14px; color: var(--muted); font-size: 12px; font-style: italic; }

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

/* NADCHODZĄCE MECZE */
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

/* FOOTER */
footer { background: #050508; border-top: 2px solid var(--bdr); text-align: center; padding: 20px; font-size: 12px; color: var(--muted); font-family: Arial, sans-serif; }
footer a { color: #444; }

@media (max-width: 768px) {
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
// Aktywuj pierwszy tab domyślnie
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
<title>DOBITKA — Piłka. Sport. Bez ściemy.</title>
<link href="https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>

<div class="ticker-wrap">
  <span class="ticker-label">▶ LIVE</span>
  <span class="ticker-text">
    ★ DOBITKA — aktualizacja co 2 godziny ★ Champions League • Premier League • La Liga • Serie A • Ligue 1 • Ekstraklasa ★ Wyniki, tabele, linki — bez ściemy ★
  </span>
</div>

<header>
  <div class="logo">⚽ DOBITKA</div>
  <div class="tagline">// Piłka. Sport. Bez ściemy. //</div>
  <div class="updated">Ostatnia aktualizacja: <span>{updated}</span> &nbsp;|&nbsp; Dane: <a href="https://www.football-data.org" target="_blank">football-data.org</a></div>
</header>

<nav>
  <a href="#linki">🔥 Linki</a>
  <a href="#tabele">📊 Tabele & Wyniki</a>
  <a href="#ciekawostki">🧠 Ciekawostki</a>
  <a href="#radar">🔭 Radary</a>
  <a href="https://www.flashscore.pl" target="_blank">⚡ Live</a>
</nav>

<div class="container">

  <!-- LEWA KOLUMNA -->
  <div>

    <div class="box" id="linki">
      <div class="box-hdr">🔥 Gorące Linki <span class="sub">wybrane przez redakcję</span></div>
      {hot_links_html()}
    </div>

    <!-- TABELE I WYNIKI — ZAKŁADKI -->
    <div class="box" id="tabele">
      <div class="box-hdr">📊 Tabele, Wyniki & Terminarz <span class="sub">football-data.org</span></div>
      <div class="tab-btns">
        {tab_btns}
      </div>
      {standings_sections}
    </div>

  </div>

  <!-- PRAWA KOLUMNA -->
  <div>

    <div class="box" id="ciekawostki">
      <div class="box-hdr">🧠 Ciekawostki</div>
      {ciekawostki_html()}
    </div>

    <div class="box" id="radar">
      <div class="box-hdr" style="background:#00356A;">🔴🔵 FC Barcelona Radar</div>
      {radar_html(BARCA_RADAR)}
    </div>

    <div class="box">
      <div class="box-hdr" style="background:#38003c;">🟣 Premier League Radar</div>
      {radar_html(PL_RADAR)}
    </div>

    <div class="box">
      <div class="box-hdr" style="background:#8B0000;">🟡 La Liga Radar</div>
      {radar_html(LALIGA_RADAR)}
    </div>

    <div class="box">
      <div class="box-hdr">🔗 Szybkie Linki</div>
      <div class="quick-link"><span>Wyniki na żywo</span><a href="https://www.flashscore.pl" target="_blank">Flashscore →</a></div>
      <div class="quick-link"><span>Statystyki zaawansowane</span><a href="https://fbref.com" target="_blank">FBref →</a></div>
      <div class="quick-link"><span>Wyceny zawodników</span><a href="https://www.transfermarkt.pl" target="_blank">Transfermarkt →</a></div>
      <div class="quick-link"><span>Sofascore</span><a href="https://www.sofascore.com" target="_blank">Sofascore →</a></div>
      <div class="quick-link"><span>Oficjalna UCL</span><a href="https://www.uefa.com" target="_blank">UEFA →</a></div>
    </div>

  </div>

</div><!-- /container -->

<footer>
  ★ DOBITKA — agregator sportowy dla kibiców bez czasu na chaos ★<br><br>
  Dane: <a href="https://www.football-data.org" target="_blank">football-data.org</a> (CC BY 4.0) &nbsp;|&nbsp;
  Linki prowadzą do oryginalnych źródeł. Opisy redakcji własne.<br>
  Zero trackerów. Zero reklam.
</footer>

<script>{js}</script>
</body>
</html>'''

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'✓ index.html wygenerowany ({updated})')

if __name__ == '__main__':
    generate()
