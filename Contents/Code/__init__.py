import requests
from updater import Updater
from DumbTools import DumbPrefs

NAME = 'Server Commands'
PREFIX = '/video/servercommands'
ICON = 'icon-default.png'

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
def server_request(endpoint, method='GET', token=None, data=None):
    url = "http://127.0.0.1:32400" + endpoint
    headers = {
        'Accept': 'application/json',
        'X-Plex-Token': token if token is not None else Dict['token']
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

    Log.Info('%s %s - %s' % (method, endpoint, res.status_code))
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
        server_request('/testauth', method='GET', token=token)[0] != 401

def add_functions_to_oc(oc, functions, item=None, title=None):
    for func, path in functions.iteritems():
        if not Prefs[func]:
            continue
        method, endpoint = path.split(' ')
        endpoint = endpoint if item is None else endpoint % item
        oc.add(DirectoryObject(
            key=Callback(ExecuteCommand, method=method, endpoint=endpoint, data=None),
            title=u'%s: %s' % (title, L(func)) if title else u'%s' % L(func)
        ))

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
        add_functions_to_oc(oc, FUNCTIONS['/library'], title=L('Library'))

        oc.add(DirectoryObject(
            key=Callback(BrowseContainers,
                         endpoint='/library/sections',
                         functions=FUNCTIONS['/library/sections']),
            title=u'%s: %s ...' % (L('Library'), L('Sections'))
        ))

        oc.add(DirectoryObject(
            key=Callback(BrowseContainers, endpoint='/library/sections'),
            title=u'%s: %s ...' % (L('Library'), L('Browse'))
        ))

        if is_authorized(Request.Headers['X-Plex-Token']):
            oc.add(DirectoryObject(
                key=Callback(UpdateToken, token=None),
                title=u'%s' % L('Deauthorize Channel')
            ))

            if Client.Product in DumbPrefs.clients:
                DumbPrefs(PREFIX, oc, title=L('Preferences'))
            else:
                oc.add(PrefsObject(title=L('Preferences')))

    return oc

################################################################################
# ROUTES
################################################################################
@route(PREFIX+'/execute', data=dict)
def ExecuteCommand(endpoint, method='GET', data=None):
    """
    A route for making requests. The request is done in a separate thread
    to prevent the client from timing out on some requests.
    """
    Log.Info("Creating request thread: %s %s" % (method,endpoint))
    Thread.CreateTimer(1, server_request, endpoint=endpoint, method=method, data=data)
    if Client.Platform in ['Plex Home Theater', 'OpenPHT']:
        # PHT will start the thread and not go anywhere. There is no feedback to
        # the user, but atleast it doesn't break. MessageContainer kind of works
        # but it kicks you back to the channel menu and the channel history
        # is broken when you try and go back to it.
        return None
    else:
        # PMP/Plex Web uses this nicely
        return MessageContainer(header=u'Command', message=u'%s %s' % (method, endpoint))

@route(PREFIX+'/browse', functions=dict)
def BrowseContainers(endpoint, functions=None):
    """
    if functions are specified, the callback will go immediately to the
    function menu, otherwise we will keep browsing until we find metadata items.
    """
    oc = ObjectContainer(title2=endpoint)

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

            callback = Callback(FunctionMenu, item=item_id, functions=item_func, title=None)
        else:
            callback = Callback(BrowseContainers, endpoint=item_endpoint)

        oc.add(DirectoryObject(key=callback, title=u'%s' % title, thumb=thumb))

    return oc

@route(PREFIX+'/functionmenu', functions=dict)
def FunctionMenu(functions, item=None, title=None):
    """ Actions to be performed on a metadata item """
    oc = ObjectContainer()
    add_functions_to_oc(oc, functions, item=item, title=title)
    return oc

@route(PREFIX+'/updatetoken')
def UpdateToken(token):
    Dict['token'] = token
    Dict.Save()
    return ObjectContainer()
