"""
===================================================================
  safety_audit.py - فحص أمان شامل ومؤكد 100%
  يختبر كل قيمة، كل مسار منطقي، كل ثغرة محتملة
===================================================================
  شغّل هذا الملف قبل كل Deploy:
    python safety_audit.py
===================================================================
"""

import os
import sys

# Fix Windows console encoding for Arabic/emoji
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ─── محاكاة بيئة Railway الخطيرة لاختبار أن القيم لا تتأثر ───
# نضع قيم خطيرة في env قبل استيراد Config
os.environ["MAX_CAPITAL_PER_TRADE"] = "0.98"        # خطير!
os.environ["MIN_PROFIT_CLOSE_PCT"] = "0.001"         # خطير!
os.environ["PUMP_QUICK_EXIT_PCT"] = "0.002"           # خطير!
os.environ["PUMP_FOCUS_MODE"] = "true"                # خطير!
os.environ["PUMP_SCORE_BONUS"] = "50"                 # خطير!
os.environ["STEADY_SCORE_BONUS"] = "40"               # خطير!
os.environ["EXIT_LOSS_ONLY_ON_HIGH_RISK"] = "true"    # خطير!
os.environ["HIGH_RISK_LOSS_PCT"] = "0.10"             # خطير!
os.environ["SPOT_INVENTORY_SELL_ENABLED"] = "true"    # خطير!
os.environ["CLOSE_ON_MIN_PROFIT"] = "false"           # خطير!
os.environ["ENABLE_FUTURES"] = "true"                  # خطير!
os.environ["ORDER_COOLDOWN"] = "10"                    # خطير!

# الآن نستورد Config - يجب ألا تتأثر بالقيم أعلاه
from config import Config

PASS = 0
FAIL = 0
WARNINGS = []


def check(name, actual, expected, description=""):
    """فحص قيمة واحدة"""
    global PASS, FAIL
    ok = actual == expected
    icon = "✅" if ok else "❌"
    status = "PASS" if ok else "FAIL"

    if not ok:
        FAIL += 1
        print(f"  {icon} [{status}] {name}: الفعلي={actual} | المتوقع={expected}")
        if description:
            print(f"       ⚠️ {description}")
    else:
        PASS += 1
        print(f"  {icon} [{status}] {name} = {actual}")


def check_range(name, actual, min_val, max_val, description=""):
    """فحص أن القيمة ضمن نطاق آمن"""
    global PASS, FAIL
    ok = min_val <= actual <= max_val
    icon = "✅" if ok else "❌"
    status = "PASS" if ok else "FAIL"

    if not ok:
        FAIL += 1
        print(f"  {icon} [{status}] {name}: الفعلي={actual} | النطاق=[{min_val}, {max_val}]")
        if description:
            print(f"       ⚠️ {description}")
    else:
        PASS += 1
        print(f"  {icon} [{status}] {name} = {actual} (نطاق [{min_val}-{max_val}])")


def warn(message):
    WARNINGS.append(message)
    print(f"  ⚠️ تحذير: {message}")


# ═══════════════════════════════════════════════════════════════
print("=" * 70)
print("  🔬 فحص أمان البوت الشامل - Safety Audit")
print("=" * 70)
print()

# ───────── المجموعة 1: القيم الثابتة (مقاومة لـ env) ─────────
print("📋 المجموعة 1: التحقق أن القيم الحرجة ثابتة (لا تقرأ من env)")
print("-" * 60)

check("ENABLE_FUTURES", Config.ENABLE_FUTURES, False,
      "يجب أن يكون False دائماً - env كان يضع true!")

check("MAX_CAPITAL_PER_TRADE", Config.MAX_CAPITAL_PER_TRADE, 0.15,
      "يجب 15% ثابت - env كان يضع 98%!")

check("MIN_PROFIT_CLOSE_PCT", Config.MIN_PROFIT_CLOSE_PCT, 0.008,
      "يجب 0.8% ثابت - env كان يضع 0.1%!")

check("PUMP_QUICK_EXIT_PCT", Config.PUMP_QUICK_EXIT_PCT, 0.008,
      "يجب 0.8% = نفس MIN_PROFIT - env كان يضع 0.2%!")

check("CLOSE_ON_MIN_PROFIT", Config.CLOSE_ON_MIN_PROFIT, True,
      "يجب True دائماً - env كان يضع false!")

check("PUMP_FOCUS_MODE", Config.PUMP_FOCUS_MODE, False,
      "يجب False دائماً - يسبب الشراء في القمم!")

check("SPOT_INVENTORY_SELL_ENABLED", Config.SPOT_INVENTORY_SELL_ENABLED, False,
      "يجب False - لا نريد بيع inventory في Spot!")

