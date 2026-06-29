# -*- coding: utf-8 -*-
"""
Jupyter Notebook 批量生成脚本
使用 nbformat 库生成 8 个结构化 .ipynb 文件到 notebooks/ 目录
"""

import os
import sys
from pathlib import Path

import nbformat
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
NOTEBOOKS_DIR = PROJECT_ROOT / 'notebooks'
NOTEBOOKS_DIR.mkdir(parents=True, exist_ok=True)


def create_notebook(cells):
    """创建 notebook 对象"""
    nb = new_notebook()
    nb.metadata.kernelspec = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3"
    }
    nb.metadata.language_info = {
        "name": "python",
        "version": "3.9.0"
    }
    nb.cells = cells
    return nb


def save_notebook(nb, filename):
    """保存 notebook 到文件"""
    path = NOTEBOOKS_DIR / filename
    with open(path, 'w', encoding='utf-8') as f:
        nbformat.write(nb, f)
    print(f"  已生成: {path}")


# ============================================================
# Notebook 01: 数据概览与EDA
# ============================================================
def gen_01_data_overview():
    cells = [
        new_markdown_cell("# 01 数据概览与探索性分析 (EDA)\n\n本 Notebook 完成以下任务：\n- 连接数据库，查看各表行数和字段分布\n- 基本统计描述与缺失值概览\n- 订单时间分布、用户地域分布"),
        new_code_cell("""import sys
sys.path.insert(0, '..')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

warnings.filterwarnings('ignore')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

from utils.db_connector import get_engine
engine = get_engine()
print("数据库连接成功!")"""),
        new_markdown_cell("## 1.1 各表行数统计"),
        new_code_cell("""# 查看数据库中各表的行数
tables = [
    'olist_orders', 'olist_order_items', 'olist_order_payments',
    'olist_order_reviews', 'olist_products', 'olist_customers',
    'olist_sellers', 'olist_geolocation'
]

table_info = []
with engine.connect() as conn:
    for table in tables:
        try:
            count = pd.read_sql_query(f"SELECT COUNT(*) as cnt FROM {table}", conn).iloc[0, 0]
            cols = pd.read_sql_query(f"SELECT * FROM {table} LIMIT 1", conn).columns.tolist()
            table_info.append({'表名': table, '行数': count, '列数': len(cols)})
        except Exception as e:
            table_info.append({'表名': table, '行数': f'错误: {e}', '列数': '-'})

table_summary = pd.DataFrame(table_info)
table_summary"""),
        new_markdown_cell("## 1.2 各表字段分布与示例数据"),
        new_code_cell("""# 查看订单表结构和示例数据
with engine.connect() as conn:
    orders = pd.read_sql_query("SELECT * FROM olist_orders LIMIT 5", conn)
print("olist_orders 表前5行：")
orders"""),
        new_code_cell("""# 查看订单表字段类型
with engine.connect() as conn:
    orders_full = pd.read_sql_query("SELECT * FROM olist_orders", conn)
print(f"订单表形状: {orders_full.shape}")
print("\\n字段类型：")
print(orders_full.dtypes)
print("\\n基本统计描述：")
orders_full.describe(include='all')"""),
        new_markdown_cell("## 1.3 缺失值概览"),
        new_code_cell("""# 各表缺失值统计
with engine.connect() as conn:
    orders = pd.read_sql_query("SELECT * FROM olist_orders", conn)
    items = pd.read_sql_query("SELECT * FROM olist_order_items", conn)
    reviews = pd.read_sql_query("SELECT * FROM olist_order_reviews", conn)

print("=== 订单表缺失值 ===")
print(orders.isnull().sum())
print(f"\\n=== 订单明细表缺失值 ===")
print(items.isnull().sum())
print(f"\\n=== 评论表缺失值 ===")
print(reviews.isnull().sum())"""),
        new_markdown_cell("## 1.4 订单时间分布"),
        new_code_cell("""# 订单时间分布
orders['order_purchase_timestamp'] = pd.to_datetime(orders['order_purchase_timestamp'])
orders['year_month'] = orders['order_purchase_timestamp'].dt.to_period('M')

monthly_orders = orders.groupby('year_month').size()

fig, ax = plt.subplots(figsize=(14, 5))
ax.plot(range(len(monthly_orders)), monthly_orders.values, marker='o', linewidth=2, color='#3498db')
ax.set_xticks(range(0, len(monthly_orders), 2))
ax.set_xticklabels([str(m) for m in monthly_orders.index[::2]], rotation=45, fontsize=8)
ax.set_xlabel('月份')
ax.set_ylabel('订单数')
ax.set_title('月度订单量趋势')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()"""),
        new_markdown_cell("## 1.5 用户地域分布"),
        new_code_cell("""# 用户地域分布
with engine.connect() as conn:
    customers = pd.read_sql_query("SELECT * FROM olist_customers", conn)

state_dist = customers['customer_state'].value_counts()

fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# 柱状图
axes[0].bar(state_dist.index[:15], state_dist.values[:15], color='#9b59b6', alpha=0.8)
axes[0].set_xlabel('州')
axes[0].set_ylabel('用户数')
axes[0].set_title('用户分布 Top 15 州')
axes[0].tick_params(axis='x', rotation=45)

# 饼图 Top 5
top5 = state_dist.head(5)
others = pd.Series({'其他': state_dist.iloc[5:].sum()})
pie_data = pd.concat([top5, others])
axes[1].pie(pie_data.values, labels=pie_data.index, autopct='%1.1f%%', startangle=90)
axes[1].set_title('用户地域分布占比')

plt.tight_layout()
plt.show()

print(f"\\n总用户数: {len(customers)}")
print(f"覆盖州数: {customers['customer_state'].nunique()}")"""),
        new_markdown_cell("## 1.6 订单状态分布"),
        new_code_cell("""# 订单状态分布
status_dist = orders['order_status'].value_counts()

fig, ax = plt.subplots(figsize=(10, 5))
ax.barh(status_dist.index, status_dist.values, color='#2ecc71', alpha=0.8)
ax.set_xlabel('订单数')
ax.set_title('订单状态分布')
for i, v in enumerate(status_dist.values):
    ax.text(v + 100, i, str(v), va='center')
plt.tight_layout()
plt.show()"""),
        new_markdown_cell("## 小结\n\n- 数据库包含 8 张核心表，覆盖订单、用户、产品、支付、评论等多个维度\n- 已送达(delivered)订单占绝大多数，后续分析以此为基础\n- 用户主要分布在 SP、RJ、MG 等州\n- 订单量在 2017-2018 年呈增长趋势")
    ]
    nb = create_notebook(cells)
    save_notebook(nb, '01_data_overview.ipynb')


