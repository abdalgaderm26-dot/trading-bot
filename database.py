"""
===================================================================
  database.py - قاعدة بيانات MySQL لبوت التداول
  MySQL Database Manager for AI Trading Bot
===================================================================
"""

import logging
import mysql.connector
from mysql.connector import Error
from datetime import datetime, date
from config import Config

logger = logging.getLogger("TradingBot.Database")


class Database:
    """مدير قاعدة البيانات - تخزين الصفقات والأداء والأخطاء"""

    def __init__(self):
        self.config = {
            "host": Config.DB_HOST,
            "port": Config.DB_PORT,
            "user": Config.DB_USER,
            "password": Config.DB_PASSWORD,
        }
        self.db_name = Config.DB_NAME

    # ──────────────── الاتصال ────────────────
    def _get_connection(self):
        """إنشاء اتصال بقاعدة البيانات"""
        try:
            conn = mysql.connector.connect(
                **self.config,
                database=self.db_name,
                charset="utf8mb4",
                collation="utf8mb4_unicode_ci"
            )
            return conn
        except Error as e:
            logger.error(f"خطأ في الاتصال بقاعدة البيانات: {e}")
            raise

    # ──────────────── إنشاء قاعدة البيانات والجداول ────────────────
    def init_db(self):
        """إنشاء قاعدة البيانات والجداول إذا لم تكن موجودة"""
        try:
            # أولاً: إنشاء قاعدة البيانات
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{self.db_name}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            conn.close()

            # ثانياً: إنشاء الجداول
            conn = self._get_connection()
            cursor = conn.cursor()

            # جدول الصفقات
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    side ENUM('BUY', 'SELL') NOT NULL,
                    entry_price DECIMAL(20, 8) NOT NULL,
                    exit_price DECIMAL(20, 8) DEFAULT NULL,
                    quantity DECIMAL(20, 8) NOT NULL,
                    stop_loss DECIMAL(20, 8) DEFAULT NULL,
                    take_profit DECIMAL(20, 8) DEFAULT NULL,
                    pnl DECIMAL(20, 8) DEFAULT 0,
                    pnl_pct DECIMAL(10, 4) DEFAULT 0,
                    ai_score DECIMAL(5, 2) DEFAULT 0,
                    status ENUM('OPEN', 'CLOSED', 'CANCELLED') DEFAULT 'OPEN',
                    order_id VARCHAR(100) DEFAULT NULL,
                    close_reason VARCHAR(50) DEFAULT NULL,
                    opened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    closed_at DATETIME DEFAULT NULL,
                    INDEX idx_status (status),
                    INDEX idx_symbol (symbol),
                    INDEX idx_opened (opened_at)
                ) ENGINE=InnoDB
            """)

            # جدول الأداء اليومي
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_performance (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    trade_date DATE NOT NULL UNIQUE,
                    total_trades INT DEFAULT 0,
                    winning_trades INT DEFAULT 0,
                    losing_trades INT DEFAULT 0,
                    total_pnl DECIMAL(20, 8) DEFAULT 0,
                    win_rate DECIMAL(5, 2) DEFAULT 0,
                    max_drawdown DECIMAL(10, 4) DEFAULT 0,
                    starting_balance DECIMAL(20, 8) DEFAULT 0,
                    ending_balance DECIMAL(20, 8) DEFAULT 0,
                    INDEX idx_date (trade_date)
                ) ENGINE=InnoDB
            """)

            # جدول سجل الأخطاء
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS error_log (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    error_type VARCHAR(100) NOT NULL,
                    error_message TEXT NOT NULL,
                    module VARCHAR(100) DEFAULT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_created (created_at)
                ) ENGINE=InnoDB
            """)

            # جدول إعدادات البوت
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_settings (
                    setting_key VARCHAR(100) PRIMARY KEY,
                    setting_value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
            """)

            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ تم إنشاء قاعدة البيانات والجداول بنجاح")
            return True

        except Error as e:
            logger.error(f"❌ خطأ في إنشاء قاعدة البيانات: {e}")
            return False

    # ──────────────── عمليات الصفقات ────────────────
    def insert_trade(self, symbol, side, entry_price, quantity,
                     stop_loss=None, take_profit=None, ai_score=0, order_id=None):
        """إدراج صفقة جديدة"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades
                    (symbol, side, entry_price, quantity, stop_loss,
                     take_profit, ai_score, order_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (symbol, side, entry_price, quantity,
                  stop_loss, take_profit, ai_score, order_id))
            trade_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"📝 تم تسجيل صفقة جديدة #{trade_id}: {side} {symbol}")
            return trade_id
        except Error as e:
            logger.error(f"خطأ في إدراج الصفقة: {e}")
            self.log_error("DB_INSERT_TRADE", str(e), "database")
            return None

    def close_trade(self, trade_id, exit_price, pnl, pnl_pct, close_reason="MANUAL"):
        """إغلاق صفقة"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE trades SET
                    exit_price = %s,
                    pnl = %s,
                    pnl_pct = %s,
                    status = 'CLOSED',
                    close_reason = %s,
                    closed_at = NOW()
                WHERE id = %s
            """, (exit_price, pnl, pnl_pct, close_reason, trade_id))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"✅ تم إغلاق الصفقة #{trade_id} | PnL: {pnl}")
            return True
        except Error as e:
            logger.error(f"خطأ في إغلاق الصفقة: {e}")
            return False

    def get_open_trades(self, symbol=None):
        """جلب الصفقات المفتوحة"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            if symbol:
                cursor.execute(
                    "SELECT * FROM trades WHERE status='OPEN' AND symbol=%s "
                    "ORDER BY opened_at DESC", (symbol,)
                )
            else:
                cursor.execute(
                    "SELECT * FROM trades WHERE status='OPEN' "
                    "ORDER BY opened_at DESC"
                )
            trades = cursor.fetchall()
            cursor.close()
            conn.close()
            return trades
        except Error as e:
            logger.error(f"خطأ في جلب الصفقات المفتوحة: {e}")
            return []

    def get_trade_history(self, limit=50):
        """جلب سجل الصفقات"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM trades ORDER BY opened_at DESC LIMIT %s",
                (limit,)
            )
            trades = cursor.fetchall()
            cursor.close()
            conn.close()
            return trades
        except Error as e:
            logger.error(f"خطأ في جلب سجل الصفقات: {e}")
            return []

    def get_open_trades_count(self):
        """عدد الصفقات المفتوحة"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM trades WHERE status='OPEN'")
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return count
        except Error as e:
            return 0

    # ──────────────── الأداء ────────────────
    def update_daily_performance(self, starting_balance=0, ending_balance=0):
        """تحديث الأداء اليومي"""
        try:
            today = date.today()
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)

            # حساب إحصائيات اليوم
            cursor.execute("""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) AS losses,
                    COALESCE(SUM(pnl), 0) AS total_pnl
                FROM trades
                WHERE status = 'CLOSED'
                  AND DATE(closed_at) = %s
            """, (today,))
            stats = cursor.fetchone()

            total = stats["total"] or 0
            wins = stats["wins"] or 0
            losses = stats["losses"] or 0
            total_pnl = float(stats["total_pnl"] or 0)
            win_rate = (wins / total * 100) if total > 0 else 0

            cursor.execute("""
                INSERT INTO daily_performance
                    (trade_date, total_trades, winning_trades, losing_trades,
                     total_pnl, win_rate, starting_balance, ending_balance)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    total_trades = VALUES(total_trades),
                    winning_trades = VALUES(winning_trades),
                    losing_trades = VALUES(losing_trades),
                    total_pnl = VALUES(total_pnl),
                    win_rate = VALUES(win_rate),
                    ending_balance = VALUES(ending_balance)
            """, (today, total, wins, losses, total_pnl,
                  win_rate, starting_balance, ending_balance))

            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Error as e:
            logger.error(f"خطأ في تحديث الأداء: {e}")
            return False

    def get_daily_pnl(self):
        """الربح/الخسارة اليوم"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(SUM(pnl), 0)
                FROM trades
                WHERE status = 'CLOSED' AND DATE(closed_at) = CURDATE()
            """)
            pnl = float(cursor.fetchone()[0])
            cursor.close()
            conn.close()
            return pnl
        except Error as e:
            return 0.0

    def get_monthly_pnl(self):
        """الربح/الخسارة هذا الشهر"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(SUM(pnl), 0)
                FROM trades
                WHERE status = 'CLOSED'
                  AND YEAR(closed_at) = YEAR(CURDATE())
                  AND MONTH(closed_at) = MONTH(CURDATE())
            """)
            pnl = float(cursor.fetchone()[0])
            cursor.close()
            conn.close()
            return pnl
        except Error as e:
            return 0.0

    def get_total_stats(self):
        """إحصائيات إجمالية"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT
                    COUNT(*) AS total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) AS losses,
                    COALESCE(SUM(pnl), 0) AS total_pnl,
                    COALESCE(AVG(pnl), 0) AS avg_pnl,
                    COALESCE(MAX(pnl), 0) AS best_trade,
                    COALESCE(MIN(pnl), 0) AS worst_trade
                FROM trades WHERE status = 'CLOSED'
            """)
            stats = cursor.fetchone()
            total = stats["total_trades"] or 0
            wins = int(stats["wins"] or 0)
            stats["win_rate"] = round((wins / total * 100), 2) if total > 0 else 0
            cursor.close()
            conn.close()
            return stats
        except Error as e:
            logger.error(f"خطأ في جلب الإحصائيات: {e}")
            return {}

    def get_performance_history(self, days=30):
        """سجل الأداء لآخر N يوم"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM daily_performance
                ORDER BY trade_date DESC LIMIT %s
            """, (days,))
            history = cursor.fetchall()
            cursor.close()
            conn.close()
            return list(reversed(history))
        except Error as e:
            return []

    # ──────────────── سجل الأخطاء ────────────────
    def log_error(self, error_type, error_message, module=None):
        """تسجيل خطأ"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO error_log (error_type, error_message, module)
                VALUES (%s, %s, %s)
            """, (error_type, error_message, module))
            conn.commit()
            cursor.close()
            conn.close()
        except Error:
            pass  # تجنب حلقة لا نهائية

    def get_recent_errors(self, limit=20):
        """جلب آخر الأخطاء"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM error_log ORDER BY created_at DESC LIMIT %s",
                (limit,)
            )
            errors = cursor.fetchall()
            cursor.close()
            conn.close()
            return errors
        except Error as e:
            return []

    # ──────────────── الإعدادات ────────────────
    def get_setting(self, key, default=None):
        """قراءة إعداد"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT setting_value FROM bot_settings WHERE setting_key=%s",
                (key,)
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return row[0] if row else default
        except Error:
            return default

    def set_setting(self, key, value):
        """حفظ إعداد"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bot_settings (setting_key, setting_value)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
            """, (key, str(value)))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Error:
            return False

    # ──────────────── دوال إضافية v2.0 ────────────────
    def get_recent_trades(self, limit=50):
        """جلب آخر الصفقات المغلقة (للمحسّن التلقائي)"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM trades WHERE status='CLOSED' "
                "ORDER BY closed_at DESC LIMIT %s",
                (limit,)
            )
            trades = cursor.fetchall()
            cursor.close()
            conn.close()
            return trades
        except Error as e:
            logger.error(f"خطأ في جلب الصفقات الأخيرة: {e}")
            return []

    def save_trade(self, trade_data: dict):
        """حفظ صفقة (واجهة مبسطة)"""
        return self.insert_trade(
            symbol=trade_data.get("symbol", ""),
            side=trade_data.get("side", "BUY"),
            entry_price=trade_data.get("entry_price", 0),
            quantity=trade_data.get("amount", 0),
            stop_loss=trade_data.get("stop_loss"),
            take_profit=trade_data.get("take_profit"),
            ai_score=trade_data.get("ai_score", 0),
            order_id=trade_data.get("order_id")
        )

