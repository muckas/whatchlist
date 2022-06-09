import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import tgbot
import mal
from gogoanimeapi import gogoanime
import manganelo
import db
import constants
import uuid

log = logging.getLogger('main')

temp_vars = {}
users = None
gogoanime_domain = 'https://gogoanime.gg/'

def check_temp_vars(user_id):
  if user_id not in temp_vars:
    temp_vars.update({user_id:constants.get_temp_vars()})

def change_state(user_id, new_state):
  temp_vars[user_id]['state'] = new_state
  log.debug(f'New state "{new_state}" for user {user_id}')

def mal_return_anime(title):
  result = {
    'mal_id': title.mal_id,
    'mal_name': title.title,
    'mal_episodes': title.episodes,
    'mal_url': title.url,
    'mal_image_url': title.image_url,
    }
  if result['mal_episodes'] == None:
    result['mal_episodes'] = '?'
  return result

def mal_get_anime(mal_id):
  log.debug(f'Getting MyAnimeList anime, mal_id: {mal_id}')
  return mal_return_anime(mal.Anime(mal_id))

def mal_anime_search(name):
  name = name[:100] # Max query - 100 characters
  log.info(f'Searching MyAnimeList anime, query: "{name}"')
  try:
    mal_search = mal.AnimeSearch(name)
    results = []
    for title in mal_search.results:
      results.append(mal_return_anime(title))
    return results
  except ValueError as e:
    log.warning(f'MyNimeList error: {e}')
    return []

def gogo_return_anime(gogo_id):
  title = gogoanime.get_anime_details(animeid=gogo_id)
  name = title['title']
  episodes = title['episodes']
  return ({
    'gogo_id': gogo_id,
    'gogo_name': name,
    'gogo_episodes': episodes,
    })

def gogo_get_anime(gogo_id):
  log.debug(f'Getting GogoAnime anime, gogo_id: {gogo_id}')
  return gogo_return_anime(gogo_id)

def gogo_search(name):
  log.info(f'Searching GogoAnime anime, query: "{name}"')
  gogo_search = gogoanime.get_search_results(query=name)
  try:
    if gogo_search['status']:
      log.warning(f'Gogoanime returned status: {gogo_search["status"]}, reason {gogo_search["reason"]}')
      return []
  except TypeError:
    pass
  results = []
  for title in gogo_search:
    results.append(gogo_return_anime(title['animeid']))
  return results

def mal_return_manga(title):
  try:
    result = {
      'mal_id': title.mal_id,
      'mal_name': title.title,
      'mal_volumes': title.volumes,
      'mal_chapters': title.chapters,
      'mal_url': title.url,
      'mal_image_url': title.image_url,
      }
  except AttributeError:
    result = {
      'mal_id': title.mal_id,
      'mal_name': title.title,
      'mal_volumes': title.volumes,
      'mal_chapters': 0,
      'mal_url': title.url,
      'mal_image_url': title.image_url,
      }
  if result['mal_chapters'] == None:
    result['mal_chapters'] = '?'
  if result['mal_volumes'] == None:
    result['mal_volumes'] = '?'
  return result

def mal_get_manga(mal_id):
  log.debug(f'Getting MyAnimeList manga, mal_id: {mal_id}')
  return mal_return_manga(mal.Manga(mal_id))

def mal_manga_search(name):
  name = name[:100] # Max query - 100 characters
  log.info(f'Searching MyAnimeList manga, query: "{name}"')
  try:
    mal_search = mal.MangaSearch(name)
    results = []
    for title in mal_search.results:
      results.append(mal_return_manga(title))
    return results
  except ValueError as e:
    log.warning(f'MyNimeList error: {e}')
    return []

def mgn_return_manga(manga):
  try:
    return ({
      'mgn_name': manga.title,
      'mgn_chapters': len(manga.chapters),
      'mgn_url': manga.url,
      'mgn_image_url': manga.icon_url,
      })
  except AttributeError:
    return ({
      'mgn_name': manga.title,
      'mgn_chapters': len(manga.chapter_list()),
      'mgn_url': manga.url,
      'mgn_image_url': manga.icon_url,
      })

def mgn_get_manga(mgn_url):
  log.debug(f'Getting Manganato manga, mgn_url: {mgn_url}')
  manga = manganelo.storypage.get_story_page(mgn_url)
  return mgn_return_manga(manga)

def mgn_search(name):
  log.info(f'Searching Manganato manga, query: "{name}"')
  mgn_search = manganelo.get_search_results(name)
  results = []
  for manga in mgn_search:
    results.append(mgn_return_manga(manga))
  return results