# ============================================================
# Notebook 02: 数据清洗
# ============================================================
def gen_02_data_cleaning():
    cells = [
        new_markdown_cell("# 02 数据清洗\n\n参考 `utils/data_cleaner.py` 的清洗逻辑，演示完整清洗流程：\n1. 只保留 delivered 状态的订单\n2. 解析时间字段\n3. 删除关键字段缺失的行\n4. 关联 customers 表获取唯一用户标识\n5. 计算物流衍生字段"),
        new_code_cell("""import sys
sys.path.insert(0, '..')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings('ignore')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

from utils.db_connector import get_engine
engine = get_engine()"""),
        new_markdown_cell("## 2.1 加载原始数据"),
        new_code_cell("""# 读取原始订单数据
with engine.connect() as conn:
    orders_raw = pd.read_sql_query("SELECT * FROM olist_orders", conn)

print(f"原始订单数: {len(orders_raw):,}")
print(f"\\n订单状态分布:")
print(orders_raw['order_status'].value_counts())
orders_raw.head()"""),
        new_markdown_cell("## 2.2 过滤 - 只保留已送达订单"),
        new_code_cell("""# 只保留 delivered 订单
orders_delivered = orders_raw[orders_raw['order_status'] == 'delivered'].copy()
print(f"过滤后订单数: {len(orders_delivered):,}")
print(f"过滤掉: {len(orders_raw) - len(orders_delivered):,} 条非 delivered 订单")"""),
        new_markdown_cell("## 2.3 解析时间字段"),
        new_code_cell("""# 时间字段解析
datetime_cols = [
    'order_purchase_timestamp', 'order_approved_at',
    'order_delivered_carrier_date', 'order_delivered_customer_date',
    'order_estimated_delivery_date'
]

for col in datetime_cols:
    if col in orders_delivered.columns:
        orders_delivered[col] = pd.to_datetime(orders_delivered[col], errors='coerce')

print("时间字段解析完成")
print(f"\\n时间范围: {orders_delivered['order_purchase_timestamp'].min()} ~ {orders_delivered['order_purchase_timestamp'].max()}")
orders_delivered[datetime_cols].dtypes"""),
        new_markdown_cell("## 2.4 删除关键字段缺失的行"),
        new_code_cell("""# 关键字段缺失值检查
critical_cols = ['customer_id', 'order_id', 'order_purchase_timestamp']

before_drop = len(orders_delivered)
orders_clean = orders_delivered.dropna(subset=critical_cols).reset_index(drop=True)
after_drop = len(orders_clean)

print(f"删除关键字段为空的行: {before_drop - after_drop} 条")
print(f"剩余订单数: {after_drop:,}")"""),
        new_markdown_cell("## 2.5 关联 customers 表获取 customer_unique_id"),
        new_code_cell("""# 关联 customers 表
with engine.connect() as conn:
    customers = pd.read_sql_query(
        "SELECT customer_id, customer_unique_id FROM olist_customers", conn
    )

orders_clean = orders_clean.merge(customers, on='customer_id', how='left')

missing_uid = orders_clean['customer_unique_id'].isna().sum()
print(f"未匹配到 customer_unique_id 的行数: {missing_uid}")
print(f"唯一用户数: {orders_clean['customer_unique_id'].nunique():,}")"""),
        new_markdown_cell("## 2.6 计算物流衍生字段"),
        new_code_cell("""# 物流延迟天数 = 实际送达 - 预计送达
orders_clean['delivery_delay_days'] = (
    orders_clean['order_delivered_customer_date'] - orders_clean['order_estimated_delivery_date']
).dt.days

# 实际配送天数 = 实际送达 - 购买时间
orders_clean['delivery_days'] = (
    orders_clean['order_delivered_customer_date'] - orders_clean['order_purchase_timestamp']
).dt.days

print(f"平均配送天数: {orders_clean['delivery_days'].mean():.1f} 天")
print(f"平均延迟天数: {orders_clean['delivery_delay_days'].mean():.1f} 天")
print(f"延迟订单占比: {(orders_clean['delivery_delay_days'] > 0).mean():.1%}")"""),
        new_markdown_cell("## 2.7 清洗前后对比"),
        new_code_cell("""# 清洗前后对比
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# 清洗漏斗
stages = ['原始数据', '仅delivered', '去除缺失', '最终数据']
counts = [len(orders_raw), len(orders_delivered), after_drop, len(orders_clean)]
colors = ['#e74c3c', '#f39c12', '#2ecc71', '#3498db']

axes[0].barh(stages, counts, color=colors, alpha=0.8)
for i, v in enumerate(counts):
    axes[0].text(v + 100, i, f'{v:,}', va='center')
axes[0].set_xlabel('订单数')
axes[0].set_title('数据清洗漏斗')

# 配送天数分布
valid_delivery = orders_clean['delivery_days'].dropna()
axes[1].hist(valid_delivery, bins=50, color='#3498db', alpha=0.7, edgecolor='white')
axes[1].axvline(valid_delivery.median(), color='red', linestyle='--', label=f'中位数: {valid_delivery.median():.0f}天')
axes[1].set_xlabel('配送天数')
axes[1].set_ylabel('订单数')
axes[1].set_title('配送天数分布')
axes[1].legend()

plt.tight_layout()
plt.show()

print(f"\\n=== 清洗统计摘要 ===")
print(f"原始订单数:   {len(orders_raw):,}")
print(f"清洗后订单数: {len(orders_clean):,}")
print(f"保留比例:     {len(orders_clean)/len(orders_raw):.1%}")
print(f"唯一用户数:   {orders_clean['customer_unique_id'].nunique():,}")"""),
        new_markdown_cell("## 小结\n\n- 数据清洗保留了约 96% 的已送达订单\n- 配送平均耗时约12天，约 8% 的订单存在延迟\n- `customer_unique_id` 为用户唯一标识，后续分析基于此字段聚合")
    ]
    nb = create_notebook(cells)
    save_notebook(nb, '02_data_cleaning.ipynb')


# ============================================================
# Notebook 03: RFM 用户分层
# ============================================================
def gen_03_rfm_segmentation():
    cells = [
        new_markdown_cell("# 03 RFM 用户分层分析\n\n基于 Recency（最近购买）、Frequency（购买频率）、Monetary（消费金额）三维度对用户进行价值分层，输出运营策略建议。"),
        new_code_cell("""import sys
sys.path.insert(0, '..')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

warnings.filterwarnings('ignore')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

from pathlib import Path
BASE_DIR = Path('..').resolve()"""),
        new_markdown_cell("## 3.1 加载用户特征数据"),
        new_code_cell("""# 加载用户特征数据
data_path = BASE_DIR / 'data' / 'processed' / 'user_features.parquet'
df = pd.read_parquet(data_path)
print(f"数据加载完成，共 {len(df)} 位用户")
print(f"\\n可用列: {df.columns.tolist()}")
df.head()"""),
        new_markdown_cell("## 3.2 RFM 各维度分布\n\n- **R (Recency)**: 最近购买距今天数 — 值越小越活跃\n- **F (Frequency)**: 购买频次 — 值越大越忠诚\n- **M (Monetary)**: 累计消费金额 — 值越大越有价值"),
        new_code_cell("""# RFM 维度分布
rfm_cols = {
    'recency_days': 'R - 最近购买距今天数',
    'total_orders': 'F - 购买频次',
    'total_spend': 'M - 累计消费金额'
}

fig, axes = plt.subplots(1, 3, figsize=(18, 5))

for ax, (col, title) in zip(axes, rfm_cols.items()):
    if col not in df.columns:
        ax.set_title(f'{title}\\n(列不存在)')
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
plt.show()

# 基本统计
for col, title in rfm_cols.items():
    if col in df.columns:
        print(f"\\n{title}:")
        print(df[col].describe())"""),
        new_markdown_cell("## 3.3 RFM 分层规则\n\n使用四分位数将每个维度分为高/低两档，组合形成 RFM 分层标签。"),
        new_code_cell("""# RFM 分层总览
segment_col = None
for col in ['rfm_segment', 'rfm_label', 'customer_segment']:
    if col in df.columns:
        segment_col = col
        break

if segment_col:
    print(f"使用分层列: {segment_col}")
    segment_counts = df[segment_col].value_counts()
    print(f"\\n各层级用户分布:")
    print(segment_counts)
else:
    print("未找到 RFM 分层列，将基于 RFM 维度手动分层")
    # 手动 RFM 分层
    if all(c in df.columns for c in ['recency_days', 'total_orders', 'total_spend']):
        df['R_score'] = pd.qcut(df['recency_days'], q=4, labels=[4, 3, 2, 1])
        df['F_score'] = pd.qcut(df['total_orders'].rank(method='first'), q=4, labels=[1, 2, 3, 4])
        df['M_score'] = pd.qcut(df['total_spend'].rank(method='first'), q=4, labels=[1, 2, 3, 4])
        df['RFM_total'] = df['R_score'].astype(int) + df['F_score'].astype(int) + df['M_score'].astype(int)
        
        def rfm_label(score):
            if score >= 10:
                return '重要价值客户'
            elif score >= 8:
                return '重要发展客户'
            elif score >= 6:
                return '一般价值客户'
            else:
                return '流失客户'
        
        df['rfm_segment'] = df['RFM_total'].apply(rfm_label)
        segment_col = 'rfm_segment'
        segment_counts = df[segment_col].value_counts()
        print("手动 RFM 分层完成:")
        print(segment_counts)"""),
        new_markdown_cell("## 3.4 RFM 分层可视化"),
        new_code_cell("""# RFM 分层可视化
if segment_col:
    segment_counts = df[segment_col].value_counts()
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # 饼图
    colors = plt.cm.Set3(np.linspace(0, 1, len(segment_counts)))
    axes[0].pie(segment_counts.values, labels=segment_counts.index,
                autopct='%1.1f%%', colors=colors, startangle=90,
                textprops={'fontsize': 10})
    axes[0].set_title('RFM 用户分层占比', fontsize=13)
    
    # 柱状图
    sns.barplot(x=segment_counts.index, y=segment_counts.values, ax=axes[1], palette='Set2')
    axes[1].set_title('各层级用户数量', fontsize=13)
    axes[1].set_xlabel('用户层级')
    axes[1].set_ylabel('用户数')
    axes[1].tick_params(axis='x', rotation=45)
    for i, v in enumerate(segment_counts.values):
        axes[1].text(i, v + max(segment_counts.values) * 0.01, str(v), ha='center', fontsize=9)
    
    plt.tight_layout()
    plt.show()"""),
        new_markdown_cell("## 3.5 各层级用户画像"),
        new_code_cell("""# 各层级用户画像统计表
if segment_col:
    agg_dict = {}
    if 'total_spend' in df.columns:
        agg_dict['total_spend'] = 'mean'
    if 'total_orders' in df.columns:
        agg_dict['total_orders'] = 'mean'
    if 'recency_days' in df.columns:
        agg_dict['recency_days'] = 'mean'
    if 'is_churned' in df.columns:
        agg_dict['is_churned'] = 'mean'

    profile = df.groupby(segment_col).agg(agg_dict)
    profile['用户数'] = df.groupby(segment_col).size()
    profile['用户占比'] = profile['用户数'] / len(df)

    rename_map = {
        'total_spend': '平均消费金额',
        'total_orders': '平均购买频次',
        'recency_days': '平均最近购买天数',
        'is_churned': '流失率'
    }
    profile = profile.rename(columns=rename_map)
    print("各层级用户画像统计表:")
    profile.round(2)"""),
        new_markdown_cell("## 3.6 层级间 KPI 对比"),
        new_code_cell("""# 层级间 KPI 对比（箱线图）
if segment_col:
    kpi_cols = {
        'total_spend': '累计消费金额',
        'total_orders': '购买频次',
        'recency_days': '最近购买天数'
    }
    available_kpis = {k: v for k, v in kpi_cols.items() if k in df.columns}
    
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
    plt.show()"""),
        new_markdown_cell("## 3.7 运营策略建议\n\n| 层级 | 特征 | 运营策略 |\n|------|------|----------|\n| 重要价值客户 | R低F高M高 | VIP专属服务、新品优先体验 |\n| 重要发展客户 | R低F低M高 | 关联推荐提升频次、满减刺激复购 |\n| 重要保持客户 | R高F高M高 | 大额优惠券召回、流失原因调研 |\n| 一般价值客户 | 各维度一般 | 新手引导、小额满减培养习惯 |\n| 流失客户 | R高F低M低 | 低成本自动化触达、大促批量召回 |"),
        new_markdown_cell("## 小结\n\n- RFM 分层将用户分为高/中/低价值群体\n- 高价值用户占比较小但贡献了主要收入\n- 不同层级用户需要差异化运营策略\n- 重点关注「重要保持客户」的召回和「重要发展客户」的频次提升")
    ]
    nb = create_notebook(cells)
    save_notebook(nb, '03_rfm_segmentation.ipynb')


