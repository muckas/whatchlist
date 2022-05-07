import os
import time
import logging
from contextlib import suppress
import telegram
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
import telegram.ext
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackQueryHandler
import db
import constants
import logic

log = logging.getLogger('main')

tg = None

help_text = '''I am sorry, but there's nothing I can help you with...'''

def send_message(user_id, text, silent=True, keyboard=None, inline_keyboard=None, reply_markup = None):
  if keyboard != None:
    if keyboard == []:
      reply_markup = ReplyKeyboardRemove()
    else:
      reply_markup = ReplyKeyboardMarkup(keyboard)
  if inline_keyboard:
    reply_markup = InlineKeyboardMarkup(inline_keyboard)
  message = tg.send_message(chat_id=user_id, text=text, disable_notification=silent, reply_markup=reply_markup)
  log.info(f'Message to user {user_id}:{text}')
  return message

def send_document(user_id, file_path, file_name, caption=None, silent=True):
  try:
    tg.send_chat_action(chat_id=user_id, action=telegram.ChatAction.UPLOAD_DOCUMENT)
    with open(file_path, 'rb') as file:
      tg.send_document(chat_id=user_id, document=file, filename=file_name, caption=caption, disable_notification=silent)
      return True
  except FileNotFoundError:
    return False

def get_options_keyboard(options, columns=2):
  keyboard = []
  for index in range(0, len(options), columns):
    row = []
    for offset in range(columns):
      with suppress(IndexError):
        row.append(options[index+offset])
    keyboard.append(row)
  return keyboard

def get_inline_options_keyboard(options_dict, columns=2):
  keyboard = []
  for index in range(0, len(options_dict), columns):
    row = []
    for offset in range(columns):
      with suppress(IndexError):
        option_key = list(options_dict.keys())[index + offset]
        row.append(InlineKeyboardButton(option_key, callback_data=options_dict[option_key]))
    keyboard.append(row)
  return keyboard

def log_message(update):
  user_id = str(update.message.chat['id'])
  username = str(update.message.chat['username'])
  text = update.message.text
  log.info(f'Message from @{username}({user_id}):{text}')

def add_user_to_db(update):
  user_id = str(update.message.chat['id'])
  log.info(f'Adding new user {user_id} to database')
  users = db.read('users')
  tg_username = str(update.message.chat['username'])
  users.update({user_id:constants.get_default_user(tg_username)})
  db.write('users', users)
  log.info(f'Added @{tg_username} to database')

def validated(update, notify=False):
  user_id = str(update.message.chat['id'])
  users = db.read('users')
  if user_id not in users:
    add_user_to_db(update)
  whitelist = db.read('whitelist')
  if db.read('params')['use_whitelist']:
    if user_id in whitelist:
      log.debug(f'User {user_id} whitelisted')
      return True
    else:
      log.debug(f'User {user_id} not whitelisted')
      if notify:
        send_message(user_id, f"Your id is {user_id}")
      return False
  else:
    return True

def message_handler(update, context):
  log_message(update)
  user_id = str(update.message.chat['id'])
  if validated(update):
    text = update.message.text
    logic.check_temp_vars(user_id)
    logic.handle_message(user_id, text)

def command_add_anime(update, context):
  log_message(update)
  user_id = str(update.message.chat['id'])
  users = db.read('users')
  if validated(update):
    logic.check_temp_vars(user_id)
    logic.add_anime(user_id)

def query_handler(update, context):
  users = db.read('users')
  query = update.callback_query
  user_id = str(query.message.chat_id)
  log.info(f'Query from user {user_id}: {query.data}')
  logic.check_temp_vars(user_id)
  function, option = query.data.split('|')
  if function == 'add_anime':
    text, reply_markup = logic.query_add_anime(user_id, option)
  else:
    text = 'Error'
    reply_markup = None
  try:
    query.edit_message_text(text=text, reply_markup=reply_markup)
  except telegram.error.BadRequest as e:
    log.warning(f'Exception while updating query: {e}')
  query.answer()

def error_handler(update, context):
  log.warning(msg="Exception while handling an update:", exc_info=context.error)

def start(tg_token):
  log.info('Starting telegram bot...')
  updater = telegram.ext.Updater(tg_token)
  dispatcher = updater.dispatcher
  dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))
  dispatcher.add_handler(CommandHandler('add_anime', command_add_anime))
  dispatcher.add_handler(CallbackQueryHandler(query_handler))
  dispatcher.add_error_handler(error_handler)
  updater.start_polling()
  log.info('Telegram bot started')
  return updater
