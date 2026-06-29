# -*- coding: utf-8 -*-
"""
RFM 用户分层分析脚本
基于 Recency（最近购买）、Frequency（购买频率）、Monetary（消费金额）三维度
对用户进行价值分层，输出运营策略建议

可直接运行，也可转为 Jupyter Notebook 使用
"""

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

warnings.filterwarnings('ignore')

# 中文字体设置
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 项目根目录
BASE_DIR = Path(__file__).parent.parent


def load_data() -> pd.DataFrame:
    """加载用户特征数据"""
    data_path = BASE_DIR / 'data' / 'processed' / 'user_features.parquet'
    print(f"正在加载数据: {data_path}")
    df = pd.read_parquet(data_path)
    print(f"数据加载完成，共 {len(df)} 位用户")
    return df


def plot_rfm_distributions(df: pd.DataFrame, plots_dir: Path):
    """
    展示 RFM 各维度分布（直方图）
    业务含义：了解用户群体在 R/F/M 三个维度的整体分布形态，
    判断是否存在明显的长尾效应或极端值
    """
    print("\n📊 绘制 RFM 各维度分布...")

    # RFM 对应的列名（根据特征工程生成的列名）
    rfm_cols = {
        'recency_days': 'R - 最近购买距今天数',
        'total_orders': 'F - 购买频次',
        'total_spend': 'M - 累计消费金额'
    }

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    for ax, (col, title) in zip(axes, rfm_cols.items()):
        if col not in df.columns:
            ax.set_title(f'{title}\n(列不存在)')
            continue

        data = df[col].dropna()
        ax.hist(data, bins=50, color='#2196F3', edgecolor='white', alpha=0.8)
        ax.axvline(data.median(), color='red', linestyle='--', linewidth=1.5,
                   label=f'中位数: {data.median():.1f}')
        ax.set_title(title, fontsize=13)
        ax.set_xlabel(col)
        ax.set_ylabel('用户数')
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.suptitle('RFM 各维度分布', fontsize=15, y=1.02)
    plt.tight_layout()

    save_path = plots_dir / 'rfm_distributions.png'
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  已保存: {save_path}")


def plot_rfm_segment_overview(df: pd.DataFrame, plots_dir: Path):
    """
    展示 RFM 分层结果（饼图 + 柱状图）
    业务含义：了解各价值层级的用户占比，判断高价值用户池大小
    """
    print("\n📊 绘制 RFM 分层总览...")

    # 查找 RFM 分层列
    segment_col = None
    for col in ['rfm_segment', 'rfm_label', 'customer_segment']:
        if col in df.columns:
            segment_col = col
            break

    if segment_col is None:
        print("  ⚠️ 未找到 RFM 分层列，跳过此图")
        return segment_col

    segment_counts = df[segment_col].value_counts()

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # 饼图：各层级占比
    colors = plt.cm.Set3(np.linspace(0, 1, len(segment_counts)))
    axes[0].pie(
        segment_counts.values,
        labels=segment_counts.index,
        autopct='%1.1f%%',
        colors=colors,
        startangle=90,
        textprops={'fontsize': 10}
    )
    axes[0].set_title('RFM 用户分层占比', fontsize=13)

    # 柱状图：各层级用户数
    sns.barplot(x=segment_counts.index, y=segment_counts.values, ax=axes[1], palette='Set2')
    axes[1].set_title('各层级用户数量', fontsize=13)
    axes[1].set_xlabel('用户层级')
    axes[1].set_ylabel('用户数')
    axes[1].tick_params(axis='x', rotation=45)

    # 在柱状图上标注数字
    for i, v in enumerate(segment_counts.values):
        axes[1].text(i, v + max(segment_counts.values) * 0.01, str(v),
                     ha='center', fontsize=9)

    plt.tight_layout()
    save_path = plots_dir / 'rfm_segment_overview.png'
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  已保存: {save_path}")

    return segment_col


