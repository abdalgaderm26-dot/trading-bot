"""
===================================================================
  telegram_bot.py - بوت التحكم عبر Telegram
  Telegram Bot for Real-Time Control
===================================================================
"""

import logging
from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, ContextTypes
)
from config import Config

logger = logging.getLogger("TradingBot.Telegram")

# مرجع عام لمكونات البوت (يتم تعيينها من main.py)
bot_components = {
    "client": None,
    "db": None,
    "risk": None,
    "execution": None,
    "strategy": None,
    "analyzer": None,
    "ai": None,
    "alerts": None,
    "is_running": False
}


def set_components(components: dict):
    """تعيين مكونات البوت (يُستدعى من main.py)"""
    bot_components.update(components)


def _get_is_running() -> bool:
    getter = bot_components.get("get_running_state")
    if callable(getter):
        try:
            return bool(getter())
        except Exception:
            pass
    return bool(bot_components.get("is_running", False))


def _set_is_running(value: bool):
    running = bool(value)
    setter = bot_components.get("set_running_state")
    if callable(setter):
        try:
            setter(running)
        except Exception:
            bot_components["is_running"] = running
            return
    bot_components["is_running"] = running


# ──────────────── الأوامر ────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start - تشغيل البوت"""
    _set_is_running(True)
    risk = bot_components.get("risk")
    if risk:
        risk.resume()
    await update.message.reply_html(
        "🤖 <b>تم تشغيل بوت التداول!</b>\n\n"
        "📊 الأزواج: " + ", ".join(Config.TRADING_PAIRS) + "\n"
        "⏱️ الدورة: كل " + str(Config.TRADING_INTERVAL) + " ثانية\n\n"
        "📋 الأوامر المتاحة:\n"
        "/stop - إيقاف البوت\n"
        "/status - حالة البوت\n"
        "/balance - الرصيد\n"
        "/profit - الأرباح\n"
        "/trades - الصفقات المفتوحة\n"
        "/history - سجل الصفقات\n"
        "/buy - شراء يدوي\n"
        "/sell - بيع يدوي\n"
        "/stats - إحصائيات شاملة"
    )
    logger.info("▶️ البوت تم تشغيله عبر Telegram")


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stop - إيقاف البوت"""
    _set_is_running(False)
    risk = bot_components.get("risk")
    if risk:
        risk.force_halt("إيقاف عبر Telegram")

    await update.message.reply_html(
        "🛑 <b>تم إيقاف البوت</b>\n"
        "لن يتم تنفيذ صفقات جديدة.\n"
        "استخدم /start لإعادة التشغيل."
    )
    logger.info("⏹️ البوت تم إيقافه عبر Telegram")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/status - حالة البوت"""
    is_running = _get_is_running()
    risk = bot_components.get("risk")
    db = bot_components.get("db")

    status_emoji = "🟢" if is_running else "🔴"
    status_text = "يعمل" if is_running else "متوقف"

    msg = (
        f"{status_emoji} <b>حالة البوت: {status_text}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
    )

    if risk:
        risk_status = risk.get_status()
        is_halted = risk_status.get("auto_halt", risk_status.get("is_halted", False))
        msg += (
            f"🛡️ إدارة المخاطر:\n"
            f"  • متوقف: {'نعم ⛔' if is_halted else 'لا ✅'}\n"
        )
        if is_halted:
            msg += f"  • السبب: {risk_status['halt_reason']}\n"

    if db:
        open_count = db.get_open_trades_count()
        msg += f"\n📊 الصفقات المفتوحة: {open_count}/{Config.MAX_OPEN_TRADES}\n"
        msg += f"🧪 Sandbox: {'نعم' if Config.BINANCE_SANDBOX else 'لا'}\n"

    await update.message.reply_html(msg)


