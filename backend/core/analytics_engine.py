"""
Analytics Engine - Computes trading analytics
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime
from statsmodels.tsa.stattools import adfuller
from sklearn.linear_model import LinearRegression, HuberRegressor
from scipy import stats

try:
    from pykalman import KalmanFilter
except ImportError:
    KalmanFilter = None

class AnalyticsEngine:
    """Computes trading analytics on market data"""
    
    def __init__(self, data_manager):
        self.data_manager = data_manager
    
    async def get_stats(self, symbol: str, window: int = 100) -> Dict:
        """Calculate basic statistics for a symbol"""
        ticks = await self.data_manager.get_recent_ticks(symbol, window)
        
        if not ticks:
            return {"error": "No data available"}
        
        prices = [t['price'] for t in ticks]
        sizes = [t['size'] for t in ticks]
        
        return {
            "symbol": symbol,
            "count": len(prices),
            "last_price": prices[-1],
            "mean": np.mean(prices),
            "std": np.std(prices),
            "min": np.min(prices),
            "max": np.max(prices),
            "volume": np.sum(sizes),
            "vwap": np.average(prices, weights=sizes) if sizes else np.mean(prices)
        }
    
    async def calculate_spread(self, symbol1: str, symbol2: str, 
                               window: int = 100, method: str = "ols") -> Dict:
        """Calculate spread between two symbols"""
        ticks1 = await self.data_manager.get_recent_ticks(symbol1, window)
        ticks2 = await self.data_manager.get_recent_ticks(symbol2, window)
        
        if not ticks1 or not ticks2:
            return {"error": "Insufficient data"}
        
        df1 = pd.DataFrame(ticks1).set_index('timestamp')
        df2 = pd.DataFrame(ticks2).set_index('timestamp')
        
        df = pd.merge(df1[['price']], df2[['price']], 
                      left_index=True, right_index=True, 
                      how='outer', suffixes=('_1', '_2'))
        df = df.fillna(method='ffill').dropna()
        
        if len(df) < 10:
            return {"error": "Insufficient aligned data"}
        
        if method == "kalman" and KalmanFilter:
            hedge_ratio = self._kalman_hedge_ratio(df['price_1'], df['price_2'])
        else:
            hedge_ratio = self._ols_hedge_ratio(df['price_1'], df['price_2'])
        
        spread = df['price_1'] - hedge_ratio * df['price_2']
        z_score = (spread - spread.mean()) / spread.std()
        half_life = self._calculate_half_life(spread.values)
        
        return {
            "symbol1": symbol1,
            "symbol2": symbol2,
            "method": method,
            "hedge_ratio": float(hedge_ratio) if np.isscalar(hedge_ratio) else float(hedge_ratio[-1]),
            "spread_mean": float(spread.mean()),
            "spread_std": float(spread.std()),
            "current_spread": float(spread.iloc[-1]),
            "z_score": float(z_score.iloc[-1]),
            "half_life": float(half_life) if half_life else None,
            "data_points": len(df),
            "spread_series": [
                {"timestamp": str(idx), "spread": float(val), "z_score": float(z)}
                for idx, val, z in zip(spread.index[-50:], spread.iloc[-50:], z_score.iloc[-50:])
            ]
        }
    
    def _ols_hedge_ratio(self, y: pd.Series, x: pd.Series) -> float:
        """Calculate hedge ratio using OLS"""
        X = x.values.reshape(-1, 1)
        Y = y.values.reshape(-1, 1)
        model = LinearRegression()
        model.fit(X, Y)
        return model.coef_[0][0]
    
    def _kalman_hedge_ratio(self, y: pd.Series, x: pd.Series) -> np.ndarray:
        """Calculate dynamic hedge ratio using Kalman Filter"""
        if not KalmanFilter:
            return self._ols_hedge_ratio(y, x)
        
        obs_mat = np.vstack([x, np.ones(len(x))]).T[:, np.newaxis]
        
        kf = KalmanFilter(
            n_dim_obs=1,
            n_dim_state=2,
            initial_state_mean=np.zeros(2),
            initial_state_covariance=np.ones((2, 2)),
            transition_matrices=np.eye(2),
            observation_matrices=obs_mat,
            observation_covariance=1.0,
            transition_covariance=0.01 * np.eye(2)
        )
        
        state_means, _ = kf.filter(y.values)
        return state_means[:, 0]
    
    def _calculate_half_life(self, spread: np.ndarray) -> Optional[float]:
        """Calculate half-life of mean reversion"""
        spread_lag = np.roll(spread, 1)[1:]
        spread_diff = spread[1:] - spread_lag
        
        try:
            X = spread_lag.reshape(-1, 1)
            y = spread_diff
            model = LinearRegression()
            model.fit(X, y)
            lambda_ = model.coef_[0]
            
            if lambda_ < 0:
                half_life = -np.log(2) / lambda_
                return half_life if half_life > 0 else None
        except:
            pass
        
        return None
    
    async def adf_test(self, symbol1: str, symbol2: str, max_lag: int = 10) -> Dict:
        """Perform ADF test for cointegration"""
        result = await self.calculate_spread(symbol1, symbol2, window=200, method="ols")
        
        if "error" in result:
            return result
        
        spread_data = result.get("spread_series", [])
        if len(spread_data) < 30:
            return {"error": "Insufficient data for ADF test"}
        
        spread = np.array([s["spread"] for s in spread_data])
        
        adf_result = adfuller(spread, maxlag=max_lag, autolag='AIC')
        
        return {
            "symbol1": symbol1,
            "symbol2": symbol2,
            "adf_statistic": float(adf_result[0]),
            "p_value": float(adf_result[1]),
            "n_lags": int(adf_result[2]),
            "n_obs": int(adf_result[3]),
            "critical_values": {k: float(v) for k, v in adf_result[4].items()},
            "is_cointegrated": adf_result[1] < 0.05,
            "interpretation": "Cointegrated" if adf_result[1] < 0.05 else "Not cointegrated"
        }
    
    async def rolling_correlation(self, symbols: List[str], 
                                  window: int = 20, timeframe: str = "1m") -> Dict:
        """Calculate rolling correlation"""
        if len(symbols) < 2:
            return {"error": "At least 2 symbols required"}
        
        data_frames = []
        for symbol in symbols:
            ohlc = await self.data_manager.get_ohlc(symbol, timeframe, limit=200)
            if ohlc:
                df = pd.DataFrame(ohlc)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.set_index('timestamp')[['close']].rename(columns={'close': symbol})
                data_frames.append(df)
        
        if len(data_frames) < 2:
            return {"error": "Insufficient data"}
        
        df = pd.concat(data_frames, axis=1).fillna(method='ffill').dropna()
        
        # Use available data, but require at least 5 points
        if len(df) < 5:
            return {"error": f"Need at least 5 data points, got {len(df)}"}
        
        # Adjust window to available data
        actual_window = min(window, len(df))
        
        correlations = {}
        for i, sym1 in enumerate(symbols):
            for sym2 in symbols[i+1:]:
                if sym1 in df.columns and sym2 in df.columns:
                    rolling_corr = df[sym1].rolling(actual_window).corr(df[sym2])
                    correlations[f"{sym1}_{sym2}"] = [
                        {"timestamp": str(idx), "correlation": float(val)}
                        for idx, val in rolling_corr.dropna().tail(50).items()
                    ]
        
        current_corr = df.tail(min(actual_window, len(df))).corr().to_dict()
        
        return {
            "symbols": symbols,
            "window": window,
            "rolling_correlations": correlations,
            "correlation_matrix": current_corr,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def backtest_mean_reversion(self, symbol1: str, symbol2: str,
                                     entry_z: float = 2.0, exit_z: float = 0.0,
                                     window: int = 100) -> Dict:
        """Simple mean reversion backtest"""
        result = await self.calculate_spread(symbol1, symbol2, window=500, method="ols")
        
        if "error" in result:
            return result
        
        spread_data = result.get("spread_series", [])
        if len(spread_data) < 100:
            return {"error": "Insufficient data"}
        
        trades = []
        position = 0
        entry_price = 0
        
        for point in spread_data:
            z = point["z_score"]
            
            if position == 0:
                if z > entry_z:
                    position = -1
                    entry_price = point["spread"]
                    trades.append({
                        "entry_time": point["timestamp"],
                        "entry_z": z,
                        "entry_spread": entry_price,
                        "type": "short"
                    })
                elif z < -entry_z:
                    position = 1
                    entry_price = point["spread"]
                    trades.append({
                        "entry_time": point["timestamp"],
                        "entry_z": z,
                        "entry_spread": entry_price,
                        "type": "long"
                    })
            
            elif position != 0:
                if (position == 1 and z > exit_z) or (position == -1 and z < -exit_z):
                    pnl = (point["spread"] - entry_price) * position
                    trades[-1].update({
                        "exit_time": point["timestamp"],
                        "exit_z": z,
                        "exit_spread": point["spread"],
                        "pnl": pnl
                    })
                    position = 0
        
        completed_trades = [t for t in trades if "pnl" in t]
        if not completed_trades:
            return {"error": "No completed trades"}
        
        pnls = [t["pnl"] for t in completed_trades]
        winning_trades = [p for p in pnls if p > 0]
        
        return {
            "symbol1": symbol1,
            "symbol2": symbol2,
            "entry_z": entry_z,
            "exit_z": exit_z,
            "total_trades": len(completed_trades),
            "winning_trades": len(winning_trades),
            "win_rate": len(winning_trades) / len(completed_trades),
            "total_pnl": sum(pnls),
            "avg_pnl": np.mean(pnls),
            "sharpe": np.mean(pnls) / np.std(pnls) if np.std(pnls) > 0 else 0,
            "max_win": max(pnls),
            "max_loss": min(pnls),
            "trades": completed_trades[-10:]
        }
    
    async def get_timeseries_stats(self, symbol: str, timeframe: str = "1m", 
                                   limit: int = 100) -> List[Dict]:
        """Get time-series statistics"""
        ohlc = await self.data_manager.get_ohlc(symbol, timeframe, limit)
        
        if not ohlc:
            return []
        
        df = pd.DataFrame(ohlc)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(10).std()
        df['range'] = df['high'] - df['low']
        df['range_pct'] = (df['range'] / df['close']) * 100
        
        result = []
        for _, row in df.tail(limit).iterrows():
            result.append({
                "timestamp": row['timestamp'].isoformat(),
                "open": round(row['open'], 2),
                "high": round(row['high'], 2),
                "low": round(row['low'], 2),
                "close": round(row['close'], 2),
                "volume": round(row['volume'], 2),
                "returns": round(row['returns'] * 100, 4) if pd.notna(row['returns']) else None,
                "volatility": round(row['volatility'] * 100, 4) if pd.notna(row['volatility']) else None,
                "range_pct": round(row['range_pct'], 4) if pd.notna(row['range_pct']) else None
            })
        
        return result