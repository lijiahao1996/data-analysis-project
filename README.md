# 优品汇电商经营分析

> 基于国内综合电商平台真实交易数据的全链路经营分析项目，涵盖用户流失预测、因果推断、RFM分层与经营健康度评估。

## 项目背景

### 企业简介

优品汇（YouPinHui）是一家成立于 2015 年的综合电商平台，总部位于杭州，主营美妆个护、家居装饰、3C 数码、服饰箱包等核心品类。平台以"品质生活，优选消费"为品牌理念，聚焦 25-40 岁城市中产消费群体。

经过三年快速发展，优品汇已累计覆盖全国 27 个省市，注册用户突破 10 万，合作卖家超过 3,000 家，SKU 总量达 32,000+。平台采用自营与第三方卖家混合经营模式，通过自建仓储物流与第三方配送结合完成订单履约。

### 业务痛点

1. **用户流失率持续攀升** — 近 6 个月仅约 35% 用户产生二次购买，大量早期用户进入沉默状态
2. **物流体验影响留存** — 东北、西北等区域平均配送超 7 天，差评率高出全国均值 40%
3. **品类经营效率不均衡** — 部分高 GMV 品类毛利率偏低且退货率高，高毛利品类流量渗透不足
4. **差评原因缺乏结构化归因** — 无法区分物流、质量、价格等因素对差评的贡献
5. **客户分层运营能力不足** — 高价值客户与普通客户采用相同营销策略，ROI 持续走低

### 分析目标

1. 构建用户流失预测模型，识别高流失风险用户
2. 量化物流延迟对用户复购的因果效应（PSM）
3. 建立 RFM 客户价值分层体系（K-Means 聚类）
4. 评论评分维度归因分析（NLP 文本挖掘）
5. 输出经营健康度 KPI 仪表盘

### 数据集说明

本项目使用优品汇平台**内部脱敏数据**，涵盖 2016 年 9 月至 2018 年 8 月：

| 数据表 | 记录数 | 说明 |
|--------|--------|------|
| 订单表 | 99,441 | 全量订单，含订单状态、时间戳 |
| 订单明细表 | 112,650 | 订单-商品关联，含价格和运费 |
| 客户表 | 99,441 | 客户地理位置信息（已脱敏） |
| 支付表 | 103,886 | 支付方式和分期信息 |
| 评论表 | 99,224 | 用户评分和评论文本 |
| 商品表 | 32,951 | 商品属性和品类 |
| 卖家表 | 3,095 | 卖家基本信息 |
| 地理位置表 | 1,000,163 | 全国邮编-城市-省份映射 |

## 快速开始

### 方式一：Docker 一键运行（推荐）

```bash
# Windows
双击 start.bat

# Linux/Mac
chmod +x start.sh && ./start.sh
```

Docker 会自动完成：MySQL 初始化 → 数据导入 → 全流程分析 → 结果输出。
结果位于 `data/processed/` 目录。

### 方式二：本地运行

#### 1. 环境要求
- Python 3.11+
- MySQL 8.0
- 8GB+ 内存

#### 2. 安装依赖
```bash
cd olist-ecommerce-analytics
python -m venv venv
# Windows
.\venv\Scripts\Activate.ps1
# Linux/Mac
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. 配置数据库
编辑 `config.yaml` 中的数据库连接信息：
```yaml
database:
  type: mysql
  host: localhost
  port: 3306
  user: root
  password: ""
  database: olist_ecommerce
```

确保 MySQL 中已创建数据库：
```sql
CREATE DATABASE olist_ecommerce CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

#### 4. 数据本地化转换
```bash
python scripts/rebrand_data.py
```

#### 5. 初始化数据库
```bash
python scripts/init_mysql_db.py
```

