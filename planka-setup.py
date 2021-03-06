#!/usr/bin/env python3


# Standard Python Libraries
import argparse
import json
import logging
import tkinter as tk
from tkinter import filedialog


# Third-Party Libraries
import psycopg2
from psycopg2 import OperationalError

POSITION_GAP = 65535


def select_file(msg):

    print(f"Select a {msg} file")
    return filedialog.askopenfilename(
        title=f"Select a {msg} file.", filetypes=[("JSON File", ".json")]
    )


def generate_insert():
    pass


def create_connection(db_name, db_user, db_password, db_host, db_port):
    """Create connection to postgres database.

    Args:
        db_name (string): Database Name
        db_user (string): Database Username
        db_password (string): Database password
        db_host (string): Database Hostname
        db_port (string): Database Port Number

    Raises:
        e: Connection errors.

    Returns:
        Psycopg2 Connection: A connection to the postgres database.
    """

    logging.debug("Connecting to postgres")
    connection = None
    try:
        connection = psycopg2.connect(
            database=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
        )
        logging.info("Connection to PostgreSQL DB successful")
    except OperationalError as e:
        raise e

    return connection


def execute_read_query(connection, query):
    """Execute a read query on the postgres database.

    Args:
        connection (Psycopg2 Connection): The connection to the postgres database.
        query (string): The SQL query to be run.

    Returns:
        list(tuples): The results of the SQL query.
    """

    logging.debug(f"Executing Read Query: {query}")
    cursor = connection.cursor()
    result = None
    try:
        cursor.execute(query)
        result = cursor.fetchall()
        logging.debug("Query was successful.")
        return result
    except OperationalError as e:
        logging.error(f"The error '{e}' occurred")


def execute_query(connection, query):
    """Execute a query to change the database.

    Args:
        connection (Psycopg2 Connection): The connection to the postgres database.
        query (string): The SQL query to be run.
    """

    logging.debug(f"Executing Action: {query}")
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        logging.debug("Query executed successfully")
    except OperationalError as e:
        logging.error(f"The error '{e}' occurred")


def load_nmap(connection, project_id):
    """Load parsed NMAP data into cards.

    Args:
        connection (Psycopg2 Connection): The connection to the postgres database.
        project_id (string): The project that boards should be added to.
    """

    # Hold the postion of each item.
    card_position = POSITION_GAP

    # Get the board's ID
    query = """SELECT id FROM board WHERE name='Investigate'"""
    board_id = execute_read_query(connection, query)[0][0]
    logging.debug(f"Board id: {board_id}")

    # Get the new list's ID
    query = """SELECT id FROM list WHERE name='To-Review'"""
    list_id = execute_read_query(connection, query)[0][0]
    logging.debug(f"List id: {list_id}")

    logging.debug("Loading data structure from output.json")
    file_name = select_file("GNMAP")

    with open(file_name, "r") as fp:
        data = json.load(fp)

    # Add the host card.
    for card_index, card in enumerate(data["hosts"]):

        # Calculate the next card postion.
        card_position = card_position + (card_index * POSITION_GAP)

        logging.info(f"Building {card['ip']} Card.")
        query = f"""
            INSERT INTO
                card (board_id, list_id, name, position)
            VALUES
                ({board_id}, {list_id}, '{card['ip']}', {card_position})
        """
        execute_query(connection, query)

        # Get the new card's ID
        query = f"""SELECT id FROM card WHERE name='{card['ip']}'"""
        card_id = execute_read_query(connection, query)[0][0]
        logging.debug(f"Card id: {card_id}")

        # Add port tasks
        for task in card["ports"]:
            logging.debug(f"Adding {task}.")
            query = f"""
                INSERT INTO
                    task (card_id, name, is_completed)
                VALUES
                    ({card_id},'{task}', false)
            """
            execute_query(connection, query)


