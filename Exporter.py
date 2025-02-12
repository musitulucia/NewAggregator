from flask import Flask
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil import parser
import pytz
import config

import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from playwright.sync_api import sync_playwright
import time
import re

import asyncio
from playwright.async_api import async_playwright

import models
import importlib
importlib.reload(models)
import streamlit as st
import notebook
importlib.reload(notebook)
import asyncio






# Global list to store news data
news_need_update = {}

last_assigned_date = {}
insight_need_update = {}

flag_year_MoneyDJ = 2025
#flag_days = True




#CALCULATE TIME AGO

def time_ago(date, source, flag_days):

    """Calculate the time difference between now and the published time"""

    #global flag_days
    global last_assigned_date
    global flag_year_MoneyDJ

    #date might be extracted but might be empty.

    # Check if date is None or an empty string and set it to None
    if date is None or len(date) == 0 or date == "":
        date = None

    # Proceed only if date is not None
    if date is not None:

        if source == 'BeyondGravity':
            str_time = datetime.strptime(date, "%d.%m.%Y")

        if source == 'SemiPress':
            str_time = datetime.strptime(date, "%m/%d/%Y")

        if source == 'Zdnet':
            str_time = datetime.strptime(date, "%Y.%m.%d %p %I:%M")

        if source == 'MoneyDJ':
            #year is not determined for this source
            date = f"{flag_year_MoneyDJ}/{date}"
            str_time = datetime.strptime(date, "%Y/%m/%d %H:%M") #all set to 2025 since year not reported
            if flag_year_MoneyDJ == 2025 and str_time.month == 12 and str_time.day == 31:
                #Change flag year for previous dates before 01/01
                flag_year_MoneyDJ = 2024
            str_time.replace(year=flag_year_MoneyDJ)


        #match if a date is as n days ago
        match = re.match(r"(\d+)\s+(hour|day|minute)s?\s+ago", date)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            if unit == "hour": delta = timedelta(hours=value)
            elif unit == "minute": delta = timedelta(minutes=value)
            elif unit == "day":  delta = timedelta(days=value)
            str_time = datetime.now() - delta


        #need YYYY-MM-DD
        if source == 'TrendForce':
            date = date[:11]

        if source == 'SIA':
            date = date[-8:]
            #print(date)

        if source == 'TheElec':
            date = date[-16:]

        if source == 'TechNews':
            #From China Standard Time (UTC+8) to CET
            str_time = parser.parse(date)
            str_time = str_time.replace(tzinfo=pytz.timezone("Asia/Shanghai"))
            published_time = str_time.astimezone(pytz.timezone("Europe/Berlin"))

        else:
            #Assuming the time is european
            str_time = locals().get("str_time", None)  #in case it doesnt exist
            if not str_time : str_time = parser.parse(date)
            published_time = str_time.astimezone(pytz.timezone('Europe/Berlin'))


        #date format
        publication_time = published_time.strftime("%d-%m-%Y")

        #how long ago
        delta = datetime.now(pytz.timezone('Europe/Berlin')) - published_time

        if delta.days > 0:

            #NOTE: Only extract news ins the last 60 days
            #if  delta.days > 2:
            if  delta.days > 10:

                '''
                ¡¡¡¡IMPORTANT!!! THIS ASSUMES ALL WEB NEWS APPEAR ORDERED IN TIME

                '''

                flag_days =  False

            name_d = "day" if delta.days == 1 else "days"
            return f"{delta.days} {name_d} ago", publication_time, published_time, flag_days

        elif delta.seconds >= 3600:  # More than an hour
            hours = delta.seconds // 3600
            name_h = "hour" if hours == 1 else "hours"
            return f"{hours} {name_h} ago", publication_time, published_time, flag_days

        elif delta.seconds >= 60:  # More than a minute
            minutes = delta.seconds // 60
            name_m = "minute" if minutes == 1 else "minutes"
            return f"{minutes} {name_m} ago", publication_time, published_time, flag_days

        else:  # Less than a minute
            return "Just now", publication_time, published_time, flag_days


    #Make uip hte date
    else:
        if not last_assigned_date.get(source):
            date =  datetime.now() - timedelta(minutes = 30)
            last_assigned_date[source] = date
        else:
            if source == 'DigiTimesAsia':
               date = last_assigned_date[source]

            else:
                date = last_assigned_date[source] - timedelta(minutes= 5)
                last_assigned_date[source] = date

        published_time = date.astimezone(pytz.timezone('Europe/Berlin'))
        publication_time = published_time.strftime("%d-%m-%Y")

        if source == 'Sina':
            return " ", publication_time, published_time, flag_days

        elif source == 'DigiTimesAsia':
            delta = datetime.now() - date
            return f"{delta.days} {'day' if delta.days == 1 else 'days'} ago", publication_time, published_time, flag_days

        else:
            return "No date reported", publication_time, published_time, flag_days


