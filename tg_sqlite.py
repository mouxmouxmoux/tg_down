import sqlite3


class Sqlite3Helper:
    def __init__(self, db_file):
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()

    def create_table(self, table_name, fields):
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({fields})"
        self.cursor.execute(sql)
        self.conn.commit()

    def drop_table(self, table_name):
        sql = f"DROP TABLE IF EXISTS {table_name}"
        self.cursor.execute(sql)
        self.conn.commit()

    def insert(self, table_name, fields, values):
        sql = f"INSERT INTO {table_name} ({fields}) VALUES ({values})"
        self.cursor.execute(sql)
        self.conn.commit()

    def delete(self, table_name, condition):
        sql = f"DELETE FROM {table_name} WHERE {condition}"
        self.cursor.execute(sql)
        self.conn.commit()

    def update(self, table_name, set_values, condition):
        sql = f"UPDATE {table_name} SET {set_values} WHERE {condition}"
        self.cursor.execute(sql)
        self.conn.commit()

    def select(self, table_name, fields="*", condition=None):
        if condition:
            sql = f"SELECT {fields} FROM {table_name} WHERE {condition}"
        else:
            sql = f"SELECT {fields} FROM {table_name}"
        self.cursor.execute(sql)
        return self.cursor.fetchall()
