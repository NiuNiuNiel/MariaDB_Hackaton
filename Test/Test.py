from Data_Stream.Data_Stream import data_stream_tool
import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.callbacks import ModelCheckpoint
import numpy as np
import gc

tool = data_stream_tool("root","root","test")
train, val, test = tool.load_files(["ptbdb_normal.csv","ptbdb_abnormal.csv"],
                      ["Train_Dataset", "Validation_Dataset", "Test_Dataset"],
                      random = True,
                      random_state = 42,
                      time_steps=True,
                      splits = (0.7,0.2,0.1))

tool.show_exist()

x_train, y_train = train.get_dataset()

norm_layer = layers.Normalization(axis=-1)
X_train_3d = np.expand_dims(x_train, axis=-1)
norm_layer.adapt(X_train_3d)

del x_train, y_train
gc.collect()

# _____INPUT LAYER______
input_node = layers.Input(shape=(None,1))
x = norm_layer(input_node)

# _____HIDDEN LAYER_____
path_rnn = layers.Bidirectional(layers.SimpleRNN(32, return_sequences=True))(x)
path_conv = layers.Dropout(0.2)(path_rnn)
path_rnn = layers.Bidirectional(layers.SimpleRNN(16, return_sequences=False))(path_rnn)

path_conv = layers.Conv1D(filters=16, kernel_size=4, dilation_rate=16, padding='causal', activation='relu')(x)
path_conv = layers.Conv1D(filters=32, kernel_size=4, dilation_rate=32, padding='causal', activation='relu')(path_conv)
path_conv = layers.GlobalMaxPooling1D()(path_conv)

merged = layers.Concatenate()([path_rnn, path_conv])

# _____OUTPUT LAYER_____
z = layers.Dense(32, activation='relu')(merged)
z = layers.Dropout(0.2)(z)
z = layers.Dense(16, activation='relu')(z)
output = layers.Dense(1, activation='sigmoid')(z)

model = models.Model(inputs=input_node, outputs=output)

model.summary()

optimizer = tf.keras.optimizers.Adam(learning_rate=0.00016)

model.compile(
    optimizer=optimizer,
    loss='binary_crossentropy',
    metrics=['accuracy']
)

checkpoint = ModelCheckpoint(
    filepath='heartbeat_model_CBRNN.keras',
    monitor='val_accuracy',
    save_best_only=True,
    mode='max',
    verbose=1
)

BATCH_SIZE = 64

train_dataset = tf.data.Dataset.from_tensor_slices(train.get_dataset())
train_dataset = train_dataset.shuffle(buffer_size=1000).batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)


val_dataset = tf.data.Dataset.from_tensor_slices(val.get_dataset())
val_dataset = val_dataset.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

history = model.fit(
    train_dataset,
    epochs=30,
    validation_data=val_dataset,
    callbacks=checkpoint
)

print("Finish Training")

x_test, y_test = test.get_dataset()

print("Predictions:\n",model.predict(x_test.iloc[:10,:]))
print("True Labels:\n",y_test.iloc[:10])