import os
import time
import requests
import psycopg
from datetime import datetime, timezone, date
from robot_api import robots as r  # qui hai tutti gli example

# API / DB config
PG_DSN = "host=localhost port=5432 dbname=mydb user=admin password=admin"

# campi timestamp stile "YYYY-MM-DD HH:MM:SS"
TS_FIELDS = ["arrival_time", "begin_time", "task_time"]


# ----------------------------------------------------------------------
# util comuni
# ----------------------------------------------------------------------
def _to_ts(value: str):
    if not value:
        return None
    return datetime.fromisoformat(value)


def _to_date(value: str):
    if not value:
        return None
    # es. "2023-08-31"
    return date.fromisoformat(value)


def _to_float(v):
    if v in ("", None):
        return None
    return float(v)


def _to_int(v):
    if v in ("", None):
        return None
    return int(v)


# ----------------------------------------------------------------------
# 1. cleaning task (tuo codice originale)
# ----------------------------------------------------------------------
def get_cleaning_task(conn):
    data = r.robots_cleaning_tasks_example
    tasks = data["data"]["item"]
    print(f"Recuperati {len(tasks)} task di pulizia")

    with conn.cursor() as cur:
        for task in tasks:
            # cleaning_task
            cur.execute(
                """
                INSERT INTO cleaning_task (
                    task_id, version, name, description, status,
                    is_single_task, task_count, task_mode, pre_clean_time,
                    is_area_connect, is_hand_sort, shop_id, robot_sn
                )
                VALUES (%s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s)
                ON CONFLICT (task_id) DO UPDATE SET
                    version = EXCLUDED.version,
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    status = EXCLUDED.status,
                    is_single_task = EXCLUDED.is_single_task,
                    task_count = EXCLUDED.task_count,
                    task_mode = EXCLUDED.task_mode,
                    pre_clean_time = EXCLUDED.pre_clean_time,
                    is_area_connect = EXCLUDED.is_area_connect,
                    is_hand_sort = EXCLUDED.is_hand_sort;
                """,
                (
                    task["task_id"],
                    task["version"],
                    task["name"],
                    task.get("desc", ""),
                    task["status"],
                    task["is_single_task"],
                    task["task_count"],
                    task["task_mode"],
                    task["pre_clean_time"],
                    task["is_area_connect"],
                    task["is_hand_sort"],
                    task.get("shop_id"),
                    task.get("robot_sn", ""),
                ),
            )

            config = task["config"]
            cur.execute(
                """
                INSERT INTO task_config (
                    task_id, ai_adaptive_switch, left_brush, mode,
                    right_brush, right_vacuum_suction, type,
                    vacuum_speed, vacuum_suction, wash_speed,
                    wash_suction, wash_water
                )
                VALUES (%s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s)
                ON CONFLICT (task_id) DO UPDATE SET
                    ai_adaptive_switch = EXCLUDED.ai_adaptive_switch,
                    left_brush = EXCLUDED.left_brush,
                    mode = EXCLUDED.mode,
                    right_brush = EXCLUDED.right_brush,
                    right_vacuum_suction = EXCLUDED.right_vacuum_suction,
                    type = EXCLUDED.type,
                    vacuum_speed = EXCLUDED.vacuum_speed,
                    vacuum_suction = EXCLUDED.vacuum_suction,
                    wash_speed = EXCLUDED.wash_speed,
                    wash_suction = EXCLUDED.wash_suction,
                    wash_water = EXCLUDED.wash_water;
                """,
                (
                    task["task_id"],
                    config["ai_adaptive_switch"],
                    config["left_brush"],
                    config["mode"],
                    config["right_brush"],
                    config["right_vacuum_suction"],
                    config["type"],
                    config["vacuum_speed"],
                    config["vacuum_suction"],
                    config["wash_speed"],
                    config["wash_suction"],
                    config["wash_water"],
                ),
            )

            station = task.get("station_config")
            if station:
                cur.execute(
                    """
                    INSERT INTO station (
                        station_id, station_name, station_type,
                        station_function, map_name, task_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (station_id) DO UPDATE SET
                        station_name = EXCLUDED.station_name,
                        station_type = EXCLUDED.station_type,
                        station_function = EXCLUDED.station_function,
                        map_name = EXCLUDED.map_name,
                        task_id = EXCLUDED.task_id;
                    """,
                    (
                        station["id"],
                        station["station_name"],
                        station["station_type"],
                        station["station_funtion"],
                        station["map_name"],
                        task["task_id"],
                    ),
                )

            bp = task.get("back_point")
            if bp:
                cur.execute(
                    """
                    INSERT INTO back_point (
                        point_id, point_name, floor, map_name, task_id
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (point_id) DO UPDATE SET
                        point_name = EXCLUDED.point_name,
                        floor = EXCLUDED.floor,
                        map_name = EXCLUDED.map_name,
                        task_id = EXCLUDED.task_id;
                    """,
                    (
                        bp["point_id"],
                        bp["point_name"],
                        bp["floor"],
                        bp["map_name"],
                        task["task_id"],
                    ),
                )

            for floor_data in task.get("floor_list", []):
                map_info = floor_data["map"]

                cur.execute(
                    """
                    INSERT INTO map (map_name, floor, level, task_id)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (map_name, task_id) DO UPDATE SET
                        floor = EXCLUDED.floor,
                        level = EXCLUDED.level;
                    """,
                    (
                        map_info["name"],
                        map_info["floor"],
                        map_info["lv"],
                        task["task_id"],
                    ),
                )

                for area in floor_data.get("area_array", []):
                    area_size = area.get("area", 0)
                    cur.execute(
                        """
                        INSERT INTO cleaning_area (
                            area_id, area_name, area_size, clean_count,
                            area_type, map_name, task_id
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (area_id) DO UPDATE SET
                            area_name = EXCLUDED.area_name,
                            area_size = EXCLUDED.area_size,
                            clean_count = EXCLUDED.clean_count,
                            area_type = EXCLUDED.area_type,
                            map_name = EXCLUDED.map_name,
                            task_id = EXCLUDED.task_id;
                        """,
                        (
                            area["area_id"],
                            area["area_name"],
                            area_size,
                            area.get("clean_count", 0),
                            area.get("type", 0),
                            map_info["name"],
                            task["task_id"],
                        ),
                    )

            cleanagent = task["cleanagent_config"]
            cur.execute(
                """
                INSERT INTO cleanagent_config (task_id, is_open, scale)
                VALUES (%s, %s, %s)
                ON CONFLICT (task_id) DO UPDATE SET
                    is_open = EXCLUDED.is_open,
                    scale = EXCLUDED.scale;
                """,
                (
                    task["task_id"],
                    cleanagent["isopen"],
                    cleanagent["scale"],
                ),
            )

    conn.commit()
    print(f"Inseriti/aggiornati {len(tasks)} task nel database")


