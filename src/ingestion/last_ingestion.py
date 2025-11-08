import psycopg

DB_DSN = "postgresql://admin:admin@localhost:5432/mydb"  # adatta al tuo docker

queries = [
    # 2. Delivery greeter
    """
    INSERT INTO robot_task_capability (sn, task_type, task_subtype)
    SELECT DISTINCT
        sn,
        'delivery' AS task_type,
        'greeter' AS task_subtype
    FROM robot_delivery_greeter_task
    WHERE sn IS NOT NULL AND sn <> ''
      AND EXISTS (
          SELECT 1 FROM robots r WHERE r.sn = robot_delivery_greeter_task.sn
      )
    ON CONFLICT (sn, task_type, task_subtype) DO NOTHING;
    """,
    # 3. Delivery call
    """
    INSERT INTO robot_task_capability (sn, task_type, task_subtype)
    SELECT DISTINCT
        sn,
        'delivery' AS task_type,
        'call' AS task_subtype
    FROM robot_delivery_call_task
    WHERE sn IS NOT NULL AND sn <> ''
      AND EXISTS (
          SELECT 1 FROM robots r WHERE r.sn = robot_delivery_call_task.sn
      )
    ON CONFLICT (sn, task_type, task_subtype) DO NOTHING;
    """,
    # 4. Delivery recovery
    """
    INSERT INTO robot_task_capability (sn, task_type, task_subtype)
    SELECT DISTINCT
        sn,
        'delivery' AS task_type,
        'recovery' AS task_subtype
    FROM robot_delivery_recovery_task
    WHERE sn IS NOT NULL AND sn <> ''
      AND EXISTS (
          SELECT 1 FROM robots r WHERE r.sn = robot_delivery_recovery_task.sn
      )
    ON CONFLICT (sn, task_type, task_subtype) DO NOTHING;
    """,
    # 5. Industrial lifting
    """
    INSERT INTO robot_task_capability (sn, task_type, task_subtype)
    SELECT DISTINCT
        sn,
        'industrial' AS task_type,
        'lifting' AS task_subtype
    FROM robot_industrial_lifting_task
    WHERE sn IS NOT NULL AND sn <> ''
      AND EXISTS (
          SELECT 1 FROM robots r WHERE r.sn = robot_industrial_lifting_task.sn
      )
    ON CONFLICT (sn, task_type, task_subtype) DO NOTHING;
    """
]

def populate_capabilities():
    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            for q in queries:
                cur.execute(q)
        conn.commit()

if __name__ == "__main__":
    populate_capabilities()
