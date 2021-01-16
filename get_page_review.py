import requests
import pandas as pd
import numpy as np
from lxml import html
from logindata import data
from proxy_list import random_proxy
from company_list import COMPANY_LIST
from userAgents import randomUserAgents

session = requests.Session()
# header = randomUserAgents()
header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'}
# proxy = {"https":random_proxy()}
# proxy = {"http":'203.150.128.191:8080'}
login_url = 'https://www.glassdoor.com/profile/login_input.htm?userOriginHook=HEADER_SIGNIN_LINK'
base_url = 'https://www.glassdoor.com'
# base_url = 'https://www.glassdoor.com/Reviews/company-reviews.htm?suggestCount=0&suggestChosen=false&clickSource=searchBtn&typedKeyword='
cookies = {"8-EzOJuOxVdw3W4fBw-Ifw:fi_6fLPaX0es4SH8_uHtZ0fj9I9vLrStU98Pmm1HWdNFDXFU2ubkc9paiIcTxO1lKLiw_yvRBOGf8FOLaQHzVA:Th2M5KiBgIIoZqVzLSE6jisL5GVrIuyd-xLIlsl16QE"}

def login():
    login_response = session.post(url=login_url, headers=header, data=data)
    if int(login_response.status_code/200) == 1:
        print("登录成功！！")
    else:
        print(login_response.status_code)
        print("加油再试一次！！")

def company_reviews(company):
    search_url = base_url + company.replace(' ', '-') + '-reviews-SRCH_KE0,' + str(len(company)) + '.htm'
    response = requests.get(search_url, headers=header)
    tree = html.fromstring(response.text)
    if '-reviews-SRCH_KE0' in response.url:
        url = tree.xpath('//*[@id="MainCol"]/div/div[1]/div/div[1]/div/div[1]/a/@href') # png
    else: # redirect
        url = tree.xpath('//*[@id="EmpHeroAndEmpInfo"]/div[3]/div[1]/a/@href') # png
    return url


def main():
    login()
    visited_companies = []
    failed_companies = []
    res = pd.DataFrame([])
    for company in COMPANY_LIST:
        if company in visited_companies:
            continue
        url = company_reviews(company)
        full_url = base_url + url[0]
        if url:
            visited_companies.append(company)
            df = [[company, full_url]]
            res = res.append(df)
        else:
            failed_companies.append(company)
    print("获取成功的企业：", visited_companies)
    print("获取失败的企业有：", failed_companies)
    res.to_csv("company_list.csv", index=False, encoding='utf-8')


if __name__ == '__main__':
    main()