import google_colab_selenium as gs
from selenium.webdriver.chrome.options import Options
from random import choice
from datetime import datetime
from io import StringIO
import pandas as pd
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from .scraperfc_exceptions import ClubEloInvalidTeamException

import time

user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36'
]

def setup_selenium():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--incognito")
    options.add_argument(f'--user-agent={choice(user_agents)}')
    driver = gs.Chrome(options=options)
    return driver

def get_page_content(url, driver, request_interval=2, page_load_delay=2):
    driver.get(url)
    time.sleep(request_interval)
    html_content = driver.page_source
    time.sleep(page_load_delay)
    return html_content

class ClubElo:

    def __init__(self):
        self.driver = setup_selenium()

    def __del__(self):
        self.driver.close()
        self.driver.quit()

    # ==============================================================================================
    def scrape_team_on_date(self, team: str, date: str) -> float:
        """ Scrapes a team's ELO score on a given date.

        Parameters
        ----------
        team : str
            To get the appropriate team name, go to clubelo.com and find the team you're looking
            for. Copy and past the team's name as it appears in the URL.
        date : str
            Must be formatted as YYYY-MM-DD
        Returns
        -------
        elo : int
            ELO score of the given team on the given date. Will be -1 if the team has no score on
            that date.
        """
        # Check inputs
        if not isinstance(team, str):
            raise TypeError('`team` must be a string.')
        if not isinstance(date, str):
            raise TypeError('`date` must be a string.')

        # Use Selenium to get team data as Pandas DataFrame
        url = f'http://api.clubelo.com/{team}'
        page_content = get_page_content(url, self.driver)
        
        df = pd.read_csv(StringIO(page_content), sep=',')
        if df.shape[0] == 0:
            raise ClubEloInvalidTeamException(team)

        # find row that given date falls in
        df["From"] = pd.DatetimeIndex(df["From"])
        df["To"] = pd.DatetimeIndex(df["To"])
        date_datetime = datetime.strptime(date, '%Y-%m-%d')
        df = df.loc[(date_datetime >= df["From"]) & (date_datetime <= df["To"])]

        elo = -1 if df.shape[0] == 0 else df["Elo"].values[0]

        return elo  # return -1 if ELO not found for given date
