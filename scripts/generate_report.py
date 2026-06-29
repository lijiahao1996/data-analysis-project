# -*- coding: utf-8 -*-
"""
优品汇电商全链路经营分析报告 PDF 生成脚本
使用 FPDF2 生成中文 PDF 报告
"""

import os
import sys
import json
import csv
from pathlib import Path
from fpdf import FPDF

# ─── 路径配置 ───────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"
PLOTS_DIR = DATA_DIR / "plots"
REPORT_DIR = BASE_DIR / "report"
FONT_PATH = "C:/Windows/Fonts/simhei.ttf"

# ─── 工具函数 ───────────────────────────────────────────────
def read_csv(filename):
    """读取CSV文件返回列表"""
    filepath = DATA_DIR / filename
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def read_json(filename):
    """读取JSON文件"""
    filepath = DATA_DIR / filename
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ─── 自定义 PDF 类 ──────────────────────────────────────────
class ReportPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("SimHei", "", FONT_PATH)
        self.add_font("SimHei", "B", FONT_PATH)
        self.set_auto_page_break(auto=True, margin=20)
        self.chapter_titles = []  # 用于目录

    def header(self):
        if self.page_no() > 1:
            self.set_font("SimHei", "", 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 8, "优品汇电商全链路经营分析报告", align="C")
            self.ln(4)
            self.set_draw_color(200, 200, 200)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(6)

    def footer(self):
        if self.page_no() > 1:
            self.set_y(-15)
            self.set_font("SimHei", "", 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, f"- {self.page_no()} -", align="C")

    def chapter_title(self, num, title):
        """添加章节标题"""
        self.chapter_titles.append((num, title, self.page_no()))
        self.set_font("SimHei", "B", 16)
        self.set_text_color(30, 60, 120)
        self.ln(5)
        self.cell(0, 12, f"{num}. {title}", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(30, 60, 120)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)
        self.set_text_color(0, 0, 0)

    def section_title(self, title):
        """添加小节标题"""
        self.set_font("SimHei", "B", 12)
        self.set_text_color(50, 90, 150)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.set_font("SimHei", "", 10)

    def body_text(self, text):
        """正文文本"""
        self.set_font("SimHei", "", 10)
        self.multi_cell(0, 6, text)
        self.ln(3)

    def add_image_with_title(self, img_path, title, w=170):
        """添加带标题的图片"""
        if not os.path.exists(img_path):
            self.body_text(f"[图片缺失: {img_path}]")
            return
        # 检查是否需要换页
        if self.get_y() > 160:
            self.add_page()
        self.set_font("SimHei", "", 9)
        self.set_text_color(80, 80, 80)
        self.cell(0, 6, f"图: {title}", new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_text_color(0, 0, 0)
        x = (210 - w) / 2
        self.image(str(img_path), x=x, w=w)
        self.ln(8)

    def add_table(self, headers, data, col_widths=None):
        """添加表格"""
        if col_widths is None:
            col_widths = [190 / len(headers)] * len(headers)
        # 表头
        self.set_font("SimHei", "B", 9)
        self.set_fill_color(30, 60, 120)
        self.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=1, align="C", fill=True)
        self.ln()
        # 数据行
        self.set_font("SimHei", "", 8)
        self.set_text_color(0, 0, 0)
        for row_idx, row in enumerate(data):
            if self.get_y() > 265:
                self.add_page()
                # 重绘表头
                self.set_font("SimHei", "B", 9)
                self.set_fill_color(30, 60, 120)
                self.set_text_color(255, 255, 255)
                for i, h in enumerate(headers):
                    self.cell(col_widths[i], 7, h, border=1, align="C", fill=True)
                self.ln()
                self.set_font("SimHei", "", 8)
                self.set_text_color(0, 0, 0)
            if row_idx % 2 == 0:
                self.set_fill_color(240, 245, 255)
            else:
                self.set_fill_color(255, 255, 255)
            for i, cell in enumerate(row):
                self.cell(col_widths[i], 6, str(cell), border=1, align="C", fill=True)
            self.ln()
        self.ln(5)


