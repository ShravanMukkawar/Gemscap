"""
FastAPI Backend for Trading Analytics Platform
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
from datetime import datetime
import json
import io
import pandas as pd

from backend.core.manager import DataManager
from backend.core.analytics_engine import AnalyticsEngine
from backend.core.alert_manager import AlertManager
from backend.websocket.client import WebSocketManager

app = FastAPI(title="Trading Analytics API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
data_manager = DataManager()
analytics_engine = AnalyticsEngine(data_manager)
alert_manager = AlertManager()
ws_manager = WebSocketManager(data_manager, alert_manager)

# Pydantic models
class StartRequest(BaseModel):
    symbols: List[str]

class AlertRule(BaseModel):
    name: str
    condition: str  # e.g., "z_score > 2"
    symbols: List[str]
    enabled: bool = True

class OHLCData(BaseModel):
    symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float

@app.on_event("startup")
async def startup_event():
    """Initialize database and connections"""
    await data_manager.initialize()
    print("[OK] Backend initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await ws_manager.stop_all()
    print("[OK] Backend shutdown complete")

@app.get("/")
async def root():
    return {
        "service": "Trading Analytics API",
        "version": "1.0.0",
        "status": "running"
    }

# ============================================================================
# Data Collection Endpoints
# ============================================================================

@app.post("/api/start")
async def start_collection(request: StartRequest, background_tasks: BackgroundTasks):
    """Start WebSocket data collection for specified symbols"""
    try:
        symbols = [s.lower().strip() for s in request.symbols]
        background_tasks.add_task(ws_manager.start_collection, symbols)
        return {
            "status": "started",
            "symbols": symbols,
            "message": f"Started collecting data for {len(symbols)} symbols"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stop")
async def stop_collection():
    """Stop all WebSocket connections"""
    try:
        await ws_manager.stop_all()
        return {"status": "stopped", "message": "All connections stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def get_status():
    """Get collection status"""
    return {
        "active_symbols": ws_manager.active_symbols,
        "is_collecting": ws_manager.is_running,
        "connections": len(ws_manager.connections),
        "uptime": ws_manager.get_uptime()
    }

# ============================================================================
# Data Retrieval Endpoints
# ============================================================================

@app.get("/api/ticks/{symbol}")
async def get_ticks(symbol: str, limit: int = 100):
    """Get recent tick data for a symbol"""
    try:
        symbol = symbol.lower()
        ticks = await data_manager.get_recent_ticks(symbol, limit)
        return {
            "symbol": symbol,
            "count": len(ticks),
            "data": ticks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ohlc/{symbol}")
async def get_ohlc(symbol: str, timeframe: str = "1m", limit: int = 100):
    """Get OHLC data for a symbol"""
    try:
        symbol = symbol.lower()
        ohlc = await data_manager.get_ohlc(symbol, timeframe, limit)
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "count": len(ohlc),
            "data": ohlc
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats/{symbol}")
async def get_stats(symbol: str, window: int = 100):
    """Get statistical summary for a symbol"""
    try:
        symbol = symbol.lower()
        stats = await analytics_engine.get_stats(symbol, window)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Analytics Endpoints
# ============================================================================

@app.get("/api/spread")
async def calculate_spread(
    symbols: str,  # comma-separated
    window: int = 100,
    method: str = "ols"  # ols or kalman
):
    """Calculate spread between two symbols"""
    try:
        sym_list = [s.strip().lower() for s in symbols.split(",")]
        if len(sym_list) != 2:
            raise HTTPException(status_code=400, detail="Exactly 2 symbols required")
        
        result = await analytics_engine.calculate_spread(
            sym_list[0], sym_list[1], window, method
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analytics/adf")
async def run_adf_test(symbols: str, max_lag: int = 10):
    """Run ADF test for cointegration"""
    try:
        sym_list = [s.strip().lower() for s in symbols.split(",")]
        if len(sym_list) != 2:
            raise HTTPException(status_code=400, detail="Exactly 2 symbols required")
        
        result = await analytics_engine.adf_test(sym_list[0], sym_list[1], max_lag)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/correlation")
async def get_correlation(symbols: str, window: int = 60, timeframe: str = "1m"):
    """Calculate rolling correlation"""
    try:
        sym_list = [s.strip().lower() for s in symbols.split(",")]
        result = await analytics_engine.rolling_correlation(sym_list, window, timeframe)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/backtest")
async def run_backtest(
    symbols: str,
    entry_z: float = 2.0,
    exit_z: float = 0.0,
    window: int = 100
):
    """Run simple mean reversion backtest"""
    try:
        sym_list = [s.strip().lower() for s in symbols.split(",")]
        if len(sym_list) != 2:
            raise HTTPException(status_code=400, detail="Exactly 2 symbols required")
        
        result = await analytics_engine.backtest_mean_reversion(
            sym_list[0], sym_list[1], entry_z, exit_z, window
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Alert Endpoints
# ============================================================================

@app.post("/api/alerts")
async def create_alert(rule: AlertRule):
    """Create a new alert rule"""
    try:
        alert_id = alert_manager.add_rule(
            rule.name, rule.condition, rule.symbols, rule.enabled
        )
        return {"alert_id": alert_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts")
async def list_alerts():
    """Get all alert rules"""
    return {"alerts": alert_manager.get_all_rules()}

@app.delete("/api/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    """Delete an alert rule"""
    success = alert_manager.remove_rule(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "deleted"}

@app.get("/api/alerts/triggered")
async def get_triggered_alerts(limit: int = 50):
    """Get recently triggered alerts"""
    return {"alerts": alert_manager.get_triggered_alerts(limit)}

# ============================================================================
# Data Management Endpoints
# ============================================================================

@app.get("/api/export/{symbol}")
async def export_data(symbol: str, format: str = "csv", timeframe: str = "1m"):
    """Export data for a symbol"""
    try:
        symbol = symbol.lower()
        data = await data_manager.get_ohlc(symbol, timeframe, limit=10000)
        
        if not data:
            raise HTTPException(status_code=404, detail="No data found")
        
        df = pd.DataFrame(data)
        
        if format == "csv":
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={symbol}_{timeframe}.csv"}
            )
        else:  # json
            return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload/ohlc")
async def upload_ohlc(file: UploadFile = File(...)):
    """Upload historical OHLC data"""
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        
        # Validate columns
        required = ["symbol", "timestamp", "open", "high", "low", "close", "volume"]
        if not all(col in df.columns for col in required):
            raise HTTPException(status_code=400, detail=f"Missing required columns: {required}")
        
        # Store data
        await data_manager.store_bulk_ohlc(df.to_dict('records'))
        
        return {
            "status": "success",
            "rows": len(df),
            "symbols": df['symbol'].unique().tolist()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/symbols")
async def list_symbols():
    """Get list of all symbols with data"""
    try:
        symbols = await data_manager.get_all_symbols()
        return {"symbols": symbols}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/timeseries/{symbol}")
async def get_timeseries_stats(symbol: str, timeframe: str = "1m", limit: int = 100):
    """Get time-series statistics table"""
    try:
        symbol = symbol.lower()
        stats = await analytics_engine.get_timeseries_stats(symbol, timeframe, limit)
        return {"data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "collecting": ws_manager.is_running
    }