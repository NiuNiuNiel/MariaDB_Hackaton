# Data Stream Tool

A Python utility for streaming and managing datasets directly into MariaDB. Built for fast, flexible data ingestion with built-in support for train/test splitting — ideal for ML pipelines backed by a relational database.

## Features

- **Multi-format ingestion** — Load CSV, JSON, and TSV files into MariaDB tables in a single call
- **Automatic schema inference** — Column types (`FLOAT`, `INT`, `VARCHAR`) are mapped from pandas dtypes
- **Train/test/validation splitting** — Split data by ratio and load each partition into its own table
- **Shuffling** — Optionally randomize row order with a reproducible seed before splitting
- **Time-series mode** — Treats the last column as the label for time-step datasets (headerless files)
- **Chunked inserts** — Data is inserted in batches of 5,000 rows to handle large files without memory issues
- **Table handles** — Returns lightweight `Table` objects for easy downstream querying
- **Raw query execution** — Run arbitrary SQL directly via `execute_query`
- **Column & row management** — Drop columns or delete rows from a `Table` with structured helpers
- **Partial data retrieval** — Fetch only specific columns by name or position with `get_partial`
- **Flexible label selection** — Specify the label column by name or index when retrieving data

## Requirements

- Python 3.7+
- MariaDB Server (running on `localhost:3306`)
- Python packages:
  ```
  mariadb
  pandas
  ```

## Quick Start

```python
from Data_Stream import data_stream_tool, Table

# Connect and create/use a database
ds = data_stream_tool(user="root", password="yourpassword", database="ml_data")

# Load a single CSV into a table
table = ds.load_files(
    files=["dataset.csv"],
    table_names="my_table"
)

# Load and split into train/test (80/20)
train, test = ds.load_files(
    files=["dataset.csv"],
    table_names=["train", "test"],
    splits=(0.8, 0.2),
    random=True
)

# Retrieve data as pandas DataFrames
X_train, y_train = train.get_dataset()
X_test, y_test = test.get_dataset()
```

## API Reference

### `data_stream_tool(user, password, database)`

Creates a connection to MariaDB and initializes the target database.

---

### `load_files(files, table_names, time_steps=False, splits=False, random=False, random_state=42)`

Loads one or more files into MariaDB, optionally splitting into multiple tables.

| Parameter      | Type              | Description                                                        |
|----------------|-------------------|--------------------------------------------------------------------|
| `files`        | `list[str]`       | Paths to CSV, JSON, or TSV files to concatenate and load           |
| `table_names`  | `str` or `list`   | Target table name(s). Provide a list when using `splits`           |
| `time_steps`   | `bool`            | If `True`, reads files without headers and labels the last column  |
| `splits`       | `tuple` or `list` | Split ratios that must sum to 1.0 (e.g., `(0.7, 0.15, 0.15)`)    |
| `random`       | `bool`            | Shuffle rows before splitting                                      |
| `random_state` | `int`             | Seed for reproducible shuffling (default: `42`)                    |

**Returns:** A single `Table` object, or a list of `Table` objects when using splits.

---

### `load_exist(table_name)`

Returns a `Table` handle for an existing table in the database.

```python
table = ds.load_exist("my_existing_table")
```

---

### `show_exist()`

Prints all tables in the current database.

---

### `execute_query(query)`

Executes an arbitrary SQL query and returns the results. Commits automatically on success and rolls back on failure.

```python
results = ds.execute_query("SELECT COUNT(*) FROM my_table;")
```

**Returns:** A list of tuples containing the query results.

---

## Table Methods

`Table` objects are returned by `load_files` and `load_exist`. They provide methods for querying and modifying the underlying MariaDB table.

---

### `Table.get_dataset(label_name=None, label_loc=None)`

Fetches the entire table and returns it as a feature/label split.

