import asyncio
import asyncpg
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

DB_DSN = "postgresql://luciacerchie@localhost:5432/rssdb"

async def main():
    conn = await asyncpg.connect(DB_DSN)
    rows = await conn.fetch('''
        SELECT 
            f.title AS feed,
            e.title,
            e.link,
            e.published_at,
            e.updated_at,
            e.fetched_at,
            COALESCE(e.published_at, e.updated_at, e.fetched_at) as display_date
        FROM entries e
        JOIN feeds f ON e.feed_id = f.id
        ORDER BY COALESCE(e.published_at, e.updated_at, e.fetched_at) DESC
        LIMIT 50;
    ''')
    await conn.close()

    entries = [dict(r) for r in rows]

    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('index.html.j2')
    html = template.render(entries=entries)

    output_path = Path('output/index.html')
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(html, encoding='utf-8')

    print(f"✅ HTML generated at {output_path.resolve()}")

if __name__ == "__main__":
    asyncio.run(main())
