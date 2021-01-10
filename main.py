import json
import logging.config
import time
import urllib
import selenium
import numpy as np
import pandas as pd
import datetime as dt
from argparse import ArgumentParser
from selenium import webdriver as wd
from schema import SCHEMA
from multiprocessing.dummy import Pool as ThreadPool

start = time.time()
# 设定默认链接，以Shopee为例
# DEFAULT_URL = 'https://www.glassdoor.com/Overview/Working-at-Amazon-EI_IE6036.11,17.htm'
DEFAULT_URL = 'https://www.glassdoor.com/Overview/Working-at-GitHub-EI_IE671945.11,17.htm'
# DEFAULT_URL = 'https://www.glassdoor.com/Overview/Working-at-Shopee-EI_IE1263091.11,17.htm'
parser = ArgumentParser()
parser.add_argument('-u', '--url', help='URL of the company\'s Glassdoor landing page.', default=DEFAULT_URL)
parser.add_argument('-f', '--file', default='glassdoor_ratings.csv', help='Output file.')
parser.add_argument('--headless', action='store_true', help='Run Chrome in headless mode.')
parser.add_argument('--username', help='Email address used to sign in to GD.')
parser.add_argument('-p', '--password', help='Password to sign in to GD.')
parser.add_argument('-c', '--credentials', help='Credentials file')
parser.add_argument('--start_from_url', action='store_true', help='Start scraping from the passed URL.')
args = parser.parse_args()
# args.start_from_url = 'https://www.glassdoor.com/Reviews/GitHub-Reviews-E671945_P5.htm'
# args.url = 'https://www.glassdoor.com/Reviews/GitHub-Reviews-E671945_P5.htm'

if args.credentials:
    with open(args.credentials) as f:
        d = json.loads(f.read())
        args.username = d['username']
        args.password = d['password']
else:
    try:
        with open('secret.json') as f:
            d = json.loads(f.read())
            args.username = d['username']
            args.password = d['password']
    except FileNotFoundError:
        msg = 'Please provide Glassdoor credentials. Credentials can be provided as a secret.json file in the working ' \
              'directory, or passed at the command line using the --username and --password flags. '
        raise Exception(msg)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(lineno)d :%(filename)s(%(process)d) - %(message)s')
ch.setFormatter(formatter)

logging.getLogger('selenium').setLevel(logging.CRITICAL)
logging.getLogger('selenium').setLevel(logging.CRITICAL)


def scrape(field, review, author):
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
        return review.find_element_by_class_name('align-items-center').text

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
                logger.warning('Failed to scrape employee_title')
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

    def scrape_status(review):
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
            print(response)
            response = response.split(' — ')[0]
            return response
        except selenium.common.exceptions.NoSuchElementException:
            return np.nan

    def scrape_response_role(review):
        try:
            response = review.find_element_by_class_name('mb-md-sm').text
            response = response.split(' — ')[1]
            return response
        except Exception:
            return np.nan

    def scrape_response(review):
        try:
            response = review.find_element_by_class_name('v2__EIReviewDetailsV2__fullWidth')
            response.click()
            response = review.find_elements_by_class_name('v2__EIReviewDetailsV2__isExpanded')[3].text
            print(response)
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
            res = review.find_element_by_class_name('v2__EIReviewDetailsV2__fullWidth')
            res.click()
            res = review.find_elements_by_class_name('v2__EIReviewDetailsV2__isExpanded')[2].text
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
        except:
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
        except:
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
        except:
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


def get_max_reviews():
    max_reviews = browser.find_element_by_class_name('common__EIReviewSortBarStyles__sortsHeader')
    max_reviews = max_reviews.find_element_by_xpath('//h2/span/strong').text
    max_reviews = max_reviews.split()[0]
    max_reviews = max_reviews.replace(',', '')
    return int(max_reviews)


def extract_from_page():
    def extract_review(review):
        try:
            author = review.find_element_by_class_name('authorInfo')
            res = {}
            for field in SCHEMA:
                res[field] = scrape(field, review, author)
            assert set(res.keys()) == set(SCHEMA)
            return res
        except Exception:
            return np.nan

    res = pd.DataFrame([], columns=SCHEMA)
    reviews = browser.find_elements_by_class_name('gdReview')

    for review in reviews:
        data = extract_review(review)
        if pd.isnull(data):
            continue
        logger.info(f'Scraped data for "{data["headline"]}"({data["date"]})')
        res.loc[idx[0]] = data
        idx[0] = idx[0] + 1

    return res


def no_reviews():
    return False
    # TODO: Find a company with no reviews to test on


def navigate_to_reviews():
    company_name = DEFAULT_URL.split('-')[2]
    logger.info(f'Navigating to company {company_name} reviews')
    browser.get(args.url)

    if no_reviews():
        logger.info('No reviews to scrape. Bailing!')
        return False

    reviews_cell = browser.find_element_by_xpath('//a[@data-label="Reviews"]')
    reviews_path = reviews_cell.get_attribute('href')
    browser.get(reviews_path)
    return True


def sign_in():
    logger.info(f'Signing in to {args.username}')
    url = 'https://www.glassdoor.com/profile/login_input.htm'
    browser.get(url)

    email_field = browser.find_element_by_name('username')
    password_field = browser.find_element_by_name('password')
    submit_btn = browser.find_element_by_xpath('//button[@type="submit"]')

    email_field.send_keys(args.username)
    password_field.send_keys(args.password)
    submit_btn.click()
    browser.get(args.url)


def get_browser():
    chrome_options = wd.ChromeOptions()
    if args.headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('log-level=3')
    browser = wd.Chrome(executable_path='./chromedriver.exe', options=chrome_options)
    return browser


def get_current_page():
    logger.info('Getting current page number')
    paging_control = browser.find_element_by_class_name('paginationFooter')
    current = paging_control.text.split()[1].replace(',', '')
    current = int(int(current) / 10)
    return current


def more_pages(max_pages):
    try:
        next_ = browser.find_element_by_class_name('nextButton')
        next_.click()
        logger.info(f'Going to page {page[0] + 1}')
        page[0] = page[0] + 1
        if page[0] < max_pages:
            return True
        else:
            return False
    except Exception:
        return False

browser = get_browser()
page = [1]
idx = [0]

def main():
    res = pd.DataFrame([], columns=SCHEMA)
    sign_in()

    if not args.start_from_url:
        reviews_exist = navigate_to_reviews()
        if not reviews_exist:
            return
    else:
        browser.get(args.url)
        page[0] = get_current_page()
        logger.info(f'Starting from page {page[0]:,}.')

    max_reviews = get_max_reviews()
    max_pages = int((max_reviews - 1) / 10) + 1

    logger.info(f'{max_reviews} English reviews in {max_pages} pages.')
    reviews_df = extract_from_page()
    res = res.append(reviews_df)

    while more_pages(max_pages):
        args.url = browser.current_url
        browser.get(args.url)
        reviews_df = extract_from_page()
        res = res.append(reviews_df)

    logger.info(f'Writing {len(res)} reviews to file {args.file}')
    res.to_csv(args.file, index=False, encoding='utf-8')

    end = time.time()
    logger.info(f'Finished in {end - start} seconds')
    browser.quit()


if __name__ == '__main__':
    main()
    # pool = ThreadPool()
    # pool.map(main())
    # pool.close() pool.join()
