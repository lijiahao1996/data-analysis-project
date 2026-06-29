-- =============================================================
-- 03_feature_engineering.sql
-- 用户级特征工程（MySQL 8.0）
--
-- 用途：构建用户级分析宽表（30+ 维度特征）
-- 参考：utils/feature_builder.py 中的 FeatureBuilder 类
--
-- 特征维度：
--   1. 交易特征：订单数、消费金额、客单价、运费、商品数
--   2. 时间特征：首/末次购买、生命周期、RFM 相关
--   3. 物流特征：配送天数、延迟情况
--   4. 品类特征：主品类、多样性、集中度
--   5. 支付特征：支付方式、分期情况
--   6. 评价特征：评分分布、低评率
--   7. RFM 特征：分箱打分 + 分层标签
--
-- 截止日期：2018-10-17（与 config.yaml 一致）
-- =============================================================

USE olist_ecommerce;

-- 定义截止日期变量
SET @cutoff_date = '2018-10-17';

-- =============================================================
-- Part 1: 交易特征
-- =============================================================
DROP TABLE IF EXISTS tmp_feat_transaction;

CREATE TABLE tmp_feat_transaction AS
WITH order_level AS (
    -- 先在订单级别聚合：每单商品数、消费、运费
    SELECT
        oc.customer_unique_id,
        oc.order_id,
        COUNT(oi.product_id) AS item_count,
        COALESCE(SUM(oi.price), 0) AS order_spend,
        COALESCE(SUM(oi.freight_value), 0) AS order_freight
    FROM orders_clean oc
    LEFT JOIN olist_order_items oi ON oc.order_id = oi.order_id
    GROUP BY oc.customer_unique_id, oc.order_id
)
SELECT
    customer_unique_id,
    COUNT(DISTINCT order_id) AS total_orders,
    SUM(order_spend) + SUM(order_freight) AS total_spend,
    SUM(order_freight) AS total_freight,
    ROUND(AVG(item_count), 2) AS avg_items_per_order,
    ROUND((SUM(order_spend) + SUM(order_freight)) / COUNT(DISTINCT order_id), 2) AS avg_order_value
FROM order_level
GROUP BY customer_unique_id;

ALTER TABLE tmp_feat_transaction ADD PRIMARY KEY (customer_unique_id);

-- =============================================================
-- Part 2: 时间特征
-- =============================================================
DROP TABLE IF EXISTS tmp_feat_time;

CREATE TABLE tmp_feat_time AS
SELECT
    customer_unique_id,
    MIN(order_purchase_timestamp) AS first_purchase_date,
    MAX(order_purchase_timestamp) AS last_purchase_date,
    -- 客户生命周期天数（首购到截止日期）
    DATEDIFF(@cutoff_date, MIN(order_purchase_timestamp)) AS customer_tenure_days,
    -- Recency: 最近一次购买距截止日期天数
    DATEDIFF(@cutoff_date, MAX(order_purchase_timestamp)) AS recency_days,
    -- 购买频率 = 总订单数 / 生命周期月数（最少1个月）
    ROUND(
        COUNT(DISTINCT order_id) / GREATEST(DATEDIFF(@cutoff_date, MIN(order_purchase_timestamp)) / 30.0, 1),
        4
    ) AS purchase_frequency,
    -- 平均购买间隔（仅对多次购买用户有意义）
    CASE
        WHEN COUNT(DISTINCT order_id) > 1
        THEN ROUND(
            DATEDIFF(MAX(order_purchase_timestamp), MIN(order_purchase_timestamp))
            / (COUNT(DISTINCT order_id) - 1), 1
        )
        ELSE NULL
    END AS avg_purchase_interval
FROM orders_clean
GROUP BY customer_unique_id;

ALTER TABLE tmp_feat_time ADD PRIMARY KEY (customer_unique_id);

-- =============================================================
-- Part 3: 物流特征
-- =============================================================
DROP TABLE IF EXISTS tmp_feat_delivery;

CREATE TABLE tmp_feat_delivery AS
SELECT
    customer_unique_id,
    ROUND(AVG(delivery_days), 1) AS avg_delivery_days,
    ROUND(AVG(delivery_delay_days), 1) AS avg_delivery_delay,
    MAX(delivery_delay_days) AS max_delivery_delay,
    -- 延迟订单占比
    ROUND(
        SUM(CASE WHEN delivery_delay_days > 0 THEN 1 ELSE 0 END) / COUNT(*), 4
    ) AS delayed_order_ratio,
    -- 是否有严重延迟（>7天）
    MAX(CASE WHEN delivery_delay_days > 7 THEN 1 ELSE 0 END) AS has_severe_delay
FROM orders_clean
GROUP BY customer_unique_id;

ALTER TABLE tmp_feat_delivery ADD PRIMARY KEY (customer_unique_id);

