"""
===================================================================
  main.py - Ø§Ù„Ù…Ù„Ù Ø§Ù„Ø±Ø¦ÙŠØ³ÙŠ Ù„Ø¨ÙˆØª Ø§Ù„ØªØ¯Ø§ÙˆÙ„ Ø§Ù„Ø°ÙƒÙŠ v2.0
  Main Entry Point - AI Trading Bot v2.0
===================================================================
  ÙŠØ´ØºÙ„ Ø¬Ù…ÙŠØ¹ Ø§Ù„Ù…ÙƒÙˆÙ†Ø§Øª Ù…Ø¹ Ø§Ù„ØªØ±Ù‚ÙŠØ§Øª Ø§Ù„Ø§Ø­ØªØ±Ø§ÙÙŠØ©:
  - Multi-Timeframe Analysis
  - AI Ensemble (3 models)
  - Market Regime Detection
  - Trailing SL + Partial TP
  - Strategy Optimizer
===================================================================
"""

import os
import sys
import time
import asyncio
import logging
import threading
import signal
from datetime import datetime

import uvicorn

from config import Config, setup_logging
from database import Database
from binance_client import BinanceClient
from technical_analysis import TechnicalAnalyzer
from ai_model import AIModel
from market_regime import MarketRegime
from strategy_engine import StrategyEngine
from risk_manager import RiskManager
from execution_engine import ExecutionEngine
from strategy_optimizer import StrategyOptimizer
from alerts import AlertSystem
from telegram_bot import create_telegram_app, set_components
from dashboard.app import app as dashboard_app, set_bot_ref
from websocket_manager import WebSocketManager
from order_book_analyzer import OrderBookAnalyzer


# Ensure console output can print Arabic/emoji on Windows terminals.
def _configure_stdio_encoding():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_configure_stdio_encoding()

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ Ø¥Ø¹Ø¯Ø§Ø¯ Ø§Ù„Ø³Ø¬Ù„Ø§Øª â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
logger = setup_logging()


