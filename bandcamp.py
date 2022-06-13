import logging
import traceback
import requests
from requests.compat import urljoin
import bs4
import re
from urllib.parse import urlparse
import db
import tgbot
import constants
import logic

log = logging.getLogger('main')

def get_bandcamp_page(url):
  try:
    page = requests.get(url)
    return bs4.BeautifulSoup(page.content, 'html.parser')
  except Exception as e:
    log.warning((traceback.format_exc()))
    return None

def get_artist_name(page):
  name_container = page.find(id="band-name-location")
  if name_container:
    name = name_container.find(class_='title').text
    return name
  else:
    return None

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

def add_music(user_id):
  tgbot.send_message(user_id, 'Bandcamp link?')
  logic.change_state(user_id, 'add_music')

def add_music_to_whatchlist(user_id, url):
  url = urljoin(url, '/')
  page = get_bandcamp_page(url)
  if page:
    name = get_artist_name(page)
    if name:
      last_release = get_artist_releases(page)[0]
      parsed_url = urlparse(url)
      subdomain = parsed_url.hostname.split('.')[0]
      music_entry = {
          'name': name,
          'url': url,
          'last_release': last_release,
          }
      logic.users[user_id]['music'].update({subdomain: music_entry})
      db.write('users', logic.users)
      tgbot.send_message(user_id, f'{name} added to whatchlist')
    else:
      tgbot.send_message(user_id, f'Incorrect bandcamp url')
  else:
    tgbot.send_message(user_id, f'Incorrect bandcamp url')
