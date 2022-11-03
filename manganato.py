import logging
import traceback
import requests
import bs4
import re

log = logging.getLogger('main')

base_domain = 'https://manganato.com/'

def get_page(url):
  log.debug(f'Getting page from url: {url}')
  try:
    page = requests.get(url)
    return bs4.BeautifulSoup(page.content, 'html.parser')
  except Exception as e:
    log.warning((traceback.format_exc()))
    return None

def get_manga(url):
  log.debug(f'Getting Manganato manga, url: {url}')
  page = get_page(url)
  name = page.find(class_='story-info-right').find_next('h1').text
  chapters = len(page.find(class_='row-content-chapter').find_all('li'))
  image_url = page.find(class_='info-image').find_next('img')['src']
  return {
      'mgn_name': name,
      'mgn_chapters': chapters,
      'mgn_url': url,
      'mgn_image_url': image_url
      }

def search_manga(query):
  query = re.sub("[^0-9a-z]",'_', query)
  search_url = f'{base_domain}search/story/{query}'
  log.info(f'Searching Manganato manga, query: "{query}"')
  page = get_page(search_url)
  search_items = page.find(class_='panel-search-story').find_all(class_='search-story-item')
  search_results = []
  for item in search_items:
    manga_url = item.find(class_='item-title')['href']
    search_results.append(get_manga(manga_url))
  return search_results
