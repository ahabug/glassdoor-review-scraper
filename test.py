import pandas as pd

CSV_FILE_PATH = './company_list.csv'
df = pd.read_csv(CSV_FILE_PATH)


def scrape(x):
    print(x)
    print(df)
    company_name = df.iat[x, 1]
    # company_url = df[x, 1]

    print(company_name)
    # print(company_url)
    # print(company_name)


for i in range(5):
    scrape(i)
