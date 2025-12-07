"""
Streamlit Dashboard for Trading Analytics Platform
"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime
import numpy as np

# Configuration
API_BASE = "http://localhost:8000"
st.set_page_config(page_title="Trading Analytics Platform", layout="wide", page_icon="📈")

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .alert-card {
        background: #ff6b6b;
        padding: 0.8rem;
        border-radius: 8px;
        color: white;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
def api_get(endpoint):
    """Make GET request to API"""
    try:
        response = requests.get(f"{API_BASE}{endpoint}", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

def api_post(endpoint, data=None):
    """Make POST request to API"""
    try:
        response = requests.post(f"{API_BASE}{endpoint}", json=data, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

# Initialize session state
if 'collecting' not in st.session_state:
    st.session_state.collecting = False
if 'selected_symbols' not in st.session_state:
    st.session_state.selected_symbols = ['btcusdt', 'ethusdt']
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = True

# Main Dashboard
st.markdown('<p class="main-header">📈 Real-Time Trading Analytics Platform</p>', unsafe_allow_html=True)
st.markdown("**MFT Statistical Arbitrage & Market Microstructure Analytics**")

# Debug/Status Bar
with st.expander("🔧 System Status & Debug Info", expanded=False):
    col1, col2, col3 = st.columns(3)
    with col1:
        api_health = api_get("/health")
        if api_health:
            st.success("✅ Backend: Connected")
            st.json(api_health)
        else:
            st.error("❌ Backend: Not responding")
    
    with col2:
        status = api_get("/api/status")
        if status:
            st.info(f"🔴 Collecting: {status.get('is_collecting', False)}")
            st.text(f"Active Connections: {status.get('connections', 0)}")
            st.text(f"Symbols: {status.get('active_symbols', [])}")
        else:
            st.warning("⚠️ Status unavailable")
    
    with col3:
        symbols_data = api_get("/api/symbols")
        if symbols_data and symbols_data.get('symbols'):
            st.success(f"📊 Symbols in DB: {len(symbols_data['symbols'])}")
            st.text(", ".join(symbols_data['symbols']))
        else:
            st.info("No data yet - Start collection!")

# Sidebar
with st.sidebar:
    st.header("⚙️ Control Panel")
    
    # Symbol selection
    symbol_input = st.text_input(
        "Symbols (comma-separated)",
        value=",".join(st.session_state.selected_symbols)
    )
    
    # Start/Stop buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Start", width="stretch", type="primary"):
            symbols = [s.strip().lower() for s in symbol_input.split(",")]
            result = api_post("/api/start", {"symbols": symbols})
            if result:
                st.session_state.collecting = True
                st.session_state.selected_symbols = symbols
                st.success(f"Started collecting {len(symbols)} symbols")
    
    with col2:
        if st.button("🛑 Stop", width="stretch"):
            result = api_post("/api/stop")
            if result:
                st.session_state.collecting = False
                st.success("Collection stopped")
    
    # Status
    status = api_get("/api/status")
    if status:
        st.metric("Status", "🟢 Collecting" if status['is_collecting'] else "🔴 Stopped")
        st.metric("Active Symbols", status.get('connections', 0))
        st.metric("Uptime", status.get('uptime', 'N/A'))
    
    st.divider()
    
    # Analytics Settings
    st.header("📊 Analytics Settings")
    timeframe = st.selectbox("Timeframe", ["1s", "1m", "5m"], index=1)
    rolling_window = st.slider("Rolling Window", 5, 100, 20)
    regression_method = st.selectbox("Regression Method", ["OLS", "Kalman"], index=0)
    
    st.divider()
    
    # Auto-refresh
    st.session_state.auto_refresh = st.checkbox("Auto Refresh", value=True)
    if st.session_state.auto_refresh:
        refresh_interval = st.slider("Refresh Rate (sec)", 1, 10, 3)

# Main Content Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Overview", "📉 Spread Analysis", "🔗 Correlation", "🔔 Alerts"
])

# ============================================================================
# TAB 1: Overview
# ============================================================================
with tab1:
    st.header("Market Overview")
    
    # Get available symbols
    symbols_data = api_get("/api/symbols")
    available_symbols = symbols_data.get('symbols', []) if symbols_data else []
    
    if not available_symbols:
        st.info("👆 Start data collection to see analytics")
    else:
        # Display stats for each symbol
        cols = st.columns(min(len(available_symbols), 3))
        
        for idx, symbol in enumerate(available_symbols[:6]):
            with cols[idx % 3]:
                stats = api_get(f"/api/stats/{symbol}?window={rolling_window}")
                if stats and 'error' not in stats:
                    st.markdown(f"### {symbol.upper()}")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Last Price", f"${stats['last_price']:,.2f}")
                        st.metric("Mean", f"${stats['mean']:,.2f}")
                    with col2:
                        st.metric("Std Dev", f"${stats['std']:,.2f}")
                        st.metric("Volume", f"{stats['volume']:,.2f}")
        
        st.divider()
        
        # Live Chart Section with Auto-Update
        st.subheader("🔴 Live Chart Monitor")
        
        if len(available_symbols) > 0:
            chart_symbol = st.selectbox("Select Symbol for Live Chart", available_symbols, key="live_chart_symbol")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                chart_type = st.radio("Chart Type", ["Candlestick", "Line", "Area"], horizontal=True)
            with col2:
                chart_timeframe = st.selectbox("Chart Timeframe", ["1s", "1m", "5m"], key="chart_tf")
            with col3:
                chart_limit = st.slider("Data Points", 20, 200, 50)
            
            # Get data for live chart
            ohlc_chart = api_get(f"/api/ohlc/{chart_symbol}?timeframe={chart_timeframe}&limit={chart_limit}")
            
            if ohlc_chart and ohlc_chart.get('data') and len(ohlc_chart['data']) > 0:
                df_chart = pd.DataFrame(ohlc_chart['data'])
                df_chart['timestamp'] = pd.to_datetime(df_chart['timestamp'], format='ISO8601')
                
                # Create chart based on type
                fig_live = go.Figure()
                
                if chart_type == "Candlestick":
                    fig_live.add_trace(go.Candlestick(
                        x=df_chart['timestamp'],
                        open=df_chart['open'],
                        high=df_chart['high'],
                        low=df_chart['low'],
                        close=df_chart['close'],
                        name=chart_symbol.upper(),
                        increasing_line_color='#00ff00',
                        decreasing_line_color='#ff0000',
                        increasing_fillcolor='rgba(0, 255, 0, 0.3)',
                        decreasing_fillcolor='rgba(255, 0, 0, 0.3)'
                    ))
                elif chart_type == "Line":
                    fig_live.add_trace(go.Scatter(
                        x=df_chart['timestamp'],
                        y=df_chart['close'],
                        mode='lines',
                        name='Close Price',
                        line=dict(color='#00d4ff', width=2)
                    ))
                else:  # Area
                    fig_live.add_trace(go.Scatter(
                        x=df_chart['timestamp'],
                        y=df_chart['close'],
                        mode='lines',
                        name='Close Price',
                        fill='tozeroy',
                        line=dict(color='#00d4ff', width=2),
                        fillcolor='rgba(0, 212, 255, 0.2)'
                    ))
                
                # Add moving average
                if len(df_chart) >= 20:
                    df_chart['ma20'] = df_chart['close'].rolling(window=20).mean()
                    fig_live.add_trace(go.Scatter(
                        x=df_chart['timestamp'],
                        y=df_chart['ma20'],
                        mode='lines',
                        name='MA(20)',
                        line=dict(color='orange', width=1, dash='dash')
                    ))
                
                fig_live.update_layout(
                    title=f"{chart_symbol.upper()} - Live {chart_type} Chart ({chart_timeframe})",
                    xaxis_title="Time",
                    yaxis_title="Price (USD)",
                    height=500,
                    hovermode='x unified',
                    template='plotly_dark',
                    xaxis_rangeslider_visible=False,
                    showlegend=True
                )
                
                # Add current price annotation
                last_price = df_chart['close'].iloc[-1]
                fig_live.add_annotation(
                    x=df_chart['timestamp'].iloc[-1],
                    y=last_price,
                    text=f"${last_price:,.2f}",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor="#00ff00",
                    ax=50,
                    ay=-30,
                    bgcolor="#00ff00",
                    font=dict(color="black", size=12)
                )
                
                st.plotly_chart(fig_live, width="stretch")
                
                # Show live stats
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("Last Price", f"${last_price:,.2f}", 
                             delta=f"{((last_price - df_chart['close'].iloc[-2]) / df_chart['close'].iloc[-2] * 100):.2f}%")
                with col2:
                    st.metric("High", f"${df_chart['high'].max():,.2f}")
                with col3:
                    st.metric("Low", f"${df_chart['low'].min():,.2f}")
                with col4:
                    st.metric("Volume", f"{df_chart['volume'].sum():,.0f}")
                with col5:
                    price_change = ((last_price - df_chart['close'].iloc[0]) / df_chart['close'].iloc[0] * 100)
                    st.metric("Change %", f"{price_change:+.2f}%")
                
                st.success(f"✅ Chart updating every {refresh_interval} seconds (Auto-refresh: {'ON' if st.session_state.auto_refresh else 'OFF'})")
            else:
                st.warning("⏳ Waiting for chart data... Start data collection first!")
        
        st.divider()
        
        # Price charts for selected symbols
        st.subheader("Real-Time Price Charts")
        
        for symbol in available_symbols[:2]:
            st.markdown(f"### 📊 {symbol.upper()}")
            
            # Try OHLC data first
            ohlc_data = api_get(f"/api/ohlc/{symbol}?timeframe={timeframe}&limit=100")
            
            if ohlc_data and ohlc_data.get('data') and len(ohlc_data['data']) > 0:
                df = pd.DataFrame(ohlc_data['data'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')
                
                fig = make_subplots(
                    rows=2, cols=1,
                    row_heights=[0.7, 0.3],
                    subplot_titles=(f"{symbol.upper()} Price (Timeframe: {timeframe})", "Volume"),
                    vertical_spacing=0.1
                )
                
                # Candlestick chart with custom colors
                fig.add_trace(
                    go.Candlestick(
                        x=df['timestamp'],
                        open=df['open'],
                        high=df['high'],
                        low=df['low'],
                        close=df['close'],
                        name="Price",
                        increasing_line_color='#26a69a',
                        decreasing_line_color='#ef5350',
                        increasing_fillcolor='#26a69a',
                        decreasing_fillcolor='#ef5350'
                    ),
                    row=1, col=1
                )
                
                # Volume bars with color based on price change
                colors = ['green' if df.iloc[i]['close'] >= df.iloc[i]['open'] else 'red' 
                         for i in range(len(df))]
                
                fig.add_trace(
                    go.Bar(
                        x=df['timestamp'], 
                        y=df['volume'], 
                        name="Volume", 
                        marker_color=colors,
                        opacity=0.7
                    ),
                    row=2, col=1
                )
                
                fig.update_layout(
                    height=600,
                    showlegend=False,
                    xaxis_rangeslider_visible=False,
                    hovermode='x unified',
                    template='plotly_dark'
                )
                
                fig.update_xaxes(title_text="Time", row=2, col=1)
                fig.update_yaxes(title_text="Price", row=1, col=1)
                fig.update_yaxes(title_text="Volume", row=2, col=1)
                
                st.plotly_chart(fig, width="stretch")
                
                # Show data summary
                st.caption(f"📈 Data Points: {len(df)} | Last Updated: {df['timestamp'].iloc[-1]}")
                
            else:
                # Fallback: Show tick data as line chart if OHLC not available
                st.warning(f"⏳ Waiting for OHLC data to accumulate for {symbol.upper()}...")
                
                tick_data = api_get(f"/api/ticks/{symbol}?limit=100")
                if tick_data and tick_data.get('data'):
                    df_ticks = pd.DataFrame(tick_data['data'])
                    df_ticks['timestamp'] = pd.to_datetime(df_ticks['timestamp'], format='ISO8601')
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df_ticks['timestamp'],
                        y=df_ticks['price'],
                        mode='lines',
                        name='Price',
                        line=dict(color='#1f77b4', width=2)
                    ))
                    
                    fig.update_layout(
                        title=f"{symbol.upper()} - Tick Data (Real-time)",
                        xaxis_title="Time",
                        yaxis_title="Price",
                        height=400,
                        hovermode='x unified',
                        template='plotly_dark'
                    )
                    
                    st.plotly_chart(fig, width="stretch")
                    st.info(f"💡 Showing tick data. OHLC candles will appear after ~60 seconds of collection.")
                else:
                    st.info(f"⏳ Collecting data for {symbol.upper()}... Please wait 30-60 seconds.")

# ============================================================================
# TAB 2: Spread Analysis
# ============================================================================
with tab2:
    st.header("Spread Analysis & Z-Score")
    
    if len(available_symbols) >= 2:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            selected_pair = st.multiselect(
                "Select Symbol Pair",
                available_symbols,
                default=available_symbols[:2],
                max_selections=2,
                key="spread_analysis_pair"
            )
        
        with col2:
            calc_button = st.button("Calculate Spread", type="primary", width="stretch")
        
        if len(selected_pair) == 2 and calc_button:
            with st.spinner("Calculating spread..."):
                spread_data = api_get(
                    f"/api/spread?symbols={','.join(selected_pair)}&window={rolling_window}&method={regression_method.lower()}"
                )
                
                if spread_data and 'error' not in spread_data:
                    # Display metrics
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Hedge Ratio (β)", f"{spread_data['hedge_ratio']:.4f}")
                    with col2:
                        st.metric("Current Spread", f"{spread_data['current_spread']:.2f}")
                    with col3:
                        st.metric("Z-Score", f"{spread_data['z_score']:.2f}")
                    with col4:
                        half_life = spread_data.get('half_life')
                        st.metric("Half-Life", f"{half_life:.1f}" if half_life else "N/A")
                    
                    # Plot spread and z-score
                    spread_series = spread_data.get('spread_series', [])
                    if spread_series:
                        df_spread = pd.DataFrame(spread_series)
                        df_spread['timestamp'] = pd.to_datetime(df_spread['timestamp'], format='ISO8601')
                        
                        fig = make_subplots(
                            rows=2, cols=1,
                            subplot_titles=("Spread", "Z-Score"),
                            vertical_spacing=0.15
                        )
                        
                        # Spread
                        fig.add_trace(
                            go.Scatter(
                                x=df_spread['timestamp'],
                                y=df_spread['spread'],
                                mode='lines',
                                name='Spread',
                                line=dict(color='blue', width=2)
                            ),
                            row=1, col=1
                        )
                        
                        # Add mean line
                        mean_spread = spread_data['spread_mean']
                        fig.add_hline(y=mean_spread, line_dash="dash", line_color="gray", row=1, col=1)
                        
                        # Z-Score
                        fig.add_trace(
                            go.Scatter(
                                x=df_spread['timestamp'],
                                y=df_spread['z_score'],
                                mode='lines',
                                name='Z-Score',
                                line=dict(color='purple', width=2)
                            ),
                            row=2, col=1
                        )
                        
                        # Add threshold lines
                        fig.add_hline(y=2, line_dash="dash", line_color="red", row=2, col=1)
                        fig.add_hline(y=-2, line_dash="dash", line_color="red", row=2, col=1)
                        fig.add_hline(y=0, line_dash="solid", line_color="gray", row=2, col=1)
                        
                        fig.update_layout(height=600, showlegend=False)
                        fig.update_xaxes(title_text="Time")
                        fig.update_yaxes(title_text="Spread", row=1, col=1)
                        fig.update_yaxes(title_text="Z-Score", row=2, col=1)
                        
                        st.plotly_chart(fig, width="stretch")
                        
                        # Interpretation
                        current_z = spread_data['z_score']
                        if abs(current_z) > 2:
                            st.warning(f"⚠️ **Mean Reversion Signal**: Z-score is {current_z:.2f} (|z| > 2)")
                        elif abs(current_z) > 1:
                            st.info(f"📊 Z-score is {current_z:.2f} - Moderate deviation")
                        else:
                            st.success(f"✅ Z-score is {current_z:.2f} - Within normal range")
                else:
                    st.error(spread_data.get('error', 'Error calculating spread'))
    else:
        st.info("Need at least 2 symbols with data to calculate spread")

# ============================================================================
# TAB 3: Correlation Analysis
# ============================================================================
with tab3:
    st.header("Rolling Correlation Analysis")
    
    if len(available_symbols) >= 2:
        selected_corr_symbols = st.multiselect(
            "Select Symbols (2+)",
            available_symbols,
            default=available_symbols[:3] if len(available_symbols) >= 3 else available_symbols,
            key="correlation_analysis_symbols"
        )
        
        if len(selected_corr_symbols) >= 2 and st.button("Calculate Correlation", type="primary"):
            with st.spinner("Calculating correlations..."):
                corr_data = api_get(
                    f"/api/correlation?symbols={','.join(selected_corr_symbols)}&window={rolling_window}&timeframe={timeframe}"
                )
                
                if corr_data and 'error' not in corr_data:
                    # Correlation Matrix Heatmap
                    st.subheader("Current Correlation Matrix")
                    
                    corr_matrix = corr_data.get('correlation_matrix', {})
                    if corr_matrix:
                        df_corr = pd.DataFrame(corr_matrix)
                        
                        fig = go.Figure(data=go.Heatmap(
                            z=df_corr.values,
                            x=df_corr.columns,
                            y=df_corr.index,
                            colorscale='RdBu',
                            zmid=0,
                            text=df_corr.values,
                            texttemplate='%{text:.2f}',
                            textfont={"size": 12}
                        ))
                        
                        fig.update_layout(
                            title="Correlation Heatmap",
                            height=400
                        )
                        
                        st.plotly_chart(fig, width="stretch")
                    
                    # Rolling Correlation Time Series
                    st.subheader("Rolling Correlation Over Time")
                    
                    rolling_corrs = corr_data.get('rolling_correlations', {})
                    if rolling_corrs:
                        fig = go.Figure()
                        
                        for pair_name, data in rolling_corrs.items():
                            df_pair = pd.DataFrame(data)
                            df_pair['timestamp'] = pd.to_datetime(df_pair['timestamp'], format='ISO8601')
                            
                            fig.add_trace(go.Scatter(
                                x=df_pair['timestamp'],
                                y=df_pair['correlation'],
                                mode='lines',
                                name=pair_name.replace('_', ' vs ').upper()
                            ))
                        
                        fig.update_layout(
                            title="Rolling Correlation",
                            xaxis_title="Time",
                            yaxis_title="Correlation",
                            height=400,
                            hovermode='x unified'
                        )
                        
                        st.plotly_chart(fig, width="stretch")
                else:
                    st.error(corr_data.get('error', 'Error calculating correlation'))
    else:
        st.info("Need at least 2 symbols with data")

# ============================================================================
# TAB 4: Cointegration Test
# ============================================================================
with tab4:
    st.header("ADF Cointegration Test")
    
    st.markdown("""
    **Augmented Dickey-Fuller Test** checks if the spread between two assets is mean-reverting.
    - **H0 (Null Hypothesis)**: Spread has unit root (non-stationary)
    - **H1 (Alternative)**: Spread is stationary (mean-reverting)
    - **Reject H0** if p-value < 0.05 → Assets are cointegrated
    """)
    
    if len(available_symbols) >= 2:
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            adf_pair = st.multiselect(
                "Select Symbol Pair",
                available_symbols,
                default=available_symbols[:2],
                max_selections=2,
                key="adf_test_pair"
            )
        
        with col2:
            max_lag = st.number_input("Max Lag", 1, 20, 10)
        
        with col3:
            if st.button("Run ADF Test", type="primary", width="stretch"):
                if len(adf_pair) == 2:
                    with st.spinner("Running ADF test..."):
                        adf_result = api_post(
                            f"/api/analytics/adf?symbols={','.join(adf_pair)}&max_lag={max_lag}"
                        )
                        
                        if adf_result and 'error' not in adf_result:
                            # Display results
                            st.subheader("Test Results")
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric("ADF Statistic", f"{adf_result['adf_statistic']:.4f}")
                            with col2:
                                st.metric("P-Value", f"{adf_result['p_value']:.4f}")
                            with col3:
                                cointegrated = adf_result['is_cointegrated']
                                st.metric("Cointegrated", "✅ Yes" if cointegrated else "❌ No")
                            
                            # Critical values
                            st.subheader("Critical Values")
                            crit_vals = adf_result.get('critical_values', {})
                            df_crit = pd.DataFrame([crit_vals]).T
                            df_crit.columns = ['Critical Value']
                            st.dataframe(df_crit, width="stretch")
                            
                            # Interpretation
                            st.subheader("Interpretation")
                            if adf_result['is_cointegrated']:
                                st.success(f"""
                                ✅ **Cointegrated (Mean-Reverting)**
                                
                                The spread between {adf_pair[0].upper()} and {adf_pair[1].upper()} 
                                is statistically significant for mean reversion trading.
                                
                                - ADF Statistic: {adf_result['adf_statistic']:.4f}
                                - P-Value: {adf_result['p_value']:.4f} < 0.05
                                """)
                            else:
                                st.warning(f"""
                                ❌ **Not Cointegrated**
                                
                                The spread shows no statistical evidence of mean reversion.
                                
                                - ADF Statistic: {adf_result['adf_statistic']:.4f}
                                - P-Value: {adf_result['p_value']:.4f} ≥ 0.05
                                """)
                        else:
                            st.error(adf_result.get('error', 'Error running ADF test'))
    else:
        st.info("Need at least 2 symbols with data")

# ============================================================================
# TAB 4: Alerts
# ============================================================================
with tab4:
    st.header("🔔 Alert Management")
    
    # Create new alert
    st.subheader("Create New Alert")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        alert_name = st.text_input("Alert Name", "Price Alert")
    
    with col2:
        alert_condition = st.text_input("Condition", "price > 50000", 
                                       help="Format: variable operator value (e.g., price > 50000)")
    
    with col3:
        if st.button("Create Alert", type="primary", width="stretch"):
            result = api_post("/api/alerts", {
                "name": alert_name,
                "condition": alert_condition,
                "symbols": available_symbols,
                "enabled": True
            })
            if result:
                st.success("Alert created!")
    
    st.divider()
    
    # Active alerts
    st.subheader("Active Alerts")
    alerts = api_get("/api/alerts")
    
    if alerts and alerts.get('alerts'):
        for alert in alerts['alerts']:
            col1, col2, col3, col4 = st.columns([2, 3, 1, 1])
            
            with col1:
                st.markdown(f"**{alert['name']}**")
            with col2:
                st.text(alert['condition'])
            with col3:
                st.text(f"Triggers: {alert.get('trigger_count', 0)}")
            with col4:
                if st.button("Delete", key=f"del_{alert['id']}"):
                    requests.delete(f"{API_BASE}/api/alerts/{alert['id']}")
                    st.rerun()
    else:
        st.info("No active alerts")
    
    st.divider()
    
    # Triggered alerts
    st.subheader("Recent Triggers")
    triggered = api_get("/api/alerts/triggered")
    
    if triggered and triggered.get('alerts'):
        for alert in triggered['alerts'][:10]:
            st.markdown(f"""
            <div class="alert-card">
                <strong>{alert['rule_name']}</strong> - {alert['symbol'].upper()}<br>
                Price: ${alert['price']:,.2f} | {alert['triggered_at']}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No triggered alerts")

# Auto-refresh logic
if st.session_state.auto_refresh and st.session_state.collecting:
    time.sleep(refresh_interval)
    st.rerun()