# -*- coding: utf-8 -*-
"""
经营分析模块
核心：GMV、毛利、品类、地区、支付方式等 KPI 计算与可视化
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yaml

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_connector import get_engine, load_config

warnings.filterwarnings('ignore')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


class BusinessAnalyzer:
    """经营分析器"""

    def __init__(self, config: dict, engine=None):
        self.config = config
        self.engine = engine or get_engine(config)
        self.project_root = Path(__file__).resolve().parent.parent
        self.data_dir = self.project_root / 'data' / 'processed'
        self.plot_dir = self.data_dir / 'plots'
        self.plot_dir.mkdir(parents=True, exist_ok=True)

        # 品类毛利率假设（中文品类名，与 rebranded 数据一致）
        self.margin_rates = config.get('margin_rates', {
            '电脑配件': 0.12,
            '数码电子': 0.15,
            '手机通讯': 0.30,
            '美妆个护': 0.50,
            '运动户外': 0.40,
            '家居装饰': 0.35,
            '家居日用': 0.42,
            '汽车用品': 0.25,
            '玩具': 0.40,
            '创意潮品': 0.35,
            '家用电器': 0.30,
            'default': 0.30
        })

    def run(self):
        """执行经营分析流程"""
        print("=" * 60)
        print("经营分析模块")
        print("=" * 60)

        # 加载数据
        df = self._load_data()

        # KPI 计算
        monthly_kpi = self._calculate_monthly_kpi(df)
        category_perf = self._category_analysis(df)
        state_perf = self._state_analysis(df)
        payment_analysis = self._payment_analysis(df)

        # 可视化
        self._plot_gmv_trend(monthly_kpi)
        self._plot_category_charts(category_perf)
        self._plot_state_gmv(state_perf)
        self._plot_payment(payment_analysis)
        self._plot_installments(df)

        # 数据导出（Power BI 使用）
        self._export_data(monthly_kpi, category_perf, state_perf, payment_analysis)

        print("\n经营分析完成!")

    def _load_data(self) -> pd.DataFrame:
        """加载订单数据"""
        print("\n[数据加载]...")

        query = """
        SELECT 
            o.order_id,
            o.customer_id,
            o.order_purchase_timestamp,
            o.order_status,
            i.product_id,
            i.seller_id,
            i.price,
            i.freight_value,
            p.product_category_name,
            c.customer_state,
            pay.payment_type,
            pay.payment_installments,
            pay.payment_value
        FROM olist_orders o
        LEFT JOIN olist_order_items i ON o.order_id = i.order_id
        LEFT JOIN olist_products p ON i.product_id = p.product_id
        LEFT JOIN olist_customers c ON o.customer_id = c.customer_id
        LEFT JOIN olist_order_payments pay ON o.order_id = pay.order_id
        WHERE o.order_status = 'delivered'
        """

        with self.engine.connect() as conn:
            df = pd.read_sql_query(query, conn)

        df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'])
        df['year_month'] = df['order_purchase_timestamp'].dt.to_period('M')

        # 计算毛利
        df['margin_rate'] = df['product_category_name'].map(
            lambda x: self.margin_rates.get(str(x), self.margin_rates['default'])
        )
        df['gross_profit'] = df['price'] * df['margin_rate']

        print(f"  加载已完成订单数: {df['order_id'].nunique()}")
        print(f"  时间范围: {df['order_purchase_timestamp'].min()} ~ {df['order_purchase_timestamp'].max()}")

        return df

    def _calculate_monthly_kpi(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算月度 KPI"""
        print("\n[月度 KPI 计算]...")

        monthly = df.groupby('year_month').agg(
            gmv=('price', 'sum'),
            freight_revenue=('freight_value', 'sum'),
            order_count=('order_id', 'nunique'),
            gross_profit=('gross_profit', 'sum')
        ).reset_index()

        monthly['aov'] = monthly['gmv'] / monthly['order_count']
        monthly['gross_margin'] = monthly['gross_profit'] / monthly['gmv']
        monthly['gmv_growth'] = monthly['gmv'].pct_change()
        monthly['month'] = monthly['year_month'].astype(str)

        print(f"  月度数据行数: {len(monthly)}")
        print(f"  总 GMV: ¥{monthly['gmv'].sum():,.2f}")
        print(f"  平均月 GMV: ¥{monthly['gmv'].mean():,.2f}")
        print(f"  平均客单价: ¥{monthly['aov'].mean():.2f}")

        return monthly

    def _category_analysis(self, df: pd.DataFrame) -> pd.DataFrame:
        """品类分析"""
        print("\n[品类分析]...")

        category = df.groupby('product_category_name').agg(
            revenue=('price', 'sum'),
            order_count=('order_id', 'nunique'),
            gross_profit=('gross_profit', 'sum'),
            avg_price=('price', 'mean')
        ).reset_index()

        category['margin_rate'] = category['gross_profit'] / category['revenue']
        category = category.sort_values('revenue', ascending=False)

        print(f"  品类数: {len(category)}")
        print(f"  Top 5 品类收入:")
        for _, row in category.head(5).iterrows():
            print(f"    {row['product_category_name']}: ¥{row['revenue']:,.2f}")

        return category

    def _state_analysis(self, df: pd.DataFrame) -> pd.DataFrame:
        """地区分析"""
        print("\n[地区分析]...")

        state = df.groupby('customer_state').agg(
            gmv=('price', 'sum'),
            order_count=('order_id', 'nunique'),
            customer_count=('customer_id', 'nunique'),
            avg_order_value=('price', 'mean')
        ).reset_index()

        state = state.sort_values('gmv', ascending=False)

        print(f"  省份数: {len(state)}")
        print(f"  Top 5 省份 GMV:")
        for _, row in state.head(5).iterrows():
            print(f"    {row['customer_state']}: ¥{row['gmv']:,.2f}")

        return state

    def _payment_analysis(self, df: pd.DataFrame) -> pd.DataFrame:
        """支付方式分析"""
        print("\n[支付方式分析]...")

        payment_df = df.drop_duplicates(subset=['order_id', 'payment_type'])
        payment = payment_df.groupby('payment_type').agg(
            transaction_count=('order_id', 'nunique'),
            total_value=('payment_value', 'sum'),
            avg_installments=('payment_installments', 'mean')
        ).reset_index()

        payment['share'] = payment['transaction_count'] / payment['transaction_count'].sum()
        payment = payment.sort_values('transaction_count', ascending=False)

        print(f"  支付方式:")
        for _, row in payment.iterrows():
            print(f"    {row['payment_type']}: {row['share']:.2%} ({row['transaction_count']} 笔)")

        return payment

    def _plot_gmv_trend(self, monthly: pd.DataFrame):
        """月度 GMV + 环比增长率双轴图"""
        fig, ax1 = plt.subplots(figsize=(14, 6))

        x = range(len(monthly))
        ax1.bar(x, monthly['gmv'] / 10000, color='#3498db', alpha=0.7, label='GMV(万)')
        ax1.set_xlabel('月份')
        ax1.set_ylabel('GMV (万)', color='#3498db')
        ax1.tick_params(axis='y', labelcolor='#3498db')
        ax1.set_xticks(x)
        ax1.set_xticklabels(monthly['month'], rotation=45, ha='right', fontsize=8)

        ax2 = ax1.twinx()
        growth_pct = monthly['gmv_growth'] * 100
        ax2.plot(x, growth_pct, color='#e74c3c', marker='o', linewidth=2, label='环比增长率(%)')
        ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax2.set_ylabel('环比增长率 (%)', color='#e74c3c')
        ax2.tick_params(axis='y', labelcolor='#e74c3c')

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

        plt.title('月度 GMV 趋势与环比增长率')
        plt.tight_layout()
        plt.savefig(self.plot_dir / 'business_gmv_trend.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  GMV 趋势图已保存")

    def _plot_category_charts(self, category: pd.DataFrame):
        """品类收入 & 毛利图表"""
        top10 = category.head(10)
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))

        axes[0].barh(range(len(top10)), top10['revenue'] / 10000, color='#3498db', alpha=0.8)
        axes[0].set_yticks(range(len(top10)))
        axes[0].set_yticklabels(top10['product_category_name'], fontsize=8)
        axes[0].set_xlabel('收入 (万)')
        axes[0].set_title('品类收入 Top 10')
        axes[0].invert_yaxis()

        top10_margin = category.nlargest(10, 'gross_profit')
        axes[1].barh(range(len(top10_margin)), top10_margin['gross_profit'] / 10000, color='#2ecc71', alpha=0.8)
        axes[1].set_yticks(range(len(top10_margin)))
        axes[1].set_yticklabels(top10_margin['product_category_name'], fontsize=8)
        axes[1].set_xlabel('毛利 (万)')
        axes[1].set_title('品类毛利贡献 Top 10')
        axes[1].invert_yaxis()

        plt.tight_layout()
        plt.savefig(self.plot_dir / 'business_category_revenue.png', dpi=150, bbox_inches='tight')
        plt.close()

        fig2, ax = plt.subplots(figsize=(10, 6))
        ax.barh(range(len(top10_margin)), top10_margin['gross_profit'] / 10000, color='#2ecc71', alpha=0.8)
        ax.set_yticks(range(len(top10_margin)))
        ax.set_yticklabels(top10_margin['product_category_name'], fontsize=8)
        ax.set_xlabel('毛利 (万)')
        ax.set_title('品类毛利贡献 Top 10')
        ax.invert_yaxis()
        plt.tight_layout()
        plt.savefig(self.plot_dir / 'business_category_margin.png', dpi=150, bbox_inches='tight')
        plt.close()

        print("  品类图表已保存")

    def _plot_state_gmv(self, state: pd.DataFrame):
        """省级 GMV 柱状图"""
        fig, ax = plt.subplots(figsize=(14, 6))

        ax.bar(range(len(state)), state['gmv'] / 10000, color='#9b59b6', alpha=0.7)
        ax.set_xticks(range(len(state)))
        ax.set_xticklabels(state['customer_state'], rotation=45, ha='right')
        ax.set_xlabel('省份')
        ax.set_ylabel('GMV (万)')
        ax.set_title('各省份 GMV 分布（降序）')

        plt.tight_layout()
        plt.savefig(self.plot_dir / 'business_state_gmv.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  省级 GMV 图已保存")

    def _plot_payment(self, payment: pd.DataFrame):
        """支付方式饼图"""
        fig, ax = plt.subplots(figsize=(8, 8))

        colors = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6']
        explode = [0.05] * len(payment)

        ax.pie(payment['transaction_count'], labels=payment['payment_type'],
               autopct='%1.1f%%', colors=colors[:len(payment)],
               explode=explode[:len(payment)], startangle=90)
        ax.set_title('支付方式占比')

        plt.tight_layout()
        plt.savefig(self.plot_dir / 'business_payment_type.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  支付方式饼图已保存")

    def _plot_installments(self, df: pd.DataFrame):
        """分期付款行为分析"""
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        installments = df.drop_duplicates(subset=['order_id', 'payment_installments'])
        inst_dist = installments['payment_installments'].value_counts().sort_index()
        inst_dist = inst_dist[inst_dist.index <= 12]

        axes[0].bar(inst_dist.index, inst_dist.values, color='#f39c12', alpha=0.8)
        axes[0].set_xlabel('分期期数')
        axes[0].set_ylabel('订单数')
        axes[0].set_title('分期期数分布')

        installments['year_month'] = installments['order_purchase_timestamp'].dt.to_period('M')
        monthly_inst = installments.groupby('year_month')['payment_installments'].mean()
        axes[1].plot(range(len(monthly_inst)), monthly_inst.values, marker='o', color='#e67e22', linewidth=2)
        axes[1].set_xlabel('月份')
        axes[1].set_ylabel('平均分期期数')
        axes[1].set_title('平均分期期数月度趋势')
        tick_positions = list(range(0, len(monthly_inst), max(1, len(monthly_inst) // 8)))
        axes[1].set_xticks(tick_positions)
        axes[1].set_xticklabels([str(monthly_inst.index[i]) for i in tick_positions], rotation=45, fontsize=8)

        plt.tight_layout()
        plt.savefig(self.plot_dir / 'business_installments.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  分期行为图表已保存")

    def _export_data(self, monthly, category, state, payment):
        """导出数据供 Power BI 使用"""
        print("\n[数据导出]...")

        monthly_export = monthly[['month', 'gmv', 'order_count', 'aov', 'gross_profit', 'gross_margin', 'gmv_growth']].copy()
        monthly_export.to_csv(self.data_dir / 'monthly_kpi.csv', index=False, encoding='utf-8-sig')

        category.to_csv(self.data_dir / 'category_performance.csv', index=False, encoding='utf-8-sig')
        state.to_csv(self.data_dir / 'state_performance.csv', index=False, encoding='utf-8-sig')
        payment.to_csv(self.data_dir / 'payment_analysis.csv', index=False, encoding='utf-8-sig')

        print(f"  已导出:")
        print(f"    - monthly_kpi.csv")
        print(f"    - category_performance.csv")
        print(f"    - state_performance.csv")
        print(f"    - payment_analysis.csv")


if __name__ == "__main__":
    config = load_config()
    analyzer = BusinessAnalyzer(config)
    analyzer.run()
