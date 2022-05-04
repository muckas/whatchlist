import logging
import os
import time
import datetime
from contextlib import suppress
import constants
import db
import easyargs

# Logger setup
with suppress(FileExistsError):
  os.makedirs('logs')
  print('Created logs folder')

log = logging.getLogger('main')
log.setLevel(logging.DEBUG)

filename = 'dbutils-' + datetime.datetime.now().strftime('%Y-%m-%d') + '.log'
file = logging.FileHandler(os.path.join('logs', filename))
file.setLevel(logging.DEBUG)
fileformat = logging.Formatter('%(asctime)s:%(levelname)s: %(message)s')
file.setFormatter(fileformat)
log.addHandler(file)

stream = logging.StreamHandler()
stream.setLevel(logging.DEBUG)
streamformat = logging.Formatter('%(asctime)s:%(levelname)s: %(message)s')
stream.setFormatter(fileformat)
log.addHandler(stream)
# End of logger setup

def check_params():
  missing_total = 0
  log.info('Checking params.json...')
  params_default = db.read('params.defaults')
  params = db.read('params')
  for param in params_default:
    if param not in params.keys():
      missing_total += 1
      value = params_default[param]
      params[param] = value
      log.info(f'Missing key "{param}", added {param}:{value} ')
  if missing_total > 0: db.write('params', params)
  log.info(f'Checked params.json, {missing_total} missing entries created')
  return missing_total

def check_users():
  missing_total = 0
  log.info('Checking users.json...')
  users = db.read('users')
  default_user = constants.get_default_user('::corrupted::')
  for user in users:
    log.info(f'Checking user {user}')
    for key in default_user:
      if key not in users[user].keys():
        missing_total += 1
        value = default_user[key]
        users[user][key] = value
        log.info(f'Missing key "{key}", adding {key}:{value}')
  if missing_total > 0: db.write('users', users)
  log.info(f'Checked users.json, {missing_total} missing entries created')
  return missing_total

@easyargs
class DButils(object):
  """Database utility"""

  def backup(self, name='backup', max_backups=0):
    '''
    Backup database
    :param name: Archive name
    :param max_backups: Max number of backups (if exceedes, removes oldest backups), 0 for infinite
    '''
    db.archive(filename=name, max_backups=max_backups)

  def chkdb(self, backup=True):
    """
    Check database for missing keys and add them
    :param backup: Backup database before checking
    """
    missing_total = 0
    date = datetime.datetime.now()
    log.info(f'Database check started on {date}')
    db.archive(filename='chkdb')
    missing_total += check_params()
    missing_total += check_users()
    log.info(f'Database check complete, total of {missing_total} missing entries created')

if __name__ == '__main__':
  log.info('================================')
  log.info('DButils started')
  DButils()
