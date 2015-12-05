import requests
from updater import Updater

NAME   = 'Server Commands'
PREFIX = '/video/servercommands'
ICON   = 'icon-default.png'

PLEX_ICONS = {
        'channels': R("glyphicons-show-big-thumbnails.png"),
        'movie':    R("glyphicons-film.png"),
        'artist':   R("glyphicons-music.png"),
        'photo':    R("glyphicons-picture.png"),
        'show':     R("glyphicons-display.png")
}

####################################################################################################                 
def Start():

        ObjectContainer.title1 = NAME

@handler(PREFIX, NAME, ICON)
def MainMenu():       

        oc = ObjectContainer()
        Updater(PREFIX + '/updater', oc)

        oc.add(DirectoryObject(
                key   = Callback(LibrarySections),
                title = "Library: Sections ..."
        ))
        oc.add(DirectoryObject(
                key   = Callback(ServerRequest, method='GET', endpoint='/library/sections/all/refresh'),
                title = u'Library: Refresh All'
        ))
        oc.add(DirectoryObject(
                key   = Callback(ServerRequest, method='PUT', endpoint='/library/optimize'),
                title = "Library: Optimize"
        ))
        oc.add(DirectoryObject(
                key   = Callback(ServerRequest, method='PUT', endpoint='/library/clean/bundles'),
                title = "Library: Clean Bundles"
        ))


        return oc

####################################################################################################  
@route(PREFIX+'/command', data=dict, xml=bool)
def ServerRequest(endpoint, method='GET', data=None, xml=False):

        url = "http://127.0.0.1:32400" + endpoint
        # Borrow the req headers from the current client
        headers = {k: Request.Headers[k] for k in Request.Headers if k.startswith('X-Plex')}

        if method == 'GET':
                r = requests.get(url, headers=headers)
        elif method == 'POST':
                r = requests.post(url, headers=headers, data=data)
        elif method == 'PUT':
                r = requests.put(url, headers=headers)
        elif method == 'DELETE':
                r = requests.delete(url, headers=headers)

        if xml:
                try:
                        xml_data = XML.ElementFromString(r.text)
                        return xml_data
                except:
                        return None
        else:
                return ObjectContainer()

@route(PREFIX+'/library/sections')
def LibrarySections():

        oc = ObjectContainer(title2=L('Libraries'))

        data = ServerRequest(endpoint='/library/sections', method='GET', xml=True)

        if not data:
                return oc

        for item in data.xpath('//Directory'):
                endpoint = "/library/sections/%s" % item.xpath("@key")[0]
                thumb    = PLEX_ICONS[item.xpath('@type')[0]]

                oc.add(DirectoryObject(
                        key   = Callback(ServerRequest, method='GET', endpoint=endpoint+"/refresh"),
                        title = u'%s: Refresh' % (item.xpath("@title")[0]),
                        thumb = thumb,
                ))
                oc.add(DirectoryObject(
                        key   = Callback(ServerRequest, method='PUT', endpoint=endpoint+"/emptyTrash"),
                        title = u'%s: Empty Trash' % (item.xpath("@title")[0]),
                        thumb = thumb,
                ))
                oc.add(DirectoryObject(
                        key   = Callback(ServerRequest, method='PUT', endpoint=endpoint+"/analyze"),
                        title = u'%s: Analyze' % (item.xpath("@title")[0]),
                        thumb = thumb,
                ))

        return oc