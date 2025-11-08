import os
import time
import psycopg
import json
from datetime import datetime, timezone
from robot_api import shops as s  # deve contenere shops = {...}
from robot_api import robots as r
from robot_api import maps as m

def _parse_ts(s: str | None):
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")

def _get_fallback_shop_id(conn):
    with conn.cursor() as cur:
        # prima provo dai log di status
        cur.execute("SELECT DISTINCT shop_id FROM robot_status_log WHERE shop_id IS NOT NULL LIMIT 1;")
        row = cur.fetchone()
        if row and row[0]:
            return row[0]
        # altrimenti prendo uno shop qualsiasi
        cur.execute("SELECT shop_id FROM shop LIMIT 1;")
        row = cur.fetchone()
        return row[0] if row else None

PG_DSN = "host=localhost port=5432 dbname=mydb user=admin password=admin"

conn = psycopg.connect(PG_DSN)

def add_company_shop_data(conn, shops_payload: dict):
    items = shops_payload["data"]["list"]

    companies = {}
    for item in items:
        companies[item["company_id"]] = item["company_name"]

    with conn.cursor() as cur:
        for cid, cname in companies.items():
            cur.execute(
                """
                INSERT INTO company (company_id, company_name)
                VALUES (%s, %s)
                ON CONFLICT (company_id) DO UPDATE
                SET company_name = EXCLUDED.company_name;
                """,
                (cid, cname),
            )

        for item in items:
            cur.execute(
                """
                INSERT INTO shop (shop_id, company_id, shop_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (shop_id) DO UPDATE
                SET company_id = EXCLUDED.company_id,
                    shop_name  = EXCLUDED.shop_name;
                """,
                (item["shop_id"], item["company_id"], item["shop_name"]),
            )
    conn.commit()
    print(f"[INFO] inserite {len(companies)} company e {len(items)} shop")

