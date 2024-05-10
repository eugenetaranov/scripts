#!/usr/bin/env python
import random
import string
from argparse import ArgumentParser
from time import sleep

import mysql.connector
from loguru import logger


def parseargs():
    p = ArgumentParser()
    p.add_argument("-s", "--server", required=True, help="Host")
    p.add_argument("-d", "--database", required=True, help="Database")
    p.add_argument("-u", "--user", required=True, help="User")
    p.add_argument("-p", "--password", required=True, help="Password")
    p.add_argument("-t", "--table", required=True, help="Table name")

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
        self.timeout = 1
        self.connection = None
        self.cursor = None
        self.connect()

    def connect(self):
        while True:
            try:
                self.connection = mysql.connector.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    connection_timeout=self.timeout,
                )
                self.cursor = self.connection.cursor()
                logger.info("Connected to the database")
                break
            except mysql.connector.Error as e:
                sleep(self.timeout)

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
        host=args["server"],
        user=args["user"],
        password=args["password"],
        database=args["database"],
    )
    table = args["table"]

    db.generate_table(table)

    last_read_state = False
    last_write_state = False

    while True:
        # check if table is readable
        try:
            db.read(table)
            if not last_read_state:
                logger.info(f"Table {table} is now readable")
                last_read_state = True
        except Exception as e:
            if last_read_state:
                logger.error(f"Table {table} is not readable: {e}")
                last_read_state = False
                last_write_state = False
                db.connect()

        # check if table is writable
        try:
            data = generate_random_string()

            db.insert(table, data)
            if not last_write_state:
                logger.info(f"Table {table} is now writable")
                last_write_state = True
        except Exception as e:
            if last_write_state:
                logger.error(f"Table {table} is not writable: {e}")
                last_read_state = False
                last_write_state = False
                db.connect()

        sleep(1)


if __name__ == "__main__":
    main()
