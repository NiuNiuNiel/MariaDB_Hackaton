import mariadb
import pandas as pd
import gc
import warnings

class data_stream_tool:
    def __init__(self, user, password, database):
        self.config = {
            "host": "127.0.0.1",
            "port": 3306,
            "user": user,
            "password": password,
        }
        try:
            self.conn = mariadb.connect(**self.config)
            self.cursor = self.conn.cursor()
        except Exception as e:
            raise e
        self.cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database};")
        self.cursor.execute(f"USE {database};")
        self.config["database"] = database

    def map_dtype(self,pandas_dtype):
        if pd.api.types.is_float_dtype(pandas_dtype):
            return "FLOAT"
        elif pd.api.types.is_integer_dtype(pandas_dtype):
            return "INT"
        else:
            return "VARCHAR(255)"

    def load_files(self, files, table_names, time_steps = False, splits = False, random = False, random_state = 42):
        import os
        df_list = []

        for file in files:
            file_path = os.path.abspath(file)
            file_type = file.split(".")[-1].lower()

            if file_type == "csv":
                df_list.append(pd.read_csv(file_path, header = None if time_steps else "infer"))
            elif file_type == "json":
                df_list.append(pd.read_json(file_path))
            elif file_type == "tsv":
                df_list.append(pd.read_csv(file_path, sep = "\t", header = None if time_steps else "infer"))
            else:
                raise TypeError
        try:
            df = pd.concat(df_list, ignore_index = True)
        except Exception as e:
            raise e

        del df_list
        gc.collect()

        if time_steps:
            df.rename(columns={df.columns[-1]: "Label"}, inplace=True)
            table_str = f"({','.join([f'`{i}` {self.map_dtype(df[i].dtype)}' for i in df.columns[:-1]])}, Label FLOAT);"
        else:
            table_str = f"({','.join([f'`{i}` {self.map_dtype(df[i].dtype)}' for i in df.columns])});"

        if random:
            df = df.sample(frac=1, random_state=random_state).reset_index(drop=True)

        if splits:
            import math

            if not isinstance(splits, (tuple, list)):
                raise TypeError("split must be a list or tuple")

            split_len = len(splits)
            if split_len <= 1:
                raise ValueError("Insufficient split amounts. Must provide at least 2 portions.")

            if table_names:
                table_names_len = len(table_names)
                if table_names_len <= 1:
                    raise ValueError("Insufficient table names. Must provide at least 2 table names.")

                if split_len != table_names_len:
                    raise ValueError(
                        f"Mismatch: You provided {split_len} split ratios but {table_names_len} table names.")

            if not math.isclose(sum(splits), 1.0):
                raise ValueError(f"Invalid split ratio. Your values sum to {sum(splits)}, but must equal 1.0")

            total_rows = len(df)
            splits_tables = []
            start_index = 0

            for i, split in enumerate(splits):
                table_name = table_names[i]
                if i == len(splits) - 1:
                    split_df = df.iloc[start_index:]
                    splits_tables.append(Table(table_name,self.conn))
                else:
                    end_index = start_index + int(total_rows * split)
                    split_df = df.iloc[start_index:end_index]
                    splits_tables.append(Table(table_name,self.conn))
                    start_index = end_index

                placeholders = ", ".join(["%s"] * len(split_df.columns))
                sql = f"INSERT INTO `{table_name}` VALUES ({placeholders});"
                split_df = split_df.astype(object).where(pd.notna(split_df), None)
                chunk_size = 5000

                try:
                    self.cursor.execute(f"CREATE TABLE IF NOT EXISTS `{table_name}` " + table_str)
                    for chunk in range(0,len(split_df),chunk_size):
                        chunk_data = list(split_df.iloc[chunk:chunk + chunk_size].itertuples(index=False, name=None))
                        self.cursor.executemany(sql, chunk_data)
                except Exception as e:
                    self.conn.rollback()
                    raise e

            self.conn.commit()

            # discard ram memory
            print("Purging DataFrame from RAM...")
            del df
            del split_df
            gc.collect()

            return splits_tables
        else:
            table_name = table_names[0] if isinstance(table_names, list) else table_names
            placeholders = ", ".join(["%s"] * len(df.columns))
            sql = f"INSERT INTO `{table_name}` VALUES ({placeholders});"
            df = df.astype(object).where(pd.notna(df), None)
            chunk_size = 5000

            try:
                self.cursor.execute(f"CREATE TABLE IF NOT EXISTS `{table_name}` " + table_str)
                for chunk in range(0,len(df),chunk_size):
                    chunk_data = list(df.iloc[chunk:chunk + chunk_size].itertuples(index=False, name=None))
                    self.cursor.executemany(sql, chunk_data)
            except Exception as e:
                self.conn.rollback()
                raise e

            self.conn.commit()

            # discard ram memory
            print("Purging DataFrame from RAM...")
            del df
            gc.collect()

            return Table(table_name,self.conn)

    def load_exist(self, table_name):
        return Table(table_name,self.conn)

    def show_exist(self):
        self.cursor.execute(f"SHOW TABLES;")
        print(pd.DataFrame(self.cursor.fetchall(), columns = ["Existing Tables"]))

    def update_table(self,table_name,dataframe):
        pass


class Table:
    def __init__(self, table_name, conn):
        self.table_name = table_name
        self.conn = conn

    def get_dataset(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)

            df = pd.read_sql(f"SELECT * FROM `{self.table_name}`;", con=self.conn)

        return df.iloc[:, :-1], df.iloc[:, -1]