# ----------------------------------------------------------------------
# 2. industrial lifting (già fatto)
# ----------------------------------------------------------------------
def insert_robot_industrial_lifting_tasks(conn, data):
    query = """
        INSERT INTO robot_industrial_lifting_task (
            arrival_time,
            begin_time,
            cur_duration,
            cur_mileage,
            destination,
            mac,
            product_code,
            robot_name,
            shop_id,
            shop_name,
            sn,
            stay_duration,
            task_time
        )
        VALUES (
            %(arrival_time)s,
            %(begin_time)s,
            %(cur_duration)s,
            %(cur_mileage)s,
            %(destination)s,
            %(mac)s,
            %(product_code)s,
            %(robot_name)s,
            %(shop_id)s,
            %(shop_name)s,
            %(sn)s,
            %(stay_duration)s,
            %(task_time)s
        )
        ON CONFLICT DO NOTHING;
    """
    rows = data["data"]["list"]

    with conn.cursor() as cur:
        for raw in rows:
            item = raw.copy()
            for f in TS_FIELDS:
                item[f] = _to_ts(item.get(f))
            cur.execute(query, item)

    conn.commit()
    print(f"[INFO] Inseriti {len(rows)} record in robot_industrial_lifting_task")


# ----------------------------------------------------------------------
# 3. delivery GREETER
# ----------------------------------------------------------------------
def insert_robot_delivery_greeter_tasks(conn, data):
    query = """
        INSERT INTO robot_delivery_greeter_task (
            arrival_time,
            begin_time,
            cur_duration,
            cur_mileage,
            destination,
            mac,
            product_code,
            robot_name,
            shop_id,
            shop_name,
            sn,
            stay_duration,
            task_time
        )
        VALUES (
            %(arrival_time)s,
            %(begin_time)s,
            %(cur_duration)s,
            %(cur_mileage)s,
            %(destination)s,
            %(mac)s,
            %(product_code)s,
            %(robot_name)s,
            %(shop_id)s,
            %(shop_name)s,
            %(sn)s,
            %(stay_duration)s,
            %(task_time)s
        )
        ON CONFLICT DO NOTHING;
    """
    rows = data["data"]["list"]

    with conn.cursor() as cur:
        for raw in rows:
            item = raw.copy()
            for f in TS_FIELDS:
                item[f] = _to_ts(item.get(f))
            cur.execute(query, item)

    conn.commit()
    print(f"[INFO] Inseriti {len(rows)} record in robot_delivery_greeter_task")


# ----------------------------------------------------------------------
# 4. delivery CALL
# ----------------------------------------------------------------------
def insert_robot_delivery_call_tasks(conn, data):
    query = """
        INSERT INTO robot_delivery_call_task (
            arrival_time,
            begin_time,
            cur_duration,
            cur_mileage,
            destination,
            mac,
            product_code,
            robot_name,
            shop_id,
            shop_name,
            sn,
            stay_duration,
            task_time
        )
        VALUES (
            %(arrival_time)s,
            %(begin_time)s,
            %(cur_duration)s,
            %(cur_mileage)s,
            %(destination)s,
            %(mac)s,
            %(product_code)s,
            %(robot_name)s,
            %(shop_id)s,
            %(shop_name)s,
            %(sn)s,
            %(stay_duration)s,
            %(task_time)s
        )
        ON CONFLICT DO NOTHING;
    """
    rows = data["data"]["list"]

    with conn.cursor() as cur:
        for raw in rows:
            item = raw.copy()
            # qui ci sono record con "" in arrival_time
            for f in TS_FIELDS:
                item[f] = _to_ts(item.get(f))
            cur.execute(query, item)

    conn.commit()
    print(f"[INFO] Inseriti {len(rows)} record in robot_delivery_call_task")


