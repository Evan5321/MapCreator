-- MapCreator annotations 真源 schema
-- 契约：docs/DATA_SPEC.md §4
-- 注意：
--   * 只导逻辑表（meta / annotation / annotation_name / relation / relation_member）
--   * FTS/RTree 是派生索引，restore 后重建
--   * search_text 由应用层维护，不由触发器重算

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- schema_version / default_lang / world_id 必存在
CREATE TABLE IF NOT EXISTS meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS annotation (
  fid          INTEGER PRIMARY KEY,
  id           TEXT NOT NULL UNIQUE CHECK (id GLOB 'anno.*.*'),
  kind         TEXT NOT NULL,
  search_text  TEXT NOT NULL DEFAULT '',
  parent_id    TEXT,
  geometry_id  TEXT,
  lon          REAL NOT NULL,
  lat          REAL NOT NULL,
  label_mode   TEXT NOT NULL DEFAULT 'point'
               CHECK (label_mode IN ('point', 'line', 'none')),
  rank         INTEGER NOT NULL DEFAULT 3 CHECK (rank BETWEEN 1 AND 5),
  min_zoom     REAL,
  max_zoom     REAL,
  icon         TEXT,
  description  TEXT,
  attrs        TEXT NOT NULL DEFAULT '{}',
  revision     INTEGER NOT NULL DEFAULT 1,
  updated_at   TEXT NOT NULL,
  deleted_at   TEXT,
  CHECK (min_zoom IS NULL OR max_zoom IS NULL OR min_zoom <= max_zoom)
);

CREATE TABLE IF NOT EXISTS annotation_name (
  annotation_id TEXT NOT NULL REFERENCES annotation(id) ON DELETE CASCADE,
  lang          TEXT NOT NULL,
  name          TEXT NOT NULL,
  role          TEXT NOT NULL DEFAULT 'name' CHECK (role IN ('name', 'alias')),
  is_primary    INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
  PRIMARY KEY (annotation_id, lang, name)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_annotation_name_primary
  ON annotation_name(annotation_id) WHERE is_primary = 1;

CREATE VIEW IF NOT EXISTS annotation_v AS
SELECT a.*, n.name AS name, n.lang AS name_lang
FROM annotation a
LEFT JOIN annotation_name n
  ON n.annotation_id = a.id AND n.is_primary = 1;

CREATE INDEX IF NOT EXISTS idx_annotation_kind     ON annotation(kind);
CREATE INDEX IF NOT EXISTS idx_annotation_parent   ON annotation(parent_id);
CREATE INDEX IF NOT EXISTS idx_annotation_geometry ON annotation(geometry_id);
CREATE INDEX IF NOT EXISTS idx_annotation_live     ON annotation(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_annotation_name_name ON annotation_name(name);

CREATE VIRTUAL TABLE IF NOT EXISTS annotation_rtree USING rtree(
  fid, min_lon, max_lon, min_lat, max_lat
);

CREATE VIRTUAL TABLE IF NOT EXISTS annotation_fts USING fts5(
  search_text,
  content='annotation',
  content_rowid='fid',
  tokenize='trigram'
);

-- ---- 触发器：FTS / RTree 同步 ----
CREATE TRIGGER IF NOT EXISTS annotation_ai AFTER INSERT ON annotation BEGIN
  INSERT INTO annotation_fts(rowid, search_text) VALUES (new.fid, new.search_text);
  INSERT INTO annotation_rtree(fid, min_lon, max_lon, min_lat, max_lat)
  VALUES (new.fid, new.lon, new.lon, new.lat, new.lat);
END;

CREATE TRIGGER IF NOT EXISTS annotation_au AFTER UPDATE ON annotation BEGIN
  INSERT INTO annotation_fts(annotation_fts, rowid, search_text)
  VALUES ('delete', old.fid, old.search_text);
  INSERT INTO annotation_fts(rowid, search_text) VALUES (new.fid, new.search_text);
  UPDATE annotation_rtree
  SET min_lon = new.lon, max_lon = new.lon, min_lat = new.lat, max_lat = new.lat
  WHERE fid = old.fid;
END;

CREATE TRIGGER IF NOT EXISTS annotation_ad AFTER DELETE ON annotation BEGIN
  INSERT INTO annotation_fts(annotation_fts, rowid, search_text)
  VALUES ('delete', old.fid, old.search_text);
  DELETE FROM annotation_rtree WHERE fid = old.fid;
END;

CREATE TABLE IF NOT EXISTS relation (
  id    TEXT PRIMARY KEY,
  kind  TEXT NOT NULL,
  name  TEXT NOT NULL,
  attrs TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS relation_member (
  relation_id TEXT NOT NULL REFERENCES relation(id) ON DELETE CASCADE,
  member_id   TEXT NOT NULL,
  role        TEXT NOT NULL,
  seq         INTEGER NOT NULL,
  PRIMARY KEY (relation_id, member_id, role)
);
