# Required Libraries
from playwright.async_api import async_playwright
from deep_translator import GoogleTranslator
from flask import Flask
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil import parser
import pytz
import config

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from playwright.sync_api import sync_playwright
import time
import re


import importlib

import models
importlib.reload(models)

import Exporter
importlib.reload(Exporter)

import streamlit as st



'''
Things to add to the sources tranformed using notebook file
'''

modifications_link = {
            'TheElec':'https://www.thelec.net' ,
            'Zdnet':' https://zdnet.co.kr' ,
            'MoneyDJ': 'https://www.moneydj.com',
            'SemiWiki': 'https://semiwiki.com',
            'DigiTimesAsia': 'https://www.digitimes.com',
            'BusinessKorea': 'https://www.businesskorea.co.kr'
}


urls_dict =  {
        'TechNews': lambda url, max_pages: [url] + [f"{url}page/{i}" for i in range(1, max_pages + 1)],
        'TheElec':   lambda url, max_pages:  [url] + [f"{url}&page={i}" for i in range(2, max_pages + 1)],
        'Zdnet': lambda url, max_pages: [f"{url}&page={i}" for i in range(1, max_pages + 1)],
        'MoneyDJ': lambda url, max_pages: [url] + [f"{url}index1={i}" for i in range(2, max_pages + 1)],
        'SemiWiki': lambda url, max_pages:  [url] + [f"{url}page-{i}" for i in range(2, max_pages + 1)],
        'BusinessKorea': lambda url, max_pages: [url] + [f"{url}&page={i}" for i in range(2,max_pages + 1)]
 }


# Function to Process Each Child Element (same as before)
async def child_post(parent_locator, child_config, source, flag_days, translate=False):
    """
    Extract posts from child elements based on the given configuration.

    Args:
        parent_locator: Locator for the parent element.
        child_config: Dictionary with child XPath configurations.
        source: Source of the news
        translate: If True, translates text from Chinese to English.

    Returns:
        List of Post objects extracted from the child elements.
    """

    if translate and (source == 'Zdnet'):
        translator = GoogleTranslator(source='ko', target='en')

    elif translate:
        translator = GoogleTranslator(source='zh-TW', target='en')
    else:
        None

    news = []

    # Find all child elements under the parent
    child_elements = await parent_locator.locator(child_config['child_path_rel_parent']).all()

    #print(len(child_elements))
    for child in child_elements:

        if flag_days:

            # Extract date
            date = None

            if child_config.get('date_rel_child'):
                if child_config.get('date_datetime', True):
                    date = await child.locator(child_config['date_rel_child']).get_attribute('datetime')

                else:
                    try:
                        date = await child.locator(child_config['date_rel_child']).text
                    except:
                        date = await child.locator(child_config['date_rel_child']).text_content()

                    date = date.strip() if date else None
                    if translate:
                        date = translator.translate(date)


            # Extract link and title
            #outer_html = await child.evaluate('(el) => el.outerHTML')  # Correct way to get

            if  source == 'MoneyDJ' or source == 'Sina':
                outer_html = await child.evaluate('(el) => el.outerHTML')
                title = re.search(child_config['title_rel_link'], outer_html).group(1)
                link = re.search(child_config['link_rel_link'], outer_html).group(1)

            else:
                link_element = child.locator(child_config['link_title_rel_child'])
                outer_html = await child.evaluate('(el) => el.outerHTML')
                title = await link_element.locator(child_config['title_rel_link']).text_content()
                link = await link_element.locator(child_config['link_rel_link']).get_attribute('href')


            #add beggingnin of dictionry if needed for the link
            beggining_link = modifications_link.get(source)
            if beggining_link:
                link = beggining_link + link

            if translate and title:
                title = translator.translate(title)

            # Convert date into publication time
            publication_time_ago, publication_time, published_time, flag_days = Exporter.time_ago(date, source, flag_days)

            # Append post to the news list
            if flag_days == True:
                news.append(models.Post(title, publication_time, publication_time_ago, link, published_time, source))
            else:
                break

        else:
            break

    return news, flag_days


# Function to Handle Multiple Child Configurations and Pages
async def multiple_childs(url, source, parent_xpath, child_configs, flag_days,  max_pages=50, translate=False):
    """
    Extract posts from multiple pages and child configurations.

    Args:
        url: Starting URL for scraping.
        source: Source of the news (e.g., "TechNews").
        parent_xpath: XPath for the parent container holding all children.
        child_configs: List of configurations for child elements.
            - element from the list should have the following form
                {'child_path_rel_parent': 'need_XPATH',
                'date_rel_child': 'need_XPATH',
                'link_title_rel_child': 'need_XPATH',
                'title_rel_link': 'default_value '.',
                'link_rel_link': default_value '.',
                'date_datetime': default_value True
                }


        max_pages: Maximum number of pages  scrape.
        translate: If True, translates text from Chinese to English.

    Returns:
        List of Post objects extracted from all pages.

    Need to edit urls logic and can change parent_path logic if wanted
    """
    news = []

    # Launch browser with Playwright
    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        async def process_page(page_url, page_num, parent_xpath, flag_days):
            """
            Processes a single page and extracts posts.
            """
            try:
                #Need to get the full path of parent for each of the pages i !!
                if source == 'TechNews':
                    #Need the path assigned in i == 1 to correspond to the first url that will be processed
                    parent_xpath = 'xpath=//*[@id="primary"]' if i == 1 else 'xpath=//html/body/div[2]/div/div[1]/div[2]'

                if source == 'Zdnet':
                    parent_xpath = 'xpath=/html/body/div[5]/div/div[1]/div[2]' if i == 1 else 'xpath=/html/body/div[4]/div/div[2]'

                await page.goto(page_url)

                #print(html)  # Prints the full page source
                #print('Trying to look for parent')

                parent_locator = page.locator(parent_xpath)

                # Wait for the parent element to load
                await parent_locator.wait_for(timeout=15000)
                # Dynamically choose the child_config based on the page number
                print('found parent')

                for child_config in child_configs(page_num):

                    if source == 'DigiTimesAsia':
                        Exporter.last_assigned_date['DigiTimesAsia'] = Exporter.last_assigned_date['DigiTimesAsia'] - timedelta(days=1)

                    # Pass page_num to decide which config to use
                    if flag_days == True:
                        child_config.setdefault('date_datetime', True)
                        child_config.setdefault('link_rel_link', 'xpath=.')
                        child_config.setdefault('title_rel_link', 'xpath=.')
                        child_config.setdefault('date_rel_child', None)

                        # Process the posts from the child configuration
                        child_news, flag_days = await child_post(parent_locator, child_config, source, flag_days, translate)
                        news.extend(child_news)

                    else:
                        break

            except Exception as e:
                print(f"Error processing {page_url}: {e}")

            return flag_days


        #Get the full http for each page
        if urls_dict.get(source):
            urls = urls_dict[source](url, max_pages)

        else:
            urls = [url]

        #i=1 is first url that we process
        for i, page_url in enumerate(urls, start=1):
            if flag_days:
                flag_days = await process_page(page_url, i, parent_xpath, flag_days)
            else:
                break

        await browser.close()

    return news, flag_days
