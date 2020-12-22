Forked from [MatthewChatham/glassdoor-review-scraper](https://github.com/MatthewChatham/glassdoor-review-scraper)

Fixed many bugs and simplified the code (Dec.14, 2020)



# Usage
```
usage: main.py [-h] [-u URL] [-f FILE] [--headless] [--username USERNAME]
               [-p PASSWORD] [-c CREDENTIALS] [-l LIMIT] [--start_from_url] 
               [--max_date MAX_DATE] [--min_date MIN_DATE]

optional arguments:
  -h, --help                                  show this help message and exit
  -u URL, --url URL                           URL of the company's Glassdoor landing page.
  -f FILE, --file FILE                        Output file.
  --headless                                  Run Chrome in headless mode.
  --username USERNAME                         Email address used to sign in to GD.
  -p PASSWORD, --password PASSWORD            Password to sign in to GD.
  -c CREDENTIALS, --credentials CREDENTIALS   Credentials file
  -l LIMIT, --limit LIMIT                     Max reviews to scrape
  --start_from_url                            Start scraping from the passed URL.
  
  --max_date MAX_DATE                         Latest review date to scrape. Only use this option
                                              with --start_from_url. You also must have sorted
                                              Glassdoor reviews ASCENDING by date.
                                              
  --min_date MIN_DATE                         Earliest review date to scrape. Only use this option
                                              with --start_from_url. You also must have sorted
                                              Glassdoor reviews DESCENDING by date.
```

Run the script as follows, taking Wells Fargo as an example. You can pass `--headless` to prevent the Chrome window from being visible, and the `--limit` option will limit how many reviews get scraped. The`-f` option specifies the output file, which defaults to `glassdoor_reviews.csv`.  

### Example 1
Suppose you want to get the top 1,000 most popular reviews for Wells Fargo. Run the command as follows:

`python main.py --headless --url "https://www.glassdoor.com/Overview/Working-at-Wells-Fargo-EI_IE8876.11,22.htm" --limit 1000 -f wells_fargo_reviews.csv`

**Note**: To be safe, always surround the URL with quotes. This only matters in the presence of a query string.

### Example 2: Date Filtering
If you want to scrape all reviews in a date range, sort reviews on Glassdoor ascending/descending by date, find the page with the appropriate starting date, set the max/min date to the other end of your desired time range, and set limit to 99999.

Suppose you want to scrape all reviews from McDonald's that were posted in 2010:

1. Navigate to McDonald's Glassdoor page and sort reviews ascending by date.
2. Find the first page with a review from 2010, which happens to be [page 13](https://www.glassdoor.com/Reviews/McDonald-s-Reviews-E432_P13.htm?sort.sortType=RD&sort.ascending=true).
3. Send the command to the script:
`python main.py --headless --start_from_url --limit 9999 --max_date 2010-12-31 --url "https://www.glassdoor.com/Reviews/McDonald-s-Reviews-E432_P13.htm?sort.sortType=RD&sort.ascending=true"`
