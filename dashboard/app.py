"""
===================================================================
  dashboard/app.py - لوحة التحكم (FastAPI Backend)
  Dashboard Backend - REST API + Static File Server
===================================================================
"""

import os
import sys
import json
import logging
from datetime import datetime, date
from decimal import Decimal

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import asyncio

# إضافة المجلد الأب إلى المسار
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from database import Database

logger = logging.getLogger("TradingBot.Dashboard")

# ──────────────── إنشاء التطبيق ────────────────
app = FastAPI(title="AI Trading Bot Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# القوالب والملفات الثابتة
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# قاعدة البيانات
db = Database()

# مرجع لمكونات البوت (يتم تعيينها من main.py)
bot_ref = {
    "client": None,
    "is_running": False,
    "risk": None,
    "execution_engine": None
}


def set_bot_ref(refs: dict):
    """تعيين مرجع البوت"""
    bot_ref.update(refs)


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder للتعامل مع Decimal و date و datetime"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


def jsonify(data):
    """تحويل البيانات إلى JSON مع دعم Decimal"""
    return JSONResponse(
        content=json.loads(json.dumps(data, cls=DecimalEncoder))
    )


# ──────────────── الصفحة الرئيسية ────────────────
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """عرض لوحة التحكم"""
    return templates.TemplateResponse("index.html", {"request": request})


# ──────────────── API Endpoints ────────────────

@app.get("/api/status")
async def api_status():
    """حالة البوت"""
    risk_status = {}
    if bot_ref.get("risk"):
        risk_status = bot_ref["risk"].get_status()

    return {
        "is_running": bot_ref.get("is_running", False),
        "sandbox": Config.BINANCE_SANDBOX,
        "trading_pairs": Config.TRADING_PAIRS,
        "interval": Config.TRADING_INTERVAL,
        "risk": risk_status,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/balance")
async def api_balance():
    """الرصيد"""
    client = bot_ref.get("client")
    if not client:
        return {"balance": {}, "usdt": 0, "error": "client not connected"}

    try:
        balance = client.fetch_balance()
        usdt = client.get_usdt_balance()
        return {"balance": balance, "usdt": usdt}
    except Exception as e:
        logger.error(f"❌ api_balance error: {e}")
        return {"error": str(e), "balance": {}, "usdt": 0}


@app.get("/api/diag")
async def api_diag():
    """تشخيص - يكشف سبب عدم ظهور الرصيد"""
    import urllib.request
    result = {
        "enable_futures": getattr(Config, "ENABLE_FUTURES", "UNKNOWN"),
        "sandbox": getattr(Config, "BINANCE_SANDBOX", "UNKNOWN"),
        "api_key_set": bool(getattr(Config, "BINANCE_API_KEY", "")),
        "api_key_prefix": getattr(Config, "BINANCE_API_KEY", "")[:8] + "..." if getattr(Config, "BINANCE_API_KEY", "") else "EMPTY",
    }

    # IP العام
    try:
        result["public_ip"] = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode("utf-8")
    except:
        result["public_ip"] = "failed to get"

    # محاولة جلب الرصيد
    client = bot_ref.get("client")
    if client:
        result["client_connected"] = True
        try:
            balance = client.exchange.fetch_balance()
            usdt_free = float(balance.get("free", {}).get("USDT", 0) or 0)
            usdt_total = float(balance.get("total", {}).get("USDT", 0) or 0)
            ldusdt_free = float(balance.get("free", {}).get("LDUSDT", 0) or 0)
            ldusdt_total = float(balance.get("total", {}).get("LDUSDT", 0) or 0)
            
            result["usdt_free"] = usdt_free + ldusdt_free
            result["usdt_total"] = usdt_total + ldusdt_total
            result["balance_keys"] = list(balance.get("total", {}).keys())[:10]
            result["fetch_success"] = True
        except Exception as e:
            result["fetch_success"] = False
            result["fetch_error"] = str(e)
    else:
        result["client_connected"] = False

    return result


@app.get("/api/config_audit")
async def api_config_audit():
    """فحص القيم الثابتة - للتأكد أن Railway لا يتجاوزها"""
    return {
        "ENABLE_FUTURES": getattr(Config, "ENABLE_FUTURES", "?"),
        "MAX_CAPITAL_PER_TRADE": getattr(Config, "MAX_CAPITAL_PER_TRADE", "?"),
        "MIN_PROFIT_CLOSE_PCT": getattr(Config, "MIN_PROFIT_CLOSE_PCT", "?"),
        "PUMP_QUICK_EXIT_PCT": getattr(Config, "PUMP_QUICK_EXIT_PCT", "?"),
        "STOP_LOSS_PCT": getattr(Config, "STOP_LOSS_PCT", "?"),
        "PUMP_FOCUS_MODE": getattr(Config, "PUMP_FOCUS_MODE", "?"),
        "PUMP_SCORE_BONUS": getattr(Config, "PUMP_SCORE_BONUS", "?"),
        "STEADY_SCORE_BONUS": getattr(Config, "STEADY_SCORE_BONUS", "?"),
        "SPOT_INVENTORY_SELL_ENABLED": getattr(Config, "SPOT_INVENTORY_SELL_ENABLED", "?"),
        "EXIT_LOSS_ONLY_ON_HIGH_RISK": getattr(Config, "EXIT_LOSS_ONLY_ON_HIGH_RISK", "?"),
        "EXCHANGE_FEE_PCT": getattr(Config, "EXCHANGE_FEE_PCT", "?"),
        "ORDER_COOLDOWN": getattr(Config, "ORDER_COOLDOWN", "?"),
        "MAX_OPEN_TRADES": getattr(Config, "MAX_OPEN_TRADES", "?"),
        "DAILY_LOSS_LIMIT": getattr(Config, "DAILY_LOSS_LIMIT", "?"),
        "RISK_PER_TRADE": getattr(Config, "RISK_PER_TRADE", "?"),
        "CLOSE_ON_MIN_PROFIT": getattr(Config, "CLOSE_ON_MIN_PROFIT", "?"),
        "status": "ALL_HARDCODED ✅"
    }


@app.get("/api/trades/open")
async def api_open_trades():
    """الصفقات المفتوحة"""
    trades = db.get_open_trades()
    # إضافة السعر الحالي و PnL
    client = bot_ref.get("client")
    for t in trades:
        if client:
            try:
                price = client.fetch_current_price(t["symbol"])
                if price:
                    entry = float(t["entry_price"])
                    if t["side"] == "BUY":
                        t["current_pnl_pct"] = round((price - entry) / entry * 100, 2)
                    else:
                        t["current_pnl_pct"] = round((entry - price) / entry * 100, 2)
                    t["current_price"] = price
            except Exception:
                pass
    return {"trades": trades}


@app.get("/api/trades/history")
async def api_trade_history():
    """سجل الصفقات"""
    trades = db.get_trade_history(limit=100)
    return {"trades": trades}


@app.get("/api/performance")
async def api_performance():
    """الأداء"""
    daily = db.get_daily_pnl()
    monthly = db.get_monthly_pnl()
    stats = db.get_total_stats()
    history = db.get_performance_history(days=30)

    return {
        "daily_pnl": daily,
        "monthly_pnl": monthly,
        "total_stats": stats,
        "performance_history": history
    }


@app.get("/api/errors")
async def api_errors():
    """سجل الأخطاء"""
    errors = db.get_recent_errors(20)
    return {"errors": errors}


@app.post("/api/control/start")
async def api_start():
    """تشغيل البوت"""
    bot_ref["is_running"] = True
    risk = bot_ref.get("risk")
    if risk:
        risk.resume()
    return {"status": "started"}


@app.post("/api/control/stop")
async def api_stop():
    """إيقاف البوت"""
    bot_ref["is_running"] = False
    risk = bot_ref.get("risk")
    if risk:
        risk.force_halt("إيقاف من لوحة التحكم")
    return {"status": "stopped"}


@app.post("/api/trade/close")
async def api_close_trade(request: Request):
    """إغلاق صفقة يدوياً من لوحة التحكم"""
    try:
        data = await request.json()
        symbol = data.get("symbol")
        if not symbol:
            return JSONResponse({"status": "error", "message": "لم يتم توفير رمز العملة"}, status_code=400)
            
        engine = bot_ref.get("execution_engine")
        if not engine:
            logger.error("❌ api_close_trade: execution_engine is missing from bot_ref")
            return JSONResponse({"status": "error", "message": "محرك التنفيذ غير متصل"}, status_code=500)
            
        logger.info(f"📩 طلب إغلاق يدوي من لوحة التحكم لـ {symbol}")
        result = engine.force_close_trade(symbol)
        
        if result.get("success"):
            logger.info(f"✅ تم الإغلاق اليدوي بنجاح لـ {symbol}")
            return {"status": "success", "message": f"تم إغلاق {symbol} بنجاح"}
        else:
            error_msg = result.get("reason", "فشل الإغلاق")
            logger.warning(f"⚠️ فشل الإغلاق اليدوي لـ {symbol}: {error_msg}")
            # إضافة حالة الصفقة الحالية للسجل للمساعدة في التتبع
            open_pairs = list(engine.open_trades.keys())
            logger.info(f"📊 الصفقات المفتوحة حالياً في المحرك: {open_pairs}")
            return JSONResponse({"status": "error", "message": error_msg}, status_code=400)
            
    except Exception as e:
        logger.error(f"💥 خطأ حرج في api_close_trade: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/api/sell_asset/{asset}")
async def api_sell_asset(asset: str):
    """بيع عملة وتحويلها لـ USDT - يعمل من Railway مباشرة"""
    try:
        client = bot_ref.get("client")
        if not client:
            return JSONResponse({"status": "error", "message": "client not connected"}, status_code=500)

        asset = asset.upper().strip()
        if asset == "USDT":
            return {"status": "skip", "message": "already USDT"}

        symbol = f"{asset}/USDT"

        # جلب الرصيد
        balance = client.fetch_balance()
        free = float(balance.get(asset, {}).get("free", 0) or 0)
        if free <= 0:
            return {"status": "error", "message": f"no {asset} balance"}

        # جلب السعر
        ticker = client.fetch_ticker(symbol)
        price = float(ticker["last"]) if ticker else 0
        if price <= 0:
            return {"status": "error", "message": "invalid price"}

        value = free * price
        if value < 5:
            return {"status": "skip", "message": f"value too low: ${value:.2f}"}

        # تطبيع الكمية
        amount = free * 0.999
        try:
            amount = float(client.exchange.amount_to_precision(symbol, amount))
        except Exception:
            pass

        if amount <= 0:
            return {"status": "error", "message": "amount too small after precision"}

        # البيع
        order = client.create_market_order(symbol, "SELL", amount)
        if not order:
            return {"status": "error", "message": "sell order failed"}

        filled = float(order.get("filled", amount))
        avg = float(order.get("average", price))
        total = filled * avg

        logger.info(f"✅ Sold {filled} {asset} @ ${avg} = ${total:.2f} USDT")
        return {
            "status": "success",
            "asset": asset,
            "amount_sold": filled,
            "price": avg,
            "usdt_received": round(total, 2)
        }

    except Exception as e:
        logger.error(f"Sell {asset} error: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/api/cancel_all_orders")
async def api_cancel_all_orders():
    """إلغاء كل الأوامر المعلقة لتحرير الرصيد المحجوز"""
    try:
        client = bot_ref.get("client")
        if not client:
            return JSONResponse({"status": "error", "message": "client not connected"}, status_code=500)

        cancelled = []
        # جلب كل الأوامر المفتوحة
        try:
            open_orders = client.exchange.fetch_open_orders()
        except Exception:
            open_orders = []

        if not open_orders:
            # محاولة إلغاء من أزواج معروفة
            from config import Config
            for pair in Config.TRADING_PAIRS[:30]:
                try:
                    orders = client.exchange.fetch_open_orders(pair)
                    for o in orders:
                        try:
                            client.exchange.cancel_order(o["id"], pair)
                            cancelled.append({"pair": pair, "id": o["id"], "amount": o.get("amount")})
                        except Exception:
                            pass
                except Exception:
                    continue
        else:
            for o in open_orders:
                try:
                    sym = o.get("symbol", "")
                    client.exchange.cancel_order(o["id"], sym)
                    cancelled.append({"pair": sym, "id": o["id"], "amount": o.get("amount")})
                except Exception:
                    pass

        # جلب الرصيد الجديد
        try:
            bal = client.fetch_balance()
            new_free = float(bal.get("USDT", {}).get("free", 0) or 0)
            new_total = float(bal.get("USDT", {}).get("total", 0) or 0)
        except Exception:
            new_free = 0
            new_total = 0

        return {
            "status": "success",
            "cancelled_count": len(cancelled),
            "cancelled_orders": cancelled,
            "usdt_free_now": new_free,
            "usdt_total_now": new_total
        }

    except Exception as e:
        logger.error(f"Cancel all orders error: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ──────────────── WebSockets ────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """بث مباشر للبيانات للوحة التحكم اللحظية"""
    await websocket.accept()
    try:
        while True:
            # تجهيز البيانات اللحظية
            data = {
                "timestamp": datetime.now().isoformat(),
                "is_running": bot_ref.get("is_running", False)
            }
            
            # 1. بيانات الحساب والصلاحيات
            client = bot_ref.get("client")
            if client:
                try:
                    usdt = client.get_usdt_balance()
                    data["usdt"] = float(usdt)
                except Exception:
                    data["usdt"] = 0
            
            # 2. الصفقات المفتوحة مع الأرباح اللحظية
            trades = db.get_open_trades()
            active_trades = []
            for t in trades:
                if client:
                    try:
                        price = client.fetch_current_price(t["symbol"])
                        if price:
                            entry = float(t["entry_price"])
                            side = t["side"]
                            pnl_pct = ((price - entry) / entry * 100) if side == "BUY" else ((entry - price) / entry * 100)
                            
                            trade_data = dict(t)
                            trade_data["current_price"] = price
                            trade_data["current_pnl_pct"] = round(pnl_pct, 2)
                            active_trades.append(trade_data)
                    except Exception:
                        pass
                else:
                    active_trades.append(dict(t))
                    
            data["open_trades"] = active_trades
            
            # 3. بيانات المخاطرة و Kill Switch
            risk = bot_ref.get("risk")
            if risk:
                status = risk.get_status()
                data["risk"] = status
                data["kill_switch"] = getattr(risk, "kill_switch_active", False)

            # 4. Live Radar / Scan Results
            scan_func = bot_ref.get("get_scan_results")
            if scan_func:
                radar_data = scan_func()
                top_coins = sorted(radar_data.values(), key=lambda x: x.get("buy_score", 0), reverse=True)[:5]
                data["radar"] = top_coins

            # بث كـ JSON
            await websocket.send_text(json.dumps(data, cls=DecimalEncoder))
            await asyncio.sleep(1)  # تحديث كل ثانية
            
    except WebSocketDisconnect:
        logger.info("انفصل العميل عن WebSocket لوحة التحكم")
    except Exception as e:
        logger.error(f"خطأ في WebSocket لوحة التحكم: {e}")

# ──────────────── تشغيل مستقل ────────────────
if __name__ == "__main__":
    import uvicorn
    db.init_db()
    uvicorn.run(app, host="0.0.0.0", port=8000)