class TradingBot:
    """Ø¨ÙˆØª Ø§Ù„ØªØ¯Ø§ÙˆÙ„ Ø§Ù„Ø±Ø¦ÙŠØ³ÙŠ v2.0"""

    def __init__(self):
        logger.info("=" * 60)
        logger.info("ðŸ¤– ØªÙ‡ÙŠØ¦Ø© Ø¨ÙˆØª Ø§Ù„ØªØ¯Ø§ÙˆÙ„ Ø§Ù„Ø°ÙƒÙŠ v2.0...")
        logger.info("=" * 60)

        # ØªÙ‡ÙŠØ¦Ø© Ù‚Ø§Ø¹Ø¯Ø© Ø§Ù„Ø¨ÙŠØ§Ù†Ø§Øª
        self.db = Database()
        self.db.init_db()
        logger.info("âœ… Ù‚Ø§Ø¹Ø¯Ø© Ø§Ù„Ø¨ÙŠØ§Ù†Ø§Øª Ø¬Ø§Ù‡Ø²Ø©")

        # ØªÙ‡ÙŠØ¦Ø© Ø¹Ù…ÙŠÙ„ Binance
        self.client = BinanceClient()
        logger.info("âœ… Ø¹Ù…ÙŠÙ„ Binance Ù…ØªØµÙ„")

        # ØªÙ‡ÙŠØ¦Ø© Ù…Ø¯ÙŠØ± WebSockets
        self.ws_manager = WebSocketManager(self.client)
        logger.info("âœ… Ù…Ø¯ÙŠØ± Ø¨ÙŠØ§Ù†Ø§Øª WebSockets Ø¬Ø§Ù‡Ø² (Zero-Latency)")

        # ØªÙ‡ÙŠØ¦Ø© Ø§Ù„Ù…Ø­Ù„Ù„ Ø§Ù„ÙÙ†ÙŠ Ø§Ù„Ù…ØªÙ‚Ø¯Ù…
        self.analyzer = TechnicalAnalyzer()
        logger.info("âœ… Ø§Ù„Ù…Ø­Ù„Ù„ Ø§Ù„ÙÙ†ÙŠ Ø§Ù„Ù…ØªÙ‚Ø¯Ù… (MTF) Ø¬Ø§Ù‡Ø²")

        # ØªÙ‡ÙŠØ¦Ø© Ù†Ù…ÙˆØ°Ø¬ AI Ensemble
        self.ai_model = AIModel()
        logger.info("âœ… Ù†Ù…ÙˆØ°Ø¬ AI Ensemble Ø¬Ø§Ù‡Ø²")

        # ØªÙ‡ÙŠØ¦Ø© ÙƒØ´Ù Ù†Ø¸Ø§Ù… Ø§Ù„Ø³ÙˆÙ‚
        self.regime = MarketRegime()
        logger.info("âœ… ÙƒØ§Ø´Ù Ù†Ø¸Ø§Ù… Ø§Ù„Ø³ÙˆÙ‚ Ø¬Ø§Ù‡Ø²")
        
        # ØªÙ‡ÙŠØ¦Ø© Ù…Ø­Ù„Ù„ Ø¯ÙØªØ± Ø§Ù„Ø£ÙˆØ§Ù…Ø± (Whales & Liquidity)
        self.ob_analyzer = OrderBookAnalyzer(self.ws_manager)
        logger.info("âœ… Ù…Ø­Ù„Ù„ Ø¯ÙØªØ± Ø§Ù„Ø£ÙˆØ§Ù…Ø± (Ø­ÙŠØªØ§Ù† ÙˆØ³ÙŠÙˆÙ„Ø©) Ø¬Ø§Ù‡Ø²")

        # ØªÙ‡ÙŠØ¦Ø© Ù…Ø­Ø±Ùƒ Ø§Ù„Ø§Ø³ØªØ±Ø§ØªÙŠØ¬ÙŠØ© (Ù…Ø¹ regime Ùˆ ob_analyzer)
        self.strategy = StrategyEngine(self.analyzer, self.ai_model, self.regime)
        self.strategy.ob_analyzer = self.ob_analyzer
        logger.info("âœ… Ù…Ø­Ø±Ùƒ Ø§Ù„Ø§Ø³ØªØ±Ø§ØªÙŠØ¬ÙŠØ© v3.0 Ø¬Ø§Ù‡Ø² (Ù†Ù‚Ø§Ø· + Ø¯ÙØªØ± Ø§Ù„Ø£ÙˆØ§Ù…Ø±)")

        # ØªÙ‡ÙŠØ¦Ø© Ù…Ø¯ÙŠØ± Ø§Ù„Ù…Ø®Ø§Ø·Ø±
        self.risk = RiskManager(self.db)
        logger.info("âœ… Ù…Ø¯ÙŠØ± Ø§Ù„Ù…Ø®Ø§Ø·Ø± Ø§Ù„Ø¯ÙŠÙ†Ø§Ù…ÙŠÙƒÙŠ Ø¬Ø§Ù‡Ø²")

        # ØªÙ‡ÙŠØ¦Ø© Ù†Ø¸Ø§Ù… Ø§Ù„ØªÙ†Ø¨ÙŠÙ‡Ø§Øª
        self.alerts = AlertSystem()
        logger.info("âœ… Ù†Ø¸Ø§Ù… Ø§Ù„ØªÙ†Ø¨ÙŠÙ‡Ø§Øª Ø¬Ø§Ù‡Ø²")

        # ØªÙ‡ÙŠØ¦Ø© Ù…Ø­Ø±Ùƒ Ø§Ù„ØªÙ†ÙÙŠØ° Ø§Ù„Ù…ØªÙ‚Ø¯Ù…
        self.execution = ExecutionEngine(
            self.client, self.db, self.risk, self.alerts
        )
        logger.info("âœ… Ù…Ø­Ø±Ùƒ Ø§Ù„ØªÙ†ÙÙŠØ° (Trailing SL + Partial TP) Ø¬Ø§Ù‡Ø²")

        # ØªÙ‡ÙŠØ¦Ø© Ø§Ù„Ù…Ø­Ø³Ù‘Ù† Ø§Ù„ØªÙ„Ù‚Ø§Ø¦ÙŠ
        self.optimizer = StrategyOptimizer(self.db, self.strategy)
        logger.info("âœ… Ù…Ø­Ø³Ù‘Ù† Ø§Ù„Ø§Ø³ØªØ±Ø§ØªÙŠØ¬ÙŠØ© Ø§Ù„ØªÙ„Ù‚Ø§Ø¦ÙŠ Ø¬Ø§Ù‡Ø²")

        # Ø­Ø§Ù„Ø© Ø§Ù„Ø¨ÙˆØª
        self.is_running = False
        self._stop_event = asyncio.Event()
        self.latest_scan_results = {}

        # ØªØ¹ÙŠÙŠÙ† Ø§Ù„Ù…Ø±Ø§Ø¬Ø¹
        self._setup_references()

        logger.info("=" * 60)
        logger.info("ðŸ¤– v2.0 - ØªÙ… ØªÙ‡ÙŠØ¦Ø© Ø¬Ù…ÙŠØ¹ Ø§Ù„Ù…ÙƒÙˆÙ†Ø§Øª Ø¨Ù†Ø¬Ø§Ø­!")
        logger.info("=" * 60)

    def _setup_references(self):
        """ØªØ¹ÙŠÙŠÙ† Ø§Ù„Ù…Ø±Ø§Ø¬Ø¹ Ù„Ø¨ÙˆØª Telegram ÙˆÙ„ÙˆØ­Ø© Ø§Ù„ØªØ­ÙƒÙ…"""
        set_components({
            "client": self.client,
            "db": self.db,
            "risk": self.risk,
            "execution": self.execution,
            "strategy": self.strategy,
            "analyzer": self.analyzer,
            "ai": self.ai_model,
            "alerts": self.alerts,
            "is_running": self.is_running,
            "get_running_state": self._get_running_state,
            "set_running_state": self._set_running_state,
            "get_scan_results": lambda: getattr(self, "latest_scan_results", {})
        })
        set_bot_ref({
            "client": self.client,
            "is_running": self.is_running,
            "risk": self.risk,
            "execution_engine": self.execution,
            "get_running_state": self._get_running_state,
            "set_running_state": self._set_running_state,
            "get_scan_results": lambda: getattr(self, "latest_scan_results", {})
        })

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ ØªØ¯Ø±ÙŠØ¨ AI Ensemble â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _get_running_state(self):
        return self.is_running

    def _set_running_state(self, running: bool):
        self.is_running = bool(running)
        state = {"is_running": self.is_running}
        set_components(state)
        set_bot_ref(state)

    def _refresh_runtime_pairs_from_balance(self):
        """Merge wallet-held quote pairs into runtime scanning list."""
        if not getattr(Config, "SCAN_BALANCE_COINS", False):
            return
        if not hasattr(self.client, "get_balance_trading_pairs"):
            return

        try:
            quote_assets = getattr(Config, "BALANCE_QUOTE_ASSETS", None)
            if not quote_assets:
                quote_assets = [getattr(Config, "BALANCE_QUOTE_ASSET", "USDT")]

            detected_pairs = self.client.get_balance_trading_pairs(
                quote_assets=quote_assets,
                min_total=Config.BALANCE_COIN_MIN_TOTAL,
                max_pairs=Config.MAX_BALANCE_SCAN_PAIRS,
            )
            if not detected_pairs:
                return

            base_pairs = list(Config.TRADING_PAIRS)
            merged_pairs = []
            seen = set()

            for pair in base_pairs + detected_pairs:
                if pair not in seen:
                    seen.add(pair)
                    merged_pairs.append(pair)

            added_pairs = [p for p in merged_pairs if p not in base_pairs]
            if added_pairs:
                Config.TRADING_PAIRS = merged_pairs
                logger.info(
                    f"🔎 تمت إضافة {len(added_pairs)} زوج من الرصيد: {added_pairs}"
                )

        except Exception as e:
            logger.error(f"خطأ أثناء فحص عملات الرصيد: {e}")

    def _sync_funding_wallet_to_spot(self):
        """Optional: move configured assets from Funding wallet to Spot wallet."""
        if not getattr(Config, "AUTO_TRANSFER_FUNDING_TO_SPOT", False):
            return
        if not hasattr(self.client, "sync_funding_to_spot"):
            return

        try:
            moved = self.client.sync_funding_to_spot(
                assets=getattr(Config, "FUNDING_TRANSFER_ASSETS", ["BNB"]),
                min_free=getattr(Config, "FUNDING_TRANSFER_MIN_FREE", 0.00001),
            )
            if moved:
                logger.info(f"💱 Funding -> Spot completed: {moved}")
            else:
                logger.info("💱 Funding -> Spot: no transferable balances found")
        except Exception as e:
            logger.error(f"Funding wallet sync error: {e}")

    def _sync_spot_to_futures(self):
        """تحويل رصيد USDT من Spot إلى Futures تلقائياً."""
        if not getattr(Config, "ENABLE_FUTURES", False):
            return
        if not getattr(Config, "AUTO_TRANSFER_SPOT_TO_FUTURES", False):
            return
        if not hasattr(self.client, "transfer_spot_to_futures"):
            return

        try:
            transferred = self.client.transfer_spot_to_futures("USDT")
            if transferred > 0:
                logger.info(f"💱 تم تحويل {transferred:.4f} USDT من Spot إلى Futures")
            else:
                logger.info("💱 Spot -> Futures: لا يوجد رصيد للتحويل (قد يكون موجوداً في Futures بالفعل)")
        except Exception as e:
            logger.error(f"خطأ تحويل Spot -> Futures: {e}")

    def _show_ip_address(self):
        """عرض عنوان IP المحلي والعام عند بدء التشغيل."""
        import socket
        # IP المحلي
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "غير معروف"

        # IP العام
        public_ip = "غير معروف"
        try:
            import urllib.request
            public_ip = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode("utf-8")
        except Exception:
            try:
                import urllib.request
                public_ip = urllib.request.urlopen("https://ifconfig.me/ip", timeout=5).read().decode("utf-8").strip()
            except Exception:
                pass

        logger.info("=" * 50)
        logger.info(f"🌐 IP المحلي (Local):  {local_ip}")
        logger.info(f"🌍 IP العام (Public):  {public_ip}")
        logger.info("=" * 50)


    def train_ai_model(self):
        """ØªØ¯Ø±ÙŠØ¨ Ù†Ù…Ø§Ø°Ø¬ AI Ensemble"""
        logger.info("ðŸ§  Ø¨Ø¯Ø¡ ØªØ¯Ø±ÙŠØ¨ AI Ensemble...")
        for pair in Config.TRADING_PAIRS:
            try:
                ohlcv = self.client.fetch_ohlcv(pair, limit=500)
                if ohlcv and len(ohlcv) > 200:
                    self.ai_model.train(ohlcv)
                    logger.info(f"âœ… ØªÙ… ØªØ¯Ø±ÙŠØ¨ Ensemble Ø¹Ù„Ù‰ {pair}")
                else:
                    logger.warning(f"âš ï¸ Ø¨ÙŠØ§Ù†Ø§Øª ØºÙŠØ± ÙƒØ§ÙÙŠØ© Ù„ØªØ¯Ø±ÙŠØ¨ {pair}")
            except Exception as e:
                logger.error(f"âŒ Ø®Ø·Ø£ ØªØ¯Ø±ÙŠØ¨ AI Ø¹Ù„Ù‰ {pair}: {e}")
            finally:
                # Keep exit monitoring active during long startup/training phase.
                try:
                    if self.execution.open_trades:
                        self.execution.check_open_trades()
                except Exception as monitor_err:
                    logger.error(f"❌ خطأ مراقبة الصفقات أثناء التدريب: {monitor_err}")

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ Ø¯ÙˆØ±Ø© Ø§Ù„ØªØ¯Ø§ÙˆÙ„ v2.0 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    async def trading_cycle(self):
        """Ø¯ÙˆØ±Ø© ØªØ¯Ø§ÙˆÙ„ Ø§Ø­ØªØ±Ø§ÙÙŠØ©"""

        # Fast monitor pass so profit exits are not delayed.
        try:
            self.execution.check_open_trades()
        except Exception as e:
            logger.error(f"❌ خطأ مراقبة الصفقات (بداية الدورة): {e}")
        
        # 0. ÙØ­Øµ Ø§Ù†Ù‡ÙŠØ§Ø± Ø§Ù„Ø³ÙˆÙ‚ Ø§Ù„Ø´Ø§Ù…Ù„ (Global Kill Switch)
        btc_ohlcv = self.ws_manager.fetch_ohlcv("BTC/USDT", limit=2)
        if btc_ohlcv and len(btc_ohlcv) > 0:
            btc_current = btc_ohlcv[-1][4] if len(btc_ohlcv[-1]) >= 5 else 0
            btc_open = btc_ohlcv[-1][1] if len(btc_ohlcv[-1]) >= 2 else 0
            
            if self.risk.check_global_crash(btc_current, btc_open):
                logger.critical("ðŸš¨ ØªØ¹Ù„ÙŠÙ‚ Ø¯ÙˆØ±Ø© Ø§Ù„ØªØ¯Ø§ÙˆÙ„ Ù…Ø¤Ù‚ØªØ§Ù‹ Ù„Ø­ÙŠÙ† Ø§Ø³ØªÙ‚Ø±Ø§Ø± Ø§Ù„Ø³ÙˆÙ‚!")
                self.execution.close_all_trades("BTC_FLASH_CRASH")
                return  # ØªØ®Ø·ÙŠ Ø§Ù„Ø¯ÙˆØ±Ø© ÙˆØ¹Ø¯Ù… ÙØªØ­ Ø£ÙŠ ØµÙÙ‚Ø§Øª
        
        for idx, pair in enumerate(Config.TRADING_PAIRS, start=1):
            try:
                # 1. Ø¬Ù„Ø¨ Ø§Ù„Ø¨ÙŠØ§Ù†Ø§Øª Ø§Ù„Ù„Ø­Ø¸ÙŠØ© Ù…Ù† Ø§Ù„Ø°Ø§ÙƒØ±Ø© (Ø³Ø±ÙŠØ¹ Ø¬Ø¯Ø§Ù‹)
                ohlcv = self.ws_manager.fetch_ohlcv(pair, limit=300)
                if not ohlcv:
                    continue

                # 2. ØªÙ‚ÙŠÙŠÙ… Ø§Ù„Ø§Ø³ØªØ±Ø§ØªÙŠØ¬ÙŠØ© (Ø¨Ø¯Ù„Ø§Ù‹ Ù…Ù† client Ø§Ù„Ø£ØµÙ„ÙŠ Ù†Ù…Ø±Ø± ws_manager)
                signal = self.strategy.evaluate(ohlcv, pair, self.ws_manager)
                
                self.latest_scan_results[pair] = {
                    "symbol": pair,
                    "buy_score": signal.get("buy_score", 0),
                    "ai_score": signal.get("ai_score", 0),
                    "regime": signal.get("regime", "UNKNOWN"),
                    "is_pump": signal.get("is_pump", False),
                    "is_steady": signal.get("is_steady", False),
                    "price": signal.get("price", 0),
                    "timestamp": time.time()
                }

                # 3. ØªÙ†ÙÙŠØ° Ø¥Ø°Ø§ ÙƒØ§Ù†Øª Ø§Ù„Ø¥Ø´Ø§Ø±Ø© ÙˆØ§Ø¶Ø­Ø©
                if signal["signal"] in ("BUY", "SELL"):
                    result = self.execution.execute_trade(signal, pair)
                    if result["success"]:
                        logger.info(f"âœ… ØµÙÙ‚Ø© Ù†Ø§Ø¬Ø­Ø©: {pair}")
                    else:
                        logger.info(
                            f"â¸ï¸ Ù„Ù… ØªÙÙ†ÙØ° {pair}: {result.get('reason')}"
                        )

                # Extra monitoring during long symbol scans.
                if self.execution.open_trades and (idx % 4 == 0):
                    self.execution.check_open_trades()

            except Exception as e:
                logger.error(f"âŒ Ø®Ø·Ø£ ÙÙŠ Ø¯ÙˆØ±Ø© {pair}: {e}")
                self.db.log_error("TRADING_CYCLE", str(e), "main")

        # 4. Ù…Ø±Ø§Ù‚Ø¨Ø© Ø§Ù„ØµÙÙ‚Ø§Øª Ø§Ù„Ù…ÙØªÙˆØ­Ø© (Ù…Ø±Ø© ÙˆØ§Ø­Ø¯Ø© ÙÙŠ Ù†Ù‡Ø§ÙŠØ© Ø§Ù„Ø¯ÙˆØ±Ø©)
        try:
            self.execution.check_open_trades()
        except Exception as e:
            logger.error(f"âŒ Ø®Ø·Ø£ Ù…Ø±Ø§Ù‚Ø¨Ø© Ø§Ù„ØµÙÙ‚Ø§Øª: {e}")

        # 5. ØªØ­Ø¯ÙŠØ« Ø¹Ø¯Ø¯ Ø§Ù„ØµÙÙ‚Ø§Øª
        self.risk.update_trade_count(len(self.execution.open_trades))

        # 6. ØªØ­Ø¯ÙŠØ« Ø§Ù„Ø£Ø¯Ø§Ø¡ Ø§Ù„ÙŠÙˆÙ…ÙŠ
        try:
            balance = self.client.get_usdt_balance()
            if balance > 0:
                self.db.update_daily_performance(
                    starting_balance=self.risk.starting_balance or balance,
                    ending_balance=balance
                )
        except Exception as e:
            logger.error(f"Ø®Ø·Ø£ ÙÙŠ ØªØ­Ø¯ÙŠØ« Ø§Ù„Ø£Ø¯Ø§Ø¡: {e}")

        # 7. ØªØ­Ø³ÙŠÙ† Ø§Ù„Ø§Ø³ØªØ±Ø§ØªÙŠØ¬ÙŠØ© (ÙƒÙ„ 24 Ø³Ø§Ø¹Ø©)
        try:
            self.optimizer.optimize()
        except Exception as e:
            logger.error(f"Ø®Ø·Ø£ ÙÙŠ Ø§Ù„ØªØ­Ø³ÙŠÙ†: {e}")

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ Ø§Ù„Ø­Ù„Ù‚Ø© Ø§Ù„Ø±Ø¦ÙŠØ³ÙŠØ© â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    async def run_trading_loop(self):
        """Ø§Ù„Ø­Ù„Ù‚Ø© Ø§Ù„Ø±Ø¦ÙŠØ³ÙŠØ© Ù„Ù„ØªØ¯Ø§ÙˆÙ„"""
        logger.info("ðŸ”„ Ø¨Ø¯Ø¡ Ø­Ù„Ù‚Ø© Ø§Ù„ØªØ¯Ø§ÙˆÙ„ v2.0...")
        logger.info(
            f"âš™ï¸ Ø§Ù„Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª: Ø´Ø±Ø§Ø¡â‰¥{self.strategy.buy_threshold} | "
            f"AIâ‰¥{self.strategy.min_ai_score} | "
            f"Ø£Ø²ÙˆØ§Ø¬={Config.TRADING_PAIRS} | "
            f"ÙØ§ØµÙ„={Config.TRADING_INTERVAL}s"
        )

        while not self._stop_event.is_set():
            if self.is_running:
                try:
                    await self.trading_cycle()
                except Exception as e:
                    logger.error(f"âŒ Ø®Ø·Ø£ ÙÙŠ Ø§Ù„Ø­Ù„Ù‚Ø©: {e}")
                    self.db.log_error("MAIN_LOOP", str(e), "main")
            else:
                # Ù†ÙˆØ§ØµÙ„ Ù…Ø±Ø§Ù‚Ø¨Ø© Ø§Ù„ØµÙÙ‚Ø§Øª Ø§Ù„Ù…ÙØªÙˆØ­Ø© Ø­ØªÙ‰ Ø£Ø«Ù†Ø§Ø¡ Ø§Ù„ØªÙˆÙ‚Ù Ø§Ù„Ù…Ø¤Ù‚Øª
                try:
                    self.execution.check_open_trades()
                    self.risk.update_trade_count(len(self.execution.open_trades))
                except Exception as e:
                    logger.error(f"âŒ Ø®Ø·Ø£ Ù…Ø±Ø§Ù‚Ø¨Ø© Ø£Ø«Ù†Ø§Ø¡ Ø§Ù„ØªÙˆÙ‚Ù: {e}")

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=Config.TRADING_INTERVAL
                )
            except asyncio.TimeoutError:
                pass

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ ØªØ´ØºÙŠÙ„ Dashboard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def run_dashboard(self):
        try:
            config = uvicorn.Config(
                dashboard_app,
                host=Config.DASHBOARD_HOST,
                port=Config.DASHBOARD_PORT,
                log_level="warning"
            )
            server = uvicorn.Server(config)
            server.run()
        except Exception as e:
            logger.error(f"âŒ Ø®Ø·Ø£ ÙÙŠ Ù„ÙˆØ­Ø© Ø§Ù„ØªØ­ÙƒÙ…: {e}")

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ Ø§Ù„ØªØ´ØºÙŠÙ„ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    async def start(self):
        self._set_running_state(True)

        # عرض عنوان IP الخاص بالجهاز
        self._show_ip_address()

        # Close any open trades before moving funds
        self.execution.close_all_trades("USER_STOP")

        # Optional funding wallet sync before scanning pairs.
        self._sync_funding_wallet_to_spot()

        # تحويل تلقائي من Spot إلى Futures إذا كان وضع الفيوتشرز مفعّل
        self._sync_spot_to_futures()

        # Restore persisted open trades after restarts.
        try:
            self.execution.restore_open_trades_from_db()
        except Exception as e:
            logger.error(f"Failed to restore open trades: {e}")

        # Expand trading scope with wallet-held assets before warmup.
        self._refresh_runtime_pairs_from_balance()

        # Early monitor pass after restoring positions.
        try:
            if self.execution.open_trades:
                self.execution.check_open_trades()
        except Exception as e:
            logger.error(f"❌ خطأ مراقبة الصفقات (بدء التشغيل): {e}")

        # Dashboard (Start first for immediate UI access)
        dashboard_thread = threading.Thread(
            target=self.run_dashboard, daemon=True
        )
        dashboard_thread.start()
        logger.info(
            f"ðŸ“Š Ù„ÙˆØ­Ø© Ø§Ù„ØªØ­ÙƒÙ…: http://localhost:{Config.DASHBOARD_PORT}"
        )

        # ØªØ´ØºÙŠÙ„ WebSockets Ù„Ø³Ø­Ø¨ Ø§Ù„Ø¨ÙŠØ§Ù†Ø§Øª ÙÙŠ Ø§Ù„Ø®Ù„ÙÙŠØ©
        logger.info("ðŸ“¡ Ø¬Ø§Ø±ÙŠ ØªØ´ØºÙŠÙ„ WebSockets ÙˆØ§Ù„ØªØ­Ù…ÙŠÙ„ Ø§Ù„Ù…Ø³Ø¨Ù‚ Ù„Ù„Ø¨ÙŠØ§Ù†Ø§Øª...")
        await self.ws_manager.start()

        # Monitor again right after websocket warmup.
        try:
            if self.execution.open_trades:
                self.execution.check_open_trades()
        except Exception as e:
            logger.error(f"❌ خطأ مراقبة الصفقات (بعد WebSockets): {e}")

        # ØªØ¯Ø±ÙŠØ¨ AI
        try:
            self.train_ai_model()
        except Exception as e:
            logger.warning(f"âš ï¸ ØªØ®Ø·ÙŠ ØªØ¯Ø±ÙŠØ¨ AI: {e}")

        # ØªÙ†Ø¨ÙŠÙ‡ Ø§Ù„ØªØ´ØºÙŠÙ„
        self.alerts.bot_started()

        # Telegram
        telegram_app = create_telegram_app()

        if telegram_app:
            async with telegram_app:
                await telegram_app.initialize()
                await telegram_app.start()
                await telegram_app.updater.start_polling(drop_pending_updates=True)
                logger.info("ðŸ¤– Ø¨ÙˆØª Telegram ÙŠØ¹Ù…Ù„")
                await self.run_trading_loop()
                await telegram_app.updater.stop()
                await telegram_app.stop()
                await telegram_app.shutdown()
        else:
            logger.info("âš ï¸ ØªØ´ØºÙŠÙ„ Ø¨Ø¯ÙˆÙ† Telegram")
            await self.run_trading_loop()

    def stop(self):
        logger.info("ðŸ›‘ Ø¥ÙŠÙ‚Ø§Ù Ø§Ù„Ø¨ÙˆØª...")
        self._set_running_state(False)
        self._stop_event.set()
        self.alerts.bot_stopped("Ø¥ÙŠÙ‚Ø§Ù ÙŠØ¯ÙˆÙŠ")
        logger.info("âœ… ØªÙ… Ø¥ÙŠÙ‚Ø§Ù Ø§Ù„Ø¨ÙˆØª Ø¨Ù†Ø¬Ø§Ø­")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ Ù†Ù‚Ø·Ø© Ø§Ù„Ø¯Ø®ÙˆÙ„ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def main():
    print("""
    â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
    â•‘       ðŸ¤– AI Trading Bot v2.0                 â•‘
    â•‘       Ù†Ø¸Ø§Ù… Ø§Ù„ØªØ¯Ø§ÙˆÙ„ Ø§Ù„Ø°ÙƒÙŠ Ø§Ù„Ø§Ø­ØªØ±Ø§ÙÙŠ            â•‘
    â•‘                                              â•‘
    â•‘  âœ… Multi-Timeframe Analysis                  â•‘
    â•‘  âœ… AI Ensemble (3 Models)                    â•‘
    â•‘  âœ… Market Regime Detection                   â•‘
    â•‘  âœ… Trailing Stop + Partial TP                â•‘
    â•‘  âœ… Auto Strategy Optimizer                   â•‘
    â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    """)

    if not os.path.exists(os.path.join(os.path.dirname(__file__), ".env")):
        print("âš ï¸  Ù„Ù… ÙŠØªÙ… Ø§Ù„Ø¹Ø«ÙˆØ± Ø¹Ù„Ù‰ Ù…Ù„Ù .env")
        sys.exit(1)

    if not Config.validate():
        print("\nâŒ ÙŠØ±Ø¬Ù‰ Ø¥ØµÙ„Ø§Ø­ Ø§Ù„Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª")
        sys.exit(1)

    bot = TradingBot()

    def handle_shutdown(signum, frame):
        print("\nðŸ›‘ Ø¬Ø§Ø±Ù Ø§Ù„Ø¥ÙŠÙ‚Ø§Ù...")
        bot.stop()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        bot.stop()
    except Exception as e:
        logger.error(f"âŒ Ø®Ø·Ø£ Ø­Ø±Ø¬: {e}")
        bot.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
