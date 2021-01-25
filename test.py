# This file is used to practice Python programming.
import pandas as pd
company_name = 'abc'
file_path = './csv/' + company_name + '.csv'
print(file_path)

a = 1
b = 2
c = [a, b]
df = pd.DataFrame(c)
df.to_csv(file_path)