async def fetch_news(source, flag_days):

    print(f'{source} being loaded')
    start_time = time.time()

    '''

    Function to fetch news from various sources

    '''

    global news_need_update
    global insight_need_update


    news = []
    flag_days = True

    if source == "Wccftech":

        ############################   Wccftech  #############################


        #For this source only extracting first 30 pages
        #Their "time_ago" in main page is wrong... (compare it to the time_ago in specific linked page)


        try:
            base_url = "https://wccftech.com/category/news/page/"
            page_number = 1


            #print(f'{source} started using flag which is {flag_days}')

            while flag_days:
                url = f"{base_url}{page_number}/"

                # Get html structure
                response = requests.get(url)
                soup = BeautifulSoup(response.content, 'html.parser')

                # Iterate through each post
                for post_div in soup.find_all('div', class_='post'):

                    if flag_days:

                        headline_tag = post_div.find('h3').find('a')
                        headline = headline_tag.get_text(strip=True)
                        link = headline_tag['href']


                        footer = post_div.find('footer')
                        time_tag = footer.find('span', class_='post-time relative-time')
                        if time_tag:
                            date = time_tag['title']  # Extract 'data-time' attribute, format
                            publication_time_ago, publication_time, published_time, flag_days  = time_ago(date, source, flag_days)

                        else:
                            publication_time = "Unknown time"
                            publication_time_ago = "Unknown"
                            published_time = "Unknown"

                        post = models.Post(headline, publication_time, publication_time_ago, link, published_time, "Wccftech")
                        if flag_days:
                            news.append(post)
                    else:
                        break

                page_number += 1

        except Exception as e:
            news_need_update[source] = e

    elif source == "Intel":

        ############################   INTEL  #############################


        '''
        Gets the last five pages as n < 3
        NOTE: cookies need to be accepted: try automatising this in the future

        '''

        try:

            app = Flask(__name__)


            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Go to the Intel Newsroom URL
                url = "https://www.intel.com/content/www/us/en/newsroom/news-stories.html"
                page.goto(url)

                # Click the "Accept Cookies" button
                try:
                    page.locator('#onetrust-accept-btn-handler').click()
                    print("Accepted cookies")
                except Exception as e:
                    print(f"Error clicking accept cookies button: {e}")

                # Wait for the content to load
                page.wait_for_timeout(3000)  # Wait 3 seconds for safety

                # Extract the page source and parse it with Beautiful Soup
                soup = BeautifulSoup(page.content(), 'html.parser')

                # Extract news items
                news_items = soup.find_all("div", class_="sortable-grid-item")
                for item in news_items:

                    #print(f'{source} started using flag which is {flag_days}')

                    if flag_days:
                        try:
                            title_tag = item.find("h3")
                            link_tag = item.find("a")
                            date_tag = item.find("div", class_="article-date")

                            if title_tag and link_tag and date_tag:
                                title = title_tag.text.strip()
                                link = link_tag["href"].strip()
                                date = date_tag.text.strip()

                                # Process the date
                                date_str, time_str = date.split(" | ")
                                publication_time_ago, publication_time, published_time, flag_days = time_ago(date_str, "Intel", flag_days)

                                # Append the news post to the list
                                if flag_days:
                                    news.append(models.Post(title, publication_time, publication_time_ago, link, published_time, "Intel"))

                        except Exception as e:
                            print(f"Error extracting news item: {e}")
                    else:
                        #print(f'{source} stopped using flag which is {flag_days}')
                        break

                browser.close()

        except Exception as e:
            news_need_update[source] = e



        ############## BELLOW HERE IS THE CODE IF NEEDED TO EXTRACT MORE PAGES -  NEED GOOGLE CHROME ##########

        #flag_days = True

        # Initialize WebDriver
        # driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        # url = "https://www.intel.com/content/www/us/en/newsroom/news-stories.html"
        # driver.get(url)
        # n = 0

        # # Wait for the page to load
        # time.sleep(3)

        # try:
        #     # Use XPath to find the button with the text "Accept all"
        #     # Wait for the "Accept Cookies" button to be clickable
        #     WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="onetrust-accept-btn-handler"]'))).click()

        #     print("Accepted cookies")

        # except Exception as e:
        #     print(f"Error clicking accept cookies button: {e}")

        # while flag_days: #NOTE: n < num => num is number of pages to extract

        #     try:
        #         # Extract news items on the current page
        #         news_items = driver.find_elements(By.CLASS_NAME, "sortable-grid-item")
        #         for item in news_items:

        #             if flag_days:
        #                 try:
        #                     title = item.find_element(By.TAG_NAME, "h3").text
        #                     link = item.find_element(By.TAG_NAME, "a").get_attribute("href")
        #                     date = item.find_element(By.CLASS_NAME, "article-date").text

        #                     if title:
        #                         date_str, time_str = date.split(" | ")
        #                         publication_time_ago , publication_time,  published_time = time_ago(date_str, source)
        #                         #print(title, publication_time, publication_time_ago, link, published_time, "intel")
        #                         if flag_days:
        #                             news.append(Post(title, publication_time, publication_time_ago, link, published_time, "Intel"))


        #                 except Exception as e:
        #                     print(f"Error extracting news item: {e}")
        #             else:
        #                 break

        #         # Look for the "Next" button using the updated class and aria-label
        #         next_button = driver.find_element(By.CSS_SELECTOR, ".paging-paddle.next[aria-label='Next']")
        #         if next_button:
        #             next_button.click()  # Click the "Next" button
        #             n += 1
        #             time.sleep(2)  # Wait for the next page to load

        #         else:
        #             print("No more pages found.")
        #             break

        #     except Exception as e:
        #         print(f"Error: {e}")
        #         break

        # driver.quit()

    elif source == "TSMC":


        ############################   TSMC  #############################

            try:
                # Set up WebDriver with headless options
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))



                #driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
                url = "https://pr.tsmc.com/english/latest-news"
                driver.get(url)
                n = 0

                # Wait for the page to load
                time.sleep(1)

                try:
                    # Use XPath to find the button with the text "Accept all"
                    # Wait for the "Accept Cookies" button to be clickable
                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="tsmc_cookie_cookiePanel"]/div[1]/button[1]'))).click()

                    print("Accepted cookies")

                except Exception as e:
                    print(f"Error clicking accept cookies button: {e}")


                try:
                    # Extract news items on the current page
                    news_items = driver.find_elements(By.CLASS_NAME, "node")
                    for item in news_items:

                        #print(f'{source} started using flag which is {flag_days}')

                        if flag_days:
                            try:
                                title = item.find_element(By.TAG_NAME, "h2").text
                                link = item.find_element(By.TAG_NAME, "a").get_attribute("href")
                                date = item.find_element(By.CLASS_NAME, "datetime").text

                                if title:
                                    publication_time_ago , publication_time, published_time, flag_days = time_ago(date, source, flag_days)
                                    #print(title, publication_time, publication_time_ago, link, published_time, "intel")
                                    if flag_days:
                                        news.append(models.Post(title, publication_time, publication_time_ago, link, published_time, "TSMC"))


                            except Exception as e:
                                print(f"Error extracting news item: {e}")
                        else:
                            #print(f'{source} stopped using flag which is {flag_days}')
                            break

                except Exception as e:
                            print(f"Error extracting news item: {e}")

                driver.quit()


            except Exception as e:
                news_need_update[source] = e

    elif source == 'SCMP':

        ############################   SCMP  #############################


        try:

            # Function to extract post details
            def extract_post_details(item, source, flag_days):
                try:
                    link = item.find_all('a', attrs={'target': '_self'})[1]['href']
                    link = "https://www.scmp.com/" + link
                    headline = item.find('h2', class_='css-1xdhyk6 e298i0d4').text.strip()
                    date = item.find('time')['datetime']
                    publication_time_ago, publication_time, published_time, flag_days = time_ago(date, source, flag_days)
                    return models.Post(headline, publication_time, publication_time_ago, link, published_time, source) , flag_days

                except Exception as e:
                    print(f"Error extracting data: {e}")
                    return None, flag_days

            # Request to fetch the page source
            url = "https://www.scmp.com/topics/semiconductors"
            response = requests.get(url)

            # Parse content with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract the primary post
            primary_item = soup.find('div', attrs={'data-qa': 'Component-Primary'})
            if primary_item:
                post, flag_days = extract_post_details(primary_item, "SCMP", flag_days)
                if post:
                    news.append(post)


            # Extract secondary posts
            rest_items = soup.find('div', attrs={'data-qa': 'Component-Rest'})
            if rest_items:
                items = rest_items.find_all('div', attrs={'class': 'e102obc91 e1daqvjd0 css-1hvuudh efy545l13'}) #class here might change!!
                #print(items)
                for item in items:
                    post, flag_days = extract_post_details(item, "SCMP", flag_days)
                    #print(post)
                    if post:
                        news.append(post)

            else:
                news_need_update['SCMP'] = 'Check for classes to be correctly specified in all but Component-Primary'



            # Extract remaining posts

            #print(f'{source} started using flag which is {flag_days}')
            flag_days = True
            other_items = soup.find_all('div', class_='ez1wmkq4 css-1r9zbkb e10l40di0')
            if other_items:
                for item in other_items:
                    if flag_days:
                        post, flag_days = extract_post_details(item, "SCMP", flag_days)
                        if post and flag_days:
                            news.append(post)
                    else:
                        #print(f'{source} stopped using flag which is {flag_days}')
                        break
            else:
                news_need_update['SCMP'] = 'Check for classes to be correctly specified in all but Component-Primary'


        except Exception as e:
            news_need_update[source] = e

    elif source == 'IONQ':

        ############################   IONQ  #############################


        try:

            #### NEWSEOOM ####

            session = requests.Session()
            response = session.get("https://ionq.com/newsroom")
            soup = BeautifulSoup(response.text, 'html.parser')


            try:
                news_items = soup.find_all(class_="ResourceGridItem")
                i = 0
                for item in news_items:
                    try:
                        title = item.find(class_="resources-item-title").get_text(strip=True)

                        link = item.find(class_="resources-panel")['href']

                        date = item.find(class_="resources-item-date").get_text(strip=True)
                        publication_time_ago, publication_time, published_time, flag_days = time_ago(date, "IONQ", flag_days)

                        if i < 6:
                            link = 'https://ionq.com' + link
                            title = 'Newsroom | ' + title

                            #print(f'{source} started using flag which is {flag_days}')
                            if flag_days:
                                news.append(models.Post(title, publication_time, publication_time_ago, link, published_time, "IONQ"))

                        else:
                            title = 'Articles | ' + title
                            if flag_days:
                                news.append(models.Post(title, publication_time, publication_time_ago, link, published_time, "IONQ"))

                        i += 1
                        flag_days = True


                    except Exception as e:
                        print(f"Error extracting news item: {e}")

                #print(f'{source} stopped using flag which is {flag_days}')

            except Exception as e:
                news_need_update['IONQ |Newsroom'] = e


            #### BLOG ####

            #print(f'{source} started using flag which is {flag_days}')
            flag_days = True
            url1 = "https://ionq.com/blog"
            response = requests.get(url1)
            soup1 = BeautifulSoup(response.text, 'html.parser')

            try:
                news_items = soup1.find_all(class_="ResourceGridItem")

                for item in news_items:
                    if flag_days:
                        try:
                            # Extract title, link, and date of the news item
                            title = 'Articles |' + item.find(class_="resources-item-title").get_text(strip=True)
                            link = item.find(class_="resources-panel")['href']
                            date = item.find(class_="resources-item-date").get_text(strip=True)
                            publication_time_ago, publication_time, published_time, flag_days = time_ago(date, "IONQ", flag_days)

                            if flag_days:
                                news.append(models.Post(title, publication_time, publication_time_ago, link, published_time, "IONQ"))
                        except Exception as e:
                            print(f"Error extracting news item: {e}")
                    else:
                        #print(f'{source} stopped using flag which is {flag_days}')
                        break

            except Exception as e:
                news_need_update['IONQ | Blog'] = e
                print(f"Error extracting news items: {e}")

        except Exception as e:
            news_need_update[source] = e

    elif source == 'Skhynix':

        ################################# Skhynix ############################

        '''

        Note only news from first page are displayed

        '''

        try:

            session = requests.Session()

            #First page
            response = session.get('https://news.skhynix.com/press-center/')
            soup = BeautifulSoup(response.text, 'html.parser')
            soup = soup.find_all('div', class_ = 'article-content-wrap')

            if soup:
                for item in soup:
                    title = item.find('a').get_text(strip= True)
                    link = item.find('a')['href']
                    date = item.find(class_ = 'post_date').get_text(strip = True)
                    publication_time_ago, publication_time, published_time, flag_days = time_ago(date, "Skhynix", flag_days)
                    #print(f'{source} started using flag which is {flag_days}')
                    if flag_days:
                        news.append(models.Post(title, publication_time, publication_time_ago, link, published_time, "Skhynix"))
                    else:
                        #print(f'{source} stopped using flag which is {flag_days}')
                        break
            else:
                news_need_update["Skhynix"] = 'Connection with server was unsuccesful, please modify code'


        except Exception as e:
            news_need_update[source] = e

    elif source == 'TEL':

        try:

            response = requests.get('https://www.tel.com/news/')
            soup  = BeautifulSoup(response.content, 'html.parser')
            soup =  soup.find_all(class_ = 'p-news__item' )

            for item in soup:
                title = item.find(class_ = 'c-news__summary u-fileicon').get_text(strip = True)
                link =  'https://www.tel.com' + item.find(class_ = 'u-hover')['href']
                date = item.find(class_ = 'c-news__date').get_text(strip = True)
                publication_time_ago, publication_time, published_time, flag_days = time_ago(date, "TEL", flag_days)

                #print(f'{source} started using flag which is {flag_days}')
                if flag_days:
                    news.append(models.Post(title, publication_time, publication_time_ago, link, published_time, "TEL"))
                else:
                    #print(f'{source} stopped using flag which is {flag_days}')
                    break #added this now

        except Exception as e:
            news_need_update[source] = e

    elif source == 'Nature':


        try:

            response = requests.get('https://www.nature.com/subjects/nanoscience-and-technology/nature')
            soup  = BeautifulSoup(response.content, 'html.parser')
            soup =  soup.find_all(class_ = 'border-gray-medium border-bottom-1 pb20') + soup.find_all(class_ = 'border-gray-medium border-bottom-1 pb20 mt20')


            for item in soup:
                #print(f'{source} started using flag which is {flag_days}')
                if flag_days:
                    s = item.find(class_ = 'text-gray')
                    title = s.get_text(strip = True)
                    link = 'https://www.nature.com' + s['href'] #NOTE: need ot complete endpoint
                    date = item.find('time')['datetime']
                    publication_time_ago, publication_time, published_time, flag_days = time_ago(date, "Nature", flag_days)

                    if flag_days:
                        news.append(models.Post(title, publication_time, publication_time_ago, link, published_time, "Nature"))
                else:
                    #print(f'{source} stopped using flag which is {flag_days}')
                    break

        except Exception as e:
            news_need_update[source] = e

    elif source == 'Jwt625':

        ############################   Jwt625  #############################

        try:

            session = requests.Session()
            response = session.get("https://jwt625.github.io/posts/")
            soup = BeautifulSoup(response.text, 'html.parser')

            news_items = soup.find_all('article', class_="archive__item")
            for item in news_items:
                #print(f'{source} started using flag which is {flag_days}')
                if flag_days:
                    title = item.find("h2", class_="archive__item-title").get_text(strip=True)
                    link = 'https://jwt625.github.io/' + item.find("a", rel="permalink")["href"]

                    date = item.find("time")['datetime']
                    publication_time_ago, publication_time, published_time, flag_days = time_ago(date, "Jwt625", flag_days)

                    if flag_days:
                        news.append(models.Post(title, publication_time, publication_time_ago, link, published_time, "Jwt625"))

                else:
                    break
            #print(f'{source} stopped using flag which is {flag_days}')


        except Exception as e:
            news_need_update[source] = e

    elif source == 'ViksNewsletter':

        ############################   ViksNewsletter  #############################
        try:
            #print('ViksNewsletter trying')
            #print(f'Here we have FD {flag_days}')

            news, flag_days = models.structure_1(flag_days = flag_days, url = 'https://www.viksnewsletter.com/archive', source = 'ViksNewsletter')

        except Exception as e:
            news_need_update[source] = e

    elif source == 'Morethanmoore':

        ############################   moorethanmore  #############################

        try:
            news, flag_days = models.structure_1(flag_days, "https://morethanmoore.substack.com/archive", 'Morethanmoore')

        except Exception as e:
            news_need_update[source] = e

    elif source == 'Chipstrat':

        ############################   Chipstrat  #############################

        try:
            news, flag_days = models.structure_1(flag_days, "https://www.chipstrat.com/archive", 'Chipstrat')

        except Exception as e:
            news_need_update[source] = e

    elif source == 'Eenewseurope':

        ############################   Eenewseurope  #############################

        try:
            news, flag_days =  models.structure_1(flag_days, 'https://www.eenewseurope.com/en/news/', 'Eenewseurope',
                    parent_abs = '//*[@id="content"]/main/div[4]/section/content/div[2]',
                    child1_abs_or_relative_to_parent = './div[1]/div[*]',
                    child_two = True,
                    child2_abs_or_relative_to_parent = './div[3]/div[*]',
                    date_abs_or_relative_to_child= './a/div[2]/div[2]/time',
                    link_title_link_abs_or_relative_to_child = './a',
                    title_abs_or_relative_to_link = './div[2]/div[1]/div',
                    date_datetime = False)

        except Exception as e:
            news_need_update[source] = e

    elif source == 'Infierna':

        ############################   Infierna  #############################

        '''
        Only gets news of last year ie 2025

        '''

        try:

            news, flag_days = models.structure_1(flag_days, 'https://investors.infinera.com/news/', 'Infierna',
                    parent_abs = '//*[@id="_ctrl0_ctl49_divNewsItemsContainer"]',
                    child1_abs_or_relative_to_parent = '//*[@id="_ctrl0_ctl49_divNewsItemsContainer"]/div[*]',
                    child_two = False,
                    date_abs_or_relative_to_child= './div/div/div[1]/div[1]',
                    link_title_link_abs_or_relative_to_child = './div/div/div[1]/div[2]/a',
                    date_datetime = False)

        except Exception as e:
            news_need_update[source] = e

    elif source == 'XFAB':

         ############################   XFAB  #############################


        try:
            news, flag_days = models.structure_1(flag_days, 'https://www.xfab.com/news/archive', 'XFAB',
                    parent_abs = '//*[@id="c26"]/div/div',
                    child1_abs_or_relative_to_parent = './div[*]',
                    child_two = False,
                    date_abs_or_relative_to_child= './div/div[1]/div/p/span/time',
                    link_title_link_abs_or_relative_to_child = './div/div[1]/div/h3/a',
                    title_abs_or_relative_to_link = './span',
                    date_datetime = True,
                    list_cookies= [{
                'name': 'cookie_consent',
                'value': '%7B%22consent%22:true,%22options%22:%5B%5D%7D',
                'domain': 'www.xfab.com',
                'path': '/',
                'secure': False,  # Set to True if the website uses HTTPS
                'sameSite': 'Strict'
            }, {
                'name': 'fe_typo_user',
                'value': 'f7de63284c6beaab267ca96931452d9c',
                'domain': 'www.xfab.com',
                'path': '/',
                'secure': False,  # Set to True if the website uses HTTPS
                'sameSite': 'Lax'} ])

        except Exception as e:
            news_need_update[source] = e

    elif source == 'Corsair':

        ############################   Corsair  #############################

        try:

            news, flag_days = models.structure_1(flag_days, 'https://www.corsair.com/newsroom', 'Corsair',
                    parent_abs = '//*[@id="post-1239"]/div',
                    child1_abs_or_relative_to_parent = './section[1]/div/div/div/div/div/section/div/section/div/div/div[*]',
                    child_two = True,
                    child2_abs_or_relative_to_parent = './section[2]/div/div/div/div/div/section/div/div[1]/article[*]',
                    date_abs_or_relative_to_child= './/span/span/time',
                    link_title_link_abs_or_relative_to_child = './/div/h2/a',
                    date_datetime = True)

        except Exception as e:
            news_need_update[source] = e

    elif source == 'semianalysis':

        ############################   semianalysis  #############################

        '''

        For this website, needed to create a pattern so that it finds any string that mathces apart from the number

        '''

        try:

            session = requests.Session()
            response = session.get("https://semianalysis.com/archives/")
            soup = BeautifulSoup(response.text, 'html.parser')

            pattern = re.compile(r"^wp-block-group archive-card__meta is-layout-flow wp-container-core-group-is-layout-\d+ wp-block-group-is-layout-flow$")
            news_items = soup.find_all('div', class_=pattern)

            for item in news_items:
                if flag_days:
                    try:
                        title = item.find('a', target = '_self').get_text(strip = True)
                        link = item.find('a', target = '_self')['href']
                        date = item.find('time')['datetime']
                        publication_time_ago, publication_time, published_time, flag_days = time_ago(date, "semianalysis", flag_days)

                        if flag_days:
                            news.append(models.Post(title, publication_time, publication_time_ago, link, published_time, "semianalysis"))

                    except Exception as e:
                        news_need_update['semianalysis'] = e
                else:
                    break

        except Exception as e:
            news_need_update[source] = e

    elif source == 'Google.news':

        '''
        Need to add path to link

        '''

        try:
            session = requests.Session()
            response = session.get("https://news.google.com/search?q=semiconductor%20when%3A1d&hl=en-US&gl=US&ceid=US%3Aen")
            soup = BeautifulSoup(response.text, 'html.parser')

            news_items = soup.find_all('article', class_='IFHyqb DeXSAc')
            for item in news_items:
                try:
                    if flag_days:
                        title = item.find('a', class_ = 'JtKRv').get_text(strip = True)
                        link = 'https://news.google.com' + item.find('a', class_ = 'WwrzSb')['href'][1:]
                        date = item.find('time', class_ = 'hvbAAd')['datetime']
                        publication_time_ago, publication_time, published_time, flag_days = time_ago(date, "Google.news", flag_days)
                        if flag_days:
                            news.append(models.Post(title, publication_time, publication_time_ago, link, published_time, "Google.news"))
                    else:
                        break
                except Exception as e:
                        continue

        except Exception as e:
            news_need_update[source] = e

    elif source == 'Yolegroup':


        '''

        Here the website blocks the server blocks the request

        '''

        try:
            session = requests.Session()

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get('https://www.yolegroup.com/semiconductor-news/' ,headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')



            news_items = [soup.find('a', class_='card-post-highlight')] + soup.find_all('a', class_='card-post')
            i = 0
            for item in news_items:
                try:
                    if flag_days:
                        if i == 0:
                            title = item.find('h3', class_ = 'card-post-highlight__title').get_text(strip = True)
                            link = item['href']
                            date = item.find('time', class_ = 'card-post-highlight__date').get_text(strip = True)
                            publication_time_ago, publication_time, published_time, flag_days = time_ago(date, "Yolegroup", flag_days)

                        else:
                            title = item.find('h3', class_ = 'card-post__title').get_text(strip = True)
                            link = item['href']
                            date = item.find('time', class_ = 'card-post__date').get_text(strip = True)
                            publication_time_ago, publication_time, published_time, flag_days = time_ago(date, "Yolegroup", flag_days)
                        if flag_days:
                            news.append(models.Post(title, publication_time, publication_time_ago, link, published_time, "Yolegroup"))
                    else:
                        break

                except Exception as e:
                        continue
                i += 1

        except Exception as e:
            news_need_update[source] = e

    elif source == 'Phys.org':

        '''
        NOTE: Only extracting at max top 21st news
        NOTE: headless not working ...

        '''

        try:
            #Selenium WebDriver
            options = webdriver.ChromeOptions()
            #options.add_argument('--headless')
            driver = webdriver.Chrome(service= Service(), options=options)
            #driver.get("https://phys.org/nanotech-news/huihlui")
            driver.get("https://phys.org/nanotech-news/")

            #Wait for list to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".sorted-news-list.px-3"))
            )

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            driver.quit()


            # We want class "sorted-article" and to exclude those with additional classes since ads have classes = ['sorted-article' and 'ads']
            items = soup.select(".sorted-article:not(.ads)")
            if items:
                for item in items:
                    main = item.find('a', class_='news-link')
                    title = main.text.strip()
                    link = main['href']
                    date = item.find(class_='article__info-item mr-3').find(class_='text-uppercase text-low').text.strip()


                    publication_time_ago, publication_time, published_time, flag_days = time_ago(date, "Phys.org", flag_days)
                    if flag_days:
                        news.append(models.Post(title, publication_time, publication_time_ago, link, published_time, "Phys.org"))
                    else:
                        break

        except Exception as e:
            news_need_update[source] = e

    elif source == 'Eejournal':

        try:

            # # Initialize Selenium WebDriver
            # options = webdriver.ChromeOptions()
            # options.add_argument('--headless')
            # driver = webdriver.Chrome(service=Service(), options=options)

            # Initialize Selenium WebDriver options for headless browsing (necessary for Docker)
            #options = Options()
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')  # No GUI
            options.add_argument('--disable-gpu')  # Disables GPU acceleration
            options.add_argument('--no-sandbox')  # Required in Docker for Chromium
            options.add_argument('--disable-dev-shm-usage')  # Prevent crashes in Docker

            # Initialize driver and scrape the webpage
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)

            driver.get("https://www.eejournal.com/category/semiconductor/")

            # driver.get("https://www.eejournal.com/category/semiconductor/")

            #Wait for list to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".archiveleft"))
            )

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            driver.quit()

            #get articles
            items = soup.find("div", class_ = 'archiveleft').find_all("article")
            if items:
                for item in items:
                    main = item.find('h2', class_ = 'entry-title title-list-front').find('a')
                    title = main.text
                    link = main['href']
                    date = item.find(class_ = 'author').find('i').text

                    publication_time_ago, publication_time, published_time, flag_days= time_ago(date, "Eejournal", flag_days)
                    if flag_days:
                        news.append(models.Post(title, publication_time, publication_time_ago, link, published_time, "Eejournal"))
                    else:
                        break

            #get industry news, need to reset flag_days
            flag_days = True
            list_all = soup.find('div', id = "homebottomleft")

            #dates an titles/link in different elements
            dates =  list_all.find_all(class_ = 'newsdatehead')
            items = list_all.find_all(class_ = 'newsitem')

            for item, date in zip(items, dates):
                main = item.find('a')
                title = main.text
                link = main['href']
                publication_time_ago, publication_time, published_time, flag_days = time_ago(date.text, "Eejournal", flag_days)
                if flag_days:
                        news.append(models.Post(title, publication_time, publication_time_ago, link, published_time, "Eejournal"))
                else:
                        break

        except Exception as e:
            news_need_update[source] = e

    elif source == 'BeyondGravity':

        try:

            news, flag_days = models.structure_1(flag_days, 'https://www.beyondgravity.com/en/news-overview', 'BeyondGravity',
                            parent_abs = '//*[@id="block-terrific-content"]/article/div[3]/div[2]/div',
                            child1_abs_or_relative_to_parent = './div[*]',
                            child_two = False,
                            date_abs_or_relative_to_child= './a/div[2]/div/span',
                            link_title_link_abs_or_relative_to_child = './a',
                            date_datetime = False,
                            title_abs_or_relative_to_link = './div[2]/div/h3',
                            link_abs_or_relative_to_link = '.',
                            use_stealth = True,
                            list_cookies = False)

        except Exception as e:
            news_need_update[source] = e

    elif source == 'TrendForce':

        try:

            news = []
            #taking first 50 pages
            for i in range(1,50):
                if i == 1:
                    list_news, flag_days =  models.multiple_childs(flag_days,
                                                                   'https://www.trendforce.com/news/',
                                                                    'TrendForce',
                                                                    '/html/body',
                                                                    child_list = [{'child_path_rel_parent': '//*[@id="insight-index-header"]/div/div[1]/div',
                                                                                    'link_title_rel_child':  './div/a'},
                                                                                {'child_path_rel_parent': '//*[@id="insight-index-header"]/div/div[2]/div[*]/div[*]',
                                                                                    'link_title_rel_child':   './div/a'},
                                                                                {'child_path_rel_parent': './div[3]/div/div[2]/div[3]/div/div[2]/div[1]/div/div[*]/div',
                                                                                    'date_rel_child': './div/div',
                                                                                    'link_title_rel_child':   './div/div/h2/a',
                                                                                    'date_datetime':  False }
                                                                                ])
                    news.extend(list_news)

                elif flag_days == True:
                    list_news, flag_days = models.multiple_childs(flag_days, f'https://www.trendforce.com/news/page/{i}/',
                            'TrendForce',
                            '/html/body',
                            child_list = [{'child_path_rel_parent': './div[3]/div/div[2]/div[3]/div/div[2]/div[1]/div/div[*]/div',
                                            'date_rel_child': './div/div',
                                            'link_title_rel_child':   './div/div/h2/a',
                                            'date_datetime':  False }
                                        ])
                    news.extend(list_news)

                else:
                    break

        except Exception as e:
            news_need_update[source] = e

    elif source == 'TechNews':

        '''
        max_pages set to 5 so will extract at most 5 pages

        '''

        try:
            def technews_child_configs(page_num):
                '''
                Logic for the child elements of each URL based on the page number.
                '''
                if page_num == 1:
                    return [
                        # First page - Include both parts (Part 1 and Part 2)
                        {
                            'child_path_rel_parent': 'xpath=//*[@id="album_test1"]/div/ul/li[*]/div[2]/a',
                            'link_title_rel_child': 'xpath=.',
                            'title_rel_link': 'xpath=./div[2]',
                            'link_rel_link': 'xpath=.'
                        },
                        {
                            'child_path_rel_parent': 'xpath=//*[@id="album_test1"]/div/ul/li[*]/div[3]/ul/li[*]',
                            'link_title_rel_child': 'xpath=./a',
                            'title_rel_link': 'xpath=.',
                            'link_rel_link': 'xpath=.'
                        },
                    ]
                else:
                    # For subsequent pages, use only the second part
                    return [
                        {
                            'child_path_rel_parent': 'xpath=./article[*]',
                            'link_title_rel_child': 'xpath=./div/header/table/tbody/tr[1]/td/h1/a',
                            'date_rel_child': "xpath=.//span[contains(text(), '發布日期')]/following-sibling::span[@class='body'][1]",
                            'title_rel_link': 'xpath=.',
                            'link_rel_link': 'xpath=.',
                            'date_datetime': False
                        }
                    ]

            #max_pages=5 will extract at msot 5 pages
            news, flag_days = await notebook.multiple_childs(
                url='https://cdn.technews.tw/',
                source='TechNews',
                parent_xpath='xpath=//*[@id="primary"]',
                child_configs=technews_child_configs,
                flag_days = flag_days,
                translate=True,
                max_pages=5
            )

        except Exception as e:
             news_need_update[source] = e

    elif source == 'TheElec':

        try:

            def TheElec_child_configs(page_num=any):
                return [{ 'child_path_rel_parent': 'xpath=./div[*]',
                            'date_rel_child': 'xpath=./div[3]',
                            'link_title_rel_child': 'xpath=./div[2]/a',
                            'title_rel_link': 'xpath=./strong',
                            'link_rel_link': 'xpath=.',
                            'date_datetime': False
                        }]


            # Use `notebook.multiple_childs` for fetching
            news, flag_days = await notebook.multiple_childs(
                url='https://www.thelec.net/news/articleList.html?view_type=sm',
                source='TheElec',
                parent_xpath='xpath=//*[@id="user-container"]/div[3]/div[2]/section/article/div[2]/section',
                child_configs= TheElec_child_configs,
                flag_days = flag_days,
                translate=True,
                max_pages=5)

        except Exception as e:
             news_need_update[source] = e

    elif source == 'ETNews':

        '''

        Does not have dates, can edit pages_ETNews to adjust hte number of scrolling, default set

        '''
        news, flag_days = models.multiple_childs(flag_days, 'https://english.etnews.com/news/section.html?id1=07',
                    'ETNews',
                    '/html/body/main',
                    [ {'child_path_rel_parent': '//*[@id="contents_list"]/li[*]',
                        'link_title_rel_child': './a',
                        'title_rel_link': './div[2]/strong',
                        'link_rel_link':  '.',
                        }]
                        ,
                    use_stealth = True,
                    list_cookies = False,
                    translate = False,
                    pages_ETNews = 5)

    elif source == 'TomsHardware':

        '''
        Change value in range(1, value) to choose how many pages it can have at most
        '''

        news = []
        for i in range(1,10):
            if flag_days == True:
                list_news, flag_days = models.multiple_childs(flag_days, f'https://www.tomshardware.com/news/page/{i}',
                                'TomsHardware',
                                '//*[@id="river-latest-filtered-listing"]/div/section/div',
                                [ {'child_path_rel_parent': './div[*]',
                                    'date_rel_child': './a[1]/article/div[2]/header/p/time',
                                    'link_title_rel_child': './a[1]',
                                    'title_rel_link': './article/div[2]/header/h3',
                                    }]
                                    ,
                                use_stealth = False,
                                list_cookies = False,
                                translate = False)
                news.extend(list_news)

            else:
                break

    elif source == 'Zdnet':

        '''
        max_pages set to 50 so will extract at most 50 last pages

        '''

        try:

            def Zdnet_child_configs(page_num):

                if page_num == 1:
                    return [
                        # First page - Include both parts (Part 1 and Part 2)
                        {
                            'child_path_rel_parent': 'xpath=./div[*]',
                            'link_title_rel_child': 'xpath=./div[2]/a',
                            'title_rel_link': 'xpath=./h3',
                            'date_rel_child': 'xpath=./div[2]/p/span',
                            'date_datetime': False,
                            'link_rel_link': 'xpath=.'
                        }
                    ]
                else:
                    # For subsequent pages, use only the second part
                    return [
                        {
                            'child_path_rel_parent': 'xpath=./div[1]/div[*]',
                            'link_title_rel_child': 'xpath=./div[2]/a',
                            'title_rel_link': 'xpath=./h3',
                            'link_rel_link': 'xpath=.',
                            'date_rel_child': 'xpath=./div[2]/p/span',
                            'date_datetime': False
                        }
                    ]

            #max_pages=5 will extract at msot 5 pages
            news, flag_days = await notebook.multiple_childs(
                url='https://zdnet.co.kr/news/?lstcode=0050',
                source='Zdnet',
                parent_xpath='/html/body/div[5]/div/div[1]/div[2]',
                child_configs= Zdnet_child_configs,
                translate=True,
                flag_days = flag_days,
                max_pages=5
            )

        except Exception as e:
             news_need_update[source] = e

    elif source == 'MoneyDJ':

            '''
            max_pages set to 50 so will extract at most 50 last pages

            '''

            try:

                def MoneyDJ_child_configs(page_num):
                    return [
                        # First page - Include both parts (Part 1 and Part 2)
                        {
                            'child_path_rel_parent': 'xpath=./tr[position() > 1]',
                            'link_rel_link': r'href="([^"]+)"',
                            'title_rel_link': r'<a [^>]*title="[^"]+"[^>]*>(.*?)</a>',
                            'date_rel_child': 'xpath=./td[1]',
                            'date_datetime': False
                        }
                    ]


                #max_pages=5 will extract at msot 5 pages
                news,flag_days = await notebook.multiple_childs(
                    url='https://www.moneydj.com/kmdj/news/newsreallist.aspx?a=mb070100',
                    source='MoneyDJ',
                    parent_xpath='//*[@id="MainContent_Contents_sl_gvList"]/tbody',
                    child_configs= MoneyDJ_child_configs,
                    translate=True,
                    flag_days = flag_days,
                    max_pages=5
                )

            except Exception as e:
                news_need_update[source] = e

    elif source == 'Sina':

            '''
            max_pages set to 50 so will extract at most 50 last pages

            '''

            try:

                def Sina_child_configs(page_num):
                    return [
                        # First page - Include both parts (Part 1 and Part 2)
                        {   'child_path_rel_parent': 'xpath=./h1[*]',
                            'link_rel_link': r'href="([^"]+)"',
                            'title_rel_link' : r'>([^<]+)</a>',
                            'date_datetime': False
                        }
                    ]


                #max_pages=5 will extract at msot 5 pages
                news, flag_days = await notebook.multiple_childs(
                    url='https://news.sina.com.cn/',
                    source='Sina',
                    parent_xpath='//*[@id="syncad_1"]',
                    child_configs= Sina_child_configs,
                    translate=True,
                    flag_days = flag_days,
                    max_pages=5
                )

            except Exception as e:
                news_need_update[source] = e

    elif source == 'SemiWiki':

        try:

            def Semiwiki_child_configs(page_num=any):
                return [{ 'child_path_rel_parent': 'xpath=./div[*]',
                            'date_rel_child': 'xpath=./div[4]/a/time',
                            'link_title_rel_child': 'xpath=./div[2]/div[1]/a',
                            'date_datetime': True
                        }]

            # Use `notebook.multiple_childs` for fetching
            news, flag_days = await notebook.multiple_childs(
                url='https://semiwiki.com/forum/index.php?forums/semiwiki-main-forum-ask-the-experts.2/',
                source='SemiWiki',
                parent_xpath='xpath=//*[@id="top"]/div[5]/div/div[4]/div/div/div/div[2]/div[2]/div/div',
                child_configs= Semiwiki_child_configs,
                flag_days = flag_days,
                translate=True,
                max_pages=5)

        except Exception as e:
             news_need_update[source] = e

    elif source == 'DigiTimesAsia':

        '''

        Taking news only last five days were news were posted

        '''

        global last_assigned_date
        last_assigned_date['DigiTimesAsia']  = datetime.now() + timedelta(days=1)

        try:
            def DigiTimesAsia_child_configs(page_num):
                '''
                Logic for the child elements of each URL based on the page number.
                '''
                return [
                    # First page - Include both parts (Part 1 and Part 2)
                    {
                        'child_path_rel_parent': 'xpath=./div[2]/div/div[2]/div[*]',
                        'link_title_rel_child': 'xpath= ./a'
                    },
                    {
                        'child_path_rel_parent': 'xpath=./div[3]/div/div[2]/div[*]',
                        'link_title_rel_child': 'xpath=./a'
                    },
                    {
                        'child_path_rel_parent': 'xpath=./div[4]/div/div[2]/div[*]',
                        'link_title_rel_child': 'xpath=./a'
                    },
                    {
                        'child_path_rel_parent': 'xpath=./div[5]/div/div[2]/div[*]',
                        'link_title_rel_child': 'xpath=./a'
                    },
                    {
                        'child_path_rel_parent': 'xpath=./div[6]/div/div[2]/div[*]',
                        'link_title_rel_child': 'xpath=./a'
                    }
                ]

            #max_pages=5 will extract at msot 5 pages
            news, flag_days = await notebook.multiple_childs(
                url='https://www.digitimes.com/calendar.asp?d=7d',
                source='DigiTimesAsia',
                parent_xpath='xpath=//*[@id="calendar" and @class="col col-left"]',
                child_configs= DigiTimesAsia_child_configs,
                translate = False,
                flag_days = flag_days,
                max_pages= 5
            )

        except Exception as e:
             news_need_update[source] = e


     ############################   OTHER  #############################

    elif source == 'SemiPress':

        '''
        Only getting last page

        '''
        try:
            news, flag_days = models.multiple_childs(flag_days, url = 'https://www.semi.org/en/news-media-press/semi-press-releases/press-archive',
                       source = 'SemiPress',
                       parent_xpath= '//*[@id="block-views-block-press-releases-semi-paged"]/div/div/div/div[2]/table',
                       child_list = [{ 'child_path_rel_parent': "table.cols-0 tbody tr"}],
                       list_cookies=False,
                       use_stealth = True)

        except Exception as e:
             news_need_update[source] = e

    elif source == 'SIA':

        '''
        Only getting last page

        '''
        try:

            def SIA_child_configs(page_num):
                return [
                    { 'child_path_rel_parent': 'xpath=./div[*]',
                        'title_rel_link': 'xpath=./h3',
                        'link_title_rel_child': 'xpath=./div/div[2]/a',
                        'date_rel_child': 'xpath=./div/div[2]/div[1]',
                        'date_datetime': False
                    }
                ]


            #max_pages=5 will extract at msot 5 pages
            news, flag_days = await notebook.multiple_childs(
                url='https://www.semiconductors.org/category/press-releases/',
                source='SIA',
                parent_xpath='//*[@id="fullwidth"]',
                flag_days = flag_days,
                child_configs= SIA_child_configs
            )

        except Exception as e:
                news_need_update[source] = e

    ############################   INSIGHT DATA  #############################


    elif source == 'Futurum':

        try:

            def Fut_child_configs(page_num):
                return [
                    { 'child_path_rel_parent': 'xpath=./div[*]',
                        'link_title_rel_child': 'xpath=./div/div[5]/div/h4/a',
                        'date_rel_child': 'xpath=./div/div[2]/div/ul/li/span[2]/time',
                        'date_datetime': False
                    }
                ]


            #max_pages=5 will extract at msot 5 pages
            news, flag_days = await notebook.multiple_childs(
                url='https://futurumgroup.com/news-insights/insights/',
                source='Futurum',
                flag_days = flag_days,
                parent_xpath='//html/body/div[7]/div[2]/div/div/div/div/div/div[2]/div/div/div[1]',
                child_configs= Fut_child_configs
            )

        except Exception as e:
                insight_need_update[source] = e

    elif source == 'FabricatedKnowledge':

        try:

            def Fab_child_configs(page_num):
                return [
                    { 'child_path_rel_parent': 'xpath=./div[position() mod 2 = 1]/div/div[position() mod 2 = 1]',
                        'link_title_rel_child': 'xpath=./div/div[1]/div[1]/a',
                        'date_rel_child': 'xpath=./div/div[1]/div[3]/time',
                        'date_datetime': True
                    }
                ]


            news, flag_days = await notebook.multiple_childs(
                url='https://www.fabricatedknowledge.com/archive',
                source='FabricatedKnowledge',
                flag_days = flag_days,
                parent_xpath='//*[@id="main"]/div[2]/div/div/div/div[2]',
                child_configs= Fab_child_configs
            )

        except Exception as e:
                insight_need_update[source] = e

    elif source == 'SemiconSam':
        try:
            news, flag_days = models.structure_1(flag_days, 'https://semiconsam.substack.com/archive', 'SemiconSam',
                    parent_abs = '//*[@id="main"]/div[2]/div/div/div/div/div[1]',
                    child1_abs_or_relative_to_parent = './div/div[position() mod 2 = 1]',
                    child_two = False,
                    date_abs_or_relative_to_child= './div/div[1]/div[3]/time',
                    link_title_link_abs_or_relative_to_child = './div/div[1]/div[1]/a',
                    date_datetime = True)

        except Exception as e:
                insight_need_update[source] = e

    elif source == 'ProPro':

        try:
            url = "https://procurementpro.com/category/industry-insights/"

            # Set headers to mimic a real browser
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            # Fetch page content
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")  # Parse HTML
            pdf_divs = soup.find_all("div", class_=re.compile(".*blog-layout-2.*wow.*fadeInUp.*post.*has-post-thumbnail.*category-industry-insights.*"))

            news = []

            for div in pdf_divs:
                # Extract the title
                title_tag = div.find("h2", class_="entry-title title-animation-black-bold")
                title = title_tag.get_text(strip=True)

                # Extract the date
                date_tag = div.find("li", class_="post-date")
                date = date_tag.get_text(strip=True).replace("•", "").strip()

                # Extract the link
                link = soup.find("a", class_="img-opacity-hover")["href"]


                publication_time_ago, publication_time, published_time, flag_days = time_ago(None, 'ProPro', True)
                publication_time_ago, publication_time = " ", " "


                news.append(models.Post(title, publication_time, date , link, published_time, 'ProPro'))


        except Exception as e:
                insight_need_update[source] = e

    elif source == 'CSR':
        news = [models.Post(headline = 'REPORT | Chip Scale Review Report' ,publication_time = " ", publication_time_ago = " ", link = 'https://chipscalereview.com/2024-issues-2/', published_time =  (datetime.now() - timedelta(days = 2)).astimezone(pytz.timezone('Europe/Berlin')) , source = 'CSR') ]

    elif source == 'SemiconDigest':
        news = [models.Post(headline = 'MAGAZINE | Semicon Digest Magazine' ,publication_time = " ", publication_time_ago = " ", link = 'https://www.semiconductor-digest.com/magazine', published_time =  (datetime.now() - timedelta(days = 2)).astimezone(pytz.timezone('Europe/Berlin')) , source = 'SemiconDigest') ]

    elif source == 'SemiconToday':

        url = "https://semiconductor-today.com/PDFdownload.shtml"

        # Set headers to mimic a real browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # Fetch page content
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")  # Parse HTML
        pdf_divs = soup.find_all("div", class_="pdfCovers pure-u-1-2 pure-u-md-1-4 pure-u-lg-1-5")

        news = []

        for div in pdf_divs:
            link_tag = div.find("a")
            Title = link_tag.get_text(strip=True, separator= " ")  # Get text, keeping line breaks
            publication_time_ago, publication_time, published_time, flag_days = time_ago(None, 'SemiconToday', True)
            publication_time_ago, publication_time = " ", " "
            link = 'https://semiconductor-today.com/PDFdownload.shtml' + link_tag["href"]

            news.append(models.Post(Title, publication_time, publication_time_ago, link, published_time, 'SemiconToday'))

    elif source == 'SSsilicon':
        # Set headers to mimic a real browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        response = requests.get("https://siliconsemiconductor.net/news/interviews/1", headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")  # Parse HTML
        pdf_divs = soup.find_all("div", class_="col-lg-4 col-md-6 col-sm-12")

        news = []

        for div in pdf_divs:

            date_text = div.find("div", style="font-size:11px;font-weight:bold;")
            date_text = date_text.text.strip()
            title_link_tag = div.find("a", class_="news-list-title-link sub", style="font-size:20px;")
            title = title_link_tag.text.strip()
            link = 'https://siliconsemiconductor.net' + title_link_tag["href"]

            publication_time_ago, publication_time, published_time, flag_days = time_ago(None, 'SSsilicon', True)
            publication_time_ago, publication_time = date_text, " "

            news.append(models.Post(title, publication_time, publication_time_ago, link, published_time, 'SSsilicon'))

    elif source == 'CScompound':
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # Fetch page content
        response = requests.get("https://compoundsemiconductor.net/news/interviews/1", headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")  # Parse HTML
        pdf_divs = soup.find_all("div", class_="col-lg-4 col-md-6 col-sm-12")
        news = []


        for div in pdf_divs:
            date = div.find("div", style="font-size:11px;font-weight:bold;")
            date_text = div.text.strip() if date else "No date found"
            title_link_tag = div.find("a", class_="news-list-title-link sub", style="font-size:20px;")
            title = str(title_link_tag.text.strip())
            link = 'https://compoundsemiconductor.net' + title_link_tag["href"]

            publication_time_ago, publication_time, published_time, flag_days = time_ago(None, 'CScompound', True)
            publication_time_ago, publication_time = re.match(r"(.*?)(\n)", date_text).group(1), " "

            news.append(models.Post(title, publication_time, publication_time_ago, link, published_time, 'CScompound'))

    elif source == 'SSsilicon_news':
        news = [models.Post(headline = 'MAGAZINE | Silicon Semiconductor Magazine' ,publication_time = " ", publication_time_ago = " ", link = 'https://siliconsemiconductor.net/magazine#', published_time =  (datetime.now() - timedelta(days = 2)).astimezone(pytz.timezone('Europe/Berlin')) , source = 'SSsilicon_news') ]


    else:
        news = []  # Default to an empty list if source is unknown


    print(f" Finished {source} taking: {time.time() - start_time} sec")

    print(f'Giving news for {source} of len {len(news)}')

    return news



###############################   FUNCTION TO UPDATE NEWS  ###################################



async def update_news(sources):
    """
    Function to update the global news_data with fresh news from multiple sources.
    """
    news_data = []

    # Run all tasks and collect results
    #print(config.sources)
    flag_days = True
    results = await asyncio.gather(*(fetch_news(source, flag_days) for source in sources), return_exceptions=True)

    # Process results
    for result in results:
        if isinstance(result, list):
            news_data.extend(result)  # Add valid news data
        else:
            print(f"Error while fetching news: {result}")  # Log errors

    # Sort by published time
    news_data.sort(key=lambda post: post.published_time, reverse=True)

    return news_data



async def update_news_async():
    news_data = await update_news(config.sources)
    models.save_news_data(news_data, news = True)
    return news_data  # Fetch news asynchronously


async def update_insights_async():
    sources_insights = await update_news(config.sources_insights)
    models.save_news_data(sources_insights, news = False)
    return sources_insights












# def update_news():

#     """Function that updates the global news_data with fresh news from multiple sources"""

#     global flag_days
#     news_data = []

#     for source in config.sources:
#         print(f'{source} being loaded')
#         flag_days = True
#         news_data.extend(fetch_news(source))  # Fetch news from each source

#     news_data.sort(key=lambda post: post.published_time, reverse=True)

#     return news_data
