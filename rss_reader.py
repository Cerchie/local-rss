import asyncio
import asyncpg
import aiohttp
from urllib.parse import urlparse
import feedparser
from datetime import datetime, timezone, timedelta
from dateutil import parser as dateparser
import logging

# Logging setup 👇
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

# replace luciacerchie with your local postgres user
DB_DSN = "postgresql://luciacerchie@localhost:5432/rssdb"

# CONFIG
FETCH_CONCURRENCY = 20
WRITE_CONCURRENCY = 10
DEFAULT_POLL = 3600  # seconds

class RateLimiter:
    def __init__(self, per_host_limit=2):
        self.semaphores = {}
        self.limit = per_host_limit
        self.lock = asyncio.Lock()
    async def acquire(self, host):
        async with self.lock:
            if host not in self.semaphores:
                self.semaphores[host] = asyncio.Semaphore(self.limit)
            sem = self.semaphores[host]
        await sem.acquire()
        return sem

rate_limiter = RateLimiter(per_host_limit=2)

async def fetch_feed(session, url):
    host = urlparse(url).hostname or "default"
    sem = await rate_limiter.acquire(host)
    try:
        async with session.get(url, timeout=30) as resp:
            text = await resp.read()
            return resp.status, text, resp.headers
    finally:
        sem.release()

def parse_feed_bytes(payload_bytes):
    raw = feedparser.parse(payload_bytes)
    items = []
    for e in raw.entries:
        items.append({
            "guid": e.get('id') or e.get('guid'),
            "link": e.get('link'),
            "title": e.get('title'),
            "summary": e.get('summary'),
            "content": e.get('content', [{}])[0].get('value') if e.get('content') else None,
            "published": dateparser.parse(e.published) if e.get('published') else None,
            "updated": dateparser.parse(e.updated) if e.get('updated') else None
        })
    return raw.feed.get('title'), items, raw.get('bozo')

async def writer_worker(db_pool, write_q):
    async with db_pool.acquire() as conn:
        while True:
            task = await write_q.get()
            if task is None:
                write_q.task_done()
                break
            feed_id, item = task
            try:
                await conn.execute('''
                    INSERT INTO entries(
                        feed_id, guid, link, title, summary, 
                        content, published_at, updated_at
                    )
                    VALUES($1,$2,$3,$4,$5,$6,$7,$8)
                    ON CONFLICT ON CONSTRAINT entries_unique_guid DO NOTHING
                ''', feed_id, item['guid'], item['link'], item['title'],
                     item['summary'], item['content'], 
                     item['published'], item['updated'])
            except Exception as e:
                log.error(f"DB write error: {e}")
            write_q.task_done()

async def fetch_and_enqueue(session, db_pool, write_q, feed_row):
    feed_id = feed_row['id']
    url = feed_row['url']
    log.info(f"Fetching feed {url}")  ### 👇 visible feedback

    try:
        status, body, headers = await fetch_feed(session, url)
    except Exception as e:
        log.error(f"Failed fetch {url}: {e}")
        async with db_pool.acquire() as conn:
            await conn.execute('''
                UPDATE feeds SET last_error=$1, last_status=NULL,
                last_fetched_at=now(), next_poll_at=now() + INTERVAL '1 hour'
                WHERE id=$2
            ''', str(e), feed_id)
        return

    loop = asyncio.get_event_loop()
    title, items, bozo = await loop.run_in_executor(None, parse_feed_bytes, body)

    async with db_pool.acquire() as conn:
        await conn.execute('''
            UPDATE feeds
            SET title=$1,
                last_status=$2,
                last_fetched_at=now(),
                last_error=NULL,
                next_poll_at=now() + make_interval(secs => $3)
            WHERE id=$4
        ''', title, status, DEFAULT_POLL, feed_id)

    log.info(f"Parsed {len(items)} items from {url}")  ### 👇 visible feedback

    for it in items:
        await write_q.put((feed_id, it))

async def scheduler_loop(db_pool, fetch_q):
    while True:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch('''
               SELECT id, url, poll_interval, next_poll_at
               FROM feeds
               WHERE next_poll_at IS NULL OR next_poll_at <= now()
               ORDER BY next_poll_at NULLS FIRST
               LIMIT 500
            ''')
        if not rows:
            log.debug("No feeds ready; sleeping 10s")  ### 👇
            await asyncio.sleep(10)
            continue
        log.info(f"Found {len(rows)} feeds ready to fetch")  ### 👇 visible feedback
        for r in rows:
            await fetch_q.put(dict(r))
        await asyncio.sleep(1)

async def fetch_worker(session, db_pool, fetch_q, write_q):
    while True:
        feed_row = await fetch_q.get()
        if feed_row is None:
            fetch_q.task_done()
            break
        try:
            await fetch_and_enqueue(session, db_pool, write_q, feed_row)
        except Exception as e:
            log.error(f"fetch_worker error: {e}")
        fetch_q.task_done()

async def main():
    db_pool = await asyncpg.create_pool(DB_DSN, min_size=1, max_size=20)
    fetch_q = asyncio.Queue()
    write_q = asyncio.Queue()

    writers = [asyncio.create_task(writer_worker(db_pool, write_q))
               for _ in range(WRITE_CONCURRENCY)]

    async with aiohttp.ClientSession() as session:
        fetchers = [asyncio.create_task(fetch_worker(session, db_pool, fetch_q, write_q))
                    for _ in range(FETCH_CONCURRENCY)]
        sched = asyncio.create_task(scheduler_loop(db_pool, fetch_q))

        try:
            await asyncio.gather(sched, *fetchers)
        except asyncio.CancelledError:
            pass
        finally:
            for _ in fetchers:
                await fetch_q.put(None)
            for _ in writers:
                await write_q.put(None)
            await write_q.join()
            for w in writers:
                w.cancel()

    await db_pool.close()

if __name__ == "__main__":
    asyncio.run(main())
