import json
import logging.config
import math
import time
from multiprocessing.dummy import Pool as ThreadPool

import requests
import numpy as np
import pandas as pd
from selenium import webdriver
from schema import SCHEMA

CSV_FILE_PATH = './company_list.csv'
df = pd.read_csv(CSV_FILE_PATH)

with open('secret.json') as file:
    d = json.loads(file.read())
    username = d['username']
    password = d['password']

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

logger.addHandler(ch)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(lineno)d :%(filename)s(%(process)d) - %(message)s')
ch.setFormatter(formatter)
logging.getLogger('selenium').setLevel(logging.CRITICAL)

start_from_base = True
failed_company = []
API_KEY = '1ac7dc172b226ea535d1b82f1684f1d2'


def get_driver():
    chrome_options = webdriver.ChromeOptions()
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('log-level=3')
    chrome = webdriver.Chrome(executable_path='./chromedriver.exe', options=chrome_options)
    return chrome


def sign_in(driver, company_url, x):
    logger.info(f'"{x}" thread: Signing in to {username}')
    login_url = 'https://www.glassdoor.com.hk/profile/login_input.htm?userOriginHook=HEADER_SIGNIN_LINK'
    driver.get(login_url)

    email_field = driver.find_element_by_name('username')
    password_field = driver.find_element_by_name('password')
    submit_btn = driver.find_element_by_xpath('//button[@type="submit"]')

    email_field.send_keys(username)
    password_field.send_keys(password)
    submit_btn.click()
    time.sleep(1)
    driver.get(company_url)


def no_reviews():
    return False
    # Todo: Find a company without reviews to test on


def navigate_to_reviews(driver, company_name, company_url, x):
    logger.info(f'"{x}" thread: Navigating to company {company_name} reviews')
    driver.get(company_url)
    if no_reviews():
        logger.info(f'"{x}" thread: No reviews to scrape!')
        return False
    reviews_cell = driver.find_element_by_xpath('//a[@data-label="Reviews"]')
    reviews_path = reviews_cell.get_attribute('href')
    driver.get(reviews_path)
    return True


def get_current_page(driver):
    paging_control = driver.find_element_by_class_name('paginationFooter')
    current = paging_control.text.split()[1].replace(',', '')
    current = int(int(current) / 10)
    return current


def get_max_reviews(driver):
    max_reviews = driver.find_element_by_class_name('common__EIReviewSortBarStyles__sortsHeader')
    max_reviews = max_reviews.find_element_by_xpath('//h2/span/strong').text
    max_reviews = max_reviews.split()[0]
    max_reviews = max_reviews.replace(',', '')
    return int(max_reviews)


