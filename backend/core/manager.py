"""
Data Manager - Handles data storage and retrieval
Supports SQLite for persistence and Redis for caching
"""
import asyncio
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import pandas as pd
import json
from pathlib import Path

class DataManager:
    """Manages data storage in SQLite with optional Redis caching"""
    
    def __init__(self, db_path: str = "data/trading.db"):
        self.db_path = db_path
        self.conn = None
        Path("data").mkdir(exist_ok=True)
    
    async def initialize(self):
        """Initialize database schema"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        
        # Tick data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ticks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                price REAL NOT NULL,
                size REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # OHLC data table with multiple timeframes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ohlc (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, timeframe, timestamp)
            )
        """)
        
        # Analytics cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticks_symbol_ts ON ticks(symbol, timestamp DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ohlc_symbol_tf_ts ON ohlc(symbol, timeframe, timestamp DESC)")
        
        self.conn.commit()
        print(" Database initialized")
    
    async def store_tick(self, symbol: str, timestamp: str, price: float, size: float):
        """Store a single tick"""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO ticks (symbol, timestamp, price, size) VALUES (?, ?, ?, ?)",
            (symbol, timestamp, price, size)
        )
        self.conn.commit()
    
    async def store_ticks_batch(self, ticks: List[Dict]):
        """Store multiple ticks efficiently"""
        if not ticks:
            return
        
        cursor = self.conn.cursor()
        cursor.executemany(
            "INSERT INTO ticks (symbol, timestamp, price, size) VALUES (?, ?, ?, ?)",
            [(t['symbol'], t['ts'], t['price'], t['size']) for t in ticks]
        )
        self.conn.commit()
    
    async def get_recent_ticks(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent ticks for a symbol"""
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT symbol, timestamp, price, size FROM ticks 
               WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?""",
            (symbol, limit)
        )
        
        rows = cursor.fetchall()
        return [dict(row) for row in reversed(rows)]  # Return in chronological order
    
    async def get_ticks_range(self, symbol: str, start: str, end: str) -> List[Dict]:
        """Get ticks within a time range"""
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT symbol, timestamp, price, size FROM ticks 
               WHERE symbol = ? AND timestamp BETWEEN ? AND ?
               ORDER BY timestamp ASC""",
            (symbol, start, end)
        )
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def store_ohlc(self, symbol: str, timeframe: str, timestamp: str,
                         open_: float, high: float, low: float, close: float, volume: float):
        """Store OHLC bar"""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO ohlc 
               (symbol, timeframe, timestamp, open, high, low, close, volume)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (symbol, timeframe, timestamp, open_, high, low, close, volume)
        )
        self.conn.commit()
    
    async def store_bulk_ohlc(self, data: List[Dict]):
        """Store multiple OHLC bars"""
        if not data:
            return
        
        cursor = self.conn.cursor()
        cursor.executemany(
            """INSERT OR REPLACE INTO ohlc 
               (symbol, timeframe, timestamp, open, high, low, close, volume)
               VALUES (?, '1m', ?, ?, ?, ?, ?, ?)""",
            [(d['symbol'], d['timestamp'], d['open'], d['high'], 
              d['low'], d['close'], d['volume']) for d in data]
        )
        self.conn.commit()
    
    async def get_ohlc(self, symbol: str, timeframe: str = "1m", limit: int = 100) -> List[Dict]:
        """Get OHLC data"""
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT symbol, timeframe, timestamp, open, high, low, close, volume
               FROM ohlc WHERE symbol = ? AND timeframe = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (symbol, timeframe, limit)
        )
        
        rows = cursor.fetchall()
        return [dict(row) for row in reversed(rows)]
    
    async def resample_ticks(self, symbol: str, timeframe: str, lookback_minutes: int = 60):
        """Resample tick data to OHLC"""
        try:
            # Get recent ticks - use a simple query to get last N ticks
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT timestamp, price, size 
                FROM ticks 
                WHERE symbol = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (symbol, lookback_minutes * 60))  # Rough estimate: 60 ticks per minute
            
            rows = cursor.fetchall()
            
            if not rows:
                return
            
            # Convert to DataFrame
            df = pd.DataFrame(rows, columns=['timestamp', 'price', 'size'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')
            
            # Filter out invalid prices
            df = df[df['price'] > 0]
            
            if len(df) == 0:
                return
            
            df = df.set_index('timestamp').sort_index()
            
            # Resample based on timeframe
            freq_map = {'1s': 's', '1m': 'min', '5m': '5min'}
            freq = freq_map.get(timeframe, 'min')
            
            ohlc = df['price'].resample(freq).ohlc()
            volume = df['size'].resample(freq).sum()
            
            # Store resampled data
            stored_count = 0
            for ts, row in ohlc.iterrows():
                if pd.notna(row['open']) and row['open'] > 0:
                    await self.store_ohlc(
                        symbol, timeframe, ts.isoformat(),
                        row['open'], row['high'], row['low'], row['close'],
                        volume.loc[ts]
                    )
                    stored_count += 1
            
            if stored_count > 0:
                print(f"[OK] Resampled {symbol} {timeframe}: stored {stored_count} bars")
                
        except Exception as e:
            print(f"[ERROR] Error resampling {symbol} {timeframe}: {e}")
            import traceback
            traceback.print_exc()
    
    async def get_all_symbols(self) -> List[str]:
        """Get list of all symbols with data"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT symbol FROM ticks ORDER BY symbol")
        return [row[0] for row in cursor.fetchall()]
    
    async def cache_analytics(self, key: str, value: Any, ttl_seconds: int = 60):
        """Cache analytics result"""
        expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO analytics_cache (key, value, expires_at)
               VALUES (?, ?, ?)""",
            (key, json.dumps(value), expires_at)
        )
        self.conn.commit()
    
    async def get_cached_analytics(self, key: str) -> Optional[Any]:
        """Get cached analytics result"""
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT value FROM analytics_cache 
               WHERE key = ? AND expires_at > ?""",
            (key, datetime.utcnow().isoformat())
        )
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()