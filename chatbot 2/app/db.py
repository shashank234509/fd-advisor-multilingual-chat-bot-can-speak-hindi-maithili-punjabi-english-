from typing import Any, Optional

import mysql.connector
from mysql.connector import MySQLConnection

from app.config import settings


def get_connection() -> MySQLConnection:
    return mysql.connector.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
    )


def fetch_best_offer(tenor_months: Optional[int] = None) -> Optional[dict[str, Any]]:
    query = """
        SELECT bank_name, tenor_months, rate, goal_tag
        FROM bank_offers
    """
    params: tuple[Any, ...] = ()
    if tenor_months:
        query += " WHERE tenor_months = %s"
        params = (tenor_months,)
    query += " ORDER BY rate DESC, tenor_months ASC LIMIT 1"

    with get_connection() as conn:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()
            if row:
                return row
            # If exact tenor match is unavailable, fall back to best overall offer.
            if tenor_months:
                cursor.execute(
                    """
                    SELECT bank_name, tenor_months, rate, goal_tag
                    FROM bank_offers
                    ORDER BY rate DESC, tenor_months ASC
                    LIMIT 1
                    """
                )
                return cursor.fetchone()
            return None


def fetch_jargon_map(language: str) -> dict[str, str]:
    query = """
        SELECT term, local_translation
        FROM dialect_jargon
        WHERE language = %s
    """
    with get_connection() as conn:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(query, (language,))
            rows = cursor.fetchall()
    return {row["term"]: row["local_translation"] for row in rows}


def save_user_advice(
    username: str,
    language: str,
    user_reason: str,
    invested_amount: float,
    suggested_bank: str,
    suggested_rate: float,
) -> None:
    query = """
        INSERT INTO user_history
            (username, language, user_reason, invested_amount, suggested_bank, suggested_rate)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                query,
                (
                    username,
                    language,
                    user_reason,
                    invested_amount,
                    suggested_bank,
                    suggested_rate,
                ),
            )
            conn.commit()
