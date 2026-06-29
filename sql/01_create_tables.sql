-- =============================================================
-- 01_create_tables.sql
-- Olist 电商数据集建表 DDL（MySQL 8.0）
-- 
-- 用途：创建 9 张核心数据表及索引
-- 字符集：utf8mb4，支持中文及 emoji
-- 参考：scripts/init_mysql_db.py 中的表结构与索引定义
-- =============================================================

CREATE DATABASE IF NOT EXISTS olist_ecommerce
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE olist_ecommerce;

-- -----------------------------------------
-- 1. 客户表
-- -----------------------------------------
DROP TABLE IF EXISTS olist_customers;
CREATE TABLE olist_customers (
    customer_id              VARCHAR(32)  NOT NULL COMMENT '订单级客户ID',
    customer_unique_id       VARCHAR(32)  NOT NULL COMMENT '用户唯一标识',
    customer_zip_code_prefix INT          DEFAULT NULL COMMENT '邮编前缀',
    customer_city            VARCHAR(100) DEFAULT NULL COMMENT '城市',
    customer_state           VARCHAR(10)  DEFAULT NULL COMMENT '州/省',
    PRIMARY KEY (customer_id),
    INDEX idx_customers_unique (customer_unique_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='客户信息表';

-- -----------------------------------------
-- 2. 订单表
-- -----------------------------------------
DROP TABLE IF EXISTS olist_orders;
CREATE TABLE olist_orders (
    order_id                       VARCHAR(32)  NOT NULL COMMENT '订单ID',
    customer_id                    VARCHAR(32)  NOT NULL COMMENT '客户ID',
    order_status                   VARCHAR(20)  DEFAULT NULL COMMENT '订单状态',
    order_purchase_timestamp       DATETIME     DEFAULT NULL COMMENT '下单时间',
    order_approved_at              DATETIME     DEFAULT NULL COMMENT '支付确认时间',
    order_delivered_carrier_date   DATETIME     DEFAULT NULL COMMENT '发货时间',
    order_delivered_customer_date  DATETIME     DEFAULT NULL COMMENT '送达时间',
    order_estimated_delivery_date  DATETIME     DEFAULT NULL COMMENT '预计送达时间',
    PRIMARY KEY (order_id),
    INDEX idx_orders_customer (customer_id),
    INDEX idx_orders_status (order_status),
    INDEX idx_orders_purchase_ts (order_purchase_timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='订单主表';

-- -----------------------------------------
-- 3. 订单商品明细表
-- -----------------------------------------
DROP TABLE IF EXISTS olist_order_items;
CREATE TABLE olist_order_items (
    order_id            VARCHAR(32)    NOT NULL COMMENT '订单ID',
    order_item_id       INT            NOT NULL COMMENT '订单内商品序号',
    product_id          VARCHAR(32)    NOT NULL COMMENT '商品ID',
    seller_id           VARCHAR(32)    NOT NULL COMMENT '卖家ID',
    shipping_limit_date DATETIME       DEFAULT NULL COMMENT '发货截止时间',
    price               DECIMAL(10,2)  NOT NULL DEFAULT 0 COMMENT '商品价格',
    freight_value       DECIMAL(10,2)  NOT NULL DEFAULT 0 COMMENT '运费',
    PRIMARY KEY (order_id, order_item_id),
    INDEX idx_items_order (order_id),
    INDEX idx_items_product (product_id),
    INDEX idx_items_seller (seller_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='订单商品明细表';

-- -----------------------------------------
-- 4. 订单支付表
-- -----------------------------------------
DROP TABLE IF EXISTS olist_order_payments;
CREATE TABLE olist_order_payments (
    order_id             VARCHAR(32)   NOT NULL COMMENT '订单ID',
    payment_sequential   INT           NOT NULL COMMENT '支付序号',
    payment_type         VARCHAR(30)   DEFAULT NULL COMMENT '支付方式',
    payment_installments INT           DEFAULT 0 COMMENT '分期期数',
    payment_value        DECIMAL(10,2) DEFAULT 0 COMMENT '支付金额',
    PRIMARY KEY (order_id, payment_sequential),
    INDEX idx_payments_order (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='订单支付信息表';

-- -----------------------------------------
-- 5. 订单评价表
-- -----------------------------------------
DROP TABLE IF EXISTS olist_order_reviews;
CREATE TABLE olist_order_reviews (
    review_id                VARCHAR(32)  NOT NULL COMMENT '评价ID',
    order_id                 VARCHAR(32)  NOT NULL COMMENT '订单ID',
    review_score             TINYINT      DEFAULT NULL COMMENT '评分(1-5)',
    review_comment_title     VARCHAR(200) DEFAULT NULL COMMENT '评论标题',
    review_comment_message   TEXT         DEFAULT NULL COMMENT '评论内容',
    review_creation_date     DATETIME     DEFAULT NULL COMMENT '评论创建时间',
    review_answer_timestamp  DATETIME     DEFAULT NULL COMMENT '商家回复时间',
    PRIMARY KEY (review_id),
    INDEX idx_reviews_order (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='订单评价表';

-- -----------------------------------------
-- 6. 商品表
-- -----------------------------------------
DROP TABLE IF EXISTS olist_products;
CREATE TABLE olist_products (
    product_id                 VARCHAR(32)   NOT NULL COMMENT '商品ID',
    product_category_name      VARCHAR(100)  DEFAULT NULL COMMENT '品类名称',
    product_name_lenght        INT           DEFAULT NULL COMMENT '商品名长度',
    product_description_lenght INT           DEFAULT NULL COMMENT '描述长度',
    product_photos_qty         INT           DEFAULT NULL COMMENT '图片数量',
    product_weight_g           INT           DEFAULT NULL COMMENT '重量(克)',
    product_length_cm          DECIMAL(8,2)  DEFAULT NULL COMMENT '长度(cm)',
    product_height_cm          DECIMAL(8,2)  DEFAULT NULL COMMENT '高度(cm)',
    product_width_cm           DECIMAL(8,2)  DEFAULT NULL COMMENT '宽度(cm)',
    PRIMARY KEY (product_id),
    INDEX idx_products_category (product_category_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='商品信息表';

-- -----------------------------------------
-- 7. 卖家表
-- -----------------------------------------
DROP TABLE IF EXISTS olist_sellers;
CREATE TABLE olist_sellers (
    seller_id              VARCHAR(32)  NOT NULL COMMENT '卖家ID',
    seller_zip_code_prefix INT          DEFAULT NULL COMMENT '邮编前缀',
    seller_city            VARCHAR(100) DEFAULT NULL COMMENT '城市',
    seller_state           VARCHAR(10)  DEFAULT NULL COMMENT '州/省',
    seller_name            VARCHAR(200) DEFAULT NULL COMMENT '店铺名称',
    PRIMARY KEY (seller_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='卖家信息表';

-- -----------------------------------------
-- 8. 地理位置表
-- -----------------------------------------
DROP TABLE IF EXISTS olist_geolocation;
CREATE TABLE olist_geolocation (
    geolocation_zip_code_prefix INT            NOT NULL COMMENT '邮编前缀',
    geolocation_lat             DECIMAL(18,14) DEFAULT NULL COMMENT '纬度',
    geolocation_lng             DECIMAL(18,14) DEFAULT NULL COMMENT '经度',
    geolocation_city            VARCHAR(100)   DEFAULT NULL COMMENT '城市',
    geolocation_state           VARCHAR(10)    DEFAULT NULL COMMENT '州/省',
    INDEX idx_geo_zip (geolocation_zip_code_prefix)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='地理位置表（邮编级别，含重复）';

-- -----------------------------------------
-- 9. 品类名称翻译表
-- -----------------------------------------
DROP TABLE IF EXISTS category_translation;
CREATE TABLE category_translation (
    product_category_name         VARCHAR(100) NOT NULL COMMENT '品类名称（原始语言）',
    product_category_name_english VARCHAR(100) DEFAULT NULL COMMENT '品类名称（英文）',
    PRIMARY KEY (product_category_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='品类名称中英对照表';
