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
