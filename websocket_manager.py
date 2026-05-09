"""
===================================================================
  websocket_manager.py - جلب البيانات اللحظية (Zero-Latency)
  WebSocket Manager for Real-Time Tickers and Klines
===================================================================
  يسحب البيانات مرة واحدة في البداية عبر REST API، 
  ثم يقوم بتحديثها لحظياً عبر WebSockets لتجنب أي تأخير.
===================================================================
"""

import asyncio
import json
import logging
import aiohttp
from config import Config

logger = logging.getLogger("TradingBot.WebSocket")

class WebSocketManager:
    """إدارة اتصال WebSockets للحصول على أسعار وشموع لحظية"""
    
    def __init__(self, client):
        self._client = client
        self.tickers = {}  
        self.klines = {}   
        self.is_connected = False
        
        # التبديل بين سيرفر Spot وسيرفر Futures بناءً على الإعدادات
        if getattr(Config, "ENABLE_FUTURES", False):
            self.base_url = "wss://fstream.binance.com/stream"
        else:
            self.base_url = "wss://stream.binance.com:9443/stream"
        
    async def initial_load(self):
        """تحميل الشموع التاريخية لكل العملات لتكون الأساس"""
        logger.info("📡 جاري جلب البيانات التاريخية للذاكرة (قد يستغرق 10-20 ثانية)...")
        
        # نعملها في thread خارجي عشان ما نجمد الـ event loop
        await asyncio.to_thread(self._fetch_all_history_sync)
        logger.info("✅ تم تحميل البيانات التاريخية للذاكرة بنجاح")

    def _fetch_all_history_sync(self):
        """تُنفذ بشكل تسلسلي لتجنب حظر IP أو أخطاء DNS في ويندوز"""
        timeframes = list(set([Config.TIMEFRAME, "15m", "1h", "4h"]))
        total = len(Config.TRADING_PAIRS)
        
        for i, pair in enumerate(Config.TRADING_PAIRS):
            self.klines[pair] = {}
            self.tickers[pair] = {"last": 0}
            
            for tf in timeframes:
                try:
                    ohlcv = self._client.fetch_ohlcv(pair, tf, limit=300)
                    self.klines[pair][tf] = ohlcv
                except Exception as e:
                    logger.error(f"❌ خطأ بسيط في تحميل {pair} {tf}: {e}")
            
            # طباعة التقدم كل 10 عملات
            if (i + 1) % 10 == 0 or (i + 1) == total:
                logger.info(f"⏳ تم تحميل بيانات {i + 1} / {total} عملة...")
        
    async def start(self):
        """بدء الاتصال بالـ WebSockets"""
        await self.initial_load()
        asyncio.create_task(self._connect_and_listen())

    async def _connect_and_listen(self):
        streams = []
        for pair in Config.TRADING_PAIRS:
            s_lower = pair.replace("/", "").lower()
            streams.append(f"{s_lower}@ticker")
            streams.append(f"{s_lower}@kline_{Config.TIMEFRAME}")
            if Config.TIMEFRAME != "15m":
                streams.append(f"{s_lower}@kline_15m")
            streams.append(f"{s_lower}@kline_1h")
            streams.append(f"{s_lower}@kline_4h")
        
        # Binance allows max 1024 streams per connection
        sub_payload = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": 1
        }
        
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(self.base_url, heartbeat=30) as ws:
                        self.is_connected = True
                        logger.info("🔗 متصل بنجاح بـ Binance WebSockets (Zero-Latency)")
                        await ws.send_json(sub_payload)
                        
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                if "data" in data and "stream" in data:
                                    self._handle_stream_data(data["stream"], data["data"])
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
            except Exception as e:
                self.is_connected = False
                logger.error(f"❌ انقطع اتصال WebSocket: {e}. محاولة إعادة الاتصال...")
                await asyncio.sleep(5)
                
    def _handle_stream_data(self, stream, data):
        symbol_raw = data.get("s", "")
        pair = self._match_symbol(symbol_raw)
        if not pair:
            return

        # 1. Ticker Stream
        if "@ticker" in stream:
            self.tickers[pair]["last"] = float(data.get("c", 0))
            self.tickers[pair]["bid"] = float(data.get("b", 0))
            self.tickers[pair]["ask"] = float(data.get("a", 0))
            self.tickers[pair]["vol"] = float(data.get("v", 0))
            
        # 2. Kline Stream
        elif "@kline" in stream:
            kline = data.get("k", {})
            tf = kline.get("i")
            valid_tfs = [Config.TIMEFRAME, "15m", "1h", "4h"]
            if tf not in valid_tfs: return
            
            candle = [
                kline.get("t"),          # Open time
                float(kline.get("o")),   # Open
                float(kline.get("h")),   # High
                float(kline.get("l")),   # Low
                float(kline.get("c")),   # Close
                float(kline.get("v"))    # Volume
            ]
            
            hist = self.klines.get(pair, {}).get(tf, [])
            if not hist:
                return
                
            last_candle_ts = hist[-1][0]
            new_candle_ts = candle[0]
            
            if new_candle_ts == last_candle_ts:
                hist[-1] = candle # Update current live candle
            elif new_candle_ts > last_candle_ts:
                hist.append(candle) # Append new finished candle
                if len(hist) > 500:
                    hist.pop(0)

    def _match_symbol(self, raw):
        """مطابقة הرمز الخام من WebSocket مع المتوفر في الإعدادات"""
        for p in Config.TRADING_PAIRS:
            if p.replace("/", "") == raw:
                return p
        return None
        
    def fetch_ohlcv(self, symbol=None, timeframe=None, limit=500):
        """يحاكي return من fetch_ohlcv ليكون المخرج نفس شكل CCXT"""
        symbol = symbol or Config.DEFAULT_PAIR
        timeframe = timeframe or Config.TIMEFRAME
        data = self.klines.get(symbol, {}).get(timeframe, [])
        return list(data)[-limit:] if limit else list(data)
        
    def fetch_current_price(self, symbol=None):
        """جلب السعر اللحظي (بدون انتظار REST)"""
        symbol = symbol or Config.DEFAULT_PAIR
        return self.tickers.get(symbol, {}).get("last", 0.0)