# ----------------------------------------------------------------------
# 5. delivery RECOVERY (schema diverso)
# ----------------------------------------------------------------------
def insert_robot_delivery_recovery_tasks(conn, data):
    query = """
        INSERT INTO robot_delivery_recovery_task (
            task_time,
            mac,
            shop_id,
            shop_name,
            product_code,
            product_name,
            bind_time,
            mileage,
            duration,
            table_count,
            tray_count,
            already_unbind,
            sn,
            task_count,
            speed,
            run_count,
            bind_count
        )
        VALUES (
            %(task_time)s,
            %(mac)s,
            %(shop_id)s,
            %(shop_name)s,
            %(product_code)s,
            %(product_name)s,
            %(bind_time)s,
            %(mileage)s,
            %(duration)s,
            %(table_count)s,
            %(tray_count)s,
            %(already_unbind)s,
            %(sn)s,
            %(task_count)s,
            %(speed)s,
            %(run_count)s,
            %(bind_count)s
        )
        ON CONFLICT DO NOTHING;
    """
    rows = data["data"]["list"]

    with conn.cursor() as cur:
        for raw in rows:
            item = raw.copy()
            item["task_time"] = _to_date(item.get("task_time"))
            item["bind_time"] = _to_ts(item.get("bind_time"))
            item["mileage"] = _to_float(item.get("mileage"))
            item["duration"] = _to_float(item.get("duration"))
            item["table_count"] = _to_int(item.get("table_count"))
            item["tray_count"] = _to_int(item.get("tray_count"))
            item["task_count"] = _to_int(item.get("task_count"))
            item["speed"] = _to_float(item.get("speed"))
            item["run_count"] = _to_int(item.get("run_count"))
            item["bind_count"] = _to_int(item.get("bind_count"))
            cur.execute(query, item)

    conn.commit()
    print(f"[INFO] Inseriti {len(rows)} record in robot_delivery_recovery_task")

def load_movements(conn):
    """
    Carica i dati dei movimenti nel database.
    """

    print(f"Caricamento di {len(r.movement)} movimenti...")

    # Inserimento nel database
    with conn.cursor() as cur:
        inserted = 0
        updated = 0

        for entry in r.movement:
            # Verifica che la risposta sia SUCCESS
            if entry["code"] != 0:
                print(f"Warning: movimento con trace_id {entry['trace_id']} ha code {entry['code']}")

            data = entry["data"]
            position = data["position"]

            # Inserisci il movimento
            cur.execute(
                """
                INSERT INTO robot_movement (trace_id, message, code, map_name, point_name,
                                            point_id, floor, position_x, position_y, position_z)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (trace_id) DO UPDATE
                    SET message    = EXCLUDED.message,
                        code       = EXCLUDED.code,
                        map_name   = EXCLUDED.map_name,
                        point_name = EXCLUDED.point_name,
                        point_id   = EXCLUDED.point_id,
                        floor      = EXCLUDED.floor,
                        position_x = EXCLUDED.position_x,
                        position_y = EXCLUDED.position_y,
                        position_z = EXCLUDED.position_z
                RETURNING (xmax = 0) AS inserted
                """,
                (
                    entry["trace_id"],
                    entry["message"],
                    entry["code"],
                    data["map_name"],
                    data["point_name"],
                    data["point_id"],
                    data["floor"],
                    position["x"],
                    position["y"],
                    position["z"]
                ),
            )

            # Conta inserimenti vs aggiornamenti
            result = cur.fetchone()
            if result and result[0]:
                inserted += 1
            else:
                updated += 1

    conn.commit()
    print(f"Operazione completata: {inserted} movimenti inseriti, {updated} movimenti aggiornati")


# ----------------------------------------------------------------------
# main
# ----------------------------------------------------------------------
def main():
    conn = psycopg.connect(PG_DSN)
    try:
        # 1. cleaning
        get_cleaning_task(conn)

        # 2. industrial lifting
        insert_robot_industrial_lifting_tasks(conn, r.robot_industrial_lifting_tasks_example)

        # 3. delivery greeter
        insert_robot_delivery_greeter_tasks(conn, r.robot_delivery_greeter_tasks_example)

        # 4. delivery call
        insert_robot_delivery_call_tasks(conn, r.robot_delivery_call_tasks_example)

        # 5. delivery recovery
        insert_robot_delivery_recovery_tasks(conn, r.robot_delivery_recovery_tasks_example)

        load_movements(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