-- =============================================================
-- Part 4: 品类特征
-- =============================================================
DROP TABLE IF EXISTS tmp_feat_category;

CREATE TABLE tmp_feat_category AS
WITH user_category_spend AS (
    -- 每用户每品类的消费
    SELECT
        oc.customer_unique_id,
        p.product_category_name,
        SUM(oi.price) AS cat_spend,
        COUNT(*) AS cat_count
    FROM orders_clean oc
    JOIN olist_order_items oi ON oc.order_id = oi.order_id
    JOIN olist_products p ON oi.product_id = p.product_id
    WHERE p.product_category_name IS NOT NULL
    GROUP BY oc.customer_unique_id, p.product_category_name
),
user_main_category AS (
    -- 最常购买品类（按购买次数取最多的）
    SELECT customer_unique_id, product_category_name AS main_category
    FROM (
        SELECT
            customer_unique_id,
            product_category_name,
            ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY cat_count DESC, cat_spend DESC) AS rn
        FROM user_category_spend
    ) ranked
    WHERE rn = 1
),
user_cat_diversity AS (
    -- 品类多样性
    SELECT
        customer_unique_id,
        COUNT(DISTINCT product_category_name) AS category_diversity
    FROM user_category_spend
    GROUP BY customer_unique_id
),
user_top_ratio AS (
    -- 最大品类消费占比
    SELECT
        ucs.customer_unique_id,
        ROUND(MAX(ucs.cat_spend) / SUM(ucs.cat_spend), 4) AS top_category_spend_ratio
    FROM user_category_spend ucs
    GROUP BY ucs.customer_unique_id
)
SELECT
    d.customer_unique_id,
    d.category_diversity,
    mc.main_category,
    tr.top_category_spend_ratio
FROM user_cat_diversity d
LEFT JOIN user_main_category mc ON d.customer_unique_id = mc.customer_unique_id
LEFT JOIN user_top_ratio tr ON d.customer_unique_id = tr.customer_unique_id;

ALTER TABLE tmp_feat_category ADD PRIMARY KEY (customer_unique_id);

-- =============================================================
-- Part 5: 支付特征
-- =============================================================
DROP TABLE IF EXISTS tmp_feat_payment;

CREATE TABLE tmp_feat_payment AS
WITH user_payment AS (
    SELECT
        oc.customer_unique_id,
        op.payment_type,
        op.payment_installments,
        op.payment_value
    FROM orders_clean oc
    JOIN olist_order_payments op ON oc.order_id = op.order_id
),
user_main_pay AS (
    -- 主要支付方式（使用次数最多的）
    SELECT customer_unique_id, payment_type AS main_payment_type
    FROM (
        SELECT
            customer_unique_id,
            payment_type,
            COUNT(*) AS pay_count,
            ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY COUNT(*) DESC) AS rn
        FROM user_payment
        GROUP BY customer_unique_id, payment_type
    ) ranked
    WHERE rn = 1
)
SELECT
    up.customer_unique_id,
    mp.main_payment_type,
    ROUND(AVG(up.payment_installments), 2) AS avg_installments,
    MAX(up.payment_installments) AS max_installments
FROM user_payment up
LEFT JOIN user_main_pay mp ON up.customer_unique_id = mp.customer_unique_id
GROUP BY up.customer_unique_id, mp.main_payment_type;

ALTER TABLE tmp_feat_payment ADD PRIMARY KEY (customer_unique_id);

-- =============================================================
-- Part 6: 评价特征
-- =============================================================
DROP TABLE IF EXISTS tmp_feat_review;

CREATE TABLE tmp_feat_review AS
SELECT
    oc.customer_unique_id,
    ROUND(AVG(r.review_score), 2) AS avg_review_score,
    MIN(r.review_score) AS min_review_score,
    SUM(CASE WHEN r.review_score <= 2 THEN 1 ELSE 0 END) AS low_score_count,
    ROUND(
        SUM(CASE WHEN r.review_score <= 2 THEN 1 ELSE 0 END) / COUNT(r.review_score), 4
    ) AS low_score_ratio,
    MAX(CASE WHEN r.review_comment_message IS NOT NULL AND r.review_comment_message != '' THEN 1 ELSE 0 END) AS has_review_comment
FROM orders_clean oc
JOIN olist_order_reviews r ON oc.order_id = r.order_id
WHERE r.review_score IS NOT NULL
GROUP BY oc.customer_unique_id;

ALTER TABLE tmp_feat_review ADD PRIMARY KEY (customer_unique_id);

-- =============================================================
-- Part 7: 合并所有特征为用户宽表
-- =============================================================
DROP TABLE IF EXISTS user_features;

