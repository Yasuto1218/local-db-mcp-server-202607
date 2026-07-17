# MCPサーバーの起動
up-local:
	docker compose up --build

down-local:
	docker compose down

# PostgreSQLに直接テーブルを作成する
init-db:
	docker compose up -d postgres
	docker compose exec -T postgres sh -lc 'until pg_isready -U postgres -d app >/dev/null 2>&1; do :; done; psql -U postgres -d app -f /docker-entrypoint-initdb.d/01-schema.sql'

# Olist CSVをDBに取り込む
import-olist:
	$(MAKE) init-db
	uv run python scripts/import_olist.py --csv-dir "$${CSV_DIR:-data/olist}" --service "$${PG_SERVICE:-postgres}" --db-user "$${PGUSER:-postgres}" --db-name "$${PGDATABASE:-app}"

import-olist-reset:
	$(MAKE) init-db
	uv run python scripts/import_olist.py --truncate --csv-dir "$${CSV_DIR:-data/olist}" --service "$${PG_SERVICE:-postgres}" --db-user "$${PGUSER:-postgres}" --db-name "$${PGDATABASE:-app}"

# 依存関係の脆弱性を監査する
audit-deps:
	uv export --format requirements-txt -o /tmp/local-db-requirements.txt
	uvx pip-audit -r /tmp/local-db-requirements.txt