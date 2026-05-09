"""
===================================================================
  binance_client.py - عميل Binance عبر CCXT
  Binance Exchange Client via CCXT Library
===================================================================
"""

import logging
import ccxt
import time
from config import Config

logger = logging.getLogger("TradingBot.Binance")


class BinanceClient:
    """عميل Binance - جلب البيانات وتنفيذ الأوامر"""

    def __init__(self):
        # التبديل بين Spot و Futures
        exchange_class = ccxt.binanceusdm if getattr(Config, "ENABLE_FUTURES", False) else ccxt.binance
        default_type = "future" if getattr(Config, "ENABLE_FUTURES", False) else "spot"
        
        # ═══ اتصال عام (بدون API Key) لجلب البيانات - لا يحتاج IP Whitelist ═══
        public_class = ccxt.binanceusdm if getattr(Config, "ENABLE_FUTURES", False) else ccxt.binance
        self.public = public_class({
            "enableRateLimit": True,
            "options": {
                "defaultType": default_type,
                "adjustForTimeDifference": True
            }
        })
        
        # ═══ اتصال خاص (مع API Key) للتداول والرصيد فقط ═══
        self.exchange = exchange_class({
            "apiKey": Config.BINANCE_API_KEY,
            "secret": Config.BINANCE_API_SECRET,
            "sandbox": Config.BINANCE_SANDBOX,
            "enableRateLimit": True,
            "options": {
                "defaultType": default_type,
                "adjustForTimeDifference": True
            }
        })
        
        if Config.BINANCE_SANDBOX:
            self.exchange.set_sandbox_mode(True)
            self.public.set_sandbox_mode(True)
            logger.info("🧪 وضع الاختبار (Sandbox) مفعّل")
            
        if getattr(Config, "ENABLE_FUTURES", False):
            logger.info("⚡ تم الاتصال بصالة العقود الآجلة (Binance Futures)")
            self._setup_futures()
        else:
            logger.info("🔗 تم الاتصال بـ Binance بنجاح (Spot)")

    def _setup_futures(self):
        """تأمين حساب الـ Futures برافعة مالية ووضع معزول (Isolated)"""
        try:
            self.exchange.load_markets()
            margin_mode = getattr(Config, "FUTURES_MARGIN_MODE", "isolated")
            leverage = getattr(Config, "FUTURES_LEVERAGE", 5)
            for pair in Config.TRADING_PAIRS:
                try:
                    self.exchange.set_margin_mode(margin_mode, pair)
                except Exception as e:
                    if "No need to change" not in str(e):
                        logger.debug(f"⚠️ فشل تعيين العزل لـ {pair}: {e}")
                try:
                    self.exchange.set_leverage(leverage, pair)
                    logger.debug(f"⚙️ {pair}: رافعة {leverage}x ({margin_mode})")
                except Exception as e:
                    logger.debug(f"⚠️ فشل تعيين الرافعة لـ {pair}: {e}")
            logger.info(f"✅ تم تأمين العقود الآجلة ({margin_mode} / {leverage}x)")
        except Exception as e:
            logger.error(f"❌ خطأ ضخم في تهيئة العقود الآجلة: {e}")

    # ──────────────── Futures: Server-Side SL/TP ────────────────
    def create_futures_stop_order(self, symbol, side, amount, stop_price):
        """أمر وقف خسارة سيرفري على Binance Futures (STOP_MARKET)."""
        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type="STOP_MARKET",
                side=side.lower(),
                amount=amount,
                params={
                    "stopPrice": stop_price,
                    "reduceOnly": True,
                    "workingType": "MARK_PRICE",
                }
            )
            logger.info(f"🛡️ Server SL: {side} {amount} {symbol} @ stop={stop_price:.6f} | ID={order['id']}")
            return order
        except Exception as e:
            logger.error(f"❌ Server SL فشل {symbol}: {e}")
            return None

    def create_futures_tp_order(self, symbol, side, amount, tp_price):
        """أمر جني أرباح سيرفري على Binance Futures (TAKE_PROFIT_MARKET)."""
        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type="TAKE_PROFIT_MARKET",
                side=side.lower(),
                amount=amount,
                params={
                    "stopPrice": tp_price,
                    "reduceOnly": True,
                    "workingType": "MARK_PRICE",
                }
            )
            logger.info(f"🎯 Server TP: {side} {amount} {symbol} @ tp={tp_price:.6f} | ID={order['id']}")
            return order
        except Exception as e:
            logger.error(f"❌ Server TP فشل {symbol}: {e}")
            return None

    def cancel_symbol_orders(self, symbol):
        """إلغاء جميع الأوامر المعلقة لزوج محدد."""
        try:
            orders = self.exchange.fetch_open_orders(symbol)
            cancelled = 0
            for order in orders:
                try:
                    self.exchange.cancel_order(order['id'], symbol)
                    cancelled += 1
                except Exception:
                    pass
            if cancelled > 0:
                logger.info(f"🚫 تم إلغاء {cancelled} أمر معلق لـ {symbol}")
            return cancelled
        except Exception as e:
            logger.error(f"خطأ إلغاء أوامر {symbol}: {e}")
            return 0

    def get_futures_position(self, symbol):
        """جلب المركز المفتوح لزوج في الفيوتشرز."""
        try:
            positions = self.exchange.fetch_positions([symbol])
            for pos in positions:
                amt = abs(float(pos.get('contracts', 0) or 0))
                if amt > 0:
                    return pos
            return None
        except Exception as e:
            logger.error(f"خطأ جلب مركز {symbol}: {e}")
            return None

    def transfer_spot_to_futures(self, asset="USDT", amount=None):
        """تحويل رصيد من محفظة Spot إلى Futures."""
        try:
            if amount is None:
                bal = self.exchange.fetch_balance()
                amount = float(bal.get('free', {}).get(asset, 0) or 0)
            if amount <= 0:
                logger.info(f"لا يوجد {asset} للتحويل")
                return 0.0
            # Use CCXT universal transfer: spot -> usdm-future
            self.exchange.transfer(asset, amount, 'spot', 'future')
            logger.info(f"💱 تم تحويل {amount:.4f} {asset} من Spot إلى Futures")
            return amount
        except Exception as e:
            logger.error(f"❌ فشل تحويل {asset} Spot->Futures: {e}")
            return 0.0

    # ──────────────── جلب البيانات ────────────────
    def fetch_ohlcv(self, symbol=None, timeframe=None, limit=500):
        """جلب بيانات الشموع (OHLCV) - يستخدم اتصال عام بدون API Key"""
        symbol = symbol or Config.DEFAULT_PAIR
        timeframe = timeframe or Config.TIMEFRAME
        try:
            ohlcv = self.public.fetch_ohlcv(
                symbol, timeframe, limit=limit
            )
            logger.debug(f"📊 تم جلب {len(ohlcv)} شمعة لـ {symbol}")
            return ohlcv
        except ccxt.BaseError as e:
            logger.error(f"خطأ في جلب OHLCV: {e}")
            return []

    def fetch_ticker(self, symbol=None):
        """جلب السعر الحالي - يستخدم اتصال عام بدون API Key"""
        symbol = symbol or Config.DEFAULT_PAIR
        try:
            ticker = self.public.fetch_ticker(symbol)
            return ticker
        except ccxt.BaseError as e:
            logger.error(f"خطأ في جلب السعر: {e}")
            return None

    def fetch_current_price(self, symbol=None):
        """جلب السعر الحالي فقط"""
        ticker = self.fetch_ticker(symbol)
        return float(ticker["last"]) if ticker else None

    def fetch_order_book(self, symbol=None, limit=20):
        """جلب دفتر الأوامر - يستخدم اتصال عام بدون API Key"""
        symbol = symbol or Config.DEFAULT_PAIR
        try:
            order_book = self.public.fetch_order_book(symbol, limit)
            return order_book
        except ccxt.BaseError as e:
            logger.error(f"خطأ في جلب دفتر الأوامر: {e}")
            return None

    def fetch_balance(self):
        """جلب الرصيد"""
        try:
            balance = self.exchange.fetch_balance()
            # تصفية العملات ذات الرصيد > 0
            filtered = {}
            for currency, data in balance.get("total", {}).items():
                if data and float(data) > 0:
                    filtered[currency] = {
                        "total": float(balance["total"].get(currency, 0)),
                        "free": float(balance["free"].get(currency, 0)),
                        "used": float(balance["used"].get(currency, 0))
                    }
            return filtered
        except ccxt.BaseError as e:
            logger.error(f"خطأ في جلب الرصيد: {e}")
            return {}

    def get_usdt_balance(self):
        """جلب رصيد USDT الحر - مع تشخيص للـ IP"""
        try:
            balance = self.exchange.fetch_balance()
            return float(balance.get("free", {}).get("USDT", 0))
        except Exception as e:
            # استخراج الـ IP العام للتشخيص
            public_ip = "غير معروف"
            try:
                import urllib.request
                public_ip = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode("utf-8")
            except: pass
            
            logger.error(f"❌ فشل جلب الرصيد! الـ IP الخاص بالبوت هو: {public_ip}")
            logger.error(f"⚠️ سبب الرفض من بينانس: {e}")
            return 0.0

    # ──────────────── تنفيذ الأوامر ────────────────
    def get_balance_trading_pairs(
        self,
        quote_asset=None,
        quote_assets=None,
        min_total=None,
        max_pairs=None,
    ):
        """
        Build tradable pairs using quote assets that exist in wallet balance.
        Example output: BTC/BNB, ETH/LTC, LTC/USDT.
        """
        min_total = (
            Config.BALANCE_COIN_MIN_TOTAL
            if min_total is None
            else float(min_total)
        )
        max_pairs = (
            Config.MAX_BALANCE_SCAN_PAIRS
            if max_pairs is None
            else int(max_pairs)
        )

        try:
            balances = self.fetch_balance()
            if not balances:
                return []

            if quote_assets is None:
                if quote_asset:
                    quote_assets = [quote_asset]
                else:
                    quote_assets = getattr(Config, "BALANCE_QUOTE_ASSETS", None)
            if not quote_assets:
                quote_assets = [getattr(Config, "BALANCE_QUOTE_ASSET", "USDT")]

            normalized_quotes = []
            for q in quote_assets:
                q_clean = str(q).strip().upper()
                if q_clean and q_clean not in normalized_quotes:
                    normalized_quotes.append(q_clean)

            markets = self.exchange.load_markets()
            pairs = []

            active_quotes = []
            for quote in normalized_quotes:
                quote_total = float(balances.get(quote, {}).get("total", 0.0) or 0.0)
                if quote_total > min_total:
                    active_quotes.append(quote)
            if not active_quotes:
                return []

            # Base asset universe:
            # 1) Existing configured base symbols, 2) wallet-held assets.
            base_assets = set()
            for pair in getattr(Config, "TRADING_PAIRS", []):
                if "/" in pair:
                    base_assets.add(pair.split("/")[0].upper())
            for asset in balances.keys():
                base_assets.add(str(asset).upper())

            for base_asset in sorted(base_assets):
                for quote in active_quotes:
                    if base_asset == quote:
                        continue

                    candidate = f"{base_asset}/{quote}"
                    market = markets.get(candidate)
                    if not market:
                        continue
                    if not market.get("active", True):
                        continue
                    pairs.append(candidate)

            pairs = sorted(set(pairs))
            if max_pairs > 0:
                pairs = pairs[:max_pairs]
            return pairs

        except Exception as e:
            logger.error(f"Failed to extract balance trading pairs: {e}")
            return []

    def get_funding_free_balance(self, asset: str) -> float:
        """Read free balance for an asset in Funding wallet."""
        asset = str(asset or "").upper()
        if not asset:
            return 0.0
        try:
            rows = self.exchange.sapiPostAssetGetFundingAsset({"asset": asset})
            if not rows:
                return 0.0
            return float(rows[0].get("free", 0.0) or 0.0)
        except Exception as e:
            logger.error(f"Funding balance read failed for {asset}: {e}")
            return 0.0

    def sync_funding_to_spot(self, assets=None, min_free=None):
        """
        Move available balances from Funding wallet to Spot wallet.
        Returns map {ASSET: transferred_amount}.
        """
        assets = assets or getattr(Config, "FUNDING_TRANSFER_ASSETS", ["BNB"])
        min_free = (
            float(getattr(Config, "FUNDING_TRANSFER_MIN_FREE", 0.00001))
            if min_free is None
            else float(min_free)
        )

        moved = {}
        try:
            spot_balances = self.fetch_balance() or {}
            for asset in assets:
                symbol = str(asset or "").upper().strip()
                if not symbol:
                    continue

                spot_free = float((spot_balances.get(symbol) or {}).get("free", 0.0) or 0.0)
                if spot_free >= min_free:
                    continue

                funding_free = self.get_funding_free_balance(symbol)
                if funding_free < min_free:
                    continue

                amount = funding_free
                try:
                    self.exchange.transfer(symbol, amount, "funding", "spot")
                    moved[symbol] = amount
                    logger.info(f"Moved {amount:.8f} {symbol} from Funding to Spot")
                except Exception as e:
                    logger.error(f"Funding->Spot transfer failed for {symbol}: {e}")

            return moved
        except Exception as e:
            logger.error(f"Funding sync failed: {e}")
            return moved

    def create_market_order(self, symbol, side, amount, params=None):
        """أمر سوق (Market Order)"""
        params = params or {}
        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type="market",
                side=side.lower(),
                amount=amount,
                params=params
            )
            logger.info(
                f"✅ أمر سوق: {side} {amount} {symbol} "
                f"| Order ID: {order['id']}"
            )
            return order
        except ccxt.InsufficientFunds as e:
            logger.error(f"❌ رصيد غير كافٍ: {e}")
            return None
        except ccxt.BaseError as e:
            logger.error(f"❌ خطأ في أمر السوق: {e}")
            return None

    def create_limit_order(self, symbol, side, amount, price, params=None):
        """أمر محدد (Limit Order)"""
        params = params or {}
        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type="limit",
                side=side.lower(),
                amount=amount,
                price=price,
                params=params
            )
            logger.info(
                f"✅ أمر محدد: {side} {amount} {symbol} @ {price} "
                f"| Order ID: {order['id']}"
            )
            return order
        except ccxt.BaseError as e:
            logger.error(f"❌ خطأ في الأمر المحدد: {e}")
            return None

    def create_stop_loss_order(self, symbol, side, amount, stop_price, params=None):
        """أمر وقف الخسارة (Stop Loss)"""
        params = params or {}
        params["stopPrice"] = stop_price
        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type="stop_loss_limit",
                side=side.lower(),
                amount=amount,
                price=stop_price,
                params=params
            )
            logger.info(
                f"🛡️ وقف خسارة: {side} {amount} {symbol} @ {stop_price}"
            )
            return order
        except ccxt.BaseError as e:
            logger.error(f"❌ خطأ في وقف الخسارة: {e}")
            return None

    def create_take_profit_order(self, symbol, side, amount, tp_price, params=None):
        """أمر جني الأرباح (Take Profit)"""
        params = params or {}
        params["stopPrice"] = tp_price
        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type="take_profit_limit",
                side=side.lower(),
                amount=amount,
                price=tp_price,
                params=params
            )
            logger.info(
                f"🎯 جني أرباح: {side} {amount} {symbol} @ {tp_price}"
            )
            return order
        except ccxt.BaseError as e:
            logger.error(f"❌ خطأ في جني الأرباح: {e}")
            return None

    def cancel_order(self, order_id, symbol=None):
        """إلغاء أمر"""
        symbol = symbol or Config.DEFAULT_PAIR
        try:
            result = self.exchange.cancel_order(order_id, symbol)
            logger.info(f"🚫 تم إلغاء الأمر: {order_id}")
            return result
        except ccxt.BaseError as e:
            logger.error(f"خطأ في إلغاء الأمر: {e}")
            return None

    def fetch_open_orders(self, symbol=None):
        """جلب الأوامر المفتوحة"""
        symbol = symbol or Config.DEFAULT_PAIR
        try:
            orders = self.exchange.fetch_open_orders(symbol)
            return orders
        except ccxt.BaseError as e:
            logger.error(f"خطأ في جلب الأوامر المفتوحة: {e}")
            return []

    def get_market_limits(self, symbol=None):
        """قراءة حدود السوق (الكمية الدنيا / القيمة الدنيا / خطوة الكمية)"""
        symbol = symbol or Config.DEFAULT_PAIR
        try:
            markets = self.exchange.load_markets()
            market = markets.get(symbol, {})

            amount_limits = market.get("limits", {}).get("amount", {}) or {}
            cost_limits = market.get("limits", {}).get("cost", {}) or {}
            min_amount = float(amount_limits.get("min") or 0.0)
            min_cost = float(cost_limits.get("min") or 0.0)

            step_size = 0.0
            min_notional = 0.0
            filters = market.get("info", {}).get("filters", []) or []
            for f in filters:
                f_type = f.get("filterType", "")
                if f_type == "LOT_SIZE":
                    step_size = float(f.get("stepSize") or 0.0)
                elif f_type in ("MIN_NOTIONAL", "NOTIONAL"):
                    min_notional = float(
                        f.get("minNotional") or f.get("notional") or 0.0
                    )

            if min_notional > min_cost:
                min_cost = min_notional

            return {
                "min_amount": min_amount,
                "min_cost": min_cost,
                "min_notional": min_notional,
                "step_size": step_size,
            }
        except Exception as e:
            logger.debug(f"تعذر قراءة حدود السوق {symbol}: {e}")
            return {
                "min_amount": 0.0,
                "min_cost": 0.0,
                "min_notional": 0.0,
                "step_size": 0.0,
            }

    def get_min_amount(self, symbol=None):
        """الحد الأدنى لكمية التداول"""
        symbol = symbol or Config.DEFAULT_PAIR
        try:
            limits = self.get_market_limits(symbol)
            min_amount = float(limits.get("min_amount", 0.0))
            return min_amount if min_amount > 0 else 0.001
        except Exception:
            return 0.001
