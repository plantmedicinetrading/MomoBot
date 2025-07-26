import sqlite3
from typing import List, Dict, Any
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'momo.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            shares INTEGER NOT NULL,
            entry_price REAL NOT NULL,
            exit_price REAL NOT NULL,
            entry_type TEXT,
            entry_time TEXT NOT NULL,
            exit_time TEXT NOT NULL,
            profit_loss REAL NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            side TEXT NOT NULL,
            datetime TEXT NOT NULL,
            trade_id INTEGER,
            commission REAL,
            entry_type TEXT
        )
    ''')
    conn.commit()
    conn.close()

def insert_trade(trade: Dict[str, Any]):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO trades (symbol, shares, entry_price, exit_price, entry_type, entry_time, exit_time, profit_loss)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        trade['symbol'],
        trade['shares'],
        trade['entry_price'],
        trade['exit_price'],
        trade.get('entry_type'),
        trade['entry_time'],
        trade['exit_time'],
        trade['profit_loss']
    ))
    conn.commit()
    conn.close()

def get_all_trades() -> List[Dict[str, Any]]:
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM trades ORDER BY exit_time DESC')
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def insert_execution(exe: Dict[str, Any]):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO executions (symbol, quantity, price, side, datetime, trade_id, commission, entry_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        exe['symbol'],
        exe['quantity'],
        exe['price'],
        exe['side'],
        exe['datetime'],
        exe.get('trade_id'),
        exe.get('commission'),
        exe.get('entry_type')
    ))
    conn.commit()
    conn.close()

def get_all_executions() -> List[Dict[str, Any]]:
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM executions ORDER BY datetime ASC')
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_trade_by_id(trade_id):
    import sqlite3
    conn = sqlite3.connect('backend/app/momo.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted > 0 