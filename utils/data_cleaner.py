# -*- coding: utf-8 -*-
"""
数据清洗模块
职责：过滤、标准化、缺失值处理

清洗流程：
1. 从 MySQL 读取原始订单数据
2. 只保留 delivered 状态的订单
3. 解析时间字段为 datetime 格式
4. 删除关键字段缺失的行
5. 关联 customers 表获取 customer_unique_id
6. 计算物流衍生字段（延迟天数、配送天数）
7. 输出 parquet 格式清洗结果
"""

import logging
from pathlib import Path

import pandas as pd

from utils.db_connector import get_engine, load_config


class DataCleaner:
    """
    Olist 电商数据集清洗器

    Parameters
    ----------
    config : dict
        项目配置字典，需包含 data.processed_dir 等路径配置
    engine : sqlalchemy.engine.Engine, optional
        SQLAlchemy 数据库引擎；若未提供则从 config 自动创建
    """

    # 需要解析为 datetime 的时间字段
    DATETIME_COLS = [
        'order_purchase_timestamp',
        'order_approved_at',
        'order_delivered_carrier_date',
        'order_delivered_customer_date',
        'order_estimated_delivery_date',
    ]

    # 关键字段：若为空则直接删除该行
    CRITICAL_COLS = ['customer_id', 'order_id', 'order_purchase_timestamp']

    def __init__(self, config: dict, engine=None):
        self.config = config
        self.engine = engine or get_engine(config)
        self.logger = logging.getLogger(self.__class__.__name__)

        # 项目根目录（通过 config 解析）
        self.project_root = Path(__file__).parent.parent
        # 输出目录（相对项目根解析）
        self.output_dir = self.project_root / config['data']['processed_dir']
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> pd.DataFrame:
        """
        执行完整数据清洗流程

        Returns
        -------
        pd.DataFrame
            清洗后的订单数据
        """
        self.logger.info("=" * 60)
        self.logger.info("开始数据清洗流程")
        self.logger.info("=" * 60)

        # Step 1: 读取原始数据
        df = self._load_raw_data()
        raw_count = len(df)
        self.logger.info(f"[读取] 原始订单数: {raw_count:,}")

        # Step 2: 过滤 - 只保留已送达订单
        df = self._filter_delivered(df)
        after_filter_count = len(df)
        self.logger.info(f"[过滤] 保留 delivered 订单: {after_filter_count:,} "
                         f"(过滤掉 {raw_count - after_filter_count:,} 条)")

        # Step 3: 解析时间字段
        df = self._parse_datetime(df)

        # Step 4: 删除关键字段为空的行
        before_drop = len(df)
        df = self._drop_missing_critical(df)
        after_drop = len(df)
        self.logger.info(f"[缺失值] 删除关键字段为空的行: {before_drop - after_drop:,} 条")

        # Step 5: 关联 customers 表获取 customer_unique_id
        df = self._join_customers(df)
        self.logger.info(f"[关联] 成功关联 customer_unique_id，唯一用户数: "
                         f"{df['customer_unique_id'].nunique():,}")

        # Step 6: 计算物流衍生字段
        df = self._compute_delivery_features(df)

        # Step 7: 保存结果
        output_path = self.output_dir / 'orders_clean.parquet'
        df.to_parquet(output_path, index=False, engine='pyarrow')
        self.logger.info(f"[保存] 清洗结果已保存至: {output_path}")

        # 输出统计摘要
        self._log_summary(raw_count, df)

        return df

    def _load_raw_data(self) -> pd.DataFrame:
        """从 MySQL 数据库读取原始订单数据"""
        with self.engine.connect() as conn:
            query = "SELECT * FROM olist_orders"
            df = pd.read_sql_query(query, conn)
        return df

    def _filter_delivered(self, df: pd.DataFrame) -> pd.DataFrame:
        """只保留 order_status='delivered' 的订单"""
        return df[df['order_status'] == 'delivered'].copy()

    def _parse_datetime(self, df: pd.DataFrame) -> pd.DataFrame:
        """将所有时间字段解析为 datetime 类型"""
        for col in self.DATETIME_COLS:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                null_count = df[col].isna().sum()
                if null_count > 0:
                    self.logger.debug(f"  时间字段 {col} 解析后有 {null_count} 个空值")
        return df

    def _drop_missing_critical(self, df: pd.DataFrame) -> pd.DataFrame:
        """删除关键字段（customer_id, order_id, order_purchase_timestamp）为空的行"""
        return df.dropna(subset=self.CRITICAL_COLS).reset_index(drop=True)

    def _join_customers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        关联 customers 表，获取 customer_unique_id 作为用户唯一标识

        逻辑说明：
        Olist 的 customer_id 是订单级别的（同一用户不同订单可能有不同 customer_id），
        而 customer_unique_id 才是真正的用户唯一标识。
        """
        with self.engine.connect() as conn:
            customers = pd.read_sql_query(
                "SELECT customer_id, customer_unique_id FROM olist_customers", conn
            )

        df = df.merge(customers, on='customer_id', how='left')

        # 删除未匹配到 unique_id 的行（理论上不应存在）
        missing_uid = df['customer_unique_id'].isna().sum()
        if missing_uid > 0:
            self.logger.warning(f"有 {missing_uid} 行未匹配到 customer_unique_id，已删除")
            df = df.dropna(subset=['customer_unique_id']).reset_index(drop=True)

        return df

    def _compute_delivery_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算物流衍生字段：
        - delivery_delay_days: 实际送达日期 - 预计送达日期（正数表示延迟）
        - delivery_days: 实际送达日期 - 购买日期（总配送天数）
        """
        # 物流延迟 = 实际送达 - 预计送达（天数）
        df['delivery_delay_days'] = (
            df['order_delivered_customer_date'] - df['order_estimated_delivery_date']
        ).dt.days

        # 实际配送天数 = 实际送达 - 购买时间
        df['delivery_days'] = (
            df['order_delivered_customer_date'] - df['order_purchase_timestamp']
        ).dt.days

        self.logger.info(f"[物流] 平均配送天数: {df['delivery_days'].mean():.1f} 天")
        self.logger.info(f"[物流] 平均延迟天数: {df['delivery_delay_days'].mean():.1f} 天")
        self.logger.info(f"[物流] 延迟订单占比: "
                         f"{(df['delivery_delay_days'] > 0).mean():.1%}")

        return df

    def _log_summary(self, raw_count: int, df: pd.DataFrame) -> None:
        """输出清洗统计摘要"""
        self.logger.info("-" * 60)
        self.logger.info("清洗统计摘要:")
        self.logger.info(f"  原始订单数:       {raw_count:,}")
        self.logger.info(f"  清洗后订单数:     {len(df):,}")
        self.logger.info(f"  保留比例:         {len(df) / raw_count:.1%}")
        self.logger.info(f"  唯一用户数:       {df['customer_unique_id'].nunique():,}")
        self.logger.info(f"  时间跨度:         "
                         f"{df['order_purchase_timestamp'].min().strftime('%Y-%m-%d')} ~ "
                         f"{df['order_purchase_timestamp'].max().strftime('%Y-%m-%d')}")
        self.logger.info("=" * 60)
