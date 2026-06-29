# -*- coding: utf-8 -*-
"""
特征工程模块
职责：构建用户级分析宽表（20+维度特征）

特征维度：
- 交易特征：订单数、消费金额、客单价、运费、商品数
- 时间特征：首/末次购买、生命周期、RFM相关
- 物流特征：配送天数、延迟情况
- 品类特征：主品类、多样性、集中度
- 支付特征：支付方式、分期情况
- 评价特征：评分分布、低评率
- RFM特征：分箱打分 + 分层标签
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from utils.db_connector import get_engine, load_config


class FeatureBuilder:
    """
    用户级特征宽表构建器

    Parameters
    ----------
    config : dict
        项目配置字典
    engine : sqlalchemy.engine.Engine, optional
        SQLAlchemy 数据库引擎；若未提供则从 config 自动创建
    """

    def __init__(self, config: dict, engine=None):
        self.config = config
        self.engine = engine or get_engine(config)
        self.logger = logging.getLogger(self.__class__.__name__)

        # 项目根目录
        self.project_root = Path(__file__).parent.parent
        self.processed_dir = self.project_root / config['data']['processed_dir']
        self.cutoff_date = pd.Timestamp(config['data']['cutoff_date'])

    def run(self) -> pd.DataFrame:
        """
        执行完整特征构建流程

        Returns
        -------
        pd.DataFrame
            用户级特征宽表
        """
        self.logger.info("=" * 60)
        self.logger.info("开始特征工程构建")
        self.logger.info(f"截止日期: {self.cutoff_date.strftime('%Y-%m-%d')}")
        self.logger.info("=" * 60)

        # 读取清洗后的订单数据
        orders = self._load_clean_orders()
        self.logger.info(f"[读取] 清洗后订单数: {len(orders):,}，"
                         f"唯一用户: {orders['customer_unique_id'].nunique():,}")

        # 读取辅助表
        order_items, payments, reviews = self._load_auxiliary_tables()

        # 合并数据
        df = self._merge_all(orders, order_items, payments, reviews)

        # 构建各维度特征
        self.logger.info("[构建] 开始聚合用户级特征...")
        feat_transaction = self._build_transaction_features(df)
        feat_time = self._build_time_features(orders)
        feat_delivery = self._build_delivery_features(orders)
        feat_category = self._build_category_features(df)
        feat_payment = self._build_payment_features(df)
        feat_review = self._build_review_features(df)

        # 合并所有特征
        user_features = feat_transaction
        for feat_df in [feat_time, feat_delivery, feat_category, feat_payment, feat_review]:
            user_features = user_features.merge(feat_df, on='customer_unique_id', how='left')

        # 构建 RFM 特征
        user_features = self._build_rfm_features(user_features)

        # 保存结果
        output_path = self.processed_dir / 'user_features.parquet'
        user_features.to_parquet(output_path, index=False, engine='pyarrow')
        self.logger.info(f"[保存] 用户特征宽表已保存至: {output_path}")

        # 输出摘要
        self._log_summary(user_features)

        return user_features

    def _load_clean_orders(self) -> pd.DataFrame:
        """读取清洗后的订单数据"""
        path = self.processed_dir / 'orders_clean.parquet'
        df = pd.read_parquet(path, engine='pyarrow')
        # 确保时间字段是 datetime
        for col in ['order_purchase_timestamp', 'order_delivered_customer_date',
                    'order_estimated_delivery_date']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col])
        return df

    def _load_auxiliary_tables(self):
        """从数据库读取品类、支付、评价辅助表"""
        with self.engine.connect() as conn:
            order_items = pd.read_sql_query(
                """SELECT oi.order_id, oi.product_id, oi.price, oi.freight_value,
                          p.product_category_name
                   FROM olist_order_items oi
                   LEFT JOIN olist_products p ON oi.product_id = p.product_id""", conn
            )
            payments = pd.read_sql_query(
                "SELECT order_id, payment_type, payment_installments, payment_value "
                "FROM olist_order_payments", conn
            )
            reviews = pd.read_sql_query(
                "SELECT order_id, review_score, review_comment_message FROM olist_order_reviews", conn
            )

        self.logger.info(f"[辅助表] order_items: {len(order_items):,}, "
                         f"payments: {len(payments):,}, reviews: {len(reviews):,}")
        return order_items, payments, reviews

    def _merge_all(self, orders: pd.DataFrame, order_items: pd.DataFrame,
                   payments: pd.DataFrame, reviews: pd.DataFrame) -> pd.DataFrame:
        """合并订单与辅助表数据"""
        df = orders.merge(order_items, on='order_id', how='left')
        df = df.merge(payments, on='order_id', how='left')
        df = df.merge(reviews, on='order_id', how='left')
        return df

    def _build_transaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        交易特征（向量化聚合）：
        - total_orders: 总订单数
        - total_spend: 总消费金额（含运费）
        - avg_order_value: 平均客单价
        - total_freight: 总运费支出
        - avg_items_per_order: 平均每单商品数
        """
        # 先在订单级别去重计算每单商品数
        items_per_order = df.groupby(['customer_unique_id', 'order_id']).agg(
            item_count=('product_id', 'count'),
            order_spend=('price', 'sum'),
            order_freight=('freight_value', 'sum'),
        ).reset_index()

        result = items_per_order.groupby('customer_unique_id').agg(
            total_orders=('order_id', 'nunique'),
            total_spend=('order_spend', 'sum'),
            total_freight=('order_freight', 'sum'),
            avg_items_per_order=('item_count', 'mean'),
        ).reset_index()

        result['total_spend'] = result['total_spend'] + result['total_freight']
        result['avg_order_value'] = result['total_spend'] / result['total_orders']

        self.logger.info(f"  [交易] 平均客单价: {result['avg_order_value'].mean():.2f}")
        return result

    def _build_time_features(self, orders: pd.DataFrame) -> pd.DataFrame:
        """
        时间特征：
        - first_purchase_date / last_purchase_date
        - customer_tenure_days: 客户生命周期（首购到截止日期）
        - recency_days: 最近购买距截止日期天数（R）
        - purchase_frequency: 购买频率
        - avg_purchase_interval: 平均购买间隔
        """
        time_agg = orders.groupby('customer_unique_id').agg(
            first_purchase_date=('order_purchase_timestamp', 'min'),
            last_purchase_date=('order_purchase_timestamp', 'max'),
            order_count=('order_id', 'nunique'),
        ).reset_index()

        # 客户生命周期天数（首购到截止日期）
        time_agg['customer_tenure_days'] = (
            self.cutoff_date - time_agg['first_purchase_date']
        ).dt.days

        # Recency: 最近购买距截止日期天数
        time_agg['recency_days'] = (
            self.cutoff_date - time_agg['last_purchase_date']
        ).dt.days

        # 购买频率 = 总订单数 / 生命周期月数（避免除零）
        tenure_months = time_agg['customer_tenure_days'] / 30.0
        tenure_months = tenure_months.clip(lower=1)  # 最少算1个月
        time_agg['purchase_frequency'] = time_agg['order_count'] / tenure_months

        # 平均购买间隔（天）：仅对多次购买用户有意义
        # 对于单次购买用户设为 NaN
        purchase_span = (
            time_agg['last_purchase_date'] - time_agg['first_purchase_date']
        ).dt.days
        time_agg['avg_purchase_interval'] = np.where(
            time_agg['order_count'] > 1,
            purchase_span / (time_agg['order_count'] - 1),
            np.nan
        )

        time_agg = time_agg.drop(columns=['order_count'])
        self.logger.info(f"  [时间] 平均 Recency: {time_agg['recency_days'].mean():.1f} 天")
        return time_agg

    def _build_delivery_features(self, orders: pd.DataFrame) -> pd.DataFrame:
        """
        物流特征：
        - avg_delivery_days: 平均实际配送天数
        - avg_delivery_delay: 平均延迟天数
        - max_delivery_delay: 最大延迟天数
        - delayed_order_ratio: 延迟订单占比
        - has_severe_delay: 是否有严重延迟（>7天）
        """
        delivery_agg = orders.groupby('customer_unique_id').agg(
            avg_delivery_days=('delivery_days', 'mean'),
            avg_delivery_delay=('delivery_delay_days', 'mean'),
            max_delivery_delay=('delivery_delay_days', 'max'),
        ).reset_index()

        # 延迟订单占比
        orders_with_delay = orders.copy()
        orders_with_delay['is_delayed'] = (orders_with_delay['delivery_delay_days'] > 0).astype(int)
        orders_with_delay['is_severe_delay'] = (orders_with_delay['delivery_delay_days'] > 7).astype(int)

        delay_ratio = orders_with_delay.groupby('customer_unique_id').agg(
            delayed_order_ratio=('is_delayed', 'mean'),
            has_severe_delay=('is_severe_delay', 'max'),
        ).reset_index()

        delivery_agg = delivery_agg.merge(delay_ratio, on='customer_unique_id', how='left')
        delivery_agg['has_severe_delay'] = delivery_agg['has_severe_delay'].astype(bool)

        self.logger.info(f"  [物流] 严重延迟用户占比: "
                         f"{delivery_agg['has_severe_delay'].mean():.1%}")
        return delivery_agg

    def _build_category_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        品类特征：
        - main_category: 最常购买的品类
        - category_diversity: 购买品类多样性
        - top_category_spend_ratio: 最大品类消费占比
        """
        # 品类多样性
        cat_diversity = df.groupby('customer_unique_id')['product_category_name'].nunique() \
            .reset_index().rename(columns={'product_category_name': 'category_diversity'})

        # 最常购买品类（众数）
        main_cat = df.groupby('customer_unique_id')['product_category_name'] \
            .agg(lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else np.nan) \
            .reset_index().rename(columns={'product_category_name': 'main_category'})

        # 最大品类消费占比
        cat_spend = df.groupby(['customer_unique_id', 'product_category_name'])['price'].sum() \
            .reset_index()
        total_spend_per_user = cat_spend.groupby('customer_unique_id')['price'].sum() \
            .reset_index().rename(columns={'price': 'total_cat_spend'})
        max_cat_spend = cat_spend.groupby('customer_unique_id')['price'].max() \
            .reset_index().rename(columns={'price': 'max_cat_spend'})

        spend_ratio = max_cat_spend.merge(total_spend_per_user, on='customer_unique_id')
        spend_ratio['top_category_spend_ratio'] = (
            spend_ratio['max_cat_spend'] / spend_ratio['total_cat_spend']
        )
        spend_ratio = spend_ratio[['customer_unique_id', 'top_category_spend_ratio']]

        # 合并
        result = cat_diversity.merge(main_cat, on='customer_unique_id', how='left')
        result = result.merge(spend_ratio, on='customer_unique_id', how='left')

        self.logger.info(f"  [品类] 平均品类多样性: {result['category_diversity'].mean():.2f}")
        return result

    def _build_payment_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        支付特征：
        - main_payment_type: 主要支付方式
        - avg_installments: 平均分期期数
        - max_installments: 最大分期期数
        """
        # 主要支付方式
        main_pay = df.groupby('customer_unique_id')['payment_type'] \
            .agg(lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else np.nan) \
            .reset_index().rename(columns={'payment_type': 'main_payment_type'})

        # 分期统计
        installment_agg = df.groupby('customer_unique_id')['payment_installments'].agg(
            avg_installments='mean',
            max_installments='max',
        ).reset_index()

        result = main_pay.merge(installment_agg, on='customer_unique_id', how='left')
        self.logger.info(f"  [支付] 平均分期期数: {result['avg_installments'].mean():.2f}")
        return result

    def _build_review_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        评价特征：
        - avg_review_score: 平均评分
        - min_review_score: 最低评分
        - low_score_count: 低评分（≤2）订单数
        - low_score_ratio: 低评分占比
        - has_review_comment: 是否留过文字评论
        """
        df_review = df.copy()
        df_review['is_low_score'] = (df_review['review_score'] <= 2).astype(int)
        df_review['has_comment'] = df_review['review_comment_message'].notna().astype(int)

        result = df_review.groupby('customer_unique_id').agg(
            avg_review_score=('review_score', 'mean'),
            min_review_score=('review_score', 'min'),
            low_score_count=('is_low_score', 'sum'),
            total_reviews=('review_score', 'count'),
            has_review_comment=('has_comment', 'max'),
        ).reset_index()

        result['low_score_ratio'] = result['low_score_count'] / result['total_reviews']
        result['has_review_comment'] = result['has_review_comment'].astype(bool)
        result = result.drop(columns=['total_reviews'])

        self.logger.info(f"  [评价] 平均评分: {result['avg_review_score'].mean():.2f}")
        return result

    def _build_rfm_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        RFM 特征构建：
        - 使用 pd.qcut 四分位分箱（1-4分）
        - R: recency_days 越小得分越高（最近 = 4分）
        - F: purchase_frequency 越高得分越高
        - M: total_spend 越高得分越高
        - 综合分层标签

        RFM 分层规则：
        - 高价值客户：R>=3 & F>=3 & M>=3
        - 重点保持：R>=3 & (F>=2 | M>=3)
        - 需唤醒：R<=2 & F>=2
        - 流失风险：R<=2 & F<=2
        """
        # R 得分：recency 越小越好，所以用 ascending=False 的 labels
        df['rfm_r_score'] = pd.qcut(
            df['recency_days'].rank(method='first'),
            q=4, labels=[4, 3, 2, 1]
        ).astype(int)

        # F 得分：frequency 越高越好
        df['rfm_f_score'] = pd.qcut(
            df['purchase_frequency'].rank(method='first'),
            q=4, labels=[1, 2, 3, 4]
        ).astype(int)

        # M 得分：monetary 越高越好
        df['rfm_m_score'] = pd.qcut(
            df['total_spend'].rank(method='first'),
            q=4, labels=[1, 2, 3, 4]
        ).astype(int)

        # RFM 分层标签
        df['rfm_segment'] = self._assign_rfm_segment(df)

        self.logger.info(f"  [RFM] 分层分布:")
        segment_dist = df['rfm_segment'].value_counts()
        for seg, cnt in segment_dist.items():
            self.logger.info(f"    {seg}: {cnt:,} ({cnt/len(df):.1%})")

        return df

    @staticmethod
    def _assign_rfm_segment(df: pd.DataFrame) -> pd.Series:
        """
        根据 RFM 得分分配客户分层标签

        规则：
        - 高价值客户：R>=3 & F>=3 & M>=3（核心忠诚用户）
        - 重点保持：R>=3 & (F>=2 | M>=3)（近期活跃但需维护）
        - 需唤醒：R<=2 & F>=2（沉默的老用户）
        - 流失风险：R<=2 & F<=2（长期未购 + 频率低）
        """
        conditions = [
            (df['rfm_r_score'] >= 3) & (df['rfm_f_score'] >= 3) & (df['rfm_m_score'] >= 3),
            (df['rfm_r_score'] >= 3) & ((df['rfm_f_score'] >= 2) | (df['rfm_m_score'] >= 3)),
            (df['rfm_r_score'] <= 2) & (df['rfm_f_score'] >= 2),
        ]
        choices = ['高价值客户', '重点保持', '需唤醒']

        return pd.Series(
            np.select(conditions, choices, default='流失风险'),
            index=df.index
        )

    def _log_summary(self, df: pd.DataFrame) -> None:
        """输出特征统计摘要"""
        self.logger.info("-" * 60)
        self.logger.info("特征工程统计摘要:")
        self.logger.info(f"  用户总数:         {len(df):,}")
        self.logger.info(f"  特征维度:         {len(df.columns)}")
        self.logger.info(f"  缺失值情况:")
        missing = df.isnull().sum()
        missing_cols = missing[missing > 0]
        if len(missing_cols) > 0:
            for col, cnt in missing_cols.items():
                self.logger.info(f"    {col}: {cnt:,} ({cnt/len(df):.1%})")
        else:
            self.logger.info(f"    无缺失值")
        self.logger.info("=" * 60)

