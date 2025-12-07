# 📈 Real-Time Trading Analytics Platform

A high-performance real-time cryptocurrency trading analytics platform built with FastAPI, Streamlit, and WebSocket technology. Designed for statistical arbitrage and market microstructure analysis.

## 🌟 Features

### Real-Time Data Collection
- **WebSocket Integration**: Live data streaming from Binance Futures
- **Multi-Symbol Support**: Track multiple cryptocurrency pairs simultaneously
- **Tick-Level Data**: High-frequency tick data collection and storage
- **Automatic Resampling**: Convert tick data to OHLC (1s, 1m, 5m timeframes)

### Advanced Analytics
- **Live Candlestick Charts**: Real-time price visualization with multiple chart types
- **Spread Analysis**: Calculate and visualize price spreads between pairs
- **Correlation Analysis**: Rolling correlation and correlation heatmaps
- **Statistical Metrics**: Real-time mean, std dev, volume, and other statistics

### Alert System
- **Custom Alerts**: Create price-based alert rules
- **Real-Time Monitoring**: Automatic alert triggering on tick data
- **Alert History**: View triggered alerts with timestamps

### Data Management
- **SQLite Persistence**: Efficient local database storage
- **Data Export**: Export OHLC data to CSV format
- **Bulk Data Upload**: Import historical data from CSV

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER INTERFACE LAYER                         │
│                   (Streamlit Dashboard)                          │
│  - Live Charts  - Spread Analysis  - Correlation  - Alerts      │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/REST API
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API LAYER (FastAPI)                         │
│                                                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │  /api/start │  │  /api/ohlc   │  │  /api/correlation   │   │
│  │  /api/stop  │  │  /api/ticks  │  │  /api/spread        │   │
│  │  /api/stats │  │  /api/export │  │  /api/alerts        │   │
│  └─────────────┘  └──────────────┘  └─────────────────────┘   │
└────────────────┬────────────────┬────────────────┬─────────────┘
                 │                │                │
                 ▼                ▼                ▼
┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐
│  WebSocket       │  │  Data Manager     │  │  Analytics     │
│  Manager         │  │                   │  │  Engine        │
│                  │  │  - Store ticks    │  │                │
│  - Connect to    │  │  - Resample OHLC  │  │  - Spread      │
│  - Binance WS    │  │  - Query data     │  │  - Correlation │
│  - Process ticks │  │  - SQLite ops     │  │  - Statistics  │
│  - Buffer mgmt   │  │                   │  │  - Regression  │
└────────┬─────────┘  └─────────┬────────┘  └────────────────┘
         │                      │
         │                      ▼
         │            ┌──────────────────┐
         │            │  SQLite Database │
         │            │                  │
         │            │  Tables:         │
         │            │  - ticks         │
         │            │  - ohlc          │
         │            │  - analytics     │
         │            └──────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL DATA SOURCE                          │
│              Binance Futures WebSocket API                       │
│          wss://fstream.binance.com/ws/{symbol}@trade            │
└─────────────────────────────────────────────────────────────────┘
```

## 📊 Data Flow

```
1. User starts collection via Dashboard
   │
   ▼
2. WebSocket Manager connects to Binance
   │
   ▼
3. Real-time ticks received and buffered
   │
   ▼
4. Buffer flushed to SQLite every 1 second
   │
   ▼
5. Automatic resampling every 10 seconds
   │
   ▼
6. OHLC bars created (1s, 1m, 5m)
   │
   ▼
7. Dashboard queries API for latest data
   │
   ▼
8. Charts update automatically
```


### Data Collection
- `POST /api/start` - Start WebSocket collection
- `POST /api/stop` - Stop all connections
- `GET /api/status` - Get collection status

### Data Retrieval
- `GET /api/ticks/{symbol}?limit=100` - Get recent tick data
- `GET /api/ohlc/{symbol}?timeframe=1m&limit=100` - Get OHLC data
- `GET /api/symbols` - List all symbols with data
- `GET /api/stats/{symbol}?window=60` - Get statistical summary

### Analytics
- `GET /api/spread?symbols=btcusdt,ethusdt&window=100` - Calculate spread
- `GET /api/correlation?symbols=btcusdt,ethusdt&window=20` - Calculate correlation

### Alerts
- `POST /api/alerts` - Create alert rule
- `GET /api/alerts` - List all alerts
- `GET /api/alerts/triggered` - Get triggered alerts
- `DELETE /api/alerts/{alert_id}` - Delete alert

### Data Management
- `GET /api/export/{symbol}?format=csv` - Export data
- `POST /api/upload/ohlc` - Upload historical data


