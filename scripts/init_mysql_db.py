# -*- coding: utf-8 -*-
"""
MySQL 数据库初始化脚本
将 CSV 数据导入 MySQL olist_ecommerce 数据库
"""

import sys
import time
import logging
from pathlib import Path

import pandas as pd

# 确保项目根目录在 sys.path 中，以便直接 import utils
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_connector import get_engine, load_config
from sqlalchemy import text

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 路径配置
BASE_DIR = Path(__file__).parent.parent

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
    """初始化 MySQL 数据库"""
    start_time = time.time()

    config = load_config()
    raw_dir = BASE_DIR / config['data']['raw_dir']

    # 检查数据目录
    if not raw_dir.exists():
        logger.error(f"原始数据目录不存在: {raw_dir}")
        logger.error("请先将 CSV 文件放入 data/rebranded/ 目录")
        sys.exit(1)

    # 检查 CSV 文件
    csv_files = list(raw_dir.glob("*.csv"))
    if not csv_files:
        logger.error(f"在 {raw_dir} 中未找到 CSV 文件")
        sys.exit(1)

    logger.info(f"找到 {len(csv_files)} 个 CSV 文件")

    engine = get_engine(config)

    total_rows = 0

    for csv_filename, table_name in CSV_TABLE_MAP.items():
        csv_path = raw_dir / csv_filename
        if not csv_path.exists():
            logger.warning(f"  缺失文件: {csv_filename}，跳过")
            continue

        try:
            # 分块读取大文件（如 geolocation 约100万行）
            chunk_size = 50000
            rows_imported = 0

            for i, chunk in enumerate(pd.read_csv(
                str(csv_path), encoding='utf-8', chunksize=chunk_size
            )):
                if_exists = 'replace' if i == 0 else 'append'
                chunk.to_sql(table_name, engine, if_exists=if_exists, index=False,
                             method='multi', chunksize=chunk_size)
                rows_imported += len(chunk)

            total_rows += rows_imported
            logger.info(f"  [OK] {table_name}: {rows_imported:,} 行导入成功")

        except Exception as e:
            logger.error(f"  [FAIL] 导入失败 {csv_filename}: {str(e)}")

    # 创建常用索引
    logger.info("创建索引...")
    index_statements = [
        "CREATE INDEX idx_orders_customer ON olist_orders(customer_id)",
        "CREATE INDEX idx_orders_status ON olist_orders(order_status)",
        "CREATE INDEX idx_items_order ON olist_order_items(order_id)",
        "CREATE INDEX idx_items_product ON olist_order_items(product_id)",
        "CREATE INDEX idx_customers_unique ON olist_customers(customer_unique_id)",
        "CREATE INDEX idx_payments_order ON olist_order_payments(order_id)",
        "CREATE INDEX idx_reviews_order ON olist_order_reviews(order_id)",
    ]
    with engine.connect() as conn:
        for stmt in index_statements:
            try:
                # 先检查索引是否存在（MySQL 语法）
                idx_name = stmt.split("INDEX ")[1].split(" ")[0]
                tbl_name = stmt.split("ON ")[1].split("(")[0]
                check = conn.execute(text(
                    f"SELECT COUNT(*) FROM information_schema.statistics "
                    f"WHERE table_schema = DATABASE() AND table_name = '{tbl_name}' "
                    f"AND index_name = '{idx_name}'"
                )).scalar()
                if check == 0:
                    conn.execute(text(stmt))
                    conn.commit()
                    logger.info(f"  索引已创建: {idx_name}")
                else:
                    logger.info(f"  索引已存在，跳过: {idx_name}")
            except Exception as e:
                logger.warning(f"索引创建失败: {e}")

    elapsed = time.time() - start_time
    logger.info(f"\n{'='*50}")
    logger.info(f"  MySQL 数据库初始化完成")
    logger.info(f"  数据库: olist_ecommerce")
    logger.info(f"  总导入行数: {total_rows:,}")
    logger.info(f"  耗时: {elapsed:.1f} 秒")
    logger.info(f"{'='*50}")


if __name__ == "__main__":
    create_database()