#### 6. 运行分析 Pipeline
```bash
# 全流程
python main.py --step all

# 或单步执行
python main.py --step clean      # 数据清洗
python main.py --step feature    # 特征工程
python main.py --step churn      # 流失标签
python main.py --step model      # 模型训练
python main.py --step causal     # 因果分析（PSM）
python main.py --step review     # 评论分析
python main.py --step business   # 经营KPI
```

## 项目结构

```
olist-ecommerce-analytics/
├── main.py                  # Pipeline 主入口
├── config.yaml              # 全局配置
├── requirements.txt         # Python 依赖
├── Dockerfile               # Docker 镜像构建
├── docker-compose.yml       # Docker Compose 编排
├── start.bat                # Windows 一键启动脚本
├── start.sh                 # Linux/Mac 一键启动脚本
├── BACKGROUND.md            # 项目背景详述
├── data/
│   ├── raw/                 # 原始 CSV 数据
│   ├── rebranded/           # 本地化转换后的 CSV
│   └── processed/           # 清洗/特征工程产出
│       └── plots/           # 可视化图表
├── sql/                     # SQL 脚本
├── notebooks/               # 探索性分析脚本
├── scripts/                 # 独立执行脚本
│   ├── rebrand_data.py      # 数据本地化转换
│   ├── init_mysql_db.py     # MySQL 数据库初始化
│   ├── business_analysis.py # 经营KPI分析
│   ├── causal_analysis.py   # PSM 因果分析
│   ├── churn_label_builder.py # 流失标签构建
│   └── review_analysis.py   # 评论NLP分析
├── utils/                   # 核心工具模块
│   ├── data_loader.py       # 数据加载器
│   ├── data_cleaner.py      # 数据清洗
│   ├── db_connector.py      # 数据库连接
│   ├── feature_builder.py   # 特征工程
│   └── model_trainer.py     # 模型训练
├── models/                  # 训练模型产出
├── logs/                    # 运行日志
├── report/                  # 分析报告
└── powerbi/                 # Power BI 看板文件
```

## 核心分析方法

### 流失定义：P75×2 规则

采用数据驱动的动态阈值方案定义客户流失：

1. 计算每位复购客户的平均购买间隔天数
2. 取所有客户购买间隔的 **P75 分位数**
3. 阈值 = P75 × 2
4. 若客户最后一次购买距数据截止日超过该阈值，则标记为流失

**优势**：避免人为设定固定天数，适应不同品类的购买频率差异。

### PSM 因果推断

使用**倾向得分匹配（Propensity Score Matching）**评估物流延迟对客户流失的因果效应：

- **处理组**：经历过严重物流延迟（>7天）的客户
- **对照组**：未经历延迟的匹配客户
- **匹配策略**：1:1 最近邻匹配，caliper = 0.05
- **平衡检验**：SMD < 0.1 视为协变量平衡

### RFM 分层 + K-Means 聚类

基于 Recency / Frequency / Monetary 三维度构建客户价值分层，结合 K-Means 无监督聚类确定最优客群数量（Silhouette Score 选 K）。

### 多模型流失预测

- Logistic Regression（基线）
- Random Forest
- XGBoost
- SMOTE 过采样处理类别不平衡
- 5折交叉验证 + AUC/F1/Recall 综合评估

### 中文评论 NLP 分析
- jieba 中文分词
- 自定义中文停用词表
- 按评分维度的评论高频词分析
- 中文词云可视化

## 常见问题

**Q: 运行 init_mysql_db.py 报错连接失败？**
检查 MySQL 服务是否启动，以及 config.yaml 中的连接信息是否正确。

**Q: Pipeline 中途失败怎么办？**
每一步骤相互独立，可通过 --step 参数单独重跑。日志位于 logs/pipeline.log。

**Q: Docker 运行报错？**
确保 Docker Desktop 已启动（系统托盘图标为绿色）。首次构建镜像约需 3-5 分钟。

**Q: 如何修改流失阈值？**
编辑 config.yaml 中 thresholds.churn 节，调整 percentile 和 multiplier 参数。