def add_robot_data(conn, robots_payload: dict):
    # struttura: {"data": {"count": ..., "list": [ {...}, ... ]}}
    items = robots_payload["data"]["list"]

    # assicurati che la tabella esista
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS robots (
                sn           TEXT PRIMARY KEY,
                shop_id      BIGINT NOT NULL REFERENCES shop(shop_id),
                mac          TEXT,
                product_code TEXT,
                shop_name    TEXT
            );
            """
        )
    conn.commit()

    inserted = 0
    with conn.cursor() as cur:
        for rb in items:
            sn = rb["sn"]
            shop_id = int(rb["shop_id"])  # nel JSON è stringa
            shop_name = rb.get("shop_name")
            mac = rb.get("mac")
            product_code = rb.get("product_code")

            cur.execute(
                """
                INSERT INTO robots (sn, shop_id, mac, product_code, shop_name)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (sn) DO UPDATE
                SET shop_id = EXCLUDED.shop_id,
                    mac = EXCLUDED.mac,
                    product_code = EXCLUDED.product_code,
                    shop_name = EXCLUDED.shop_name;
                """,
                (sn, shop_id, mac, product_code, shop_name),
            )
            inserted += 1

    conn.commit()
    print(f"[INFO] robot inseriti/aggiornati: {inserted}")
from datetime import datetime, timezone


def add_robot_status_log(conn, status_payload: dict):
    items = status_payload["data"]["list"]

    with conn.cursor() as cur:
        cur.execute("SELECT sn, shop_id FROM robots;")
        sn_to_shop = {sn: shop_id for sn, shop_id in cur.fetchall()}

    inserted = 0
    skipped = 0
    with conn.cursor() as cur:
        for row in items:
            sn = row["sn"]
            shop_id = sn_to_shop.get(sn)
            if shop_id is None:
                skipped += 1
                continue

            cur.execute(
                """
                INSERT INTO robot_status_log (
                    id, sn, shop_id,
                    upload_time, task_time,
                    soft_version, hard_version,
                    ip, check_result, is_success
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE
                SET sn = EXCLUDED.sn,
                    shop_id = EXCLUDED.shop_id,
                    upload_time = EXCLUDED.upload_time,
                    task_time = EXCLUDED.task_time,
                    soft_version = EXCLUDED.soft_version,
                    hard_version = EXCLUDED.hard_version,
                    ip = EXCLUDED.ip,
                    check_result = EXCLUDED.check_result,
                    is_success = EXCLUDED.is_success;
                """,
                (
                    row["id"],
                    sn,
                    shop_id,
                    _parse_ts(row.get("upload_time")),
                    _parse_ts(row.get("task_time")),
                    row.get("soft_version"),
                    row.get("hard_version"),
                    row.get("ip"),
                    json.dumps(row.get("check_result") or []),
                    row.get("is_success"),
                ),
            )
            inserted += 1

    conn.commit()
    print(f"[INFO] robot_status_log inseriti/aggiornati: {inserted} (saltati: {skipped})")


def add_robot_error_log(conn, errors_payload: dict):
    items = errors_payload["data"]["list"]

    # mappa corrente sn -> shop_id
    with conn.cursor() as cur:
        cur.execute("SELECT sn, shop_id FROM robots;")
        sn_to_shop = {sn: shop_id for sn, shop_id in cur.fetchall()}

    fallback_shop_id = _get_fallback_shop_id(conn)

    inserted = 0
    autoinserted_robots = 0

    with conn.cursor() as cur:
        for row in items:
            sn = row["sn"]
            shop_id = sn_to_shop.get(sn)

            if shop_id is None:
                # creo il robot minimo
                cur.execute(
                    """
                    INSERT INTO robots (sn, shop_id, mac, product_code, shop_name)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (sn) DO NOTHING;
                    """,
                    (
                        sn,
                        fallback_shop_id,
                        row.get("mac"),
                        row.get("product_code"),
                        None,
                    ),
                )
                sn_to_shop[sn] = fallback_shop_id
                shop_id = fallback_shop_id
                autoinserted_robots += 1

            cur.execute(
                """
                INSERT INTO robot_error_log (
                    id, sn, shop_id,
                    upload_time, task_time,
                    soft_version, hard_version,
                    error_level, error_type, error_source_id,
                    mac, product_code
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE
                SET sn = EXCLUDED.sn,
                    shop_id = EXCLUDED.shop_id,
                    upload_time = EXCLUDED.upload_time,
                    task_time = EXCLUDED.task_time,
                    soft_version = EXCLUDED.soft_version,
                    hard_version = EXCLUDED.hard_version,
                    error_level = EXCLUDED.error_level,
                    error_type = EXCLUDED.error_type,
                    error_source_id = EXCLUDED.error_source_id,
                    mac = EXCLUDED.mac,
                    product_code = EXCLUDED.product_code;
                """,
                (
                    row["id"],
                    sn,
                    shop_id,
                    _parse_ts(row.get("upload_time")),
                    _parse_ts(row.get("task_time")),
                    row.get("soft_version"),
                    row.get("hard_version"),
                    row.get("error_level"),
                    row.get("error_type"),
                    row.get("error_id"),
                    row.get("mac"),
                    row.get("product_code"),
                ),
            )
            inserted += 1

    conn.commit()
    print(f"[INFO] robot_error_log inseriti/aggiornati: {inserted} (robot auto-inseriti: {autoinserted_robots})")

def add_robot_charge_log(conn, charges_payload: dict):
    items = charges_payload["data"]["list"]

    with conn.cursor() as cur:
        cur.execute("SELECT sn, shop_id FROM robots;")
        sn_to_shop = {sn: shop_id for sn, shop_id in cur.fetchall()}

    fallback_shop_id = _get_fallback_shop_id(conn)

    inserted = 0
    autoinserted_robots = 0

    with conn.cursor() as cur:
        for row in items:
            sn = row["sn"]
            shop_id = sn_to_shop.get(sn)

            if shop_id is None:
                # creo robot minimale
                cur.execute(
                    """
                    INSERT INTO robots (sn, shop_id, mac, product_code, shop_name)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (sn) DO NOTHING;
                    """,
                    (
                        sn,
                        fallback_shop_id,
                        row.get("mac"),
                        row.get("product_code"),
                        None,
                    ),
                )
                sn_to_shop[sn] = fallback_shop_id
                shop_id = fallback_shop_id
                autoinserted_robots += 1

            cur.execute(
                """
                INSERT INTO robot_charge_log (
                    id, sn, shop_id,
                    upload_time, task_time,
                    soft_version, hard_version,
                    mac, product_code,
                    charge_power_pct, charge_duration_s,
                    min_power_pct, max_power_pct
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE
                SET sn = EXCLUDED.sn,
                    shop_id = EXCLUDED.shop_id,
                    upload_time = EXCLUDED.upload_time,
                    task_time = EXCLUDED.task_time,
                    soft_version = EXCLUDED.soft_version,
                    hard_version = EXCLUDED.hard_version,
                    mac = EXCLUDED.mac,
                    product_code = EXCLUDED.product_code,
                    charge_power_pct = EXCLUDED.charge_power_pct,
                    charge_duration_s = EXCLUDED.charge_duration_s,
                    min_power_pct = EXCLUDED.min_power_pct,
                    max_power_pct = EXCLUDED.max_power_pct;
                """,
                (
                    row["id"],
                    sn,
                    shop_id,
                    _parse_ts(row.get("upload_time")),
                    _parse_ts(row.get("task_time")),
                    row.get("soft_version"),
                    row.get("hard_version"),
                    row.get("mac"),
                    row.get("product_code"),
                    row.get("charge_power_percent"),
                    row.get("charge_duration"),
                    row.get("min_power_percent"),
                    row.get("max_power_percent"),
                ),
            )
            inserted += 1

    conn.commit()
    print(f"[INFO] robot_charge_log inseriti/aggiornati: {inserted} (robot auto-inseriti: {autoinserted_robots})")


def main():
    add_company_shop_data(conn, s.shops_example)
    add_robot_data(conn, r.robots_example)
    add_robot_status_log(conn, s.shops_robotstatus_example)
    add_robot_error_log(conn, s.shops_roboterrors_example)
    add_robot_charge_log(conn, s.shops_robotcharges_example)
    conn.close()

if __name__ == "__main__":
    main()
