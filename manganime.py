import logging
import traceback
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import tgbot
import mal
import uuid
import db
import logic
import manganato
import gogoanime

log = logging.getLogger('main')

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

def add_anime(user_id):
  logic.temp_vars[user_id]['search_string'] = None
  logic.temp_vars[user_id]['mal_anime'] = None
  logic.temp_vars[user_id]['mal_search_results'] = None
  logic.temp_vars[user_id]['gogo_anime'] = None
  logic.temp_vars[user_id]['gogo_search_results'] = None
  tgbot.send_message(user_id, 'Name of the anime?')
  logic.change_state(user_id, 'add_anime')

def save_anime_to_db(user_id):
  anime_dict = logic.temp_vars[user_id]['mal_anime']
  anime_dict.update(logic.temp_vars[user_id]['gogo_anime'])
  log.debug(f'User {user_id}: saving anime entry to with id {anime_dict["mal_id"]}')
  logic.users[user_id]['anime'][anime_dict['mal_id']] = anime_dict
  db.write('users', logic.users)

def query_add_anime(user_id, query='0:noid'):
  query_name = 'add_anime'
  page_entries = 5
  columns = 1
  search_string = logic.temp_vars[user_id]['search_string']
  mal_anime = logic.temp_vars[user_id]['mal_anime']
  mal_search_results = logic.temp_vars[user_id]['mal_search_results']
  gogo_anime = logic.temp_vars[user_id]['gogo_anime']
  gogo_search_results = logic.temp_vars[user_id]['gogo_search_results']
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
      gogo_anime = logic.temp_vars[user_id]['gogo_anime'] = gogoanime.get_anime(gogo_search_results[search_id]['gogo_url'])
    else:
      mal_anime = logic.temp_vars[user_id]['mal_anime'] = mal_get_anime(mal_search_results[search_id]['mal_id'])
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
        logic.temp_vars[user_id]['gogo_search_results'] = gogo_search_results = gogoanime.search_anime(search_string)
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
        logic.temp_vars[user_id]['mal_search_results'] = mal_search_results = mal_anime_search(search_string)
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
  logic.temp_vars[user_id]['search_string'] = None
  logic.temp_vars[user_id]['mal_manga'] = None
  logic.temp_vars[user_id]['mal_search_results'] = None
  logic.temp_vars[user_id]['mgn_manga'] = None
  logic.temp_vars[user_id]['mgn_search_results'] = None
  tgbot.send_message(user_id, 'Name of the manga?')
  logic.change_state(user_id, 'add_manga')

def save_manga_to_db(user_id):
  mal_manga_id = logic.temp_vars[user_id]['mal_manga']['mal_id']
  manga_dict = logic.temp_vars[user_id]['mal_manga']
  manga_dict.update(logic.temp_vars[user_id]['mgn_manga'])
  log.debug(f'User {user_id}: saving manga entry to db with id {manga_dict["mal_id"]}')
  logic.users[user_id]['manga'][manga_dict['mal_id']] = manga_dict
  db.write('users', logic.users)

def query_add_manga(user_id, query='0:noid'):
  query_name = 'add_manga'
  page_entries = 5
  columns = 1
  search_string = logic.temp_vars[user_id]['search_string']
  mal_manga = logic.temp_vars[user_id]['mal_manga']
  mal_search_results = logic.temp_vars[user_id]['mal_search_results']
  mgn_manga = logic.temp_vars[user_id]['mgn_manga']
  mgn_search_results = logic.temp_vars[user_id]['mgn_search_results']
  page, search_id = query.split(':')
  page = int(page)
  if page < 0: page = 0
  max_pages = 0
  # Last row
  last_row = [
      InlineKeyboardButton('<', callback_data=f'{query_name}|{page-1}:noid'),
      InlineKeyboardButton('Cancel', callback_data=f'{query_name}|{page}:cancel'),
      ]
  if not mal_manga:
    last_row.append(InlineKeyboardButton('Skip MAL', callback_data=f'{query_name}|{page+1}:skip'),)
  last_row.append(InlineKeyboardButton('>', callback_data=f'{query_name}|{page+1}:noid'),)
  if search_id == 'cancel':
    return 'Canceled adding manga', None, None
  elif search_id == 'skip':
    mal_manga = logic.temp_vars[user_id]['mal_manga'] = {
      'mal_id': str(uuid.uuid4()),
      'mal_name': '',
      'mal_volumes': '?',
      'mal_chapters': '?',
      'mal_url': '',
      'mal_image_url': '',
      }
    page = 0
  elif search_id != 'noid':
    search_id = int(search_id)
    if mal_manga:
      mgn_manga = logic.temp_vars[user_id]['mgn_manga'] = manganato.get_manga(mgn_search_results[search_id]['mgn_url'])
    else:
      mal_manga = logic.temp_vars[user_id]['mal_manga'] = mal_get_manga(mal_search_results[search_id]['mal_id'])
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
        logic.temp_vars[user_id]['mgn_search_results'] = mgn_search_results = manganato.search_manga(search_string)
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
        logic.temp_vars[user_id]['mal_search_results'] = mal_search_results = mal_manga_search(search_string)
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

