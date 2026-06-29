# -*- coding: utf-8 -*-
"""
流失标签构建脚本
核心算法：P75×2 数据驱动流失定义

业务合理性说明：
为什么选用 P75×2 作为流失阈值？
1. P75（第三四分位数）代表了75%用户的典型购买间隔上限
   - 它比均值更稳健，不受极端值影响
   - 反映了"正常回购周期"的合理上界
2. 乘以2倍的系数含义：
   - 如果一个用户超过正常回购周期的2倍仍未回购
   - 可以合理推断该用户已经"脱离"正常消费模式
   - 这是一个保守但有效的流失判定标准
3. 相比固定天数阈值的优势：
   - 数据驱动，适应不同品类的回购周期差异
   - 可解释性强，便于向业务方沟通
   - 避免了人为拍脑袋定义的主观性

参考：该方法在学术论文和工业界广泛使用
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd


class ChurnLabelBuilder:
    """
    数据驱动的流失标签构建器

    核心逻辑：
    1. 筛选多次购买用户计算购买间隔
    2. 取购买间隔的 P75 分位数
    3. 流失阈值 = P75 × multiplier
    4. 若用户 recency_days > 阈值，则标记为流失

    Parameters
    ----------
    config : dict
        项目配置字典，需包含：
        - data.processed_dir: 处理后数据目录
        - thresholds.churn.min_orders: 参与阈值计算的最少订单数
        - thresholds.churn.multiplier: P75 乘数（默认2）
    """

    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        # 项目根目录（通过当前文件位置推断：scripts/ 向上一级）
        self.project_root = Path(__file__).parent.parent
        self.processed_dir = self.project_root / config['data']['processed_dir']
        self.min_orders = config['thresholds']['churn']['min_orders']
        self.multiplier = config['thresholds']['churn'].get('multiplier', 2.0)

    def run(self) -> pd.DataFrame:
        """
        执行流失标签构建流程

        Returns
        -------
        pd.DataFrame
            包含流失标签的用户数据
        """
        self.logger.info("=" * 60)
        self.logger.info("开始流失标签构建")
        self.logger.info(f"配置: min_orders={self.min_orders}, multiplier={self.multiplier}")
        self.logger.info("=" * 60)

        # Step 1: 读取用户特征数据
        user_features = self._load_user_features()
        self.logger.info(f"[读取] 用户总数: {len(user_features):,}")

        # Step 2: 读取清洗后的订单数据计算购买间隔
        orders_clean = self._load_clean_orders()

        # Step 3: 计算多次购买用户的购买间隔
        intervals = self._compute_purchase_intervals(orders_clean)

        # Step 4: 计算 P75 和流失阈值
        churn_threshold = self._compute_churn_threshold(intervals)

        # Step 5: 标记流失
        churn_labels = self._label_churn(user_features, churn_threshold)

        # Step 6: 输出详细统计
        self._log_statistics(churn_labels, churn_threshold, intervals)

        # Step 7: 保存结果
        self._save_results(churn_labels, user_features)

        return churn_labels

    def _load_user_features(self) -> pd.DataFrame:
        """读取用户特征宽表"""
        path = self.processed_dir / 'user_features.parquet'
        return pd.read_parquet(path, engine='pyarrow')

    def _load_clean_orders(self) -> pd.DataFrame:
        """读取清洗后的订单数据"""
        path = self.processed_dir / 'orders_clean.parquet'
        df = pd.read_parquet(path, engine='pyarrow')
        df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'])
        return df

    def _compute_purchase_intervals(self, orders: pd.DataFrame) -> pd.Series:
        """
        向量化计算多次购买用户的购买间隔

        方法：
        1. 按用户和时间排序
        2. groupby + diff 计算相邻订单时间差
        3. 只保留有 min_orders 笔以上订单的用户的间隔数据

        Parameters
        ----------
        orders : pd.DataFrame
            清洗后的订单数据

        Returns
        -------
        pd.Series
            所有合格用户的购买间隔天数（展平为一维）
        """
        # 每个用户每个订单只保留一条记录（去重）
        user_orders = orders.drop_duplicates(subset=['customer_unique_id', 'order_id']) \
            .sort_values(['customer_unique_id', 'order_purchase_timestamp'])

        # 筛选订单数 >= min_orders 的用户
        order_counts = user_orders.groupby('customer_unique_id')['order_id'].nunique()
        qualified_users = order_counts[order_counts >= self.min_orders].index

        self.logger.info(f"[间隔] 满足 >={self.min_orders} 笔订单的用户: "
                         f"{len(qualified_users):,}")

        # 筛选合格用户的订单
        qualified_orders = user_orders[
            user_orders['customer_unique_id'].isin(qualified_users)
        ].copy()

        # 向量化计算购买间隔（groupby + diff，不用 for 循环）
        qualified_orders['purchase_interval'] = qualified_orders.groupby(
            'customer_unique_id'
        )['order_purchase_timestamp'].diff().dt.days

        # 去除每个用户第一条记录的 NaN
        intervals = qualified_orders['purchase_interval'].dropna()

        self.logger.info(f"[间隔] 有效间隔样本数: {len(intervals):,}")
        self.logger.info(f"[间隔] 间隔统计: "
                         f"均值={intervals.mean():.1f}天, "
                         f"中位数={intervals.median():.1f}天, "
                         f"P75={intervals.quantile(0.75):.1f}天")

        return intervals

    def _compute_churn_threshold(self, intervals: pd.Series) -> float:
        """
        计算流失阈值 = P75 × multiplier

        Parameters
        ----------
        intervals : pd.Series
            购买间隔天数序列

        Returns
        -------
        float
            流失阈值（天数）
        """
        p75 = intervals.quantile(0.75)
        threshold = p75 * self.multiplier

        self.logger.info(f"[阈值] P75 购买间隔: {p75:.1f} 天")
        self.logger.info(f"[阈值] 流失阈值 (P75 × {self.multiplier}): {threshold:.1f} 天")

        return threshold

    def _label_churn(self, user_features: pd.DataFrame, threshold: float) -> pd.DataFrame:
        """
        根据 recency_days 和阈值标记流失

        规则：recency_days > threshold → is_churned = 1

        注意：
        - 所有用户都使用相同阈值判断
        - 单次购买用户虽不参与阈值计算，但同样适用该阈值进行标记

        Parameters
        ----------
        user_features : pd.DataFrame
            用户特征宽表（需含 recency_days）
        threshold : float
            流失阈值天数

        Returns
        -------
        pd.DataFrame
            含流失标签的结果 DataFrame
        """
        result = user_features[['customer_unique_id', 'recency_days', 'total_orders']].copy()
        result['churn_threshold'] = threshold
        result['days_since_last'] = result['recency_days']
        result['is_churned'] = (result['recency_days'] > threshold).astype(int)

        return result

    def _log_statistics(self, churn_labels: pd.DataFrame, threshold: float,
                        intervals: pd.Series) -> None:
        """输出详细的流失统计信息"""
        total_users = len(churn_labels)
        churned_users = churn_labels['is_churned'].sum()
        churn_rate = churned_users / total_users

        # 区分单次购买和多次购买用户
        single_purchase = churn_labels[churn_labels['total_orders'] == 1]
        multi_purchase = churn_labels[churn_labels['total_orders'] >= self.min_orders]

        single_churn_rate = single_purchase['is_churned'].mean() if len(single_purchase) > 0 else 0
        multi_churn_rate = multi_purchase['is_churned'].mean() if len(multi_purchase) > 0 else 0

        self.logger.info("-" * 60)
        self.logger.info("流失标签统计摘要:")
        self.logger.info(f"  P75 购买间隔:       {intervals.quantile(0.75):.1f} 天")
        self.logger.info(f"  流失阈值:           {threshold:.1f} 天")
        self.logger.info(f"  总用户数:           {total_users:,}")
        self.logger.info(f"  流失用户数:         {churned_users:,}")
        self.logger.info(f"  整体流失率:         {churn_rate:.1%}")
        self.logger.info(f"  单次购买用户数:     {len(single_purchase):,}")
        self.logger.info(f"  单次购买流失率:     {single_churn_rate:.1%}")
        self.logger.info(f"  多次购买用户数:     {len(multi_purchase):,}")
        self.logger.info(f"  多次购买流失率:     {multi_churn_rate:.1%}")
        self.logger.info("-" * 60)

    def _save_results(self, churn_labels: pd.DataFrame, user_features: pd.DataFrame) -> None:
        """
        保存流失标签结果：
        1. 保存独立的 churn_labels.parquet
        2. 更新 user_features.parquet 添加 is_churned 列
        """
        # 保存流失标签文件
        churn_output = self.processed_dir / 'churn_labels.parquet'
        churn_save = churn_labels[['customer_unique_id', 'is_churned',
                                    'days_since_last', 'churn_threshold']].copy()
        churn_save.to_parquet(churn_output, index=False, engine='pyarrow')
        self.logger.info(f"[保存] 流失标签已保存至: {churn_output}")

        # 更新用户特征宽表，添加 is_churned 列
        user_features_updated = user_features.merge(
            churn_labels[['customer_unique_id', 'is_churned']],
            on='customer_unique_id',
            how='left'
        )
        features_output = self.processed_dir / 'user_features.parquet'
        user_features_updated.to_parquet(features_output, index=False, engine='pyarrow')
        self.logger.info(f"[保存] 用户特征宽表已更新（添加 is_churned 列）: {features_output}")
        self.logger.info("=" * 60)
