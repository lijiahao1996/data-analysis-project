# -*- coding: utf-8 -*-
"""
数据加载工具模块
支持 MySQL 数据库的读写操作（基于 SQLAlchemy Engine）
"""

import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DataLoader:
    """MySQL 数据加载器（基于 SQLAlchemy Engine）"""

    def __init__(self, engine):
        """
        Parameters
        ----------
        engine : sqlalchemy.engine.Engine
            SQLAlchemy 数据库引擎实例
        """
        self.engine = engine

    def query(self, sql: str, params=None) -> pd.DataFrame:
        """执行 SQL 查询，返回 DataFrame"""
        with self.engine.connect() as conn:
            return pd.read_sql_query(sql, conn, params=params)

    def load_table(self, table_name: str) -> pd.DataFrame:
        """加载整张表"""
        return self.query(f"SELECT * FROM {table_name}")

    def get_table_list(self) -> list:
        """获取所有表名"""
        from sqlalchemy import inspect
        inspector = inspect(self.engine)
        return inspector.get_table_names()

    def get_table_info(self, table_name: str) -> dict:
        """获取表的元数据"""
        from sqlalchemy import inspect, text
        inspector = inspect(self.engine)
        columns_info = inspector.get_columns(table_name)
        columns = [(col['name'], str(col['type'])) for col in columns_info]
        with self.engine.connect() as conn:
            row_count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
        return {
            "table_name": table_name,
            "row_count": row_count,
            "column_count": len(columns),
            "columns": columns
        }

    def save_dataframe(self, df: pd.DataFrame, table_name: str, if_exists='replace'):
        """将 DataFrame 保存到数据库表"""
        with self.engine.connect() as conn:
            df.to_sql(table_name, conn, if_exists=if_exists, index=False)
            logger.info(f"  保存 {len(df)} 行到表 {table_name}")
# -*- coding: utf-8 -*-
"""
数据加载工具模块
支持 SQLite 数据库的读写操作
"""

import sqlite3
import pandas as pd
from pathlib import Path
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class DataLoader:
    """SQLite 数据加载器"""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            logger.warning(f"数据库文件不存在: {self.db_path}")

    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器，自动关闭）"""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")  # 提升并发性能
        try:
            yield conn
        finally:
            conn.close()

    def query(self, sql: str, params=None) -> pd.DataFrame:
        """执行 SQL 查询，返回 DataFrame"""
        with self.get_connection() as conn:
            return pd.read_sql_query(sql, conn, params=params)

    def load_table(self, table_name: str) -> pd.DataFrame:
        """加载整张表"""
        return self.query(f"SELECT * FROM {table_name}")

    def get_table_list(self) -> list:
        """获取所有表名"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            return [row[0] for row in cursor.fetchall()]

    def get_table_info(self, table_name: str) -> dict:
        """获取表的元数据"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [(row[1], row[2]) for row in cursor.fetchall()]
            return {
                "table_name": table_name,
                "row_count": row_count,
                "column_count": len(columns),
                "columns": columns
            }

    def save_dataframe(self, df: pd.DataFrame, table_name: str, if_exists='replace'):
        """将 DataFrame 保存到 SQLite 表"""
        with self.get_connection() as conn:
            df.to_sql(table_name, conn, if_exists=if_exists, index=False)
            logger.info(f"✓ 保存 {len(df)} 行到表 {table_name}")
