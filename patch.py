import sys, time

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add latest_scan_results
old1 = "        self.is_running = False\n        self._stop_event = asyncio.Event()"
new1 = "        self.is_running = False\n        self._stop_event = asyncio.Event()\n        self.latest_scan_results = {}"
content = content.replace(old1, new1)

# 2. Expose get_scan_results
old2 = '            "set_running_state": self._set_running_state,\n        })'
new2 = '            "set_running_state": self._set_running_state,\n            "get_scan_results": lambda: getattr(self, "latest_scan_results", {})\n        })'
content = content.replace(old2, new2)

# 3. Update scan results
old3 = '                signal = self.strategy.evaluate(ohlcv, pair, self.ws_manager)'
new3 = '''                signal = self.strategy.evaluate(ohlcv, pair, self.ws_manager)
                
                self.latest_scan_results[pair] = {
                    "symbol": pair,
                    "buy_score": signal.get("buy_score", 0),
                    "ai_score": signal.get("ai_score", 0),
                    "regime": signal.get("regime", "UNKNOWN"),
                    "is_pump": signal.get("is_pump", False),
                    "is_steady": signal.get("is_steady", False),
                    "price": signal.get("price", 0),
                    "timestamp": time.time()
                }'''
content = content.replace(old3, new3)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied to main.py successfully")
