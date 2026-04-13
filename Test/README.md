# Heartbeat Anomaly Detection with Data Stream Tool

A demonstration of the **Data Stream Tool** in action — streaming the PTB Diagnostic ECG Database from CSV into MariaDB, then training a hybrid CNN + BiRNN model to classify normal vs. abnormal heartbeats.

## Overview

This project showcases a full ML pipeline powered by MariaDB as the data backend:

1. **Ingest** — Two raw CSV files (normal & abnormal heartbeats) are loaded, shuffled, and split into train/validation/test tables inside MariaDB using `data_stream_tool`.
2. **Train** — A dual-path neural network (Bidirectional RNN + Dilated Causal CNN) learns temporal patterns in the ECG signals.
3. **Evaluate** — The best model checkpoint is saved and predictions are compared against ground-truth labels.

## Architecture

```
Input (187 time-steps x 1)
        |
   Normalization
      /       \
BiRNN Path     Conv1D Path
     |              |
BiRNN(32)      Conv1D(16, dilation=16)
  Dropout(0.2) Conv1D(32, dilation=32)
BiRNN(16)      GlobalMaxPool1D
      \       /
     Concatenate
        |
    Dense(32, ReLU)
    Dropout(0.2)
    Dense(16, ReLU)
    Dense(1, Sigmoid)
```

- **BiRNN path** captures sequential dependencies across the heartbeat signal
- **Dilated Causal CNN path** captures multi-scale local patterns without future leakage
- Both paths are merged and fed through dense layers for binary classification

## Dataset

[PTB Diagnostic ECG Database](https://physionet.org/content/ptbdb/1.0.0/) — preprocessed into fixed-length time-series segments.

| File                 | Samples | Features | Label     |
|----------------------|---------|----------|-----------|
| `ptbdb_normal.csv`   | 4,046   | 187      | 0 (normal)   |
| `ptbdb_abnormal.csv` | 10,506  | 187      | 1 (abnormal) |

**Split (70 / 20 / 10):**

| Partition  | Approx. Samples |
|------------|-----------------|
| Train      | ~10,186         |
| Validation | ~2,910          |
| Test       | ~1,456          |

## How It Works with Data Stream Tool

```python
from Data_Stream.Data_Stream import data_stream_tool

tool = data_stream_tool("root", "root", "test")

train, val, test = tool.load_files(
    ["ptbdb_normal.csv", "ptbdb_abnormal.csv"],
    ["Train_Dataset", "Validation_Dataset", "Test_Dataset"],
    random=True,
    random_state=42,
    time_steps=True,
    splits=(0.7, 0.2, 0.1)
)

# Data is now in MariaDB — pull it back as DataFrames
x_train, y_train = train.get_dataset()
```

The tool handles concatenation, shuffling, splitting, schema creation, and chunked insertion into MariaDB — all in one call.

## Requirements

- Python 3.7+
- MariaDB Server (localhost:3306)
- Python packages:
  ```
  tensorflow >= 2.x
  mariadb
  pandas
  numpy
  ```

## Usage

```bash
# Make sure MariaDB is running, then:
python Test.py
```

The script will:
1. Create the `test` database and load all three table splits
2. Print the model summary
3. Train for 30 epochs with checkpointing on best `val_accuracy`
4. Print predictions vs. true labels on the first 10 test samples

## Hyperparameters

| Parameter       | Value            |
|-----------------|------------------|
| Optimizer       | Adam             |
| Learning Rate   | 0.00016          |
| Loss            | Binary Crossentropy |
| Batch Size      | 64               |
| Epochs          | 30               |
| Checkpoint      | Best val_accuracy |

## Output

- `heartbeat_model_CBRNN.keras` — saved model weights (best validation accuracy)

## Built With

- [MariaDB](https://mariadb.org/) + [Data Stream Tool](../Data_Stream.py) — database-backed data ingestion and splitting
- [TensorFlow / Keras](https://www.tensorflow.org/) — model training
- [PTB Diagnostic ECG Database](https://physionet.org/content/ptbdb/1.0.0/) — heartbeat data
