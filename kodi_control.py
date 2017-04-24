#!bin/python
from flask import Flask, jsonify, request, make_response
from fuzzywuzzy import process, fuzz
import requests, json, re
import random
import kodi_creds

app = Flask(__name__)

KODI=kodi_creds.address
USER=kodi_creds.username
PW=kodi_creds.password

def active_player():
    library = requests.get('http://%s/jsonrpc?request={"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}' % KODI, auth=(USER, PW))
    if json.loads(library.text)['result']:
        return True
    return False

def play_pause():
    library = requests.get('http://%s/jsonrpc?request={"jsonrpc": "2.0", "method": "Player.PlayPause", "params": {"playerid":1}, "id": 1}' % KODI, auth=(USER, PW))
    return library.text

def update_movies():
    library = requests.get('http://%s/jsonrpc?request={"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": { "sort": { "order": "ascending", "method": "label", "ignorearticle": true } }, "id": "libMovies"}' % KODI, auth=(USER, PW))
    return library.text

def update_tv():
    library = requests.get('http://%s/jsonrpc?request={"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": { "sort": { "order": "ascending", "method": "label", "ignorearticle": true } }, "id": "libTV"}' % KODI, auth=(USER, PW))
    return library.text

def get_episodes_for_show(tvshowid):
    library = requests.get('http://%s/jsonrpc?request={"jsonrpc":"2.0", "method": "VideoLibrary.GetEpisodes", "id": 1, "params": { "properties":["season", "episode", "tvshowid"], "tvshowid": %s , "sort": {"order": "descending", "method": "lastplayed"}}}' % (KODI, tvshowid), auth=(USER, PW) )
    return library.text

def get_season(season, tvshowid):
    library = requests.get('http://%s/jsonrpc?request={"jsonrpc":"2.0", "method": "VideoLibrary.GetEpisodes", "id": 1, "params": { "properties":["season", "episode", "tvshowid"], "tvshowid": %s , "season": %d, "sort": {"order": "descending", "method": "lastplayed"}}}' % (KODI, tvshowid, int(season)), auth=(USER, PW) )
    return library.text


def get_seasons(tvshowid):
    library = requests.get('http://%s/jsonrpc?request={"jsonrpc":"2.0", "method": "VideoLibrary.GetSeasons", "id": 1, "params": { "properties":["season", "episode", "tvshowid"], "tvshowid": %s , "sort": {"order": "descending", "method": "lastplayed"}}}' % (KODI, tvshowid), auth=(USER, PW) )
    return library.text



def play_movie(movieid):
    req = requests.get('http://%s/jsonrpc?request={"jsonrpc": "2.0", "params": {"item": {"movieid": %s}}, "method": "Player.Open", "id": 1}' % (KODI, movieid), auth=(USER, PW))

def play_episode(episodeid):
    req = requests.get('http://%s/jsonrpc?request={"jsonrpc": "2.0", "params": {"item": {"episodeid": %s}}, "method": "Player.Open", "id": 1}' % (KODI, episodeid), auth=(USER, PW))



@app.route('/webhook', methods=['POST'])
def webhook():
    #if active_player():
    req = request.get_json(silent=True, force=True)
    print ("Request:{}".format(json.dumps(req, indent=4)))
    resp = {}
    if req.get("result").get("parameters").get("media_type") == "movie":
        resp = process_movie(req)
    elif req.get("result").get("parameters").get("media_type") == "show":
        resp = process_tv(req)
    r = make_response(resp)
    r.headers['Content-Type'] = 'application/json'
    return r

def generate_response(speech):
    print ("Response:{}".format(speech))
    resp = {
        "speech": speech,
        "displayText": speech,
        "source": "kodi-control"
    }
    return json.dumps(resp, indent=4)

def process_movie(req):
    title = req.get("result").get("parameters").get("media_name")
    movies  =  json.loads(update_movies())
    titles = tuple([(movie['label'], movie['movieid']) for movie in movies['result']['movies']])
    match = process.extractOne(title, titles, scorer=fuzz.token_sort_ratio)
    #play_movie(match[0][1])
    speech = "Playing {}".format(match[0][0])
    #return str(match[0])
    return generate_response(speech)

def process_tv(req):
    title = req.get("result").get("parameters").get("media_name")
    shows  =  json.loads(update_tv())
    titles = tuple([(show['label'], show['tvshowid']) for show in shows['result']['tvshows']])
    if 'season' not in title:
        show = title
        show_match = process.extractOne(show.strip(), titles, scorer=fuzz.token_sort_ratio)
        seasons =  json.loads(get_seasons(show_match[0][1]))
        all_seasons = [s['season'] for s in seasons['result']['seasons']]
        season = random.choice(all_seasons)
        print ('Chosen Season: {}'.format(season))
        season_lib = json.loads(get_season(season, show_match[0][1]))
        all_episodes = [e['episode']for e in season_lib['result']['episodes']]
        episode = random.choice(all_episodes)
        print ('Chosen Episode: {}'.format(episode))
    else:
        show, season, episode = re.compile('season|episode', re.IGNORECASE).split(title)
        show_match = process.extractOne(show.strip(), titles, scorer=fuzz.token_sort_ratio)
        season_lib = json.loads(get_season(season, show_match[0][1]))
        
    ep_id = [ep['episodeid'] for ep in season_lib['result']['episodes'] if ep['episode'] == int(episode)]
    #play_episode(str(ep_id[0]))
    #return str(show_match[0])
    speech = "Playing {} Season {} Episode {}".format(show_match[0][0], season, episode)
    #return str(match[0])
    return generate_response(speech)


if __name__ == '__main__':
    app.run(debug=True, host= '0.0.0.0')



#TODO Add support to simply say a show name and play a random episode for that show. Support for a random movies as well.
#Lookup KODI IP using DNS or upnp
#Need to fix TV to not error when no season/episode provided
