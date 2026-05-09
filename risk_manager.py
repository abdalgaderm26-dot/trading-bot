"""
===================================================================
  risk_manager.py - Advanced Risk Manager v2.0
===================================================================
"""

import time
import logging
from config import Config

logger = logging.getLogger("TradingBot.Risk")


class RiskManager:
    """Dynamic risk manager with position sizing and safety guards."""

    def __init__(self, db, client=None):
        self.db = db
        self.client = client
        self.starting_balance = 0
        self.daily_pnl = 0
        self.open_trade_count = 0
        self.auto_halt = False
        self.halt_reason = ""

        # Balance cache to reduce API calls
        self._cached_balances = {}
        self._last_balance_check = 0.0
        self._balance_ttl = max(1, int(getattr(Config, "BALANCE_CACHE_TTL", 8)))

        # Global Kill Switch
        self.kill_switch_active = False
        self.kill_switch_until = 0

    def set_client(self, client):
        """Attach runtime Binance client."""
        self.client = client

    def _extract_quote_asset(self, pair="") -> str:
        """Extract quote asset from symbol, fallback to USDT."""
        if pair and "/" in pair:
            return pair.split("/")[-1].upper()
        return "USDT"

    def _get_free_balance(self, asset="USDT", force=False):
        """Get free balance for specific asset with short TTL caching."""
        asset = str(asset or "USDT").upper()
        now = time.time()
        if (
            not force
            and self._last_balance_check > 0
            and (now - self._last_balance_check) < self._balance_ttl
        ):
            return float(self._cached_balances.get(asset, 0.0))

        if not self.client:
            from binance_client import BinanceClient
            self.client = BinanceClient()

        balances = self.client.fetch_balance() if self.client else {}
        fresh_cache = {}
        for symbol, data in (balances or {}).items():
            if isinstance(data, dict) and 'free' in data:
                fresh_cache[str(symbol).upper()] = max(
                    0.0,
                    float(data.get("free", 0.0) or 0.0)
                )

        self._cached_balances = fresh_cache
        self._last_balance_check = now
        return float(self._cached_balances.get(asset, 0.0))

    def can_open_trade(self, pair="") -> dict:
        """Check whether opening a new trade is currently allowed."""
        # 1) Global Kill Switch
        if self.kill_switch_active:
            if time.time() < self.kill_switch_until:
                return {"allowed": False, "reason": "KILL SWITCH ACTIVE"}
            self.kill_switch_active = False
            logger.info("Kill Switch period ended. Trading resumed.")

        # 2) Daily halt
        if self.auto_halt:
            return {"allowed": False, "reason": f"Auto halt: {self.halt_reason}"}

        # 3) Max open trades
        if self.open_trade_count >= Config.MAX_OPEN_TRADES:
            return {"allowed": False, "reason": f"Max open trades: {Config.MAX_OPEN_TRADES}"}

        # 4) Daily loss limit
        if self.starting_balance > 0:
            loss_pct = abs(self.daily_pnl) / self.starting_balance
            if self.daily_pnl < 0 and loss_pct >= Config.DAILY_LOSS_LIMIT:
                self.auto_halt = True
                self.halt_reason = f"Daily loss limit reached ({loss_pct:.1%})"
                return {"allowed": False, "reason": self.halt_reason}

        return {"allowed": True, "reason": ""}

    def calculate_position_size(self, price, pair="") -> dict:
        """Base position sizing from risk-per-trade and stop distance."""
        try:
            quote_asset = self._extract_quote_asset(pair)
            balance = self._get_free_balance(quote_asset, force=True)
            if balance <= 0 or price <= 0:
                return {
                    "amount": 0,
                    "stop_loss": 0,
                    "take_profit": 0,
                    "reason": f"No {quote_asset} balance or invalid price",
                }

            if quote_asset == "USDT":
                self.starting_balance = max(self.starting_balance, balance)

            risk_amount = balance * Config.RISK_PER_TRADE
            stop_loss_price = price * (1 - Config.STOP_LOSS_PCT)
            risk_per_unit = price - stop_loss_price

            if risk_per_unit <= 0:
                return {
                    "amount": 0,
                    "stop_loss": 0,
                    "take_profit": 0,
                    "reason": "Invalid stop-loss distance",
                }

            amount = risk_amount / risk_per_unit
            take_profit_price = price * (1 + Config.TAKE_PROFIT_MAX)

            return {
                "amount": amount,
                "stop_loss": stop_loss_price,
                "take_profit": take_profit_price,
                "risk_amount": risk_amount,
                "balance": balance,
                "quote_asset": quote_asset,
            }

        except Exception as e:
            logger.error(f"Position size error: {e}")
            return {"amount": 0, "stop_loss": 0, "take_profit": 0, "reason": str(e)}

    def calculate_dynamic_position(self, price, ai_score=60, pair="") -> dict:
        """AI-weighted sizing with capital cap, leverage, and min notional checks."""
        position = self.calculate_position_size(price, pair=pair)
        if position.get("amount", 0) <= 0:
            return position

        if ai_score >= 80:
            multiplier = 1.15
        elif ai_score >= 70:
            multiplier = 1.0
        elif ai_score >= 60:
            multiplier = 0.85
        else:
            multiplier = 0.7

        quote_asset = position.get("quote_asset", self._extract_quote_asset(pair))
        balance = float(
            position.get("balance", 0) or self._get_free_balance(quote_asset)
        )
        if balance <= 0:
            position["amount"] = 0
            position["reason"] = f"No {quote_asset} balance"
            return position

        desired_cost = position["amount"] * price * multiplier
        max_cost = balance * float(getattr(Config, "MAX_CAPITAL_PER_TRADE", 0.15))
        final_cost = min(desired_cost, max_cost)

        # في وضع الفيوتشرز: الرافعة تضاعف القوة الشرائية
        leverage = 1
        if getattr(Config, "ENABLE_FUTURES", False):
            leverage = max(1, int(getattr(Config, "FUTURES_LEVERAGE", 5)))
            # final_cost هو الهامش الفعلي، الرافعة تضاعف حجم المركز
            final_cost_with_leverage = final_cost * leverage
        else:
            final_cost_with_leverage = final_cost

        # Keep strict floor for USDT
        if quote_asset == "USDT":
            min_notional = float(getattr(Config, "MIN_TRADE_NOTIONAL", 5.0))
            if final_cost_with_leverage < min_notional:
                position["amount"] = 0
                position["reason"] = (
                    f"Notional too small ({final_cost_with_leverage:.2f} < {min_notional:.2f})"
                )
                return position

        position["amount"] = final_cost_with_leverage / price
        position["estimated_cost"] = final_cost  # الهامش الفعلي المقتطع
        position["leveraged_cost"] = final_cost_with_leverage
        position["ai_multiplier"] = multiplier
        position["quote_asset"] = quote_asset
        position["leverage"] = leverage

        logger.info(
            f"Dynamic size: AI={ai_score:.0f} x{multiplier:.2f} | "
            f"margin={final_cost:.2f} | lev={leverage}x | "
            f"amount={position['amount']:.6f} ({quote_asset})"
        )
        return position

    def update_pnl(self, pnl):
        """Update daily PnL."""
        self.daily_pnl += pnl
        logger.info(f"Daily PnL: {self.daily_pnl:+.2f}")

    def reset_daily(self):
        """Reset daily limits and state."""
        self.daily_pnl = 0
        self.auto_halt = False
        self.halt_reason = ""
        logger.info("Daily risk state reset")

    def update_trade_count(self, count):
        """Update current count of open trades."""
        self.open_trade_count = count

    def check_global_crash(self, btc_current_price, btc_recent_open):
        """Trigger kill switch if BTC drops sharply in a single candle."""
        if self.kill_switch_active:
            return True

        if btc_recent_open <= 0:
            return False

        drop_pct = (btc_current_price - btc_recent_open) / btc_recent_open
        if drop_pct <= -0.03:
            logger.critical(f"GLOBAL KILL SWITCH TRIGGERED: BTC drop {drop_pct:.2%}")
            self.kill_switch_active = True
            self.kill_switch_until = time.time() + (4 * 3600)
            return True

        return False

    def get_status(self):
        """Risk manager status for UI/Telegram."""
        return {
            "daily_pnl": self.daily_pnl,
            "open_trades": self.open_trade_count,
            "max_trades": Config.MAX_OPEN_TRADES,
            "auto_halt": self.auto_halt,
            "halt_reason": self.halt_reason,
            "risk_per_trade": Config.RISK_PER_TRADE,
            "daily_loss_limit": Config.DAILY_LOSS_LIMIT,
        }

    def force_halt(self, reason):
        """Force trading halt."""
        self.auto_halt = True
        self.halt_reason = reason
        logger.warning(f"Trading force-halted: {reason}")

    def resume(self):
        """Resume trading after halt."""
        self.auto_halt = False
        self.halt_reason = ""
        self.kill_switch_active = False
        logger.info("Trading resumed")
