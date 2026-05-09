"""
===================================================================
  strategy_optimizer.py - محسّن الاستراتيجية التلقائي
  Auto Strategy Optimizer - Self-tuning based on performance
===================================================================
  كل 24 ساعة يراجع الأداء ويعدّل المعاملات تلقائياً
===================================================================
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger("TradingBot.Optimizer")


class StrategyOptimizer:
    """محسّن الاستراتيجية التلقائي"""

    def __init__(self, db, strategy_engine):
        self.db = db
        self.strategy = strategy_engine
        self.last_optimization = None
        self.optimization_interval = 24 * 3600  # كل 24 ساعة

    def should_optimize(self) -> bool:
        """هل حان وقت التحسين؟"""
        if self.last_optimization is None:
            return True
        elapsed = (datetime.now() - self.last_optimization).total_seconds()
        return elapsed >= self.optimization_interval

    def optimize(self):
        """تحسين المعاملات بناءً على الأداء"""
        try:
            if not self.should_optimize():
                return

            logger.info("🔧 بدء تحسين الاستراتيجية...")

            # جلب بيانات آخر 7 أيام
            stats = self._get_recent_stats(days=7)
            if not stats or stats["total_trades"] < 5:
                logger.info("⚠️ صفقات غير كافية للتحسين (أقل من 5)")
                self.last_optimization = datetime.now()
                return

            win_rate = stats["win_rate"]
            avg_pnl = stats["avg_pnl"]
            total_trades = stats["total_trades"]

            logger.info(
                f"📊 إحصائيات 7 أيام: صفقات={total_trades} | "
                f"نسبة ربح={win_rate:.1f}% | متوسط PnL={avg_pnl:+.2f}"
            )

            # ──── تعديل الحدود ────
            current_buy = self.strategy.buy_threshold
            current_ai = self.strategy.min_ai_score

            if win_rate < 40:
                # أداء ضعيف → شدّد الشروط
                new_buy = min(current_buy + 5, 80)
                new_ai = min(current_ai + 5, 75)
                logger.info(f"📈 تشديد الشروط: شراء {current_buy}→{new_buy} | AI {current_ai}→{new_ai}")
                self.strategy.adjust_thresholds(buy_threshold=new_buy, min_ai=new_ai)

            elif win_rate > 65 and total_trades < 3:
                # أداء جيد لكن صفقات قليلة → رخّي الشروط قليلاً
                new_buy = max(current_buy - 3, 55)
                new_ai = max(current_ai - 3, 50)
                logger.info(f"📉 ترخية الشروط: شراء {current_buy}→{new_buy} | AI {current_ai}→{new_ai}")
                self.strategy.adjust_thresholds(buy_threshold=new_buy, min_ai=new_ai)

            elif win_rate > 60:
                # أداء جيد → حافظ على الإعدادات
                logger.info("✅ الأداء جيد - إبقاء الإعدادات الحالية")

            self.last_optimization = datetime.now()
            logger.info("✅ اكتمل تحسين الاستراتيجية")

        except Exception as e:
            logger.error(f"خطأ في التحسين: {e}")

    def _get_recent_stats(self, days=7) -> dict:
        """جلب إحصائيات الأيام الأخيرة"""
        try:
            trades = self.db.get_recent_trades(limit=50)
            if not trades:
                return None

            # فلترة آخر N أيام
            cutoff = datetime.now() - timedelta(days=days)
            recent = []
            for t in trades:
                if t.get("status") == "CLOSED":
                    recent.append(t)

            if not recent:
                return None

            total = len(recent)
            wins = sum(1 for t in recent if float(t.get("pnl", 0)) > 0)
            total_pnl = sum(float(t.get("pnl", 0)) for t in recent)

            return {
                "total_trades": total,
                "wins": wins,
                "losses": total - wins,
                "win_rate": (wins / total * 100) if total > 0 else 0,
                "avg_pnl": total_pnl / total if total > 0 else 0,
                "total_pnl": total_pnl
            }

        except Exception as e:
            logger.error(f"خطأ في جلب الإحصائيات: {e}")
            return None
