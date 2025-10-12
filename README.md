# 🗞️ Local RSS Reader

A local, database-backed RSS reader that fetches posts from your favorite feeds, stores them in PostgreSQL, and generates a clean static HTML page you can open in your browser.

---

## 🚀 Quick Start

### 1. Create the database

Make sure PostgreSQL is running locally and create a database named `rssdb`. If you've created the db but not logged in, you can skip all this with something like:

```
psql -U username -d rssdb -h localhost
```

```bash
createdb rssdb
```

Create your tables (if you haven’t already):

```sql

CREATE TABLE feeds (
  id SERIAL PRIMARY KEY,
  url TEXT NOT NULL UNIQUE,
  title TEXT,
  poll_interval INTEGER DEFAULT 3600,
  last_fetched_at TIMESTAMPTZ,
  next_poll_at TIMESTAMPTZ,
  last_error TEXT,
  last_status INTEGER
);

CREATE TABLE entries (
  id SERIAL PRIMARY KEY,
  feed_id INTEGER REFERENCES feeds(id) ON DELETE CASCADE,
  guid TEXT,
  link TEXT,
  title TEXT,
  summary TEXT,
  content TEXT,
  published_at TIMESTAMPTZ,
  CONSTRAINT entries_unique_guid UNIQUE (feed_id, guid)
);
``` 

### 2. Add a new feed manually
To insert a feed URL into the database:

```sql
INSERT INTO feeds (url, next_poll_at) VALUES ('https://example.com/feed.xml', now());
```
You can use psql to connect:

```bash
psql rssdb
```

### 3. Run the RSS fetcher

This script polls feeds that are due for fetching, parses entries, and writes them into the database.

```bash
python3 rss_reader.py
```

You should see logs like:

```bash
14:09:46 [INFO] Found 2 feeds ready to fetch
14:09:46 [INFO] Fetching feed https://rmoff.net/index.xml
14:09:46 [INFO] Parsed 10 items from https://rmoff.net/index.xml
```

### 4. Generate the static HTML page

After feeds are fetched, generate a local HTML view:

```bash
python3 generate_html.py
```

You’ll see output like:

```swift
✅ HTML generated at /Users/luciacerchie/reader/output/index.html
```

Then open it in your browser:

```bash
open output/index.html
```

### 🧠 Diagnosing Database Issues

If something isn’t working, here are common checks:

✅ Check connection

Make sure your DSN matches your local username:

```python
DB_DSN = "postgresql://<username>@localhost:5432/rssdb"
```

Example for user luciacerchie:

```python
DB_DSN = "postgresql://luciacerchie@localhost:5432/rssdb"
```

🔍 See all feeds
```sql
SELECT id, url, title, next_poll_at, last_error FROM feeds;
```

🔍 See latest entries

```sql
SELECT id, feed_id, link, title, published_at
FROM entries
ORDER BY published_at DESC
LIMIT 10;
```

🔧 Force a re-fetch

If you updated a feed but it’s not being fetched:

```sql
UPDATE feeds SET next_poll_at = now();
🧹 Clear broken feeds or entries

```sql
DELETE FROM feeds WHERE last_error IS NOT NULL;
DELETE FROM entries WHERE published_at IS NULL;
```

⚠️ Common errors

Error	Likely Cause	Fix
DB write error: constraint "entries_unique_guid" does not exist	The unique constraint wasn’t created	Recreate it using ALTER TABLE entries ADD CONSTRAINT entries_unique_guid UNIQUE (feed_id, guid);
asyncpg.exceptions.InvalidCatalogNameError	Database rssdb doesn’t exist	Run createdb rssdb
No output from rss_reader.py	No feeds are due to poll	Run UPDATE feeds SET next_poll_at = now();

🧩 Folder Overview
graphql

reader/
├── rss_reader.py        # main fetcher and database writer
├── generate_html.py     # generates index.html from DB
├── templates/
│   └── index.html.j2    # Jinja2 template for HTML page
├── output/
│   └── index.html       # rendered output
└── README.md            # this file
✨ Example Output
After running generate_html.py, your index.html will show a simple feed reader like this:


```yaml
🗞️ My RSS Feed Reader
──────────────────────────────
Title: Kafka Blog
Feed: blog.net
Published: 2025-10-08
[Open Link]
```

🧭 ### Troubleshooting Tips

<i> If feeds aren’t being fetched: </i>

Ensure their next_poll_at ≤ now().

Check last_error in the feeds table.

<i> If nothing appears in HTML: </i>

Run the SQL query manually to confirm entries exist.


<i> To clean up and start fresh: </i>

```sql
TRUNCATE entries, feeds RESTART IDENTITY;
```
