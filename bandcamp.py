import logging
import requests
from requests.compat import urljoin
import bs4
import re
import db
import constants
import logic

log = logging.getLogger('main')

def get_bandcamp_page(url):
  page = requests.get(url)
  return bs4.BeautifulSoup(page.content, 'html.parser')

def get_artist_name(page):
  name_container = page.find(id="band-name-location")
  name = name_container.find(class_='title').text
  return name

def get_artist_releases(page):
  music = page.find(id='music-grid')
  releases= []
  for release in music.find_all('a'):
    releases.append(release['href'])
  return releases

def get_release_info(page):
  name_section = page.find(id='name-section')
  release_name = name_section.find(class_='trackTitle').text
  release_name = re.sub(r'\s{2}', '', release_name)
  release_author = name_section.find('a').text
  release_artwork = page.find(id='tralbumArt')
  image_url = release_artwork.find('img')['src']
  release_info = {
      'name': release_name,
      'author': release_author,
      'image_url': image_url,
      'tracks': []
      }
  track_table = page.find(id='track_table')
  if track_table:
    for title in track_table.find_all(class_='track-title'):
      release_info['tracks'].append(title.text)
  return release_info
