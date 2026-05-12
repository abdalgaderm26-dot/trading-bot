"""
===================================================================
  ai_model.py - نموذج ذكاء اصطناعي متقدم v2.0
  Advanced AI Model - Ensemble (3 Models Voting)
===================================================================
"""

import os
import logging
import numpy as np
import joblib
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.model_selection import train_test_split
from config import Config

logger = logging.getLogger("TradingBot.AI")


class AIModel:
    """نموذج AI متقدم مع Ensemble (3 نماذج تصوّت معاً)"""

    def __init__(self):
        self.models = {
            "gb": GradientBoostingClassifier(
                n_estimators=150, max_depth=5, learning_rate=0.05,
                min_samples_split=10, random_state=42
            ),
            "rf": RandomForestClassifier(
                n_estimators=150, max_depth=8, min_samples_split=10,
                random_state=42, n_jobs=-1
            )
        }
        self.model_weights = {"gb": 0.5, "rf": 0.5}
        self.model_accuracies = {}
        self.is_trained = False
        self._load_model()

    def _load_model(self):
        """تحميل النماذج المحفوظة"""
        for name in self.models:
            path = Config.MODEL_PATH.replace(".pkl", f"_{name}.pkl")
            if os.path.exists(path):
                try:
                    self.models[name] = joblib.load(path)
                    self.is_trained = True
                    logger.info(f"🧠 تم تحميل نموذج {name}")
                except Exception:
                    pass
        if self.is_trained:
            logger.info("🧠 تم تحميل نماذج AI المحفوظة (Ensemble)")

    def _save_models(self):
        """حفظ النماذج"""
        os.makedirs(os.path.dirname(Config.MODEL_PATH), exist_ok=True)
        for name, model in self.models.items():
            path = Config.MODEL_PATH.replace(".pkl", f"_{name}.pkl")
            joblib.dump(model, path)
        logger.info("💾 تم حفظ نماذج AI (Ensemble)")

    # ──────────────── التدريب ────────────────
    def train(self, ohlcv_data):
        """تدريب Ensemble على البيانات التاريخية"""
        try:
            features, labels = self._prepare_training_data(ohlcv_data)
            if features is None or len(features) < 100:
                logger.warning("⚠️ بيانات غير كافية للتدريب")
                return False

            X_train, X_test, y_train, y_test = train_test_split(
                features, labels, test_size=0.2, random_state=42, shuffle=False
            )

            total_weight = 0
            for name, model in self.models.items():
                model.fit(X_train, y_train)
                accuracy = model.score(X_test, y_test)
                self.model_accuracies[name] = accuracy
                # وزن أعلى للنموذج الأدق
                self.model_weights[name] = accuracy
                total_weight += accuracy
                logger.info(f"🧠 {name}: دقة {accuracy:.2%}")

            # تطبيع الأوزان
            for name in self.model_weights:
                self.model_weights[name] /= total_weight if total_weight > 0 else 1

            self.is_trained = True
            self._save_models()

            avg_acc = np.mean(list(self.model_accuracies.values()))
            logger.info(
                f"🧠 Ensemble مدرّب | متوسط الدقة: {avg_acc:.2%} | "
                f"عينات: {len(X_train)}+{len(X_test)}"
            )
            return True

        except Exception as e:
            logger.error(f"خطأ في التدريب: {e}")
            return False

    # ──────────────── التقييم ────────────────
    def predict_score(self, analysis: dict) -> dict:
        """تقييم الصفقة بنظام Ensemble"""
        try:
            features = self._extract_features(analysis)
            if features is None:
                return self._rule_based_score(analysis)

            features = np.array(features).reshape(1, -1)

            if self.is_trained:
                # تصويت مرجّح من عدة نماذج
                weighted_score = 0
                predictions = {}

                for name, model in self.models.items():
                    try:
                        if hasattr(model, "predict_proba"):
                            proba = model.predict_proba(features)[0]
                            # احتمال الصعود (class 1)
                            score = proba[1] * 100 if len(proba) > 1 else proba[0] * 100
                        else:
                            pred = model.predict(features)[0]
                            score = 80 if pred == 1 else 30

                        predictions[name] = score
                        weighted_score += score * self.model_weights.get(name, 0.5)
                    except Exception:
                        continue

                if predictions:
                    final_score = weighted_score
                    # الدمج مع التحليل القواعدي (50% rules + 50% ML) - ML غير موثوق ببيانات قليلة
                    rule_score = self._rule_based_score(analysis)["score"]
                    combined = final_score * 0.5 + rule_score * 0.5

                    return {
                        "score": round(min(max(combined, 0), 100), 1),
                        "ml_score": round(final_score, 1),
                        "rule_score": round(rule_score, 1),
                        "model_scores": predictions,
                        "confidence": self._calc_confidence(predictions),
                        "method": "ensemble"
                    }

            return self._rule_based_score(analysis)

        except Exception as e:
            logger.error(f"خطأ في التقييم: {e}")
            return self._rule_based_score(analysis)

    # ──────────────── Rule-Based Score ────────────────
    def _rule_based_score(self, analysis: dict) -> dict:
        """نظام نقاط قائم على القواعد (fallback)"""
        if not analysis:
            return {"score": 50, "confidence": 0, "method": "default"}

        score = 50
        rsi = analysis.get("rsi", 50)
        trend = analysis.get("trend", {})
        macd_cross = analysis.get("macd_cross", {})
        vol = analysis.get("volume_analysis", {})
        candle = analysis.get("candle_pattern", {})
        momentum = analysis.get("momentum_score", 50)
        position = analysis.get("price_position", {})

        # RSI Score (-20 to +20)
        if rsi < 30:
            score += 20
        elif rsi < 40:
            score += 12
        elif rsi < 50:
            score += 5
        elif rsi > 70:
            score -= 20
        elif rsi > 60:
            score -= 10

        # Trend (+15)
        if trend.get("direction") == "BULLISH":
            score += 15
        elif trend.get("direction") == "BEARISH":
            score -= 15

        # MACD Cross (+10)
        if macd_cross.get("signal") == "BULLISH_CROSS":
            score += 12
        elif macd_cross.get("signal") == "BEARISH_CROSS":
            score -= 12
        elif macd_cross.get("signal") == "BULLISH":
            score += 5

        # Volume (+8)
        if vol.get("is_high"):
            score += 8
        elif vol.get("is_increasing"):
            score += 5

        # Candle Pattern (+10)
        if candle.get("direction") == "BULLISH":
            score += candle.get("score", 0) / 10
        elif candle.get("direction") == "BEARISH":
            score -= candle.get("score", 0) / 10

        # Price Position (+10)
        pos_score = position.get("score", 0)
        score += pos_score / 2

        # Momentum
        score += (momentum - 50) / 5

        score = max(0, min(100, score))
        return {"score": round(score, 1), "confidence": 50, "method": "rules"}

    # ──────────────── Features ────────────────
    def _extract_features(self, analysis: dict):
        """استخراج الميزات للنماذج"""
        try:
            return [
                analysis.get("rsi", 50),
                analysis.get("macd", 0),
                analysis.get("macd_signal", 0),
                analysis.get("macd_histogram", 0),
                analysis.get("atr_pct", 0),
                analysis.get("volume_analysis", {}).get("ratio", 1),
                1 if analysis.get("trend", {}).get("direction") == "BULLISH" else
                -1 if analysis.get("trend", {}).get("direction") == "BEARISH" else 0,
                analysis.get("momentum_score", 50),
                analysis.get("price_position", {}).get("score", 0),
                analysis.get("candle_pattern", {}).get("score", 0) *
                (1 if analysis.get("candle_pattern", {}).get("direction") == "BULLISH" else -1),
                analysis.get("bb_upper", 0) - analysis.get("bb_lower", 0),
                1 if analysis.get("breakout", {}).get("breakout") else 0,
            ]
        except:
            return None

    def _prepare_training_data(self, ohlcv_data):
        """تحضير بيانات التدريب"""
        try:
            import pandas as pd
            df = pd.DataFrame(ohlcv_data, columns=["timestamp", "open", "high", "low", "close", "volume"])
            if len(df) < 100:
                return None, None

            from technical_analysis import TechnicalAnalyzer
            ta = TechnicalAnalyzer()
            features_list = []
            labels = []

            for i in range(50, len(df) - 5):
                subset = df.iloc[:i+1]
                close = subset["close"].values
                high = subset["high"].values
                low = subset["low"].values
                volume = subset["volume"].values
                opens = subset["open"].values

                rsi = ta.calc_rsi(close)
                sma50 = ta.calc_sma(close, 50)
                sma200 = ta.calc_sma(close, 200)
                macd, signal, hist = ta.calc_macd(close)
                atr = ta.calc_atr(high, low, close)
                vol_ratio = volume[-1] / np.mean(volume[-20:]) if np.mean(volume[-20:]) > 0 else 1
                trend_dir = 1 if close[-1] > sma50 else -1
                bb_u, bb_m, bb_l = ta.calc_bollinger(close)
                candle = ta.detect_candle_patterns(opens, high, low, close)
                momentum = ta.calc_momentum_score(close, rsi, macd, hist, volume)

                features = [
                    rsi, macd, signal, hist,
                    atr / close[-1] if close[-1] > 0 else 0,
                    vol_ratio, trend_dir, momentum, 0,
                    candle.get("score", 0) * (1 if candle.get("direction") == "BULLISH" else -1),
                    bb_u - bb_l,
                    0
                ]
                features_list.append(features)

                # Label: 1 = سعر ارتفع بعد 5 شموع، 0 = لا
                future_price = df.iloc[i+5]["close"]
                current_price = close[-1]
                label = 1 if future_price > current_price * 1.01 else 0  # ✅ 1% بدل 0.5% لتنبؤ أقوى
                labels.append(label)

            return np.array(features_list), np.array(labels)

        except Exception as e:
            logger.error(f"خطأ في تحضير البيانات: {e}")
            return None, None

    def _calc_confidence(self, predictions: dict) -> float:
        """حساب مستوى الثقة (مدى اتفاق النماذج)"""
        if len(predictions) < 2:
            return 50
        scores = list(predictions.values())
        std = np.std(scores)
        # كلما قل التباين بين النماذج كلما زادت الثقة
        confidence = max(0, 100 - std * 2)
        return round(confidence, 1)
