# -*- coding: utf-8 -*-
"""
评论评分维度分析模块
核心方法：低评分订单归因分析 + 中文高频词统计
"""

import warnings
import sys
from pathlib import Path
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_connector import get_engine, load_config

warnings.filterwarnings('ignore')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


class ReviewAnalyzer:
    """评论评分维度分析器"""

    def __init__(self, config: dict, engine=None):
        self.config = config
        self.engine = engine or get_engine(config)
        self.project_root = Path(__file__).resolve().parent.parent
        self.data_dir = self.project_root / 'data' / 'processed'
        self.plot_dir = self.data_dir / 'plots'
        self.plot_dir.mkdir(parents=True, exist_ok=True)

        # 阈值配置
        thresholds = config.get('thresholds', {})
        self.low_score_threshold = thresholds.get('low_review_score', 2)

    def run(self):
        """执行评论分析流程"""
        print("=" * 60)
        print("评论评分维度分析")
        print("=" * 60)

        # Part 1: 评分维度分析
        df = self._load_data()
        self._score_dimension_analysis(df)

        # Part 2: 中文高频词分析
        self._text_analysis(df)

        print("\n评论分析完成!")

    def _load_data(self) -> pd.DataFrame:
        """加载评论相关数据"""
        print("\n[数据加载]...")

        query = """
        SELECT 
            r.review_id,
            r.order_id,
            r.review_score,
            r.review_comment_message,
            o.order_purchase_timestamp,
            o.order_delivered_customer_date,
            o.order_estimated_delivery_date,
            o.customer_id,
            i.product_id,
            i.price,
            p.product_category_name,
            c.customer_state
        FROM olist_order_reviews r
        LEFT JOIN olist_orders o ON r.order_id = o.order_id
        LEFT JOIN olist_order_items i ON r.order_id = i.order_id
        LEFT JOIN olist_products p ON i.product_id = p.product_id
        LEFT JOIN olist_customers c ON o.customer_id = c.customer_id
        """

        with self.engine.connect() as conn:
            df = pd.read_sql_query(query, conn)

        # 计算配送天数
        df['order_delivered_customer_date'] = pd.to_datetime(df['order_delivered_customer_date'])
        df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'])
        df['order_estimated_delivery_date'] = pd.to_datetime(df['order_estimated_delivery_date'])

        df['delivery_days'] = (df['order_delivered_customer_date'] - df['order_purchase_timestamp']).dt.days
        df['delay_days'] = (df['order_delivered_customer_date'] - df['order_estimated_delivery_date']).dt.days
        df['is_delayed'] = (df['delay_days'] > 0).astype(int)

        # 定义低评分/高评分
        df['score_group'] = df['review_score'].apply(
            lambda x: 'low' if x <= self.low_score_threshold else ('high' if x >= 4 else 'mid')
        )

        print(f"  加载评论数: {len(df)}")
        print(f"  低评分(≤{self.low_score_threshold}): {(df['score_group'] == 'low').sum()}")
        print(f"  高评分(≥4): {(df['score_group'] == 'high').sum()}")

        return df

    def _score_dimension_analysis(self, df: pd.DataFrame):
        """Part 1: 多维度评分分析"""
        print("\n[Part 1] 评分维度分析...")

        low_df = df[df['score_group'] == 'low']
        high_df = df[df['score_group'] == 'high']

        # === 物流维度 ===
        print("\n  --- 物流维度 ---")
        logistics_compare = pd.DataFrame({
            '低评分': [
                low_df['delivery_days'].mean(),
                low_df['is_delayed'].mean(),
                low_df.loc[low_df['is_delayed'] == 1, 'delay_days'].mean()
            ],
            '高评分': [
                high_df['delivery_days'].mean(),
                high_df['is_delayed'].mean(),
                high_df.loc[high_df['is_delayed'] == 1, 'delay_days'].mean()
            ]
        }, index=['平均配送天数', '延迟率', '平均延迟天数'])
        print(logistics_compare.to_string())

        # === 品类维度 ===
        print("\n  --- 品类维度 ---")
        category_low_rate = df.groupby('product_category_name').apply(
            lambda x: (x['score_group'] == 'low').mean()
        ).sort_values(ascending=False)
        print(f"  低评分占比最高的品类 Top 5:")
        for cat, rate in category_low_rate.head(5).items():
            print(f"    {cat}: {rate:.4f}")

        # === 地区维度 ===
        print("\n  --- 地区维度 ---")
        state_low_rate = df.groupby('customer_state').apply(
            lambda x: (x['score_group'] == 'low').mean()
        ).sort_values(ascending=False)
        print(f"  低评分占比最高的州 Top 5:")
        for state, rate in state_low_rate.head(5).items():
            print(f"    {state}: {rate:.4f}")

        # === 金额维度 ===
        print("\n  --- 金额维度 ---")
        print(f"  低评分客单价均值: ¥{low_df['price'].mean():.2f}")
        print(f"  高评分客单价均值: ¥{high_df['price'].mean():.2f}")

        # === 卖家维度 ===
        print("\n  --- 卖家维度 ---")
        if 'seller_id' in df.columns:
            seller_low_count = low_df.groupby('seller_id').size().sort_values(ascending=False)
            top10_sellers_low = seller_low_count.head(10).sum()
            total_low = len(low_df)
            print(f"  Top 10 差评卖家贡献了 {top10_sellers_low}/{total_low} = {top10_sellers_low/total_low:.2%} 的差评")

        # === 统计检验 ===
        print("\n  --- 统计检验 ---")
        from scipy.stats import chi2_contingency, mannwhitneyu

        # 卡方检验：品类与低评分是否独立
        top_cats = df['product_category_name'].value_counts().head(20).index
        df_top_cats = df[df['product_category_name'].isin(top_cats)]
        contingency = pd.crosstab(df_top_cats['product_category_name'], df_top_cats['score_group'] == 'low')
        chi2, p_chi2, dof, expected = chi2_contingency(contingency)
        print(f"  卡方检验(品类 vs 低评分): χ²={chi2:.2f}, p={p_chi2:.4e}, {'显著' if p_chi2 < 0.05 else '不显著'}")

        # Mann-Whitney U 检验：配送天数
        low_delivery = low_df['delivery_days'].dropna()
        high_delivery = high_df['delivery_days'].dropna()
        if len(low_delivery) > 0 and len(high_delivery) > 0:
            u_stat, p_mwu = mannwhitneyu(low_delivery, high_delivery, alternative='greater')
            print(f"  Mann-Whitney U(配送天数): U={u_stat:.0f}, p={p_mwu:.4e}, {'显著' if p_mwu < 0.05 else '不显著'}")

        # === 可视化 ===
        self._plot_review_charts(df, category_low_rate, state_low_rate)

    def _plot_review_charts(self, df, category_low_rate, state_low_rate):
        """生成评论分析可视化"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # 1. 评分分布条形图
        score_counts = df['review_score'].value_counts().sort_index()
        colors = ['#e74c3c', '#e74c3c', '#f39c12', '#2ecc71', '#2ecc71']
        axes[0, 0].bar(score_counts.index, score_counts.values, color=colors, alpha=0.8)
        axes[0, 0].set_xlabel('评分')
        axes[0, 0].set_ylabel('评论数')
        axes[0, 0].set_title('评分分布')

        # 2. 品类低评分排名 Top 10
        top10_cats = category_low_rate.head(10)
        axes[0, 1].barh(range(len(top10_cats)), top10_cats.values, color='#e74c3c', alpha=0.7)
        axes[0, 1].set_yticks(range(len(top10_cats)))
        axes[0, 1].set_yticklabels(top10_cats.index, fontsize=8)
        axes[0, 1].set_xlabel('低评分占比')
        axes[0, 1].set_title('品类低评分率 Top 10')

        # 3. 地区低评分分布
        top10_states = state_low_rate.head(10)
        axes[1, 0].barh(range(len(top10_states)), top10_states.values, color='#3498db', alpha=0.7)
        axes[1, 0].set_yticks(range(len(top10_states)))
        axes[1, 0].set_yticklabels(top10_states.index)
        axes[1, 0].set_xlabel('低评分占比')
        axes[1, 0].set_title('各州低评分率 Top 10')

        # 4. 低评分归因热力图（物流/品类/地区）
        low_df = df[df['score_group'] == 'low']
        high_df = df[df['score_group'] == 'high']
        heatmap_data = pd.DataFrame({
            '配送天数': [low_df['delivery_days'].mean(), high_df['delivery_days'].mean()],
            '延迟率': [low_df['is_delayed'].mean(), high_df['is_delayed'].mean()],
            '客单价': [low_df['price'].mean(), high_df['price'].mean()],
        }, index=['低评分', '高评分'])

        # 归一化热力图数据
        heatmap_norm = heatmap_data.apply(lambda x: (x - x.min()) / (x.max() - x.min() + 1e-8))
        im = axes[1, 1].imshow(heatmap_norm.values, cmap='RdYlGn_r', aspect='auto')
        axes[1, 1].set_xticks(range(len(heatmap_data.columns)))
        axes[1, 1].set_xticklabels(heatmap_data.columns)
        axes[1, 1].set_yticks(range(len(heatmap_data.index)))
        axes[1, 1].set_yticklabels(heatmap_data.index)
        axes[1, 1].set_title('低评分 vs 高评分 归因对比')
        # 添加数值标注
        for i in range(len(heatmap_data.index)):
            for j in range(len(heatmap_data.columns)):
                axes[1, 1].text(j, i, f'{heatmap_data.iloc[i, j]:.2f}',
                               ha='center', va='center', fontsize=11)
        plt.colorbar(im, ax=axes[1, 1])

        plt.tight_layout()
        plt.savefig(self.plot_dir / 'review_dimension_analysis.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  评分维度分析图表已保存")

    def _text_analysis(self, df: pd.DataFrame):
        """Part 2: 中文高频词分析"""
        print("\n[Part 2] 中文高频词分析...")

        import re
        import jieba

        # 中文停用词列表
        zh_stopwords = set([
            '的', '了', '是', '我', '很', '在', '也', '都', '就', '不',
            '有', '和', '那', '这', '个', '一', '上', '为', '什么', '么',
            '吗', '呢', '啊', '哦', '嗯', '还', '而', '但', '又', '或',
            '会', '能', '可以', '把', '被', '让', '给', '到', '着', '过',
            '吧', '呀', '哈', '嘿', '哎', '嘛', '吗', '噢', '喔', '哇',
            '比较', '已经', '真的', '觉得', '知道', '应该', '可能', '需要',
            '因为', '所以', '如果', '虽然', '但是', '而且', '然后', '不过',
            '这个', '那个', '这些', '那些', '一个', '一些', '一下', '一点',
            '没', '要', '去', '做', '说', '看', '想', '买',
        ])

        # 筛选有评论文本的低评分订单
        low_text = df[(df['score_group'] == 'low') &
                      (df['review_comment_message'].notna()) &
                      (df['review_comment_message'].str.strip() != '')]['review_comment_message']

        high_text = df[(df['score_group'] == 'high') &
                       (df['review_comment_message'].notna()) &
                       (df['review_comment_message'].str.strip() != '')]['review_comment_message']

        print(f"  低评分有效评论数: {len(low_text)}")
        print(f"  高评分有效评论数: {len(high_text)}")

        def preprocess_text(texts):
            """文本预处理：jieba分词、去停用词"""
            all_words = []
            for text in texts:
                text = str(text).strip()
                # 去除标点和数字
                text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z]', '', text)
                # jieba 分词
                words = list(jieba.cut(text))
                # 去除停用词和短词
                words = [w for w in words if w not in zh_stopwords and len(w) > 1]
                all_words.extend(words)
            return all_words

        # 低评分词频统计
        low_words = preprocess_text(low_text)
        low_freq = Counter(low_words).most_common(50)
        print(f"\n  低评分高频词 Top 20:")
        for word, count in low_freq[:20]:
            print(f"    {word}: {count}")

        # 高评分词频统计
        high_words = preprocess_text(high_text)
        high_freq = Counter(high_words).most_common(50)

        # 生成词云
        try:
            from wordcloud import WordCloud

            low_word_dict = dict(low_freq)
            wc = WordCloud(
                width=800, height=400,
                background_color='white',
                max_words=100,
                colormap='Reds',
                font_path='C:/Windows/Fonts/simhei.ttf'
            ).generate_from_frequencies(low_word_dict)

            plt.figure(figsize=(12, 6))
            plt.imshow(wc, interpolation='bilinear')
            plt.axis('off')
            plt.title('低评分评论词云 (中文)', fontsize=14)
            plt.tight_layout()
            plt.savefig(self.plot_dir / 'wordcloud_low_score.png', dpi=150, bbox_inches='tight')
            plt.close()
            print("  低评分词云已保存")
        except ImportError:
            print("  [警告] wordcloud 未安装，跳过词云生成")

        # 高频词对比表
        low_freq_df = pd.DataFrame(low_freq, columns=['word', 'low_score_count'])
        high_freq_df = pd.DataFrame(high_freq, columns=['word', 'high_score_count'])
        compare_df = low_freq_df.merge(high_freq_df, on='word', how='outer').fillna(0)
        compare_df['low_score_count'] = compare_df['low_score_count'].astype(int)
        compare_df['high_score_count'] = compare_df['high_score_count'].astype(int)
        compare_df['diff_ratio'] = (compare_df['low_score_count'] - compare_df['high_score_count']) / \
                                    (compare_df['low_score_count'] + compare_df['high_score_count'] + 1)
        compare_df = compare_df.sort_values('diff_ratio', ascending=False)

        output_path = self.data_dir / 'review_keywords.csv'
        compare_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"  高频词对比表已保存至: {output_path}")


if __name__ == "__main__":
    config = load_config()
    analyzer = ReviewAnalyzer(config)
    analyzer.run()
