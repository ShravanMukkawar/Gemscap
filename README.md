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

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip package manager

### Installation

1. **Clone or download the project**
```bash
cd C:\Users\mukka\Desktop\Gemcap
```

2. **Create virtual environment**
```bash
python -m venv venv
venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

### Running the Application

**Option 1: Launch Everything (Recommended)**
```bash
python app.py
```
This starts both the FastAPI backend and Streamlit frontend automatically.

**Option 2: Manual Launch**

Terminal 1 - Backend:
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Terminal 2 - Frontend:
```bash
streamlit run frontend/dashboard.py
```

### Access the Application
- **Dashboard**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/health

## 📖 Usage Guide

### Starting Data Collection

1. Open the Dashboard at http://localhost:8501
2. In the sidebar, enter symbols (e.g., `btcusdt,ethusdt`)
3. Click **🚀 Start** button
4. Wait 5-10 seconds for data to populate
5. Charts will appear automatically

### Viewing Live Charts

**Overview Tab:**
- Real-time candlestick charts for each symbol
- Live price statistics
- Multiple chart types: Candlestick, Line, Area
- Adjustable timeframes: 1s, 1m, 5m

**Spread Analysis Tab:**
- Calculate spread between two symbols
- Z-score visualization
- Mean reversion signals

**Correlation Tab:**
- Correlation heatmap
- Rolling correlation over time
- Multiple symbol pair analysis

**Alerts Tab:**
- Create custom price alerts
- View triggered alerts
- Manage alert rules

### Stopping Collection

Click **🛑 Stop** button in the sidebar to stop all data collection.

## 🔧 Configuration

### Analytics Settings (Sidebar)

- **Timeframe**: Select data granularity (1s, 1m, 5m)
- **Rolling Window**: Adjust window size for calculations (5-100, default: 20)
- **Regression Method**: Choose between OLS or Kalman filtering
- **Auto Refresh**: Toggle automatic chart updates (1-10 seconds)

### Database Location

SQLite database is stored at: `data/trading.db`

## 📁 Project Structure

```
Gemcap/
├── app.py                      # Main entry point
├── requirements.txt            # Python dependencies
├── README.md                   # This file
│
├── backend/                    # Backend services
│   ├── main.py                # FastAPI application
│   ├── core/
│   │   ├── manager.py         # Data management & SQLite
│   │   ├── analytics_engine.py # Statistical analysis
│   │   └── alert_manager.py   # Alert system
│   └── websocket/
│       └── client.py          # WebSocket manager
│
├── frontend/                   # Frontend UI
│   └── dashboard.py           # Streamlit dashboard
│
└── data/                       # Data storage
    ├── trading.db             # SQLite database
    └── logs/                  # Log files
```

## 🛠️ Technology Stack

### Backend
- **FastAPI**: High-performance async web framework
- **Uvicorn**: ASGI server
- **WebSockets**: Real-time data streaming
- **SQLite**: Lightweight database
- **Pandas**: Data manipulation
- **NumPy**: Numerical computing

### Frontend
- **Streamlit**: Interactive dashboard framework
- **Plotly**: Interactive charting library
- **Requests**: HTTP client

### Analytics
- **Statsmodels**: Statistical analysis
- **SciPy**: Scientific computing
- **Scikit-learn**: Machine learning utilities

## 📊 API Endpoints

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

## 🔍 Key Features Explained

### Tick-to-OHLC Resampling

The platform automatically converts tick-level data to OHLC (Open-High-Low-Close) bars:

1. **Tick Collection**: Raw trade data stored in SQLite
2. **Buffering**: Ticks buffered for 1 second before bulk insert
3. **Resampling**: Every 10 seconds, ticks are resampled to OHLC
4. **Multiple Timeframes**: Generates 1s, 1m, and 5m bars simultaneously

### Real-Time Chart Updates

- **Initial Data**: Shows tick data as line chart if OHLC not ready
- **Quick Resample**: Triggers fast resample after first data batch
- **Auto-refresh**: Dashboard refreshes every 1-10 seconds (configurable)
- **Smooth Transition**: Automatically switches from tick to candlestick view

### Statistical Analysis

- **Rolling Statistics**: Mean, standard deviation calculated on rolling windows
- **Spread Calculation**: OLS or Kalman filter regression
- **Z-Score**: Standardized spread for mean reversion signals
- **Correlation**: Pearson correlation on rolling windows

## 🐛 Troubleshooting

### No data appearing in charts

1. Check if data collection is started (green indicator in sidebar)
2. Wait 10-15 seconds for initial resampling
3. Verify symbols are correct (lowercase, e.g., `btcusdt`)
4. Check API status at http://localhost:8000/health

### WebSocket connection errors

1. Verify internet connection
2. Check Binance API is accessible
3. Restart the backend service

### Database locked errors

1. Stop all running instances
2. Delete `data/trading.db` if corrupted
3. Restart the application

### Memory issues with large datasets

1. Reduce the number of symbols
2. Lower the data retention period
3. Use larger timeframes (5m instead of 1s)

## 🔒 Data Storage

### Database Schema

**ticks table:**
- id (INTEGER PRIMARY KEY)
- symbol (TEXT)
- timestamp (TEXT ISO8601)
- price (REAL)
- size (REAL)
- created_at (TEXT)

**ohlc table:**
- id (INTEGER PRIMARY KEY)
- symbol (TEXT)
- timeframe (TEXT: '1s', '1m', '5m')
- timestamp (TEXT ISO8601)
- open, high, low, close (REAL)
- volume (REAL)
- created_at (TEXT)

## 📈 Performance Metrics

- **Tick Processing**: ~1000 ticks/second per symbol
- **Database Writes**: Bulk inserts every 1 second
- **Resampling**: 10-second intervals for OHLC generation
- **API Response**: <100ms for most endpoints
- **Dashboard Refresh**: 1-10 seconds (configurable)

## 🚧 Future Enhancements

- [ ] Redis caching layer
- [ ] Multiple exchange support
- [ ] Advanced order book analytics
- [ ] Machine learning predictions
- [ ] Portfolio optimization
- [ ] Risk management tools
- [ ] Paper trading simulation
- [ ] Email/SMS alert notifications

## 📝 Notes

- The platform is designed for educational and research purposes
- Not intended for production trading without additional safeguards
- Always test with paper trading first
- Monitor resource usage with large datasets

## 🤝 Contributing

This is a personal project for MFT (Market Microstructure and Trading) research.

## 📄 License

Private project - All rights reserved.

## 📧 Contact

For questions or issues, please refer to the project documentation.

---

**Last Updated**: December 7, 2025  
**Version**: 1.0.0  
**Status**: Active Development
