import argparse

from .qemployees import get_conn, query_employees, create_table, truncate_table, load_fixture


def init_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qemployees",
        description="CLI tool to query employees from the same office",
    )
    parser.add_argument(
        "-i",
        "--init",
        help="Create table if not exists",
        action="store_true"
    )
    parser.add_argument(
        "-t",
        "--truncate",
        help="Truncate table",
        action="store_true"
    )
    parser.add_argument(
        "-ld", "--loaddata",
        help="Path to a fixture to load",
        type=str
    )
    parser.add_argument(
        "employee_id",
        metavar="ID",
        type=str,
        help="Employee id",
        nargs="?",
        default=None
    )
    return parser


def run(args=None):
    parser = init_parser()
    parsed_args = parser.parse_args(args)

    conn = next(get_conn())
    with conn.cursor() as cur:
        if parsed_args.init:
            create_table(cur)

        if parsed_args.truncate:
            truncate_table(cur)

        if parsed_args.loaddata:
            load_fixture(parsed_args.loaddata, cur)

        if parsed_args.employee_id is not None:
            result = query_employees(parsed_args.employee_id, cur)
            print(result)
    conn.commit()
