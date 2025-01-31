import importlib

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
import Exporter
from selenium_stealth import stealth
import time
from selenium.common.exceptions import NoSuchElementException
from deep_translator import GoogleTranslator

importlib.reload(Exporter)
from bs4 import BeautifulSoup

#CREATE CLASS TO STORE DATA OF EACH POST
class Post:
    def __init__(self, headline, publication_time, publication_time_ago, link, published_time, source):
        self.headline = headline
        self.publication_time = publication_time
        self.link = link
        self.publication_time_ago = publication_time_ago
        self.published_time = published_time
        self.source = source

    def __repr__(self):
        return f"<Post(headline={self.headline}, time={self.publication_time}, ago ={self.publication_time_ago}, link={self.link}, t = {self.published_time}, source = {self.source})>"

    def to_dict(self):
        """Convert the Post object to a dictionary."""
        return {
            "headline": self.headline,
            "publication_time": str(self.publication_time),  # Ensure datetime is converted to string
            "publication_time_ago": self.publication_time_ago,
            'published_time': self.published_time,
            "source": self.source,
            "link": self.link
        }

    @classmethod
    def from_dict(cls, data):
        """Create a Post object from a dictionary."""
        return cls(
            headline=data["headline"],
            publication_time=data["publication_time"],
            publication_time_ago=data["publication_time_ago"],
            link=data["link"],
            published_time=data["published_time"],
            source=data["source"]
        )


'''

Similar html structure

'''


def child_post_model(parent_element,
                child_path_rel_parent,
                date_rel_child,
                link_title_rel_child,
                title_rel_link,
                link_rel_link,
                date_datetime,
                source,
                flag_days,
                translate = False):

            news = []

            #print('Looking for childs')
            #print(parent_element.get_attribute('outerHTML'))


            #BS4
            if source == 'SemiPress':
                #print('Here trying')
                outer_html = parent_element.get_attribute('outerHTML')
                soup = BeautifulSoup(outer_html, "html.parser")
                child_elements = soup.select(child_path_rel_parent)


            else: child_elements = parent_element.find_elements(By.XPATH, child_path_rel_parent)

            #print('There is child_elements number:',len(child_elements))

            for child in child_elements:

                try:
                    #BS4
                    if source == 'SemiPress':
                        date = child.find("td", class_="views-field-field-date").get_text(strip=True)
                        Title = child.find("td", class_="views-field-title").find("a").get_text(strip=True)
                        link =  'https://www.semi.org' + child.find("td", class_="views-field-title").find("a")["href"]  # Relative URL

                    else:
                        try:
                            if date_datetime:
                                date = child.find_element(By.XPATH, date_rel_child).get_attribute('datetime')
                            else:
                                date = child.find_element(By.XPATH, date_rel_child).text.strip()
                                if translate:  date = GoogleTranslator(source='zh-TW', target='en').translate(date)
                        except:
                            date = None


                        link_element = child.find_element(By.XPATH, link_title_rel_child)

                        #print('getting link title success')

                        Title = link_element.find_element(By.XPATH, title_rel_link)
                        #print('getting title success')
                        Title_try = Title.text
                        #print('Title_try imposible')

                        if not Title_try.strip():
                            Title = Title.get_attribute("textContent")
                        else:
                            Title = Title_try
                        #print('Title got succesfully')

                        link = link_element.find_element(By.XPATH, link_rel_link).get_attribute('href')
                        #print('link sucess')

                    if translate:
                        Title = GoogleTranslator(source='zh-TW', target='en').translate(Title)

                    #print('before time ago')
                    publication_time_ago, publication_time, published_time, flag_days = Exporter.time_ago(date, source, flag_days)
                    #print('sucess time ago')

                    if flag_days:
                        #print('adding new')
                        #print(Post(Title, publication_time, publication_time_ago, link, published_time, source))
                        news.append(Post(Title, publication_time, publication_time_ago, link, published_time, source))

                    else:
                        break

                except Exception as e:
                    print('Problem getting child', e)

            return news, flag_days


def initiation( url, use_stealth = True, list_cookies = False):

    if use_stealth:
        options = webdriver.ChromeOptions()
        options.add_argument("start-maximized")
        options.add_argument('--headless=new')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        #will need to change this in hte future to ChomeDriver path from Docker container
        driver = webdriver.Chrome(options=options, service=Service(executable_path='/opt/homebrew/bin/chromedriver'))
        #print('got driver')
        stealth(driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
                )

        driver.get(url)
        #print('goturl')
        time.sleep(10)

    else:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        driver = webdriver.Chrome(service=Service(), options=options)
        driver.get(url)

    if  list_cookies:
        #can give it a list with dictionary elements of cookies or as button xpath if visisble
        if type(list_cookies) == list:
            for dict_cookie in list_cookies:
                driver.add_cookie(dict_cookie)
        else:
            button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, list_cookies))
            )
            # Click the button
            button.click()


    return driver


