import sqlite3

DEBUG = False

class R53SQLDatabase(object):

    def __init__(self, hosted_zone_id, table_name='records'):
        self.db_name = "{0}.db".format(hosted_zone_id)
        self.connection = sqlite3.connect(self.db_name)
        self.table_name = table_name
        self.table_struct = ['alias', 'weighted', 'weight', 'name', 'value', 'ttl', 'type', 'set_id']

    def close_connection(self):
        self.connection.commit()
        self.connection.close()
        self.connection = None

    def initialize_database(self):
        self._drop_table()
        self._create_table()

    def initialize_delete_db(self):
        self._drop_del_table()
        self._create_del_table()

    def execute_query(self, query, values=[]):
        if DEBUG:
            print(query)
        if self.connection:
            c = self.connection.cursor()
            c.execute(query, values)
            self.connection.commit()

            # Return a list of tuples for selects
            if query.lstrip().upper().startswith('SELECT'):
                result = c.fetchall()
                c.close()
                return result
            else:
                c.close()
        else:
            print('No connection to database')

    def _drop_table(self):
        query = "DROP TABLE IF EXISTS {table_name};".format(table_name=self.table_name)
        self.execute_query(query)

    def _create_table(self):
        query = "CREATE TABLE {table_name}(id INTEGER PRIMARY KEY AUTOINCREMENT, name VARCHAR, ttl INTEGER, alias BOOLEAN, weighted BOOLEAN, value VARCHAR, weight INTEGER, type VARCHAR, set_id VARCHAR)".format(table_name=self.table_name)
        self.execute_query(query)

    def _drop_del_table(self):
        query = "DROP TABLE IF EXISTS {table_name}_to_del;".format(table_name=self.table_name)
        self.execute_query(query)

    def _create_del_table(self):
        query = "CREATE TABLE {table_name}_to_del(id INTEGER PRIMARY KEY AUTOINCREMENT, name VARCHAR, value VARCHAR, type VARCHAR, ttl INTEGER, set_id VARCHAR, weight INTEGER)".format(table_name=self.table_name)
        self.execute_query(query)


    def upload_resource_records(self, resource_records):
        if self.connection:
            c = self.connection.cursor()

            for record in resource_records:
                if DEBUG:
                    print(record)

                if set(self.table_struct) == set(record.keys()):
                    query = "INSERT INTO {table_name} (alias, weighted, weight, name, value, ttl, type, set_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?);".format(table_name=self.table_name)
                    if DEBUG:
                        print(query)

                    c.execute(query, (record['alias'],
                                        record['weighted'],
                                        record['weight'],
                                        record['name'],
                                        record['value'],
                                        record['ttl'],
                                        record['type'],
                                        record['set_id']))
                else:
                    print('Possible malformed input, skipping row')

            self.connection.commit()
            c.close()
        else:
            print('No connection to database')

    def get_parent_records(self, target, final_result=[]):
        query = "SELECT name, value, type, ttl, weighted, weight, set_id FROM {table_name} WHERE value=?;".format(table_name=self.table_name)
        result = self.execute_query(query, (target,))
        if len(result) > 0:
            for row in result:
                if row not in final_result:
                    name, value, rtype, ttl, weighted, weight, set_id = row
                    if weighted == 1:
                        if weight != 0:
                            final_result.append(row)
                            return self.get_parent_records(name, final_result=final_result)
                    else:
                            final_result.append(row)
                            return self.get_parent_records(name, final_result=final_result)
        else:
            return final_result
