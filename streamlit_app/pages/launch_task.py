import streamlit as st
import requests
from collections import defaultdict
from datetime import datetime, timezone
import random

API_BASE = "http://api:8000"  # nome del servizio nel docker-compose


def fetch_shops():
    r = requests.get(f"{API_BASE}/shops")
    r.raise_for_status()
    return r.json()["shops"]


def fetch_tasks_flat():
    r = requests.get(f"{API_BASE}/tasks")
    r.raise_for_status()
    return r.json()["tasks"]


def run_task(sn: str, task_type: str, task_subtype: str | None):
    payload = {"task_type": task_type, "task_subtype": task_subtype}
    r = requests.post(f"{API_BASE}/robots/{sn}/run-task", json=payload)
    r.raise_for_status()
    return r.json()


def fetch_eta_by_shop(shop_id: int, limit: int = 100):
    r = requests.get(f"{API_BASE}/eta", params={"shop_id": shop_id, "limit": limit})
    r.raise_for_status()
    return r.json()["results"]


def human_remaining(ending_iso: str) -> str:
    if not ending_iso:
        return "n.d."
    try:
        end = datetime.fromisoformat(ending_iso)
    except ValueError:
        return "n.d."

    now = datetime.now(timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    diff = end - now
    if diff.total_seconds() <= 0:
        # qui applichiamo la tua regola: se è 0 o passato, mostra un valore casuale
        fake_sec = random.randint(150, 400)
        return str(fake_sec) + "s"
    return str(diff).split(".")[0]


def render():
    st.title("Lancia task robot")

    # 1) shop
    shops = fetch_shops()
    shop_opts = {f"{s['shop_name']} ({s['shop_id']})": s["shop_id"] for s in shops}
    sel_shop_label = st.selectbox("Seleziona shop", list(shop_opts.keys()))
    sel_shop_id = shop_opts[sel_shop_label]

    # 2) tasks (capability)
    rows = fetch_tasks_flat()
    rows = [r for r in rows if r["shop_id"] == sel_shop_id]

    if not rows:
        st.warning("Nessuna task per questo shop.")
        return

    # 3) group per tipo
    grouped = defaultdict(list)
    for row in rows:
        key = (row["task_type"], row.get("task_subtype"))
        grouped[key].append({"sn": row["sn"], "shop_id": row["shop_id"]})

    # 4) select task
    task_labels, task_keys = [], []
    for (t, ts), _robots in grouped.items():
        label = f"{t} / {ts}" if ts else t
        task_labels.append(label)
        task_keys.append((t, ts))

    sel_idx = st.selectbox(
        "Seleziona task",
        range(len(task_labels)),
        format_func=lambda i: task_labels[i],
    )
    sel_task_type, sel_task_subtype = task_keys[sel_idx]

    # 5) select robot
    robot_list = grouped[(sel_task_type, sel_task_subtype)]
    robot_idx = st.selectbox(
        "Seleziona robot",
        range(len(robot_list)),
        format_func=lambda i: f"{robot_list[i]['sn']} (shop {robot_list[i]['shop_id']})",
    )
    sel_robot = robot_list[robot_idx]

    # 6) launch
    if st.button("Lancia task"):
        try:
            res = run_task(
                sn=sel_robot["sn"],
                task_type=sel_task_type,
                task_subtype=sel_task_subtype,
            )
        except Exception as e:
            st.error(f"Errore: {e}")
        else:
            st.success(res)

    st.markdown("---")
    st.subheader("ETA task recenti di questo shop")

    etas = fetch_eta_by_shop(sel_shop_id, limit=100)
    if not etas:
        st.info("Nessuna ETA trovata per questo shop.")
        return

    table_names = {
        "robot_delivery_greeter_task": "delivery / greeter",
        "robot_delivery_call_task": "delivery / call",
        "robot_delivery_recovery_task": "delivery / recovery",
        "robot_industrial_lifting_task": "industrial / lifting",
        "cleaning_task": "cleaning",
    }

    display_rows = []
    for e in etas:
        src_table = e["src_table"]
        display_rows.append(
            {
                "tipo": table_names.get(src_table, src_table),
                "src_pk": e["src_pk"],
                "sn": e.get("sn") or "",
                "ending_time": e["ending_time"],
                "manca": human_remaining(e["ending_time"]),
                "calcolata_il": e["computed_at"],
            }
        )

    display_rows.sort(key=lambda x: x["ending_time"] or "9999-12-31T00:00:00")

    st.dataframe(display_rows)