| Parameter    | Type           | Description                                                             |
|--------------|----------------|-------------------------------------------------------------------------|
| `label_name` | `str` or `list` | Name(s) of the label column(s). Takes precedence over `label_loc`      |
| `label_loc`  | `int` or `list` | Index position(s) of the label column(s)                               |

If neither parameter is provided, the last column is used as the label by default.

**Returns:** `(X, y)` as pandas DataFrames/Series.

```python
# Default — last column is label
X, y = table.get_dataset()

# By column name
X, y = table.get_dataset(label_name="target")

# By column index
X, y = table.get_dataset(label_loc=0)
```

---

### `Table.get_partial(location, columns="index", label_name=None, label_loc=None)`

Fetches only a subset of columns from the table.

| Parameter    | Type            | Description                                                                                      |
|--------------|-----------------|--------------------------------------------------------------------------------------------------|
| `location`   | `list`          | Column positions (when `columns="index"`) or column names (when `columns="name"`)               |
| `columns`    | `str`           | `"index"` to select by ordinal position, `"name"` to select by column name (default: `"index"`) |
| `label_name` | `str` or `list` | Name(s) of the label column(s) within the selected subset                                        |
| `label_loc`  | `int` or `list` | Index position(s) of the label column(s) within the selected subset                              |

**Returns:** `(X, y)` as pandas DataFrames/Series.

```python
# Select columns by position (1-based ordinal index in the DB)
X, y = table.get_partial([1, 2, 3])

# Select columns by name
X, y = table.get_partial(["age", "income", "target"], columns="name", label_name="target")
```

---

### `Table.drop_column(columns)`

Permanently drops one or more columns from the table.

```python
# Drop a single column
table.drop_column(["unwanted_col"])

# Drop multiple columns
table.drop_column(["col1", "col2", "col3"])
```

---

### `Table.delete_row(and_condition=None, or_condition=None)`

Deletes rows matching the given conditions. At least one condition must be provided.

| Parameter      | Type   | Description                                          |
|----------------|--------|------------------------------------------------------|
| `and_condition` | `dict` | `{"col": value}` pairs joined with `AND`            |
| `or_condition`  | `dict` | `{"col": value}` pairs joined with `OR`             |

Both conditions can be provided together; they are combined with `AND` at the top level.

```python
# Delete rows where status = 'inactive' AND region = 'EU'
table.delete_row(and_condition={"status": "inactive", "region": "EU"})

# Delete rows where score = 0 OR label = -1
table.delete_row(or_condition={"score": 0, "label": -1})

# Combine both
table.delete_row(
    and_condition={"region": "EU"},
    or_condition={"score": 0, "label": -1}
)
```

---

## Examples

### Time-Series Data

```python
train, test = ds.load_files(
    files=["sensor_data.csv"],
    table_names=["train", "test"],
    time_steps=True,
    splits=(0.8, 0.2),
    random=True
)
```

### Three-Way Split (Train / Validation / Test)

```python
train, val, test = ds.load_files(
    files=["dataset.csv"],
    table_names=["train", "val", "test"],
    splits=(0.7, 0.15, 0.15),
    random=True,
    random_state=0
)
```

### Cleaning a Table After Loading

```python
table = ds.load_exist("my_table")

# Remove irrelevant columns
table.drop_column(["id", "timestamp"])

# Remove corrupt or placeholder rows
table.delete_row(or_condition={"label": -1, "feature_1": None})

# Fetch cleaned data
X, y = table.get_dataset(label_name="label")
```

### Running a Custom Query

```python
results = ds.execute_query("""
    SELECT label, COUNT(*) as count
    FROM my_table
    GROUP BY label
    ORDER BY count DESC;
""")
```

---

## Built With

- [MariaDB](https://mariadb.org/) — Open-source relational database
- [pandas](https://pandas.pydata.org/) — Data manipulation library
- [MariaDB Connector/Python](https://mariadb.com/docs/connectors/connector-python/) — Native Python driver
