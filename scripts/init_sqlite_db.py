# -*- coding: utf-8 -*-
"""
SQLite 数据库初始化脚本
将 Kaggle Olist CSV 数据导入 SQLite 数据库
"""

import sqlite3
import pandas as pd
from pathlib import Path
import logging
import sys
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 路径配置
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "olist.db"
RAW_DATA_DIR = BASE_DIR / "data" / "raw"

# Olist 数据集 CSV 文件映射
CSV_TABLE_MAP = {
    "olist_orders_dataset.csv": "olist_orders",
    "olist_order_items_dataset.csv": "olist_order_items",
    "olist_customers_dataset.csv": "olist_customers",
    "olist_order_payments_dataset.csv": "olist_order_payments",
    "olist_order_reviews_dataset.csv": "olist_order_reviews",
    "olist_products_dataset.csv": "olist_products",
    "olist_sellers_dataset.csv": "olist_sellers",
    "olist_geolocation_dataset.csv": "olist_geolocation",
    "product_category_name_translation.csv": "category_translation",
}


def create_database():
    """初始化 SQLite 数据库"""
    start_time = time.time()

    # 检查数据目录
    if not RAW_DATA_DIR.exists():
        logger.error(f"原始数据目录不存在: {RAW_DATA_DIR}")
        logger.error("请先将 Olist CSV 文件解压到 data/raw/ 目录")
        sys.exit(1)

    # 检查 CSV 文件
    csv_files = list(RAW_DATA_DIR.glob("*.csv"))
    if not csv_files:
        logger.error(f"在 {RAW_DATA_DIR} 中未找到 CSV 文件")
        sys.exit(1)

    logger.info(f"找到 {len(csv_files)} 个 CSV 文件")

    # 如果数据库已存在，删除重建
    if DB_PATH.exists():
        logger.info(f"删除已有数据库: {DB_PATH}")
        DB_PATH.unlink()

    # 确保 data 目录存在
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 创建数据库连接
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    total_rows = 0

    for csv_filename, table_name in CSV_TABLE_MAP.items():
        csv_path = RAW_DATA_DIR / csv_filename
        if not csv_path.exists():
            logger.warning(f"⚠ 缺失文件: {csv_filename}，跳过")
            continue

        try:
            # 分块读取大文件（如 geolocation 约100万行）
            chunk_size = 50000
            rows_imported = 0

            for i, chunk in enumerate(pd.read_csv(
                str(csv_path), encoding='utf-8', chunksize=chunk_size
            )):
                if_exists = 'replace' if i == 0 else 'append'
                chunk.to_sql(table_name, conn, if_exists=if_exists, index=False)
                rows_imported += len(chunk)

            total_rows += rows_imported
            logger.info(f"✓ {table_name}: {rows_imported:,} 行导入成功")

        except Exception as e:
            logger.error(f"✗ 导入失败 {csv_filename}: {str(e)}")

    # 创建常用索引
    logger.info("创建索引...")
    index_statements = [
        "CREATE INDEX IF NOT EXISTS idx_orders_customer ON olist_orders(customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_orders_status ON olist_orders(order_status)",
        "CREATE INDEX IF NOT EXISTS idx_items_order ON olist_order_items(order_id)",
        "CREATE INDEX IF NOT EXISTS idx_items_product ON olist_order_items(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_customers_unique ON olist_customers(customer_unique_id)",
        "CREATE INDEX IF NOT EXISTS idx_payments_order ON olist_order_payments(order_id)",
        "CREATE INDEX IF NOT EXISTS idx_reviews_order ON olist_order_reviews(order_id)",
    ]
    for stmt in index_statements:
        try:
            conn.execute(stmt)
        except Exception as e:
            logger.warning(f"索引创建失败: {e}")

    conn.commit()
    conn.close()

    elapsed = time.time() - start_time
    logger.info(f"\n{'='*50}")
    logger.info(f"✓ 数据库初始化完成: {DB_PATH}")
    logger.info(f"  总导入行数: {total_rows:,}")
    logger.info(f"  数据库大小: {DB_PATH.stat().st_size / 1024 / 1024:.1f} MB")
    logger.info(f"  耗时: {elapsed:.1f} 秒")
    logger.info(f"{'='*50}")


if __name__ == "__main__":
    create_database()
