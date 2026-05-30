# database.py
import sqlite3
import os
from datetime import datetime

DB_PATH = "enterprise_agent.db"

def get_db_connection():
    """建立数据库连接，返回标准的连接对象"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 允许通过列名访问数据，极具专业度
    return conn

def init_database():
    """初始化企业级结构化数据库表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. 建立高价值商业线索表（全面替代脆弱的 CSV）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS commercial_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact TEXT NOT NULL,
            intent TEXT,
            timestamp TEXT NOT NULL
        )
    """)
    
    # 2. 建立全量流式聊天记录表（为未来的长文本记忆与多租户隔离做铺垫）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()
    print("📋 [SQL 数据库状态] 标准关系型数据表初始化成功，企业级存储就绪。")

def save_lead_to_db(name, contact, intent):
    """持久化写入高价值商业线索"""
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute(
        "INSERT INTO commercial_leads (name, contact, intent, timestamp) VALUES (?, ?, ?, ?)",
        (name, contact, intent, current_time)
    )
    conn.commit()
    conn.close()
    print(f"🗄️ [SQL 持久化] 商业线索已成功写入 commercial_leads 表！客户: {name}")

def save_chat_message(session_id, role, content):
    """自动流式追踪并写入全量会话历史"""
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute(
        "INSERT INTO chat_records (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (session_id, role, content, current_time)
    )
    conn.commit()
    conn.close()

# 脚本被直接运行时自动激活初始化
if __name__ == "__main__":
    init_database()