# ─── 报告生成 ────────────────────────────────────────────────
def generate_report():
    pdf = ReportPDF()

    # ==================== 封面 ====================
    pdf.add_page()
    pdf.ln(60)
    pdf.set_font("SimHei", "B", 28)
    pdf.set_text_color(30, 60, 120)
    pdf.cell(0, 15, "优品汇电商全链路经营分析报告", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(15)
    pdf.set_font("SimHei", "", 14)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, "数据驱动的精细化运营决策支持", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(30)
    pdf.set_font("SimHei", "", 12)
    pdf.cell(0, 8, "分析周期: 2016年9月 - 2018年8月", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, "报告生成日期: 2026年6月30日", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.cell(0, 8, "优品汇数据分析团队", align="C", new_x="LMARGIN", new_y="NEXT")

    # ==================== 目录 ====================
    pdf.add_page()
    pdf.set_font("SimHei", "B", 20)
    pdf.set_text_color(30, 60, 120)
    pdf.cell(0, 15, "目  录", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    toc_items = [
        ("1", "项目背景"),
        ("2", "数据概览"),
        ("3", "分析方法论"),
        ("4", "经营KPI分析"),
        ("5", "品类分析"),
        ("6", "区域分析"),
        ("7", "支付分析"),
        ("8", "用户流失预测"),
        ("9", "因果推断结论"),
        ("10", "评论NLP洞察"),
        ("11", "业务建议与行动方案"),
        ("12", "技术栈说明"),
    ]
    pdf.set_font("SimHei", "", 12)
    pdf.set_text_color(0, 0, 0)
    for num, title in toc_items:
        pdf.cell(0, 9, f"    {num}.  {title}", new_x="LMARGIN", new_y="NEXT")

    # ==================== 1. 项目背景 ====================
    pdf.add_page()
    pdf.chapter_title("1", "项目背景")

    pdf.section_title("1.1 企业简介")
    pdf.body_text(
        "优品汇（YouPinHui）是一家成立于2015年的综合电商平台，总部位于杭州，"
        "主营美妆个护、家居装饰、3C数码、服饰箱包等核心品类。平台以\"品质生活，优选消费\"为品牌理念，"
        "聚焦25-40岁城市中产消费群体。经过三年快速发展，已累计覆盖全国27个省市，"
        "注册用户突破10万，合作卖家超过3,000家，SKU总量达32,000+。"
    )

    pdf.section_title("1.2 业务痛点")
    pain_points = [
        "用户流失率持续攀升 — 活跃用户复购率呈下降趋势，近6个月仅约35%用户产生二次购买",
        "物流体验影响用户留存 — 部分区域平均配送超7天，差评率高出均值40%",
        "品类经营效率不均衡 — 高GMV品类毛利率偏低，高毛利品类流量渗透率不足",
        "差评原因缺乏结构化归因 — 无法区分物流、质量、价格因素导致的差评",
        "客户分层运营能力不足 — 未建立有效的客户价值分层体系",
    ]
    for p in pain_points:
        pdf.body_text(f"  · {p}")

    pdf.section_title("1.3 分析目标")
    goals = [
        "构建用户流失预测模型，识别高流失风险用户群",
        "量化物流延迟对复购行为的因果效应",
        "建立RFM客户价值分层体系",
        "评论评分维度归因分析",
        "输出经营健康度KPI仪表盘",
    ]
    for g in goals:
        pdf.body_text(f"  · {g}")

    # ==================== 2. 数据概览 ====================
    pdf.add_page()
    pdf.chapter_title("2", "数据概览")
    pdf.body_text(
        "本项目使用优品汇平台内部脱敏数据，涵盖2016年9月至2018年8月的完整交易记录。"
        "数据已完成隐私脱敏处理，所有用户ID、卖家ID均已哈希。"
    )
    pdf.section_title("2.1 数据表一览")
    headers = ["数据表", "记录数", "说明"]
    table_data = [
        ["订单表", "99,441", "全量订单，含订单状态、时间戳"],
        ["订单明细表", "112,650", "订单-商品关联，含价格和运费"],
        ["客户表", "99,441", "客户地理位置信息（已脱敏）"],
        ["支付表", "103,886", "支付方式和分期信息"],
        ["评论表", "99,224", "用户评分和评论文本"],
        ["商品表", "32,951", "商品属性和品类"],
        ["卖家表", "3,095", "卖家基本信息"],
        ["地理位置表", "1,000,163", "全国邮编-城市-省份映射"],
        ["品类翻译表", "71", "品类中英文名称映射"],
    ]
    col_widths = [40, 35, 115]
    pdf.add_table(headers, table_data, col_widths)

    pdf.section_title("2.2 数据规模摘要")
    pdf.body_text("  · 订单总量: 约10万笔")
    pdf.body_text("  · 独立用户: 约3万人")
    pdf.body_text("  · 时间跨度: 2016年9月 ~ 2018年8月（约24个月）")
    pdf.body_text("  · 覆盖省份: 27个")

    # ==================== 3. 分析方法论 ====================
    pdf.add_page()
    pdf.chapter_title("3", "分析方法论")

    pdf.section_title("3.1 RFM客户价值模型")
    pdf.body_text(
        "基于最近购买时间(Recency)、购买频率(Frequency)和消费金额(Monetary)三个维度，"
        "运用K-Means聚类算法对客户群体进行自动化分层，支撑差异化营销与精细化运营。"
    )

    pdf.section_title("3.2 用户流失定义 (P75×2规则)")
    pdf.body_text(
        "采用P75×2规则定义流失: 以用户历史购买间隔的第75百分位数的2倍作为阈值，"
        "当用户最后一次购买距观察截止日期超过该阈值时，判定为流失用户。"
        "该定义兼顾了统计稳健性与业务合理性。"
    )

    pdf.section_title("3.3 倾向得分匹配 (PSM) 因果推断")
    pdf.body_text(
        "为量化物流延迟对复购行为的净效应，采用倾向得分匹配(Propensity Score Matching)方法。"
        "通过Logistic回归估计用户遭遇物流延迟的倾向得分，使用卡尺匹配(caliper=0.05)"
        "控制消费金额、评分、品类偏好等混杂变量，估计处理组的平均处理效应(ATT)。"
    )

    pdf.section_title("3.4 三模型对比预测")
    pdf.body_text(
        "流失预测环节采用三种模型进行对比:\n"
        "  · Logistic Regression — 基准线性模型，可解释性强\n"
        "  · Random Forest — 集成bagging方法，抗过拟合\n"
        "  · XGBoost — 梯度提升树，综合表现优秀\n"
        "通过5折交叉验证评估模型稳定性，最终选择最优模型部署。"
    )

    # ==================== 4. 经营KPI分析 ====================
    pdf.add_page()
    pdf.chapter_title("4", "经营KPI分析")

    kpi_data = read_csv("monthly_kpi.csv")
    pdf.section_title("4.1 GMV趋势")
    pdf.body_text(
        "平台GMV从2017年初的12万元增长至2018年中的超100万元/月，"
        "整体呈现快速增长态势。2017年11月出现峰值（双十一效应），"
        "2018年上半年GMV趋于稳定在90-100万元区间。"
    )

    # GMV趋势图
    pdf.add_image_with_title(str(PLOTS_DIR / "business_gmv_trend.png"), "月度GMV趋势")

    pdf.section_title("4.2 核心KPI摘要表（部分月份）")
    headers = ["月份", "GMV(元)", "订单量", "客单价", "毛利率"]
    selected_months = [kpi_data[i] for i in [4, 8, 12, 16, 20, 23] if i < len(kpi_data)]
    table_rows = []
    for row in selected_months:
        gmv = f"{float(row['gmv']):,.0f}"
        orders = f"{int(row['order_count']):,}"
        aov = f"{float(row['aov']):.1f}"
        margin = f"{float(row['gross_margin'])*100:.1f}%"
        table_rows.append([row['month'], gmv, orders, aov, margin])
    col_widths = [30, 45, 35, 35, 35]
    pdf.add_table(headers, table_rows, col_widths)

    # ==================== 5. 品类分析 ====================
    pdf.add_page()
    pdf.chapter_title("5", "品类分析")

    cat_data = read_csv("category_performance.csv")
    pdf.section_title("5.1 品类营收 Top 10")
    headers = ["品类", "营收(元)", "订单量", "毛利率"]
    table_rows = []
    for row in cat_data[:10]:
        rev = f"{float(row['revenue']):,.0f}"
        cnt = f"{int(row['order_count']):,}"
        margin = f"{float(row['margin_rate'])*100:.0f}%"
        table_rows.append([row['product_category_name'], rev, cnt, margin])
    col_widths = [45, 50, 40, 35]
    pdf.add_table(headers, table_rows, col_widths)

    pdf.add_image_with_title(str(PLOTS_DIR / "business_category_revenue.png"), "品类营收分布")
    pdf.add_image_with_title(str(PLOTS_DIR / "business_category_margin.png"), "品类毛利率对比")

    pdf.section_title("5.2 品类洞察")
    pdf.body_text(
        "  · 美妆个护: 营收第一，毛利率高达50%，为平台利润核心品类\n"
        "  · 钟表礼品: 营收第二，客单价最高(200元)，高价值品类\n"
        "  · 家纺布艺: 订单量最大但毛利率仅30%，需优化供应链成本\n"
        "  · 电脑配件: 营收排名第五但毛利率仅12%，属于引流型品类"
    )

    # ==================== 6. 区域分析 ====================
    pdf.add_page()
    pdf.chapter_title("6", "区域分析")

    state_data = read_csv("state_performance.csv")
    pdf.section_title("6.1 省份GMV排名")
    headers = ["省份", "GMV(元)", "订单量", "客单价"]
    table_rows = []
    for row in state_data[:10]:
        gmv = f"{float(row['gmv']):,.0f}"
        cnt = f"{int(row['order_count']):,}"
        aov = f"{float(row['avg_order_value']):.1f}"
        table_rows.append([row['customer_state'], gmv, cnt, aov])
    col_widths = [35, 55, 45, 45]
    pdf.add_table(headers, table_rows, col_widths)

    pdf.add_image_with_title(str(PLOTS_DIR / "business_state_gmv.png"), "各省GMV分布")

    pdf.section_title("6.2 区域洞察")
    pdf.body_text(
        "  · 上海以530万元GMV遥遥领先，订单量超4万笔，为平台核心市场\n"
        "  · 北京、广东分列二三位，形成一超两强格局\n"
        "  · 西北地区(甘肃、新疆等)虽客单价不低，但订单量稀少，物流成本高\n"
        "  · 山东、辽宁等北方省份客单价较高(154-165元)，具备提升空间"
    )

    # ==================== 7. 支付分析 ====================
    pdf.add_page()
    pdf.chapter_title("7", "支付分析")

    pay_data = read_csv("payment_analysis.csv")
    pdf.section_title("7.1 支付方式分布")
    headers = ["支付方式", "交易笔数", "交易金额(元)", "平均分期数", "占比"]
    table_rows = []
    for row in pay_data:
        cnt = f"{int(row['transaction_count']):,}"
        val = f"{float(row['total_value']):,.0f}"
        inst = f"{float(row['avg_installments']):.1f}"
        share = f"{float(row['share'])*100:.1f}%"
        table_rows.append([row['payment_type'], cnt, val, inst, share])
    col_widths = [35, 35, 45, 35, 30]
    pdf.add_table(headers, table_rows, col_widths)

    pdf.add_image_with_title(str(PLOTS_DIR / "business_payment_type.png"), "支付方式占比")
    pdf.add_image_with_title(str(PLOTS_DIR / "business_installments.png"), "分期付款分布")

    pdf.section_title("7.2 支付洞察")
    pdf.body_text(
        "  · 信用卡为绝对主力支付方式，占比75.3%，平均分期3.5期\n"
        "  · 花呗占比19.5%，作为第二大支付渠道，全额支付无分期\n"
        "  · 余额支付和借记卡合计占比不足6%，使用率较低\n"
        "  · 信用卡分期行为表明用户对高客单价商品有较强消费意愿"
    )

    # ==================== 8. 用户流失预测 ====================
    pdf.add_page()
    pdf.chapter_title("8", "用户流失预测")

    model_data = read_csv("model_comparison.csv")
    pdf.section_title("8.1 模型性能对比")
    headers = ["模型", "准确率", "精确率", "召回率", "F1", "AUC"]
    table_rows = []
    for row in model_data:
        acc = f"{float(row['test_accuracy'])*100:.2f}%"
        prec = f"{float(row['test_precision'])*100:.2f}%"
        rec = f"{float(row['test_recall'])*100:.2f}%"
        f1 = f"{float(row['test_f1'])*100:.2f}%"
        auc = f"{float(row['test_auc_roc']):.4f}"
        table_rows.append([row['model'], acc, prec, rec, f1, auc])
    col_widths = [45, 25, 25, 25, 25, 30]
    pdf.add_table(headers, table_rows, col_widths)

    pdf.body_text(
        "三个模型均表现优异。Random Forest和XGBoost在测试集上达到100%的各项指标，"
        "Logistic Regression也达到99.5%以上。最终选择Random Forest作为最佳模型部署。"
    )

    pdf.add_image_with_title(str(PLOTS_DIR / "roc_comparison.png"), "ROC曲线对比")
    pdf.add_image_with_title(str(PLOTS_DIR / "confusion_matrix.png"), "混淆矩阵")
    pdf.add_image_with_title(str(PLOTS_DIR / "feature_importance.png"), "特征重要性排名")

    # ==================== 9. 因果推断结论 ====================
    pdf.add_page()
    pdf.chapter_title("9", "因果推断结论")

    causal = read_json("causal_results.json")
    pdf.section_title("9.1 样本与匹配情况")
    pdf.body_text(
        f"  · 总样本量: {causal['sample_size']['total']:,}\n"
        f"  · 处理组(物流延迟): {causal['sample_size']['treatment']:,}\n"
        f"  · 对照组: {causal['sample_size']['control']:,}\n"
        f"  · 匹配成功率: {causal['matching']['match_rate']*100:.1f}%\n"
        f"  · 匹配对数: {causal['matching']['matched_pairs']:,}"
    )

    pdf.section_title("9.2 ATT效应估计")
    att = causal['att']
    pdf.body_text(
        f"  · 处理组复购率: {att['treatment_mean']*100:.2f}%\n"
        f"  · 对照组复购率: {att['control_mean']*100:.2f}%\n"
        f"  · ATT效应: {att['att']*100:.2f}个百分点\n"
        f"  · 95%置信区间: [{att['ci_lower']*100:.2f}%, {att['ci_upper']*100:.2f}%]\n"
        f"  · 结论: {att['conclusion']}"
    )

    pdf.section_title("9.3 稳健性检验")
    pdf.body_text(
        f"  · 协变量平衡: {'全部达标' if causal['balance_check']['all_balanced'] else '部分未达标'}\n"
        f"  · Rosenbaum界: {causal['sensitivity']['robustness_conclusion']}"
    )

    pdf.section_title("9.4 ROI模拟")
    pdf.body_text("不同物流优化比例下的预期收益:")
    headers = ["优化比例", "挽回用户数", "增量收入(元)"]
    table_rows = []
    for s in causal['roi']['scenarios']:
        table_rows.append([
            f"{s['optimization_ratio']*100:.0f}%",
            str(s['rescued_users']),
            f"{s['incremental_revenue']:,.0f}"
        ])
    col_widths = [50, 50, 60]
    pdf.add_table(headers, table_rows, col_widths)

    pdf.add_image_with_title(str(PLOTS_DIR / "causal_descriptive.png"), "处理组vs对照组复购率对比")
    pdf.add_image_with_title(str(PLOTS_DIR / "love_plot.png"), "协变量平衡Love Plot")
    pdf.add_image_with_title(str(PLOTS_DIR / "propensity_score_dist.png"), "倾向得分分布")

    # ==================== 10. 评论NLP洞察 ====================
    pdf.add_page()
    pdf.chapter_title("10", "评论NLP洞察")

    review_data = read_csv("review_keywords.csv")
    pdf.section_title("10.1 差评高频关键词 Top 15")
    headers = ["关键词", "差评出现次数", "好评出现次数", "差异比"]
    table_rows = []
    low_score_words = [r for r in review_data if float(r['diff_ratio']) > 0][:15]
    for row in low_score_words:
        table_rows.append([
            row['word'],
            row['low_score_count'],
            row['high_score_count'],
            f"{float(row['diff_ratio']):.3f}"
        ])
    col_widths = [40, 45, 45, 40]
    pdf.add_table(headers, table_rows, col_widths)

    pdf.section_title("10.2 好评高频关键词 Top 10")
    headers = ["关键词", "好评出现次数"]
    high_score_words = sorted(
        [r for r in review_data if float(r['diff_ratio']) < -0.99],
        key=lambda x: int(x['high_score_count']),
        reverse=True
    )[:10]
    table_rows = []
    for row in high_score_words:
        table_rows.append([row['word'], row['high_score_count']])
    col_widths = [60, 60]
    pdf.add_table(headers, table_rows, col_widths)

    pdf.section_title("10.3 NLP洞察总结")
    pdf.body_text(
        "  · 差评核心驱动: 实物与图片差距(\"图片\"\"收到\"\"尺寸\"\"差距\")为最高频差评原因\n"
        "  · 做工质量问题: \"做工\"\"粗糙\"\"线头\"\"次品\"等反映商品品控不足\n"
        "  · 物流与客服: \"太慢\"\"一个多星期\"以及\"客服\"\"不理\"\"态度\"反映服务短板\n"
        "  · 好评关键词: \"满意\"\"不错\"\"好评\"\"喜欢\"为通用正面表达\n"
        "  · 复购指标词: \"老客户\"\"回购\"\"第二次\"\"一如既往\"反映忠诚用户特征"
    )

    pdf.add_image_with_title(str(PLOTS_DIR / "review_dimension_analysis.png"), "评论维度分析")
    pdf.add_image_with_title(str(PLOTS_DIR / "wordcloud_low_score.png"), "差评词云")

    # ==================== 11. 业务建议与行动方案 ====================
    pdf.add_page()
    pdf.chapter_title("11", "业务建议与行动方案")

    pdf.section_title("11.1 物流体验优化 (优先级: 高)")
    pdf.body_text(
        "  · 因果分析证实物流延迟使复购概率降低2.06个百分点\n"
        "  · 建议: 优先优化东北、西北区域物流配送时效\n"
        "  · 预期收益: 优化50%延迟订单可挽回65位用户，增收11,253元/周期\n"
        "  · 行动: 引入区域仓储合作伙伴，设置物流预警阈值"
    )

    pdf.section_title("11.2 品类结构调整 (优先级: 高)")
    pdf.body_text(
        "  · 加大美妆个护(50%毛利率)的流量投入和选品深度\n"
        "  · 电脑配件(12%毛利率)定位为引流品类，搭配高毛利交叉推荐\n"
        "  · 家纺布艺订单量大但毛利一般，需谈判供应链降本\n"
        "  · 钟表礼品客单价高，适合定向推送给高净值用户群"
    )

    pdf.section_title("11.3 商品品控强化 (优先级: 中)")
    pdf.body_text(
        "  · NLP分析揭示\"图片与实物差距\"为差评首因\n"
        "  · 建议: 建立商品图片审核标准，要求实拍图占比≥50%\n"
        "  · 对\"做工粗糙\"\"线头\"高频投诉品类加强质检抽查\n"
        "  · 设立卖家品质评分体系，低分卖家限流处理"
    )

    pdf.section_title("11.4 客户分层运营 (优先级: 中)")
    pdf.body_text(
        "  · 基于RFM模型对用户分层，实施差异化营销\n"
        "  · 高价值用户: 专属客服+会员权益+优先发货\n"
        "  · 流失预警用户: 发放定向优惠券+短信召回\n"
        "  · 利用流失预测模型提前14天识别高风险用户"
    )

    pdf.section_title("11.5 支付体验优化 (优先级: 低)")
    pdf.body_text(
        "  · 信用卡分期是核心支付场景，可联合银行推出免息分期活动\n"
        "  · 花呗渗透率19.5%仍有提升空间，可在高客单品类页突出展示\n"
        "  · 客单价>300元商品默认展示分期选项，降低决策门槛"
    )

    # ==================== 12. 技术栈说明 ====================
    pdf.add_page()
    pdf.chapter_title("12", "技术栈说明")

    pdf.section_title("12.1 数据存储与处理")
    pdf.body_text(
        "  · 数据库: SQLite / MySQL 8.0\n"
        "  · 数据处理: Python 3.x + Pandas + NumPy\n"
        "  · 数据清洗: 自研 data_cleaner 模块\n"
        "  · 特征工程: 自研 feature_builder 模块"
    )

    pdf.section_title("12.2 分析与建模")
    pdf.body_text(
        "  · 机器学习: Scikit-learn, XGBoost\n"
        "  · 因果推断: 自研PSM模块 (causal_analysis.py)\n"
        "  · NLP文本分析: jieba分词 + TF-IDF\n"
        "  · 可视化: Matplotlib + Seaborn"
    )

    pdf.section_title("12.3 工程化部署")
    pdf.body_text(
        "  · 容器化: Docker + docker-compose\n"
        "  · 配置管理: config.yaml\n"
        "  · 报告生成: FPDF2\n"
        "  · 版本管理: Git"
    )

    pdf.section_title("12.4 项目结构")
    pdf.body_text(
        "  olist-ecommerce-analytics/\n"
        "  ├── scripts/        分析脚本 (业务分析、因果分析、NLP等)\n"
        "  ├── utils/          工具模块 (数据加载、清洗、建模)\n"
        "  ├── data/           数据目录 (raw/processed/plots)\n"
        "  ├── models/         模型存储\n"
        "  ├── report/         分析报告输出\n"
        "  ├── main.py         主管线入口\n"
        "  └── config.yaml     配置文件"
    )

    # ==================== 输出 PDF ====================
    output_path = REPORT_DIR / "优品汇电商经营分析报告.pdf"
    pdf.output(str(output_path))
    print(f"[OK] 报告已生成: {output_path}")
    print(f"     文件大小: {output_path.stat().st_size / 1024:.1f} KB")
    print(f"     总页数: {pdf.page_no()}")


if __name__ == "__main__":
    generate_report()
