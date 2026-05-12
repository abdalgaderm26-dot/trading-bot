"""
===================================================================
  strategy_engine.py - محرك الاستراتيجية المتقدم v2.0
  Advanced Strategy Engine - Score-Based with MTF
===================================================================
  نظام نقاط مرن بدل شروط صارمة:
  - كل مؤشر يضيف نقاط (0-100)
  - BUY عند مجموع > 65
  - SELL عند مجموع < 35
===================================================================
"""

import logging
from config import Config
from order_book_analyzer import OrderBookAnalyzer

logger = logging.getLogger("TradingBot.Strategy")


class StrategyEngine:
    """محرك استراتيجية متقدم بنظام النقاط"""

    def __init__(self, analyzer, ai_model, market_regime=None):
        self.analyzer = analyzer
        self.ai_model = ai_model
        self.market_regime = market_regime
        # في وضع الفيوتشرز: حدود صارمة لدخول صفقات قوية فقط
        if getattr(Config, "ENABLE_FUTURES", False):
            self.buy_threshold = int(getattr(Config, "FUTURES_MIN_SCORE", 70))
            self.sell_threshold = 55
            self.min_ai_score = 60
        else:
            # وضع Spot المحترف: دخول عالي الثقة مع فلاتر احترافية
            self.buy_threshold = 72   # ⚡ خُفض من 78 (الفلاتر الـ8 تحمي بدلاً منه)
            self.sell_threshold = 50
            self.min_ai_score = 60   # ⚡ خُفض من 65 (confluence >= 3 يعوّض)

    # ──────────────── التقييم الرئيسي ────────────────
    def evaluate(self, ohlcv_data, pair, client=None) -> dict:
        """تقييم شامل مع نظام النقاط"""
        try:
            # تحليل الإطار الرئيسي (1h)
            analysis = self.analyzer.analyze(ohlcv_data, pair)
            if not analysis:
                return self._hold_signal(pair, "بيانات غير كافية")

            # تحليل متعدد الأطر (اختياري - يحتاج client)
            mtf = None
            if client:
                try:
                    mtf = self.analyzer.multi_timeframe_analyze(client, pair)
                except:
                    pass

            # كشف نظام السوق
            regime = None
            if self.market_regime:
                df = analysis.get("df")
                if df is not None:
                    regime = self.market_regime.detect(df)

            # تقييم AI
            ai_result = self.ai_model.predict_score(analysis)
            ai_score = ai_result.get("score", 50)

            # تقييم تحليل دفتر الأوامر (WebSockets/REST)
            ob_analysis = {}
            if client and hasattr(self, 'ob_analyzer'):
                 ob_analysis = self.ob_analyzer.analyze(pair)

            # ──── حساب النقاط ────
            buy_score, sell_score, details, pump_ctx = self._calculate_scores(
                analysis, ai_result, mtf, regime, ob_analysis
            )

            # ──── القرار ────
            signal = self._make_decision(
                buy_score, sell_score, ai_score, pair, analysis, details, regime, pump_ctx
            )

            return signal

        except Exception as e:
            logger.error(f"❌ خطأ في التقييم: {e}")
            return self._hold_signal(pair, str(e))

    # ──────────────── فلتر ضمان الربح ────────────────
    def _profit_guarantee_filter(self, analysis, pair) -> bool:
        """
        فلتر احترافي: يتأكد أن التذبذب الطبيعي للعملة (ATR) أكبر من تكلفة الصفقة.
        بمعنى: إذا كان التذبذب صغير جداً (= عملة راكدة) لن تصل للهدف قبل أن تأخذ بينانس عمولتها.
        """
        atr_pct = float(analysis.get("atr_pct", 0) or 0)
        # الحد الأدنى = عمولة بينانس (0.2%) * 2 (شراء+بيع) + هدف الربح الأدنى (0.5%) = 0.9%
        # لكن نستخدم نصفه فقط لأن ATR هو متوسط التذبذب اليومي وليس الربح المباشر
        # ATR 0.45% يعني العملة تتحرك بما يكفي لتحقيق ربح 0.5% بشكل واقعي
        min_atr_required = float(getattr(Config, "TAKE_PROFIT_MIN", 0.007)) * 0.6 + 0.002  # ≈ 0.42%+
        if atr_pct < min_atr_required:
            logger.info(
                f"⏸️ {pair}: ⛔ تذبذب ATR ضعيف جداً ({atr_pct:.3%}) | "
                f"الحد الأدنى المطلوب {min_atr_required:.3%} | "
                f"العملة راكدة لن تغطي العمولة!"
            )
            return False  # رفض الدخول
        return True  # مسموح بالدخول

    # ──────────────── حساب النقاط ────────────────
    def _calculate_scores(self, analysis, ai_result, mtf, regime, ob_analysis=None):
        """حساب نقاط الشراء والبيع"""
        buy_score = 0
        sell_score = 0
        details = []

        rsi = analysis.get("rsi", 50)
        trend = analysis.get("trend", {})
        macd_cross = analysis.get("macd_cross", {})
        volume = analysis.get("volume_analysis", {})
        candle = analysis.get("candle_pattern", {})
        position = analysis.get("price_position", {})
        breakout = analysis.get("breakout", {})
        momentum = analysis.get("momentum_score", 50)
        ai_score = ai_result.get("score", 50)

        # ═══════ 1. RSI (max 20 pts) ═══════
        if rsi < 30:
            buy_score += 20
            details.append(f"RSI تشبع بيع قوي ({rsi:.0f}) +20")
        elif rsi < 40:
            buy_score += 15
            details.append(f"RSI منخفض ({rsi:.0f}) +15")
        elif rsi < 50:
            buy_score += 8
            details.append(f"RSI معتدل ({rsi:.0f}) +8")
        elif rsi > 75:
            sell_score += 20
            details.append(f"RSI تشبع شراء قوي ({rsi:.0f}) بيع+20")
        elif rsi > 65:
            sell_score += 15
            details.append(f"RSI مرتفع ({rsi:.0f}) بيع+15")
        elif rsi > 55:
            sell_score += 8

        # ═══════ 2. الاتجاه (max 15 pts) ═══════
        if trend.get("direction") == "BULLISH":
            buy_score += 15
            details.append("اتجاه صعودي +15")
        elif trend.get("direction") == "BEARISH":
            sell_score += 15
            details.append("اتجاه هبوطي بيع+15")

        # ═══════ 3. MACD Cross (max 15 pts) ═══════
        macd_sig = macd_cross.get("signal", "NEUTRAL")
        if macd_sig == "BULLISH_CROSS":
            buy_score += 15
            details.append("تقاطع MACD صعودي +15")
        elif macd_sig == "BULLISH":
            buy_score += 7
        elif macd_sig == "BEARISH_CROSS":
            sell_score += 15
            details.append("تقاطع MACD هبوطي بيع+15")
        elif macd_sig == "BEARISH":
            sell_score += 7

        # ═══════ 4. الحجم (max 10 pts) ═══════
        if volume.get("is_high"):
            buy_score += 10
            details.append("حجم مرتفع +10")
        elif volume.get("is_increasing"):
            buy_score += 5
            details.append("حجم متزايد +5")

        # ═══════ 5. أنماط الشموع (max 12 pts) ═══════
        if candle.get("direction") == "BULLISH":
            pts = min(candle.get("score", 0) / 7, 12)
            buy_score += pts
            details.append(f"نمط شمعة صعودي ({candle['pattern']}) +{pts:.0f}")
        elif candle.get("direction") == "BEARISH":
            pts = min(candle.get("score", 0) / 7, 12)
            sell_score += pts

        # ═══════ 6. موقع السعر (max 10 pts) ═══════
        if position.get("near_support"):
            buy_score += 10
            details.append("قرب دعم +10")
        if position.get("below_bb"):
            buy_score += 8
            details.append("تحت بولينجر +8")
        if position.get("near_resistance"):
            sell_score += 10
        if position.get("above_bb"):
            sell_score += 8

        # ═══════ 7. الاختراق (max 12 pts) ═══════
        if breakout.get("breakout"):
            if breakout["direction"] == "UP":
                buy_score += 12
                details.append("اختراق صعودي! +12")
            elif breakout["direction"] == "DOWN":
                sell_score += 12

        # ═══════ 8. AI Score (max 20 pts) ═══════
        if ai_score > 70:
            buy_score += 20
            details.append(f"AI عالي ({ai_score:.0f}) +20")
        elif ai_score > 60:
            buy_score += 12
            details.append(f"AI إيجابي ({ai_score:.0f}) +12")
        elif ai_score < 35:
            sell_score += 20
        elif ai_score < 45:
            sell_score += 10

        # ═══════ 9. Multi-Timeframe (max 15 pts) ═══════
        if mtf and mtf.get("alignment"):
            align = mtf["alignment"]
            if align.get("buy_aligned"):
                buy_score += 15
                details.append(f"توافق 3 أطر صعودي +15")
            elif align.get("sell_aligned"):
                sell_score += 15
            elif align.get("score", 0) > 60:
                buy_score += 8

        # ═══════ 10. Order Book (Whales) (max 25 pts) ═══════
        if ob_analysis:
            ob_score = ob_analysis.get("score", 0)
            if ob_score > 0:
                buy_score += min(ob_score, 25)
                details.append(f"سيولة لصالح الشراء (OBI/Whales) +{min(ob_score, 25)}")
            elif ob_score < 0:
                sell_score += min(abs(ob_score), 25)
                details.append(f"سيولة لصالح البيع (OBI/Whales) بيع+{min(abs(ob_score), 25)}")
                
            if ob_analysis.get("whale_bid"):
                details.append("🐋 حوت شراء (BID Wall) يحمي السعر")
            if ob_analysis.get("whale_ask"):
                details.append("🐋 حوت بيع (ASK Wall) يضغط السعر")

        # ═══════ 11. Pump / Steady-Up Focus ═══════
        pump_ctx = self._detect_pump_context(analysis)
        if pump_ctx["is_pump"]:
            bonus = int(getattr(Config, "PUMP_SCORE_BONUS", 18))
            buy_score += bonus
            details.append(
                f"اندفاع قوي +{bonus} (3c={pump_ctx['pct_3']:.2%}, vol×{pump_ctx['volume_ratio']:.2f})"
            )
        elif pump_ctx["is_steady"]:
            bonus = int(getattr(Config, "STEADY_SCORE_BONUS", 12))
            buy_score += bonus
            details.append(
                f"صعود منتظم +{bonus} (5c={pump_ctx['pct_5']:.2%}, green={pump_ctx['green_5']}/5)"
            )

        # ═══════ 12. نظام السوق (modifier) ═══════
        if regime:
            r = regime.get("regime", "UNKNOWN")
            if r == "TRENDING_UP":
                buy_score *= 1.15
                details.append("سوق صعودي ×1.15")
            elif r == "TRENDING_DOWN":
                sell_score *= 1.15
            elif r == "VOLATILE":
                buy_score *= 0.6
                sell_score *= 0.6
                details.append("⚠️ سوق متذبذب ×0.6")
            elif r == "RANGING":
                if position.get("near_support"):
                    buy_score *= 1.2

        # ═══════ 13. Trend Pullback Bonus (الأهم!) ═══════
        pullback = self._is_trend_pullback(analysis)
        if pullback["is_pullback"]:
            buy_score += 20
            details.append(
                f"🎯 انخفاض في صعود! (4h={pullback['trend_4h']}, RSI15m={pullback['rsi_short']:.0f}) +20"
            )

        return round(buy_score), round(sell_score), details, pump_ctx

    # ──────────────── اتخاذ القرار (عقل متداول 20 سنة خبرة) ────────────────
    def _make_decision(self, buy_score, sell_score, ai_score, pair,
                       analysis, details, regime, pump_ctx=None):
        """اتخاذ قرار الشراء/البيع بناءً على النقاط + فلاتر احترافية"""

        pump_ctx = pump_ctx or {
            "is_pump": False,
            "is_steady": False,
            "pct_3": 0.0,
            "pct_5": 0.0,
            "green_5": 0,
            "volume_ratio": 0.0,
            "breakout_up": False,
        }

        # حالة خاصة: لا تداول في سوق متذبذب
        if regime and regime.get("regime") == "VOLATILE" and regime.get("strength", 0) > 70:
            logger.info(f"⏸️ {pair}: ⚠️ سوق متذبذب جداً - انتظار")
            return self._hold_signal(pair, "سوق متذبذب")

        # ──── قرار الشراء ────
        if buy_score >= self.buy_threshold and ai_score >= self.min_ai_score:

            # ═══ فلتر 0: Trend Pullback يعطي أولوية ═══
            pullback = self._is_trend_pullback(analysis)
            if pullback["is_pullback"]:
                logger.info(
                    f"🎯 {pair}: فرصة Pullback! الاتجاه صاعد + السعر تراجع مؤقتاً"
                )

            # ═══ فلتر 1: التحقق من التذبذب كافي لتغطية العمولة ═══
            if not self._profit_guarantee_filter(analysis, pair):
                return self._hold_signal(pair, "ATR صغير - العملة راكدة لن تغطي العمولة")

            # ═══ فلتر 2: التقاطع (Confluence) - قاعدة المحترف ═══
            # المتداول المحترف لا يدخل إلا عندما تتفق 3+ مؤشرات مختلفة
            confluence = self._count_confluence(analysis, ai_score, pump_ctx)
            if confluence < 3:
                logger.info(
                    f"⏸️ {pair}: فلتر الاحتراف - تقاطع ضعيف ({confluence}/3 مؤشرات فقط)"
                )
                return self._hold_signal(pair, f"تقاطع ضعيف ({confluence}/3)")

            # ═══ فلتر 3: لا تشتري في قمة RSI (خطأ المبتدئين) ═══
            rsi = analysis.get("rsi", 50)
            if rsi > 68:
                logger.info(f"⏸️ {pair}: RSI مرتفع جداً ({rsi:.0f}) - خطر الشراء في القمة")
                return self._hold_signal(pair, f"RSI مرتفع {rsi:.0f} - انتظار تراجع")

            # ═══ فلتر 4: تباعد الحجم (Volume Divergence) ═══
            # إذا السعر يرتفع لكن الحجم ينخفض = ارتفاع وهمي
            vol = analysis.get("volume_analysis", {})
            if pump_ctx.get("pct_3", 0) > 0.005 and vol.get("ratio", 1) < 0.8:
                logger.info(f"⏸️ {pair}: تباعد حجم! السعر يرتفع لكن الحجم ضعيف = فخ")
                return self._hold_signal(pair, "تباعد حجم - ارتفاع وهمي")

            # ═══ فلتر 5: لا تشتري ضد اتجاه السوق العام ═══
            if regime and regime.get("regime") == "TRENDING_DOWN" and regime.get("strength", 0) > 55:
                logger.info(f"⏸️ {pair}: السوق هابط بقوة - لا تشتري ضد التيار")
                return self._hold_signal(pair, "اتجاه هابط قوي")

            # ═══ فلتر 6: لا تشتري سكين ساقط (شمعة هبوطية كبيرة) ═══
            candle = analysis.get("candle_pattern", {})
            if candle.get("direction") == "BEARISH" and candle.get("score", 0) > 60:
                logger.info(f"⏸️ {pair}: شمعة هبوطية قوية - سكين ساقط!")
                return self._hold_signal(pair, "شمعة هبوطية قوية - انتظار استقرار")

            # ═══ فلتر 7: لا تشتري فوق المقاومة بكثير (ممتد) ═══
            price_pos = analysis.get("price_position", {})
            if price_pos.get("above_bb"):
                bb_upper = analysis.get("bb_upper", 0)
                current = analysis.get("price", 0)
                if bb_upper > 0 and current > bb_upper * 1.005:
                    logger.info(f"⏸️ {pair}: السعر فوق بولينجر العلوي = ممتد")
                    return self._hold_signal(pair, "سعر ممتد فوق بولينجر")

            # ═══ فلتر 8: التأكد أن الربح المتوقع > العمولة الفعلية ═══
            atr_pct = float(analysis.get("atr_pct", 0) or 0)
            fee_pct = getattr(Config, "EXCHANGE_FEE_PCT", 0.002)
            if atr_pct > 0 and atr_pct < fee_pct * 3:
                logger.info(f"⏸️ {pair}: ATR ({atr_pct:.3%}) < 3x العمولة ({fee_pct*3:.3%})")
                return self._hold_signal(pair, "تذبذب أقل من 3 أضعاف العمولة")

            # ═══ فلتر Pump Focus ═══
            is_fast_opportunity = bool(
                pump_ctx.get("is_pump") or pump_ctx.get("is_steady")
            )
            if getattr(Config, "PUMP_FOCUS_MODE", False) and not is_fast_opportunity:
                logger.info(
                    f"⏸️ {pair}: تجاهل الشراء (وضع القنص الصارم) | "
                    f"السعر لا يظهر موجة صعود واضحة"
                )
                return self._hold_signal(pair, "focus mode strict: no pump/steady setup")

            # ✅ كل الفلاتر اجتازت - دخول احترافي مؤكد!
            strength = min(buy_score, 100)
            logger.info(
                f"🟢 إشارة شراء احترافية {pair} | نقاط={buy_score} | "
                f"AI={ai_score:.0f} | تقاطع={confluence} | القوة={strength}"
            )
            for d in details[:5]:
                logger.info(f"   ↳ {d}")

            quick_exit_pct = 0.0
            if is_fast_opportunity:
                quick_exit_pct = float(getattr(Config, "PUMP_QUICK_EXIT_PCT", 0.0) or 0.0)
                if quick_exit_pct <= 0:
                    quick_exit_pct = float(getattr(Config, "MIN_PROFIT_CLOSE_PCT", 0.0) or 0.0)

            return {
                "signal": "BUY",
                "pair": pair,
                "strength": strength,
                "buy_score": buy_score,
                "sell_score": sell_score,
                "ai_score": ai_score,
                "price": analysis.get("price", 0),
                "details": details,
                "regime": regime.get("regime") if regime else "UNKNOWN",
                "is_pump": bool(pump_ctx.get("is_pump")),
                "is_steady": bool(pump_ctx.get("is_steady")),
                "pump_metrics": pump_ctx,
                "quick_exit_pct": quick_exit_pct,
                "confluence": confluence,
            }

        # ──── قرار البيع ────
        elif sell_score >= self.buy_threshold and sell_score > buy_score:
            strength = min(sell_score, 100)
            logger.info(f"🔴 إشارة بيع {pair} | نقاط بيع={sell_score}")
            return {
                "signal": "SELL",
                "pair": pair,
                "strength": strength,
                "buy_score": buy_score,
                "sell_score": sell_score,
                "ai_score": ai_score,
                "price": analysis.get("price", 0),
                "details": details,
                "regime": regime.get("regime") if regime else "UNKNOWN"
            }

        # ──── انتظار ────
        else:
            gap = self.buy_threshold - buy_score
            logger.info(
                f"⏳ {pair}: انتظار | شراء={buy_score} | بيع={sell_score} | "
                f"AI={ai_score:.0f} | ينقص {gap} نقطة للشراء"
            )
            return self._hold_signal(pair, f"نقاط غير كافية (شراء={buy_score})")

    def _count_confluence(self, analysis, ai_score, pump_ctx):
        """
        عد عدد المؤشرات المتوافقة (Confluence Count).
        المتداول المحترف يحتاج 3+ مؤشرات متفقة قبل الدخول.
        """
        count = 0

        # 1. RSI في منطقة تشبع بيعي حقيقي (< 40 بدل 45)
        rsi = analysis.get("rsi", 50)
        if rsi < 40:
            count += 1

        # 2. الاتجاه صعودي
        trend = analysis.get("trend", {})
        if trend.get("direction") == "BULLISH":
            count += 1

        # 3. MACD تقاطع صعودي (التقاطع أقوى من مجرد إيجابي)
        macd = analysis.get("macd_cross", {}).get("signal", "NEUTRAL")
        if macd == "BULLISH_CROSS":
            count += 1
        elif macd == "BULLISH":
            count += 0.5

        # 4. حجم مرتفع (ليس فقط متزايد)
        vol = analysis.get("volume_analysis", {})
        if vol.get("is_high"):
            count += 1

        # 5. AI يدعم الشراء (> 60 بدل 55)
        if ai_score > 60:
            count += 1

        # 6. السعر قرب دعم أو تحت بولينجر
        pos = analysis.get("price_position", {})
        if pos.get("near_support") or pos.get("below_bb"):
            count += 1

        # 7. زخم صعودي
        if pump_ctx.get("is_pump") or pump_ctx.get("is_steady"):
            count += 1

        # 8. شمعة صعودية
        candle = analysis.get("candle_pattern", {})
        if candle.get("direction") == "BULLISH":
            count += 1

        return int(count)

    def _detect_pump_context(self, analysis):
        """
        Detect fast upward momentum (pump) or steady ordered climb.
        Uses only current OHLCV window from analysis to avoid extra API calls.
        """
        context = {
            "is_pump": False,
            "is_steady": False,
            "pct_3": 0.0,
            "pct_5": 0.0,
            "green_5": 0,
            "volume_ratio": 0.0,
            "breakout_up": False,
        }

        try:
            df = analysis.get("df")
            if df is None or len(df) < 6:
                return context

            close = df["close"].values
            opens = df["open"].values

            current = float(close[-1] or 0.0)
            past_3 = float(close[-4] or 0.0) if len(close) >= 4 else 0.0
            past_5 = float(close[-6] or 0.0) if len(close) >= 6 else 0.0

            pct_3 = ((current - past_3) / past_3) if past_3 > 0 else 0.0
            pct_5 = ((current - past_5) / past_5) if past_5 > 0 else 0.0

            green_5 = 0
            for i in range(1, 6):
                if float(close[-i]) > float(opens[-i]):
                    green_5 += 1

            vol_ratio = float(
                (analysis.get("volume_analysis") or {}).get("ratio", 0.0) or 0.0
            )
            trend_dir = (analysis.get("trend") or {}).get("direction", "NEUTRAL")
            breakout = analysis.get("breakout") or {}
            breakout_up = bool(breakout.get("breakout") and breakout.get("direction") == "UP")

            is_pump = (
                (pct_3 >= float(getattr(Config, "PUMP_MIN_3C_PCT", 0.012))
                 and vol_ratio >= float(getattr(Config, "PUMP_VOLUME_RATIO_MIN", 1.8)))
                or
                (pct_5 >= float(getattr(Config, "PUMP_MIN_5C_PCT", 0.02))
                 and vol_ratio >= max(1.1, float(getattr(Config, "PUMP_VOLUME_RATIO_MIN", 1.8)) * 0.85))
                or
                (breakout_up and vol_ratio >= float(getattr(Config, "PUMP_VOLUME_RATIO_MIN", 1.8)) and pct_3 > 0)
            )

            is_steady = (
                pct_5 >= float(getattr(Config, "STEADY_UP_MIN_5C_PCT", 0.008))
                and green_5 >= int(getattr(Config, "STEADY_UP_MIN_GREEN_CANDLES", 4))
                and trend_dir == "BULLISH"
            )

            context.update({
                "is_pump": bool(is_pump),
                "is_steady": bool(is_steady),
                "pct_3": float(pct_3),
                "pct_5": float(pct_5),
                "green_5": int(green_5),
                "volume_ratio": float(vol_ratio),
                "breakout_up": bool(breakout_up),
            })
            return context
        except Exception:
            return context

    def _is_trend_pullback(self, analysis) -> dict:
        """
        كشف "الانخفاض المؤقت في اتجاه صاعد" (Trend Pullback).
        هذا هو أفضل وقت للشراء: الاتجاه العام صاعد لكن السعر تراجع مؤقتاً.
        
        الشروط:
        1. الاتجاه على الإطار الأكبر (4h/1h) = صاعد
        2. RSI على الإطار الأصغر (15m) < 40 = تراجع مؤقت
        3. MACD يبدأ بالتحول للصعود = بداية ارتداد
        """
        result = {
            "is_pullback": False,
            "trend_4h": "UNKNOWN",
            "rsi_short": 50,
            "confidence": 0,
        }

        try:
            # الاتجاه الرئيسي (من التحليل الحالي)
            trend = analysis.get("trend", {})
            trend_dir = trend.get("direction", "NEUTRAL")
            rsi = analysis.get("rsi", 50)
            macd_cross = analysis.get("macd_cross", {}).get("signal", "NEUTRAL")
            momentum = analysis.get("momentum_score", 50)

            # MTF data إذا متوفر
            mtf = analysis.get("mtf", {})
            trend_4h = "UNKNOWN"
            if mtf:
                trend_4h = mtf.get("4h", {}).get("trend", "UNKNOWN")

            # شروط الـ Pullback:
            # 1. الاتجاه العام صاعد (الإطار الحالي أو 4h)
            is_uptrend = trend_dir == "BULLISH" or trend_4h == "BULLISH"

            # 2. RSI منخفض = تراجع مؤقت (أقل من 42)
            is_dip = rsi < 42

            # 3. بداية ارتداد (MACD صعودي أو تقاطع)
            is_recovering = macd_cross in ("BULLISH_CROSS", "BULLISH")

            # 4. الزخم لا يزال إيجابي على المدى المتوسط
            has_momentum = momentum >= 40

            result["trend_4h"] = trend_4h if trend_4h != "UNKNOWN" else trend_dir
            result["rsi_short"] = rsi

            if is_uptrend and is_dip and is_recovering and has_momentum:
                result["is_pullback"] = True
                # حساب الثقة
                confidence = 50
                if rsi < 35:
                    confidence += 15
                if macd_cross == "BULLISH_CROSS":
                    confidence += 15
                if trend_4h == "BULLISH":
                    confidence += 10
                if momentum >= 55:
                    confidence += 10
                result["confidence"] = min(100, confidence)

        except Exception:
            pass

        return result

    def _hold_signal(self, pair, reason=""):
        return {
            "signal": "HOLD",
            "pair": pair,
            "strength": 0,
            "reason": reason
        }

    # ──────────────── تعديل الحدود ────────────────
    def adjust_thresholds(self, buy_threshold=None, sell_threshold=None, min_ai=None):
        """تعديل حدود القرار (يستخدمه المحسّن التلقائي) مع حدود أمان"""
        if buy_threshold:
            self.buy_threshold = max(65, min(90, buy_threshold))  # ✅ لا تنزل تحت 65
        if sell_threshold:
            self.sell_threshold = max(20, min(60, sell_threshold))
        if min_ai:
            self.min_ai_score = max(55, min(80, min_ai))  # ✅ لا تنزل تحت 55
        logger.info(
            f"⚙️ تم تعديل الحدود: شراء≥{self.buy_threshold} | "
            f"بيع≤{self.sell_threshold} | AI≥{self.min_ai_score}"
        )