async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/balance - عرض الرصيد"""
    client = bot_components.get("client")
    if not client:
        await update.message.reply_text("❌ العميل غير متصل")
        return

    try:
        balance = client.fetch_balance()
        if not balance:
            await update.message.reply_text("📭 لا يوجد رصيد")
            return

        msg = "💰 <b>الرصيد الحالي</b>\n━━━━━━━━━━━━━━━\n"
        for currency, data in balance.items():
            total = data.get("total", 0)
            free = data.get("free", 0)
            if total > 0:
                msg += (
                    f"  <b>{currency}</b>: "
                    f"{total:.4f} (متاح: {free:.4f})\n"
                )

        await update.message.reply_html(msg)
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


async def cmd_profit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/profit - عرض الأرباح"""
    db = bot_components.get("db")
    if not db:
        await update.message.reply_text("❌ قاعدة البيانات غير متصلة")
        return

    daily = db.get_daily_pnl()
    monthly = db.get_monthly_pnl()
    stats = db.get_total_stats()

    daily_emoji = "🟢" if daily >= 0 else "🔴"
    monthly_emoji = "🟢" if monthly >= 0 else "🔴"

    msg = (
        f"📈 <b>الأرباح والخسائر</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{daily_emoji} اليوم: <code>{daily:+.2f} USDT</code>\n"
        f"{monthly_emoji} هذا الشهر: <code>{monthly:+.2f} USDT</code>\n"
        f"💰 الإجمالي: <code>{float(stats.get('total_pnl', 0)):+.2f} USDT</code>\n"
        f"\n📊 <b>الإحصائيات</b>\n"
        f"  • إجمالي: {stats.get('total_trades', 0)} صفقة\n"
        f"  • الربح: {stats.get('win_rate', 0)}%\n"
        f"  • أفضل صفقة: {float(stats.get('best_trade', 0)):+.2f}\n"
        f"  • أسوأ صفقة: {float(stats.get('worst_trade', 0)):+.2f}\n"
    )
    await update.message.reply_html(msg)


async def cmd_trades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/trades - الصفقات المفتوحة"""
    db = bot_components.get("db")
    client = bot_components.get("client")
    if not db:
        await update.message.reply_text("❌ قاعدة البيانات غير متصلة")
        return

    trades = db.get_open_trades()
    if not trades:
        await update.message.reply_text("📭 لا توجد صفقات مفتوحة")
        return

    msg = f"📋 <b>الصفقات المفتوحة ({len(trades)})</b>\n━━━━━━━━━━━━━━━\n"

    for t in trades:
        price = None
        if client:
            price = client.fetch_current_price(t["symbol"])

        entry = float(t["entry_price"])
        pnl_text = ""

        if price:
            if t["side"] == "BUY":
                pnl = (price - entry) / entry * 100
            else:
                pnl = (entry - price) / entry * 100
            pnl_emoji = "🟢" if pnl >= 0 else "🔴"
            pnl_text = f" | {pnl_emoji} {pnl:+.2f}%"

        emoji = "🟢" if t["side"] == "BUY" else "🔴"
        msg += (
            f"\n{emoji} #{t['id']} | {t['side']} {t['symbol']}\n"
            f"  💰 دخول: {entry:.2f}{pnl_text}\n"
            f"  🛡️ SL: {float(t['stop_loss'] or 0):.2f} | "
            f"🎯 TP: {float(t['take_profit'] or 0):.2f}\n"
        )

    await update.message.reply_html(msg)


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/history - سجل آخر 10 صفقات"""
    db = bot_components.get("db")
    if not db:
        await update.message.reply_text("❌ قاعدة البيانات غير متصلة")
        return

    trades = db.get_trade_history(limit=10)
    if not trades:
        await update.message.reply_text("📭 لا يوجد سجل")
        return

    msg = "📜 <b>آخر 10 صفقات</b>\n━━━━━━━━━━━━━━━\n"

    for t in trades:
        pnl = float(t.get("pnl", 0) or 0)
        emoji = "🟢" if pnl >= 0 else "🔴"
        status = t["status"]
        msg += (
            f"{emoji} #{t['id']} | {t['side']} {t['symbol']} | "
            f"{status} | PnL: {pnl:+.2f}\n"
        )

    await update.message.reply_html(msg)