def generate_segment_profile(df: pd.DataFrame, segment_col: str, plots_dir: Path):
    """
    各层级用户画像统计表
    业务含义：量化不同层级用户的行为特征差异，为运营策略提供数据支撑
    """
    print("\n📊 生成用户画像统计表...")

    if segment_col is None:
        print("  ⚠️ 无分层列，跳过")
        return None

    # 核心统计指标
    agg_dict = {}
    if 'total_spend' in df.columns:
        agg_dict['total_spend'] = 'mean'
    if 'total_orders' in df.columns:
        agg_dict['total_orders'] = 'mean'
    if 'recency_days' in df.columns:
        agg_dict['recency_days'] = 'mean'
    if 'is_churned' in df.columns:
        agg_dict['is_churned'] = 'mean'

    if not agg_dict:
        print("  ⚠️ 缺少必要指标列")
        return None

    # 添加用户数
    profile = df.groupby(segment_col).agg(agg_dict)
    profile['用户数'] = df.groupby(segment_col).size()
    profile['用户占比'] = profile['用户数'] / len(df)

    # 重命名列
    rename_map = {
        'total_spend': '平均消费金额',
        'total_orders': '平均购买频次',
        'recency_days': '平均最近购买天数',
        'is_churned': '流失率'
    }
    profile = profile.rename(columns=rename_map)

    print("\n" + "=" * 60)
    print("各层级用户画像统计表")
    print("=" * 60)
    print(profile.round(2).to_string())
    print("=" * 60)

    # 保存为 CSV
    profile_path = BASE_DIR / 'data' / 'processed' / 'rfm_segment_profile.csv'
    profile.to_csv(profile_path, encoding='utf-8-sig')
    print(f"  统计表已保存: {profile_path}")

    return profile


def plot_segment_kpi_comparison(df: pd.DataFrame, segment_col: str, plots_dir: Path):
    """
    层级间 KPI 对比可视化
    业务含义：直观对比各层级在关键业务指标上的差异
    """
    print("\n📊 绘制层级间 KPI 对比...")

    if segment_col is None:
        print("  ⚠️ 无分层列，跳过")
        return

    kpi_cols = {
        'total_spend': '累计消费金额',
        'total_orders': '购买频次',
        'recency_days': '最近购买天数',
        'is_churned': '流失率'
    }

    available_kpis = {k: v for k, v in kpi_cols.items() if k in df.columns}

    if not available_kpis:
        print("  ⚠️ 无可用 KPI 列")
        return

    n_kpis = len(available_kpis)
    fig, axes = plt.subplots(1, n_kpis, figsize=(5 * n_kpis, 6))
    if n_kpis == 1:
        axes = [axes]

    for ax, (col, label) in zip(axes, available_kpis.items()):
        order = df.groupby(segment_col)[col].mean().sort_values(ascending=False).index
        sns.boxplot(data=df, x=segment_col, y=col, ax=ax, order=order, palette='Set2')
        ax.set_title(f'各层级 {label} 对比', fontsize=12)
        ax.set_xlabel('')
        ax.set_ylabel(label)
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, alpha=0.3, axis='y')

    plt.suptitle('RFM 层级间 KPI 对比', fontsize=14, y=1.02)
    plt.tight_layout()

    save_path = plots_dir / 'rfm_kpi_comparison.png'
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  已保存: {save_path}")


