# -*- coding: utf-8 -*-
"""
K-Means 聚类分析脚本
基于用户行为特征进行无监督聚类，发现自然用户群体
包含：肘部法则、轮廓系数、PCA 可视化、聚类画像

可直接运行，也可转为 Jupyter Notebook 使用
"""

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings('ignore')

# 中文字体设置
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# 随机种子
RANDOM_STATE = 42


def load_data() -> pd.DataFrame:
    """加载用户特征数据"""
    data_path = BASE_DIR / 'data' / 'processed' / 'user_features.parquet'
    print(f"正在加载数据: {data_path}")
    df = pd.read_parquet(data_path)
    print(f"数据加载完成，共 {len(df)} 位用户")
    return df


def select_clustering_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    选择聚类特征
    业务含义：选取能代表用户消费行为多维画像的核心特征
    - recency_days: 活跃度/沉睡程度
    - total_orders: 购买频率/忠诚度
    - total_spend: 消费能力/价值贡献
    - avg_review_score: 满意度/体验质量
    - delayed_order_ratio: 物流体验/不满风险
    """
    print("\n📋 选择聚类特征...")

    cluster_features = [
        'recency_days',
        'total_orders',
        'total_spend',
        'avg_review_score',
        'delayed_order_ratio'
    ]

    # 检查哪些特征实际存在
    available = [f for f in cluster_features if f in df.columns]
    missing = [f for f in cluster_features if f not in df.columns]

    if missing:
        print(f"  ⚠️ 以下特征不存在，将被跳过: {missing}")

    if len(available) < 2:
        raise ValueError(f"可用聚类特征不足（至少需要2个），当前可用: {available}")

    X = df[available].copy()

    # 填充缺失值（中位数填充，避免极端值影响）
    for col in X.columns:
        if X[col].isnull().sum() > 0:
            X[col] = X[col].fillna(X[col].median())

    print(f"  已选择 {len(available)} 个特征: {available}")
    print(f"  数据形状: {X.shape}")

    return X


def standardize_features(X: pd.DataFrame):
    """
    StandardScaler 标准化
    业务含义：消除量纲差异，使各特征对聚类贡献均等
    """
    print("\n📋 标准化特征...")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print(f"  标准化完成，均值≈0，标准差≈1")
    return X_scaled, scaler


def find_optimal_k_elbow(X_scaled: np.ndarray, plots_dir: Path) -> list:
    """
    肘部法则确定 K 值
    业务含义：寻找聚类数量的"拐点"，平衡粒度与解释性
    """
    print("\n📊 肘部法则分析 (K=2~8)...")

    k_range = range(2, 9)
    inertias = []

    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
        kmeans.fit(X_scaled)
        inertias.append(kmeans.inertia_)
        print(f"  K={k}: Inertia={kmeans.inertia_:.2f}")

    # 绘制 Inertia 曲线
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(list(k_range), inertias, 'bo-', linewidth=2, markersize=8)
    ax.set_xlabel('聚类数 K', fontsize=12)
    ax.set_ylabel('Inertia (簇内平方和)', fontsize=12)
    ax.set_title('肘部法则 - 确定最优聚类数', fontsize=14)
    ax.set_xticks(list(k_range))
    ax.grid(True, alpha=0.3)

    # 标注各点数值
    for k, inertia in zip(k_range, inertias):
        ax.annotate(f'{inertia:.0f}', (k, inertia),
                    textcoords="offset points", xytext=(0, 10),
                    ha='center', fontsize=9)

    plt.tight_layout()
    save_path = plots_dir / 'kmeans_elbow.png'
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  肘部法则图已保存: {save_path}")

    return inertias


def find_optimal_k_silhouette(X_scaled: np.ndarray, plots_dir: Path) -> int:
    """
    轮廓系数确定最优 K
    业务含义：衡量聚类质量 —— 簇内紧凑度 vs 簇间分离度
    轮廓系数越接近1，聚类效果越好
    """
    print("\n📊 轮廓系数分析 (K=2~8)...")

    k_range = range(2, 9)
    silhouette_scores = []

    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        score = silhouette_score(X_scaled, labels)
        silhouette_scores.append(score)
        print(f"  K={k}: 轮廓系数={score:.4f}")

    # 最优 K（轮廓系数最大）
    best_k = list(k_range)[np.argmax(silhouette_scores)]
    best_score = max(silhouette_scores)
    print(f"\n  ✅ 最优 K = {best_k} (轮廓系数 = {best_score:.4f})")

    # 绘制轮廓系数曲线
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(list(k_range), silhouette_scores, 'rs-', linewidth=2, markersize=8)
    ax.axvline(x=best_k, color='green', linestyle='--', linewidth=1.5,
               label=f'最优 K={best_k}')
    ax.set_xlabel('聚类数 K', fontsize=12)
    ax.set_ylabel('轮廓系数', fontsize=12)
    ax.set_title('轮廓系数 - 聚类质量评估', fontsize=14)
    ax.set_xticks(list(k_range))
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)

    # 标注各点数值
    for k, score in zip(k_range, silhouette_scores):
        ax.annotate(f'{score:.3f}', (k, score),
                    textcoords="offset points", xytext=(0, 10),
                    ha='center', fontsize=9)

    plt.tight_layout()
    save_path = plots_dir / 'kmeans_silhouette.png'
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  轮廓系数图已保存: {save_path}")

    return best_k


def run_final_kmeans(X_scaled: np.ndarray, best_k: int) -> tuple:
    """
    使用最优 K 执行最终聚类
    """
    print(f"\n📋 执行最终 K-Means 聚类 (K={best_k})...")

    kmeans = KMeans(n_clusters=best_k, random_state=RANDOM_STATE, n_init=10)
    labels = kmeans.fit_predict(X_scaled)

    final_score = silhouette_score(X_scaled, labels)
    print(f"  最终轮廓系数: {final_score:.4f}")
    print(f"  各簇样本量: {pd.Series(labels).value_counts().sort_index().to_dict()}")

    return labels, kmeans


def pca_visualization(X_scaled: np.ndarray, labels: np.ndarray, plots_dir: Path):
    """
    PCA 降维到 2D 可视化
    业务含义：将高维用户特征投影到二维平面，直观查看聚类分离效果
    """
    print("\n📊 PCA 降维可视化...")

    pca = PCA(n_components=2, random_state=RANDOM_STATE)
    X_pca = pca.fit_transform(X_scaled)

    explained_var = pca.explained_variance_ratio_
    print(f"  PC1 解释方差: {explained_var[0]:.2%}")
    print(f"  PC2 解释方差: {explained_var[1]:.2%}")
    print(f"  累计解释方差: {sum(explained_var):.2%}")

    # 绘制散点图
    fig, ax = plt.subplots(figsize=(12, 8))

    unique_labels = np.unique(labels)
    colors = plt.cm.Set1(np.linspace(0, 1, len(unique_labels)))

    for label, color in zip(unique_labels, colors):
        mask = labels == label
        ax.scatter(
            X_pca[mask, 0], X_pca[mask, 1],
            c=[color], label=f'簇 {label} (n={mask.sum()})',
            alpha=0.6, s=30, edgecolors='white', linewidth=0.5
        )

    ax.set_xlabel(f'PC1 ({explained_var[0]:.1%})', fontsize=12)
    ax.set_ylabel(f'PC2 ({explained_var[1]:.1%})', fontsize=12)
    ax.set_title('K-Means 聚类结果 - PCA 2D 可视化', fontsize=14)
    ax.legend(fontsize=10, loc='best')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    save_path = plots_dir / 'kmeans_pca_scatter.png'
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  PCA 散点图已保存: {save_path}")


def analyze_cluster_profiles(df: pd.DataFrame, X: pd.DataFrame,
                             labels: np.ndarray, scaler, plots_dir: Path) -> pd.DataFrame:
    """
    各簇特征统计表（聚类中心还原到原始尺度）
    业务含义：理解每个簇的用户特征，为业务命名提供依据
    """
    print("\n📊 各簇特征分析...")

    X_with_labels = X.copy()
    X_with_labels['cluster'] = labels

    # 各簇均值（原始尺度）
    cluster_means = X_with_labels.groupby('cluster').mean()

    print("\n各簇特征均值:")
    print("=" * 60)
    print(cluster_means.round(2).to_string())
    print("=" * 60)

    # 可视化：各簇特征雷达图/热力图
    fig, ax = plt.subplots(figsize=(12, 6))

    # 标准化后的均值用于热力图（方便对比）
    cluster_means_scaled = (cluster_means - cluster_means.mean()) / cluster_means.std()

    sns.heatmap(
        cluster_means_scaled.T, annot=cluster_means.T.round(2).values,
        fmt='', cmap='RdYlGn', center=0, ax=ax,
        xticklabels=[f'簇 {i}' for i in cluster_means.index],
        yticklabels=cluster_means.columns,
        linewidths=0.5
    )
    ax.set_title('各簇特征对比热力图\n(颜色=标准化值, 数字=原始均值)', fontsize=13)

    plt.tight_layout()
    save_path = plots_dir / 'kmeans_cluster_heatmap.png'
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  热力图已保存: {save_path}")

    return cluster_means


def assign_business_names(cluster_means: pd.DataFrame) -> dict:
    """
    各簇业务命名
    业务含义：将数据聚类结果翻译为业务可理解的用户群体标签
    命名逻辑基于各簇在关键维度上的相对表现
    """
    print("\n📋 业务命名...")

    cluster_names = {}
    n_clusters = len(cluster_means)

    # 基于特征排序进行命名
    for cluster_id in cluster_means.index:
        row = cluster_means.loc[cluster_id]
        traits = []

        # 判断消费水平
        if 'total_spend' in row.index:
            spend_rank = cluster_means['total_spend'].rank(ascending=False)
            if spend_rank[cluster_id] == 1:
                traits.append('高价值')
            elif spend_rank[cluster_id] == n_clusters:
                traits.append('低价值')

        # 判断活跃度
        if 'recency_days' in row.index:
            recency_rank = cluster_means['recency_days'].rank(ascending=True)
            if recency_rank[cluster_id] == 1:
                traits.append('活跃')
            elif recency_rank[cluster_id] == n_clusters:
                traits.append('流失高风险')

        # 判断忠诚度
        if 'total_orders' in row.index:
            order_rank = cluster_means['total_orders'].rank(ascending=False)
            if order_rank[cluster_id] == 1:
                traits.append('忠诚')

        # 判断满意度
        if 'avg_review_score' in row.index:
            review_rank = cluster_means['avg_review_score'].rank(ascending=False)
            if review_rank[cluster_id] == n_clusters:
                traits.append('低满意度')

        # 判断物流敏感
        if 'delayed_order_ratio' in row.index:
            delay_rank = cluster_means['delayed_order_ratio'].rank(ascending=False)
            if delay_rank[cluster_id] == 1:
                traits.append('物流敏感')

        # 组合命名
        if not traits:
            traits.append('普通')

        name = '/'.join(traits)
        cluster_names[cluster_id] = name
        print(f"  簇 {cluster_id} → 【{name}】")

    return cluster_names


def cross_tab_with_rfm(df: pd.DataFrame, labels: np.ndarray, plots_dir: Path):
    """
    聚类结果与 RFM 分层交叉表
    业务含义：验证无监督聚类与规则化 RFM 分层的一致性
    """
    print("\n📊 聚类 × RFM 交叉分析...")

    # 查找 RFM 分层列
    segment_col = None
    for col in ['rfm_segment', 'rfm_label', 'customer_segment']:
        if col in df.columns:
            segment_col = col
            break

    if segment_col is None:
        print("  ⚠️ 未找到 RFM 分层列，跳过交叉分析")
        return

    cross_df = pd.crosstab(
        labels, df[segment_col],
        margins=True, margins_name='合计'
    )

    print("\n聚类 × RFM 交叉表:")
    print(cross_df.to_string())

    # 可视化
    cross_df_no_margin = cross_df.iloc[:-1, :-1]

    fig, ax = plt.subplots(figsize=(12, 6))
    cross_df_no_margin.plot(kind='bar', ax=ax, colormap='Set3')
    ax.set_title('K-Means 聚类 × RFM 分层 交叉分布', fontsize=13)
    ax.set_xlabel('聚类簇')
    ax.set_ylabel('用户数')
    ax.legend(title='RFM 分层', bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.tick_params(axis='x', rotation=0)

    plt.tight_layout()
    save_path = plots_dir / 'kmeans_rfm_crosstab.png'
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  交叉分布图已保存: {save_path}")


def save_cluster_labels(df: pd.DataFrame, labels: np.ndarray, cluster_names: dict):
    """
    保存聚类标签到用户特征文件
    """
    print("\n💾 保存聚类结果...")

    df['kmeans_cluster'] = labels
    df['kmeans_cluster_name'] = df['kmeans_cluster'].map(cluster_names)

    output_path = BASE_DIR / 'data' / 'processed' / 'user_features.parquet'
    df.to_parquet(output_path, index=False)
    print(f"  聚类标签已追加保存至: {output_path}")

    # 同时保存簇统计摘要
    summary_path = BASE_DIR / 'data' / 'processed' / 'kmeans_cluster_summary.csv'
    summary = df.groupby('kmeans_cluster_name').agg({
        'kmeans_cluster': 'count',
        'total_spend': 'mean' if 'total_spend' in df.columns else 'count',
        'total_orders': 'mean' if 'total_orders' in df.columns else 'count',
        'recency_days': 'mean' if 'recency_days' in df.columns else 'count',
    }).rename(columns={'kmeans_cluster': '用户数'})
    summary.to_csv(summary_path, encoding='utf-8-sig')
    print(f"  簇摘要已保存: {summary_path}")


def main():
    """主执行函数"""
    print("=" * 60)
    print("K-Means 聚类分析")
    print("=" * 60)

    # 创建图表输出目录
    plots_dir = BASE_DIR / 'data' / 'processed' / 'plots'
    plots_dir.mkdir(parents=True, exist_ok=True)

    # 1. 加载数据
    df = load_data()

    # 2. 选择聚类特征
    X = select_clustering_features(df)

    # 3. 标准化
    X_scaled, scaler = standardize_features(X)

    # 4. 肘部法则
    inertias = find_optimal_k_elbow(X_scaled, plots_dir)

    # 5. 轮廓系数确定最优 K
    best_k = find_optimal_k_silhouette(X_scaled, plots_dir)

    # 6. 最终聚类
    labels, kmeans_model = run_final_kmeans(X_scaled, best_k)

    # 7. PCA 可视化
    pca_visualization(X_scaled, labels, plots_dir)

    # 8. 各簇特征分析
    cluster_means = analyze_cluster_profiles(df, X, labels, scaler, plots_dir)

    # 9. 业务命名
    cluster_names = assign_business_names(cluster_means)

    # 10. 与 RFM 交叉分析
    cross_tab_with_rfm(df, labels, plots_dir)

    # 11. 保存聚类标签
    save_cluster_labels(df, labels, cluster_names)

    print("\n" + "=" * 60)
    print(f"✅ K-Means 聚类分析完成！最优 K={best_k}")
    print(f"   所有图表已保存至: {plots_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
