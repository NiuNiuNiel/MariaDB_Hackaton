from Data_Stream.Data_Stream import data_stream_tool

tool = data_stream_tool("root","root","test")
train, val, test = tool.load_files(["ptbdb_normal.csv","ptbdb_abnormal.csv"],
                      ["Train_Dataset", "Validation_Dataset", "Test_Dataset"],
                      random = True,
                      random_state = 42,
                      time_steps=True,
                      splits = (0.7,0.2,0.1))

# train = tool.load_files(["ptbdb_normal.csv","ptbdb_abnormal.csv"],
#                       "Train_Dataset",
#                       random = True,
#                       random_state = 42,
#                       time_steps=True)

print(train.table_name)
print(val.table_name)
print(test.table_name)

tool.show_exist()
x_train, y_train = tool.load_exist("train_dataset").get_dataset()
print(x_train, y_train)