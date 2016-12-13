import requests
import os
from updater import Updater
from DumbTools import DumbPrefs

NAME = 'Server Commands'
PREFIX = '/video/servercommands'
ICON = 'icon-default.png'

# Single shot functions
FUNCTIONS = {
    '/library': {
        "refresh_all":    "GET /library/sections/all/refresh",
        "cancel_refresh": "DELETE /library/sections/all/refresh",
        "optimize":       "PUT /library/optimize",
        "clean_bundles":  "PUT /library/clean/bundles"
    },
    '/library/sections': {
        "refresh":        "GET /library/sections/%s/refresh",
        "cancel_refresh": "DELETE /library/sections/%s/refresh",
        "empty_trash":    "PUT /library/sections/%s/emptyTrash",
        "analyze":        "PUT /library/sections/%s/analyze"
    },
    '/library/metadata': {
        "refresh": "PUT /library/metadata/%s/refresh",
        "analyze": "PUT /library/metadata/%s/analyze"
    }
}
# Functions that need to be performed in sequence, with menus in between
MULTI_STEP_FUNCTIONS = {
    'fix_match': [
        "GET /library/metadata/%s/matches?manual=1",
        "PUT /library/metadata/%s/match?guid=%s&name=%s"
    ]
}

################################################################################
def server_request(endpoint, method='GET', data=None):
    url = "http://127.0.0.1:32400" + endpoint
    headers = {
        'Accept': 'application/json',
        'X-Plex-Token': os.environ['PLEXTOKEN']
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

def add_functions_to_oc(oc, functions, item=None, title=None):
    for func, path in functions.iteritems():
        if not Prefs[func]:
            continue
        method, endpoint = path.split(' ')
        endpoint = endpoint if item is None else endpoint % item
        item_title = '%s: %s' % (title, L(func)) if title else L(func)
        oc.add(DirectoryObject(key=Callback(ExecuteCommand, method=method,
                                            endpoint=endpoint, data=None),
                               title=unicode(item_title)))

def error_message(header, message):
    if Client.Platform in ['Plex Home Theater', 'OpenPHT']:
        return ObjectContainer(objects=[DirectoryObject(title=u'{}: {}'.format(header, message),
                                                        key=None)])
    else:
        return MessageContainer(header=unicode(header), message=unicode(message))

################################################################################
def Start():
    ObjectContainer.title1 = NAME

@handler(PREFIX, NAME, ICON)
def MainMenu():       
    oc = ObjectContainer(no_cache=True)

    oc.add(DirectoryObject(key=Callback(BrowseContainers, endpoint='/library/sections',
                                        functions=FUNCTIONS['/library/sections']),
                           title=u'%s: %s ...' % (L('Library'), L('Sections'))))
    oc.add(DirectoryObject(key=Callback(BrowseContainers, endpoint='/library/sections'),
                           title=u'%s: %s ...' % (L('Library'), L('Browse'))))
    add_functions_to_oc(oc, FUNCTIONS['/library'], title=L('Library'))

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
    return error_message(header='Command', message='%s %s' % (method, endpoint))

@route(PREFIX+'/browse', functions=dict)
def BrowseContainers(endpoint, functions=None):
    """
    if functions are specified, the callback will go immediately to the
    function menu, otherwise we will keep browsing until we find metadata items.
    """
    oc = ObjectContainer(title2=endpoint)

    res = get_json(endpoint)
    if res is None:
        return error_message(header=oc.title2, message='Error')
    if not res['MediaContainer']:
        return error_message(header=oc.title2, message='No child items')

    if 'Directory' in res['MediaContainer']:
        items = res['MediaContainer']['Directory']
    elif 'Metadata' in res['MediaContainer']:
        items = res['MediaContainer']['Metadata']
    else:
        return error_message(header=oc.title2, message='No child items')

    for item in items:
        key = item['key']
        metadata = key.startswith('/library/metadata')
        thumb = item['thumb'] if 'thumb' in item else None
        rating_key = item['ratingKey'] if 'ratingKey' in item else None
        title = item['title']
        item_endpoint = "%s/%s" %(endpoint, key) if '/' not in key else key

        # if functions is not None or rating_key is not None:
        if functions is not None or metadata:
            item_func = FUNCTIONS['/library/metadata'] if functions is None \
                        else functions
            item_id = key if rating_key is None else rating_key
            callback = Callback(FunctionMenu, item=item_id, functions=item_func, title=None,
                                metadata=metadata)
        else:
            callback = Callback(BrowseContainers, endpoint=item_endpoint)
        oc.add(DirectoryObject(key=callback, title=u'%s' % title, thumb=thumb))
    return oc

@route(PREFIX+'/functionmenu', functions=dict, metadata=bool)
def FunctionMenu(functions, item=None, title=None, metadata=False):
    """ Actions to be performed on a metadata item """
    oc = ObjectContainer()
    add_functions_to_oc(oc, functions, item=item, title=title)
    if metadata and Prefs['fix_match']:
        oc.add(DirectoryObject(key=Callback(Matches, item=item),
                               title=L('fix_match')))
    return oc

@route(PREFIX+'/matches')
def Matches(item):
    """
    return a list of matches, with callback to replace the metadata with
    the chosen match
    """
    # First Step
    step_method, step_endpoint = MULTI_STEP_FUNCTIONS['fix_match'][0].split()
    data = get_json(step_endpoint % item)
    oc = ObjectContainer(title2=L('fix_match'))
    if data is None:
        return error_message(header=L('fix_match'), message='Error')
    if not data['MediaContainer']:
        return error_message(header=L('fix_match'), message='No Matches')

    # Second Step
    step_method, step_endpoint = MULTI_STEP_FUNCTIONS['fix_match'][1].split()
    for result in data['MediaContainer']['SearchResult']:
        title = '[%s%%] %s - %s' % (result['score'], result.get('year', None), result['name'])
        guid = String.Quote(result['guid'], usePlus=True)
        name = String.Quote(result['name'], usePlus=True)
        oc.add(DirectoryObject(key=Callback(ExecuteCommand, method=step_method,
                                            endpoint=step_endpoint%(item, guid, name)),
                               thumb=Resource.ContentsOfURLWithFallback(result.get('thumb', None)),
                               title=unicode(title)))
    return oc
