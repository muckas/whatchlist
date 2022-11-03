import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import tgbot
import mal
from gogoanimeapi import gogoanime
import uuid
import db
import constants
import manganime
import bandcamp

log = logging.getLogger('main')

temp_vars = {}
users = None

def is_valid_uuid(value):
	try:
		uuid.UUID(str(value))
		return True
	except ValueError:
		return False

def check_temp_vars(user_id):
  if user_id not in temp_vars:
    temp_vars.update({user_id:constants.get_temp_vars()})

def change_state(user_id, new_state):
  temp_vars[user_id]['state'] = new_state
  log.debug(f'New state "{new_state}" for user {user_id}')

def send_whatchlist(user_id):
  text, reply_markup, parse_mode = query_whatchlist(user_id)
  tgbot.send_message(user_id, text, reply_markup=reply_markup, parse_mode=parse_mode)

def query_whatchlist(user_id, query=None):
  if query:
    whatchlist = temp_vars[user_id]['whatchlist'] = query
  else:
    whatchlist = temp_vars[user_id]['whatchlist']
  if whatchlist == 'anime':
    return manganime.get_anime_whatchlist(user_id)
  elif whatchlist == 'manga':
    return manganime.get_manga_whatchlist(user_id)
  elif whatchlist == 'music':
    return bandcamp.get_music_whatchlist(user_id)

def query_whatchlist_remove(user_id, query='0:anime:noid'):
  query_name = 'whatchlist_remove'
  page_entries = 5
  columns = 1
  page, entry_type, remove_id = query.split(':')
  if remove_id == 'finish':
    return query_whatchlist(user_id)
  page = int(page)
  if page < 0: page = 0
  max_pages = 0
  # Last row
  last_row = [
      InlineKeyboardButton('<', callback_data=f'{query_name}|{page-1}:{entry_type}:noid'),
      InlineKeyboardButton('Finish', callback_data=f'{query_name}|0:{entry_type}:finish'),
      InlineKeyboardButton('>', callback_data=f'{query_name}|{page+1}:{entry_type}:noid'),
      ]
  if remove_id != 'noid':
    log.info(f'User {user_id}: Removing entry {remove_id} from whatchlist')
    del users[user_id][entry_type][remove_id]
    db.write('users', users)
  text = '*Removing from* '
  whatchlist_text, *args = query_whatchlist(user_id, entry_type)
  text += whatchlist_text
  # Keyboard generation
  options_dict = {}
  slice_start = page * page_entries
  slice_end = slice_start + page_entries
  user_entries = users[user_id][entry_type]
  user_entry_keys = list(user_entries.keys())
  max_pages = (len(user_entries) // page_entries)
  for title_id in user_entry_keys[slice_start:slice_end]:
    if entry_type == 'anime':
      mal_episodes = user_entries[title_id]['mal_episodes']
      gogo_episodes = user_entries[title_id]['gogo_episodes']
      gogo_name = user_entries[title_id]['gogo_name']
      title_name = f'{gogo_episodes}/{mal_episodes} {gogo_name}'
    elif entry_type == 'manga':
      mal_chapters = user_entries[title_id]['mal_chapters']
      mgn_chapters = user_entries[title_id]['mgn_chapters']
      mgn_name = user_entries[title_id]['mgn_name']
      title_name = f'{mgn_chapters}/{mal_chapters} {mgn_name}'
    elif entry_type == 'music':
      title_name = user_entries[title_id]['name']
    options_dict.update({title_name:f'{query_name}|{page}:{entry_type}:{title_id}'})
  text += f'\n\npage {page+1} of {max_pages+1}'
  keyboard = tgbot.get_inline_options_keyboard(options_dict, columns)
  keyboard.append(last_row)
  reply_markup = InlineKeyboardMarkup(keyboard)
  return text, reply_markup, 'MarkdownV2'

def check_all_whatchlists():
  for user_id in users:
    manganime.check_anime_whatchlist(user_id)
    manganime.check_manga_whatchlist(user_id)
    bandcamp.check_music_whatchlist(user_id)

def handle_message(user_id, text):
  users = db.read('users')
  state = temp_vars[user_id]['state']

  # STATE - add_anime
  if state == 'add_anime':
    temp_vars[user_id]['search_string'] = text
    text, reply_markup, parse_mode = manganime.query_add_anime(user_id)
    tgbot.send_message(user_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    change_state(user_id, 'main_menu')

  # STATE - add_manga
  elif state == 'add_manga':
    temp_vars[user_id]['search_string'] = text
    text, reply_markup, parse_mode = manganime.query_add_manga(user_id)
    tgbot.send_message(user_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    change_state(user_id, 'main_menu')

  # STATE - add_music
  elif state == 'add_music':
    bandcamp.add_music_to_whatchlist(user_id, text)
    change_state(user_id, 'main_menu')

  else:
    reply = 'Error, try again'
    tgbot.send_message(user_id, reply)
    change_state(user_id, 'main_menu')