async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/buy [symbol] - شراء يدوي"""
    if not _get_is_running():
        await update.message.reply_text("❌ البوت متوقف. استخدم /start أولاً")
        return

    execution = bot_components.get("execution")
    if not execution:
        await update.message.reply_text("❌ محرك التنفيذ غير جاهز")
        return

    # قراءة العملة من الأمر
    args = context.args
    symbol = args[0] if args else Config.DEFAULT_PAIR
    if "/" not in symbol:
        symbol = f"{symbol.upper()}/USDT"

    await update.message.reply_text(f"⏳ جارٍ تنفيذ شراء {symbol}...")

    result = execution.manual_buy(symbol)
    if result["success"]:
        await update.message.reply_html(
            f"✅ <b>تم الشراء!</b>\n"
            f"📊 {symbol} @ {result.get('price', 0):.2f}\n"
            f"📦 الكمية: {result.get('quantity', 0):.6f}"
        )
    else:
        await update.message.reply_text(f"❌ فشل: {result.get('reason')}")


async def cmd_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/sell [symbol] - بيع يدوي"""
    execution = bot_components.get("execution")
    if not execution:
        await update.message.reply_text("❌ محرك التنفيذ غير جاهز")
        return

    args = context.args
    symbol = args[0] if args else Config.DEFAULT_PAIR
    if "/" not in symbol:
        symbol = f"{symbol.upper()}/USDT"

    await update.message.reply_text(f"⏳ جارٍ إغلاق صفقات {symbol}...")

    result = execution.manual_sell(symbol)
    if result["success"]:
        await update.message.reply_html(
            f"✅ <b>تم الإغلاق!</b>\n"
            f"📊 أُغلقت {result.get('closed', 0)} صفقة"
        )
    else:
        await update.message.reply_text(f"❌ {result.get('reason')}")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stats - إحصائيات شاملة"""
    db = bot_components.get("db")
    client = bot_components.get("client")

    if not db:
        await update.message.reply_text("❌ قاعدة البيانات غير متصلة")
        return

    stats = db.get_total_stats()
    usdt = client.get_usdt_balance() if client else 0

    msg = (
        f"📊 <b>إحصائيات شاملة</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💼 الرصيد: {usdt:.2f} USDT\n"
        f"📈 إجمالي الصفقات: {stats.get('total_trades', 0)}\n"
        f"✅ رابحة: {int(stats.get('wins', 0))}\n"
        f"❌ خاسرة: {int(stats.get('losses', 0))}\n"
        f"📊 نسبة الربح: {stats.get('win_rate', 0)}%\n"
        f"💰 إجمالي PnL: {float(stats.get('total_pnl', 0)):+.2f} USDT\n"
        f"📈 أفضل صفقة: {float(stats.get('best_trade', 0)):+.2f}\n"
        f"📉 أسوأ صفقة: {float(stats.get('worst_trade', 0)):+.2f}\n"
        f"📊 متوسط PnL: {float(stats.get('avg_pnl', 0)):+.4f}\n"
    )
    await update.message.reply_html(msg)


# ──────────────── إنشاء وتشغيل البوت ────────────────

def create_telegram_app():
    """إنشاء تطبيق Telegram"""
    if not Config.TELEGRAM_BOT_TOKEN:
        logger.warning("⚠️ TELEGRAM_BOT_TOKEN غير محدد - بوت Telegram لن يعمل")
        return None

    app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

    # تسجيل الأوامر
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("balance", cmd_balance))
    app.add_handler(CommandHandler("profit", cmd_profit))
    app.add_handler(CommandHandler("trades", cmd_trades))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("buy", cmd_buy))
    app.add_handler(CommandHandler("sell", cmd_sell))
    app.add_handler(CommandHandler("stats", cmd_stats))

    logger.info("🤖 تم إنشاء بوت Telegram")
    return app