def scrape(field, review, author, x):
    def scrape_featured(review):
        res = review.find_element_by_class_name('justify-content-between').text
        if 'Featured Review' not in res:
            return 0
        else:
            return 1

    def scrape_covid(review):
        res = review.find_element_by_class_name('justify-content-between').text
        if 'COVID-19' not in res:
            return 0
        else:
            return 1

    def scrape_anonymous(review):
        res = review.find_element_by_class_name('authorJobTitle').text
        if 'Anonymous' in res:
            return 1
        else:
            return 0

    def scrape_date(review):
        res = review.find_element_by_class_name('align-items-center').find_element_by_class_name('subtle').text
        return res

    def scrape_time(review):
        try:
            res = review.find_element_by_class_name('justify-content-between').find_element_by_tag_name(
                'time').get_attribute('datetime')
            res = res.split()[4]
            return res
        except Exception:
            res = np.nan
            return res

    def scrape_headline(review):
        return review.find_element_by_class_name('reviewLink').text.strip('"')

    def scrape_role(review):
        if 'Anonymous Employee' not in review.text:
            try:
                res = author.find_element_by_class_name('authorJobTitle').text
                if '-' in res:
                    res = res.split('-')[1]
            except Exception:
                logger.warning(f'"{x}" thread: Failed to scrape employee_title')
                res = np.nan
        else:
            res = np.nan
        return res

    def scrape_location(review):
        if 'in' in review.text:
            try:
                res = author.find_element_by_class_name('authorLocation').text
            except Exception:
                res = np.nan
        else:
            res = np.nan
        return res

    def scrape_status(author):
        try:
            res = author.text.split('-')[0]
            if 'Employee' not in res:
                res = np.nan
        except Exception:
            logger.warning('Failed to scrape employee_status')
            res = np.nan
        return res

    def scrape_contract(review):
        try:
            contract = review.find_element_by_class_name('mainText').text
            if 'full-time' in contract:
                return 'full-time'
            elif 'part-time' in contract:
                return 'part-time'
            elif 'contract' in contract:
                return 'contract'
            elif 'intern' in contract:
                return 'intern'
            elif 'freelance' in contract:
                return 'freelance'
        except Exception:
            res = np.nan
            return res

    def scrape_years(review):
        try:
            years = review.find_element_by_class_name('mainText').text
            years = years.split('for')[1]
            return years
        except Exception:
            res = np.nan
            return res

    def scrape_helpful(review):
        try:
            helpful = review.find_element_by_class_name('helpfulReviews').text
            res = helpful.split()[1].replace('(', '').replace(')', '')
            return res
        except Exception:
            res = 0
        return res

    def scrape_response_date(review):
        try:
            response = review.find_element_by_class_name('mb-md-sm').text
            response = response.split(' – ')[0]
            return response
        except Exception:
            return np.nan

    def scrape_response_role(review):
        try:
            response = review.find_element_by_class_name('mb-md-sm').text
            response = response.split(' – ')[1]
            return response
        except Exception:
            return np.nan

    def scrape_response(review):
        try:
            if type(scrape_response_date(review)) == float:  # without response
                response = np.nan
            elif type(scrape_advice(review)) == float:  # with response but without advice
                response = review.find_element_by_class_name('v2__EIReviewDetailsV2__fullWidth')
                response.click()
                response = review.find_elements_by_class_name('v2__EIReviewDetailsV2__isExpanded')[2].text
            else:  # with advice and response
                response = review.find_element_by_class_name('v2__EIReviewDetailsV2__fullWidth')
                response.click()
                response = review.find_elements_by_class_name('v2__EIReviewDetailsV2__isExpanded')[3].text
            return response
        except Exception:
            return np.nan

    def scrape_pros(review):
        try:
            res = review.find_element_by_class_name('v2__EIReviewDetailsV2__fullWidth')
            res.click()
            res = review.find_element_by_class_name('v2__EIReviewDetailsV2__isExpanded').text
        except Exception:
            res = np.nan
        return res

    def scrape_cons(review):
        try:
            res = review.find_element_by_class_name('v2__EIReviewDetailsV2__fullWidth')
            res.click()
            res = review.find_elements_by_class_name('v2__EIReviewDetailsV2__isExpanded')[1].text
        except Exception:
            res = np.nan
        return res

    def scrape_advice(review):
        try:
            res = review.find_elements_by_class_name('v2__EIReviewDetailsV2__fullWidth')[2]
            res.click()
            if 'Advice to Management' in res.text:
                return res.find_element_by_class_name('v2__EIReviewDetailsV2__isExpanded').text
            res = np.nan
        except Exception:
            res = np.nan
        return res

    def scrape_main_rating(review):
        try:
            res = review.find_element_by_class_name('v2__EIReviewsRatingsStylesV2__ratingNum').text
        except Exception:
            res = np.nan
        return res

    def scrape_work_life_balance(review):
        try:
            for i in range(6):
                subratings_name = review.find_elements_by_class_name('minor')[i].get_attribute('textContent')
                if 'Balance' in subratings_name:
                    subratings = review.find_element_by_class_name(
                        'subRatings__SubRatingsStyles__subRatings').find_element_by_tag_name('ul')
                    this_one = subratings.find_elements_by_tag_name('li')[i]
                    res = this_one.find_element_by_class_name('gdBars').get_attribute('title')
                    return res
        except Exception:
            res = np.nan
            return res

    def scrape_culture_and_values(review):
        try:
            for i in range(6):
                subratings_name = review.find_elements_by_class_name('minor')[i].get_attribute('textContent')
                if 'Culture' in subratings_name:
                    subratings = review.find_element_by_class_name(
                        'subRatings__SubRatingsStyles__subRatings').find_element_by_tag_name('ul')
                    this_one = subratings.find_elements_by_tag_name('li')[i]
                    res = this_one.find_element_by_class_name('gdBars').get_attribute('title')
                    return res
        except Exception:
            res = np.nan
            return res

    def scrape_diversity_inclusion(review):
        try:
            for i in range(6):
                subratings_name = review.find_elements_by_class_name('minor')[i].get_attribute('textContent')
                if 'Diversity' in subratings_name:
                    subratings = review.find_element_by_class_name(
                        'subRatings__SubRatingsStyles__subRatings').find_element_by_tag_name('ul')
                    this_one = subratings.find_elements_by_tag_name('li')[i]
                    res = this_one.find_element_by_class_name('gdBars').get_attribute('title')
                    return res
        except Exception:
            res = np.nan
            return res

    def scrape_career_opportunities(review):
        try:
            for i in range(6):
                subratings_name = review.find_elements_by_class_name('minor')[i].get_attribute('textContent')
                if 'Career' in subratings_name:
                    subratings = review.find_element_by_class_name(
                        'subRatings__SubRatingsStyles__subRatings').find_element_by_tag_name('ul')
                    this_one = subratings.find_elements_by_tag_name('li')[i]
                    res = this_one.find_element_by_class_name('gdBars').get_attribute('title')
                    return res
        except Exception:
            res = np.nan
            return res

    def scrape_comp_and_benefits(review):
        try:
            for i in range(6):
                subratings_name = review.find_elements_by_class_name('minor')[i].get_attribute('textContent')
                if 'Compensation' in subratings_name:
                    subratings = review.find_element_by_class_name(
                        'subRatings__SubRatingsStyles__subRatings').find_element_by_tag_name('ul')
                    this_one = subratings.find_elements_by_tag_name('li')[i]
                    res = this_one.find_element_by_class_name('gdBars').get_attribute('title')
                    return res
        except Exception:
            res = np.nan
            return res

    def scrape_senior_management(review):
        try:
            for i in range(6):
                subratings_name = review.find_elements_by_class_name('minor')[i].get_attribute('textContent')
                if 'Senior' in subratings_name:
                    subratings = review.find_element_by_class_name(
                        'subRatings__SubRatingsStyles__subRatings').find_element_by_tag_name('ul')
                    this_one = subratings.find_elements_by_tag_name('li')[i]
                    res = this_one.find_element_by_class_name('gdBars').get_attribute('title')
                    return res
        except Exception:
            res = np.nan
            return res

    def scrape_recommends(review):
        try:
            res = review.find_element_by_class_name('reviewBodyCell').text
            if 'Recommends' or 'Recommend' in res:
                res = res.split('\n')
                return res[0]
        except Exception:
            return np.nan

    def scrape_outlook(review):
        try:
            res = review.find_element_by_class_name('reviewBodyCell').text
            if 'Outlook' in res:
                res = res.split('\n')
                if 'Recommends' or 'Recommend' in res:
                    return res[1]
                else:
                    return res[0]
            return np.nan
        except Exception:
            return np.nan

    def scrape_ceo_approval(review):
        try:
            res = review.find_element_by_class_name('reviewBodyCell').text
            if 'CEO' in res:
                res = res.split('\n')
                if len(res) == 3:
                    return res[2]
                if len(res) == 2:
                    return res[1]
                return res[0]
            return np.nan
        except Exception:
            return np.nan

    funcs = [
        scrape_featured,
        scrape_covid,
        scrape_anonymous,
        scrape_date,
        scrape_time,
        scrape_headline,
        scrape_role,
        scrape_location,
        scrape_status,
        scrape_contract,
        scrape_years,
        scrape_helpful,
        scrape_pros,
        scrape_cons,
        scrape_advice,
        scrape_main_rating,
        scrape_work_life_balance,
        scrape_culture_and_values,
        scrape_diversity_inclusion,
        scrape_career_opportunities,
        scrape_comp_and_benefits,
        scrape_senior_management,
        scrape_recommends,
        scrape_outlook,
        scrape_ceo_approval,
        scrape_response_date,
        scrape_response_role,
        scrape_response
    ]

    fdict = dict((s, f) for (s, f) in zip(SCHEMA, funcs))

    return fdict[field](review)


