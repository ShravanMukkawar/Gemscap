"""
WebSocket Manager - Handles Binance WebSocket connections
"""
import asyncio
import websockets
import json
from typing import List, Dict, Set
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections to Binance Futures"""
    
    def __init__(self, data_manager, alert_manager):
        self.data_manager = data_manager
        self.alert_manager = alert_manager
        self.connections: Dict[str, asyncio.Task] = {}
        self.active_symbols: Set[str] = set()
        self.is_running = False
        self.start_time = None
        self.tick_buffer: List[Dict] = []
        self.buffer_size = 100
    
    async def start_collection(self, symbols: List[str]):
        """Start collecting data for symbols"""
        self.is_running = True
        self.start_time = datetime.utcnow()
        
        for symbol in symbols:
            if symbol not in self.active_symbols:
                self.active_symbols.add(symbol)
                task = asyncio.create_task(self._connect_symbol(symbol))
                self.connections[symbol] = task
                logger.info(f"Started WebSocket for {symbol}")
        
        # Start buffer flusher
        if not hasattr(self, '_flusher_task') or self._flusher_task.done():
            self._flusher_task = asyncio.create_task(self._flush_buffer_periodically())
        
        # Start resampler
        if not hasattr(self, '_resampler_task') or self._resampler_task.done():
            self._resampler_task = asyncio.create_task(self._resample_periodically())
        
        # Start initial resampler for quick chart display
        if not hasattr(self, '_initial_resampler_task') or self._initial_resampler_task.done():
            self._initial_resampler_task = asyncio.create_task(self._initial_resample())
    
    async def _connect_symbol(self, symbol: str):
        """Connect to Binance WebSocket for a symbol"""
        url = f"wss://fstream.binance.com/ws/{symbol}@trade"
        
        while symbol in self.active_symbols:
            try:
                async with websockets.connect(url) as ws:
                    logger.info(f"✅ Connected to {symbol}")
                    
                    async for message in ws:
                        if symbol not in self.active_symbols:
                            break
                        
                        try:
                            data = json.loads(message)
                            if data.get('e') == 'trade':
                                await self._process_tick(data)
                        except json.JSONDecodeError:
                            logger.error(f"Failed to decode message for {symbol}")
                        except Exception as e:
                            logger.error(f"Error processing tick for {symbol}: {e}")
                
            except websockets.exceptions.WebSocketException as e:
                logger.error(f"WebSocket error for {symbol}: {e}")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Unexpected error for {symbol}: {e}")
                await asyncio.sleep(5)
    
    async def _process_tick(self, data: Dict):
        """Process incoming tick data"""
        try:
            tick = {
                'symbol': data['s'].lower(),
                'ts': datetime.fromtimestamp(data['T'] / 1000).isoformat(),
                'price': float(data['p']),
                'size': float(data['q'])
            }
            
            # Add to buffer
            self.tick_buffer.append(tick)
            
            # Check alerts
            await self.alert_manager.check_tick(tick)
            
        except Exception as e:
            logger.error(f"Error processing tick: {e}")
    
    async def _flush_buffer_periodically(self):
        """Flush buffer to database periodically"""
        first_flush = True
        while self.is_running:
            await asyncio.sleep(1)
            
            if len(self.tick_buffer) > 0:
                ticks_to_store = self.tick_buffer.copy()
                self.tick_buffer.clear()
                
                try:
                    await self.data_manager.store_ticks_batch(ticks_to_store)
                    logger.debug(f"✅ Flushed {len(ticks_to_store)} ticks")
                    
                    # Trigger immediate resample after first flush for quick chart display
                    if first_flush:
                        first_flush = False
                        asyncio.create_task(self._quick_resample())
                        
                except Exception as e:
                    logger.error(f"Error flushing buffer: {e}")
                    self.tick_buffer.extend(ticks_to_store)
    
    async def _resample_periodically(self):
        """Resample tick data to OHLC periodically"""
        while self.is_running:
            await asyncio.sleep(10)  # Reduced from 60 to 10 seconds for more frequent updates
            
            for symbol in list(self.active_symbols):
                try:
                    logger.info(f"🔄 Starting periodic resample for {symbol}")
                    for timeframe in ['1s', '1m', '5m']:
                        lookback = {'1s': 1, '1m': 5, '5m': 15}[timeframe]
                        await self.data_manager.resample_ticks(symbol, timeframe, lookback)
                    
                    logger.info(f"✅ Resampled {symbol}")
                except Exception as e:
                    logger.error(f"Error resampling {symbol}: {e}")
    
    async def _initial_resample(self):
        """Perform initial quick resamples for immediate chart display"""
        # Wait for some initial data to accumulate
        for i in range(6):  # Wait up to 6 seconds
            await asyncio.sleep(1)
            if len(self.tick_buffer) > 5:  # If we have some ticks, start resampling
                break
        
        # Perform quick resamples every 2 seconds for the first 30 seconds
        for _ in range(15):
            if not self.is_running:
                break
            
            await asyncio.sleep(2)
            await self._quick_resample()
    
    async def _quick_resample(self):
        """Quick resample for initial chart display"""
        for symbol in list(self.active_symbols):
            try:
                logger.info(f"⚡ Quick resampling {symbol}")
                for timeframe in ['1s', '1m', '5m']:
                    lookback = {'1s': 1, '1m': 2, '5m': 5}[timeframe]
                    await self.data_manager.resample_ticks(symbol, timeframe, lookback)
                logger.info(f"⚡ Quick resampled {symbol}")
            except Exception as e:
                logger.error(f"Error quick resampling {symbol}: {e}")
    
    async def stop_all(self):
        """Stop all WebSocket connections"""
        self.is_running = False
        symbols_to_remove = list(self.active_symbols)
        self.active_symbols.clear()
        
        # Cancel all connection tasks
        for task in self.connections.values():
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.connections:
            await asyncio.gather(*self.connections.values(), return_exceptions=True)
        
        self.connections.clear()
        
        # Flush remaining buffer
        if self.tick_buffer:
            try:
                await self.data_manager.store_ticks_batch(self.tick_buffer)
                self.tick_buffer.clear()
            except Exception as e:
                logger.error(f"Error flushing final buffer: {e}")
        
        logger.info(f"✅ Stopped WebSocket connections for: {', '.join(symbols_to_remove)}")
    
    def get_uptime(self) -> str:
        """Get uptime in human-readable format"""
        if not self.start_time:
            return "Not started"
        
        delta = datetime.utcnow() - self.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h {minutes}m {seconds}s"