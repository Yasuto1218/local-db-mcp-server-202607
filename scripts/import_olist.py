from __future__ import annotations

import argparse
import csv
from pathlib import Path
import subprocess

TABLE_IMPORTS = [
    (
        "geolocation",
        "olist_geolocation_dataset.csv",
        [
            "zip_code_prefix",
            "geolocation_lat",
            "geolocation_lng",
            "geolocation_city",
            "geolocation_state",
        ],
    ),
    (
        "product_category_name_translation",
        "product_category_name_translation.csv",
        ["product_category_name", "product_category_name_english"],
    ),
    (
        "customers",
        "olist_customers_dataset.csv",
        [
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ],
    ),
    (
        "sellers",
        "olist_sellers_dataset.csv",
        ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
    ),
    (
        "products",
        "olist_products_dataset.csv",
        [
            "product_id",
            "product_category_name",
            "product_name_lenght",
            "product_description_lenght",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ],
    ),
    (
        "orders",
        "olist_orders_dataset.csv",
        [
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    ),
    (
        "order_items",
        "olist_order_items_dataset.csv",
        [
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "shipping_limit_date",
            "price",
            "freight_value",
        ],
    ),
    (
        "order_payments",
        "olist_order_payments_dataset.csv",
        [
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
        ],
    ),
    (
        "order_reviews",
        "olist_order_reviews_dataset.csv",
        [
            "review_id",
            "order_id",
            "review_score",
            "review_comment_title",
            "review_comment_message",
            "review_creation_date",
            "review_answer_timestamp",
        ],
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Olist CSV files into PostgreSQL.")
    parser.add_argument(
        "--csv-dir",
        default="data/olist",
        help="Directory containing the Olist CSV files.",
    )
    parser.add_argument(
        "--service",
        default="postgres",
        help="Docker Compose service name for PostgreSQL.",
    )
    parser.add_argument(
        "--db-user",
        default="postgres",
        help="PostgreSQL user inside the container.",
    )
    parser.add_argument(
        "--db-name",
        default="app",
        help="PostgreSQL database name inside the container.",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Truncate Olist tables before import. Use only when you want to reset data.",
    )
    return parser.parse_args()


def run_psql(
    args: argparse.Namespace,
    sql: str,
    stdin_file: Path | None = None,
    capture_output: bool = False,
) -> str | None:
    command = [
        "docker",
        "compose",
        "exec",
        "-T",
        args.service,
        "psql",
        "-U",
        args.db_user,
        "-d",
        args.db_name,
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        sql,
    ]

    if stdin_file is None:
        if capture_output:
            command.extend(["-t", "-A"])
        result = subprocess.run(command, check=True, capture_output=capture_output, text=True)
        return result.stdout if capture_output else None

    with stdin_file.open("rb") as source:
        subprocess.run(command, stdin=source, check=True)
    return None


def truncate_tables(args: argparse.Namespace) -> None:
    run_psql(
        args,
        "TRUNCATE TABLE order_reviews, order_payments, order_items, orders, products, sellers, customers, product_category_name_translation, geolocation RESTART IDENTITY CASCADE",
    )


def table_has_rows(args: argparse.Namespace, table_name: str) -> bool:
    output = run_psql(
        args,
        f"SELECT EXISTS (SELECT 1 FROM {table_name} LIMIT 1)",
        capture_output=True,
    )
    return (output or "").strip() == "t"


def import_csv(args: argparse.Namespace, csv_path: Path, table_name: str, columns: list[str]) -> None:
    copy_sql = f"COPY {table_name} ({', '.join(columns)}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
    run_psql(args, copy_sql, stdin_file=csv_path)


def ensure_category_translations(args: argparse.Namespace, products_csv: Path) -> None:
    existing_raw = run_psql(
        args,
        "SELECT product_category_name FROM product_category_name_translation",
        capture_output=True,
    )
    existing = {
        line.strip()
        for line in (existing_raw or "").splitlines()
        if line.strip() and not line.startswith("product_category_name") and not line.startswith("(")
    }

    categories_in_products: set[str] = set()
    with products_csv.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        for row in reader:
            category = (row.get("product_category_name") or "").strip()
            if category:
                categories_in_products.add(category)

    missing = sorted(categories_in_products - existing)
    if not missing:
        return

    values_parts: list[str] = []
    for category in missing:
        escaped = category.replace("'", "''")
        values_parts.append(f"('{escaped}', '{escaped}')")

    values = ", ".join(values_parts)
    run_psql(
        args,
        "INSERT INTO product_category_name_translation (product_category_name, product_category_name_english) "
        f"VALUES {values} ON CONFLICT (product_category_name) DO NOTHING",
    )


def main() -> None:
    args = parse_args()
    csv_dir = Path(args.csv_dir)

    if not csv_dir.exists():
        raise FileNotFoundError(f"CSV directory not found: {csv_dir}")

    if args.truncate:
        truncate_tables(args)

    for table_name, file_name, columns in TABLE_IMPORTS:
        csv_path = csv_dir / file_name
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing CSV file: {csv_path}")

        if not args.truncate and table_has_rows(args, table_name):
            print(f"skip {table_name}: table already has data")
            continue

        if table_name == "products":
            ensure_category_translations(args, csv_path)

        import_csv(args, csv_path, table_name, columns)


if __name__ == "__main__":
    main()