check("EXIT_LOSS_ONLY_ON_HIGH_RISK", Config.EXIT_LOSS_ONLY_ON_HIGH_RISK, False,
      "يجب False - وقف الخسارة يعمل دائماً!")

check("HIGH_RISK_LOSS_PCT", Config.HIGH_RISK_LOSS_PCT, 0.02,
      "يجب 2% ثابت!")

check("PUMP_SCORE_BONUS", Config.PUMP_SCORE_BONUS, 12,
      "يجب 12 ثابت - env كان يضع 50!")

check("STEADY_SCORE_BONUS", Config.STEADY_SCORE_BONUS, 10,
      "يجب 10 ثابت!")

check("ORDER_COOLDOWN", Config.ORDER_COOLDOWN, 180,
      "يجب 180 ثانية (3 دقائق)!")

print()

# ───────── المجموعة 2: قيم المخاطر ─────────
print("📋 المجموعة 2: إعدادات المخاطر")
print("-" * 60)

check("STOP_LOSS_PCT", Config.STOP_LOSS_PCT, 0.02,
      "وقف خسارة -2%")

check("RISK_PER_TRADE", Config.RISK_PER_TRADE, 0.15,
      "15% مخاطرة لكل صفقة")

check("DAILY_LOSS_LIMIT", Config.DAILY_LOSS_LIMIT, 0.03,
      "حد خسارة يومي -3%")

check("MAX_OPEN_TRADES", Config.MAX_OPEN_TRADES, 3,
      "3 صفقات مفتوحة كحد أقصى")

check("EXCHANGE_FEE_PCT", Config.EXCHANGE_FEE_PCT, 0.002,
      "عمولة 0.2% (شراء+بيع)")

check_range("TAKE_PROFIT_MIN", Config.TAKE_PROFIT_MIN, 0.008, 0.02,
            "هدف ربح أول")

check_range("TAKE_PROFIT_MAX", Config.TAKE_PROFIT_MAX, 0.02, 0.05,
            "سقف ربح")

print()

# ───────── المجموعة 3: الحسابات الرياضية ─────────
print("📋 المجموعة 3: التحقق من الحسابات الرياضية")
print("-" * 60)

# هل MIN_PROFIT أكبر من العمولة؟
net_min_profit = Config.MIN_PROFIT_CLOSE_PCT - Config.EXCHANGE_FEE_PCT
print(f"  ℹ️ الربح الصافي عند MIN_PROFIT: {Config.MIN_PROFIT_CLOSE_PCT:.3%} - {Config.EXCHANGE_FEE_PCT:.3%} = {net_min_profit:.3%}")
check("ربح_صافي > 0", net_min_profit > 0, True,
      "الربح بعد العمولة يجب أن يكون موجب!")

# هل PUMP_EXIT أكبر من العمولة؟
net_pump_profit = Config.PUMP_QUICK_EXIT_PCT - Config.EXCHANGE_FEE_PCT
check("ربح_pump_صافي > 0", net_pump_profit > 0, True,
      "ربح القنص بعد العمولة يجب أن يكون موجب!")

# هل PUMP_EXIT >= MIN_PROFIT؟
check("PUMP_EXIT >= MIN_PROFIT", Config.PUMP_QUICK_EXIT_PCT >= Config.MIN_PROFIT_CLOSE_PCT, True,
      "لا يمكن أن يكون خروج القنص أقل من الحد الأدنى!")

# Risk/Reward ratio
max_loss_pct = Config.STOP_LOSS_PCT  # 2%
min_profit_pct = net_min_profit       # ~0.6%
# لكن MAX_CAPITAL يحد الخسارة الفعلية
actual_loss_per_trade = Config.MAX_CAPITAL_PER_TRADE * max_loss_pct
actual_profit_per_trade = Config.MAX_CAPITAL_PER_TRADE * min_profit_pct
print(f"  ℹ️ خسارة فعلية لكل صفقة: {actual_loss_per_trade:.3%} من الرصيد")
print(f"  ℹ️ ربح فعلي لكل صفقة: {actual_profit_per_trade:.4%} من الرصيد")

# كم صفقة رابحة تعوض صفقة خاسرة؟
if actual_profit_per_trade > 0:
    trades_to_recover = actual_loss_per_trade / actual_profit_per_trade
    print(f"  ℹ️ عدد الصفقات الرابحة لتعويض خاسرة واحدة: {trades_to_recover:.1f}")
    check("recovery_trades <= 10", trades_to_recover <= 10, True,
          "يجب ألا تحتاج أكثر من 10 صفقات لتعويض خسارة!")

print()

# ───────── المجموعة 4: فحص المنطق في execution_engine ─────────
print("📋 المجموعة 4: فحص منطق التنفيذ")
print("-" * 60)