def extract_from_page(driver, idx, x):
    def extract_review(review):
        try:
            author = review.find_element_by_class_name('authorInfo')
            result = {}
            for field in SCHEMA:
                result[field] = scrape(field, review, author, x)
            assert set(result.keys()) == set(SCHEMA)
            return result
        except Exception:
            logger.warning('Warning!')
            return np.nan

    res = pd.DataFrame([], columns=SCHEMA)
    reviews = driver.find_elements_by_class_name('gdReview')

    for review in reviews:
        data = extract_review(review)
        if pd.isnull(data):
            continue
        logger.info(f'"{x}" thread: Scraped data for "{data["headline"]}"({data["date"]})')
        res.loc[idx] = data
        idx = idx + 1
    return res


def more_pages(page, driver, max_pages, x):
    try:
        next_ = driver.find_element_by_class_name('nextButton')
        next_.click()
        logger.info(f'"{x}" thread: Going to page {page + 1}.')
        if page < max_pages:
            return True  # There are some pages left
        else:
            return False  # Done!
    except Exception:  # We are caught!!!
        return False


def main(x):
    start_time = time.time()
    driver = get_driver()
    company_name = df.iat[x, 0]
    company_url = df.iat[x, 1]
    temp_url = company_url  # the page different from the index page
    logger.info(f'Now we are scraping reviews of No."{x}" company.')
    sign_in(driver, company_url, x)

    page = 1
    idx = 0
    res = pd.DataFrame([], columns=SCHEMA)

    if start_from_base:  # if we start from
        reviews_exist = navigate_to_reviews(driver, company_name, company_url, x)
        if not reviews_exist:
            return
    else:
        driver.get(temp_url)
        page = get_current_page(driver)

    logger.info(f'"{x}" thread: Now we are scraping reviews of "{company_name}" from page "{page}"')
    max_reviews = get_max_reviews(driver)
    max_pages = int((max_reviews - 1) / 10) + 1
    logger.info(f'"{x}" thread: {max_reviews} English reviews in {max_pages} pages.')
    reviews_df = extract_from_page(driver, idx, x)
    res = res.append(reviews_df)

    while more_pages(page, driver, max_pages, x):
        page = page + 1
        company_url = driver.current_url
        driver.get(company_url)
        time.sleep(3)
        reviews_df = extract_from_page(driver, idx, x)
        res = res.append(reviews_df)
        # if page < max_pages:
        #     try:
        #         code = driver.find_element_by_id('recaptcha-token').get_attribute("value")
        #         open_google(code, driver)
        #     except Exception:
        #         pass

    file_path = './csv/' + company_name + '.csv'
    logger.info(f'"{x}" thread: Writing {len(res)} reviews to file {company_name}.csv.')
    res.to_csv(file_path, index=False, encoding='utf-8')
    if len(res) < max_reviews:
        fail = [company_name, page-1]
        failed_company.append(fail)

    end_time = time.time()
    logger.info(f'"{x}" thread: Finished in {end_time - start_time} seconds')
    driver.quit()


