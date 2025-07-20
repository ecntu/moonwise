-- Script that creates tables
-- Ran with: sqlite3 main.db < tables.sql
CREATE TABLE IF NOT EXISTS highlights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deleted BOOLEAN DEFAULT 0,
    original_book_title TEXT NOT NULL,
    book_title TEXT NOT NULL,
    author TEXT,
    original_text TEXT NOT NULL,
    highlight_text TEXT NOT NULL,
    location TEXT,  -- Could be a page number or other reference
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,  -- When it was added
    favorite BOOLEAN DEFAULT 0,  -- If the user marks it as a favorite
    note TEXT,  -- Optional user note
    color TEXT CHECK (LENGTH(color) = 7 AND color LIKE '#%') DEFAULT '#FFFF00', -- Hex code for highlight color

    last_review  DATETIME DEFAULT '1970-01-01',  
    review_count INTEGER DEFAULT 0, 
    review_today BOOLEAN DEFAULT 0
);

-- FTS table for full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS highlights_fts USING fts5(
    highlight_text,
    note,
    content='highlights',
    content_rowid='id'
);

-- Triggers to keep FTS table in sync with highlights table
CREATE TRIGGER IF NOT EXISTS highlights_after_insert
AFTER INSERT ON highlights
BEGIN
    INSERT INTO highlights_fts(rowid, highlight_text, note)
    VALUES (new.id, new.highlight_text, new.note);
END;

CREATE TRIGGER IF NOT EXISTS highlights_after_delete
AFTER DELETE ON highlights
BEGIN
    INSERT INTO highlights_fts(highlights_fts, rowid)
    VALUES ('delete', old.id);
END;


CREATE TRIGGER IF NOT EXISTS highlights_after_update
AFTER UPDATE ON highlights
BEGIN
    INSERT INTO highlights_fts(highlights_fts, rowid)
    VALUES ('delete', old.id);

    INSERT INTO highlights_fts(rowid, highlight_text, note)
    VALUES (new.id, new.highlight_text, new.note);
END;


INSERT INTO highlights_fts(rowid, highlight_text, note)
SELECT id, highlight_text, note FROM highlights;