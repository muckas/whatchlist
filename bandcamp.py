import logging
import traceback
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
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
  log.debug(f'Getting bandcamp page from url: {url}')
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

def get_music_whatchlist(user_id):
  text = '*Music whatchlist*\n'
  user_music = logic.users[user_id]['music']
  for bandcamp_id in user_music:
    music_entry = user_music[bandcamp_id]
    artist_name = tgbot.markdown_replace(music_entry['name'])
    artist_link = music_entry['url']
    text += f'\n\t\t[{artist_name}]({artist_link})'
  keyboard = tgbot.get_inline_options_keyboard(
      {
        'Anime':'whatchlist|anime',
        'Manga':'whatchlist|manga',
        'Music':'whatchlist|music',
      },
      columns = 3
    )
  keyboard += tgbot.get_inline_options_keyboard(
      {'Remove an entry':'whatchlist_remove|0:music:noid'},
      columns = 1
    )
  reply_markup = InlineKeyboardMarkup(keyboard)
  return text, reply_markup, 'MarkdownV2'

def check_music_whatchlist(user_id):
  log.debug(f'Checking music for user {user_id}')
  user_music = logic.users[user_id]['music']
  for artist in user_music:
    try:
      artist_name = user_music[artist]['name']
      artist_url = user_music[artist]['url']
      last_release = user_music[artist]['last_release']
      page = get_bandcamp_page(artist_url)
      releases = get_artist_releases(page)
      new_releases = []
      for release in releases:
        if release == last_release:
          break
        else:
          new_releases.append(release)
      if new_releases:
        new_releases.reverse()
        for release in new_releases:
          log.info(f'User {user_id}: New music release for {artist}: {release}')
          release_url = urljoin(artist_url, release)
          release_page = get_bandcamp_page(release_url)
          release_info = get_release_info(release_page)
          release_name = tgbot.markdown_replace(release_info['name'])
          release_author = tgbot.markdown_replace(release_info['author'])
          release_image_url = (release_info['image_url'])
          release_tracks = (release_info['tracks'])
          text = f'\t\tNew music [release]({release_url}) from [{artist_name}]({artist_url})\!'
          print(text)
          text += f'\n*{release_name}* by *{release_author}*\n'
          for track in release_tracks:
            track_name = tgbot.markdown_replace(track)
            text += f'\n\t\t{track_name}'
          logic.users[user_id]['music'][artist]['last_release'] = release
          db.write('users', logic.users)
          tgbot.send_image(user_id, text=text, url=release_image_url, parse_mode='MarkdownV2')
    except Exception:
      log.warning((traceback.format_exc()))
