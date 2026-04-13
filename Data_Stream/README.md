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

### `load_files(files, table_names, time_steps=False, splits=False, random=False, random_state=42)`

| Parameter      | Type              | Description                                                        |
|----------------|-------------------|--------------------------------------------------------------------|
| `files`        | `list[str]`       | Paths to CSV, JSON, or TSV files to concatenate and load           |
| `table_names`  | `str` or `list`   | Target table name(s). Provide a list when using `splits`           |
| `time_steps`   | `bool`            | If `True`, reads files without headers and labels the last column  |
| `splits`       | `tuple` or `list` | Split ratios that must sum to 1.0 (e.g., `(0.7, 0.15, 0.15)`)    |
| `random`       | `bool`            | Shuffle rows before splitting                                      |
| `random_state` | `int`             | Seed for reproducible shuffling                                    |

**Returns:** A `Table` object, or a list of `Table` objects when using splits.

### `load_exist(table_name)`

Returns a `Table` handle for an existing table in the database.

### `show_exist()`

Prints all tables in the current database.

### `Table.get_dataset()`

Returns `(X, y)` where `X` is all columns except the last, and `y` is the last column — ready for model training.

## Example: Time-Series Data

```python
train, test = ds.load_files(
    files=["sensor_data.csv"],
    table_names=["train", "test"],
    time_steps=True,
    splits=(0.8, 0.2),
    random=True
)
```

## Built With

- [MariaDB](https://mariadb.org/) — Open-source relational database
- [pandas](https://pandas.pydata.org/) — Data manipulation library
- [MariaDB Connector/Python](https://mariadb.com/docs/connectors/connector-python/) — Native Python driver
