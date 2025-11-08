-- INIT QUERY

-- 1. company
CREATE TABLE IF NOT EXISTS company (
    company_id   BIGINT PRIMARY KEY,
    company_name TEXT NOT NULL
);

-- 2. shop v
CREATE TABLE IF NOT EXISTS shop (
    shop_id    BIGINT PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES company(company_id),
    shop_name  TEXT NOT NULL
);

-- 4. robots
-- nell’API il robot è identificato dal serial number (sn),
-- quindi lo uso come PK. shop_id è la FK.
CREATE TABLE IF NOT EXISTS robots (
    sn           TEXT PRIMARY KEY,
    shop_id      BIGINT NOT NULL REFERENCES shop(shop_id),
    mac          TEXT,
    product_code TEXT,
    -- se vuoi tenere anche il nome negozio come arriva dall’API:
    shop_name    TEXT
);

-- 5. task
-- continene le task fisse, quindi quello per cui il robot è stato programmato,
--     task_category: la categoria per cui il robot e stato creato
--     task_type: a cosa il robot è stato assegnato
--     sn: serial number del robot
CREATE TABLE IF NOT EXISTS task (
    task_id       BIGSERIAL PRIMARY KEY,
    sn            TEXT NOT NULL REFERENCES robots(sn),
    task_category TEXT NOT NULL,
    task_type     TEXT NOT NULL
);

-- Fact table
-- 1. log diagnostica: /shops/robot-status
CREATE TABLE IF NOT EXISTS robot_status_log (
    id           UUID PRIMARY KEY,
    sn           TEXT NOT NULL REFERENCES robots(sn),
    shop_id      BIGINT REFERENCES shop(shop_id),
    upload_time  TIMESTAMPTZ,
    task_time    TIMESTAMPTZ,
    soft_version TEXT,
    hard_version TEXT,
    ip           TEXT,
    check_result JSONB,     -- array di step con stato
    is_success   INT        -- 0/1
);

-- 2. log errori/eventi: /shops/robot-errors
CREATE TABLE IF NOT EXISTS robot_error_log (
    id             UUID PRIMARY KEY,
    sn             TEXT NOT NULL REFERENCES robots(sn),
    shop_id        BIGINT REFERENCES shop(shop_id),
    upload_time    TIMESTAMPTZ,
    task_time      TIMESTAMPTZ,
    soft_version   TEXT,
    hard_version   TEXT,
    error_level    TEXT,
    error_type     TEXT,
    error_source_id TEXT,   -- mappa error_id dell'API
    mac            TEXT,
    product_code   TEXT
);

-- 3. log ricariche: /shops/robot-charges
CREATE TABLE IF NOT EXISTS robot_charge_log (
    id                 UUID PRIMARY KEY,
    sn                 TEXT NOT NULL REFERENCES robots(sn),
    shop_id            BIGINT REFERENCES shop(shop_id),
    upload_time        TIMESTAMPTZ,
    task_time          TIMESTAMPTZ,
    soft_version       TEXT,
    hard_version       TEXT,
    mac                TEXT,
    product_code       TEXT,
    charge_power_pct   INT,
    charge_duration_s  INT,
    min_power_pct      INT,
    max_power_pct      INT
);

