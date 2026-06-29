-- =============================================================
-- 05_business_kpi.sql
-- 核心经营 KPI 计算（MySQL 版本）
-- =============================================================

-- -----------------------------------------
-- 1. 月度 GMV、订单量、客单价
-- -----------------------------------------
SELECT 
    DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS year_month,
    COUNT(DISTINCT o.order_id) AS order_count,
    SUM(i.price) AS gmv,
    SUM(i.freight_value) AS total_freight,
    SUM(i.price) / COUNT(DISTINCT o.order_id) AS aov  -- 客单价 (Average Order Value)
FROM olist_orders o
JOIN olist_order_items i ON o.order_id = i.order_id
WHERE o.order_status = 'delivered'
GROUP BY DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m')
ORDER BY year_month;


-- -----------------------------------------
-- 2. 品类销售排名
-- -----------------------------------------
SELECT 
    p.product_category_name,
    COUNT(DISTINCT o.order_id) AS order_count,
    SUM(i.price) AS total_revenue,
    AVG(i.price) AS avg_price,
    COUNT(DISTINCT i.seller_id) AS seller_count
FROM olist_orders o
JOIN olist_order_items i ON o.order_id = i.order_id
JOIN olist_products p ON i.product_id = p.product_id
WHERE o.order_status = 'delivered'
GROUP BY p.product_category_name
ORDER BY total_revenue DESC
LIMIT 20;


-- -----------------------------------------
-- 3. 用户复购率
-- -----------------------------------------
WITH user_orders AS (
    SELECT 
        c.customer_unique_id,
        COUNT(DISTINCT o.order_id) AS order_count
    FROM olist_orders o
    JOIN olist_customers c ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
)
SELECT 
    COUNT(*) AS total_users,
    SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) AS repeat_users,
    ROUND(
        CAST(SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100, 
        2
    ) AS repeat_rate_pct
FROM user_orders;


-- -----------------------------------------
-- 4. 各支付方式占比
-- -----------------------------------------
SELECT 
    pay.payment_type,
    COUNT(DISTINCT pay.order_id) AS order_count,
    SUM(pay.payment_value) AS total_payment_value,
    ROUND(
        CAST(COUNT(DISTINCT pay.order_id) AS FLOAT) / 
        (SELECT COUNT(DISTINCT order_id) FROM olist_order_payments) * 100,
        2
    ) AS share_pct,
    AVG(pay.payment_installments) AS avg_installments
FROM olist_order_payments pay
JOIN olist_orders o ON pay.order_id = o.order_id
WHERE o.order_status = 'delivered'
GROUP BY pay.payment_type
ORDER BY order_count DESC;


-- -----------------------------------------
-- 5. 月度复购率趋势（附加）
-- -----------------------------------------
WITH monthly_user_orders AS (
    SELECT 
        c.customer_unique_id,
        DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS year_month,
        COUNT(DISTINCT o.order_id) AS monthly_orders
    FROM olist_orders o
    JOIN olist_customers c ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id, DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m')
)
SELECT 
    year_month,
    COUNT(DISTINCT customer_unique_id) AS active_users,
    SUM(CASE WHEN monthly_orders > 1 THEN 1 ELSE 0 END) AS repeat_in_month,
    ROUND(
        CAST(SUM(CASE WHEN monthly_orders > 1 THEN 1 ELSE 0 END) AS FLOAT) / 
        COUNT(DISTINCT customer_unique_id) * 100, 
        2
    ) AS monthly_repeat_rate_pct
FROM monthly_user_orders
GROUP BY year_month
ORDER BY year_month;
-- =============================================================
-- 05_business_kpi.sql
-- 核心经营 KPI 计算（兼容 SQLite）
-- =============================================================

-- -----------------------------------------
-- 1. 月度 GMV、订单量、客单价
-- -----------------------------------------
SELECT 
    strftime('%Y-%m', o.order_purchase_timestamp) AS year_month,
    COUNT(DISTINCT o.order_id) AS order_count,
    SUM(i.price) AS gmv,
    SUM(i.freight_value) AS total_freight,
    SUM(i.price) / COUNT(DISTINCT o.order_id) AS aov  -- 客单价 (Average Order Value)
FROM olist_orders o
JOIN olist_order_items i ON o.order_id = i.order_id
WHERE o.order_status = 'delivered'
GROUP BY strftime('%Y-%m', o.order_purchase_timestamp)
ORDER BY year_month;


-- -----------------------------------------
-- 2. 品类销售排名
-- -----------------------------------------
SELECT 
    p.product_category_name,
    COUNT(DISTINCT o.order_id) AS order_count,
    SUM(i.price) AS total_revenue,
    AVG(i.price) AS avg_price,
    COUNT(DISTINCT i.seller_id) AS seller_count
FROM olist_orders o
JOIN olist_order_items i ON o.order_id = i.order_id
JOIN olist_products p ON i.product_id = p.product_id
WHERE o.order_status = 'delivered'
GROUP BY p.product_category_name
ORDER BY total_revenue DESC
LIMIT 20;


-- -----------------------------------------
-- 3. 用户复购率
-- -----------------------------------------
WITH user_orders AS (
    SELECT 
        c.customer_unique_id,
        COUNT(DISTINCT o.order_id) AS order_count
    FROM olist_orders o
    JOIN olist_customers c ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
)
SELECT 
    COUNT(*) AS total_users,
    SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) AS repeat_users,
    ROUND(
        CAST(SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100, 
        2
    ) AS repeat_rate_pct
FROM user_orders;


-- -----------------------------------------
-- 4. 各支付方式占比
-- -----------------------------------------
SELECT 
    pay.payment_type,
    COUNT(DISTINCT pay.order_id) AS order_count,
    SUM(pay.payment_value) AS total_payment_value,
    ROUND(
        CAST(COUNT(DISTINCT pay.order_id) AS FLOAT) / 
        (SELECT COUNT(DISTINCT order_id) FROM olist_order_payments) * 100,
        2
    ) AS share_pct,
    AVG(pay.payment_installments) AS avg_installments
FROM olist_order_payments pay
JOIN olist_orders o ON pay.order_id = o.order_id
WHERE o.order_status = 'delivered'
GROUP BY pay.payment_type
ORDER BY order_count DESC;


-- -----------------------------------------
-- 5. 月度复购率趋势（附加）
-- -----------------------------------------
WITH monthly_user_orders AS (
    SELECT 
        c.customer_unique_id,
        strftime('%Y-%m', o.order_purchase_timestamp) AS year_month,
        COUNT(DISTINCT o.order_id) AS monthly_orders
    FROM olist_orders o
    JOIN olist_customers c ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id, strftime('%Y-%m', o.order_purchase_timestamp)
)
SELECT 
    year_month,
    COUNT(DISTINCT customer_unique_id) AS active_users,
    SUM(CASE WHEN monthly_orders > 1 THEN 1 ELSE 0 END) AS repeat_in_month,
    ROUND(
        CAST(SUM(CASE WHEN monthly_orders > 1 THEN 1 ELSE 0 END) AS FLOAT) / 
        COUNT(DISTINCT customer_unique_id) * 100, 
        2
    ) AS monthly_repeat_rate_pct
FROM monthly_user_orders
GROUP BY year_month
ORDER BY year_month;
