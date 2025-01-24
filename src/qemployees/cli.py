import argparse

from .qemployees import (
    get_conn,
    query_employees,
    create_table,
    truncate_table,
    load_fixture,
)


def run_service(args) -> None:
    """
    Default function for service subcommand
    :param args: parsed args from ArgumentParser object
    :return: None
    """
    conn = next(get_conn())
    with conn.cursor() as cur:
        if args.init:
            create_table(cur)
            print("CREATE TABLE complete")

        if args.truncate:
            truncate_table(cur)
            print("TRUNCATE TABLE complete")

        if args.loaddata:
            load_fixture(args.loaddata, cur)
            print(f"Loaded fixture data from {args.loaddata}")
    conn.commit()


def run_query(args) -> None:
    """
    Default function for query subcommand
    :param args: parsed args from ArgumentParser object
    :return: None
    """
    conn = next(get_conn())
    with conn.cursor() as cur:
        result = query_employees(args.employee_id, cur)
    print("Found: ", result)


def init_parser() -> argparse.ArgumentParser:
    """
    Initialize cli args parsers
    :return: argparse.ArgumentParser object
    """
    # Main parser and subparsers object init
    parser = argparse.ArgumentParser(
        prog="qemployees",
        description="CLI tool to query employees from the same office",
    )
    subparsers = parser.add_subparsers(
        title="Operation mode",
        description="Choose either service or query mode",
        help="Service mode is for DB and data manipulation. Query mode is a 'combat' mode for querying employees",
        required=True,
    )

    # Service parser setup
    parser_service = subparsers.add_parser(
        "service", help="Service mod for table and data manipulation"
    )
    parser_service.add_argument(
        "-i", "--init", help="Create table if not exists", action="store_true"
    )
    parser_service.add_argument(
        "-t", "--truncate", help="Truncate table", action="store_true"
    )
    parser_service.add_argument(
        "-ld", "--loaddata", help="Path to a fixture to load", type=str
    )
    parser_service.set_defaults(func=run_service)

    # Combat mode parser setup
    parser_query = subparsers.add_parser("query", help="Query (combat) mode")
    parser_query.add_argument("employee_id", metavar="ID", type=str, help="Employee id")
    parser_query.set_defaults(func=run_query)

    return parser


def run(args=None):
    """
    CLI entry point
    :param args: args if provided
    """
    parser = init_parser()
    parsed_args = parser.parse_args(args)
    parsed_args.func(parsed_args)