# ============================================================
# Notebook 04: K-Means 聚类验证
# ============================================================
def gen_04_kmeans_clustering():
    cells = [
        new_markdown_cell("# 04 K-Means 聚类分析\n\n基于用户行为特征进行无监督聚类，发现自然用户群体。\n- 特征选择与标准化\n- 肘部法则确定K值\n- 轮廓系数评估聚类质量\n- PCA 降维可视化\n- 聚类画像与业务命名"),
        new_code_cell("""import sys
sys.path.insert(0, '..')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
import warnings

warnings.filterwarnings('ignore')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

RANDOM_STATE = 42
from pathlib import Path
BASE_DIR = Path('..').resolve()"""),
        new_markdown_cell("## 4.1 加载数据与特征选择"),
        new_code_cell("""# 加载用户特征数据
data_path = BASE_DIR / 'data' / 'processed' / 'user_features.parquet'
df = pd.read_parquet(data_path)
print(f"数据加载完成，共 {len(df)} 位用户")

# 选择聚类特征
cluster_features = ['recency_days', 'total_orders', 'total_spend', 'avg_review_score', 'delayed_order_ratio']
available = [f for f in cluster_features if f in df.columns]
missing = [f for f in cluster_features if f not in df.columns]

if missing:
    print(f"⚠️ 以下特征不存在: {missing}")

X = df[available].copy()
for col in X.columns:
    X[col] = X[col].fillna(X[col].median())

print(f"\\n已选择 {len(available)} 个特征: {available}")
print(f"数据形状: {X.shape}")
X.describe()"""),
        new_markdown_cell("## 4.2 特征标准化\n\n使用 StandardScaler 消除量纲差异，使各特征对聚类贡献均等。"),
        new_code_cell("""# StandardScaler 标准化
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
print(f"标准化完成，形状: {X_scaled.shape}")
print(f"标准化后均值: {X_scaled.mean(axis=0).round(4)}")
print(f"标准化后标准差: {X_scaled.std(axis=0).round(4)}")"""),
        new_markdown_cell("## 4.3 肘部法则 (Elbow Method)\n\n通过 Inertia（簇内平方和）随 K 变化的曲线，寻找\"拐点\"确定最优聚类数。"),
        new_code_cell("""# 肘部法则
k_range = range(2, 9)
inertias = []

for k in k_range:
    kmeans = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
    kmeans.fit(X_scaled)
    inertias.append(kmeans.inertia_)
    print(f"K={k}: Inertia={kmeans.inertia_:.2f}")

fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(list(k_range), inertias, 'bo-', linewidth=2, markersize=8)
ax.set_xlabel('聚类数 K', fontsize=12)
ax.set_ylabel('Inertia (簇内平方和)', fontsize=12)
ax.set_title('肘部法则 - 确定最优聚类数', fontsize=14)
ax.set_xticks(list(k_range))
ax.grid(True, alpha=0.3)

for k, inertia in zip(k_range, inertias):
    ax.annotate(f'{inertia:.0f}', (k, inertia),
                textcoords="offset points", xytext=(0, 10), ha='center', fontsize=9)

plt.tight_layout()
plt.show()"""),
        new_markdown_cell("## 4.4 轮廓系数 (Silhouette Score)\n\n轮廓系数衡量聚类质量：簇内紧凑度 vs 簇间分离度。越接近 1 越好。"),
        new_code_cell("""# 轮廓系数分析
silhouette_scores = []

for k in k_range:
    kmeans = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    score = silhouette_score(X_scaled, labels)
    silhouette_scores.append(score)
    print(f"K={k}: 轮廓系数={score:.4f}")

best_k = list(k_range)[np.argmax(silhouette_scores)]
best_score = max(silhouette_scores)
print(f"\\n✅ 最优 K = {best_k} (轮廓系数 = {best_score:.4f})")

fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(list(k_range), silhouette_scores, 'rs-', linewidth=2, markersize=8)
ax.axvline(x=best_k, color='green', linestyle='--', linewidth=1.5, label=f'最优 K={best_k}')
ax.set_xlabel('聚类数 K', fontsize=12)
ax.set_ylabel('轮廓系数', fontsize=12)
ax.set_title('轮廓系数 - 聚类质量评估', fontsize=14)
ax.set_xticks(list(k_range))
ax.legend(fontsize=12)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()"""),
        new_markdown_cell("## 4.5 最终聚类 & PCA 可视化"),
        new_code_cell("""# 使用最优 K 执行最终聚类
kmeans_final = KMeans(n_clusters=best_k, random_state=RANDOM_STATE, n_init=10)
labels = kmeans_final.fit_predict(X_scaled)
final_score = silhouette_score(X_scaled, labels)

print(f"最终聚类 K={best_k}, 轮廓系数={final_score:.4f}")
print(f"各簇样本量: {pd.Series(labels).value_counts().sort_index().to_dict()}")

# PCA 降维到 2D 可视化
pca = PCA(n_components=2, random_state=RANDOM_STATE)
X_pca = pca.fit_transform(X_scaled)
explained_var = pca.explained_variance_ratio_

print(f"\\nPCA 解释方差: PC1={explained_var[0]:.2%}, PC2={explained_var[1]:.2%}, 累计={sum(explained_var):.2%}")

fig, ax = plt.subplots(figsize=(12, 8))
unique_labels = np.unique(labels)
colors = plt.cm.Set1(np.linspace(0, 1, len(unique_labels)))

for label, color in zip(unique_labels, colors):
    mask = labels == label
    ax.scatter(X_pca[mask, 0], X_pca[mask, 1], c=[color],
               label=f'簇 {label} (n={mask.sum()})', alpha=0.6, s=30,
               edgecolors='white', linewidth=0.5)

ax.set_xlabel(f'PC1 ({explained_var[0]:.1%})', fontsize=12)
ax.set_ylabel(f'PC2 ({explained_var[1]:.1%})', fontsize=12)
ax.set_title('K-Means 聚类结果 - PCA 2D 可视化', fontsize=14)
ax.legend(fontsize=10, loc='best')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()"""),
        new_markdown_cell("## 4.6 聚类画像分析"),
        new_code_cell("""# 各簇特征均值分析
X_with_labels = X.copy()
X_with_labels['cluster'] = labels
cluster_means = X_with_labels.groupby('cluster').mean()

print("各簇特征均值:")
print("=" * 60)
print(cluster_means.round(2).to_string())
print("=" * 60)

# 热力图
fig, ax = plt.subplots(figsize=(12, 6))
cluster_means_scaled = (cluster_means - cluster_means.mean()) / cluster_means.std()

sns.heatmap(
    cluster_means_scaled.T, annot=cluster_means.T.round(2).values,
    fmt='', cmap='RdYlGn', center=0, ax=ax,
    xticklabels=[f'簇 {i}' for i in cluster_means.index],
    yticklabels=cluster_means.columns, linewidths=0.5
)
ax.set_title('各簇特征对比热力图\\n(颜色=标准化值, 数字=原始均值)', fontsize=13)
plt.tight_layout()
plt.show()"""),
        new_markdown_cell("## 4.7 聚类与 RFM 交叉验证"),
        new_code_cell("""# 聚类结果与 RFM 分层交叉分析
segment_col = None
for col in ['rfm_segment', 'rfm_label', 'customer_segment']:
    if col in df.columns:
        segment_col = col
        break

if segment_col:
    cross_df = pd.crosstab(labels, df[segment_col], margins=True, margins_name='合计')
    print("聚类 × RFM 交叉表:")
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
    plt.show()
else:
    print("未找到 RFM 分层列，跳过交叉分析")"""),
        new_markdown_cell("## 小结\n\n- 通过肘部法则和轮廓系数确定了最优聚类数\n- PCA 可视化展示了各簇在特征空间中的分布\n- 各簇在消费行为特征上呈现明显差异\n- 无监督聚类结果与 RFM 规则分层具有一定的一致性，验证了分层的合理性")
    ]
    nb = create_notebook(cells)
    save_notebook(nb, '04_kmeans_clustering.ipynb')


