import datetime as dt
import json
import logging.config
import time
import urllib
from argparse import ArgumentParser
import numpy as np
import pandas as pd
import selenium
from selenium import webdriver as wd
from schema import SCHEMA
from url_list import URL_LIST

start = time.time()
# 设定默认链接，以airbnb为例
DEFAULT_URL = 'https://www.glassdoor.com/Overview/Working-at-Airbnb-EI_IE391850.11,17.htm'
parser = ArgumentParser()
parser.add_argument('-u', '--url', help='URL of the company\'s Glassdoor landing page.', default=DEFAULT_URL)
parser.add_argument('-f', '--file', default='glassdoor_ratings.csv', help='Output file.')
parser.add_argument('--headless', action='store_true', help='Run Chrome in headless mode.')
parser.add_argument('--username', help='Email address used to sign in to GD.')
parser.add_argument('-p', '--password', help='Password to sign in to GD.')
parser.add_argument('-c', '--credentials', help='Credentials file')
parser.add_argument('-l', '--limit', default=25, action='store', type=int, help='Max reviews to scrape')
parser.add_argument('--start_from_url', action='store_true', help='Start scraping from the passed URL.')
parser.add_argument('--max_date', help='Latest review date to scrape. Only use this option with --start_from_url.\
    You also must have sorted Glassdoor reviews ASCENDING by date.', type=lambda s: dt.datetime.strptime(s, "%Y-%m-%d"))
parser.add_argument('--min_date', help='Earliest review date to scrape. Only use this option with --start_from_url.\
    You also must have sorted Glassdoor reviews DESCENDING by date.',
                    type=lambda s: dt.datetime.strptime(s, "%Y-%m-%d"))
args = parser.parse_args()

if not args.start_from_url and (args.max_date or args.min_date):
    raise Exception('Invalid argument combination: No starting url passed, but max/min date specified.')
elif args.max_date and args.min_date:
    raise Exception('Invalid argument combination: Both min_date and max_date specified.')

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
            res = review.find_element_by_class_name('justify-content-between').find_element_by_tag_name('time').get_attribute('datetime')
            res = res.split()[4]
            return res
        except Exception:
            res = np.nan
            return res

    def scrape_headline(review):
        return review.find_element_by_class_name('summary').text.strip('"')

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
            helpful = review.find_element_by_class_name('helpfulCount')
            res = helpful[helpful.find('(') + 1: -1]
        except Exception:
            res = 0
        return res

    def scrape_pros(review):
        try:
            res = review.find_element_by_class_name('v2__EIReviewDetailsV2__isExpanded').text
        except Exception:
            res = np.nan
        return res

    def scrape_cons(review):
        try:
            res = review.find_elements_by_class_name('v2__EIReviewDetailsV2__isExpanded')[1].text
        except Exception:
            res = np.nan
        return res

    def scrape_advice(review):
        try:
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
        scrape_ceo_approval
    ]

    fdict = dict((s, f) for (s, f) in zip(SCHEMA, funcs))

    return fdict[field](review)


def extract_from_page():
    def extract_review(review):
        author = review.find_element_by_class_name('authorInfo')
        res = {}
        for field in SCHEMA:
            res[field] = scrape(field, review, author)
        assert set(res.keys()) == set(SCHEMA)
        return res

    logger.info(f'Extracting reviews from page {page[0]}')

    res = pd.DataFrame([], columns=SCHEMA)

    reviews = browser.find_elements_by_class_name('gdReview')

    logger.info(f'Found {len(reviews)} reviews on page {page[0]}')

    for review in reviews:
        data = extract_review(review)
        logger.info(f'Scraped data for "{data["headline"]}"({data["date"]})')
        res.loc[idx[0]] = data
        idx[0] = idx[0] + 1

    if args.max_date and (pd.to_datetime(res['date']).max() > args.max_date) or args.min_date and (
            pd.to_datetime(res['date']).min() < args.min_date):
        logger.info('Date limit reached, ending process')
        date_limit_reached[0] = True

    return res


def more_pages():
    try:
        # paging_control = browser.find_element_by_class_name('pagingControls')
        next_ = browser.find_element_by_class_name('nextButton')
        next_.find_element_by_tag_name('a')
        return True
    except selenium.common.exceptions.NoSuchElementException:
        return False


def go_to_next_page():
    logger.info(f'Going to page {page[0] + 1}')
    # paging_control = browser.find_element_by_class_name('pagingControls')
    next_ = browser.find_element_by_class_name('nextButton').find_element_by_tag_name('a')
    browser.get(next_.get_attribute('href'))
    time.sleep(1)
    page[0] = page[0] + 1


def no_reviews():
    return False
    # TODO: Find a company with no reviews to test on


def navigate_to_reviews():
    logger.info('Navigating to company reviews')

    browser.get(args.url)
    time.sleep(1)

    if no_reviews():
        logger.info('No reviews to scrape. Bailing!')
        return False

    reviews_cell = browser.find_element_by_xpath('//a[@data-label="Reviews"]')
    reviews_path = reviews_cell.get_attribute('href')

    # reviews_path = driver.current_url.replace('Overview','Reviews')
    browser.get(reviews_path)
    time.sleep(1)
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

    time.sleep(3)
    browser.get(args.url)


def get_browser():
    logger.info('Configuring browser')
    chrome_options = wd.ChromeOptions()
    if args.headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('log-level=3')
    browser = wd.Chrome(executable_path='./chromedriver.exe', options=chrome_options)
    return browser


def get_current_page():
    logger.info('Getting current page number')
    paging_control = browser.find_element_by_class_name('pagingControls')
    current = int(paging_control.find_element_by_xpath('//ul//li[contains(concat(\' \',normalize-space(@class),\' \'),\' current \')]\
        //span[contains(concat(\' \',normalize-space(@class),\' \'),\' disabled \')]').text.replace(',', ''))
    return current


def verify_date_sorting():
    logger.info('Date limit specified, verifying date sorting')
    ascending = urllib.parse.parse_qs(args.url)['sort.ascending'] == ['true']

    if args.min_date and ascending:
        raise Exception('min_date required reviews to be sorted DESCENDING by date.')
    elif args.max_date and not ascending:
        raise Exception('max_date requires reviews to be sorted ASCENDING by date.')


browser = get_browser()
page = [1]
idx = [0]
date_limit_reached = [False]


def main():
    logger.info(f'Scraping up to {args.limit} reviews.')
    res = pd.DataFrame([], columns=SCHEMA)
    sign_in()

    if not args.start_from_url:
        reviews_exist = navigate_to_reviews()
        if not reviews_exist:
            return
    elif args.max_date or args.min_date:
        verify_date_sorting()
        browser.get(args.url)
        page[0] = get_current_page()
        logger.info(f'Starting from page {page[0]:,}.')
        time.sleep(1)
    else:
        browser.get(args.url)
        page[0] = get_current_page()
        logger.info(f'Starting from page {page[0]:,}.')
        time.sleep(1)

    reviews_df = extract_from_page()
    res = res.append(reviews_df)

    # print(more_pages())
    # print(args.limit)
    # print(len(res))
    
    while more_pages() and len(res) < args.limit and not date_limit_reached[0]:
        go_to_next_page()
        reviews_df = extract_from_page()
        res = res.append(reviews_df)

    logger.info(f'Writing {len(res)} reviews to file {args.file}')
    res.to_csv(args.file, index=False, encoding='utf-8')

    end = time.time()
    logger.info(f'Finished in {end - start} seconds')
    browser.quit()


if __name__ == '__main__':
    main()
