# database.py
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = "enterprise_agent.db"


@contextmanager
def get_db():
    """上下文管理器：自动管理连接生命周期，确保 commit/close"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 允许通过列名访问数据
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """初始化企业级结构化数据库表"""
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. 高价值商业线索表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS commercial_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT NOT NULL,
                intent TEXT,
                timestamp TEXT NOT NULL
            )
        """)

        # 2. 全量流式聊天记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

    print("📋 [SQL 数据库状态] 标准关系型数据表初始化成功，企业级存储就绪。")


def save_lead_to_db(name, contact, intent):
    """持久化写入高价值商业线索"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        conn.cursor().execute(
            "INSERT INTO commercial_leads (name, contact, intent, timestamp) VALUES (?, ?, ?, ?)",
            (name, contact, intent, current_time)
        )
    print(f"🗄️ [SQL 持久化] 商业线索已成功写入 commercial_leads 表！客户: {name}")


def save_chat_message(session_id, role, content):
    """自动流式追踪并写入全量会话历史"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        conn.cursor().execute(
            "INSERT INTO chat_records (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (session_id, role, content, current_time)
        )


def get_recent_messages(session_id, limit=20):
    """获取指定会话的最近 N 条消息（为未来历史恢复做准备）"""
    with get_db() as conn:
        rows = conn.cursor().execute(
            "SELECT role, content FROM chat_records WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit)
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


# 脚本被直接运行时自动激活初始化
if __name__ == "__main__":
    init_database()