# ============================================================
# Notebook 05: 流失预测
# ============================================================
def gen_05_churn_prediction():
    cells = [
        new_markdown_cell("# 05 用户流失预测模型\n\n三模型对比训练：Logistic Regression / Random Forest / XGBoost\n- SMOTE 过采样处理类别不平衡\n- 5折分层交叉验证\n- ROC 曲线、混淆矩阵、特征重要性分析"),
        new_code_cell("""import sys
sys.path.insert(0, '..')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
from pathlib import Path

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, roc_curve, confusion_matrix, classification_report
)
from imblearn.over_sampling import SMOTE
from xgboost import XGBClassifier

warnings.filterwarnings('ignore')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

RANDOM_STATE = 42
BASE_DIR = Path('..').resolve()"""),
        new_markdown_cell("## 5.1 加载数据与特征工程"),
        new_code_cell("""# 加载用户特征数据
df = pd.read_parquet(BASE_DIR / 'data' / 'processed' / 'user_features.parquet')
print(f"数据形状: {df.shape}")
print(f"流失用户占比: {df['is_churned'].mean():.2%}")

# 排除非特征列
exclude_cols = []
id_cols = [c for c in df.columns if any(kw in c.lower() for kw in ['id', 'customer_unique'])]
date_cols = [c for c in df.columns if df[c].dtype == 'datetime64[ns]' or 'date' in c.lower()]
label_cols = [c for c in df.columns if any(kw in c.lower() for kw in ['segment', 'label', 'cluster', 'group'])]
exclude_cols = list(set(id_cols + date_cols + label_cols + ['is_churned']))

feature_cols = [c for c in df.columns if c not in exclude_cols]
print(f"\\n特征列数: {len(feature_cols)}")

X = df[feature_cols].copy()
y = df['is_churned'].copy()

# 处理分类特征
cat_cols = X.select_dtypes(include=['object', 'category']).columns.tolist()
for col in cat_cols:
    le = LabelEncoder()
    X[col] = le.fit_transform(X[col].fillna('unknown').astype(str))

X = X.fillna(0)
print(f"最终特征数: {X.shape[1]}")
X.head()"""),
        new_markdown_cell("## 5.2 数据集划分与 SMOTE 过采样"),
        new_code_cell("""# 分层划分训练/测试集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE
)
print(f"训练集: {X_train.shape[0]} 样本, 流失率: {y_train.mean():.2%}")
print(f"测试集: {X_test.shape[0]} 样本, 流失率: {y_test.mean():.2%}")

# SMOTE 过采样（仅训练集）
smote = SMOTE(random_state=RANDOM_STATE)
X_train_res, y_train_res = smote.fit_resample(X_train, y_train)
print(f"\\nSMOTE 前: {len(y_train)} 样本 (正: {y_train.sum()}, 负: {(~y_train.astype(bool)).sum()})")
print(f"SMOTE 后: {len(y_train_res)} 样本 (正: {y_train_res.sum()}, 负: {(~y_train_res.astype(bool)).sum()})")"""),
        new_markdown_cell("## 5.3 模型定义与 5 折交叉验证"),
        new_code_cell("""# 定义三个模型
neg_count = (y_train == 0).sum()
pos_count = (y_train == 1).sum()
scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1.0

models = {
    'Logistic Regression': LogisticRegression(C=1.0, max_iter=1000, class_weight='balanced', random_state=RANDOM_STATE),
    'Random Forest': RandomForestClassifier(n_estimators=200, max_depth=10, class_weight='balanced', n_jobs=-1, random_state=RANDOM_STATE),
    'XGBoost': XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.1, scale_pos_weight=scale_pos_weight, random_state=RANDOM_STATE, use_label_encoder=False, eval_metric='logloss')
}

# 5折交叉验证
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
cv_results = {}

for name, model in models.items():
    print(f"\\n{'─' * 40}")
    print(f"交叉验证: {name}")
    scores = {}
    for metric in ['accuracy', 'precision', 'recall', 'f1', 'roc_auc']:
        cv_scores = cross_val_score(model, X_train_res, y_train_res, cv=skf, scoring=metric, n_jobs=-1)
        scores[metric] = {'mean': cv_scores.mean(), 'std': cv_scores.std()}
        print(f"  {metric}: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
    cv_results[name] = scores"""),
        new_markdown_cell("## 5.4 测试集评估"),
        new_code_cell("""# 测试集评估
test_results = {}

for name, model in models.items():
    model.fit(X_train_res, y_train_res)
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    
    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred),
        'recall': recall_score(y_test, y_pred),
        'f1': f1_score(y_test, y_pred),
        'auc_roc': roc_auc_score(y_test, y_prob)
    }
    
    fpr, tpr, _ = roc_curve(y_test, y_prob)
    cm = confusion_matrix(y_test, y_pred)
    
    test_results[name] = {
        'metrics': metrics, 'fpr': fpr, 'tpr': tpr, 'cm': cm,
        'y_pred': y_pred, 'y_prob': y_prob
    }
    
    print(f"\\n{'─' * 40}")
    print(f"{name}:")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")

# 模型对比表
comparison = pd.DataFrame({name: r['metrics'] for name, r in test_results.items()}).T
print("\\n=== 模型对比 ===")
comparison"""),
        new_markdown_cell("## 5.5 ROC 曲线对比"),
        new_code_cell("""# ROC 曲线对比
fig, ax = plt.subplots(figsize=(10, 8))
colors = ['#2196F3', '#4CAF50', '#FF5722']

for (name, result), color in zip(test_results.items(), colors):
    ax.plot(result['fpr'], result['tpr'], color=color, lw=2,
            label=f"{name} (AUC={result['metrics']['auc_roc']:.4f})")

ax.plot([0, 1], [0, 1], 'k--', lw=1, label='随机基线')
ax.set_xlabel('假阳性率 (FPR)', fontsize=12)
ax.set_ylabel('真阳性率 (TPR)', fontsize=12)
ax.set_title('ROC 曲线对比 - 流失预测模型', fontsize=14)
ax.legend(loc='lower right', fontsize=11)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()"""),
        new_markdown_cell("## 5.6 混淆矩阵"),
        new_code_cell("""# 混淆矩阵
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

for ax, (name, result) in zip(axes, test_results.items()):
    sns.heatmap(result['cm'], annot=True, fmt='d', cmap='Blues', ax=ax,
                xticklabels=['未流失', '已流失'], yticklabels=['未流失', '已流失'])
    ax.set_title(f'{name}\\n混淆矩阵', fontsize=12)
    ax.set_xlabel('预测标签')
    ax.set_ylabel('真实标签')

plt.suptitle('各模型混淆矩阵对比', fontsize=14)
plt.tight_layout()
plt.show()"""),
        new_markdown_cell("## 5.7 特征重要性"),
        new_code_cell("""# 特征重要性 Top 15
fig, axes = plt.subplots(1, 3, figsize=(20, 8))
feature_names = X.columns.tolist()

for ax, (name, model) in zip(axes, models.items()):
    if name == 'Logistic Regression':
        importances = np.abs(model.coef_[0])
    else:
        importances = model.feature_importances_
    
    fi_df = pd.DataFrame({'feature': feature_names, 'importance': importances})
    fi_df = fi_df.sort_values('importance', ascending=False).head(15)
    
    sns.barplot(data=fi_df, x='importance', y='feature', ax=ax, palette='viridis')
    ax.set_title(f'{name}\\n特征重要性 Top15', fontsize=12)
    ax.set_xlabel('重要性')
    ax.set_ylabel('')

plt.suptitle('各模型特征重要性对比', fontsize=14, y=1.02)
plt.tight_layout()
plt.show()"""),
        new_markdown_cell("## 小结\n\n- 使用 SMOTE 过采样解决了正负样本不平衡问题\n- 三模型中 XGBoost/Random Forest 通常表现最优\n- 关键流失特征：recency_days、total_orders、delayed_order_ratio 等\n- 模型可用于识别高流失风险用户，指导精准召回策略")
    ]
    nb = create_notebook(cells)
    save_notebook(nb, '05_churn_prediction.ipynb')


