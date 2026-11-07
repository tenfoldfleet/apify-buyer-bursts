"""Spot buyer bursts on your public Apify Actors: a jump in 30-day runs by other users from one day to the next.

Usage:
  APIFY_TOKEN=... python bursts.py              # snapshot today's stats into stats.jsonl, print bursts vs the last snapshot
  python bursts.py --replay metrics.jsonl       # replay an existing log of {"ts", "actor", "runs30", "users30"} rows
  python bursts.py --selftest
Standard library only.
"""
import json, os, sys, urllib.error, urllib.request
from datetime import datetime, timezone

API = 'https://api.apify.com/v2'
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stats.jsonl')


def get(path):
    req = urllib.request.Request(API + path, headers={'Authorization': 'Bearer ' + os.environ['APIFY_TOKEN']})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)['data']
    except urllib.error.HTTPError as e:  # 401 bad token, 404 deleted Actor, 429 rate limit
        sys.exit(f'GET {path}: HTTP {e.code} {e.read().decode(errors="replace")[:200]}')


def snapshot():
    """One row per public Actor you own: runs and users by other people over the last 30 days."""
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    rows = []
    for a in get('/acts?my=1&limit=1000')['items']:
        d = get(f"/acts/{a['id']}")
        if not d.get('isPublic'):
            continue
        s = d.get('stats') or {}
        rows.append({'ts': now, 'actor': d['name'], 'runs30': (s.get('publicActorRunStats30Days') or {}).get('TOTAL', 0),
                     'users30': s.get('totalUsers30Days', 0)})
    return rows


def by_day(rows):
    """{date: {actor: row}}, keeping the last row per actor per day."""
    days = {}
    for r in rows:
        if 'runs30' in r:
            days.setdefault(r['ts'][:10], {})[r['actor']] = r
    return days


def bursts(prev, cur, min_runs=20):
    """Actors whose 30-day run count rose by min_runs or more since the previous day, biggest first.
    A big jump with users30 nearly flat means one buyer running a script or an agent, not new users."""
    out = []
    for name, r in cur.items():
        p = prev.get(name)
        if p is None or not r.get('users30'):
            continue  # new Actor, or only your own runs (you never count as your own user)
        jump = (r['runs30'] or 0) - (p['runs30'] or 0)
        if jump >= min_runs:
            out.append((jump, name, p['runs30'], r['runs30'], p.get('users30'), r.get('users30')))
    return sorted(out, reverse=True)


def report(rows, min_runs=20):
    days = by_day(rows)
    dates = sorted(days)
    for a, b in zip(dates, dates[1:]):
        for jump, name, r0, r1, u0, u1 in bursts(days[a], days[b], min_runs):
            print(f'{b}  {name}: runs30 {r0} -> {r1} (+{jump}), users30 {u0} -> {u1}')


def selftest():
    rows = [{'ts': '2026-11-05T03:00:00', 'actor': 'image-search', 'runs30': 11, 'users30': 1},
            {'ts': '2026-11-05T03:00:00', 'actor': 'news', 'runs30': 40, 'users30': 5},
            {'ts': '2026-11-06T03:00:00', 'actor': 'image-search', 'runs30': 266, 'users30': 2},
            {'ts': '2026-11-06T03:00:00', 'actor': 'news', 'runs30': 45, 'users30': 6},
            {'ts': '2026-11-06T03:00:00', 'actor': 'brand-new', 'runs30': 90, 'users30': 1},
            {'ts': '2026-11-05T03:00:00', 'actor': 'my-tests', 'runs30': 0, 'users30': 0},
            {'ts': '2026-11-06T03:00:00', 'actor': 'my-tests', 'runs30': 77, 'users30': 0}]
    days = by_day(rows)
    assert bursts(days['2026-11-05'], days['2026-11-06']) == [(255, 'image-search', 11, 266, 1, 2)], 'new Actors, small rises and owner-only runs are not bursts'
    print('selftest ok')


if __name__ == '__main__':
    if sys.argv[1:] == ['--selftest']:
        selftest()
    elif sys.argv[1:2] == ['--replay']:
        report([json.loads(l) for l in open(sys.argv[2], encoding='utf-8') if l.strip()])
    else:
        rows = snapshot()
        with open(LOG, 'a', encoding='utf-8') as f:
            f.writelines(json.dumps(r) + '\n' for r in rows)
        report([json.loads(l) for l in open(LOG, encoding='utf-8')])