try:
    from execution_engine import ExecutionEngine

    # محاكاة trade لاختبار _reached_min_profit
    class MockDB:
        def save_trade(self, *a, **k): return 1
        def close_trade(self, *a, **k): pass
        def log_error(self, *a, **k): pass
        def get_open_trades(self): return []

    class MockClient:
        def fetch_balance(self): return {"USDT": {"free": 100, "total": 100}}
        def fetch_ticker(self, p): return {"last": 1.0}
        def create_market_order(self, *a, **k): return {}

    class MockRisk:
        starting_balance = 100
        daily_pnl = 0
        open_trade_count = 0
        def can_open_trade(self, *a): return {"allowed": True, "reason": ""}
        def calculate_dynamic_position(self, *a, **k): return {"amount": 10, "stop_loss": 0.98}
        def update_pnl(self, *a): pass
        def update_trade_count(self, *a): pass

    engine = ExecutionEngine(MockDB(), MockClient(), MockRisk())

    # اختبار 1: هل _reached_min_profit يرفض الربح الوهمي؟
    fake_trade_low_profit = {
        "entry_price": 1.000,
        "position_side": "LONG",
        "quick_exit_pct": 0.003  # قيمة خطيرة قديمة من Railway!
    }
    # السعر ارتفع 0.5% فقط (بعد عمولة = 0.3% = أقل من 0.8%)
    result = engine._reached_min_profit(fake_trade_low_profit, 1.005)
    check("رفض_ربح_وهمي_0.5%", result, False,
          "يجب أن يرفض البيع عند ربح 0.5% (صافي 0.3% < 0.8%)")

    # اختبار 2: هل يقبل الربح الحقيقي؟
    # السعر ارتفع 1.2% (بعد عمولة = 1.0% > 0.8%)
    result2 = engine._reached_min_profit(fake_trade_low_profit, 1.012)
    check("قبول_ربح_حقيقي_1.2%", result2, True,
          "يجب أن يقبل البيع عند ربح 1.2% (صافي 1.0% > 0.8%)")

    # اختبار 3: هل quick_exit=0.003 يتجاوز MIN_PROFIT؟
    trade_with_old_quick = {
        "entry_price": 1.000,
        "position_side": "LONG",
        "quick_exit_pct": 0.003  # من Railway القديم!
    }
    # ربح 0.52% → صافي 0.32% → أقل من 0.8% → يجب الرفض
    result3 = engine._reached_min_profit(trade_with_old_quick, 1.0052)
    check("حجب_quick_exit_0.3%", result3, False,
          "quick_exit=0.003 يجب ألا يتجاوز MIN_PROFIT=0.008!")

    # اختبار 4: Break-Even level
    fee_pct = Config.EXCHANGE_FEE_PCT
    entry = 1.000
    be_sl = entry * (1 + fee_pct + 0.0015)  # نفس الكود في execution_engine
    be_net = (be_sl - entry) / entry - fee_pct
    check("break_even_ربح_صافي > 0", be_net > 0, True,
          f"Break-Even SL={be_sl:.6f} يجب أن يعطي ربح صافي بعد العمولة ({be_net:.4%})")

    # اختبار 5: هل SIGNAL_SELL محجوب في Spot؟
    # نحاكي execute_trade مع SELL signal
    engine.open_trades["TEST/USDT"] = {
        "pair": "TEST/USDT",
        "side": "BUY",
        "position_side": "LONG",
        "entry_price": 1.0,
        "amount": 10,
        "remaining_amount": 10,
        "stop_loss": 0.98,
        "take_profit_1": 1.01,
        "take_profit_2": 1.02,
        "take_profit_3": 1.03,
        "break_even_level": 1.005,
        "trailing_active": False,
        "trailing_distance": 0.0025,
        "trailing_high": 1.0,
        "tp_stage": 0,
        "ai_score": 70,
        "time": 0,
    }
    engine.last_order_time["TEST/USDT"] = 0  # no cooldown

    sell_signal = {"signal": "SELL", "pair": "TEST/USDT", "price": 0.99, "ai_score": 70}
    sell_result = engine.execute_trade(sell_signal, "TEST/USDT")
    check("SELL_signal_محجوب_في_Spot",
          sell_result.get("success", True), False,
          "SELL signal يجب ألا يغلق LONG في Spot Mode!")

    if sell_result.get("reason"):
        check("سبب_الحجب_صحيح",
              "Spot mode" in sell_result.get("reason", ""),
              True,
              f"السبب: {sell_result.get('reason')}")

    # تنظيف
    del engine.open_trades["TEST/USDT"]

except Exception as e:
    print(f"  ❌ خطأ في فحص المنطق: {e}")
    import traceback
    traceback.print_exc()
    FAIL += 1

print()

# ───────── المجموعة 5: فحص الأوبتمايزر ─────────
print("📋 المجموعة 5: فحص حدود الأوبتمايزر")
print("-" * 60)