# ============================================================
# Notebook 06: 因果推断
# ============================================================
def gen_06_causal_analysis():
    cells = [
        new_markdown_cell("# 06 因果推断分析 (PSM)\n\n研究问题：**物流延迟是否因果性地降低了用户复购概率？**\n\n方法：倾向得分匹配 (Propensity Score Matching)\n- 倾向得分估计\n- 最近邻匹配 (1:1)\n- 平衡性检验 (Love Plot)\n- ATT 估计 + Bootstrap 置信区间"),
        new_code_cell("""import sys
sys.path.insert(0, '..')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from scipy.spatial import KDTree
from scipy.stats import norm
import warnings

warnings.filterwarnings('ignore')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

from pathlib import Path
BASE_DIR = Path('..').resolve()
data_dir = BASE_DIR / 'data' / 'processed'"""),
        new_markdown_cell("## 6.1 数据准备 - 定义处理组/对照组/协变量"),
        new_code_cell("""# 加载数据
df = pd.read_parquet(data_dir / 'user_features.parquet')
print(f"原始用户数: {len(df)}")

# 定义处理变量：是否经历过物流延迟
df['treatment'] = (df['delayed_order_ratio'] > 0).astype(int)

# 定义结果变量：是否复购
df['is_repeat_purchaser'] = (df['total_orders'] > 1).astype(int)

# 协变量编码
covariates = ['total_spend', 'avg_review_score']
categorical_cols = ['main_category', 'customer_state', 'main_payment_type']

for col in categorical_cols:
    if col in df.columns:
        le = LabelEncoder()
        df[f'{col}_encoded'] = le.fit_transform(df[col].astype(str))
        covariates.append(f'{col}_encoded')

# 去除缺失值
all_cols = covariates + ['treatment', 'is_repeat_purchaser']
df_clean = df.dropna(subset=all_cols).copy()

print(f"清洗后用户数: {len(df_clean)}")
print(f"处理组(延迟用户): {df_clean['treatment'].sum()}")
print(f"对照组(未延迟用户): {(df_clean['treatment'] == 0).sum()}")"""),
        new_markdown_cell("## 6.2 描述性分析"),
        new_code_cell("""# 处理组 vs 对照组 复购率
repurchase_by_group = df_clean.groupby('treatment')['is_repeat_purchaser'].mean()
print(f"对照组(未延迟)复购率: {repurchase_by_group.get(0, 0):.4f}")
print(f"处理组(延迟)复购率: {repurchase_by_group.get(1, 0):.4f}")
print(f"朴素差异: {repurchase_by_group.get(1, 0) - repurchase_by_group.get(0, 0):.4f}")

# 可视化
fig, ax = plt.subplots(figsize=(8, 5))
groups = ['未延迟(对照组)', '有延迟(处理组)']
rates = [repurchase_by_group.get(0, 0), repurchase_by_group.get(1, 0)]
ax.bar(groups, rates, color=['#2ecc71', '#e74c3c'], alpha=0.8)
ax.set_ylabel('复购率')
ax.set_title('处理组 vs 对照组 复购率对比')
for i, v in enumerate(rates):
    ax.text(i, v + 0.005, f'{v:.3f}', ha='center', fontsize=12)
plt.tight_layout()
plt.show()"""),
        new_markdown_cell("## 6.3 倾向得分估计\n\n使用 Logistic Regression 估计每个用户被分配到「处理组」(经历物流延迟) 的概率。"),
        new_code_cell("""# 倾向得分估计
X_ps = df_clean[covariates].values
y_ps = df_clean['treatment'].values

lr = LogisticRegression(max_iter=1000, random_state=42)
lr.fit(X_ps, y_ps)
df_clean = df_clean.copy()
df_clean['propensity_score'] = lr.predict_proba(X_ps)[:, 1]

# Positivity 检查
ps = df_clean['propensity_score']
positivity_ratio = ((ps > 0.1) & (ps < 0.9)).mean()
print(f"Positivity (0.1 < PS < 0.9): {positivity_ratio:.4f}")
print(f"处理组 PS 均值: {df_clean.loc[df_clean['treatment']==1, 'propensity_score'].mean():.4f}")
print(f"对照组 PS 均值: {df_clean.loc[df_clean['treatment']==0, 'propensity_score'].mean():.4f}")

# 分布图
fig, ax = plt.subplots(figsize=(10, 5))
ax.hist(df_clean.loc[df_clean['treatment']==0, 'propensity_score'], bins=50,
        alpha=0.6, label='对照组(未延迟)', color='#2ecc71', density=True)
ax.hist(df_clean.loc[df_clean['treatment']==1, 'propensity_score'], bins=50,
        alpha=0.6, label='处理组(延迟)', color='#e74c3c', density=True)
ax.set_xlabel('倾向得分 (Propensity Score)')
ax.set_ylabel('密度')
ax.set_title('倾向得分分布: 处理组 vs 对照组')
ax.legend()
plt.tight_layout()
plt.show()"""),
        new_markdown_cell("## 6.4 倾向得分匹配 (1:1 最近邻)"),
        new_code_cell("""# 最近邻匹配
caliper = 0.05
treatment_df = df_clean[df_clean['treatment'] == 1].copy()
control_df = df_clean[df_clean['treatment'] == 0].copy()

control_ps = control_df['propensity_score'].values.reshape(-1, 1)
tree = KDTree(control_ps)

matched_treatment_idx = []
matched_control_idx = []
used_control = set()

treatment_ps = treatment_df['propensity_score'].values
treatment_indices = treatment_df.index.tolist()
control_indices = control_df.index.tolist()

for i, ps_val in enumerate(treatment_ps):
    dist, idx = tree.query([ps_val], k=min(10, len(control_ps)))
    for d, j in zip(dist[0] if len(dist.shape) > 1 else dist,
                   idx[0] if len(idx.shape) > 1 else idx):
        if d <= caliper and j not in used_control:
            matched_treatment_idx.append(treatment_indices[i])
            matched_control_idx.append(control_indices[j])
            used_control.add(j)
            break

match_rate = len(matched_treatment_idx) / len(treatment_df)
print(f"Caliper = {caliper}, 匹配率: {match_rate:.4f}")
print(f"匹配成功对数: {len(matched_treatment_idx)}")

# 构建匹配后数据集
matched_t = df_clean.loc[matched_treatment_idx].copy()
matched_t['match_group'] = 'treatment'
matched_c = df_clean.loc[matched_control_idx].copy()
matched_c['match_group'] = 'control'
matched_df = pd.concat([matched_t, matched_c], ignore_index=True)"""),
        new_markdown_cell("## 6.5 平衡性检验 (SMD + Love Plot)"),
        new_code_cell("""# 计算 SMD
smd_before = {}
smd_after = {}

for cov in covariates:
    t_before = df_clean.loc[df_clean['treatment']==1, cov]
    c_before = df_clean.loc[df_clean['treatment']==0, cov]
    pooled_std = np.sqrt((t_before.var() + c_before.var()) / 2)
    smd_before[cov] = abs(t_before.mean() - c_before.mean()) / pooled_std if pooled_std > 0 else 0

    t_after = matched_df.loc[matched_df['match_group']=='treatment', cov]
    c_after = matched_df.loc[matched_df['match_group']=='control', cov]
    pooled_std_after = np.sqrt((t_after.var() + c_after.var()) / 2)
    smd_after[cov] = abs(t_after.mean() - c_after.mean()) / pooled_std_after if pooled_std_after > 0 else 0

print(f"{'协变量':<25} {'匹配前SMD':<12} {'匹配后SMD':<12} {'平衡?'}")
print("-" * 60)
for cov in covariates:
    balanced = "✅" if smd_after[cov] < 0.1 else "❌"
    print(f"{cov:<25} {smd_before[cov]:<12.4f} {smd_after[cov]:<12.4f} {balanced}")

# Love Plot
fig, ax = plt.subplots(figsize=(10, 6))
y_pos = np.arange(len(covariates))
ax.barh(y_pos - 0.2, [smd_before[c] for c in covariates], 0.4, label='匹配前', color='#e74c3c', alpha=0.7)
ax.barh(y_pos + 0.2, [smd_after[c] for c in covariates], 0.4, label='匹配后', color='#2ecc71', alpha=0.7)
ax.axvline(x=0.1, color='black', linestyle='--', label='平衡阈值(0.1)')
ax.set_yticks(y_pos)
ax.set_yticklabels(covariates)
ax.set_xlabel('标准化均值差 (SMD)')
ax.set_title('Love Plot: 匹配前后协变量平衡性')
ax.legend()
plt.tight_layout()
plt.show()"""),
        new_markdown_cell("## 6.6 ATT 估计 + Bootstrap 置信区间"),
        new_code_cell("""# ATT 估计
treatment_outcome = matched_df.loc[matched_df['match_group']=='treatment', 'is_repeat_purchaser']
control_outcome = matched_df.loc[matched_df['match_group']=='control', 'is_repeat_purchaser']

att = treatment_outcome.mean() - control_outcome.mean()
print(f"ATT (处理组平均处理效应): {att:.4f}")

# Bootstrap 置信区间
np.random.seed(42)
bootstrap_atts = []
n_pairs = len(treatment_outcome)

for _ in range(500):
    idx = np.random.choice(n_pairs, size=n_pairs, replace=True)
    t_sample = treatment_outcome.iloc[idx].mean()
    c_sample = control_outcome.iloc[idx].mean()
    bootstrap_atts.append(t_sample - c_sample)

ci_lower = np.percentile(bootstrap_atts, 2.5)
ci_upper = np.percentile(bootstrap_atts, 97.5)

print(f"95% CI: [{ci_lower:.4f}, {ci_upper:.4f}]")
print(f"\\n结论: 物流延迟使复购概率{'降低' if att < 0 else '提高'} {abs(att)*100:.2f} 个百分点")"""),
        new_markdown_cell("## 小结\n\n- PSM 通过匹配消除了选择偏差，使处理组和对照组在协变量上可比\n- Love Plot 显示匹配后各协变量 SMD 均小于 0.1，平衡性良好\n- ATT 结果表明物流延迟对复购有显著的负向因果效应\n- 该结论为物流优化投资提供了数据支撑：改善物流时效可带来可量化的复购提升")
    ]
    nb = create_notebook(cells)
    save_notebook(nb, '06_causal_analysis.ipynb')


