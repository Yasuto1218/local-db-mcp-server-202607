# local-db-mcp-server-202607

Local DB MCP Server

## データソース

Olist のデータセットを利用します。

- [Olist Brazilian E-Commerce (Kaggle)](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce/data)

CSV を使う場合は、取得したファイルを `data/olist/` 配下に配置してください。

## システム起動手順

1. PostgreSQL を起動してスキーマを適用します。

```bash
make init-db
```

2. （任意）Olist CSV を取り込みます。

```bash
make import-olist
```

3. MCP サーバーを起動します。

```bash
docker compose up --build
```

MCP サーバーは `http://localhost:8000/mcp`、PostgreSQL は `localhost:55432` で公開されます。

MCP のトランスポートは `MCP_TRANSPORT` で切り替えできます。

- `stdio`（既定）: MCP クライアントからコマンド起動する場合に推奨
- `streamable-http` / `sse`: HTTP公開して接続する場合

DB 接続先 (`DATABASE_URL`) は実行環境に合わせてください。

- ローカル実行（`uv run python main.py`）: `postgresql://postgres:postgres@localhost:55432/app`
- Docker の `mcp` サービス内実行: `postgresql://postgres:postgres@postgres:5432/app`

HTTPで使う例:

```bash
MCP_TRANSPORT=streamable-http MCP_PORT=8001 uv run python main.py
```

接続エラー対処:

- `role "postgres" does not exist`: 想定外のPostgreSQLに接続しています。`make init-db` を実行するか、`DATABASE_URL` の接続先を見直してください。
- `failed to resolve host 'postgres'`: ローカル実行時にDocker内向けホスト名を使っています。ローカル実行では `localhost` を指定してください。

`db/schema.sql` に Olist の主要テーブル定義を置いています。

テーブルとスキーマの説明は [docs/schema.md](docs/schema.md) にまとめています。

MCP サーバー向け instructions 文は [prompts/mcp_instructions.md](prompts/mcp_instructions.md) で管理しています。

## テーブル構築

MCP を通さずに直接 PostgreSQL へ流す場合は、次で作成できます。

```bash
make init-db
```

Olist の CSV を読み込む場合は、CSV を `data/olist/` に置いたうえで次を実行します。

```bash
make import-olist
```

`make import-olist` は非破壊です。既にデータがあるテーブルはスキップされます。

全テーブルを再投入したい場合のみ、次を使ってください。

```bash
make import-olist-reset
```

必要なら `CSV_DIR=/path/to/csv` で読み込み元を変えられます。コンテナ名や DB 名を変えている場合は `PG_SERVICE`、`PGUSER`、`PGDATABASE` を指定してください。

テーブル定義は [db/schema.sql](/Users/terasawayasuto/Portfolio/local-db-mcp-server-202607/db/schema.sql) に置いてあります。

## セキュリティ監査

依存関係の既知脆弱性は次で監査できます。

```bash
make audit-deps
```

脆弱性が検出された場合は、該当パッケージを更新して `uv lock` を再生成し、再度 `make audit-deps` を実行してください。

## ER 図

```mermaid
erDiagram
    CUSTOMERS ||--o{ ORDERS : places
    ORDERS ||--o{ ORDER_ITEMS : contains
    ORDERS ||--o{ ORDER_PAYMENTS : has
    ORDERS ||--o{ ORDER_REVIEWS : receives
    PRODUCTS ||--o{ ORDER_ITEMS : referenced_by
    SELLERS ||--o{ ORDER_ITEMS : fulfills
    PRODUCT_CATEGORY_NAME_TRANSLATION ||--o{ PRODUCTS : classifies

    CUSTOMERS {
        text customer_id PK
        text customer_unique_id
        int customer_zip_code_prefix
        text customer_city
        text customer_state
    }

    ORDERS {
        text order_id PK
        text customer_id FK
        text order_status
        timestamp order_purchase_timestamp
        timestamp order_approved_at
        timestamp order_delivered_carrier_date
        timestamp order_delivered_customer_date
        timestamp order_estimated_delivery_date
    }

    ORDER_ITEMS {
        text order_id PK, FK
        int order_item_id PK
        text product_id FK
        text seller_id FK
        timestamp shipping_limit_date
        numeric price
        numeric freight_value
    }

    ORDER_PAYMENTS {
        text order_id PK, FK
        int payment_sequential PK
        text payment_type
        int payment_installments
        numeric payment_value
    }

    ORDER_REVIEWS {
        text review_id PK
        text order_id FK
        int review_score
        text review_comment_title
        text review_comment_message
        timestamp review_creation_date
        timestamp review_answer_timestamp
    }

    PRODUCTS {
        text product_id PK
        text product_category_name FK
        int product_name_lenght
        int product_description_lenght
        int product_photos_qty
        int product_weight_g
        int product_length_cm
        int product_height_cm
        int product_width_cm
    }

    SELLERS {
        text seller_id PK
        int seller_zip_code_prefix
        text seller_city
        text seller_state
    }

    PRODUCT_CATEGORY_NAME_TRANSLATION {
        text product_category_name PK
        text product_category_name_english
    }
```

## システム構成図

```mermaid
flowchart LR
    chatgpt(["ChatGPT"])

    subgraph docker["🐳 Docker"]
        direction LR
        mcp{{"⚙️ MCP Server"}}
        postgres[("PostgreSQL")]
    end

    chatgpt --> mcp
    mcp --> postgres
```
