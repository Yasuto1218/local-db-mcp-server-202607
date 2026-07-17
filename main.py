import os
from pathlib import Path
from contextlib import contextmanager

import psycopg
from psycopg import OperationalError
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row

from mcp.server.fastmcp import FastMCP

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:55432/app",
)

MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()
if MCP_TRANSPORT not in {"stdio", "sse", "streamable-http"}:
    raise ValueError("MCP_TRANSPORT must be one of: stdio, sse, streamable-http")


def load_mcp_instructions() -> str:
    instructions_path = Path(__file__).parent / "prompts" / "mcp_instructions.md"
    return instructions_path.read_text(encoding="utf-8").strip()


def _safe_conn_summary(dsn: str) -> str:
    info = conninfo_to_dict(dsn)
    host = info.get("host", "localhost")
    port = info.get("port", "5432")
    dbname = info.get("dbname", "")
    user = info.get("user", "")
    return f"host={host} port={port} db={dbname} user={user}"


@contextmanager
def db_connection():
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            yield conn
    except OperationalError as exc:
        summary = _safe_conn_summary(DATABASE_URL)
        raise RuntimeError(
            "データベース接続に失敗しました。"
            f"接続先: {summary}. "
            "`role \"postgres\" does not exist` が出る場合は、"
            "想定外のPostgreSQLに接続しています。"
            "`make init-db` でプロジェクトDBを起動・初期化するか、"
            "正しい `DATABASE_URL` を設定してください。"
        ) from exc

mcp = FastMCP(
    "local-postgres-mcp",
    instructions=load_mcp_instructions(),
    host=os.getenv("MCP_HOST", "0.0.0.0"),
    port=int(os.getenv("MCP_PORT", "8000")),
)


@mcp.tool()
def list_recent_orders(limit: int = 20) -> list[dict]:
    """Olistの注文一覧を新しい順で返す。既定は20件。"""
    if limit <= 0:
        raise ValueError("limitは1以上を指定してください")

    with db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    o.order_id,
                    o.order_status,
                    o.order_purchase_timestamp,
                    c.customer_unique_id
                FROM orders o
                JOIN customers c ON c.customer_id = o.customer_id
                ORDER BY o.order_purchase_timestamp DESC NULLS LAST
                LIMIT %s
                """,
                (limit,),
            )
            return cur.fetchall()


@mcp.tool()
def query_sql(sql: str) -> list[dict]:
    """Olistスキーマに対してSELECT文を実行し、結果を返す。"""
    if not sql.strip().lower().startswith("select"):
        raise ValueError("SELECT文のみ実行できます")

    with db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql)
            return cur.fetchall()


if __name__ == "__main__":
    mcp.run(transport=MCP_TRANSPORT)