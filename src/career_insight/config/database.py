from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import pymysql
from pymysql.connections import Connection

from career_insight.config.settings import Settings, get_settings


def get_mysql_connection(
    settings: Settings | None = None,
    *,
    autocommit: bool = True,
    dict_cursor: bool = True,
) -> Connection:
    cfg = settings or get_settings()
    cursorclass = pymysql.cursors.DictCursor if dict_cursor else pymysql.cursors.Cursor
    return pymysql.connect(
        host=cfg.mysql_host,
        port=cfg.mysql_port,
        user=cfg.mysql_user,
        password=cfg.mysql_password,
        database=cfg.mysql_database,
        charset="utf8mb4",
        cursorclass=cursorclass,
        autocommit=autocommit,
        connect_timeout=10,
        read_timeout=30,
        write_timeout=30,
    )


@contextmanager
def mysql_cursor(
    settings: Settings | None = None,
    *,
    autocommit: bool = True,
) -> Iterator[pymysql.cursors.DictCursor]:
    conn = get_mysql_connection(settings, autocommit=autocommit, dict_cursor=True)
    try:
        with conn.cursor() as cursor:
            yield cursor
        if not autocommit:
            conn.commit()
    except Exception:
        if not autocommit:
            conn.rollback()
        raise
    finally:
        conn.close()
