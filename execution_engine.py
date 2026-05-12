"""
===================================================================
  execution_engine.py - Advanced Execution Engine v2.0
===================================================================
"""

import math
import time
import logging
from config import Config

logger = logging.getLogger("TradingBot.Exec")


class ExecutionEngine:
    """Execution engine with trailing SL and partial TP support."""

    def __init__(self, client, db, risk_manager, alerts=None):
        self.client = client
        self.db = db
        self.risk = risk_manager
        self.alerts = alerts
        self.open_trades = {}       # {pair: trade_data}
        self.last_order_time = {}   # anti-duplicate
        self.trade_counter = 0
        self._server_orders = {}    # {pair: [order_ids]} for server SL/TP

        if hasattr(self.risk, "set_client"):
            self.risk.set_client(self.client)

    def _normalize_order_amount(self, pair: str, amount: float, price: float) -> tuple[float, str]:
        """Normalize amount based on Binance limits to avoid order rejection."""
        amount = float(amount or 0.0)
        price = float(price or 0.0)
        if amount <= 0 or price <= 0:
            return 0.0, "invalid amount/price"

        limits = {}
        if hasattr(self.client, "get_market_limits"):
            limits = self.client.get_market_limits(pair) or {}

        min_amount = float(limits.get("min_amount", 0.0) or self.client.get_min_amount(pair))
        quote_asset = pair.split("/")[-1].upper() if "/" in pair else "USDT"
        fallback_min_notional = (
            float(getattr(Config, "MIN_TRADE_NOTIONAL", 5.0))
            if quote_asset == "USDT"
            else 0.0
        )
        min_notional = float(
            limits.get("min_notional", 0.0)
            or limits.get("min_cost", 0.0)
            or fallback_min_notional
        )
        step_size = float(limits.get("step_size", 0.0) or 0.0)

        if step_size > 0:
            amount = math.floor(amount / step_size) * step_size

        if min_amount > 0 and amount < min_amount:
            return 0.0, f"amount below min ({amount:.8f} < {min_amount:.8f})"

        notional = amount * price
        if min_notional > 0 and notional < min_notional:
            return 0.0, f"notional below min ({notional:.2f} < {min_notional:.2f})"

        return amount, ""

    def _ensure_trade_defaults(self, trade: dict):
        """Backfill missing runtime fields for restored/incomplete trades."""
        entry = float(trade.get("entry_price", 0) or 0)
        amount = float(trade.get("amount", 0) or 0)
        pos_side = trade.get("position_side", "LONG")
        if entry <= 0:
            return

        if trade.get("stop_loss") is None:
            trade["stop_loss"] = (
                entry * (1 - Config.STOP_LOSS_PCT)
                if pos_side == "LONG"
                else entry * (1 + Config.STOP_LOSS_PCT)
            )

        tp_min = Config.TAKE_PROFIT_MIN
        tp_max = Config.TAKE_PROFIT_MAX
        tp_mid = (tp_min + tp_max) / 2
        trade.setdefault(
            "take_profit_1",
            entry * (1 + tp_min) if pos_side == "LONG" else entry * (1 - tp_min),
        )
        trade.setdefault(
            "take_profit_2",
            entry * (1 + tp_mid) if pos_side == "LONG" else entry * (1 - tp_mid),
        )
        trade.setdefault(
            "take_profit_3",
            entry * (1 + tp_max) if pos_side == "LONG" else entry * (1 - tp_max),
        )

        trade.setdefault("remaining_amount", amount)
        trade.setdefault("tp_stage", 0)
        trade.setdefault("trailing_active", False)
        trade.setdefault("trailing_distance", 0.0025)

        if pos_side == "LONG":
            trade.setdefault("trailing_high", entry)
        else:
            trade.setdefault("trailing_low", entry)

        be_pct = max(0.0035, Config.TAKE_PROFIT_MIN * 0.6)
        trade.setdefault(
            "break_even_level",
            entry * (1 + be_pct) if pos_side == "LONG" else entry * (1 - be_pct),
        )

    def _resolve_pair_key(self, pair: str):
        """Resolve symbol key from open_trades using normalized matching."""
        clean_pair = pair.replace("/", "").upper()
        for p in self.open_trades.keys():
            if p.replace("/", "").upper() == clean_pair:
                return p
        return None

    def _get_free_asset_balance(self, asset: str) -> float:
        """Read free spot balance for an asset symbol."""
        asset = str(asset or "").upper()
        if not asset:
            return 0.0
        try:
            balances = self.client.fetch_balance() or {}
            data = balances.get(asset, {}) or {}
            return float(data.get("free", 0.0) or 0.0)
        except Exception as e:
            logger.error(f"Balance read error for {asset}: {e}")
            return 0.0

    def _extract_filled_amount(self, order: dict, fallback: float = 0.0) -> float:
        """Read filled base quantity from order payload."""
        if not order:
            return float(fallback or 0.0)
        try:
            filled = float(order.get("filled") or order.get("amount") or fallback or 0.0)
            return max(0.0, filled)
        except Exception:
            return float(fallback or 0.0)

    def _extract_base_fee(self, order: dict, base_asset: str) -> float:
        """Read paid fee in base asset (if any)."""
        base_asset = str(base_asset or "").upper()
        if not order or not base_asset:
            return 0.0

        fee_total = 0.0
        try:
            fee = order.get("fee")
            if fee and str(fee.get("currency", "")).upper() == base_asset:
                fee_total += float(fee.get("cost") or 0.0)
        except Exception:
            pass

        try:
            fees = order.get("fees") or []
            for fee_item in fees:
                if str(fee_item.get("currency", "")).upper() == base_asset:
                    fee_total += float(fee_item.get("cost") or 0.0)
        except Exception:
            pass

        return max(0.0, fee_total)

    def _resolve_open_amount_from_order(self, pair: str, requested_amount: float, side: str, order: dict) -> float:
        """Resolve actual tracked amount after order fill/fees."""
        actual_amount = self._extract_filled_amount(order, requested_amount)
        if actual_amount <= 0:
            return float(requested_amount or 0.0)

        # In spot BUY, fee can be deducted from base asset and cause insufficient
        # balance on later SELL if we track requested amount.
        if (
            side == "BUY"
            and not getattr(Config, "ENABLE_FUTURES", False)
            and "/" in pair
        ):
            base_asset = pair.split("/")[0].upper()
            base_fee = self._extract_base_fee(order, base_asset)
            if base_fee > 0:
                actual_amount = max(0.0, actual_amount - base_fee)

        return actual_amount if actual_amount > 0 else float(requested_amount or 0.0)

    def _prepare_close_amount(self, pair: str, desired_amount: float, position_side: str) -> tuple[float, float, str]:
        """Prepare a safe close amount that respects precision, limits, and spot balance."""
        desired_amount = float(desired_amount or 0.0)
        if desired_amount <= 0:
            return 0.0, 0.0, "remaining amount is zero"

        ticker = self.client.fetch_ticker(pair)
        current_price = float(ticker["last"]) if ticker and ticker.get("last") else 0.0
        if current_price <= 0:
            return 0.0, 0.0, "invalid close price"

        close_amount = desired_amount

        # Spot LONG close (SELL): clamp by free base balance to avoid insufficient funds.
        if (
            position_side == "LONG"
            and not getattr(Config, "ENABLE_FUTURES", False)
            and "/" in pair
        ):
            base_asset = pair.split("/")[0].upper()
            free_base = self._get_free_asset_balance(base_asset)
            if free_base <= 0:
                return 0.0, current_price, f"no free {base_asset} balance"
            close_amount = min(close_amount, free_base * 0.9995)

        close_amount, close_reason = self._normalize_order_amount(pair, close_amount, current_price)
        if close_amount <= 0:
            return 0.0, current_price, close_reason

        return close_amount, current_price, ""

    def _market_is_tradable(self, symbol: str) -> bool:
        """Check if symbol exists and is active on exchange."""
        try:
            if not hasattr(self.client, "exchange"):
                return False
            markets = self.client.exchange.load_markets()
            market = (markets or {}).get(symbol)
            if not market:
                return False
            return bool(market.get("active", True))
        except Exception:
            return False

    def _auto_convert_asset_to_usdt(self, asset: str, preferred_amount: float = 0.0) -> dict:
        """Convert asset balance to USDT after trade close (spot only)."""
        if not getattr(Config, "AUTO_CONVERT_PROCEEDS_TO_USDT", False):
            return {"success": False, "reason": "disabled"}
        if getattr(Config, "ENABLE_FUTURES", False):
            return {"success": False, "reason": "futures mode"}

        asset = str(asset or "").upper().strip()
        if not asset or asset == "USDT":
            return {"success": False, "reason": "no conversion needed"}
        if asset.startswith("LD"):
            return {"success": False, "reason": "earn asset"}

        symbol = f"{asset}/USDT"
        if not self._market_is_tradable(symbol):
            return {"success": False, "reason": f"market unavailable: {symbol}"}

        free_asset = self._get_free_asset_balance(asset)
        if free_asset <= 0:
            return {"success": False, "reason": f"no free {asset}"}

        amount = free_asset
        if preferred_amount and preferred_amount > 0:
            amount = min(amount, float(preferred_amount))

        buffer_ratio = float(getattr(Config, "AUTO_CONVERT_BUFFER_RATIO", 0.995) or 0.995)
        buffer_ratio = min(1.0, max(0.5, buffer_ratio))
        amount *= buffer_ratio

        ticker = self.client.fetch_ticker(symbol)
        if not ticker:
            return {"success": False, "reason": f"ticker unavailable: {symbol}"}
        price = float(ticker.get("last") or 0.0)
        if price <= 0:
            return {"success": False, "reason": "invalid conversion price"}

        min_usdt_value = float(getattr(Config, "AUTO_CONVERT_MIN_USDT_VALUE", 5.0) or 5.0)
        if amount * price < min_usdt_value:
            return {
                "success": False,
                "reason": f"value below convert minimum ({amount * price:.2f} < {min_usdt_value:.2f})",
            }

        amount, amount_reason = self._normalize_order_amount(symbol, amount, price)
        if amount <= 0:
            return {"success": False, "reason": amount_reason}

        order = self.client.create_market_order(symbol, "SELL", amount)
        if not order:
            return {"success": False, "reason": "conversion market order failed"}

        logger.info(f"Auto-convert to USDT: sold {amount:.8f} {asset} via {symbol}")
        return {"success": True, "symbol": symbol, "amount": amount}

    def _auto_convert_trade_proceeds(self, pair: str, position_side: str, closed_amount: float, exit_price: float):
        """Convert non-USDT proceeds from closed trade to USDT automatically."""
        if not getattr(Config, "AUTO_CONVERT_PROCEEDS_TO_USDT", False):
            return
        if "/" not in pair:
            return

        base_asset, quote_asset = pair.split("/")
        base_asset = base_asset.upper()
        quote_asset = quote_asset.upper()

        targets = []
        if position_side == "LONG":
            if quote_asset != "USDT":
                estimated_quote = max(0.0, float(closed_amount or 0.0) * float(exit_price or 0.0))
                targets.append((quote_asset, estimated_quote))
        else:
            # For short-style spot flow, position settles back to base asset.
            if base_asset != "USDT":
                targets.append((base_asset, float(closed_amount or 0.0)))

        for asset, pref_amount in targets:
            result = self._auto_convert_asset_to_usdt(asset, pref_amount)
            if result.get("success"):
                continue
            logger.info(
                f"Auto-convert skipped for {asset}: {result.get('reason', 'unknown reason')}"
            )

    def _reached_min_profit(self, trade: dict, current_price: float) -> bool:
        """Check fast-exit mode: close the whole trade at minimal profit.
        ✅ يخصم العمولة قبل المقارنة لتجنب البيع بربح وهمي.
        """
        if not getattr(Config, "CLOSE_ON_MIN_PROFIT", False):
            return False

        # Allow per-trade override for fast pump opportunities.
        min_profit_pct = float(
            trade.get("quick_exit_pct")
            or getattr(Config, "MIN_PROFIT_CLOSE_PCT", 0.0)
            or 0.0
        )
        if min_profit_pct <= 0:
            return False

        entry_price = float(trade.get("entry_price", 0.0) or 0.0)
        if entry_price <= 0:
            return False

        position_side = trade.get("position_side", "LONG")
        if position_side == "LONG":
            pnl_ratio = (current_price - entry_price) / entry_price
        else:
            pnl_ratio = (entry_price - current_price) / entry_price

        # ✅ خصم العمولة من الربح الفعلي قبل القرار
        fee_pct = getattr(Config, "EXCHANGE_FEE_PCT", 0.002)
        net_pnl = pnl_ratio - fee_pct

        return net_pnl >= min_profit_pct

    def _pnl_ratio(self, trade: dict, current_price: float) -> float:
        """Return signed pnl ratio (e.g. -0.01 = -1%)."""
        entry_price = float(trade.get("entry_price", 0.0) or 0.0)
        if entry_price <= 0 or current_price <= 0:
            return 0.0

        position_side = trade.get("position_side", "LONG")
        if position_side == "LONG":
            return (current_price - entry_price) / entry_price
        return (entry_price - current_price) / entry_price

    def _is_high_risk_loss(self, trade: dict, current_price: float) -> bool:
        """True when current loss reaches configured high-risk threshold."""
        pnl_ratio = self._pnl_ratio(trade, current_price)
        if pnl_ratio >= 0:
            return False

        high_risk_pct = float(getattr(Config, "HIGH_RISK_LOSS_PCT", 0.03) or 0.03)
        return abs(pnl_ratio) >= high_risk_pct

    def _should_block_loss_exit(self, pair: str, trade: dict, reason: str, current_price: float) -> bool:
        """
        Block auto-exit on losses until high-risk threshold is reached.
        Manual and kill-switch exits are always allowed.
        """
        if not getattr(Config, "EXIT_LOSS_ONLY_ON_HIGH_RISK", False):
            return False

        allowed_loss_reasons = {
            "MANUAL",
            "MANUAL_CLOSE",
            "GLOBAL_KILL_SWITCH",
            "BTC_FLASH_CRASH",
            "HIGH_RISK_STOP",
        }
        if reason in allowed_loss_reasons:
            return False

        pnl_ratio = self._pnl_ratio(trade, current_price)
        if pnl_ratio >= 0:
            return False

        if self._is_high_risk_loss(trade, current_price):
            return False

        high_risk_pct = float(getattr(Config, "HIGH_RISK_LOSS_PCT", 0.03) or 0.03)
        logger.info(
            f"{pair}: holding losing trade ({pnl_ratio:.2%}); "
            f"skip auto-close ({reason}) until high-risk >= {high_risk_pct:.2%}"
        )
        return True

    # ---------------------------------------------------------------
    # Public execution entry
    # ---------------------------------------------------------------
    def execute_trade(self, signal: dict, pair: str) -> dict:
        """Execute BUY/SELL signal."""
        try:
            action = signal.get("signal")
            if action not in ("BUY", "SELL"):
                return {"success": False, "reason": "invalid signal"}

            cooldown = Config.ORDER_COOLDOWN
            if pair in self.last_order_time:
                elapsed = time.time() - self.last_order_time[pair]
                if elapsed < cooldown:
                    return {"success": False, "reason": f"cooldown {int(cooldown - elapsed)}s"}

            if action == "BUY":
                if pair in self.open_trades:
                    trade = self.open_trades[pair]
                    if trade.get("position_side", "LONG") == "SHORT":
                        current_price = float(signal.get("price") or 0.0)
                        if current_price <= 0:
                            ticker = self.client.fetch_ticker(pair)
                            current_price = float(ticker["last"]) if ticker else float(trade.get("entry_price", 0.0) or 0.0)
                        if self._should_block_loss_exit(pair, trade, "SIGNAL_BUY", current_price):
                            return {"success": False, "reason": "holding losing trade (risk not high yet)"}
                        return self._close_trade(pair, trade, "SIGNAL_BUY")
                    return {"success": False, "reason": "LONG already open"}
                return self._execute_long(signal, pair)

            if pair in self.open_trades:
                trade = self.open_trades[pair]
                if trade.get("position_side", "LONG") == "LONG":
                    current_price = float(signal.get("price") or 0.0)
                    if current_price <= 0:
                        ticker = self.client.fetch_ticker(pair)
                        current_price = float(ticker["last"]) if ticker else float(trade.get("entry_price", 0.0) or 0.0)
                    if self._should_block_loss_exit(pair, trade, "SIGNAL_SELL", current_price):
                        return {"success": False, "reason": "holding losing trade (risk not high yet)"}
                    return self._close_trade(pair, trade, "SIGNAL_SELL")
                return {"success": False, "reason": "SHORT already open"}

            if getattr(Config, "ENABLE_FUTURES", False):
                return self._execute_short(signal, pair)
            if getattr(Config, "SPOT_INVENTORY_SELL_ENABLED", False):
                return self._execute_spot_inventory_sell(signal, pair)
            return {"success": False, "reason": "Futures disabled (spot mode)"}

        except Exception as e:
            logger.error(f"Execution error: {e}")
            self.db.log_error("EXECUTION", str(e), pair)
            return {"success": False, "reason": str(e)}

    # ---------------------------------------------------------------
    # Open Long
    # ---------------------------------------------------------------
    def _execute_long(self, signal: dict, pair: str) -> dict:
        risk_check = self.risk.can_open_trade(pair)
        if not risk_check["allowed"]:
            return {"success": False, "reason": risk_check["reason"]}

        price = signal.get("price", 0)
        if price <= 0:
            ticker = self.client.fetch_ticker(pair)
            price = ticker["last"] if ticker else 0
        if price <= 0:
            return {"success": False, "reason": "invalid price"}

        ai_score = signal.get("ai_score", 60)
        position = self.risk.calculate_dynamic_position(price, ai_score, pair=pair)
        if position.get("amount", 0) <= 0:
            return {"success": False, "reason": position.get("reason", "invalid position size")}

        amount, amount_reason = self._normalize_order_amount(pair, position["amount"], price)
        if amount <= 0:
            return {"success": False, "reason": amount_reason}

        order = self.client.create_market_order(pair, "BUY", amount)
        if not order:
            return {"success": False, "reason": "market order failed"}

        entry_price = float(order.get("average") or price)
        actual_amount = self._resolve_open_amount_from_order(pair, amount, "BUY", order)
        if actual_amount <= 0:
            return {"success": False, "reason": "filled amount is zero"}
        quick_exit_pct = float(signal.get("quick_exit_pct", 0.0) or 0.0)
        tp_mid = (Config.TAKE_PROFIT_MIN + Config.TAKE_PROFIT_MAX) / 2
        # ✅ Break-even يتفعل بعد تغطية العمولة + هامش أمان
        fee_pct = getattr(Config, "EXCHANGE_FEE_PCT", 0.002)
        break_even_pct = max(fee_pct * 2.5, Config.TAKE_PROFIT_MIN * 0.5)  # ~0.5%

        trade = {
            "pair": pair,
            "side": "BUY",
            "position_side": "LONG",
            "entry_price": entry_price,
            "amount": actual_amount,
            "stop_loss": float(position["stop_loss"]),
            "take_profit_1": entry_price * (1 + Config.TAKE_PROFIT_MIN),
            "take_profit_2": entry_price * (1 + tp_mid),
            "take_profit_3": entry_price * (1 + Config.TAKE_PROFIT_MAX),
            "break_even_level": entry_price * (1 + break_even_pct),
            "trailing_active": False,
            "trailing_distance": 0.0025,
            "trailing_high": entry_price,
            "tp_stage": 0,
            "remaining_amount": actual_amount,
            "ai_score": ai_score,
            "buy_score": signal.get("buy_score", 0),
            "regime": signal.get("regime", "UNKNOWN"),
            "quick_exit_pct": quick_exit_pct if quick_exit_pct > 0 else None,
            "time": time.time(),
            "order_id": order.get("id", ""),
        }

        self.open_trades[pair] = trade
        self.last_order_time[pair] = time.time()
        self.trade_counter += 1

        db_id = self.db.save_trade(
            {
                "symbol": pair,
                "side": "BUY",
                "entry_price": entry_price,
                "amount": actual_amount,
                "stop_loss": trade["stop_loss"],
                "take_profit": trade["take_profit_3"],
                "ai_score": ai_score,
                "status": "OPEN",
            }
        )
        trade["db_id"] = db_id
        trade["id"] = db_id

        if self.alerts:
            self.alerts.trade_opened(
                pair,
                "BUY",
                entry_price,
                actual_amount,
                trade["stop_loss"],
                trade["take_profit_3"],
            )

        logger.info(
            f"BUY {pair} | price={entry_price:.6f} | amount={actual_amount:.6f} | "
            f"SL={trade['stop_loss']:.6f} | TP1={trade['take_profit_1']:.6f}"
        )

        # أوامر سيرفرية للحماية (Futures فقط)
        self._place_server_sl_tp(pair, trade)

        return {"success": True, "trade": trade, "price": entry_price, "quantity": actual_amount}

    # ---------------------------------------------------------------
    # Open Short (futures only)
    # ---------------------------------------------------------------
    def _execute_short(self, signal: dict, pair: str) -> dict:
        risk_check = self.risk.can_open_trade(pair)
        if not risk_check["allowed"]:
            return {"success": False, "reason": risk_check["reason"]}

        price = signal.get("price", 0)
        if price <= 0:
            ticker = self.client.fetch_ticker(pair)
            price = ticker["last"] if ticker else 0
        if price <= 0:
            return {"success": False, "reason": "invalid price"}

        ai_score = signal.get("ai_score", 60)
        position = self.risk.calculate_dynamic_position(price, ai_score, pair=pair)
        if position.get("amount", 0) <= 0:
            return {"success": False, "reason": position.get("reason", "invalid position size")}

        amount, amount_reason = self._normalize_order_amount(pair, position["amount"], price)
        if amount <= 0:
            return {"success": False, "reason": amount_reason}

        order = self.client.create_market_order(pair, "SELL", amount)
        if not order:
            return {"success": False, "reason": "market order failed"}

        entry_price = float(order.get("average") or price)
        actual_amount = self._resolve_open_amount_from_order(pair, amount, "SELL", order)
        if actual_amount <= 0:
            return {"success": False, "reason": "filled amount is zero"}
        quick_exit_pct = float(signal.get("quick_exit_pct", 0.0) or 0.0)
        tp_mid = (Config.TAKE_PROFIT_MIN + Config.TAKE_PROFIT_MAX) / 2
        break_even_pct = max(0.0015, Config.TAKE_PROFIT_MIN * 0.5)

        trade = {
            "pair": pair,
            "side": "SELL",
            "position_side": "SHORT",
            "entry_price": entry_price,
            "amount": actual_amount,
            "stop_loss": entry_price * (1 + Config.STOP_LOSS_PCT),
            "take_profit_1": entry_price * (1 - Config.TAKE_PROFIT_MIN),
            "take_profit_2": entry_price * (1 - tp_mid),
            "take_profit_3": entry_price * (1 - Config.TAKE_PROFIT_MAX),
            "break_even_level": entry_price * (1 - break_even_pct),
            "trailing_active": False,
            "trailing_distance": 0.0025,
            "trailing_low": entry_price,
            "tp_stage": 0,
            "remaining_amount": actual_amount,
            "ai_score": ai_score,
            "buy_score": signal.get("buy_score", 0),
            "regime": signal.get("regime", "UNKNOWN"),
            "quick_exit_pct": quick_exit_pct if quick_exit_pct > 0 else None,
            "time": time.time(),
            "order_id": order.get("id", ""),
        }

        self.open_trades[pair] = trade
        self.last_order_time[pair] = time.time()
        self.trade_counter += 1

        db_id = self.db.save_trade(
            {
                "symbol": pair,
                "side": "SELL",
                "entry_price": entry_price,
                "amount": actual_amount,
                "stop_loss": trade["stop_loss"],
                "take_profit": trade["take_profit_3"],
                "ai_score": ai_score,
                "status": "OPEN",
            }
        )
        trade["db_id"] = db_id
        trade["id"] = db_id

        if self.alerts:
            self.alerts.trade_opened(
                pair,
                "SHORT",
                entry_price,
                actual_amount,
                trade["stop_loss"],
                trade["take_profit_3"],
            )

        logger.info(
            f"SHORT {pair} | price={entry_price:.6f} | amount={actual_amount:.6f} | "
            f"SL={trade['stop_loss']:.6f} | TP1={trade['take_profit_1']:.6f}"
        )

        # أوامر سيرفرية للحماية (Futures فقط)
        self._place_server_sl_tp(pair, trade)

        return {"success": True, "trade": trade, "price": entry_price, "quantity": actual_amount}

    # ---------------------------------------------------------------
    # Spot inventory sell (sell from existing base balance)
    # ---------------------------------------------------------------
    def _execute_spot_inventory_sell(self, signal: dict, pair: str) -> dict:
        risk_check = self.risk.can_open_trade(pair)
        if not risk_check["allowed"]:
            return {"success": False, "reason": risk_check["reason"]}

        if "/" not in pair:
            return {"success": False, "reason": "invalid pair format"}

        base_asset = pair.split("/")[0].upper()
        free_base = self._get_free_asset_balance(base_asset)
        if free_base <= 0:
            return {"success": False, "reason": f"no {base_asset} balance to sell"}

        sell_ratio = float(getattr(Config, "SPOT_INVENTORY_SELL_RATIO", 0.35) or 0.35)
        sell_ratio = max(0.01, min(1.0, sell_ratio))

        price = signal.get("price", 0)
        if price <= 0:
            ticker = self.client.fetch_ticker(pair)
            price = ticker["last"] if ticker else 0
        if price <= 0:
            return {"success": False, "reason": "invalid price"}

        requested_amount = free_base * sell_ratio
        amount, amount_reason = self._normalize_order_amount(pair, requested_amount, price)
        if amount <= 0:
            return {"success": False, "reason": amount_reason}

        order = self.client.create_market_order(pair, "SELL", amount)
        if not order:
            return {"success": False, "reason": "market order failed"}

        entry_price = float(order.get("average") or price)
        actual_amount = self._resolve_open_amount_from_order(pair, amount, "SELL", order)
        if actual_amount <= 0:
            return {"success": False, "reason": "filled amount is zero"}
        quick_exit_pct = float(signal.get("quick_exit_pct", 0.0) or 0.0)
        tp_mid = (Config.TAKE_PROFIT_MIN + Config.TAKE_PROFIT_MAX) / 2
        break_even_pct = max(0.0035, Config.TAKE_PROFIT_MIN * 0.6)

        trade = {
            "pair": pair,
            "side": "SELL",
            "position_side": "SHORT",
            "entry_price": entry_price,
            "amount": actual_amount,
            "stop_loss": entry_price * (1 + Config.STOP_LOSS_PCT),
            "take_profit_1": entry_price * (1 - Config.TAKE_PROFIT_MIN),
            "take_profit_2": entry_price * (1 - tp_mid),
            "take_profit_3": entry_price * (1 - Config.TAKE_PROFIT_MAX),
            "break_even_level": entry_price * (1 - break_even_pct),
            "trailing_active": False,
            "trailing_distance": 0.0025,
            "trailing_low": entry_price,
            "tp_stage": 0,
            "remaining_amount": actual_amount,
            "ai_score": signal.get("ai_score", 60),
            "buy_score": signal.get("buy_score", 0),
            "regime": signal.get("regime", "UNKNOWN"),
            "quick_exit_pct": quick_exit_pct if quick_exit_pct > 0 else None,
            "time": time.time(),
            "order_id": order.get("id", ""),
            "spot_inventory_mode": True,
        }

        self.open_trades[pair] = trade
        self.last_order_time[pair] = time.time()
        self.trade_counter += 1

        db_id = self.db.save_trade(
            {
                "symbol": pair,
                "side": "SELL",
                "entry_price": entry_price,
                "amount": actual_amount,
                "stop_loss": trade["stop_loss"],
                "take_profit": trade["take_profit_3"],
                "ai_score": trade["ai_score"],
                "status": "OPEN",
            }
        )
        trade["db_id"] = db_id
        trade["id"] = db_id

        if self.alerts:
            self.alerts.trade_opened(
                pair,
                "SPOT_SELL",
                entry_price,
                actual_amount,
                trade["stop_loss"],
                trade["take_profit_3"],
            )

        logger.info(
            f"SPOT-SELL {pair} | price={entry_price:.6f} | amount={actual_amount:.6f} | "
            f"SL={trade['stop_loss']:.6f} | TP1={trade['take_profit_1']:.6f}"
        )
        return {"success": True, "trade": trade, "price": entry_price, "quantity": actual_amount}

    # ---------------------------------------------------------------
    # Open trades monitoring
    # ---------------------------------------------------------------
    def check_open_trades(self):
        """Monitor open positions and manage trailing/partial TP."""
        pairs_to_close = []

        for pair, trade in list(self.open_trades.items()):
            try:
                self._ensure_trade_defaults(trade)

                ticker = self.client.fetch_ticker(pair)
                if not ticker:
                    continue

                current_price = float(ticker["last"])
                entry_price = float(trade["entry_price"])
                pos_side = trade.get("position_side", "LONG")

                if pos_side == "LONG":
                    pnl_ratio = self._pnl_ratio(trade, current_price)

                    # ✅ وقف خسارة حقيقي - يبيع فعلاً عند الخسارة
                    if current_price <= float(trade["stop_loss"]):
                        logger.warning(
                            f"⛔ {pair}: وقف خسارة! السعر {current_price:.6f} <= SL {float(trade['stop_loss']):.6f} | "
                            f"خسارة {pnl_ratio:.2%} - إغلاق فوري لحماية رأس المال!"
                        )
                        pairs_to_close.append((pair, trade, "STOP_LOSS"))
                        continue

                    if self._reached_min_profit(trade, current_price):
                        logger.info(f"{pair}: fast exit at minimal profit ({current_price:.6f})")
                        pairs_to_close.append((pair, trade, "MIN_PROFIT"))
                        continue

                    if (not trade["trailing_active"]) and current_price >= float(trade["break_even_level"]):
                        # ✅ نقل وقف الخسارة لنقطة الدخول + 0.05% = ربح مضمون
                        trade["stop_loss"] = entry_price * 1.001
                        trade["trailing_active"] = True
                        trade["trailing_high"] = current_price
                        logger.info(
                            f"🔒 {pair}: Break-Even! SL → {trade['stop_loss']:.6f} (ربح مضمون)"
                        )

                    # ✅ Trailing Stop ذكي: إذا ربح 1%+ → يتبع السعر بمسافة 0.5%
                    if trade["trailing_active"] and current_price > float(trade.get("trailing_high", entry_price)):
                        trade["trailing_high"] = current_price
                        # مسافة trailing ديناميكية: 0.5% أو trailing_distance أيهما أصغر
                        trail_dist = min(float(trade["trailing_distance"]), 0.005)
                        new_sl = current_price * (1 - trail_dist)
                        if new_sl > float(trade["stop_loss"]):
                            trade["stop_loss"] = new_sl

                    if trade["tp_stage"] == 0 and current_price >= float(trade["take_profit_1"]):
                        sell_amount = float(trade["remaining_amount"]) * 0.30
                        closed_amount = self._partial_close(pair, sell_amount, "TP1", pos_side)
                        if closed_amount > 0:
                            trade["remaining_amount"] = max(
                                0.0, float(trade["remaining_amount"]) - closed_amount
                            )
                            trade["tp_stage"] = 1
                    elif trade["tp_stage"] == 1 and current_price >= float(trade["take_profit_2"]):
                        sell_amount = float(trade["remaining_amount"]) * 0.43
                        closed_amount = self._partial_close(pair, sell_amount, "TP2", pos_side)
                        if closed_amount > 0:
                            trade["remaining_amount"] = max(
                                0.0, float(trade["remaining_amount"]) - closed_amount
                            )
                            trade["tp_stage"] = 2
                    elif trade["tp_stage"] == 2 and current_price >= float(trade["take_profit_3"]):
                        pairs_to_close.append((pair, trade, "TAKE_PROFIT_FULL"))

                else:  # SHORT
                    pnl_ratio = self._pnl_ratio(trade, current_price)

                    # ✅ وقف خسارة حقيقي للشورت
                    if current_price >= float(trade["stop_loss"]):
                        logger.warning(
                            f"⛔ {pair} (SHORT): وقف خسارة! السعر {current_price:.6f} >= SL {float(trade['stop_loss']):.6f} | "
                            f"خسارة {pnl_ratio:.2%}"
                        )
                        pairs_to_close.append((pair, trade, "STOP_LOSS"))
                        continue

                    if self._reached_min_profit(trade, current_price):
                        logger.info(f"{pair} (SHORT): fast exit at minimal profit ({current_price:.6f})")
                        pairs_to_close.append((pair, trade, "MIN_PROFIT"))
                        continue

                    if (not trade["trailing_active"]) and current_price <= float(trade["break_even_level"]):
                        # ✅ نقل وقف الخسارة لنقطة الدخول = ربح مضمون
                        trade["stop_loss"] = entry_price * 0.999
                        trade["trailing_active"] = True
                        trade["trailing_low"] = current_price
                        logger.info(
                            f"🔒 {pair} (SHORT): Break-Even! SL → {trade['stop_loss']:.6f}"
                        )

                    if trade["trailing_active"] and current_price < float(trade.get("trailing_low", entry_price)):
                        trade["trailing_low"] = current_price
                        trail_dist = min(float(trade["trailing_distance"]), 0.005)
                        new_sl = current_price * (1 + trail_dist)
                        if new_sl < float(trade["stop_loss"]):
                            trade["stop_loss"] = new_sl

                    if trade["tp_stage"] == 0 and current_price <= float(trade["take_profit_1"]):
                        buy_amount = float(trade["remaining_amount"]) * 0.30
                        closed_amount = self._partial_close(pair, buy_amount, "TP1", pos_side)
                        if closed_amount > 0:
                            trade["remaining_amount"] = max(
                                0.0, float(trade["remaining_amount"]) - closed_amount
                            )
                            trade["tp_stage"] = 1
                    elif trade["tp_stage"] == 1 and current_price <= float(trade["take_profit_2"]):
                        buy_amount = float(trade["remaining_amount"]) * 0.43
                        closed_amount = self._partial_close(pair, buy_amount, "TP2", pos_side)
                        if closed_amount > 0:
                            trade["remaining_amount"] = max(
                                0.0, float(trade["remaining_amount"]) - closed_amount
                            )
                            trade["tp_stage"] = 2
                    elif trade["tp_stage"] == 2 and current_price <= float(trade["take_profit_3"]):
                        pairs_to_close.append((pair, trade, "TAKE_PROFIT_FULL"))

            except Exception as e:
                logger.error(f"Open trade monitor error {pair}: {e}")

        for pair, trade, reason in pairs_to_close:
            self._close_trade(pair, trade, reason)

    def _place_server_sl_tp(self, pair, trade):
        """وضع أوامر وقف خسارة وجني أرباح سيرفرية على Binance بعد فتح الصفقة."""
        if not getattr(Config, "ENABLE_FUTURES", False):
            return
        if not hasattr(self.client, "create_futures_stop_order"):
            return

        pos_side = trade.get("position_side", "LONG")
        amount = float(trade.get("amount", 0) or 0)
        sl_price = float(trade.get("stop_loss", 0) or 0)
        tp_price = float(trade.get("take_profit_3", 0) or 0)
        if amount <= 0:
            return

        order_ids = []
        close_side = "SELL" if pos_side == "LONG" else "BUY"

        # Server-side Stop Loss
        if getattr(Config, "FUTURES_SERVER_SL", True) and sl_price > 0:
            sl_order = self.client.create_futures_stop_order(
                pair, close_side, amount, sl_price
            )
            if sl_order:
                order_ids.append(sl_order.get("id", ""))
                trade["server_sl_id"] = sl_order.get("id", "")

        # Server-side Take Profit
        if getattr(Config, "FUTURES_SERVER_TP", True) and tp_price > 0:
            tp_order = self.client.create_futures_tp_order(
                pair, close_side, amount, tp_price
            )
            if tp_order:
                order_ids.append(tp_order.get("id", ""))
                trade["server_tp_id"] = tp_order.get("id", "")

        if order_ids:
            self._server_orders[pair] = order_ids
            logger.info(f"✅ {pair}: تم وضع {len(order_ids)} أمر حماية سيرفري")

    def _cancel_server_orders(self, pair):
        """إلغاء أوامر الحماية السيرفرية عند الإغلاق اليدوي."""
        if not getattr(Config, "ENABLE_FUTURES", False):
            return
        if hasattr(self.client, "cancel_symbol_orders"):
            try:
                self.client.cancel_symbol_orders(pair)
            except Exception as e:
                logger.error(f"خطأ إلغاء أوامر سيرفرية {pair}: {e}")
        self._server_orders.pop(pair, None)

    def _partial_close(self, pair, amount, reason, position_side="LONG") -> float:
        """Close part of position and return actual closed amount."""
        try:
            if amount <= 0:
                return 0.0

            close_amount, current_price, close_reason = self._prepare_close_amount(
                pair, amount, position_side
            )
            if close_amount <= 0:
                logger.warning(f"Partial close skipped {pair}: {close_reason}")
                return 0.0

            side = "SELL" if position_side == "LONG" else "BUY"
            params = {"reduceOnly": True} if getattr(Config, "ENABLE_FUTURES", False) else {}
            order = self.client.create_market_order(pair, side, close_amount, params)
            if not order:
                logger.error(f"Partial close order failed {pair}: {reason}")
                return 0.0

            closed_amount = self._extract_filled_amount(order, close_amount)
            logger.info(
                f"Partial close {pair}: closed={closed_amount:.8f} @ {current_price:.6f} ({reason})"
            )
            return closed_amount
        except Exception as e:
            logger.error(f"Partial close error {pair}: {e}")
            return 0.0

    def _close_trade(self, pair, trade, reason):
        """Close full trade and persist PnL."""
        try:
            self._ensure_trade_defaults(trade)

            remaining = float(trade.get("remaining_amount", trade.get("amount", 0)) or 0)
            if remaining <= 0:
                return {"success": False, "reason": "remaining amount is zero"}

            pos_side = trade.get("position_side", "LONG")
            current_price = float(trade.get("entry_price", 0.0) or 0.0)
            try:
                ticker = self.client.fetch_ticker(pair)
                if ticker and ticker.get("last"):
                    current_price = float(ticker["last"])
            except Exception:
                pass

            if self._should_block_loss_exit(pair, trade, reason, current_price):
                return {"success": False, "reason": "loss exit blocked (risk not high)"}

            # إلغاء أوامر الحماية السيرفرية قبل الإغلاق
            self._cancel_server_orders(pair)

            side = "SELL" if pos_side == "LONG" else "BUY"
            params = {"reduceOnly": True} if getattr(Config, "ENABLE_FUTURES", False) else {}
            close_amount, market_price, close_reason = self._prepare_close_amount(
                pair, remaining, pos_side
            )
            if close_amount <= 0:
                if any(x in close_reason.lower() for x in ["no free", "remaining amount is zero", "dust"]):
                    logger.warning(f"⚠️ Forcing DB close for {pair} despite 0 balance (likely sold manually): {close_reason}")
                    order = {}
                else:
                    logger.error(f"Close skipped {pair}: {close_reason}")
                    return {"success": False, "reason": close_reason}
            else:
                order = self.client.create_market_order(pair, side, close_amount, params)
                if not order:
                    logger.error(f"Close order failed {pair} | reason={reason}")
                    return {"success": False, "reason": "market close order failed"}

            exit_price = float(order.get("average") or market_price or 0)
            closed_amount = self._extract_filled_amount(order, close_amount)
            if closed_amount <= 0:
                closed_amount = close_amount

            if exit_price == 0:
                ticker = self.client.fetch_ticker(pair)
                exit_price = float(ticker["last"]) if ticker else float(trade["entry_price"])

            entry_price = float(trade["entry_price"])
            base_amount = closed_amount

            if pos_side == "LONG":
                raw_pnl = (exit_price - entry_price) * base_amount
                raw_pnl_pct = (exit_price - entry_price) / entry_price * 100
            else:
                raw_pnl = (entry_price - exit_price) * base_amount
                raw_pnl_pct = (entry_price - exit_price) / entry_price * 100

            # ✅ خصم عمولة بينانس من الربح الحقيقي
            fee_pct = getattr(Config, "EXCHANGE_FEE_PCT", 0.002)
            fee_amount = entry_price * base_amount * fee_pct  # عمولة شراء + بيع
            pnl = raw_pnl - fee_amount
            pnl_pct = raw_pnl_pct - (fee_pct * 100)

            remaining_after = max(0.0, remaining - closed_amount)
            if remaining_after > 0:
                # If what remains is not tradable (dust), treat as fully closed.
                dust_amount, _, dust_reason = self._prepare_close_amount(
                    pair, remaining_after, pos_side
                )
                if dust_amount > 0:
                    trade["remaining_amount"] = remaining_after
                    logger.warning(
                        f"Close partial for {pair}: closed={closed_amount:.8f}, "
                        f"remaining={remaining_after:.8f}"
                    )
                    return {
                        "success": False,
                        "reason": "partial close",
                        "closed_amount": closed_amount,
                        "remaining_amount": remaining_after,
                    }
                logger.info(
                    f"{pair}: residual amount treated as dust after close "
                    f"({remaining_after:.8f}, {dust_reason})"
                )

            db_id = trade.get("db_id") or trade.get("id")
            if db_id:
                self.db.close_trade(db_id, exit_price, pnl, pnl_pct, reason)

            if hasattr(self.risk, "update_pnl"):
                self.risk.update_pnl(pnl)

            if self.alerts:
                self.alerts.trade_closed(
                    pair,
                    trade.get("side", "BUY"),
                    entry_price,
                    exit_price,
                    pnl,
                    pnl_pct,
                    reason,
                )

            emoji = "✅" if pnl >= 0 else "❌"
            logger.info(
                f"{emoji} Close {pair} | entry={entry_price:.6f} | exit={exit_price:.6f} | "
                f"PnL={pnl:+.4f} ({pnl_pct:+.2f}%) | reason={reason}"
            )

            try:
                self._auto_convert_trade_proceeds(pair, pos_side, closed_amount, exit_price)
            except Exception as convert_err:
                logger.error(f"Auto-convert error {pair}: {convert_err}")

            if pair in self.open_trades:
                del self.open_trades[pair]

            return {
                "success": True,
                "pnl": pnl,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "closed_amount": closed_amount,
                "closed": 1,
            }

        except Exception as e:
            logger.error(f"Close trade error {pair}: {e}")
            return {"success": False, "reason": str(e)}

    def close_all_trades(self, reason="GLOBAL_KILL_SWITCH"):
        """Emergency close all open trades."""
        pairs = list(self.open_trades.keys())
        if not pairs:
            return

        logger.warning(f"Emergency mode: closing {len(pairs)} open trades ({reason})")
        for pair in pairs:
            self._close_trade(pair, self.open_trades[pair], reason)
        logger.warning("All open trades have been closed")

    def force_close_trade(self, pair: str) -> dict:
        """Force close from Dashboard/Telegram by symbol."""
        try:
            match_pair = self._resolve_pair_key(pair)

            if not match_pair:
                db_trades = self.db.get_open_trades()
                clean_pair = pair.replace("/", "").upper()
                for db_t in db_trades:
                    if db_t["symbol"].replace("/", "").upper() == clean_pair:
                        entry = float(db_t.get("entry_price") or 0)
                        amount = float(db_t.get("quantity") or 0)
                        side = db_t.get("side", "BUY")
                        pos_side = "LONG" if side == "BUY" else "SHORT"

                        tp_min = Config.TAKE_PROFIT_MIN
                        tp_max = Config.TAKE_PROFIT_MAX
                        tp_mid = (tp_min + tp_max) / 2
                        be_pct = max(0.0035, tp_min * 0.6)

                        match_pair = db_t["symbol"]
                        self.open_trades[match_pair] = {
                            "pair": match_pair,
                            "side": side,
                            "position_side": pos_side,
                            "entry_price": entry,
                            "amount": amount,
                            "remaining_amount": amount,
                            "stop_loss": float(
                                db_t.get("stop_loss")
                                or (entry * (1 - Config.STOP_LOSS_PCT) if pos_side == "LONG" else entry * (1 + Config.STOP_LOSS_PCT))
                            ),
                            "take_profit_1": entry * (1 + tp_min) if pos_side == "LONG" else entry * (1 - tp_min),
                            "take_profit_2": entry * (1 + tp_mid) if pos_side == "LONG" else entry * (1 - tp_mid),
                            "take_profit_3": float(
                                db_t.get("take_profit")
                                or (entry * (1 + tp_max) if pos_side == "LONG" else entry * (1 - tp_max))
                            ),
                            "break_even_level": entry * (1 + be_pct) if pos_side == "LONG" else entry * (1 - be_pct),
                            "trailing_active": False,
                            "trailing_distance": 0.0025,
                            "trailing_high": entry,
                            "trailing_low": entry,
                            "tp_stage": 0,
                            "db_id": db_t["id"],
                            "id": db_t["id"],
                        }
                        break

            if not match_pair:
                return {"success": False, "reason": f"No open trade found for {pair}"}

            trade = self.open_trades[match_pair]
            logger.warning(f"Manual force close requested for {match_pair}")
            return self._close_trade(match_pair, trade, "MANUAL_CLOSE")

        except Exception as e:
            logger.error(f"Force close error {pair}: {e}")
            return {"success": False, "reason": str(e)}

    def restore_open_trades_from_db(self) -> int:
        """Restore in-memory open trades after process restart."""
        restored = 0
        try:
            db_trades = self.db.get_open_trades()
            if not db_trades:
                return 0

            for db_t in db_trades:
                pair = db_t.get("symbol")
                if not pair or pair in self.open_trades:
                    continue

                entry = float(db_t.get("entry_price") or 0)
                amount = float(db_t.get("quantity") or db_t.get("amount") or 0)
                if entry <= 0 or amount <= 0:
                    continue

                side = db_t.get("side", "BUY")
                pos_side = "LONG" if side == "BUY" else "SHORT"

                tp_min = Config.TAKE_PROFIT_MIN
                tp_max = Config.TAKE_PROFIT_MAX
                tp_mid = (tp_min + tp_max) / 2
                be_pct = max(0.0035, tp_min * 0.6)

                trade = {
                    "pair": pair,
                    "side": side,
                    "position_side": pos_side,
                    "entry_price": entry,
                    "amount": amount,
                    "remaining_amount": amount,
                    "stop_loss": float(
                        db_t.get("stop_loss")
                        or (
                            entry * (1 - Config.STOP_LOSS_PCT)
                            if pos_side == "LONG"
                            else entry * (1 + Config.STOP_LOSS_PCT)
                        )
                    ),
                    "take_profit_1": entry * (1 + tp_min) if pos_side == "LONG" else entry * (1 - tp_min),
                    "take_profit_2": entry * (1 + tp_mid) if pos_side == "LONG" else entry * (1 - tp_mid),
                    "take_profit_3": float(
                        db_t.get("take_profit")
                        or (
                            entry * (1 + tp_max)
                            if pos_side == "LONG"
                            else entry * (1 - tp_max)
                        )
                    ),
                    "break_even_level": entry * (1 + be_pct) if pos_side == "LONG" else entry * (1 - be_pct),
                    "trailing_active": False,
                    "trailing_distance": 0.0025,
                    "trailing_high": entry,
                    "trailing_low": entry,
                    "tp_stage": 0,
                    "ai_score": float(db_t.get("ai_score") or 60),
                    "regime": "RESTORED",
                    "db_id": db_t.get("id"),
                    "id": db_t.get("id"),
                    "time": time.time(),
                }

                self._ensure_trade_defaults(trade)
                self.open_trades[pair] = trade
                self.last_order_time[pair] = time.time()
                restored += 1

            if restored > 0:
                logger.info(f"Restored {restored} open trades from database")
            return restored
        except Exception as e:
            logger.error(f"Restore open trades error: {e}")
            return restored

    def manual_buy(self, pair, amount=None):
        """Manual BUY from Telegram."""
        try:
            ticker = self.client.fetch_ticker(pair)
            if not ticker:
                return {"success": False, "reason": "failed to fetch ticker"}

            price = float(ticker["last"])
            signal = {
                "signal": "BUY",
                "pair": pair,
                "price": price,
                "ai_score": 60,
                "buy_score": 70,
                "strength": 70,
                "regime": "MANUAL",
            }
            return self.execute_trade(signal, pair)

        except Exception as e:
            return {"success": False, "reason": str(e)}

    def manual_sell(self, pair):
        """Manual close from Telegram."""
        match_pair = self._resolve_pair_key(pair)
        if match_pair and match_pair in self.open_trades:
            return self._close_trade(match_pair, self.open_trades[match_pair], "MANUAL")
        return {"success": False, "reason": "no open trade found"}