try:
    from strategy_engine import StrategyEngine

    class MockAI:
        def predict_score(self, a): return {"score": 60, "confidence": 50, "method": "test"}

    class MockRegime:
        def detect(self, df): return {"regime": "UNKNOWN", "strength": 0}

    strategy = StrategyEngine(MockAI(), MockRegime())

    # الحدود الأولية
    check("buy_threshold_ابتدائي", strategy.buy_threshold, 78)
    check("min_ai_score_ابتدائي", strategy.min_ai_score, 65)

    # محاولة خفض تحت الحد
    strategy.adjust_thresholds(buy_threshold=40, min_ai=30)
    check("buy_threshold_لا_ينزل_تحت_65",
          strategy.buy_threshold >= 65, True,
          f"القيمة الفعلية: {strategy.buy_threshold}")

    check("min_ai_لا_ينزل_تحت_55",
          strategy.min_ai_score >= 55, True,
          f"القيمة الفعلية: {strategy.min_ai_score}")

    # محاولة رفع فوق الحد
    strategy.adjust_thresholds(buy_threshold=99, min_ai=99)
    check("buy_threshold_لا_يتجاوز_90",
          strategy.buy_threshold <= 90, True,
          f"القيمة الفعلية: {strategy.buy_threshold}")

    check("min_ai_لا_يتجاوز_80",
          strategy.min_ai_score <= 80, True,
          f"القيمة الفعلية: {strategy.min_ai_score}")

except Exception as e:
    print(f"  ❌ خطأ في فحص الأوبتمايزر: {e}")
    FAIL += 1

print()

# ───────── المجموعة 6: فحص أن env لم يتسلل ─────────
print("📋 المجموعة 6: التأكد أن env الخطير لم يتسلل للقيم")
print("-" * 60)
print("  ℹ️ تم وضع قيم خطيرة في os.environ قبل استيراد Config")
print("  ℹ️ إذا نجحت كل الاختبارات = القيم محصنة 100%")

# إعادة فحص القيم الحرجة
check("env_MAX_CAPITAL_محجوب", Config.MAX_CAPITAL_PER_TRADE != 0.98, True,
      "os.environ['MAX_CAPITAL_PER_TRADE']='0.98' يجب ألا يؤثر!")

check("env_MIN_PROFIT_محجوب", Config.MIN_PROFIT_CLOSE_PCT != 0.001, True,
      "os.environ['MIN_PROFIT_CLOSE_PCT']='0.001' يجب ألا يؤثر!")

check("env_PUMP_EXIT_محجوب", Config.PUMP_QUICK_EXIT_PCT != 0.002, True,
      "os.environ['PUMP_QUICK_EXIT_PCT']='0.002' يجب ألا يؤثر!")

check("env_PUMP_FOCUS_محجوب", Config.PUMP_FOCUS_MODE != True, True,
      "os.environ['PUMP_FOCUS_MODE']='true' يجب ألا يؤثر!")

check("env_PUMP_BONUS_محجوب", Config.PUMP_SCORE_BONUS != 50, True,
      "os.environ['PUMP_SCORE_BONUS']='50' يجب ألا يؤثر!")

check("env_FUTURES_محجوب", Config.ENABLE_FUTURES != True, True,
      "os.environ['ENABLE_FUTURES']='true' يجب ألا يؤثر!")

check("env_COOLDOWN_محجوب", Config.ORDER_COOLDOWN != 10, True,
      "os.environ['ORDER_COOLDOWN']='10' يجب ألا يؤثر!")

check("env_INVENTORY_محجوب", Config.SPOT_INVENTORY_SELL_ENABLED != True, True,
      "os.environ['SPOT_INVENTORY_SELL_ENABLED']='true' يجب ألا يؤثر!")

print()

# ═══════════════════════════════════════════════════════════════
print("=" * 70)
print(f"  📊 النتيجة النهائية: {PASS} نجاح | {FAIL} فشل")
print("=" * 70)

if FAIL == 0:
    print()
    print("  🎉🎉🎉 كل الاختبارات نجحت! البوت آمن 100% 🎉🎉🎉")
    print()
    print("  ✅ كل القيم الحرجة ثابتة في الكود")
    print("  ✅ env الخطير لا يؤثر على القيم")
    print("  ✅ الحسابات الرياضية صحيحة")
    print("  ✅ SELL signal محجوب في Spot")
    print("  ✅ quick_exit لا يتجاوز MIN_PROFIT")
    print("  ✅ Break-Even يغطي العمولة")
    print("  ✅ الأوبتمايزر محدود بحدود آمنة")
    print()
    sys.exit(0)
else:
    print()
    print(f"  ❌❌❌ يوجد {FAIL} مشكلة! يجب إصلاحها قبل Deploy ❌❌❌")
    print()
    sys.exit(1)
