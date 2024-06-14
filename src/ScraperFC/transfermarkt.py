from .scraperfc_exceptions import InvalidLeagueException, InvalidYearException
from tqdm import tqdm
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import cloudscraper

TRANSFERMARKT_ROOT = 'https://www.transfermarkt.us'

comps = {
    'EPL': 'https://www.transfermarkt.us/premier-league/startseite/wettbewerb/GB1',
    'EFL Championship': 'https://www.transfermarkt.us/championship/startseite/wettbewerb/GB2',
    'EFL1': 'https://www.transfermarkt.us/league-one/startseite/wettbewerb/GB3',
    'EFL2': 'https://www.transfermarkt.us/league-two/startseite/wettbewerb/GB4',
    'Bundesliga': 'https://www.transfermarkt.us/bundesliga/startseite/wettbewerb/L1',
    '2.Bundesliga': 'https://www.transfermarkt.us/2-bundesliga/startseite/wettbewerb/L2',
    'Serie A': 'https://www.transfermarkt.us/serie-a/startseite/wettbewerb/IT1',
    'Serie B': 'https://www.transfermarkt.us/serie-b/startseite/wettbewerb/IT2',
    'La Liga': 'https://www.transfermarkt.us/laliga/startseite/wettbewerb/ES1',
    'La Liga 2': 'https://www.transfermarkt.us/laliga2/startseite/wettbewerb/ES2',
    'Ligue 1': 'https://www.transfermarkt.us/ligue-1/startseite/wettbewerb/FR1',
    'Ligue 2': 'https://www.transfermarkt.us/ligue-2/startseite/wettbewerb/FR2',
    'Eredivisie': 'https://www.transfermarkt.us/eredivisie/startseite/wettbewerb/NL1',
    'Scottish PL': 'https://www.transfermarkt.us/scottish-premiership/startseite/wettbewerb/SC1',
    'Super Lig': 'https://www.transfermarkt.us/super-lig/startseite/wettbewerb/TR1',
    'Jupiler Pro League': 'https://www.transfermarkt.us/jupiler-pro-league/startseite/wettbewerb/BE1',
    'Liga Nos': 'https://www.transfermarkt.us/liga-nos/startseite/wettbewerb/PO1',
    'Russian Premier League': 'https://www.transfermarkt.us/premier-liga/startseite/wettbewerb/RU1',
    'Brasileirao': 'https://www.transfermarkt.us/campeonato-brasileiro-serie-a/startseite/wettbewerb/BRA1',
    'Argentina Liga Profesional': 'https://www.transfermarkt.us/superliga/startseite/wettbewerb/AR1N',
    'MLS': 'https://www.transfermarkt.us/major-league-soccer/startseite/wettbewerb/MLS1'
}


