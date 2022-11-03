import logging
import traceback
import requests
import bs4
import re
from requests.compat import urljoin

log = logging.getLogger('main')

base_domain = 'https://gogoanime.tel/'

def get_page(url):
  log.debug(f'Getting page from url: {url}')
  try:
    page = requests.get(url)
    return bs4.BeautifulSoup(page.content, 'html.parser')
  except Exception as e:
    log.warning((traceback.format_exc()))
    return None

def get_anime(url):
  log.debug(f'Getting Gogoanime anime, url: {url}')
  page = get_page(url)
  name = page.find(class_='anime_info_body_bg').find_next('h1').text
  episodes = page.find(id='load_ep').find_previous('li').find_next('a')['ep_end']
  image_url = page.find(class_='anime_info_body_bg').find_next('img')['src']
  return {
      'gogo_name': name,
      'gogo_episodes': episodes,
      'gogo_url': url,
      'gogo_image_url': image_url,
      }

def search_anime(query):
  log.info(f'Searching Manganato manga, query: "{query}"')
  search_url = f'{base_domain}search.html?keyword={query}'
  page = get_page(search_url)
  search_items = page.find(class_='items').find_all('li')
  search_results = []
  for item in search_items:
    href = item.find_next('a')['href']
    search_results.append(get_anime(urljoin(base_domain, href)))
  return search_results