def add_anime(user_id):
  temp_vars[user_id]['search_string'] = None
  temp_vars[user_id]['mal_anime'] = None
  temp_vars[user_id]['mal_search_results'] = None
  temp_vars[user_id]['gogo_anime'] = None
  temp_vars[user_id]['gogo_search_results'] = None
  tgbot.send_message(user_id, 'Name of the anime?')
  change_state(user_id, 'add_anime')

def save_anime_to_db(user_id):
  anime_dict = temp_vars[user_id]['mal_anime']
  anime_dict.update(temp_vars[user_id]['gogo_anime'])
  log.debug(f'User {user_id}: saving anime entry to with id {anime_dict["mal_id"]}')
  users[user_id]['anime'][anime_dict['mal_id']] = anime_dict
  db.write('users', users)

def query_add_anime(user_id, query='0:noid'):
  query_name = 'add_anime'
  page_entries = 5
  columns = 1
  search_string = temp_vars[user_id]['search_string']
  mal_anime = temp_vars[user_id]['mal_anime']
  mal_search_results = temp_vars[user_id]['mal_search_results']
  gogo_anime = temp_vars[user_id]['gogo_anime']
  gogo_search_results = temp_vars[user_id]['gogo_search_results']
  page, search_id = query.split(':')
  page = int(page)
  if page < 0: page = 0
  max_pages = 0
  # Last row
  last_row = [
      InlineKeyboardButton('<', callback_data=f'{query_name}|{page-1}:noid'),
      InlineKeyboardButton('Cancel', callback_data=f'{query_name}|{page}:cancel'),
      InlineKeyboardButton('>', callback_data=f'{query_name}|{page+1}:noid'),
      ]
  if search_id == 'cancel':
    return 'Canceled adding anime', None, None
  if search_id != 'noid':
    search_id = int(search_id)
    if mal_anime:
      gogo_anime = temp_vars[user_id]['gogo_anime'] = gogo_get_anime(gogo_search_results[search_id]['gogo_id'])
    else:
      mal_anime = temp_vars[user_id]['mal_anime'] = mal_get_anime(mal_search_results[search_id]['mal_id'])
      page = 0

  text = 'Anime search\n==================='
  if search_string:
    if gogo_anime:
      text = 'Added new anime to whatchlist\n================'
      text += f'\nMyAnimeList title:\n\t{mal_anime["mal_name"]}'
      text += f'\n\nGogoAnime title:\n\t{gogo_anime["gogo_name"]}'
      text += f'\n\nEpisodes: {gogo_anime["gogo_episodes"]}/{mal_anime["mal_episodes"]}'
      keyboard = []
      save_anime_to_db(user_id)
    elif mal_anime:
      text = f'\nMyAnimeList title:\n\t{mal_anime["mal_name"]}'
      # Keyboard generation
      options_dict = {}
      slice_start = page * page_entries
      slice_end = slice_start + page_entries
      if gogo_search_results == None:
        temp_vars[user_id]['gogo_search_results'] = gogo_search_results = gogo_search(search_string)
      max_pages = (len(gogo_search_results) // page_entries)
      if gogo_search_results:
        num_id = 0
        for title in gogo_search_results[slice_start:slice_end]:
          gogo_anime_name = title['gogo_name']
          gogo_anime_episodes = title['gogo_episodes']
          options_dict.update({f'{gogo_anime_episodes} | {gogo_anime_name}':f'{query_name}|{page}:{slice_start+num_id}'})
          num_id += 1
        text += '\n\nGogoAnime title?'
        text += f'\n\npage {page+1} of {max_pages+1}'
        keyboard = tgbot.get_inline_options_keyboard(options_dict, columns)
        keyboard.append(last_row)
      else:
        text += '\n\nNothing was found on GogoAnime'
        keyboard = []
    else:
      # Keyboard generation
      options_dict = {}
      slice_start = page * page_entries
      slice_end = slice_start + page_entries
      if mal_search_results == None:
        temp_vars[user_id]['mal_search_results'] = mal_search_results = mal_anime_search(search_string)
      max_pages = (len(mal_search_results) // page_entries)
      if mal_search_results:
        num_id = 0
        for title in mal_search_results[slice_start:slice_end]:
          mal_anime_name = title['mal_name']
          mal_anime_episodes = title['mal_episodes']
          options_dict.update({f'{mal_anime_episodes} | {mal_anime_name}':f'{query_name}|{page}:{slice_start+num_id}'})
          num_id += 1
        text += '\nMyAnimeList title?'
        text += f'\n\npage {page+1} of {max_pages+1}'
        keyboard = tgbot.get_inline_options_keyboard(options_dict, columns)
        keyboard.append(last_row)
      else:
        text += '\nNothing was found on MyAnimeList'
        keyboard = []
    reply_markup = InlineKeyboardMarkup(keyboard)
    return text, reply_markup, None
  else:
    return 'Error', None, None

def add_manga(user_id):
  temp_vars[user_id]['search_string'] = None
  temp_vars[user_id]['mal_manga'] = None
  temp_vars[user_id]['mal_search_results'] = None
  temp_vars[user_id]['mgn_manga'] = None
  temp_vars[user_id]['mgn_search_results'] = None
  tgbot.send_message(user_id, 'Name of the manga?')
  change_state(user_id, 'add_manga')

def save_manga_to_db(user_id):
  mal_manga_id = temp_vars[user_id]['mal_manga']['mal_id']
  manga_dict = mal_get_manga(mal_manga_id)
  manga_dict.update(temp_vars[user_id]['mgn_manga'])
  log.debug(f'User {user_id}: saving manga entry to with id {manga_dict["mal_id"]}')
  users[user_id]['manga'][manga_dict['mal_id']] = manga_dict
  db.write('users', users)

def query_add_manga(user_id, query='0:noid'):
  query_name = 'add_manga'
  page_entries = 5
  columns = 1
  search_string = temp_vars[user_id]['search_string']
  mal_manga = temp_vars[user_id]['mal_manga']
  mal_search_results = temp_vars[user_id]['mal_search_results']
  mgn_manga = temp_vars[user_id]['mgn_manga']
  mgn_search_results = temp_vars[user_id]['mgn_search_results']
  page, search_id = query.split(':')
  page = int(page)
  if page < 0: page = 0
  max_pages = 0
  # Last row
  last_row = [
      InlineKeyboardButton('<', callback_data=f'{query_name}|{page-1}:noid'),
      InlineKeyboardButton('Cancel', callback_data=f'{query_name}|{page}:cancel'),
      InlineKeyboardButton('>', callback_data=f'{query_name}|{page+1}:noid'),
      ]
  if search_id == 'cancel':
    return 'Canceled adding manga', None, None
  if search_id != 'noid':
    search_id = int(search_id)
    if mal_manga:
      mgn_manga = temp_vars[user_id]['mgn_manga'] = mgn_get_manga(mgn_search_results[search_id]['mgn_url'])
    else:
      mal_manga = temp_vars[user_id]['mal_manga'] = mal_get_manga(mal_search_results[search_id]['mal_id'])
      page = 0

  text = 'Manga search\n==================='
  if search_string:
    if mgn_manga:
      text = 'Added new manga to whatchlist\n================'
      text += f'\nMyAnimeList title:\n\t{mal_manga["mal_name"]}'
      text += f'\n\nManganato title:\n\t{mgn_manga["mgn_name"]}'
      text += f'\n\nChapters: {mgn_manga["mgn_chapters"]}/{mal_manga["mal_chapters"]}'
      keyboard = []
      save_manga_to_db(user_id)
    elif mal_manga:
      text = f'\nMyAnimeList title:\n\t{mal_manga["mal_name"]}'
      # Keyboard generation
      options_dict = {}
      slice_start = page * page_entries
      slice_end = slice_start + page_entries
      if mgn_search_results == None:
        temp_vars[user_id]['mgn_search_results'] = mgn_search_results = mgn_search(search_string)
      max_pages = (len(mgn_search_results) // page_entries)
      if mgn_search_results:
        num_id = 0
        for title in mgn_search_results[slice_start:slice_end]:
          mgn_manga_name = title['mgn_name']
          mgn_manga_chapters = title['mgn_chapters']
          options_dict.update({f'{mgn_manga_chapters} | {mgn_manga_name}':f'{query_name}|{page}:{slice_start+num_id}'})
          num_id += 1
        text += '\n\nManganato title?'
        text += f'\n\npage {page+1} of {max_pages+1}'
        keyboard = tgbot.get_inline_options_keyboard(options_dict, columns)
        keyboard.append(last_row)
      else:
        text += '\n\nNothing was found on Manganato'
        keyboard = []
    else:
      # Keyboard generation
      options_dict = {}
      slice_start = page * page_entries
      slice_end = slice_start + page_entries
      if mal_search_results == None:
        temp_vars[user_id]['mal_search_results'] = mal_search_results = mal_manga_search(search_string)
      max_pages = (len(mal_search_results) // page_entries)
      if mal_search_results:
        num_id = 0
        for title in mal_search_results[slice_start:slice_end]:
          mal_manga_name = title['mal_name']
          mal_manga_volumes = title['mal_volumes']
          options_dict.update({f'{mal_manga_volumes} | {mal_manga_name}':f'{query_name}|{page}:{slice_start+num_id}'})
          num_id += 1
        text += '\nMyAnimeList title?'
        text += f'\n\npage {page+1} of {max_pages+1}'
        keyboard = tgbot.get_inline_options_keyboard(options_dict, columns)
        keyboard.append(last_row)
      else:
        text += '\nNothing was found on MyAnimeList'
        keyboard = []
    reply_markup = InlineKeyboardMarkup(keyboard)
    return text, reply_markup, None
  else:
    return 'Error', None, None

def send_whatchlist(user_id):
  text, reply_markup, parse_mode = get_whatchlist(user_id)
  tgbot.send_message(user_id, text, reply_markup=reply_markup, parse_mode=parse_mode)

def get_whatchlist(user_id):
  text = '*Current whatchlist*\n'
  user_anime = users[user_id]['anime']
  user_manga = users[user_id]['manga']
  if user_anime:
    text += '\n*Anime*'
    for mal_id in user_anime:
      anime_entry = user_anime[mal_id]
      anime_name = anime_entry['gogo_name'].replace('(','\(').replace(')','\)').replace('!','\!').replace('-',"\-")
      anime_episodes = f'{anime_entry["gogo_episodes"]}/{anime_entry["mal_episodes"]}'
      gogo_link = f'{gogoanime_domain}category/{anime_entry["gogo_id"]}'
      mal_link = anime_entry['mal_url']
      text += f'\n\t\t[{anime_episodes}]({gogo_link}) [{anime_name}]({mal_link})'
  if user_manga:
    text += '\n*Manga*'
    for mal_id in user_manga:
      manga_entry = user_manga[mal_id]
      manga_name = manga_entry['mgn_name'].replace('(', '\(').replace(')', '\)').replace('!', '\!').replace('-',"\-")
      manga_chapters = f'{manga_entry["mgn_chapters"]}/{manga_entry["mal_chapters"]}'
      mgn_link = manga_entry['mgn_url']
      mal_link = manga_entry['mal_url']
      text += f'\n\t\t[{manga_chapters}]({mgn_link}) [{manga_name}]({mal_link})'
  keyboard = tgbot.get_inline_options_keyboard(
      {'Remove an entry':'whatchlist_remove|0:noid'},
      columns = 1
      )
  reply_markup = InlineKeyboardMarkup(keyboard)
  return text, reply_markup, 'MarkdownV2'

def query_whatchlist_remove(user_id, query='0:noid'):
  query_name = 'whatchlist_remove'
  page_entries = 5
  columns = 1
  page, remove_id = query.split(':')
  if remove_id == 'finish':
    return get_whatchlist(user_id)
  page = int(page)
  if page < 0: page = 0
  max_pages = 0
  # Last row
  last_row = [
      InlineKeyboardButton('<', callback_data=f'{query_name}|{page-1}:noid'),
      InlineKeyboardButton('Finish', callback_data=f'{query_name}|0:finish'),
      InlineKeyboardButton('>', callback_data=f'{query_name}|{page+1}:noid'),
      ]
  if remove_id != 'noid':
    log.info(f'User {user_id}: Removing entry {remove_id} from whatchlist')
    try:
      del users[user_id]['anime'][remove_id]
    except KeyError:
      del users[user_id]['manga'][remove_id]
    db.write('users', users)
  text = 'Remove from whatchlist\n================='
  text += '\nAnime:'
  for mal_id in users[user_id]['anime']:
    anime_name = users[user_id]['anime'][mal_id]['gogo_name']
    text += f'\n\t{anime_name}'
  text += '\n\nManga:'
  for mal_id in users[user_id]['manga']:
    manga_name = users[user_id]['manga'][mal_id]['mgn_name']
    text += f'\n\t{manga_name}'
  # Keyboard generation
  options_dict = {}
  slice_start = page * page_entries
  slice_end = slice_start + page_entries
  user_entries = users[user_id]['anime']
  user_entries.update(users[user_id]['manga'])
  user_entry_keys = list(user_entries.keys())
  max_pages = (len(user_entries) // page_entries)
  for title_id in user_entry_keys[slice_start:slice_end]:
    try:
      title_name = user_entries[title_id]['gogo_name']
    except KeyError:
      title_name = user_entries[title_id]['mgn_name']
    options_dict.update({title_name:f'{query_name}|{page}:{title_id}'})
  text += f'\n\npage {page+1} of {max_pages+1}'
  keyboard = tgbot.get_inline_options_keyboard(options_dict, columns)
  keyboard.append(last_row)
  reply_markup = InlineKeyboardMarkup(keyboard)
  return text, reply_markup, None

def check_whatchlist(user_id):
  user_anime = users[user_id]['anime']
  user_manga = users[user_id]['manga']
  for mal_id in user_anime:
    gogo_id = user_anime[mal_id]['gogo_id']
    gogo_name = user_anime[mal_id]['gogo_name'].replace('(', '\(').replace(')', '\)').replace('!','\!').replace('-',"\-")
    gogo_episodes = user_anime[mal_id]['gogo_episodes']
    gogo_url = f'{gogoanime_domain}category/{gogo_id}'
    mal_image_url = user_anime[mal_id]['mal_image_url']
    mal_url = user_anime[mal_id]['mal_url']
    mal_anime = mal_get_anime(mal_id)
    mal_episodes = user_anime[mal_id]['mal_episodes']
    if mal_anime['mal_episodes'] != mal_episodes:
      log.info(f'User {user_id}: Episodes changed for MyAnimeList anime {mal_id}')
      users[user_id]['anime'][mal_id]['mal_episodes'] = mal_episodes = mal_anime['mal_episodes']
    gogo_anime = gogo_get_anime(gogo_id)
    if int(gogo_anime['gogo_episodes']) > int(gogo_episodes):
      log.info(f'User {user_id}: New episode for anime {gogo_name}')
      users[user_id]['anime'][mal_id]['gogo_episodes'] = gogo_episodes = gogo_anime['gogo_episodes']
      db.write('users', users)
      text = f'''\t\tNew [episode]({gogo_url}) released\!
{gogo_episodes}/{mal_episodes} [{gogo_name}]({mal_url})
      '''
      tgbot.send_image(user_id, text=text, url=mal_image_url, parse_mode='MarkdownV2')
  for mal_id in user_manga:
    mgn_url = user_manga[mal_id]['mgn_url']
    mgn_name = user_manga[mal_id]['mgn_name'].replace('(', '\(').replace(')', '\)').replace('!','\!').replace('-',"\-")
    mgn_chapters = user_manga[mal_id]['mgn_chapters']
    mgn_image_url = user_manga[mal_id]['mgn_image_url']
    mal_manga = mal_get_manga(mal_id)
    mal_chapters = user_manga[mal_id]['mal_chapters']
    mal_url = user_manga[mal_id]['mal_url']
    if mal_manga['mal_chapters'] != mal_chapters:
      log.info(f'User {user_id}: Chapters changed for MyAnimeList manga {mal_id}')
      users[user_id]['manga'][mal_id]['mal_chapters'] = mal_chapters = mal_manga['mal_chapters']
    mgn_manga = mgn_get_manga(mgn_url)
    if int(mgn_manga['mgn_chapters']) > int(mgn_chapters):
      log.info(f'User {user_id}: New chapter for manga {mgn_name}')
      users[user_id]['manga'][mal_id]['mgn_chapters'] = mgn_chapters = mgn_manga['mgn_chapters']
      db.write('users', users)
      text = f'''\t\tNew [chapter]({mgn_url}) released\!
{mgn_chapters}/{mal_chapters} [{mgn_name}]({mal_url})
      '''
      tgbot.send_image(user_id, text=text, url=mgn_image_url, parse_mode='MarkdownV2')

def check_all_whatchlists():
  for user_id in users:
    log.debug(f'Checking whatchlist for user {user_id}')
    check_whatchlist(user_id)

def handle_message(user_id, text):
  users = db.read('users')
  state = temp_vars[user_id]['state']

  # STATE - add_anime
  if state == 'add_anime':
    temp_vars[user_id]['search_string'] = text
    text, reply_markup, parse_mode = query_add_anime(user_id)
    tgbot.send_message(user_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    change_state(user_id, 'main_menu')

  # STATE - add_manga
  if state == 'add_manga':
    temp_vars[user_id]['search_string'] = text
    text, reply_markup, parse_mode = query_add_manga(user_id)
    tgbot.send_message(user_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    change_state(user_id, 'main_menu')

  else:
    reply = 'Error, try again'
    tgbot.send_message(user_id, reply)
    change_state(user_id, 'main_menu')
