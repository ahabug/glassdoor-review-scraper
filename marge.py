import os
import pandas as pd

path = './csv'
files = os.listdir(path)

df1 = pd.read_csv(path + '/' + files[0], encoding='utf_8_sig')

for file in files[1:]:
    df2 = pd.read_csv(path + '/' + file, encoding='utf_8_sig')
    df1 = pd.concat([df1, df2], axis=0, ignore_index=True)

df1 = df1.drop_duplicates()
df1 = df1.reset_index(drop=True)
df1.to_csv(path + '/' + 'total.csv')
