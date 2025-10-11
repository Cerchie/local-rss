import asyncio
import asyncpg
import argparse
from datetime import datetime, timezone

DB_DSN = "postgresql://postgres:postgres@localhost:5432/rssdb"

async def add_feed(url, interval):
    conn = await asyncpg.connect(DB_DSN)
    try:
        await conn.execute('''
            INSERT INTO feeds (url, poll_interval, next_poll_at)
            VALUES ($1, $2, $3)
            ON CONFLICT (url) DO UPDATE
            SET poll_interval = EXCLUDED.poll_interval,
                next_poll_at = EXCLUDED.next_poll_at
        ''', url, interval, datetime.now(timezone.utc))
        print(f"✅ Added or updated feed: {url}")
    finally:
        await conn.close()

async def list_feeds():
    conn = await asyncpg.connect(DB_DSN)
    rows = await conn.fetch('SELECT id, url, poll_interval, next_poll_at FROM feeds ORDER BY id')
    print("📰 Feeds:")
    for row in rows:
        print(f"  [{row['id']}] {row['url']} (every {row['poll_interval']}s, next at {row['next_poll_at']})")
    await conn.close()

def main():
    parser = argparse.ArgumentParser(description="Manage RSS feeds")
    sub = parser.add_subparsers(dest="command")

    add_cmd = sub.add_parser("add", help="Add a new feed")
    add_cmd.add_argument("url", help="RSS feed URL")
    add_cmd.add_argument("--interval", type=int, default=3600, help="Polling interval in seconds")

    list_cmd = sub.add_parser("list", help="List all feeds")

    args = parser.parse_args()

    if args.command == "add":
        asyncio.run(add_feed(args.url, args.interval))
    elif args.command == "list":
        asyncio.run(list_feeds())
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

