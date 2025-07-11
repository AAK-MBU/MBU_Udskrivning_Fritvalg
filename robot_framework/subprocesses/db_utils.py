"""This module contains functions to interact with the database."""

import pyodbc


def get_exceptions(db_connection: str) -> list[dict]:
    """ Get exceptions from the database. """
    conn = pyodbc.connect(db_connection)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT
                [exception_code]
                ,[message_text]
            FROM
                [RPA].[rpa].[BusinessExceptionMessages]
            """
        )
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]
        return result
    finally:
        cursor.close()
