-- =============================================================
-- 04_churn_labels.sql
-- 流失标签定义（MySQL 8.0）
--
-- 用途：基于 P75×2 动态阈值法构建用户流失标签
-- 参考：scripts/churn_label_builder.py 中的 ChurnLabelBuilder 类
--
-- 核心算法：
--   1. 筛选多次购买用户（>=2单）计算购买间隔
--   2. 取购买间隔的 P75 分位数
--   3. 流失阈值 = P75 × 2
--   4. 若用户 recency_days > 阈值，则标记为流失
--
-- 业务说明：
--   P75 代表 75% 用户的典型回购周期上限，
--   2倍系数表示超出正常周期两倍仍未回购→判定流失
-- =============================================================

USE olist_ecommerce;

-- 截止日期（与 config.yaml 一致）
SET @cutoff_date = '2018-10-17';
-- 参与阈值计算的最少订单数
SET @min_orders = 2;
-- P75 乘数
SET @multiplier = 2;

-- =============================================================
-- Step 1: 计算多次购买用户的购买间隔
-- =============================================================
DROP TABLE IF EXISTS tmp_purchase_intervals;

CREATE TABLE tmp_purchase_intervals AS
WITH user_order_seq AS (
    -- 每用户每订单只保留一条，按时间排序
    SELECT
        customer_unique_id,
        order_id,
        order_purchase_timestamp,
        ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY order_purchase_timestamp) AS seq_num
    FROM orders_clean
),
qualified_users AS (
    -- 筛选订单数 >= @min_orders 的用户
    SELECT customer_unique_id
    FROM orders_clean
    GROUP BY customer_unique_id
    HAVING COUNT(DISTINCT order_id) >= 2  -- @min_orders
),
intervals AS (
    -- 计算相邻订单间隔天数（用 LAG 窗口函数）
    SELECT
        s.customer_unique_id,
        s.order_purchase_timestamp,
        DATEDIFF(
            s.order_purchase_timestamp,
            LAG(s.order_purchase_timestamp) OVER (
                PARTITION BY s.customer_unique_id ORDER BY s.order_purchase_timestamp
            )
        ) AS purchase_interval_days
    FROM user_order_seq s
    INNER JOIN qualified_users q ON s.customer_unique_id = q.customer_unique_id
)
SELECT
    customer_unique_id,
    purchase_interval_days
FROM intervals
WHERE purchase_interval_days IS NOT NULL
  AND purchase_interval_days > 0;

-- =============================================================
-- Step 2: 计算 P75 分位数
-- 使用 PERCENT_RANK 近似 P75
-- =============================================================
DROP TABLE IF EXISTS tmp_churn_threshold;

CREATE TABLE tmp_churn_threshold AS
WITH ranked_intervals AS (
    SELECT
        purchase_interval_days,
        PERCENT_RANK() OVER (ORDER BY purchase_interval_days) AS pct_rank
    FROM tmp_purchase_intervals
)
SELECT
    -- P75: 取最接近 75% 分位的值
    MIN(purchase_interval_days) AS p75_interval,
    -- 流失阈值 = P75 × multiplier
    MIN(purchase_interval_days) * 2 AS churn_threshold  -- @multiplier = 2
FROM ranked_intervals
WHERE pct_rank >= 0.75;

-- =============================================================
-- Step 3: 创建流失标签表
-- =============================================================
DROP TABLE IF EXISTS churn_labels;

CREATE TABLE churn_labels AS
SELECT
    uf.customer_unique_id,
    uf.recency_days,
    uf.total_orders,
    thr.churn_threshold,
    uf.recency_days AS days_since_last,
    -- 流失判定：recency > 阈值 → 流失
    CASE
        WHEN uf.recency_days > thr.churn_threshold THEN 1
        ELSE 0
    END AS is_churned
FROM user_features uf
CROSS JOIN tmp_churn_threshold thr;

ALTER TABLE churn_labels ADD PRIMARY KEY (customer_unique_id);
ALTER TABLE churn_labels ADD INDEX idx_churn_label (is_churned);

-- =============================================================
-- Step 4: 将流失标签写回 user_features 表
-- =============================================================
ALTER TABLE user_features
    ADD COLUMN IF NOT EXISTS is_churned TINYINT DEFAULT NULL;

UPDATE user_features uf
JOIN churn_labels cl ON uf.customer_unique_id = cl.customer_unique_id
SET uf.is_churned = cl.is_churned;

-- =============================================================
-- Step 5: 清理临时表
-- =============================================================
DROP TABLE IF EXISTS tmp_purchase_intervals;
DROP TABLE IF EXISTS tmp_churn_threshold;

-- =============================================================
-- 验证：流失统计摘要
-- =============================================================
SELECT
    (SELECT churn_threshold FROM churn_labels LIMIT 1) AS churn_threshold_days,
    COUNT(*) AS total_users,
    SUM(is_churned) AS churned_users,
    ROUND(SUM(is_churned) / COUNT(*) * 100, 2) AS churn_rate_pct
FROM churn_labels;

-- 按订单数分组的流失率
SELECT
    CASE
        WHEN total_orders = 1 THEN '单次购买'
        WHEN total_orders BETWEEN 2 AND 3 THEN '2-3次'
        ELSE '4次以上'
    END AS order_group,
    COUNT(*) AS user_count,
    SUM(is_churned) AS churned,
    ROUND(SUM(is_churned) / COUNT(*) * 100, 2) AS churn_rate_pct
FROM churn_labels
GROUP BY
    CASE
        WHEN total_orders = 1 THEN '单次购买'
        WHEN total_orders BETWEEN 2 AND 3 THEN '2-3次'
        ELSE '4次以上'
    END
ORDER BY churn_rate_pct DESC;
