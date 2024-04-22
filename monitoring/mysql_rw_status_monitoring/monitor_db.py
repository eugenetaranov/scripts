#!/usr/bin/env python
import random
import string
from argparse import ArgumentParser
from time import sleep

import mysql.connector
from loguru import logger


def parseargs():
    p = ArgumentParser()
    p.add_argument("--host", required=True, help="Host")
    p.add_argument("--database", required=True, help="Database")
    p.add_argument("--user", required=True, help="User")
    p.add_argument("--password", required=True, help="Password")
    p.add_argument("--table", required=True, help="Table name")

    return vars(p.parse_args())


def generate_random_string():
    length = random.randint(20, 50)
    return "".join(random.choice(string.ascii_letters) for _ in range(length))


class DatabaseConnector:
    def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = mysql.connector.connect(
            host=host, user=user, password=password, database=database
        )
        self.cursor = self.connection.cursor()

    def __del__(self):
        self.connection.close()
        self.cursor.close()

    # read data from table
    def read(self, table):
        self.cursor.execute(f"SELECT * FROM {table} LIMIT 10")
        return self.cursor.fetchall()

    # generate sample table structure
    def generate_table(self, table):
        try:
            self.cursor.execute(
                f"CREATE TABLE {table} (id INT AUTO_INCREMENT PRIMARY KEY, text VARCHAR(255))"
            )
            self.connection.commit()
            logger.info(f"Table {table} created")

        except mysql.connector.errors.ProgrammingError:
            logger.info(f"Table {table} already exists")

    # insert data into table
    def insert(self, table, data):
        self.cursor.execute(f"INSERT INTO {table} (text) VALUES ('{data}')")
        self.connection.commit()


def main():
    args = parseargs()
    db = DatabaseConnector(
        args["host"], args["user"], args["password"], args["database"]
    )
    table = args["table"]

    db.generate_table(table)

    while True:
        # check if table is readable
        try:
            db.read(table)
            logger.info(f"Table {table} is readable")
        except Exception as e:
            logger.error(f"Table {table} is not readable: {e}")

        # check if table is writable
        try:
            data = generate_random_string()

            db.insert(table, data)
            logger.info(f"Table {table} is writable")
        except Exception as e:
            logger.error(f"Table {table} is not writable: {e}")

        sleep(1)


if __name__ == "__main__":
    main()
