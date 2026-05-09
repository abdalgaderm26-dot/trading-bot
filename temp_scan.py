import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from binance_client import BinanceClient
from technical_analysis import TechnicalAnalyzer
from ai_model import AIModel
from strategy_engine import StrategyEngine
from market_regime import MarketRegime

config = Config()
client = BinanceClient()
analyzer = TechnicalAnalyzer()
ai_model = AIModel()
regime = MarketRegime()
strategy = StrategyEngine(analyzer, ai_model, regime)

best_coin = None
best_score = 0
best_ai = 0
results = []

print("Scanning top coins...")
for pair in config.TRADING_PAIRS:
    try:
        ohlcv = client.fetch_ohlcv(pair, timeframe="15m", limit=100)
        if not ohlcv or len(ohlcv) < 50:
            continue
        
        analysis = analyzer.analyze(ohlcv, pair)
        if not analysis:
            continue
            
        ai_result = ai_model.predict_score(analysis)
        ai_score = ai_result.get("score", 50)
        
        df = analysis.get("df")
        market_regime = regime.detect(df) if (df is not None and not df.empty) else "UNKNOWN"
        
        buy_score, sell_score, details, pump_ctx = strategy._calculate_scores(
            analysis, ai_result, None, market_regime, None
        )
        
        results.append({
            "pair": pair,
            "buy_score": buy_score,
            "ai": ai_score,
            "rsi": analysis.get("rsi", 50),
            "trend": analysis.get("trend", {}).get("status", "UNKNOWN"),
            "regime": market_regime
        })
        
        if buy_score > best_score:
            best_score = buy_score
            best_ai = ai_score
            best_coin = pair
    except Exception as e:
        pass

results.sort(key=lambda x: (x["buy_score"], x["ai"]), reverse=True)
print("\nTop 5 Candidates:")
for r in results[:5]:
    print(f"{r['pair']} -> Strategy: {r['buy_score']} | AI: {r['ai']:.1f}% | RSI: {r['rsi']:.1f} | Trend: {r['trend']} | Regime: {r['regime']}")

print(f"\nWinner: {best_coin} with Strategy: {best_score} and AI: {best_ai:.1f}%")
