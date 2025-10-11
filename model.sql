-- feeds table: subscriptions / metadata
CREATE TABLE feeds (
  id              SERIAL PRIMARY KEY,
  url             TEXT NOT NULL UNIQUE,
  title           TEXT,
  etag            TEXT,
  last_modified   TEXT,
  last_status     INTEGER,
  last_fetched_at TIMESTAMP WITH TIME ZONE,
  poll_interval   INTEGER NOT NULL DEFAULT 3600, -- seconds
  next_poll_at    TIMESTAMP WITH TIME ZONE,
  last_error      TEXT
);

-- entries table: feed items
CREATE TABLE entries (
  id            BIGSERIAL PRIMARY KEY,
  feed_id       INTEGER NOT NULL REFERENCES feeds(id) ON DELETE CASCADE,
  guid          TEXT,      -- prefer GUID from feed
  link          TEXT,
  title         TEXT,
  summary       TEXT,
  content       TEXT,
  published_at  TIMESTAMP WITH TIME ZONE,
  fetched_at    TIMESTAMP WITH TIME ZONE DEFAULT now(),
  CHECK ((guid IS NOT NULL) OR (link IS NOT NULL))
);

-- Deduplication: prefer using guid, fallback to link.
CREATE UNIQUE INDEX entries_unique_guid ON entries (feed_id, (COALESCE(guid, link)));

-- simple index for queries
CREATE INDEX entries_published_idx ON entries (published_at DESC);

