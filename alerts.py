"""
===================================================================
  alerts.py - نظام التنبيهات
  Alert/Notification System (Telegram Dispatcher)
===================================================================
"""

import logging
import asyncio
import aiohttp
from config import Config

logger = logging.getLogger("TradingBot.Alerts")


class AlertSystem:
    """نظام تنبيهات فوري عبر Telegram"""

    def __init__(self):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.enabled = bool(self.token and self.chat_id)
        if not self.enabled:
            logger.warning("⚠️ نظام التنبيهات غير مفعّل (Telegram غير مهيأ)")

    async def _send_telegram(self, message):
        """إرسال رسالة عبر Telegram API"""
        if not self.enabled:
            return
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        logger.warning(f"خطأ Telegram: {resp.status}")
        except Exception as e:
            logger.error(f"خطأ في إرسال التنبيه: {e}")

    def _send_sync(self, message):
        """إرسال رسالة بشكل متزامن"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._send_telegram(message))
            else:
                loop.run_until_complete(self._send_telegram(message))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self._send_telegram(message))

    # ──────────────── أنواع التنبيهات ────────────────
    def trade_opened(self, symbol, side, price, quantity, sl, tp,
                     ai_score=0, reasons=None):
        """تنبيه فتح صفقة"""
        emoji = "🟢" if side == "BUY" else "🔴"
        reasons_text = "\n".join(
            [f"  • {r}" for r in (reasons or [])]
        )

        msg = (
            f"{emoji} <b>صفقة جديدة - {side}</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📊 العملة: <code>{symbol}</code>\n"
            f"💰 السعر: <code>{float(price):.2f}</code>\n"
            f"📦 الكمية: <code>{float(quantity):.6f}</code>\n"
            f"🛡️ وقف الخسارة: <code>{float(sl):.2f}</code>\n"
            f"🎯 جني الأرباح: <code>{float(tp):.2f}</code>\n"
            f"🧠 AI Score: <code>{ai_score}</code>\n"
        )
        if reasons_text:
            msg += f"\n📋 الأسباب:\n{reasons_text}"

        self._send_sync(msg)
        logger.info(f"📤 تنبيه: صفقة {side} {symbol}")

    def trade_closed(self, symbol, side, entry_price, exit_price,
                     pnl, pnl_pct, reason=""):
        """تنبيه إغلاق صفقة"""
        emoji = "🟢" if pnl > 0 else "🔴"
        result = "ربح ✅" if pnl > 0 else "خسارة ❌"

        msg = (
            f"{emoji} <b>إغلاق صفقة - {result}</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📊 العملة: <code>{symbol}</code>\n"
            f"📈 سعر الدخول: <code>{float(entry_price):.2f}</code>\n"
            f"📉 سعر الخروج: <code>{float(exit_price):.2f}</code>\n"
            f"💵 الربح/الخسارة: <code>{float(pnl):+.2f} USDT ({float(pnl_pct):+.2f}%)</code>\n"
            f"📋 السبب: {reason}\n"
        )

        self._send_sync(msg)

    def daily_summary(self, stats):
        """ملخص يومي"""
        msg = (
            f"📊 <b>الملخص اليومي</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📈 إجمالي الصفقات: {stats.get('total', 0)}\n"
            f"✅ رابحة: {stats.get('wins', 0)}\n"
            f"❌ خاسرة: {stats.get('losses', 0)}\n"
            f"💰 صافي الربح: {stats.get('pnl', 0):+.2f} USDT\n"
            f"📊 نسبة الربح: {stats.get('win_rate', 0):.1f}%\n"
            f"💼 الرصيد: {stats.get('balance', 0):.2f} USDT\n"
        )
        self._send_sync(msg)

    def bot_started(self):
        """تنبيه تشغيل البوت"""
        msg = (
            "🤖 <b>بوت التداول يعمل الآن!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            f"📊 الأزواج: {', '.join(Config.TRADING_PAIRS)}\n"
            f"⏱️ الدورة: كل {Config.TRADING_INTERVAL} ثانية\n"
            f"🛡️ المخاطرة: {Config.RISK_PER_TRADE*100}% لكل صفقة\n"
            f"🧪 Sandbox: {'نعم' if Config.BINANCE_SANDBOX else 'لا'}\n"
        )
        self._send_sync(msg)

    def bot_stopped(self, reason=""):
        """تنبيه إيقاف البوت"""
        msg = f"🛑 <b>تم إيقاف البوت</b>\n"
        if reason:
            msg += f"السبب: {reason}"
        self._send_sync(msg)

    def error_alert(self, error_msg, module=""):
        """تنبيه خطأ"""
        msg = (
            f"⚠️ <b>خطأ في النظام</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📦 الوحدة: {module}\n"
            f"❌ الخطأ: <code>{error_msg[:500]}</code>"
        )
        self._send_sync(msg)

    def large_loss_alert(self, pnl, pnl_pct):
        """تنبيه خسارة كبيرة"""
        msg = (
            f"🚨 <b>تحذير: خسارة كبيرة!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💸 الخسارة: {pnl:+.2f} USDT ({pnl_pct:+.2f}%)\n"
            f"⚠️ يُنصح بمراجعة الإعدادات"
        )
        self._send_sync(msg)
