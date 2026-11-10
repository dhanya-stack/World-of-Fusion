"""Refresh Fusion Field Notes news and paper cards. Standard-library only.

Run from the site root. Intended for a scheduled GitHub Actions workflow.
Cached cards remain when an upstream feed is temporarily unavailable.
"""
from __future__ import annotations
import datetime as dt
import email.utils
import html
import json
from pathlib import Path
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "feed.json"
AGENT = "FusionFieldNotes/1.0 (educational fusion digest; original links retained)"
BLOCKED = ("ukaea",)  # Keep source-specific employer material out of this publication.
NEWS_QUERIES = [
    '"nuclear fusion" (tokamak OR stellarator OR plasma) when:30d',
    '"fusion energy" (ITER OR EAST OR KSTAR OR Japan OR India OR Europe) when:30d',
    '"fusion" (tungsten OR divertor OR neutron OR tritium OR magnet) when:30d',
]
TRUSTED_PUBLISHERS = (
    'iter', 'fusion for energy', 'fusion industry association', 'world nuclear news',
    'iaea', 'nature', 'science', 'phys.org', 'physics world', 'new atlas',
    'nuclear news', 'american nuclear society', 'plasma physics',
    'princeton plasma', 'lawrence livermore', 'max planck', 'eurofusion',
    'energy.gov', 'department of energy', 'the engineer', 'scientific american',
    'mit news', 'euronews', 'reuters', 'ap news', 'interesting engineering',
)
FUSION_CUES = ('fusion', 'tokamak', 'stellarator', 'plasma', 'tritium', 'divertor', 'ignition', 'w7-x', 'iter')


def download(url: str) -> bytes:
    req = Request(url, headers={'User-Agent': AGENT, 'Accept': 'application/atom+xml,application/rss+xml,application/xml,*/*'})
    with urlopen(req, timeout=25) as f:
        return f.read(3_000_000)


def clean(text: str) -> str:
    return re.sub(r'\s+', ' ', re.sub('<[^>]+>', '', html.unescape(text or ''))).strip()


def date_from_rss(s: str) -> str:
    try:
        return email.utils.parsedate_to_datetime(s).date().isoformat()
    except Exception:
        return dt.date.today().isoformat()


def classify(s: str) -> str:
    s = s.lower()
    for needles, label in [
        (('tungsten', 'material', 'divertor', 'cooling'), 'Materials'),
        (('magnet', 'superconduct'), 'Magnets'),
        (('plasma', 'tokamak', 'stellarator', 'confinement'), 'Plasma'),
        (('joint', 'collaborat', 'partnership', 'agreement'), 'Collaboration'),
        (('money', 'funding', 'budget', 'invest', 'research program'), 'Policy'),
        (('technology', 'assembly', 'vessel', 'building'), 'Engineering'),
    ]:
        if any(x in s for x in needles):
            return label
    return 'Global news'


def classify_region(s: str) -> str:
    s=s.lower()
    if any(x in s for x in ('china','japan','korea','india','kstar','east tokamak')): return 'Asia'
    if any(x in s for x in ('united states','us ','american','u.s.','california','mit','canada','nif')): return 'North America'
    if any(x in s for x in ('germany','europe','france','italy','spain','switzerland','iter','stellarator')): return 'Europe · Global'
    return 'Global'


def rss_news() -> list[dict]:
    stories = []
    seen = set()
    for q in NEWS_QUERIES:
        url = 'https://news.google.com/rss/search?' + urlencode({'q':q,'hl':'en-US','gl':'US','ceid':'US:en'})
        try:
            root = ET.fromstring(download(url))
        except Exception as e:
            print('News source unavailable:', type(e).__name__, str(e)[:120])
            continue
        for item in root.findall('.//item'):
            title = clean(item.findtext('title'))
            description = clean(item.findtext('description'))
            source_tag = item.find('source')
            publisher = clean(source_tag.text if source_tag is not None else 'External source')
            href = clean(item.findtext('link'))
            blob = (title + ' ' + publisher + ' ' + description).lower()
            if any(x in blob for x in BLOCKED): continue
            if not any(x in blob for x in FUSION_CUES): continue
            if not any(x in publisher.lower() for x in TRUSTED_PUBLISHERS): continue
            if any(x in blob for x in ('cold fusion scam', 'fusion restaurant', 'fusion cuisine', 'nuclear war')): continue
            key = re.sub('[^a-z0-9]', '', title.lower())[:90]
            if not title or not href or key in seen: continue
            seen.add(key)
            stories.append({'title':title[:155], 'date':date_from_rss(item.findtext('pubDate') or ''),
                            'region':classify_region(blob), 'tag':classify(blob), 'source':publisher,
                            'url':href, 'summary':description[:280] or 'Read the source for the latest details.',
                            'why':'Aggregation: check the original reporting and publication date.'})
    return sorted(stories, key=lambda x:x['date'],reverse=True)[:22]