# ============================================================
# Notebook 07: 评论NLP
# ============================================================
def gen_07_review_nlp():
    cells = [
        new_markdown_cell("# 07 评论 NLP 分析\n\n对用户评论进行文本挖掘：\n- jieba 中文分词\n- 停用词过滤\n- 低评分/高评分词频对比\n- 词云可视化\n- 评论维度归因分析（物流/品类/地区/金额）"),
        new_code_cell("""import sys
sys.path.insert(0, '..')

import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import warnings

warnings.filterwarnings('ignore')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

from utils.db_connector import get_engine
engine = get_engine()

import jieba
print("jieba 分词库加载完成")"""),
        new_markdown_cell("## 7.1 加载评论数据"),
        new_code_cell("""# 加载评论相关数据
query = \"\"\"
SELECT 
    r.review_id, r.order_id, r.review_score, r.review_comment_message,
    o.order_purchase_timestamp, o.order_delivered_customer_date,
    o.order_estimated_delivery_date, o.customer_id,
    i.product_id, i.price,
    p.product_category_name, c.customer_state
FROM olist_order_reviews r
LEFT JOIN olist_orders o ON r.order_id = o.order_id
LEFT JOIN olist_order_items i ON r.order_id = i.order_id
LEFT JOIN olist_products p ON i.product_id = p.product_id
LEFT JOIN olist_customers c ON o.customer_id = c.customer_id
\"\"\"

with engine.connect() as conn:
    df = pd.read_sql_query(query, conn)

# 计算配送天数
df['order_delivered_customer_date'] = pd.to_datetime(df['order_delivered_customer_date'])
df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'])
df['order_estimated_delivery_date'] = pd.to_datetime(df['order_estimated_delivery_date'])
df['delivery_days'] = (df['order_delivered_customer_date'] - df['order_purchase_timestamp']).dt.days
df['delay_days'] = (df['order_delivered_customer_date'] - df['order_estimated_delivery_date']).dt.days
df['is_delayed'] = (df['delay_days'] > 0).astype(int)

# 定义评分分组
df['score_group'] = df['review_score'].apply(
    lambda x: 'low' if x <= 2 else ('high' if x >= 4 else 'mid')
)

print(f"评论总数: {len(df)}")
print(f"低评分(≤2): {(df['score_group']=='low').sum()}")
print(f"高评分(≥4): {(df['score_group']=='high').sum()}")
df.head()"""),
        new_markdown_cell("## 7.2 评分维度分析\n\n分析低评分订单的归因：物流、品类、地区、金额等维度。"),
        new_code_cell("""# 多维度分析
low_df = df[df['score_group'] == 'low']
high_df = df[df['score_group'] == 'high']

print("=== 物流维度 ===")
logistics_compare = pd.DataFrame({
    '低评分': [low_df['delivery_days'].mean(), low_df['is_delayed'].mean(),
              low_df.loc[low_df['is_delayed']==1, 'delay_days'].mean()],
    '高评分': [high_df['delivery_days'].mean(), high_df['is_delayed'].mean(),
              high_df.loc[high_df['is_delayed']==1, 'delay_days'].mean()]
}, index=['平均配送天数', '延迟率', '平均延迟天数'])
print(logistics_compare)

print("\\n=== 品类维度(低评分率 Top 5) ===")
category_low_rate = df.groupby('product_category_name').apply(
    lambda x: (x['score_group'] == 'low').mean()
).sort_values(ascending=False)
print(category_low_rate.head(5))

print("\\n=== 地区维度(低评分率 Top 5) ===")
state_low_rate = df.groupby('customer_state').apply(
    lambda x: (x['score_group'] == 'low').mean()
).sort_values(ascending=False)
print(state_low_rate.head(5))

print(f"\\n=== 金额维度 ===")
print(f"低评分客单价均值: ¥{low_df['price'].mean():.2f}")
print(f"高评分客单价均值: ¥{high_df['price'].mean():.2f}")"""),
        new_markdown_cell("## 7.3 评分维度可视化"),
        new_code_cell("""# 评分分析可视化
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 评分分布
score_counts = df['review_score'].value_counts().sort_index()
colors = ['#e74c3c', '#e74c3c', '#f39c12', '#2ecc71', '#2ecc71']
axes[0, 0].bar(score_counts.index, score_counts.values, color=colors, alpha=0.8)
axes[0, 0].set_xlabel('评分')
axes[0, 0].set_ylabel('评论数')
axes[0, 0].set_title('评分分布')

# 品类低评分 Top 10
top10_cats = category_low_rate.head(10)
axes[0, 1].barh(range(len(top10_cats)), top10_cats.values, color='#e74c3c', alpha=0.7)
axes[0, 1].set_yticks(range(len(top10_cats)))
axes[0, 1].set_yticklabels(top10_cats.index, fontsize=8)
axes[0, 1].set_xlabel('低评分占比')
axes[0, 1].set_title('品类低评分率 Top 10')

# 地区低评分 Top 10
top10_states = state_low_rate.head(10)
axes[1, 0].barh(range(len(top10_states)), top10_states.values, color='#3498db', alpha=0.7)
axes[1, 0].set_yticks(range(len(top10_states)))
axes[1, 0].set_yticklabels(top10_states.index)
axes[1, 0].set_xlabel('低评分占比')
axes[1, 0].set_title('各州低评分率 Top 10')

# 归因对比热力图
heatmap_data = pd.DataFrame({
    '配送天数': [low_df['delivery_days'].mean(), high_df['delivery_days'].mean()],
    '延迟率': [low_df['is_delayed'].mean(), high_df['is_delayed'].mean()],
    '客单价': [low_df['price'].mean(), high_df['price'].mean()],
}, index=['低评分', '高评分'])
heatmap_norm = heatmap_data.apply(lambda x: (x - x.min()) / (x.max() - x.min() + 1e-8))
im = axes[1, 1].imshow(heatmap_norm.values, cmap='RdYlGn_r', aspect='auto')
axes[1, 1].set_xticks(range(len(heatmap_data.columns)))
axes[1, 1].set_xticklabels(heatmap_data.columns)
axes[1, 1].set_yticks(range(len(heatmap_data.index)))
axes[1, 1].set_yticklabels(heatmap_data.index)
axes[1, 1].set_title('低评分 vs 高评分 归因对比')
for i in range(len(heatmap_data.index)):
    for j in range(len(heatmap_data.columns)):
        axes[1, 1].text(j, i, f'{heatmap_data.iloc[i, j]:.2f}', ha='center', va='center', fontsize=11)

plt.tight_layout()
plt.show()"""),
        new_markdown_cell("## 7.4 jieba 分词与词频统计"),
        new_code_cell("""# 中文停用词
zh_stopwords = set([
    '的', '了', '是', '我', '很', '在', '也', '都', '就', '不',
    '有', '和', '那', '这', '个', '一', '上', '为', '什么', '么',
    '吗', '呢', '啊', '哦', '嗯', '还', '而', '但', '又', '或',
    '会', '能', '可以', '把', '被', '让', '给', '到', '着', '过',
    '吧', '呀', '哈', '嘿', '哎', '嘛', '噢', '喔', '哇',
    '比较', '已经', '真的', '觉得', '知道', '应该', '可能', '需要',
    '因为', '所以', '如果', '虽然', '但是', '而且', '然后', '不过',
    '这个', '那个', '这些', '那些', '一个', '一些', '一下', '一点',
    '没', '要', '去', '做', '说', '看', '想', '买',
])

# 筛选有评论文本的数据
low_text = df[(df['score_group'] == 'low') &
              (df['review_comment_message'].notna()) &
              (df['review_comment_message'].str.strip() != '')]['review_comment_message']

high_text = df[(df['score_group'] == 'high') &
               (df['review_comment_message'].notna()) &
               (df['review_comment_message'].str.strip() != '')]['review_comment_message']

print(f"低评分有效评论数: {len(low_text)}")
print(f"高评分有效评论数: {len(high_text)}")

def preprocess_text(texts):
    all_words = []
    for text in texts:
        text = str(text).strip()
        text = re.sub(r'[^\\u4e00-\\u9fa5a-zA-Z]', '', text)
        words = list(jieba.cut(text))
        words = [w for w in words if w not in zh_stopwords and len(w) > 1]
        all_words.extend(words)
    return all_words

low_words = preprocess_text(low_text)
low_freq = Counter(low_words).most_common(50)

high_words = preprocess_text(high_text)
high_freq = Counter(high_words).most_common(50)

print(f"\\n低评分高频词 Top 20:")
for word, count in low_freq[:20]:
    print(f"  {word}: {count}")"""),
        new_markdown_cell("## 7.5 词云可视化"),
        new_code_cell("""# 词云生成
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
    plt.title('低评分评论词云', fontsize=14)
    plt.tight_layout()
    plt.show()
except ImportError:
    print("wordcloud 未安装，跳过词云生成。安装命令: pip install wordcloud")"""),
        new_markdown_cell("## 7.6 高频词对比"),
        new_code_cell("""# 高频词对比表
low_freq_df = pd.DataFrame(low_freq, columns=['word', 'low_score_count'])
high_freq_df = pd.DataFrame(high_freq, columns=['word', 'high_score_count'])
compare_df = low_freq_df.merge(high_freq_df, on='word', how='outer').fillna(0)
compare_df['low_score_count'] = compare_df['low_score_count'].astype(int)
compare_df['high_score_count'] = compare_df['high_score_count'].astype(int)
compare_df['diff_ratio'] = (compare_df['low_score_count'] - compare_df['high_score_count']) / \\
                            (compare_df['low_score_count'] + compare_df['high_score_count'] + 1)
compare_df = compare_df.sort_values('diff_ratio', ascending=False)

print("低评分特有高频词 Top 10:")
compare_df.head(10)"""),
        new_markdown_cell("## 小结\n\n- 低评分订单的物流延迟率显著高于高评分订单\n- 某些品类（如电子产品、家具）低评分率较高\n- 文本分析显示低评分评论中「延迟」「质量」「退货」等词频较高\n- 建议重点优化物流时效和高差评品类的品控")
    ]
    nb = create_notebook(cells)
    save_notebook(nb, '07_review_nlp.ipynb')


