import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import tgbot
import mal
from gogoanimeapi import gogoanime
import manganelo
import db
import constants
import manganime

log = logging.getLogger('main')

temp_vars = {}
users = None

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
      title_name = user_entries[title_id]['gogo_name']
    elif entry_type == 'manga':
      title_name = user_entries[title_id]['mgn_name']
    options_dict.update({title_name:f'{query_name}|{page}:{entry_type}:{title_id}'})
  text += f'\n\npage {page+1} of {max_pages+1}'
  keyboard = tgbot.get_inline_options_keyboard(options_dict, columns)
  keyboard.append(last_row)
  reply_markup = InlineKeyboardMarkup(keyboard)
  return text, reply_markup, 'MarkdownV2'

def check_whatchlist(user_id):
  user_anime = users[user_id]['anime']
  user_manga = users[user_id]['manga']
  for mal_id in user_anime:
    gogo_id = user_anime[mal_id]['gogo_id']
    gogo_name = tgbot.markdown_replace(user_anime[mal_id]['gogo_name'])
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
    mgn_name = tgbot.markdown_replace(user_manga[mal_id]['mgn_name'])
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
    text, reply_markup, parse_mode = manganime.query_add_anime(user_id)
    tgbot.send_message(user_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    change_state(user_id, 'main_menu')

  # STATE - add_manga
  elif state == 'add_manga':
    temp_vars[user_id]['search_string'] = text
    text, reply_markup, parse_mode = manganime.query_add_manga(user_id)
    tgbot.send_message(user_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    change_state(user_id, 'main_menu')

  else:
    reply = 'Error, try again'
    tgbot.send_message(user_id, reply)
    change_state(user_id, 'main_menu')
