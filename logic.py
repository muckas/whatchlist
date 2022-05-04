import logging
import mal
from gogoanimeapi import gogoanime

log = logging.getLogger('main')

def search_for_anime(name):
  mal_search = mal.AnimeSearch(name)
  for anime in mal_search.results[:5]:
    print(anime.title, anime.episodes)
  gogo_search = gogoanime.get_search_results(query=name)
  for title in gogo_search[:5]:
    episodes = gogoanime.get_anime_details(animeid=title['animeid'])['episodes']
    print(title['name'], episodes)

if __name__ == '__main__':
  search_for_anime('Spy family')