def get_company_list():
    return [i for i in range(len(df))]


if __name__ == '__main__':
    main(0)
    # start_time_main = time.time()
    # pool = ThreadPool()
    # pool.map_async(main, get_company_list())
    # pool.close()
    # pool.join()
    # failed_company = pd.DataFrame(failed_company)
    # failed_company.to_csv('failed_company.csv', index=False)
    # end_time_main = time.time()
    # logger.info(f'Finished in {(end_time_main - start_time_main) / 60} minutes')


def open_google(code, driver):
    u1 = f"https://2captcha.com/in.php?key={API_KEY}&method=userrecaptcha&googlekey={code}&pageurl={driver.current_url}&json=1&invisible=1"
    r1 = requests.get(u1)
    rid = r1.json().get("request")
    u2 = f"https://2captcha.com/res.php?key={API_KEY}&action=get&id={int(rid)}&json=1"
    time.sleep(25)
    while True:
        print(u2)
        r2 = requests.get(u2)
        print(r2.json())
        if r2.json().get("status") == 1:
            form_tokon = r2.json().get("request")
            break
        time.sleep(5)
    wirte_tokon_js = f'document.getElementById("g-recaptcha-response").innerHTML="{form_tokon}";'
    submit_js = 'document.getElementById("recaptcha-demo-form").submit();'
    driver.execute_script(wirte_tokon_js)
    time.sleep(1)
    driver.execute_script(submit_js)
