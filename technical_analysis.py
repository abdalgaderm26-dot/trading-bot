"""
===================================================================
  technical_analysis.py - التحليل الفني المتقدم v2.0
  Advanced Technical Analysis with Multi-Timeframe
===================================================================
"""

import logging
import numpy as np
import pandas as pd
from config import Config

logger = logging.getLogger("TradingBot.TA")


class TechnicalAnalyzer:
    """محلل فني متقدم مع تحليل متعدد الأطر الزمنية"""

    def __init__(self):
        self.last_analysis = {}

    # ──────────────── التحليل الكامل ────────────────
    def analyze(self, ohlcv_data, pair="") -> dict:
        """تحليل شامل لبيانات OHLCV"""
        try:
            df = self._to_dataframe(ohlcv_data)
            if df is None or len(df) < 50:
                return None

            close = df["close"].values
            high = df["high"].values
            low = df["low"].values
            volume = df["volume"].values
            opens = df["open"].values

            # المؤشرات الأساسية
            rsi = self.calc_rsi(close)
            sma50 = self.calc_sma(close, 50)
            sma200 = self.calc_sma(close, 200)
            sma20 = self.calc_sma(close, 20)
            ema9 = self.calc_ema(close, 9)
            ema21 = self.calc_ema(close, 21)
            macd, signal, histogram = self.calc_macd(close)
            vol_analysis = self.analyze_volume(volume)
            bb_upper, bb_middle, bb_lower = self.calc_bollinger(close)
            atr = self.calc_atr(high, low, close)

            # تحليلات متقدمة
            trend = self.detect_trend(close, sma50, sma200)
            support, resistance = self.find_support_resistance(high, low, close)
            breakout = self.detect_breakout(close, high, low, volume)
            candle_pattern = self.detect_candle_patterns(opens, high, low, close)
            macd_cross = self.detect_macd_crossover(macd, signal)
            rsi_divergence = self.detect_rsi_divergence(close, rsi)
            momentum = self.calc_momentum_score(close, rsi, macd, histogram, volume)
            price_position = self.calc_price_position(close[-1], support, resistance, bb_lower, bb_upper)

            current_price = close[-1]

            result = {
                "price": current_price,
                "rsi": rsi,
                "sma20": sma20,
                "sma50": sma50,
                "sma200": sma200,
                "ema9": ema9,
                "ema21": ema21,
                "macd": macd,
                "macd_signal": signal,
                "macd_histogram": histogram,
                "macd_cross": macd_cross,
                "volume_analysis": vol_analysis,
                "bb_upper": bb_upper,
                "bb_middle": bb_middle,
                "bb_lower": bb_lower,
                "atr": atr,
                "atr_pct": (atr / current_price) if current_price > 0 else 0,
                "trend": trend,
                "support": support,
                "resistance": resistance,
                "breakout": breakout,
                "candle_pattern": candle_pattern,
                "rsi_divergence": rsi_divergence,
                "momentum_score": momentum,
                "price_position": price_position,
                "df": df
            }

            self.last_analysis[pair] = result

            logger.info(
                f"📊 تحليل {pair}: السعر={current_price:.2f} | "
                f"RSI={rsi:.1f} | الاتجاه={trend['direction']} | "
                f"MACD Cross={macd_cross['signal']} | "
                f"نقاط الزخم={momentum}/100 | "
                f"حجم مرتفع={'✅' if vol_analysis['is_high'] else '❌'}"
            )

            return result

        except Exception as e:
            logger.error(f"خطأ في التحليل الفني: {e}")
            return None

    # ──────────────── التحليل متعدد الأطر ────────────────
    def multi_timeframe_analyze(self, client, pair) -> dict:
        """تحليل 3 أطر زمنية: 4h (اتجاه) + 1h (تأكيد) + 15m (دخول)"""
        try:
            # جلب بيانات 3 أطر زمنية
            ohlcv_4h = client.fetch_ohlcv(pair, timeframe="4h", limit=200)
            ohlcv_1h = client.fetch_ohlcv(pair, timeframe="1h", limit=300)
            ohlcv_15m = client.fetch_ohlcv(pair, timeframe="15m", limit=200)

            analysis_4h = self.analyze(ohlcv_4h, f"{pair}_4h") if ohlcv_4h else None
            analysis_1h = self.analyze(ohlcv_1h, f"{pair}_1h") if ohlcv_1h else None
            analysis_15m = self.analyze(ohlcv_15m, f"{pair}_15m") if ohlcv_15m else None

            # تقييم التوافق
            alignment = self._evaluate_alignment(analysis_4h, analysis_1h, analysis_15m)

            result = {
                "4h": analysis_4h,
                "1h": analysis_1h,
                "15m": analysis_15m,
                "alignment": alignment,
                "primary": analysis_1h  # الإطار الرئيسي للقرار
            }

            logger.info(
                f"🔍 MTF {pair}: "
                f"4h={alignment['trend_4h']} | "
                f"1h={alignment['trend_1h']} | "
                f"15m={alignment['trend_15m']} | "
                f"توافق={alignment['score']}/100"
            )

            return result

        except Exception as e:
            logger.error(f"خطأ في التحليل متعدد الأطر: {e}")
            return None

    def _evaluate_alignment(self, a4h, a1h, a15m) -> dict:
        """تقييم توافق الأطر الزمنية"""
        trend_4h = a4h["trend"]["direction"] if a4h else "UNKNOWN"
        trend_1h = a1h["trend"]["direction"] if a1h else "UNKNOWN"
        trend_15m = a15m["trend"]["direction"] if a15m else "UNKNOWN"

        score = 0
        buy_aligned = False
        sell_aligned = False

        # توافق الاتجاه
        if trend_4h == "BULLISH":
            score += 40
            if trend_1h == "BULLISH":
                score += 30
                if trend_15m == "BULLISH":
                    score += 30
                    buy_aligned = True
                elif trend_15m != "BEARISH":
                    score += 15
        elif trend_4h == "BEARISH":
            score += 40
            if trend_1h == "BEARISH":
                score += 30
                if trend_15m == "BEARISH":
                    score += 30
                    sell_aligned = True
                elif trend_15m != "BULLISH":
                    score += 15

        # RSI alignment
        if a1h and a15m:
            rsi_1h = a1h.get("rsi", 50)
            rsi_15m = a15m.get("rsi", 50)
            # RSI oversold في كلاهما = فرصة شراء
            if rsi_1h < 40 and rsi_15m < 35:
                score += 10
                buy_aligned = True
            # RSI overbought = فرصة بيع
            elif rsi_1h > 65 and rsi_15m > 70:
                score += 10
                sell_aligned = True

        return {
            "trend_4h": trend_4h,
            "trend_1h": trend_1h,
            "trend_15m": trend_15m,
            "score": min(score, 100),
            "buy_aligned": buy_aligned,
            "sell_aligned": sell_aligned
        }

    # ──────────────── RSI ────────────────
    def calc_rsi(self, close, period=None):
        period = period or Config.RSI_PERIOD
        if len(close) < period + 1:
            return 50.0
        deltas = np.diff(close)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    # ──────────────── SMA ────────────────
    def calc_sma(self, close, period):
        if len(close) < period:
            return close[-1] if len(close) > 0 else 0
        return float(np.mean(close[-period:]))

    # ──────────────── EMA ────────────────
    def calc_ema(self, close, period):
        if len(close) < period:
            return close[-1] if len(close) > 0 else 0
        multiplier = 2 / (period + 1)
        ema = close[0]
        for price in close[1:]:
            ema = (price - ema) * multiplier + ema
        return float(ema)

    # ──────────────── MACD ────────────────
    def calc_macd(self, close):
        ema12 = self._ema_series(close, Config.MACD_FAST)
        ema26 = self._ema_series(close, Config.MACD_SLOW)
        macd_line = ema12[-1] - ema26[-1]
        signal_series = self._ema_series(ema12 - ema26, Config.MACD_SIGNAL)
        signal_line = signal_series[-1]
        histogram = macd_line - signal_line
        return float(macd_line), float(signal_line), float(histogram)

    def _ema_series(self, data, period):
        result = np.zeros(len(data))
        result[0] = data[0]
        mult = 2 / (period + 1)
        for i in range(1, len(data)):
            result[i] = (data[i] - result[i-1]) * mult + result[i-1]
        return result

    # ──────────────── MACD Crossover Detection ────────────────
    def detect_macd_crossover(self, macd, signal):
        """كشف تقاطع MACD"""
        # نحتاج بيانات سابقة للمقارنة
        # بما أن لدينا القيم الحالية فقط، نستخدم الـ histogram
        histogram = macd - signal

        if histogram > 0 and abs(histogram) < abs(macd) * 0.3:
            return {"signal": "BULLISH_CROSS", "strength": min(abs(histogram) * 10000, 100)}
        elif histogram < 0 and abs(histogram) < abs(macd) * 0.3:
            return {"signal": "BEARISH_CROSS", "strength": min(abs(histogram) * 10000, 100)}
        elif histogram > 0:
            return {"signal": "BULLISH", "strength": 50}
        elif histogram < 0:
            return {"signal": "BEARISH", "strength": 50}
        return {"signal": "NEUTRAL", "strength": 0}

    # ──────────────── أنماط الشموع ────────────────
    def detect_candle_patterns(self, opens, high, low, close):
        """كشف أنماط الشموع اليابانية"""
        if len(close) < 3:
            return {"pattern": "NONE", "direction": "NEUTRAL", "score": 0}

        body = close[-1] - opens[-1]
        body_size = abs(body)
        total_range = high[-1] - low[-1]
        upper_shadow = high[-1] - max(opens[-1], close[-1])
        lower_shadow = min(opens[-1], close[-1]) - low[-1]

        prev_body = close[-2] - opens[-2]
        prev_size = abs(prev_body)

        if total_range == 0:
            return {"pattern": "DOJI", "direction": "REVERSAL", "score": 30}

        body_ratio = body_size / total_range

        # Doji - شمعة تردد
        if body_ratio < 0.1:
            return {"pattern": "DOJI", "direction": "REVERSAL", "score": 40}

        # Hammer - مطرقة (إشارة شراء)
        if lower_shadow > body_size * 2 and upper_shadow < body_size * 0.5:
            return {"pattern": "HAMMER", "direction": "BULLISH", "score": 70}

        # Shooting Star - نجمة ساقطة (إشارة بيع)
        if upper_shadow > body_size * 2 and lower_shadow < body_size * 0.5:
            return {"pattern": "SHOOTING_STAR", "direction": "BEARISH", "score": 70}

        # Bullish Engulfing - ابتلاع صعودي
        if body > 0 and prev_body < 0 and body_size > prev_size * 1.2:
            return {"pattern": "BULLISH_ENGULFING", "direction": "BULLISH", "score": 80}

        # Bearish Engulfing - ابتلاع هبوطي
        if body < 0 and prev_body > 0 and body_size > prev_size * 1.2:
            return {"pattern": "BEARISH_ENGULFING", "direction": "BEARISH", "score": 80}

        # شمعة صعودية قوية
        if body > 0 and body_ratio > 0.7:
            return {"pattern": "STRONG_BULL", "direction": "BULLISH", "score": 50}

        # شمعة هبوطية قوية
        if body < 0 and body_ratio > 0.7:
            return {"pattern": "STRONG_BEAR", "direction": "BEARISH", "score": 50}

        return {"pattern": "NONE", "direction": "NEUTRAL", "score": 0}

    # ──────────────── RSI Divergence ────────────────
    def detect_rsi_divergence(self, close, current_rsi):
        """كشف تباين RSI مع السعر"""
        if len(close) < 30:
            return {"divergence": "NONE", "score": 0}

        # مقارنة RSI الحالي مع السعر
        price_change = (close[-1] - close[-10]) / close[-10]
        rsi_level = current_rsi

        # Bullish divergence: سعر ينزل + RSI يرتفع أو في منطقة تشبع بيع
        if price_change < -0.02 and rsi_level < 35:
            return {"divergence": "BULLISH", "score": 70}

        # Bearish divergence: سعر يرتفع + RSI في منطقة تشبع شراء
        if price_change > 0.02 and rsi_level > 70:
            return {"divergence": "BEARISH", "score": 70}

        return {"divergence": "NONE", "score": 0}

    # ──────────────── Momentum Score ────────────────
    def calc_momentum_score(self, close, rsi, macd, histogram, volume):
        """حساب نقاط الزخم الإجمالية (0-100)"""
        score = 50  # نقطة البداية

        # RSI score
        if rsi < 30:
            score += 15  # تشبع بيع = فرصة شراء
        elif rsi < 45:
            score += 10
        elif rsi > 70:
            score -= 15
        elif rsi > 55:
            score -= 5

        # MACD score
        if histogram > 0:
            score += 10
        else:
            score -= 10

        # Price momentum (آخر 5 شموع)
        if len(close) > 5:
            pct_change = (close[-1] - close[-5]) / close[-5]
            if pct_change > 0.02:
                score += 10
            elif pct_change > 0:
                score += 5
            elif pct_change < -0.02:
                score -= 10
            else:
                score -= 5

        # Volume
        if len(volume) > 20:
            avg_vol = np.mean(volume[-20:])
            if volume[-1] > avg_vol * 1.5:
                score += 10
            elif volume[-1] > avg_vol:
                score += 5

        return max(0, min(100, score))

    # ──────────────── Price Position ────────────────
    def calc_price_position(self, price, support, resistance, bb_lower, bb_upper):
        """موقع السعر بالنسبة للدعم/المقاومة وبولينجر"""
        position = {
            "near_support": False,
            "near_resistance": False,
            "below_bb": False,
            "above_bb": False,
            "score": 0  # إيجابي = فرصة شراء، سلبي = فرصة بيع
        }

        # قرب الدعم (فرصة شراء)
        if support > 0:
            dist_support = (price - support) / price
            if dist_support < 0.015:
                position["near_support"] = True
                position["score"] += 20

        # قرب المقاومة (فرصة بيع)
        if resistance > 0:
            dist_resistance = (resistance - price) / price
            if dist_resistance < 0.015:
                position["near_resistance"] = True
                position["score"] -= 20

        # تحت بولينجر السفلي (فرصة شراء)
        if bb_lower > 0 and price < bb_lower:
            position["below_bb"] = True
            position["score"] += 15

        # فوق بولينجر العلوي (فرصة بيع)
        if bb_upper > 0 and price > bb_upper:
            position["above_bb"] = True
            position["score"] -= 15

        return position

    # ──────────────── Volume Analysis ────────────────
    def analyze_volume(self, volume, period=20):
        if len(volume) < period:
            return {"current": 0, "average": 0, "ratio": 0, "is_high": False, "is_increasing": False}
        avg = np.mean(volume[-period:])
        current = volume[-1]
        ratio = current / avg if avg > 0 else 0
        # حجم متزايد في آخر 3 شموع
        is_increasing = all(volume[-i] > volume[-i-1] for i in range(1, min(4, len(volume))))
        return {
            "current": current,
            "average": avg,
            "ratio": ratio,
            "is_high": ratio > Config.VOLUME_MULTIPLIER,
            "is_increasing": is_increasing
        }

    # ──────────────── Bollinger Bands ────────────────
    def calc_bollinger(self, close, period=20, std_dev=2):
        if len(close) < period:
            p = close[-1]
            return p, p, p
        recent = close[-period:]
        middle = np.mean(recent)
        std = np.std(recent)
        return float(middle + std_dev * std), float(middle), float(middle - std_dev * std)

    # ──────────────── ATR ────────────────
    def calc_atr(self, high, low, close, period=14):
        if len(close) < period + 1:
            return 0
        tr = []
        for i in range(1, len(close)):
            tr.append(max(high[i]-low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1])))
        return float(np.mean(tr[-period:]))

    # ──────────────── Trend Detection ────────────────
    def detect_trend(self, close, sma50, sma200):
        price = close[-1]
        if sma200 > 0 and price > sma200 and price > sma50:
            direction = "BULLISH"
        elif sma200 > 0 and price < sma200 and price < sma50:
            direction = "BEARISH"
        elif sma50 > 0 and price > sma50:
            direction = "BULLISH"
        else:
            direction = "NEUTRAL"

        # قوة الاتجاه
        if sma200 > 0:
            strength = abs(price - sma200) / sma200 * 100
        else:
            strength = 0

        return {"direction": direction, "strength": min(strength, 100),
                "above_ma50": price > sma50, "above_ma200": price > sma200 if sma200 > 0 else None}

    # ──────────────── Support / Resistance ────────────────
    def find_support_resistance(self, high, low, close, lookback=50):
        if len(close) < lookback:
            lookback = len(close)
        recent_low = np.min(low[-lookback:])
        recent_high = np.max(high[-lookback:])
        price = close[-1]

        # مستويات متعددة
        price_range = recent_high - recent_low
        support = price - (price - recent_low) * 0.3
        resistance = price + (recent_high - price) * 0.3

        return float(support), float(resistance)

    # ──────────────── Breakout ────────────────
    def detect_breakout(self, close, high, low, volume, period=20):
        if len(close) < period:
            return {"breakout": False, "direction": "NONE"}
        recent_high = np.max(high[-period:-1])
        recent_low = np.min(low[-period:-1])
        avg_vol = np.mean(volume[-period:])

        if close[-1] > recent_high and volume[-1] > avg_vol * 1.3:
            return {"breakout": True, "direction": "UP", "level": recent_high}
        elif close[-1] < recent_low and volume[-1] > avg_vol * 1.3:
            return {"breakout": True, "direction": "DOWN", "level": recent_low}
        return {"breakout": False, "direction": "NONE"}

    # ──────────────── DataFrame Helper ────────────────
    def _to_dataframe(self, ohlcv_data):
        if not ohlcv_data or len(ohlcv_data) < 10:
            return None
        df = pd.DataFrame(ohlcv_data, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
