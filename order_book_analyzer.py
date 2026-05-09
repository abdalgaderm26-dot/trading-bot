import logging
import numpy as np
from config import Config

logger = logging.getLogger("TradingBot.OrderBook")

class OrderBookAnalyzer:
    """محلل دفتر الأوامر (Market Depth & Whale Detection)"""
    
    def __init__(self, ws_manager):
        self.ws_manager = ws_manager
        self.wall_threshold_usd = 500_000  # جدار سيولة يعتبر حوت (نصف مليون دولار كحد أدنى)
        
    def analyze(self, pair):
        """تحليل دفتر الأوامر لزوج معين وإرجاع قوة الاتجاه أو الحوائط"""
        # في النسخة الحالية، نلتقط الـ Order Book اللحظي عبر REST لأن الـ Stream يحتاج تعديلات معقدة للمزامنة
        # سيتم دمج الـ Depth stream لاحقاً في V4، حالياً نأخذ لقطة سريعة لكل تقييم
        
        try:
            client = self.ws_manager._client
            # نجلب عمق 50 مستوى (حوالي 1-2% من السعر)
            order_book = client.fetch_order_book(pair, limit=50)
            
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            if not bids or not asks:
                return {"imbalance": 50, "whale_bid": False, "whale_ask": False, "score": 0}
                
            current_price = bids[0][0]
            
            # 1. حساب السيولة المتراكمة وحوائط الحيتان
            bid_walls = self._find_walls(bids, current_price, "BID")
            ask_walls = self._find_walls(asks, current_price, "ASK")
            
            # 2. حساب اختلال التوازن (Order Book Imbalance - OBI)
            # OBI = (V_bid - V_ask) / (V_bid + V_ask) -> من -1 إلى 1
            vol_bids = sum(amount for price, amount in bids)
            vol_asks = sum(amount for price, amount in asks)
            
            obi = (vol_bids - vol_asks) / (vol_bids + vol_asks) if (vol_bids + vol_asks) > 0 else 0
            
            # تحويل OBI إلى نقاط من 0 إلى 100 (50 هي نقطة التعادل)
            obi_score = 50 + (obi * 50)
            
            # 3. القرار النهائي لدفتر الأوامر
            final_score = 0
            
            # تأثير OBI
            if obi_score > 65:
                final_score += 10
            elif obi_score < 35:
                final_score -= 10
                
            # تأثير حوائط الحيتان
            if bid_walls:
                final_score += 15
                logger.debug(f"🐋 حوت شراء (BID Wall) مرصود لـ {pair} عند {bid_walls[0]['price']}")
            
            if ask_walls:
                final_score -= 15
                logger.debug(f"🐋 حوت بيع (ASK Wall) مرصود لـ {pair} عند {ask_walls[0]['price']}")
                
            return {
                "imbalance_score": obi_score,
                "whale_bid": len(bid_walls) > 0,
                "whale_ask": len(ask_walls) > 0,
                "bid_walls": bid_walls,
                "ask_walls": ask_walls,
                "score": final_score  # من -25 إلى +25 تضاف للاستراتيجية
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في تحليل دفتر أوامر {pair}: {e}")
            return {"imbalance_score": 50, "whale_bid": False, "whale_ask": False, "score": 0}

    def _find_walls(self, orders, current_price, side):
        """البحث عن أوامر ضخمة غير طبيعية في دفتر الأوامر"""
        walls = []
        for price, amount in orders:
            value_usd = price * amount
            
            # إذا كان حجم الطلب يساوى نصف مليون دولار على الأقل
            if value_usd >= self.wall_threshold_usd:
                # التأكد أن الجدار قريب من السعر (ضمن 2%)
                distance_pct = abs(price - current_price) / current_price
                if distance_pct <= 0.02:
                    walls.append({
                        "price": price,
                        "amount": amount,
                        "value_usd": value_usd,
                        "distance_pct": distance_pct * 100
                    })
        return walls