def structure_1(flag_days,
                url,
                source,
                parent_abs = '//*[@id="main"]/div[2]/div/div/div/div[2]',
                child1_abs_or_relative_to_parent = './div[1]/div/div[*]',
                child_two = True,
                child2_abs_or_relative_to_parent = './div[3]/div/div[*]',
                date_abs_or_relative_to_child= './div/div[1]/div[3]/time',
                link_title_link_abs_or_relative_to_child = './div/div[1]/div[1]/a',
                date_datetime = True,
                title_abs_or_relative_to_link = '.',
                link_abs_or_relative_to_link = '.',
                use_stealth = True,
                list_cookies = False):


    '''

        Need to use selenium because website uses JavaScript to laod content

        Selenium includes explicit waiting mechanisms to wait for contect to load

        Also need to use XPATH, tried using class names but they are automatically udpated

        NOTE; getting at most the news fro last 2 months due to html structure, more months then - './div[5]/div/div[*]', './div[7]/div/div[*]' etc


    '''

    news = []

    driver = initiation(use_stealth = use_stealth, url = url, list_cookies = list_cookies)

    #print('Driver initiated succesfully')

    try:
        parent_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, parent_abs)))

        #print('Parent found successfully')

        #Here we need to find all child hence XPATH with div[*] to get div[1], div[2] etc
        if child_two:

            #print('Inside childs')
            #print(f'FD is {flag_days}')

            #child_elements = parent_element.find_elements(By.XPATH, child1_abs_or_relative_to_parent)  +  parent_element.find_elements(By.XPATH, child2_abs_or_relative_to_parent)
            news, flag_days =  child_post_model(parent_element = parent_element,
                    child_path_rel_parent = child1_abs_or_relative_to_parent,
                    date_rel_child = date_abs_or_relative_to_child,
                    link_title_rel_child = link_title_link_abs_or_relative_to_child,
                    title_rel_link = title_abs_or_relative_to_link,
                    link_rel_link = link_abs_or_relative_to_link,
                    date_datetime = date_datetime,
                    flag_days = flag_days,
                    source = source)

            #print('Got form child two news n:', len(news))
            #print(f'FD is {flag_days}')

            if flag_days == True:
                news_list, flag_days = child_post_model(
                        parent_element = parent_element,
                        child_path_rel_parent = child2_abs_or_relative_to_parent,
                        date_rel_child = date_abs_or_relative_to_child,
                        link_title_rel_child = link_title_link_abs_or_relative_to_child,
                        title_rel_link = title_abs_or_relative_to_link,
                        link_rel_link = link_abs_or_relative_to_link,
                        date_datetime = date_datetime,
                        flag_days = flag_days,
                        source = source)


                news.extend(news_list)
                #print('Adding more news', len(news_list))

        else:
            #child_elements = parent_element.find_elements(By.XPATH, child1_abs_or_relative_to_parent)
            news, flag_days =  child_post_model(
                    parent_element = parent_element,
                    child_path_rel_parent = child1_abs_or_relative_to_parent,
                    date_rel_child = date_abs_or_relative_to_child,
                    link_title_rel_child = link_title_link_abs_or_relative_to_child,
                    title_rel_link = title_abs_or_relative_to_link,
                    link_rel_link = link_abs_or_relative_to_link,
                    date_datetime = date_datetime,
                    flag_days = flag_days,
                    source = source)



    finally:
        driver.quit()

    return news, flag_days


def multiple_childs(flag_days,
                    url,
                    source,
                    parent_xpath,
                    child_list,
                    use_stealth = True,
                    list_cookies = False,
                    translate = False,
                    pages_ETNews = 5):


    '''

    Input child_list should be a list of dictionary elements of form:
    child_list = [{'child_path_rel_parent': 'need_XPATH',
                        'date_rel_child': 'need_XPATH',
                        'link_title_rel_child': 'need_XPATH',
                        'title_rel_link': 'default_value '.',
                        'link_rel_link': default_value '.',
                        'date_datetime': default_value True
                        }]


    list_cookies can be either:
        1) list of dictionaries, where each element is one cookie,
        2) or xpath of cookie button (easier but sometimes not visible)

    '''

    news = []



    driver = initiation(use_stealth = use_stealth, url = url, list_cookies = list_cookies)

    #print('Driver initiated')

    try:

        #need scrolling down for ETNews
        if source == 'ETNews':

            for i in range(pages_ETNews):
                load_more_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="ContentsViewBtn"]'))
                )
                load_more_button.click()
                time.sleep(5)


        parent_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, parent_xpath)))
        #print(parent_element.get_attribute("outerHTML"))
        #print(parent_element.page_source)

        #get post for every child

        #print('Parent found')
        #print('There is childs n:', len(child_list))

        for child in child_list:

            if flag_days == True:
                child.setdefault('date_datetime', True)
                child.setdefault('link_rel_link', '.')
                child.setdefault('title_rel_link', '.')
                child.setdefault('link_title_rel_child', '.')
                child.setdefault('date_rel_child', None)

                list_news, flag_days = child_post_model(
                        parent_element = parent_element,
                        child_path_rel_parent = child['child_path_rel_parent'],
                        date_rel_child = child['date_rel_child'],
                        link_title_rel_child = child['link_title_rel_child'],
                        title_rel_link = child['title_rel_link'],
                        link_rel_link = child['link_rel_link'],
                        date_datetime = child['date_datetime'],
                        source = source,
                        translate = translate,
                        flag_days = flag_days)


                news.extend(list_news)

            else:
                #print(f'Outside flag {source}')
                break

    finally:
        driver.quit()

    return news, flag_days
