from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


CLICKHOUSE_HTTP_URL = "http://clickhouse:8123"
CLICKHOUSE_DB = "bionicpro_reports"

POSTGRES_CONN_ID = "postgres_crm"  # этот connection нужно создать в UI Airflow


# ------------- Вспомогательные функции -------------

def _execute_clickhouse(sql: str, database: str | None = None) -> None:
    """Выполнить SQL в ClickHouse через HTTP-интерфейс."""
    import requests

    params = {}
    if database:
        params["database"] = database

    resp = requests.post(CLICKHOUSE_HTTP_URL, params=params, data=sql.encode("utf-8"))
    if resp.status_code != 200:
        raise RuntimeError(
            f"ClickHouse HTTP error {resp.status_code}: {resp.text[:500]}"
        )


def _escape_str(value: str | None) -> str:
    """Примитивный экранировщик одинарных кавычек для VALUES."""
    if value is None:
        return ""
    return value.replace("'", "''")


# ------------- Шаг 1. Инициализация схемы в ClickHouse -------------

def _init_clickhouse(**context):
    # создаём БД, если нет
    _execute_clickhouse(f"CREATE DATABASE IF NOT EXISTS {CLICKHOUSE_DB}")

    # таблица измерения user + prosthesis
    ddl_dim = f"""
    CREATE TABLE IF NOT EXISTS dim_user_prosthesis
    (
        user_id          UInt64,
        country_code     FixedString(2),
        prosthesis_id    UInt64,
        device_model     String,
        firmware_version String
    )
    ENGINE = MergeTree
    ORDER BY (user_id, prosthesis_id)
    """
    _execute_clickhouse(ddl_dim, database=CLICKHOUSE_DB)

    # таблица витрины отчётности
    ddl_fact = f"""
    CREATE TABLE IF NOT EXISTS report_prosthesis_daily_stats
    (
        event_date          Date,
        user_id             UInt64,
        prosthesis_id       UInt64,
        country_code        FixedString(2),
        device_model        String,
        firmware_version    String,

        sessions_count      UInt32,
        avg_reaction_ms     Float32,
        p95_reaction_ms     Float32,
        max_reaction_ms     UInt32,

        battery_avg_level   Float32,
        battery_min_level   UInt8,

        errors_count        UInt32,
        overheating_count   UInt32,
        low_battery_count   UInt32,

        last_event_ts       DateTime,
        load_datetime       DateTime DEFAULT now()
    )
    ENGINE = MergeTree
    PARTITION BY toYYYYMM(event_date)
    ORDER BY (user_id, prosthesis_id, event_date)
    """
    _execute_clickhouse(ddl_fact, database=CLICKHOUSE_DB)


# ------------- Шаг 2. Загрузка измерения из CRM (Postgres -> ClickHouse) -------------

def _load_crm_dimension(**context):
    # ленивый импорт, чтобы DAG не падал при парсинге, даже если провайдер не установлен
    from airflow.providers.postgres.hooks.postgres import PostgresHook

    pg_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    sql_crm = """
        SELECT
            u.id           AS user_id,
            COALESCE(u.country_code, 'RU') AS country_code,
            p.id           AS prosthesis_id,
            p.device_model AS device_model,
            p.firmware_version AS firmware_version
        FROM crm_users u
        JOIN crm_prostheses p ON p.user_id = u.id
    """
    rows = pg_hook.get_records(sql_crm)

    # чистим измерение и перезаливаем свежие данные
    _execute_clickhouse("TRUNCATE TABLE dim_user_prosthesis", database=CLICKHOUSE_DB)

    if not rows:
        return

    # для простоты — вставляем по одной строке (для учебного проекта ок, в бою лучше делать bulk-вставки)
    for user_id, country_code, prosthesis_id, device_model, firmware_version in rows:
        country_code = (country_code or "RU")[:2]
        device_model = _escape_str(device_model or "")
        firmware_version = _escape_str(firmware_version or "")

        insert_sql = f"""
        INSERT INTO dim_user_prosthesis
            (user_id, country_code, prosthesis_id, device_model, firmware_version)
        VALUES
            ({int(user_id)}, '{country_code}', {int(prosthesis_id)}, '{device_model}', '{firmware_version}')
        """
        _execute_clickhouse(insert_sql, database=CLICKHOUSE_DB)


# ------------- Шаг 3. Подготовка суточной витрины из телеметрии + CRM -------------

def _build_daily_stats(**context):
    # дата, за которую считаем витрину (execution_date = ds)
    date_str = context["ds"]  # 'YYYY-MM-DD'

    # удаляем данные за этот день, чтобы можно было пересчитать
    delete_sql = f"""
    ALTER TABLE report_prosthesis_daily_stats
    DELETE WHERE event_date = toDate('{date_str}')
    """
    _execute_clickhouse(delete_sql, database=CLICKHOUSE_DB)

    # считаем агрегаты и вставляем в витрину
    insert_sql = f"""
    INSERT INTO report_prosthesis_daily_stats
    SELECT
        toDate(t.event_ts)                    AS event_date,
        d.user_id                             AS user_id,
        d.prosthesis_id                       AS prosthesis_id,
        d.country_code                        AS country_code,
        d.device_model                        AS device_model,
        d.firmware_version                    AS firmware_version,

        uniqExact(t.session_id)               AS sessions_count,
        avg(t.reaction_ms)                    AS avg_reaction_ms,
        quantile(0.95)(t.reaction_ms)         AS p95_reaction_ms,
        max(t.reaction_ms)                    AS max_reaction_ms,

        avg(t.battery_level)                  AS battery_avg_level,
        min(t.battery_level)                  AS battery_min_level,

        countIf(t.event_type = 'ERROR')       AS errors_count,
        countIf(t.event_type = 'OVERHEAT')    AS overheating_count,
        countIf(t.event_type = 'LOW_BATTERY') AS low_battery_count,

        max(t.event_ts)                       AS last_event_ts,
        now()                                 AS load_datetime
    FROM telemetry_raw t
    INNER JOIN dim_user_prosthesis d
        ON d.prosthesis_id = t.prosthesis_id
    WHERE toDate(t.event_ts) = toDate('{date_str}')
    GROUP BY
        event_date,
        user_id,
        prosthesis_id,
        country_code,
        device_model,
        firmware_version
    """
    _execute_clickhouse(insert_sql, database=CLICKHOUSE_DB)


# ------------- Описание DAG -------------

default_args = {
    "owner": "data-engineer",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="bionicpro_reports_daily",
    description="Daily ETL: CRM + telemetry -> ClickHouse report mart",
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule_interval="0 2 * * *",  # каждый день в 02:00
    catchup=False,
    tags=["bionicpro", "reports", "etl"],
) as dag:

    init_clickhouse = PythonOperator(
        task_id="init_clickhouse",
        python_callable=_init_clickhouse,
        provide_context=True,
    )

    load_crm_dimension = PythonOperator(
        task_id="load_crm_dimension",
        python_callable=_load_crm_dimension,
        provide_context=True,
    )

    build_daily_stats = PythonOperator(
        task_id="build_daily_stats",
        python_callable=_build_daily_stats,
        provide_context=True,
    )

    init_clickhouse >> load_crm_dimension >> build_daily_stats
