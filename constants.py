import time
import uuid

def get_temp_vars():
  return {
      'state':'main_menu',
      'whatchlist':'music',
      'search_string': None,
      'mal_anime': None,
      'mal_manga': None,
      'mal_search_results': None,
      'gogo_anime': None,
      'gogo_search_results': None,
      'mgn_manga': None,
      'mgn_search_results': None,
      }

def get_default_user(tg_username):
  return {
      'username':tg_username,
      'anime': {},
      'manga': {},
      'music': {},
      }
