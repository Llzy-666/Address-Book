"""SQLite 连接、建表与初始化。

不用 ORM，直接使用标准库 ``sqlite3``；每次取连接都显式开启外键约束，
保证删除联系人时其联系方式被级联删除。
"""
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "address_book.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS contacts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    company     TEXT,
    note        TEXT,
    is_favorite INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT,
    updated_at  TEXT
);

CREATE TABLE IF NOT EXISTS contact_methods (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL,
    type       TEXT NOT NULL,
    label      TEXT,
    value      TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY (contact_id) REFERENCES contacts (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_contact_methods_contact
    ON contact_methods (contact_id);
"""


def get_connection():
    """打开一个连接：行工厂为 sqlite3.Row，并开启外键级联。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    """建表；已存在则跳过，可重复调用。"""
    connection = get_connection()
    try:
        connection.executescript(SCHEMA_SQL)
        connection.commit()
    finally:
        connection.close()
    return DB_PATH


def reset_db():
    """清空两张表并把自增 id 归零，供种子脚本与测试使用。"""
    connection = get_connection()
    try:
        connection.execute("DELETE FROM contact_methods")
        connection.execute("DELETE FROM contacts")
        connection.execute(
            "DELETE FROM sqlite_sequence WHERE name IN ('contacts', 'contact_methods')"
        )
        connection.commit()
    finally:
        connection.close()