def generate_strategy_recommendations(df: pd.DataFrame, segment_col: str):
    """
    输出各层级差异化运营策略建议
    业务含义：将数据洞察转化为可执行的运营动作
    """
    print("\n" + "=" * 60)
    print("📋 运营策略建议")
    print("=" * 60)

    if segment_col is None:
        print("  未找到 RFM 分层列，使用通用策略建议框架")
        _print_generic_strategies()
        return

    segments = df[segment_col].unique()

    # 预定义策略模板（按常见 RFM 分层命名）
    strategy_map = {
        # 高价值用户
        '重要价值客户': {
            'description': 'R低F高M高 - 最近购买、频次高、消费高',
            'strategy': [
                '• VIP 专属服务和权益维护',
                '• 新品优先体验、专属折扣',
                '• 一对一客户经理维系关系',
                '• 会员积分加倍/生日特权'
            ]
        },
        '重要发展客户': {
            'description': 'R低F低M高 - 最近购买、频次低但消费高',
            'strategy': [
                '• 关联推荐提升购买频次',
                '• 满减/凑单优惠刺激复购',
                '• 个性化商品推荐（基于历史偏好）',
                '• 购后关怀短信/邮件触达'
            ]
        },
        '重要保持客户': {
            'description': 'R高F高M高 - 许久未购、但历史频次高消费高',
            'strategy': [
                '• 紧急召回！大额优惠券/限时折扣',
                '• 了解流失原因（问卷/客服回访）',
                '• 推送其历史偏好品类的爆款',
                '• 积分即将过期提醒'
            ]
        },
        '重要挽留客户': {
            'description': 'R高F低M高 - 许久未购、消费高但频次低',
            'strategy': [
                '• 高价值挽回专项（电话回访）',
                '• 大额无门槛优惠券',
                '• 竞品分析，了解用户是否转移',
                '• 情感营销（品牌故事/用户案例）'
            ]
        },
        '一般价值客户': {
            'description': 'R低F低M低 - 最近购买但消费和频次都一般',
            'strategy': [
                '• 新手引导和商品教育',
                '• 首单后续跟进（使用体验询问）',
                '• 小额满减培养购物习惯',
                '• 推送高性价比爆款'
            ]
        },
        '流失客户': {
            'description': '长期未购买的低价值用户',
            'strategy': [
                '• 低成本自动化触达（短信/Push）',
                '• 大促节点批量召回',
                '• 评估召回 ROI，低回报者降低投入',
                '• 清理无效用户，优化营销成本'
            ]
        }
    }

    for seg in segments:
        seg_count = (df[segment_col] == seg).sum()
        seg_ratio = seg_count / len(df) * 100

        print(f"\n┌─── 【{seg}】 ({seg_count}人, {seg_ratio:.1f}%)")

        if seg in strategy_map:
            info = strategy_map[seg]
            print(f"│  特征: {info['description']}")
            print(f"│  运营策略:")
            for s in info['strategy']:
                print(f"│    {s}")
        else:
            print(f"│  特征: 待分析")
            print(f"│  运营策略:")
            print(f"│    • 根据该群体的具体 RFM 特征制定针对性策略")
            print(f"│    • 建议进一步分析该群体的品类偏好和购买时间规律")

        print(f"└{'─' * 50}")

    print("\n" + "=" * 60)


def _print_generic_strategies():
    """通用运营策略框架"""
    strategies = {
        '高价值活跃用户': '维系关系，VIP权益，新品优先体验',
        '高价值沉睡用户': '紧急召回，大额优惠，了解流失原因',
        '潜力发展用户': '频次提升，关联推荐，购后关怀',
        '低价值活跃用户': '客单价提升，凑单优惠，品类扩展',
        '低价值流失用户': '低成本自动化触达，大促批量召回'
    }

    for seg, strategy in strategies.items():
        print(f"  【{seg}】: {strategy}")

    print("\n" + "=" * 60)


def main():
    """主执行函数"""
    print("=" * 60)
    print("RFM 用户分层分析")
    print("=" * 60)

    # 创建图表输出目录
    plots_dir = BASE_DIR / 'data' / 'processed' / 'plots'
    plots_dir.mkdir(parents=True, exist_ok=True)

    # 1. 加载数据
    df = load_data()

    # 2. RFM 维度分布
    plot_rfm_distributions(df, plots_dir)

    # 3. RFM 分层总览
    segment_col = plot_rfm_segment_overview(df, plots_dir)

    # 4. 用户画像统计表
    profile = generate_segment_profile(df, segment_col, plots_dir)

    # 5. 层级间 KPI 对比
    plot_segment_kpi_comparison(df, segment_col, plots_dir)

    # 6. 运营策略建议
    generate_strategy_recommendations(df, segment_col)

    print("\n✅ RFM 分层分析完成！所有图表已保存至:", plots_dir)


if __name__ == "__main__":
    main()