CREATE TABLE user_features AS
SELECT
    t.customer_unique_id,
    -- 交易特征
    t.total_orders,
    t.total_spend,
    t.total_freight,
    t.avg_items_per_order,
    t.avg_order_value,
    -- 时间特征
    tm.first_purchase_date,
    tm.last_purchase_date,
    tm.customer_tenure_days,
    tm.recency_days,
    tm.purchase_frequency,
    tm.avg_purchase_interval,
    -- 物流特征
    d.avg_delivery_days,
    d.avg_delivery_delay,
    d.max_delivery_delay,
    d.delayed_order_ratio,
    d.has_severe_delay,
    -- 品类特征
    c.category_diversity,
    c.main_category,
    c.top_category_spend_ratio,
    -- 支付特征
    p.main_payment_type,
    p.avg_installments,
    p.max_installments,
    -- 评价特征
    r.avg_review_score,
    r.min_review_score,
    r.low_score_count,
    r.low_score_ratio,
    r.has_review_comment
FROM tmp_feat_transaction t
LEFT JOIN tmp_feat_time tm ON t.customer_unique_id = tm.customer_unique_id
LEFT JOIN tmp_feat_delivery d ON t.customer_unique_id = d.customer_unique_id
LEFT JOIN tmp_feat_category c ON t.customer_unique_id = c.customer_unique_id
LEFT JOIN tmp_feat_payment p ON t.customer_unique_id = p.customer_unique_id
LEFT JOIN tmp_feat_review r ON t.customer_unique_id = r.customer_unique_id;

ALTER TABLE user_features ADD PRIMARY KEY (customer_unique_id);

-- =============================================================
-- Part 8: RFM 特征（四分位分箱打分）
-- R: recency_days 越小得分越高（最近=4分）
-- F: purchase_frequency 越高得分越高
-- M: total_spend 越高得分越高
-- =============================================================
ALTER TABLE user_features
    ADD COLUMN rfm_r_score TINYINT DEFAULT NULL,
    ADD COLUMN rfm_f_score TINYINT DEFAULT NULL,
    ADD COLUMN rfm_m_score TINYINT DEFAULT NULL,
    ADD COLUMN rfm_segment VARCHAR(20) DEFAULT NULL;

-- R 得分：recency 越小 → 得分越高
UPDATE user_features uf
JOIN (
    SELECT
        customer_unique_id,
        NTILE(4) OVER (ORDER BY recency_days DESC) AS r_score
    FROM user_features
) scores ON uf.customer_unique_id = scores.customer_unique_id
SET uf.rfm_r_score = scores.r_score;

-- F 得分：frequency 越高 → 得分越高
UPDATE user_features uf
JOIN (
    SELECT
        customer_unique_id,
        NTILE(4) OVER (ORDER BY purchase_frequency ASC) AS f_score
    FROM user_features
) scores ON uf.customer_unique_id = scores.customer_unique_id
SET uf.rfm_f_score = scores.f_score;

-- M 得分：monetary 越高 → 得分越高
UPDATE user_features uf
JOIN (
    SELECT
        customer_unique_id,
        NTILE(4) OVER (ORDER BY total_spend ASC) AS m_score
    FROM user_features
) scores ON uf.customer_unique_id = scores.customer_unique_id
SET uf.rfm_m_score = scores.m_score;

-- RFM 分层标签
UPDATE user_features
SET rfm_segment = CASE
    WHEN rfm_r_score >= 3 AND rfm_f_score >= 3 AND rfm_m_score >= 3 THEN '高价值客户'
    WHEN rfm_r_score >= 3 AND (rfm_f_score >= 2 OR rfm_m_score >= 3)  THEN '重点保持'
    WHEN rfm_r_score <= 2 AND rfm_f_score >= 2                        THEN '需唤醒'
    ELSE '流失风险'
END;

-- =============================================================
-- Part 9: 清理临时表
-- =============================================================
DROP TABLE IF EXISTS tmp_feat_transaction;
DROP TABLE IF EXISTS tmp_feat_time;
DROP TABLE IF EXISTS tmp_feat_delivery;
DROP TABLE IF EXISTS tmp_feat_category;
DROP TABLE IF EXISTS tmp_feat_payment;
DROP TABLE IF EXISTS tmp_feat_review;

-- =============================================================
-- 验证：查看特征宽表摘要
-- =============================================================
SELECT
    COUNT(*) AS total_users,
    COUNT(rfm_segment) AS rfm_labeled,
    ROUND(AVG(total_orders), 2) AS avg_orders,
    ROUND(AVG(total_spend), 2) AS avg_spend,
    ROUND(AVG(recency_days), 1) AS avg_recency
FROM user_features;

-- RFM 分层分布
SELECT
    rfm_segment,
    COUNT(*) AS user_count,
    ROUND(COUNT(*) / (SELECT COUNT(*) FROM user_features) * 100, 2) AS pct
FROM user_features
GROUP BY rfm_segment
ORDER BY user_count DESC;