def build_new(connection, project_id):
    """Build out the project boards

    Args:
        connection (Psycopg2 Connection): The connection to the postgres database.
        project_id (string): The project that boards should be added to.
    """

    # Hold the postion of each item.
    board_position = POSITION_GAP
    list_position = POSITION_GAP
    card_position = POSITION_GAP

    logging.debug("Loading data structure from planka_build.json")
    file_name = select_file("Build")
    with open(file_name, "r") as fp:
        data_structure = json.load(fp)

    for board_index, board in enumerate(data_structure["boards"]):
        logging.info(f"Building {board['name']} Board.")

        # Calculate the next board postion.
        board_position = board_position + (board_index * POSITION_GAP)

        query = f"""
            INSERT INTO
                board (project_id, type, name, position)
            VALUES
                ({project_id}, 'kanban', '{board['name']}', {board_position})
        """
        execute_query(connection, query)

        # Get the new board's ID
        query = f"""SELECT id FROM board WHERE name='{board['name']}'"""
        board_id = execute_read_query(connection, query)[0][0]
        logging.debug(f"Board id: {board_id}")

        for list_index, _list in enumerate(board["lists"]):
            logging.info(f"Building {_list['name']} List.")

            # Calculate the next list position.
            list_position = list_position + (list_index * POSITION_GAP)

            query = f"""
                INSERT INTO
                    list (board_id, name, position)
                VALUES
                    ({board_id}, '{_list['name']}', {list_position})
            """
            execute_query(connection, query)

            # Get the new list's ID
            query = f"""SELECT id FROM list WHERE name='{_list['name']}'"""
            list_id = execute_read_query(connection, query)[0][0]
            logging.debug(f"List id: {list_id}")

            for card_index, card in enumerate(_list["cards"]):
                # Calculate the next card postion.
                card_position = card_position + (card_index * POSITION_GAP)

                logging.info(f"Building {card['name']} Card.")
                query = f"""
                    INSERT INTO
                        card (board_id, list_id, name, position)
                    VALUES
                        ({board_id}, {list_id}, '{card['name']}', {card_position})
                """
                execute_query(connection, query)

                # Get the new card's ID
                query = f"""SELECT id FROM card WHERE name='{card['name']}'"""
                card_id = execute_read_query(connection, query)[0][0]
                logging.debug(f"Card id: {card_id}")

                for task in card["tasks"]:
                    logging.debug(f"Adding {task}.")
                    query = f"""
                        INSERT INTO
                            task (card_id, name, is_completed)
                        VALUES
                            ({card_id},'{task}', false)
                    """
                    execute_query(connection, query)

        logging.info(f"{board['name']} Board Complete!")


def main():
    """Set up logging, connect to Postgres, call requested function(s)."""
    parser = argparse.ArgumentParser(description="Build out a Planka setup.")
    parser.add_argument(
        "PROJECT_NAME",
        action="store",
        help="The project name",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-l", "--load", action="store_true", dest="load", help="Load NMAP File."
    )
    group.add_argument(
        "-n",
        "--new",
        action="store_true",
        dest="new",
        help="Set up a new Project from the the file planka_build.json",
    )

    parser.add_argument(
        "--DB-host",
        action="store",
        dest="db_host",
        default="127.0.0.1",
        help="The host IP for the postgres server.",
    )
    parser.add_argument(
        "--DB-pwd",
        action="store",
        dest="db_pwd",
        default="planka",
        help="Password for the postgres server.",
    )
    parser.add_argument(
        "--DB-port",
        action="store",
        dest="db_port",
        default="5432",
        help="Port fo the postgres server.",
    )
    parser.add_argument(
        "--DB-name",
        action="store",
        dest="db_name",
        default="planka",
        help="Postgres database name.",
    )
    parser.add_argument(
        "--DB-user",
        action="store",
        dest="db_user",
        default="postgres",
        help="Username for the postgres server.",
    )
    parser.add_argument(
        "--log-level",
        action="store",
        dest="log_level",
        default="info",
        help='If specified, then the log level will be set to the specified value.  Valid values are "debug", "info", "warning", "error", and "critical".',
    )

    args = parser.parse_args()

    # Set up logging
    log_level = args.log_level
    try:
        logging.basicConfig(
            format="%(levelname)s: %(message)s", level=log_level.upper()
        )
    except ValueError:
        logging.critical(
            f'"{log_level}"is not a valid logging level. Possible values are debug, info, warning, and error.'
        )
        return 1

    # Set up database connection
    try:
        connection = create_connection(
            args.db_name,
            args.db_user,
            args.db_pwd,
            args.db_host,
            args.db_port,
        )
    except OperationalError as e:
        logging.error(f"The connection error '{e}' occurred")
        return 1

    # Set up tkinter
    root = tk.Tk()
    root.withdraw()

    if args.new:
        query = f"""
        INSERT INTO
            project (name)
        VALUES
            ('{args.PROJECT_NAME}')
        """
        # Create the new Project.
        execute_query(connection, query)

        # Gets value from first item in list and tuple
        query = f"""SELECT id FROM project WHERE name='{args.PROJECT_NAME}'"""
        project_id = execute_read_query(connection, query)[0][0]

        # Adds demo user to project
        # TODO handle already exists error.
        query = """SELECT id FROM user_account WHERE username='demo'"""
        user_id = execute_read_query(connection, query)[0][0]

        query = f"""
            INSERT INTO
                project_membership(project_id, user_id)
            VALUES
                ({project_id}, {user_id})
        """
        execute_query(connection, query)

        build_new(connection, project_id)

    elif args.load:
        # Gets value from first item in list and tuple
        query = f"""SELECT id FROM project WHERE name='{args.PROJECT_NAME}'"""
        project_id = execute_read_query(connection, query)[0][0]

        load_nmap(connection, project_id)


if __name__ == "__main__":
    main()
