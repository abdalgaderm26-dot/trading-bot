"""
===================================================================
  market_regime.py - كشف نظام السوق
  Market Regime Detection (Trending / Ranging / Volatile)
===================================================================
  يحدد حالة السوق الحالية لتعديل الاستراتيجية تلقائياً
===================================================================
"""

import logging
import numpy as np
import pandas as pd

logger = logging.getLogger("TradingBot.Regime")


class MarketRegime:
    """
    كشف نظام السوق:
    - TRENDING_UP: اتجاه صعودي قوي → شراء مع الاتجاه
    - TRENDING_DOWN: اتجاه هبوطي قوي → بيع أو انتظار
    - RANGING: سوق جانبي → شراء عند دعم، بيع عند مقاومة
    - VOLATILE: تذبذب عالي → تقليل الحجم أو عدم التداول
    """

    def __init__(self):
        self.current_regime = "UNKNOWN"
        self.regime_strength = 0  # 0-100

    def detect(self, df: pd.DataFrame) -> dict:
        """كشف نظام السوق من بيانات OHLCV"""
        try:
            if df is None or len(df) < 50:
                return {"regime": "UNKNOWN", "strength": 0, "adx": 0, "volatility": "NORMAL"}

            close = df["close"].values
            high = df["high"].values
            low = df["low"].values

            # 1. حساب ADX (Average Directional Index)
            adx = self._calculate_adx(high, low, close, period=14)

            # 2. حساب ATR (Average True Range) كنسبة من السعر
            atr_pct = self._calculate_atr_pct(high, low, close, period=14)

            # 3. حساب ميل المتوسط المتحرك
            ma_slope = self._calculate_ma_slope(close, period=20)

            # 4. حساب تذبذب Bollinger Bands
            bb_width = self._calculate_bb_width(close, period=20)

            # 5. تحديد النظام
            regime = self._classify_regime(adx, atr_pct, ma_slope, bb_width)

            # 6. تحديد مستوى التذبذب
            volatility = self._classify_volatility(atr_pct, bb_width)

            self.current_regime = regime["regime"]
            self.regime_strength = regime["strength"]

            result = {
                "regime": regime["regime"],
                "strength": regime["strength"],
                "adx": round(adx, 2),
                "atr_pct": round(atr_pct, 4),
                "ma_slope": round(ma_slope, 6),
                "bb_width": round(bb_width, 4),
                "volatility": volatility,
                "trade_allowed": regime["regime"] != "VOLATILE",
                "recommended_action": self._get_recommendation(regime["regime"])
            }

            logger.info(
                f"🌐 نظام السوق: {result['regime']} | "
                f"القوة: {result['strength']}% | "
                f"ADX: {result['adx']} | "
                f"التذبذب: {result['volatility']}"
            )

            return result

        except Exception as e:
            logger.error(f"خطأ في كشف نظام السوق: {e}")
            return {"regime": "UNKNOWN", "strength": 0, "adx": 0, "volatility": "NORMAL",
                    "trade_allowed": True, "recommended_action": "HOLD"}

    def _calculate_adx(self, high, low, close, period=14):
        """حساب مؤشر ADX"""
        n = len(close)
        if n < period + 1:
            return 0

        # True Range
        tr = np.zeros(n)
        plus_dm = np.zeros(n)
        minus_dm = np.zeros(n)

        for i in range(1, n):
            h_diff = high[i] - high[i-1]
            l_diff = low[i-1] - low[i]

            plus_dm[i] = max(h_diff, 0) if h_diff > l_diff else 0
            minus_dm[i] = max(l_diff, 0) if l_diff > h_diff else 0
            tr[i] = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))

        # Smoothed averages
        atr = self._smooth(tr, period)
        plus_di = 100 * self._smooth(plus_dm, period) / np.where(atr > 0, atr, 1)
        minus_di = 100 * self._smooth(minus_dm, period) / np.where(atr > 0, atr, 1)

        # DX
        di_sum = plus_di + minus_di
        dx = 100 * np.abs(plus_di - minus_di) / np.where(di_sum > 0, di_sum, 1)

        # ADX = smoothed DX
        adx = self._smooth(dx, period)

        return float(adx[-1]) if len(adx) > 0 else 0

    def _smooth(self, data, period):
        """Wilder's smoothing"""
        result = np.zeros(len(data))
        result[period] = np.mean(data[1:period+1])
        for i in range(period+1, len(data)):
            result[i] = (result[i-1] * (period - 1) + data[i]) / period
        return result

    def _calculate_atr_pct(self, high, low, close, period=14):
        """حساب ATR كنسبة مئوية من السعر"""
        n = len(close)
        if n < period + 1:
            return 0

        tr = np.zeros(n)
        for i in range(1, n):
            tr[i] = max(
                high[i] - low[i],
                abs(high[i] - close[i-1]),
                abs(low[i] - close[i-1])
            )

        atr = np.mean(tr[-period:])
        current_price = close[-1]

        return (atr / current_price) if current_price > 0 else 0

    def _calculate_ma_slope(self, close, period=20):
        """حساب ميل المتوسط المتحرك"""
        if len(close) < period + 5:
            return 0

        ma = np.convolve(close, np.ones(period)/period, mode='valid')
        if len(ma) < 5:
            return 0

        # ميل آخر 5 قيم
        slope = (ma[-1] - ma[-5]) / (5 * ma[-5]) if ma[-5] > 0 else 0
        return slope

    def _calculate_bb_width(self, close, period=20):
        """حساب عرض بولينجر باند كنسبة"""
        if len(close) < period:
            return 0

        recent = close[-period:]
        ma = np.mean(recent)
        std = np.std(recent)

        if ma > 0:
            return (4 * std) / ma  # عرض الباند كنسبة من المتوسط
        return 0

    def _classify_regime(self, adx, atr_pct, ma_slope, bb_width):
        """تصنيف نظام السوق"""
        # VOLATILE: تذبذب عالي جداً
        if atr_pct > 0.04 or bb_width > 0.1:
            return {"regime": "VOLATILE", "strength": min(int(atr_pct * 2000), 100)}

        # TRENDING: ADX > 25 يعني اتجاه قوي
        if adx > 25:
            if ma_slope > 0.001:
                strength = min(int(adx * 2), 100)
                return {"regime": "TRENDING_UP", "strength": strength}
            elif ma_slope < -0.001:
                strength = min(int(adx * 2), 100)
                return {"regime": "TRENDING_DOWN", "strength": strength}

        # RANGING: ADX < 20 يعني سوق جانبي
        if adx < 20:
            return {"regime": "RANGING", "strength": min(int((20 - adx) * 5), 100)}

        # حالة وسطية
        if ma_slope > 0.0005:
            return {"regime": "TRENDING_UP", "strength": min(int(adx * 1.5), 100)}
        elif ma_slope < -0.0005:
            return {"regime": "TRENDING_DOWN", "strength": min(int(adx * 1.5), 100)}

        return {"regime": "RANGING", "strength": 50}

    def _classify_volatility(self, atr_pct, bb_width):
        """تصنيف مستوى التذبذب"""
        if atr_pct > 0.035:
            return "HIGH"
        elif atr_pct > 0.015:
            return "NORMAL"
        else:
            return "LOW"

    def _get_recommendation(self, regime):
        """توصية حسب نظام السوق"""
        recommendations = {
            "TRENDING_UP": "شراء مع الاتجاه عند التراجع",
            "TRENDING_DOWN": "بيع أو انتظار انعكاس",
            "RANGING": "شراء عند دعم - بيع عند مقاومة",
            "VOLATILE": "عدم التداول - تذبذب عالي",
            "UNKNOWN": "انتظار بيانات كافية"
        }
        return recommendations.get(regime, "HOLD")
