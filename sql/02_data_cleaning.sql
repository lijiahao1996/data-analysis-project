-- =============================================================
-- 02_data_cleaning.sql
-- 数据清洗逻辑（MySQL 8.0）
--
-- 用途：将原始导入数据清洗为可分析的干净数据集
-- 参考：utils/data_cleaner.py 中的 DataCleaner 类
--
-- 清洗流程：
--   1. 只保留已送达(delivered)的订单
--   2. 删除关键字段为 NULL 的记录
--   3. 日期字段标准化（确保 DATETIME 格式）
--   4. 关联 customers 表获取 customer_unique_id
--   5. 计算物流衍生字段（配送天数、延迟天数）
--   6. 去重处理
-- =============================================================

USE olist_ecommerce;

-- -----------------------------------------
-- Step 1: 创建清洗后的订单宽表 orders_clean
-- 合并 olist_orders + olist_customers
-- 仅保留 delivered 状态，剔除关键字段为 NULL 的行
-- -----------------------------------------
DROP TABLE IF EXISTS orders_clean;

CREATE TABLE orders_clean AS
SELECT
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    -- 物流衍生字段：实际配送天数 = 送达日期 - 购买日期
    DATEDIFF(o.order_delivered_customer_date, o.order_purchase_timestamp) AS delivery_days,
    -- 物流衍生字段：延迟天数 = 实际送达 - 预计送达（正数表示延迟）
    DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) AS delivery_delay_days
FROM olist_orders o
INNER JOIN olist_customers c ON o.customer_id = c.customer_id
WHERE
    -- 只保留已送达订单
    o.order_status = 'delivered'
    -- 关键字段不为空
    AND o.order_id IS NOT NULL
    AND o.customer_id IS NOT NULL
    AND o.order_purchase_timestamp IS NOT NULL
    -- 送达时间不为空（确保能计算物流指标）
    AND o.order_delivered_customer_date IS NOT NULL
    -- 关联到 customer_unique_id
    AND c.customer_unique_id IS NOT NULL;

-- -----------------------------------------
-- Step 2: 为清洗后的表添加主键和索引
-- -----------------------------------------
ALTER TABLE orders_clean
    ADD PRIMARY KEY (order_id),
    ADD INDEX idx_clean_customer_unique (customer_unique_id),
    ADD INDEX idx_clean_purchase_ts (order_purchase_timestamp);

-- -----------------------------------------
-- Step 3: 去重检查（同一 order_id 只保留一条）
-- 理论上 order_id 已是主键不会重复，
-- 此处用于确认数据完整性
-- -----------------------------------------
-- 如果存在重复的 order_id（正常不应发生），可执行：
-- DELETE t1 FROM orders_clean t1
-- INNER JOIN orders_clean t2
-- WHERE t1.order_id = t2.order_id
--   AND t1.order_purchase_timestamp < t2.order_purchase_timestamp;

-- -----------------------------------------
-- Step 4: 异常值过滤
-- 过滤掉配送天数为负数的异常记录（数据录入错误）
-- -----------------------------------------
DELETE FROM orders_clean
WHERE delivery_days < 0;

-- -----------------------------------------
-- Step 5: 数据质量统计（验证用）
-- -----------------------------------------
-- 查看清洗结果概览
SELECT
    COUNT(*) AS total_orders,
    COUNT(DISTINCT customer_unique_id) AS unique_users,
    MIN(order_purchase_timestamp) AS earliest_order,
    MAX(order_purchase_timestamp) AS latest_order,
    ROUND(AVG(delivery_days), 1) AS avg_delivery_days,
    ROUND(AVG(delivery_delay_days), 1) AS avg_delay_days,
    ROUND(SUM(CASE WHEN delivery_delay_days > 0 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS delayed_pct
FROM orders_clean;
