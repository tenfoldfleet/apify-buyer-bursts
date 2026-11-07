# Apify buyer bursts

Code for the article "One Actor earned over half my Apify revenue, two months running: five weeks of pay-per-event Actors".

`bursts.py` spots buyer bursts on your public Apify Actors: a jump in 30-day runs by other users from one day to the next, while the number of users barely moves. That pattern is one buyer running a script or an AI agent.

## Run it

```bash
APIFY_TOKEN=... python bursts.py              # snapshot today's stats into stats.jsonl, print bursts vs earlier snapshots
python bursts.py --replay stats.jsonl         # replay a log of {"ts", "actor", "runs30", "users30"} rows
python bursts.py --selftest
```

Run the snapshot once a day (cron, a scheduled task, or an Apify schedule). Python 3.9+, standard library only. It reads `GET /v2/acts?my=1` and `GET /v2/acts/{id}`.

## Licence

MIT