def paper_topic(blob: str) -> str:
    s=blob.lower()
    if 'stellarator' in s: return 'Stellarator'
    if any(t in s for t in ['diagnostic', 'tomography', 'interferom', 'measurement']): return 'Diagnostics'
    if any(t in s for t in ['gyrokinetic', 'simulation', 'numerical', 'computational', 'machine learning']): return 'Simulation'
    if any(t in s for t in ['divertor', 'tungsten', 'material']): return 'Materials'
    return 'Plasma physics'


def arxiv_papers() -> list[dict]:
    query = 'cat:physics.plasm-ph AND (all:tokamak OR all:stellarator OR all:divertor OR all:fusion)'
    url='https://export.arxiv.org/api/query?'+urlencode({'search_query':query,'start':0,'max_results':22,'sortBy':'submittedDate','sortOrder':'descending'})
    try: root=ET.fromstring(download(url))
    except Exception as e:
        print('Paper source unavailable:',type(e).__name__,str(e)[:120]); return []
    ns={'a':'http://www.w3.org/2005/Atom'}
    entries=[]
    for entry in root.findall('a:entry',ns):
        title=clean(entry.findtext('a:title',default='',namespaces=ns))
        summary=clean(entry.findtext('a:summary',default='',namespaces=ns))
        url=entry.findtext('a:id',default='',namespaces=ns)
        published=entry.findtext('a:published',default='',namespaces=ns)[:10]
        authors=[clean(x.findtext('a:name',default='',namespaces=ns)) for x in entry.findall('a:author',ns)]
        if not title or not url or any(x in (title+' '+summary).lower() for x in BLOCKED): continue
        if not any(x in (title+' '+summary).lower() for x in ('fusion', 'tokamak', 'stellarator', 'divertor', 'confinement','burning plasma','plasma-facing')): continue
        if 'arxiv.org' not in url: continue
        entries.append({'title':title[:160], 'date':published, 'field':paper_topic(title+' '+summary),
                        'level':'Preprint · check review status', 'url':url, 'authors':', '.join(authors[:3]) + (' et al.' if len(authors)>3 else ''),
                        'summary':summary[:230].rstrip()+'…' if len(summary)>230 else summary,
                        'question':'What is new, what evidence is shown, and what are the limitations?'})
    return entries[:12]


def main():
    feed=json.loads(DATA.read_text(encoding='utf-8'))
    incoming_news=rss_news()
    new_papers=arxiv_papers()
    if incoming_news:
        # Preserve a small editorial seed as durable engineering context.
        old=feed['news']
        seed=[x for x in old if x['source'] in ('ITER','Fusion for Energy','U.S. Department of Energy','ANS Nuclear Newswire')]
        keys=set();merged=[]
        for x in incoming_news+seed:
            key=re.sub('[^a-z0-9]', '',x['title'].lower())[:65]
            if key not in keys:
                keys.add(key);merged.append(x)
        feed['news']=sorted(merged,key=lambda x:x['date'],reverse=True)[:26]
    if new_papers:
        old=[x for x in feed['papers'] if x.get('date','')>='2025-01-01']
        keys=set();merged=[]
        for x in new_papers+old:
            if x['url'] not in keys:
                keys.add(x['url']);merged.append(x)
        feed['papers']=sorted(merged,key=lambda x:x['date'],reverse=True)[:22]
    if incoming_news or new_papers:
        feed['updated']=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
        feed['source_note']='Automated aggregator; article titles and abstracts link to original publishers. Verify claims independently.'
        DATA.write_text(json.dumps(feed,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print(f"Updated {len(incoming_news)} new articles, {len(new_papers)} papers; total {len(feed['news'])} news, {len(feed['papers'])} papers")
    else:
        print('Upstream data unavailable, preserving last known working snapshot.')

if __name__=='__main__': main()
