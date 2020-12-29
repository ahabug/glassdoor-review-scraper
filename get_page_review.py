from userAgents import randomUserAgents
import requests
from lxml import html
from company_list import COMPANY_LIST
from logindata import data
import pandas as pd
from proxy_list import random_proxy

session = requests.Session()
# header = randomUserAgents
header = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
}
# proxy = {"https":random_proxy()}
# proxy = {"http":'203.150.128.191:8080'}
login_url1 = 'https://www.glassdoor.com/profile/ajax/loginSecureAjax.htm'
login_url = 'https://www.glassdoor.com/profile/login_input.htm?userOriginHook=HEADER_SIGNIN_LINK'
base_url = 'https://www.glassdoor.com'
cookies = {
    "NmgaWKLjCAZu4ZW6phHbRQ:IVFNO3zsbc94b9r0WR5qgW-qFrwGXv_n-XbBzK8vDoLJ0m00NsE56L12YpSNOBVB9rkhAThNUmJNyUX-AudJ5A:n7DV6nNCC8DS4LRE9Lnm1_YlJ5nSYgDTcGTkYGAZc6E"}


def login():
    login_response = session.post(url=login_url, headers=header, data=data)
    if login_response.status_code == 200:
        print("登录成功！！")
    else:
        print(login_response.status_code)
        print("加油再试一次！！")


def company_url(tree):
    return tree.xpath(
        '//html/body/div[3]/div/div/div/div[1]/div/div[1]/article/div/div[1]/div/div[2]/div/div[1]/a/@href')


def search_company(company):
    search_url = base_url + '/Reviews/' + company.replace(' ', '-') + '-reviews-SRCH_KE0,' + str(len(company)) + '.htm'
    response = requests.get(search_url, headers=header)
    return html.fromstring(response.text)


def company_reviews(company):
    tree = search_company(company)  # 先获取企业搜索页面
    url = company_url(tree)  # 根据页面获取企业链接
    return url


URL_LIST = [
    'company_name',
    'company_url'
]


def main():
    login()
    visited_companies = []
    failed_companies = []
    res = pd.DataFrame([], columns=URL_LIST)
    for company in COMPANY_LIST:
        if company in visited_companies:
            continue
        url = company_reviews(company)
        print(url)
        full_url = base_url + url[0]
        if url:
            visited_companies.append(company)
            df = [[company, full_url]]
            res = res.append(df)
            print(res)
        else:
            failed_companies.append(company)
    print("获取成功的企业：", visited_companies)
    print("获取失败的企业有：", failed_companies)
    print(res)
    res.to_csv("company_list.csv", index=False, encoding='utf-8')

if __name__ == '__main__':
    main()
