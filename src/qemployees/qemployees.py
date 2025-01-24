import json
import os
from typing import Optional, Iterator

import dotenv
import psycopg2
from psycopg2 import extensions, extras

dotenv.load_dotenv()


def create_table(cur: psycopg2.extensions.cursor) -> None:
    """
    Create table if it doesn't exist already.
    Columns are: id, parent_id, name and type.
    :param cur: psycopg2 cursor object for sql execution
    :return: None
    """
    cur.execute("""
         CREATE TABLE IF NOT EXISTS hier (
            id SERIAL PRIMARY KEY,
            parent_id INT NULL,
            name VARCHAR(255) NOT NULL,
            type INT NOT NULL
         );
    """)


def truncate_table(cur: psycopg2.extensions.cursor) -> None:
    """
    Truncate working table for a fresh start.
    :param cur: psycopg2 cursor object for sql execution
    :return: None
    """
    cur.execute("TRUNCATE hier")


def load_fixture(fp: str, cur: psycopg2.extensions.cursor) -> None:
    """
    Populate working table with entries from a json file.
    :param fp: path to a .json file or any format accepted by json.load()
    :param cur: psycopg2 cursor object for sql execution
    :return: None
    """
    with open(fp, "r", encoding="utf-8") as f:
        fixture_data = json.load(f)

    psycopg2.extras.execute_values(
        cur=cur,
        sql="INSERT INTO hier (id, parent_id, name, type) VALUES %s",
        argslist=fixture_data,
        template=os.environ["JSON_TENPLATE"]
    )


def query_employees(employee_id: str, cur: psycopg2.extensions.cursor) -> list[Optional[tuple]]:
    """
    Query a full list of employees from the same office as a given employee
    :param employee_id: primary key id for the employee in question
    :param cur: psycopg2 cursor object for sql execution
    :return: list of tuples representing entries that were found or an empty list
    """

    top_level, bottom_level = os.environ["HIER_TOP_LEVEL"], os.environ["HIER_BOTTOM_LEVEL"]
    cur.execute("""
        WITH RECURSIVE path AS (
            SELECT h.id, h.parent_id, h.name, h.type
            FROM hier h
            WHERE h.id = %s
            UNION ALL
            SELECT h.id, h.parent_id, h.name, h.type
            FROM hier h
            JOIN path p ON p.parent_id = h.id
        ),
        top AS (
            SELECT p.id
            FROM path p
            WHERE p.type = %s
        ),
        children AS (
            SELECT h.id, h.parent_id, h.name, h.type
            FROM hier h
            WHERE h.id = (SELECT t.id FROM top t)
            UNION ALL
            SELECT h.id, h.parent_id, h.name, h.type
            FROM hier h
            JOIN children c ON c.id = h.parent_id
        )
        SELECT c.id, c.parent_id, c.name, c.type
        FROM children c
        WHERE c.type = %s
    """, (employee_id, top_level, bottom_level))

    return cur.fetchall()


def get_conn() -> Iterator[psycopg2.extensions.connection]:
    """
    Get psycopg2 connection object to use
    :return: iterator on psycopg2 connection object
    """
    conn = psycopg2.connect(os.environ["DB_DSN"])
    yield conn
    conn.close()