def get_anime_whatchlist(user_id):
  text = '*Anime whatchlist*\n'
  user_anime = logic.users[user_id]['anime']
  for mal_id in user_anime:
    anime_entry = user_anime[mal_id]
    anime_name = tgbot.markdown_replace(anime_entry['gogo_name'])
    anime_episodes = f'{anime_entry["gogo_episodes"]}/{anime_entry["mal_episodes"]}'
    gogo_link = anime_entry['gogo_url']
    mal_link = anime_entry['mal_url']
    text += f'\n[{anime_episodes}]({gogo_link}) [{anime_name}]({mal_link})'
  keyboard = tgbot.get_inline_options_keyboard(
      {
        'Anime':'whatchlist|anime',
        'Manga':'whatchlist|manga',
        'Music':'whatchlist|music',
      },
      columns = 3
    )
  keyboard += tgbot.get_inline_options_keyboard(
      {'Remove an entry':'whatchlist_remove|0:anime:noid'},
      columns = 1
    )
  reply_markup = InlineKeyboardMarkup(keyboard)
  return text, reply_markup, 'MarkdownV2'

def get_manga_whatchlist(user_id):
  text = '*Manga whatchlist*\n'
  user_manga = logic.users[user_id]['manga']
  for mal_id in user_manga:
    manga_entry = user_manga[mal_id]
    manga_name = tgbot.markdown_replace(manga_entry['mgn_name'])
    manga_chapters = f'{manga_entry["mgn_chapters"]}/{manga_entry["mal_chapters"]}'
    mgn_link = manga_entry['mgn_url']
    mal_link = manga_entry['mal_url']
    text += f'\n\t\t[{manga_chapters}]({mgn_link}) [{manga_name}]({mal_link})'
  keyboard = tgbot.get_inline_options_keyboard(
      {
        'Anime':'whatchlist|anime',
        'Manga':'whatchlist|manga',
        'Music':'whatchlist|music',
      },
      columns = 3
    )
  keyboard += tgbot.get_inline_options_keyboard(
      {'Remove an entry':'whatchlist_remove|0:manga:noid'},
      columns = 1
    )
  reply_markup = InlineKeyboardMarkup(keyboard)
  return text, reply_markup, 'MarkdownV2'

def check_anime_whatchlist(user_id):
  log.debug(f'Checking anime for user {user_id}')
  user_anime = logic.users[user_id]['anime']
  for mal_id in user_anime:
    try:
      gogo_name = tgbot.markdown_replace(user_anime[mal_id]['gogo_name'])
      gogo_episodes = user_anime[mal_id]['gogo_episodes']
      gogo_url = user_anime[mal_id]['gogo_url']
      mal_image_url = user_anime[mal_id]['mal_image_url']
      mal_url = user_anime[mal_id]['mal_url']
      mal_anime = mal_get_anime(mal_id)
      mal_episodes = user_anime[mal_id]['mal_episodes']
      if mal_anime['mal_episodes'] != mal_episodes:
        log.info(f'User {user_id}: Episodes changed for MyAnimeList anime {mal_id}')
        logic.users[user_id]['anime'][mal_id]['mal_episodes'] = mal_episodes = mal_anime['mal_episodes']
        db.write('users', logic.users)
      gogo_anime = gogoanime.get_anime(gogo_url)
      if int(gogo_anime['gogo_episodes']) > int(gogo_episodes):
        log.info(f'User {user_id}: New episode for anime {gogo_name}')
        logic.users[user_id]['anime'][mal_id]['gogo_episodes'] = gogo_episodes = gogo_anime['gogo_episodes']
        db.write('users', logic.users)
        text = f'''\t\tNew [episode]({gogo_url}) released\!
  {gogo_episodes}/{mal_episodes} [{gogo_name}]({mal_url})
        '''
        try: # Send text if unable to send image
          tgbot.send_image(user_id, text=text, url=mal_image_url, parse_mode='MarkdownV2')
        except telegram.error.BadRequest as e:
          log.warning(f'Handling exception "{e}"')
          tgbot.send_message(user_id, text=text, parse_mode='MarkdownV2')
          log.warning((traceback.format_exc()))
    except Exception:
      log.warning((traceback.format_exc()))

def check_manga_whatchlist(user_id):
  log.debug(f'Checking manga for user {user_id}')
  user_manga = logic.users[user_id]['manga']
  for mal_id in user_manga:
    try:
      mgn_url = user_manga[mal_id]['mgn_url']
      mgn_name = tgbot.markdown_replace(user_manga[mal_id]['mgn_name'])
      mgn_chapters = user_manga[mal_id]['mgn_chapters']
      mgn_image_url = user_manga[mal_id]['mgn_image_url']
      mal_url = user_manga[mal_id]['mal_url']
      mal_chapters = user_manga[mal_id]['mal_chapters']
      if not logic.is_valid_uuid(mal_id):
        mal_manga = mal_get_manga(mal_id)
        if mal_manga['mal_chapters'] != mal_chapters:
          log.info(f'User {user_id}: Chapters changed for MyAnimeList manga {mal_id}')
          logic.users[user_id]['manga'][mal_id]['mal_chapters'] = mal_chapters = mal_manga['mal_chapters']
          db.write('users', logic.users)
      mgn_manga = manganato.get_manga(mgn_url)
      if int(mgn_manga['mgn_chapters']) > int(mgn_chapters):
        log.info(f'User {user_id}: New chapter for manga {mgn_name}')
        logic.users[user_id]['manga'][mal_id]['mgn_chapters'] = mgn_chapters = mgn_manga['mgn_chapters']
        db.write('users', logic.users)
        text = f'''\t\tNew [chapter]({mgn_url}) released\!
  {mgn_chapters}/{mal_chapters} [{mgn_name}]({mal_url})
        '''
        try: # Send text if unable to send image
          tgbot.send_image(user_id, text=text, url=mgn_image_url, parse_mode='MarkdownV2')
        except telegram.error.BadRequest as e:
          log.warning(f'Handling exception "{e}"')
          tgbot.send_message(user_id, text=text, parse_mode='MarkdownV2')
          log.warning((traceback.format_exc()))
    except Exception:
      log.warning((traceback.format_exc()))
