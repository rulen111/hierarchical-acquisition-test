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
    cur.execute("""
        WITH RECURSIVE tree AS (
          SELECT id, parent_id, name, type, id AS root_id
          FROM hier h
          WHERE type = 1
          UNION ALL
          SELECT h.id, h.parent_id, h.name, h.type, t.root_id
          FROM hier h
          JOIN tree t ON t.id = h.parent_id
        ),
        city AS (
          SELECT root_id
          FROM tree
          WHERE id = %s
        )
        SELECT t.*
        FROM tree t
        WHERE t.root_id = (SELECT root_id FROM city) and type = 3
    """, (employee_id,))

    return cur.fetchall()


def get_conn() -> Iterator[psycopg2.extensions.connection]:
    """
    Get psycopg2 connection object to use
    :return: iterator on psycopg2 connection object
    """
    conn = psycopg2.connect(os.environ["DB_DSN"])
    yield conn
    conn.close()
