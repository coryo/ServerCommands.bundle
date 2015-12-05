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

################################################################################
def server_request(endpoint, method='GET', data=None):
    url = "http://127.0.0.1:32400" + endpoint
    # Borrow the req headers from the current client
    headers = {k: Request.Headers[k] for k in Request.Headers
               if k.startswith('X-Plex')}

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

def get_xml(endpoint):
    code, msg = server_request(endpoint, method='GET')
    Log.Info("%s - %s" % (endpoint, code))
    try:
        xml = XML.ElementFromString(msg)
    except Exception:
        return None
    else:
        return xml
################################################################################
def Start():
    ObjectContainer.title1 = NAME

@handler(PREFIX, NAME, ICON)
def MainMenu():       
    oc = ObjectContainer()

    Updater(PREFIX + '/updater', oc)

    oc.add(DirectoryObject(
        key=Callback(LibrarySections),
        title="Library: Sections ..."
    ))
    oc.add(DirectoryObject(
        key=Callback(ExecuteCommand, method='GET',
                     endpoint='/library/sections/all/refresh'),
        title=u'Library: Refresh All'
    ))
    oc.add(DirectoryObject(
        key=Callback(ExecuteCommand, method='PUT',
                     endpoint='/library/optimize'),
        title="Library: Optimize"
    ))
    oc.add(DirectoryObject(
        key=Callback(ExecuteCommand, method='PUT',
                     endpoint='/library/clean/bundles'),
        title="Library: Clean Bundles"
    ))

    oc.add(DirectoryObject(
        key=Callback(BrowseContainers, endpoint='/library/sections'),
        title="Library: Browse"
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

@route(PREFIX+'/sections')
def LibrarySections():
    """ List library sections and provide links for the functions """
    oc = ObjectContainer(title2=L('Libraries'))

    res = get_xml('/library/sections')

    if res is None:
        return oc

    endpoints = {
        "Refresh":     "GET /library/sections/%s/refresh",
        "Empty Trash": "PUT /library/sections/%s/emptyTrash",
        "Analyze":     "PUT /library/sections/%s/analyze"
    }

    for item in res.xpath('//Directory'):
        key = item.xpath("@key")[0]
        title = item.xpath("@title")[0]
        thumb = PLEX_ICONS[item.xpath('@type')[0]]

        for function, path in endpoints.iteritems():
            method, endpoint = path.split(' ')
            Log("%s - %s" % (method, endpoint%key))
            oc.add(DirectoryObject(
                key=Callback(ExecuteCommand, method=method,
                             endpoint=endpoint%key),
                title=u'%s: %s' % (title, function),
                thumb=thumb,
            ))

    return oc

@route(PREFIX+'/browse')
def BrowseContainers(endpoint):
    """
    Follow paths until you get to a metadata item, then go to the metadata menu
    """

    oc = ObjectContainer()

    res = get_xml(endpoint)

    if res is None:
        return oc

    for item in res.xpath('//Directory | //Video | //Photo'):
        key = item.xpath("@key")[0]

        try:
            thumb = item.xpath("@thumb")[0]
        except Exception:
            thumb = None

        try:
            rating_key = item.xpath("@ratingKey")[0]
        except Exception:
            rating_key = None

        item_endpoint = "%s/%s" %(endpoint, key) if '/' not in key else key

        if not rating_key:
            oc.add(DirectoryObject(
                key=Callback(BrowseContainers, endpoint=item_endpoint),
                title=u'%s' % (item.xpath("@title")[0]),
                thumb=thumb,
            ))
        else:
            oc.add(DirectoryObject(
                key=Callback(MetadataMenu, item=rating_key),
                title=u'%s' % (item.xpath("@title")[0]),
                thumb=thumb,
            ))

    return oc

@route(PREFIX+'/metadatamenu')
def MetadataMenu(item):
    """ Actions to be performed on a metadata item """

    oc = ObjectContainer()

    endpoints = {
        "Refresh": "PUT /library/metadata/%s/refresh",
        "Analyze": "PUT /library/metadata/%s/analyze"
    }

    for func, path in endpoints.iteritems():
        method, endpoint = path.split(' ')
        oc.add(DirectoryObject(
            key=Callback(ExecuteCommand, method=method, endpoint=endpoint%item),
            title=u'%s' % L(func),
        ))

    return oc