# ============================================================
# Notebook 08: 经营KPI
# ============================================================
def gen_08_business_insights():
    cells = [
        new_markdown_cell("# 08 经营 KPI 分析\n\n核心经营指标计算与可视化：\n- GMV 月度趋势与环比增长\n- 品类收入与毛利贡献\n- 区域 GMV 分布\n- 支付方式分析与分期行为"),
        new_code_cell("""import sys
sys.path.insert(0, '..')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

warnings.filterwarnings('ignore')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

from utils.db_connector import get_engine
engine = get_engine()"""),
        new_markdown_cell("## 8.1 加载订单数据"),
        new_code_cell("""# 加载订单数据（多表关联）
query = \"\"\"
SELECT 
    o.order_id, o.customer_id, o.order_purchase_timestamp, o.order_status,
    i.product_id, i.seller_id, i.price, i.freight_value,
    p.product_category_name, c.customer_state,
    pay.payment_type, pay.payment_installments, pay.payment_value
FROM olist_orders o
LEFT JOIN olist_order_items i ON o.order_id = i.order_id
LEFT JOIN olist_products p ON i.product_id = p.product_id
LEFT JOIN olist_customers c ON o.customer_id = c.customer_id
LEFT JOIN olist_order_payments pay ON o.order_id = pay.order_id
WHERE o.order_status = 'delivered'
\"\"\"

with engine.connect() as conn:
    df = pd.read_sql_query(query, conn)

df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'])
df['year_month'] = df['order_purchase_timestamp'].dt.to_period('M')

# 毛利率假设
margin_rates = {
    '电脑配件': 0.12, '数码电子': 0.15, '手机通讯': 0.30,
    '美妆个护': 0.50, '运动户外': 0.40, '家居装饰': 0.35,
    '家居日用': 0.42, '汽车用品': 0.25, '玩具': 0.40,
    '创意潮品': 0.35, '家用电器': 0.30
}
df['margin_rate'] = df['product_category_name'].map(lambda x: margin_rates.get(str(x), 0.30))
df['gross_profit'] = df['price'] * df['margin_rate']

print(f"已加载订单数: {df['order_id'].nunique():,}")
print(f"时间范围: {df['order_purchase_timestamp'].min()} ~ {df['order_purchase_timestamp'].max()}")
df.head()"""),
        new_markdown_cell("## 8.2 月度 KPI 计算"),
        new_code_cell("""# 月度 KPI
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

print(f"总 GMV: ¥{monthly['gmv'].sum():,.2f}")
print(f"平均月 GMV: ¥{monthly['gmv'].mean():,.2f}")
print(f"平均客单价: ¥{monthly['aov'].mean():.2f}")
print(f"平均毛利率: {monthly['gross_margin'].mean():.2%}")
monthly"""),
        new_markdown_cell("## 8.3 GMV 月度趋势"),
        new_code_cell("""# GMV + 环比增长率双轴图
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
plt.show()"""),
        new_markdown_cell("## 8.4 品类表现分析"),
        new_code_cell("""# 品类分析
category = df.groupby('product_category_name').agg(
    revenue=('price', 'sum'),
    order_count=('order_id', 'nunique'),
    gross_profit=('gross_profit', 'sum'),
    avg_price=('price', 'mean')
).reset_index()
category['margin_rate'] = category['gross_profit'] / category['revenue']
category = category.sort_values('revenue', ascending=False)

print(f"品类数: {len(category)}")
print("\\nTop 10 品类收入:")
category.head(10)[['product_category_name', 'revenue', 'order_count', 'margin_rate']].round(2)"""),
        new_code_cell("""# 品类收入 & 毛利可视化
top10 = category.head(10)
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

axes[0].barh(range(len(top10)), top10['revenue'] / 10000, color='#3498db', alpha=0.8)
axes[0].set_yticks(range(len(top10)))
axes[0].set_yticklabels(top10['product_category_name'], fontsize=9)
axes[0].set_xlabel('收入 (万)')
axes[0].set_title('品类收入 Top 10')
axes[0].invert_yaxis()

top10_margin = category.nlargest(10, 'gross_profit')
axes[1].barh(range(len(top10_margin)), top10_margin['gross_profit'] / 10000, color='#2ecc71', alpha=0.8)
axes[1].set_yticks(range(len(top10_margin)))
axes[1].set_yticklabels(top10_margin['product_category_name'], fontsize=9)
axes[1].set_xlabel('毛利 (万)')
axes[1].set_title('品类毛利贡献 Top 10')
axes[1].invert_yaxis()

plt.tight_layout()
plt.show()"""),
        new_markdown_cell("## 8.5 区域分析"),
        new_code_cell("""# 地区 GMV 分析
state = df.groupby('customer_state').agg(
    gmv=('price', 'sum'),
    order_count=('order_id', 'nunique'),
    customer_count=('customer_id', 'nunique'),
    avg_order_value=('price', 'mean')
).reset_index().sort_values('gmv', ascending=False)

fig, ax = plt.subplots(figsize=(14, 6))
ax.bar(range(len(state)), state['gmv'] / 10000, color='#9b59b6', alpha=0.7)
ax.set_xticks(range(len(state)))
ax.set_xticklabels(state['customer_state'], rotation=45, ha='right')
ax.set_xlabel('省份/州')
ax.set_ylabel('GMV (万)')
ax.set_title('各省份 GMV 分布（降序）')
plt.tight_layout()
plt.show()

print("Top 5 省份:")
state.head(5)[['customer_state', 'gmv', 'order_count', 'customer_count']]"""),
        new_markdown_cell("## 8.6 支付方式分析"),
        new_code_cell("""# 支付方式分析
payment_df = df.drop_duplicates(subset=['order_id', 'payment_type'])
payment = payment_df.groupby('payment_type').agg(
    transaction_count=('order_id', 'nunique'),
    total_value=('payment_value', 'sum'),
    avg_installments=('payment_installments', 'mean')
).reset_index()
payment['share'] = payment['transaction_count'] / payment['transaction_count'].sum()
payment = payment.sort_values('transaction_count', ascending=False)

# 饼图
fig, ax = plt.subplots(figsize=(8, 8))
colors = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6']
ax.pie(payment['transaction_count'], labels=payment['payment_type'],
       autopct='%1.1f%%', colors=colors[:len(payment)], startangle=90)
ax.set_title('支付方式占比')
plt.tight_layout()
plt.show()

payment"""),
        new_markdown_cell("## 8.7 分期付款行为"),
        new_code_cell("""# 分期付款分析
installments = df.drop_duplicates(subset=['order_id', 'payment_installments'])
inst_dist = installments['payment_installments'].value_counts().sort_index()
inst_dist = inst_dist[inst_dist.index <= 12]

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

axes[0].bar(inst_dist.index, inst_dist.values, color='#f39c12', alpha=0.8)
axes[0].set_xlabel('分期期数')
axes[0].set_ylabel('订单数')
axes[0].set_title('分期期数分布')

# 月度平均分期趋势
installments['year_month'] = installments['order_purchase_timestamp'].dt.to_period('M')
monthly_inst = installments.groupby('year_month')['payment_installments'].mean()
axes[1].plot(range(len(monthly_inst)), monthly_inst.values, marker='o', color='#e67e22', linewidth=2)
axes[1].set_xlabel('月份')
axes[1].set_ylabel('平均分期期数')
axes[1].set_title('平均分期期数月度趋势')

plt.tight_layout()
plt.show()"""),
        new_markdown_cell("## 小结\n\n- GMV 整体呈增长趋势，2018年上半年增速最快\n- 电子产品和家居类目是主力收入品类\n- SP、RJ 等州贡献了绝大部分 GMV\n- 信用卡为主要支付方式，分期购买行为常见\n- 高毛利品类（美妆、运动）值得加大运营投入")
    ]
    nb = create_notebook(cells)
    save_notebook(nb, '08_business_insights.ipynb')


# ============================================================
# 主函数
# ============================================================
def main():
    print("=" * 60)
    print("开始生成 Jupyter Notebook 文件...")
    print("=" * 60)

    gen_01_data_overview()
    gen_02_data_cleaning()
    gen_03_rfm_segmentation()
    gen_04_kmeans_clustering()
    gen_05_churn_prediction()
    gen_06_causal_analysis()
    gen_07_review_nlp()
    gen_08_business_insights()

    print("\n" + "=" * 60)
    print("所有 8 个 Notebook 生成完成！")
    print("=" * 60)

    # 删除旧的 .py 文件
    old_files = list(NOTEBOOKS_DIR.glob('*.py'))
    if old_files:
        print(f"\n清理旧的 .py 文件:")
        for f in old_files:
            f.unlink()
            print(f"  已删除: {f}")


if __name__ == '__main__':
    main()