-- 1. Tabella principale dei task di pulizia
CREATE TABLE IF NOT EXISTS cleaning_task (
    task_id        VARCHAR(50) PRIMARY KEY,
    version        BIGINT NOT NULL,
    name           VARCHAR(255) NOT NULL,
    description    TEXT,
    status         INTEGER NOT NULL,
    is_single_task BOOLEAN NOT NULL,
    task_count     INTEGER NOT NULL,
    task_mode      INTEGER NOT NULL,
    pre_clean_time INTEGER NOT NULL,
    is_area_connect BOOLEAN NOT NULL,
    is_hand_sort    BOOLEAN NOT NULL,
    shop_id        BIGINT,
    robot_sn       VARCHAR(50) NOT NULL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabella configurazione task
CREATE TABLE IF NOT EXISTS task_config (
    task_id              VARCHAR(50) PRIMARY KEY
        REFERENCES cleaning_task (task_id) ON DELETE CASCADE,
    ai_adaptive_switch   BOOLEAN NOT NULL,
    left_brush           INTEGER NOT NULL,
    mode                 INTEGER NOT NULL,
    right_brush          INTEGER NOT NULL,
    right_vacuum_suction INTEGER NOT NULL,
    type                 INTEGER NOT NULL,
    vacuum_speed         INTEGER NOT NULL,
    vacuum_suction       INTEGER NOT NULL,
    wash_speed           INTEGER NOT NULL,
    wash_suction         INTEGER NOT NULL,
    wash_water           INTEGER NOT NULL
);

-- 3. Tabella stazioni di lavoro
CREATE TABLE IF NOT EXISTS station (
    station_id      VARCHAR(100) PRIMARY KEY,
    station_name    VARCHAR(255) NOT NULL,
    station_type    INTEGER NOT NULL,
    station_function INTEGER NOT NULL,
    map_name        VARCHAR(255) NOT NULL,
    task_id         VARCHAR(50)
        REFERENCES cleaning_task (task_id) ON DELETE CASCADE
);

-- 4. Tabella punti di ritorno
CREATE TABLE IF NOT EXISTS back_point (
    point_id   VARCHAR(100) PRIMARY KEY,
    point_name VARCHAR(255) NOT NULL,
    floor      VARCHAR(50) NOT NULL,
    map_name   VARCHAR(255) NOT NULL,
    task_id    VARCHAR(50)
        REFERENCES cleaning_task (task_id) ON DELETE CASCADE
);

-- 5. Tabella mappe
CREATE TABLE IF NOT EXISTS map (
    map_name VARCHAR(255) NOT NULL,
    task_id  VARCHAR(50)
        REFERENCES cleaning_task (task_id) ON DELETE CASCADE,
    floor    VARCHAR(50) NOT NULL,
    level    INTEGER NOT NULL,
    PRIMARY KEY (map_name, task_id)
);

-- 6. Tabella aree di pulizia
CREATE TABLE IF NOT EXISTS cleaning_area (
    area_id     VARCHAR(100) PRIMARY KEY,
    area_name   VARCHAR(255) NOT NULL,
    area_size   DECIMAL(10,4) NOT NULL,
    clean_count INTEGER NOT NULL,
    area_type   INTEGER NOT NULL,
    map_name    VARCHAR(255) NOT NULL,
    task_id     VARCHAR(50)
        REFERENCES cleaning_task (task_id) ON DELETE CASCADE
);

-- 7. Tabella configurazione cleanagent
CREATE TABLE IF NOT EXISTS cleanagent_config (
    task_id  VARCHAR(50) PRIMARY KEY
        REFERENCES cleaning_task (task_id) ON DELETE CASCADE,
    is_open  BOOLEAN NOT NULL,
    scale    INTEGER NOT NULL
);

-- Indici
CREATE INDEX IF NOT EXISTS idx_cleaning_task_shop   ON cleaning_task (shop_id);
CREATE INDEX IF NOT EXISTS idx_cleaning_task_robot  ON cleaning_task (robot_sn);
CREATE INDEX IF NOT EXISTS idx_cleaning_area_task   ON cleaning_area (task_id);
CREATE INDEX IF NOT EXISTS idx_map_task             ON map (task_id);
CREATE INDEX IF NOT EXISTS idx_station_task         ON station (task_id);


CREATE TABLE IF NOT EXISTS robot_industrial_lifting_task (
    id SERIAL PRIMARY KEY,
    arrival_time TIMESTAMP NULL,
    begin_time TIMESTAMP NOT NULL,
    cur_duration DOUBLE PRECISION,
    cur_mileage DOUBLE PRECISION,
    destination TEXT,
    mac VARCHAR(20) NOT NULL,
    product_code TEXT NOT NULL,
    robot_name TEXT NOT NULL,
    shop_id BIGINT NOT NULL,
    shop_name TEXT NOT NULL,
    sn VARCHAR(50) NOT NULL,
    stay_duration INTEGER,
    task_time TIMESTAMP NOT NULL,
    inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 1) Task di delivery "greeter" (quelli con tavolo, cucina, ascensore)
CREATE TABLE IF NOT EXISTS robot_delivery_greeter_task (
    id SERIAL PRIMARY KEY,
    arrival_time TIMESTAMP,
    begin_time   TIMESTAMP NOT NULL,
    cur_duration DOUBLE PRECISION,
    cur_mileage  DOUBLE PRECISION,
    destination  TEXT,
    mac          VARCHAR(20) NOT NULL,
    product_code TEXT NOT NULL,
    robot_name   TEXT NOT NULL,
    shop_id      BIGINT NOT NULL,
    shop_name    TEXT NOT NULL,
    sn           VARCHAR(50) NOT NULL,
    stay_duration INTEGER,
    task_time    TIMESTAMP NOT NULL,
    inserted_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- 2) Task di delivery "recovery" (sono più daily/aggregate)
CREATE TABLE IF NOT EXISTS robot_delivery_recovery_task (
    id SERIAL PRIMARY KEY,
    task_time    DATE NOT NULL,              -- nel JSON è "2023-08-31"
    mac          VARCHAR(20) NOT NULL,
    shop_id      BIGINT NOT NULL,
    shop_name    TEXT NOT NULL,
    product_code TEXT NOT NULL,
    product_name TEXT,
    bind_time    TIMESTAMP,
    mileage      DOUBLE PRECISION,
    duration     DOUBLE PRECISION,
    table_count  INTEGER,
    tray_count   INTEGER,
    already_unbind BOOLEAN,
    sn           VARCHAR(50) NOT NULL,
    task_count   INTEGER,
    speed        DOUBLE PRECISION,
    run_count    INTEGER,
    bind_count   INTEGER,
    inserted_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3) Task di delivery "call" (molto simili ai greeter)
CREATE TABLE IF NOT EXISTS robot_delivery_call_task (
    id SERIAL PRIMARY KEY,
    arrival_time TIMESTAMP,
    begin_time   TIMESTAMP NOT NULL,
    cur_duration DOUBLE PRECISION,
    cur_mileage  DOUBLE PRECISION,
    destination  TEXT,
    mac          VARCHAR(20) NOT NULL,
    product_code TEXT NOT NULL,
    robot_name   TEXT NOT NULL,
    shop_id      BIGINT NOT NULL,
    shop_name    TEXT NOT NULL,
    sn           VARCHAR(50) NOT NULL,
    stay_duration INTEGER,
    task_time    TIMESTAMP NOT NULL,
    inserted_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS robot_movement (
    trace_id    TEXT PRIMARY KEY,
    message     TEXT,
    code        INTEGER,
    map_name    TEXT,
    point_name  TEXT,
    point_id    TEXT,
    floor       TEXT,
    position_x  DOUBLE PRECISION,
    position_y  DOUBLE PRECISION,
    position_z  DOUBLE PRECISION,
    inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

