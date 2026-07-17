# Olist Schema Guide

このファイルは、PostgreSQL 上の Olist スキーマの説明です。

## テーブル一覧

### customers

- 役割: 購入ユーザー情報
- 主キー: customer_id
- 主要カラム:
  - customer_unique_id: 同一顧客の再購入を識別するためのID
  - customer_zip_code_prefix, customer_city, customer_state: 顧客所在地

### orders

- 役割: 注文ヘッダ
- 主キー: order_id
- 外部キー: customer_id -> customers.customer_id
- 主要カラム:
  - order_status
  - order_purchase_timestamp
  - order_estimated_delivery_date

### order_items

- 役割: 注文明細（1注文に複数明細）
- 主キー: (order_id, order_item_id)
- 外部キー:
  - order_id -> orders.order_id
  - product_id -> products.product_id
  - seller_id -> sellers.seller_id
- 主要カラム:
  - price
  - freight_value

### order_payments

- 役割: 注文の支払い情報
- 主キー: (order_id, payment_sequential)
- 外部キー: order_id -> orders.order_id
- 主要カラム:
  - payment_type
  - payment_installments
  - payment_value

### order_reviews

- 役割: 注文レビュー
- 主キー: (review_id, order_id)
- 外部キー: order_id -> orders.order_id
- 主要カラム:
  - review_score
  - review_comment_title
  - review_comment_message

### products

- 役割: 商品マスタ
- 主キー: product_id
- 外部キー: product_category_name -> product_category_name_translation.product_category_name
- 主要カラム:
  - product_name_lenght
  - product_description_lenght
  - product_weight_g
  - product_length_cm / product_height_cm / product_width_cm

### product_category_name_translation

- 役割: 商品カテゴリの翻訳テーブル
- 主キー: product_category_name
- 主要カラム:
  - product_category_name_english

### sellers

- 役割: 出店者情報
- 主キー: seller_id
- 主要カラム:
  - seller_zip_code_prefix
  - seller_city
  - seller_state

### geolocation

- 役割: 郵便番号プレフィックスの緯度経度マッピング
- 主キー: geolocation_id
- インデックス: idx_geolocation_zip_code_prefix
- 主要カラム:
  - zip_code_prefix
  - geolocation_lat
  - geolocation_lng

## 代表的なリレーション

- customers 1 --- n orders
- orders 1 --- n order_items
- orders 1 --- n order_payments
- orders 1 --- n order_reviews
- products 1 --- n order_items
- sellers 1 --- n order_items
- product_category_name_translation 1 --- n products
