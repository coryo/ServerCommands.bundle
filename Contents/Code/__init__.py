import requests
from updater import Updater

NAME = 'Server Commands'
PREFIX = '/video/servercommands'
ICON = 'icon-default.png'

PLEX_ICONS = {
    'channels': R("glyphicons-show-big-thumbnails.png"),
    'movie':    R("glyphicons-film.png"),
    'artist':   R("glyphicons-music.png"),
    'photo':    R("glyphicons-picture.png"),
    'show':     R("glyphicons-display.png")
}
FUNCTIONS = {
    '/library': {
        "refresh_all":   "GET /library/sections/all/refresh",
        "optimize":      "PUT /library/optimize",
        "clean_bundles": "PUT /library/clean/bundles"
    },
    '/library/sections': {
        "refresh":     "GET /library/sections/%s/refresh",
        "empty_trash": "PUT /library/sections/%s/emptyTrash",
        "analyze":     "PUT /library/sections/%s/analyze"
    },
    '/library/metadata': {
        "refresh": "PUT /library/metadata/%s/refresh",
        "analyze": "PUT /library/metadata/%s/analyze"
    }
}

################################################################################
def server_request(endpoint, method='GET', data=None):
    url = "http://127.0.0.1:32400" + endpoint
    headers = {
        'Accept': 'application/json',
        'X-Plex-Token': Dict['token']
    }

    res = None
    if method == 'GET':
        res = requests.get(url, headers=headers)
    elif method == 'POST':
        res = requests.post(url, headers=headers, data=data)
    elif method == 'PUT':
        res = requests.put(url, headers=headers)
    elif method == 'DELETE':
        res = requests.delete(url, headers=headers)

    return (res.status_code, res.text)

def get_json(endpoint):
    code, msg = server_request(endpoint, method='GET')
    Log.Info("%s - %s" % (endpoint, code))
    try:
        json = JSON.ObjectFromString(msg)
    except Exception:
        return None
    else:
        return json

def is_authorized(token):
    """
    returns true if the given token has the auth we need.
    auth is tested on an endpoint that either returns 401 or 404
    """
    return False if token is None else \
        server_request('/testauth', method='GET')[0] != 401
################################################################################
def Start():
    ObjectContainer.title1 = NAME
    if 'token' not in Dict:
        Dict['token'] = None

@handler(PREFIX, NAME, ICON)
def MainMenu():       
    oc = ObjectContainer(no_cache=True)

    Updater(PREFIX + '/updater', oc)

    if not is_authorized(Dict['token']):
        oc.add(DirectoryObject(
            key=Callback(UpdateToken, token=Request.Headers['X-Plex-Token']),
            title=u'%s' % L('auth_message'),
            summary=u'%s' % L('auth_message')
        ))
    else:
        for func, path in FUNCTIONS['/library'].iteritems():
            if not Prefs[func]:
                continue

            method, endpoint = path.split(' ')
            oc.add(DirectoryObject(
                key=Callback(ExecuteCommand, method=method, endpoint=endpoint),
                title=u'%s: %s' % (L('Library'), L(func))
            ))

        oc.add(DirectoryObject(
            key=Callback(BrowseContainers, endpoint='/library/sections',
                         functions=FUNCTIONS['/library/sections']),
            title=u'%s: %s ...' % (L('Library'), L('Sections'))
        ))

        oc.add(DirectoryObject(
            key=Callback(BrowseContainers, endpoint='/library/sections'),
            title=u'%s: %s ...' % (L('Library'), L('Browse'))
        ))

        if Request.Headers['X-Plex-Token'] == Dict['token']:
            oc.add(DirectoryObject(
                key=Callback(UpdateToken, token=None),
                title=u'%s' % L('Deauthorize Channel')
            ))

        oc.add(PrefsObject(
            title = L('Preferences')
        ))

    return oc

################################################################################
# ROUTES
################################################################################
@route(PREFIX+'/execute', data=dict)
def ExecuteCommand(endpoint, method='GET', data=None):
    """
    A route for making requests.
    Returns an object container to the client
    """
    code, msg = server_request(endpoint, method, data)
    Log.Info("%s - %s - %d" % (endpoint, code, len(msg)))
    return ObjectContainer()

@route(PREFIX+'/browse', functions=dict)
def BrowseContainers(endpoint, functions=None):
    """
    if functions are specified, the callback will go immediately to the
    function menu, otherwise we will keep browsing until we find metadata items.
    """
    oc = ObjectContainer()

    res = get_json(endpoint)

    if res is None:
        return oc

    for item in res['_children']:
        key = item['key']

        thumb = item['thumb'] if 'thumb' in item else None
        rating_key = item['ratingKey'] if 'ratingKey' in item else None
        title = item['title']
        item_endpoint = "%s/%s" %(endpoint, key) if '/' not in key else key

        if functions is not None or rating_key is not None:
            item_func = FUNCTIONS['/library/metadata'] if functions is None \
                        else functions
            item_id = key if rating_key is None else rating_key

            callback = Callback(FunctionMenu, item=item_id, functions=item_func)
        else:
            callback = Callback(BrowseContainers, endpoint=item_endpoint)

        oc.add(DirectoryObject(key=callback, title=u'%s' % title, thumb=thumb))

    return oc

@route(PREFIX+'/functionmenu', functions=dict)
def FunctionMenu(functions, item=None):
    """ Actions to be performed on a metadata item """
    oc = ObjectContainer()

    for func, path in functions.iteritems():
        if not Prefs[func]:
            continue

        method, endpoint = path.split(' ')
        endpoint = endpoint if item is None else endpoint % item
        oc.add(DirectoryObject(
            key=Callback(ExecuteCommand, method=method, endpoint=endpoint),
            title=u'%s' % L(func),
        ))

    return oc

@route(PREFIX+'/updatetoken')
def UpdateToken(token):
    Dict['token'] = token
    Dict.Save()
    return ObjectContainer()
