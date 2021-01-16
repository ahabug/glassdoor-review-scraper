import json
import logging.config
import time
from multiprocessing.dummy import Pool as ThreadPool

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


def get_driver():
    chrome_options = webdriver.ChromeOptions()
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('log-level=3')
    chrome = webdriver.Chrome(executable_path='./chromedriver.exe', options=chrome_options)
    return chrome


def sign_in(driver, company_url, x):
    logger.info(f'"{x}" thread: Signing in to {username}')
    login_url = 'https://www.glassdoor.com/profile/login_input.htm'
    driver.get(login_url)

    email_field = driver.find_element_by_name('username')
    password_field = driver.find_element_by_name('password')
    submit_btn = driver.find_element_by_xpath('//button[@type="submit"]')

    email_field.send_keys(username)
    password_field.send_keys(password)
    submit_btn.click()
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
    def scrape_featured():
        res = review.find_element_by_class_name('justify-content-between').text
        if 'Featured Review' not in res:
            return 0
        else:
            return 1

    def scrape_covid():
        res = review.find_element_by_class_name('justify-content-between').text
        if 'COVID-19' not in res:
            return 0
        else:
            return 1

    def scrape_anonymous():
        res = review.find_element_by_class_name('authorJobTitle').text
        if 'Anonymous' in res:
            return 1
        else:
            return 0

    def scrape_date():
        return review.find_element_by_class_name('align-items-center').text

    def scrape_time():
        try:
            res = review.find_element_by_class_name('justify-content-between').find_element_by_tag_name(
                'time').get_attribute('datetime')
            res = res.split()[4]
            return res
        except Exception:
            res = np.nan
            return res

    def scrape_headline():
        return review.find_element_by_class_name('reviewLink').text.strip('"')

    def scrape_role():
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

    def scrape_location():
        if 'in' in review.text:
            try:
                res = author.find_element_by_class_name('authorLocation').text
            except Exception:
                res = np.nan
        else:
            res = np.nan
        return res

    def scrape_status():
        try:
            res = author.text.split('-')[0]
            if 'Employee' not in res:
                res = np.nan
        except Exception:
            logger.warning('Failed to scrape employee_status')
            res = np.nan
        return res

    def scrape_contract():
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

    def scrape_years():
        try:
            years = review.find_element_by_class_name('mainText').text
            years = years.split('for')[1]
            return years
        except Exception:
            res = np.nan
            return res

    def scrape_helpful():
        try:
            helpful = review.find_element_by_class_name('helpfulReviews').text
            res = helpful.split()[1].replace('(', '').replace(')', '')
            return res
        except Exception:
            res = 0
        return res

    def scrape_response_date():
        try:
            response = review.find_element_by_class_name('mb-md-sm').text
            print(response)
            response = response.split(' — ')[0]
            return response
        except Exception:
            return np.nan

    def scrape_response_role():
        try:
            response = review.find_element_by_class_name('mb-md-sm').text
            response = response.split(' — ')[1]
            return response
        except Exception:
            return np.nan

    def scrape_response():
        try:
            response = review.find_element_by_class_name('v2__EIReviewDetailsV2__fullWidth')
            response.click()
            response = review.find_elements_by_class_name('v2__EIReviewDetailsV2__isExpanded')[3].text
            print(response)
            return response
        except Exception:
            return np.nan

    def scrape_pros():
        try:
            res = review.find_element_by_class_name('v2__EIReviewDetailsV2__fullWidth')
            res.click()
            res = review.find_element_by_class_name('v2__EIReviewDetailsV2__isExpanded').text
        except Exception:
            res = np.nan
        return res

    def scrape_cons():
        try:
            res = review.find_element_by_class_name('v2__EIReviewDetailsV2__fullWidth')
            res.click()
            res = review.find_elements_by_class_name('v2__EIReviewDetailsV2__isExpanded')[1].text
        except Exception:
            res = np.nan
        return res

    def scrape_advice():
        try:
            res = review.find_element_by_class_name('v2__EIReviewDetailsV2__fullWidth')
            res.click()
            res = review.find_elements_by_class_name('v2__EIReviewDetailsV2__isExpanded')[2].text
        except Exception:
            res = np.nan
        return res

    def scrape_main_rating():
        try:
            res = review.find_element_by_class_name('v2__EIReviewsRatingsStylesV2__ratingNum').text
        except Exception:
            res = np.nan
        return res

    def scrape_work_life_balance():
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

    def scrape_culture_and_values():
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

    def scrape_diversity_inclusion():
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

    def scrape_career_opportunities():
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

    def scrape_comp_and_benefits():
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

    def scrape_senior_management():
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

    def scrape_recommends():
        try:
            res = review.find_element_by_class_name('reviewBodyCell').text
            if 'Recommends' or 'Recommend' in res:
                res = res.split('\n')
                return res[0]
        except Exception:
            return np.nan

    def scrape_outlook():
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

    def scrape_ceo_approval():
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
            return np.nan

    res = pd.DataFrame([], columns=SCHEMA)
    reviews = driver.find_elements_by_class_name('gdReview')
    for review in reviews:
        data = extract_review(review)
        if pd.isnull(data):
            continue
        logger.info(f'"{x}" thread: Scraped data for "{data["headline"]}"({data["date"]})')
        res.loc[idx[0]] = data
        idx[0] = idx[0] + 1
    return res


def more_pages(page, driver, max_pages, x):
    try:
        next_ = driver.find_element_by_class_name('nextButton')
        next_.click()
        logger.info(f'"{x}" thread: Going to page {page[0] + 1}.')
        page[0] = page[0] + 1
        if page[0] < max_pages:
            return True
        else:
            return False
    except Exception:
        return False


def main(x):
    start_time = time.time()
    driver = get_driver()
    company_name = df.iat[x, 0]
    company_url = df.iat[x, 1]
    temp_url = company_url  # the page different from the index page
    logger.info(f'Now we are scraping reviews of No."{x}" company.')
    sign_in(driver, company_url, x)

    page = [1]
    idx = [0]
    res = pd.DataFrame([], columns=SCHEMA)

    if start_from_base:  # if we start from
        reviews_exist = navigate_to_reviews(driver, company_name, company_url, x)
        if not reviews_exist:
            return
    else:
        driver.get(temp_url)
        page[0] = get_current_page(driver)

    logger.info(f'"{x}" thread: Now we are scraping reviews of "{company_name}" from page "{page[0]:,}"')
    max_reviews = get_max_reviews(driver)
    max_pages = int((max_reviews - 1) / 10) + 1
    logger.info(f'"{x}" thread: {max_reviews} English reviews in {max_pages} pages.')
    reviews_df = extract_from_page(driver, idx, x)
    res = res.append(reviews_df)

    while more_pages(page, driver, max_pages, x):
        company_url = driver.current_url
        driver.get(company_url)
        reviews_df = extract_from_page(driver, idx, x)
        res = res.append(reviews_df)

    file_name = company_name + '.csv'
    logger.info(f'"{x}" thread: Writing {len(res)} reviews to file {file_name}.')
    res.to_csv(file_name, index=False, encoding='utf-8')

    end_time = time.time()
    logger.info(f'"{x}" thread: Finished in {end_time - start_time} seconds')
    driver.quit()


def get_company_list():
    return [i for i in range(len(df))]


if __name__ == '__main__':
    pool = ThreadPool()
    pool.map_async(main, get_company_list())
    pool.close()
    pool.join()