class Transfermarkt():

    # ==============================================================================================
    def get_valid_seasons(self, league):
        """ Return valid seasons for the chosen league
        Parameters
        ----------
        league : str
            The league to gather valid seasons for
        Returns
        -------
        : list of str
            List of valid season strings
        """
        if type(league) is not str:
            raise TypeError('`league` must be a string.')
        if league not in comps.keys():
            raise InvalidLeagueException(league, 'Transfermarkt', list(comps.keys()))
        
        scraper = cloudscraper.CloudScraper()
        soup = BeautifulSoup(scraper.get(comps[league]).content, 'html.parser')
        valid_seasons = dict([
            (x.text, x['value']) for x in 
            soup.find('select', {'name': 'saison_id'}).find_all('option')
        ])
        scraper.close()
        return valid_seasons
        
    # ==============================================================================================
    def get_club_links(self, year, league):
        """ Gathers all Transfermarkt club URL's for the chosen league season.
        
        Parameters
        ----------
        year : str
            See the :ref:`transfermarkt_year` `year` parameter docs for details.
        league : str
            League to scrape.
        Returns
        -------
        : list of str
            List of the club URLs
        """
        if type(year) is not str:
            raise TypeError('`year` must be a string.')
        valid_seasons = self.get_valid_seasons(league)
        if year not in valid_seasons.keys():
            raise InvalidYearException(year, league, list(valid_seasons.keys()))
        
        scraper = cloudscraper.CloudScraper()
        soup = BeautifulSoup(
            scraper.get(f'{comps[league]}/plus/?saison_id={valid_seasons[year]}').content, 
            'html.parser'
        )
        club_els = (
            soup.find('table', {'class': 'items'})
            .find_all('td', {'class': 'hauptlink no-border-links'})
        )
        club_links = [TRANSFERMARKT_ROOT + x.find('a')['href'] for x in club_els]
        scraper.close()
        return club_links
    
    # ==============================================================================================
    def get_player_links(self, year, league):
        """ Gathers all Transfermarkt player URL's for the chosen league season.
        
        Parameters
        ----------
        year : str
            See the :ref:`transfermarkt_year` `year` parameter docs for details.
        league : str
            League to scrape.
        Returns
        -------
        : list of str
            List of the player URLs
        """
        player_links = list()
        scraper = cloudscraper.CloudScraper()
        club_links = self.get_club_links(year, league)
        for club_link in tqdm(club_links, desc=f'{year} {league} player links'):
            soup = BeautifulSoup(scraper.get(club_link).content, 'html.parser')
            player_els = (
                soup.find('table', {'class': 'items'}).find_all('td', {'class': 'hauptlink'})
            )
            p_links = [
                TRANSFERMARKT_ROOT + x.find('a')['href'] for x in player_els 
                if x.find('a') is not None
            ]
            player_links += p_links
        scraper.close()
        return list(set(player_links))
    
    # ==============================================================================================
    def scrape_players(self, year, league):
        """ Gathers all player info for the chosen league season.
        
        Parameters
        ----------
        year : str
            See the :ref:`transfermarkt_year` `year` parameter docs for details.
        league : str
            League to scrape.
        Returns
        -------
        : DataFrame
            Each row is a player and contains some of the information from their Transfermarkt 
            player profile.
        """
        player_links = self.get_player_links(year, league)
        df = pd.DataFrame()
        for player_link in tqdm(player_links, desc=f'{year} {league} players'):
            player = self.scrape_player(player_link)
            df = pd.concat([df, player], axis=0, ignore_index=True)
        return df

    # ==============================================================================================
    def scrape_player(self, player_link):
        """ Scrape a single player Transfermarkt link

        Parameters
        ----------
        player link : str
            Valid player Transfermarkt URL

        Returns
        -------
        : DataFrame
            1-row dataframe with all of the player details
        """
        r = requests.get(
            player_link, 
            headers={
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36'
            }
        )
        soup = BeautifulSoup(r.content, 'html.parser')
        # Name
        name = (
            soup.find('h1', {'class': 'data-header__headline-wrapper'}).text.split('\n')[-1].strip()
        )
        
        # Value
        try:
            value = (
                soup.find('a', {'class': 'data-header__market-value-wrapper'}).text.split(' ')[0]
            )
            value_last_updated = (
                soup.find('a', {'class': 'data-header__market-value-wrapper'}).text
                .split('Last update: ')[-1]
            )
        except AttributeError:
            value = None
            value_last_updated = None
            
        # DOB and age
        dob_el = soup.find('span', {'itemprop': 'birthDate'})
        if dob_el is None:
            dob, age = None, None
        else:
            dob = ' '.join(dob_el.text.strip().split(' ')[:3])
            age = int(dob_el.text.strip().split(' ')[-1].replace('(','').replace(')',''))
        
        # Height
        height = soup.find('span', {'itemprop': 'height'})
        height = (
            None if (height is None or height.text.strip() == 'N/A' or height.text.strip() == '- m') 
            else float(height.text.strip().replace(' m', '').replace(',', '.'))
        )
       
        # Nationality and citizenships
        nationality_el = soup.find('span', {'itemprop': 'nationality'})
        nationality = nationality_el.getText().replace('\n','').strip()

        citizenship_els = soup.find_all(
            'span', {'class': 'info-table__content info-table__content--bold'}
        )
        flag_els = [
            flag_el for el in citizenship_els 
            for flag_el in el.find_all('img', {'class': 'flaggenrahmen'})
        ]
        citizenship = list(set([el['title'] for el in flag_els]))
        
        # Position
        position_el = soup.find('dd', {'class': 'detail-position__position'})
        if position_el is None:
            position_el = [
                el for el in soup.find_all('li', {'class': 'data-header__label'}) 
                if 'position' in el.text.lower()
                ][0].find('span')
        position = position_el.text.strip()
        try:
            other_positions = [
                el.text for el in 
                soup.find('div', {'class': 'detail-position__position'}).find_all('dd')
            ]
        except AttributeError:
            other_positions = None
        other_positions = None if other_positions is None else pd.DataFrame(other_positions)

        # Data header fields
        team = soup.find('span', {'class': 'data-header__club'})
        team = None if team is None else team.text.strip()

        data_headers_labels = soup.find_all('span', {'class': 'data-header__label'})
        # Last club
        last_club = [
            x.text.split(':')[-1].strip() for x in data_headers_labels 
            if 'last club' in x.text.lower()
        ]
        assert len(last_club) < 2
        last_club = None if len(last_club) == 0 else last_club[0]
        # "Since" date
        since_date = [
            x.text.split(':')[-1].strip() for x in data_headers_labels 
            if 'since' in x.text.lower()
        ]
        assert len(since_date) < 2
        since_date = None if len(since_date) == 0 else since_date[0]
        # "Joined" date
        joined_date = [
            x.text.split(':')[-1].strip() for x in data_headers_labels if 'joined' in x.text.lower()
        ]
        assert len(joined_date) < 2
        joined_date = None if len(joined_date) == 0 else joined_date[0]
        # Contract expiration date
        contract_expiration = [
            x.text.split(':')[-1].strip() for x in data_headers_labels 
            if 'contract expires' in x.text.lower()
        ]
        assert len(contract_expiration) < 2
        contract_expiration = None if len(contract_expiration) == 0 else contract_expiration[0]
        
        # Market value history
        try:
            script = [
                s for s in soup.find_all('script', {'type': 'text/javascript'}) 
                if 'var chart = new Highcharts.Chart' in str(s)
            ][0]
            values = [int(s.split(',')[0]) for s in str(script).split('y\':')[2:-2]]
            dates = [
                s.split('datum_mw\':')[-1].split(',\'x')[0].replace('\\x20',' ').replace('\'', '')
                for s in str(script).split('y\':')[2:-2]
            ]
            market_value_history = pd.DataFrame({'date': dates, 'value': values})
        except IndexError:
            market_value_history = None
        
        # Transfer History
        rows = soup.find_all('div', {'class': 'grid tm-player-transfer-history-grid'})
        transfer_history = pd.DataFrame(
            data=[[s.strip() for s in row.getText().split('\n\n') if s!=''] for row in rows],
            columns=['Season', 'Date', 'Left', 'Joined', 'MV', 'Fee', '']
        ).drop(
            columns=['']
        )
        
        player = pd.Series(dtype=object)
        player['Name'] = name
        player['Value'] = value
        player['Value last updated'] = value_last_updated
        player['DOB'] = dob
        player['Age'] = age
        player['Height (m)'] = height
        player['Nationality'] = nationality
        player['Citizenship'] = citizenship
        player['Position'] = position
        player['Other positions'] = other_positions
        player['Team'] = team
        player['Last club'] = last_club
        player['Since'] = since_date
        player['Joined'] = joined_date
        player['Contract expiration'] = contract_expiration
        player['Market value history'] = market_value_history
        player['Transfer history'] = transfer_history

        return player.to_frame().T
        