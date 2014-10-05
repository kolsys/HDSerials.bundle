# -*- coding: utf-8 -*-

# Copyright (c) 2014, KOL
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <organization> nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from urllib import urlencode
from datetime import date

PREFIX = '/video/hdserials'
HDSERIALS_URL = 'http://www.hdserials.tv'

ART = 'art-default.jpg'
ICON = R('icon-default.png')
TITLE = L('Title')


def Start():
    HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux i686; rv:32.0) Gecko/20100101 Firefox/32.0'
    InputDirectoryObject.art = R(ART)


###############################################################################
# Video
###############################################################################

@handler(PREFIX, TITLE, R(ART), ICON)
def MainMenu():
    cats = GetPage('/').xpath('//div[@id="gkDropMain"]//a[contains(@href, ".html")]')

    if not cats:
        return MessageContainer(
            L('Error'),
            L('Service not avaliable')
        )

    oc = ObjectContainer(title2=TITLE, no_cache=True)

    oc.add(DirectoryObject(
        key=Callback(ShowNews),
        title=u'Новые серии'
    ))
    oc.add(DirectoryObject(
        key=Callback(ShowPopular),
        title=u'Популярное'
    ))

    for cat in cats:
        title = cat.text_content()
        oc.add(DirectoryObject(
            key=Callback(ShowCategory, path=cat.get('href'), title=title),
            title=title
        ))

    return oc


@route(PREFIX + '/news')
def ShowNews():
    page = GetPage('/').xpath(
        '//div[@id="gkHeaderheader1"]//div[@class="custom"]/div'
    )
    if not page:
        return ContentNotFound()

    oc = ObjectContainer(title2=u'Новые серии')
    for item in page:
        oc.add(DirectoryObject(
            key=Callback(ShowInfo, path=item.find('a').get('href')),
            title=item.text_content()
        ))

    return oc


@route(PREFIX + '/popular')
def ShowPopular():
    page = GetPage('/popular.html').xpath(
        '//div[contains(@class, "nspArts")]//div[contains(@class, "nspArt")]/div'
    )
    if not page:
        return ContentNotFound()

    oc = ObjectContainer(title2=u'Популярное')
    for item in page:
        link = item.find('a')
        if link:
            oc.add(DirectoryObject(
                key=Callback(ShowInfo, path=link.get('href')),
                title=item.find('h4').text_content(),
                thumb=link.find('img').get('src')
            ))

    return oc


@route(PREFIX + '/category')
def ShowCategory(path, title, page=None):
    content = GetPage(path)

    if not content:
        return ContentNotFound()

    oc = ObjectContainer(title2=u'%s' % title)

    items = content.xpath(
        '//div[@class="itemList"]//div[@class="catItemBody"]//span[@class="catItemImage"]/a'
    )
    cats = None

    if not page:
        cats = content.xpath(
            '//div[@class="itemListSubCategories"]//div[contains(@class, "subCategory")]/h2/a'
        )

    if cats:
        if items:
            oc.add(DirectoryObject(
                title=u'Все %s' % title.lower(),
                key=Callback(ShowCategory, path=path, title=title, page=1)
            ))

        for item in cats:
            title = u'%s' % item.text_content()
            oc.add(DirectoryObject(
                title=title,
                key=Callback(ShowSubCategory, path=item.get('href'), title=title)
            ))
    elif items:
        for item in items:
            title = u'%s' % item.text_content()
            oc.add(DirectoryObject(
                title=u'%s' % item.get('title'),
                key=Callback(ShowInfo, path=item.get('href')),
                thumb='%s%s' % (
                    HDSERIALS_URL,
                    item.find('img').get('src')
                ),
            ))
    else:
        return ContentNotFound()

    return oc

    # oc.add(TVShowObject(
    #     key=Callback(
    #         call,
    #         path=path
    #     ),
    #     rating_key=path,
    #     title=u'%s' % info['title'],
    #     rating=info['rating'],
    #     summary=info['summary'],
    #     thumb=info['thumb'],
    #     source_icon=ICON,
    #     countries=info['countries'] if 'countries' in info else None,
    # ))

    return oc


@route(PREFIX + '/subcategory')
def ShowSubCategory(path, title):
    oc = ObjectContainer(title2=u'%s' % title)
    return oc


@route(PREFIX + '/info')
def ShowInfo(path):

    info = ParsePage(path)
    if not info:
        return ContentNotFound()

    oc = ObjectContainer(title2=info['title'])

    if 'seasons' in info:
        if len(info['seasons']) == 1:
            return Episodes(path)
        else:
            return Seasons(path)
    else:
        return View(path, None)


@route(PREFIX + '/seasons')
def Seasons(path):

    data = ParsePage(path)
    if not data:
        return ContentNotFound()

    oc = ObjectContainer(
        title2=data['title'],
        content=ContainerContent.Seasons
    )
    seasons = data['seasons'].keys()

    seasons.sort(key=lambda k: int(k))
    for season in seasons:
        oc.add(SeasonObject(
            key=Callback(
                Episodes,
                path=path,
                season=season
            ),
            rating_key=GetEpisodeURL(data['url'], season, 0),
            index=int(season),
            title=data['seasons'][season],
            source_title=TITLE,
            thumb=data['thumb'],
            # summary=data['summary']
        ))

    return oc


@route(PREFIX + '/episodes')
def Episodes(path, season='1'):

    data = ParsePage(path)
    if not data:
        return ContentNotFound()

    if season != data['current_season']:
        data = UpdateItemInfo(data, season, 1)
        if not data:
            return ContentNotFound()

    oc = ObjectContainer(
        title2=u'%s / %s' % (data['title'], data['seasons'][season]),
        content=ContainerContent.Episodes
    )

    episodes = data['episodes'].keys()
    episodes.sort(key=lambda k: int(k))

    for episode in episodes:
        oc.add(GetVideoObject(data, episode))

    return oc


@route(PREFIX + '/view')
def View(path, episode, variant=None):

    item = ParsePage(path)
    if not item:
        return ContentNotFound()

    if not item:
        raise Ex.MediaNotAvailable

    if episode and episode != item['current_episode']:
        item = UpdateItemInfo(item, item['current_season'], episode)
        if not item:
            return ContentNotFound()

    return ObjectContainer(
        objects=[GetVideoObject(item, episode)],
        content=ContainerContent.Episodes if episode else ContainerContent.Movies,
    )


@route(PREFIX + '/view/extras')
def ViewExtras():
    return ObjectContainer()


@indirect
@route(PREFIX + '/play')
def Play(session):
    res = JSON.ObjectFromURL(
        url='http://moonwalk.cc//sessions/create_session',
        values=JSON.ObjectFromString(session),
        method='POST',
        cacheTime=0
    )

    if not res:
        raise Ex.MediaNotAvailable

    try:
        res = HTTP.Request(res['manifest_m3u8']).content
        Log.Debug('Found streams: %s' % res)
    except:
        raise Ex.MediaNotAvailable

    res = [line for line in res.split("\n") if line].pop()

    Log.Debug('Try to play %s' % res)

    # host with ip can return bad headers
    # if Regex('https?://(?:\d+)\.(?:\d+)\.(?:\d+)\.(?:\d+)/').match(res):
    res = Callback(Playlist, res=res)

    return IndirectResponse(VideoClipObject, key=HTTPLiveStreamURL(res))


@route(PREFIX + '/playlist.m3u8')
def Playlist(res):

    Log.Debug('Modify playlist %s' % res)
    # Some players does not support gziped response
    path = res.replace('tracks-2,4', 'tracks-1,4').split('/')
    path.pop()
    path = '/'.join(path)
    try:
        res = HTTP.Request(res).content.split("\n")
    except:
        raise Ex.MediaNotAvailable

    for i in range(0, len(res)):
        if res[i] == '#EXT-X-ENDLIST':
            break
        if res[i][:1] != '#':
            res[i] = path + '/' + res[i]

    return "\n".join(res)


def GetVideoObject(item, episode=0):
    # if 'external' in item['files']:
    #     return URLService.MetadataObjectForURL(
    #         NormalizeExternalUrl(item['files']['external'])
    #     )

    kwargs = {
        'source_title': TITLE,
        'source_icon': ICON
    }

    for k in [
        'summary', 'thumb', 'directors',
        'rating', 'duration',
        'originally_available_at',
    ]:
        if k in item and item[k]:
            kwargs[k] = item[k]

    if episode:
        if 'roles' in item:
            kwargs['guest_stars'] = item['roles']

        obj = EpisodeObject(
            key=Callback(
                View,
                path=item['path'],
                episode=episode
            ),
            rating_key=GetEpisodeURL(
                item['url'],
                item['current_season'],
                episode
            ),
            title=item['episodes'][episode],
            season=int(item['current_season']),
            index=int(episode),
            show=item['title'],
            **kwargs
        )
    else:
        for k in ['year', 'original_title', 'countries']:
            if k in item and item[k]:
                kwargs[k] = item[k]

        # if 'roles' in item:
        #     kwargs['roles'] = [RoleObject(actor=v) for v in item['roles']]

        # obj = MovieObject(
        obj = VideoClipObject(
            key=Callback(
                View,
                path=item['path'],
                episode=episode
            ),
            title=item['title'],
            rating_key=item['url'],
            **kwargs
        )

    for k in item['variants']:
        obj.add(MediaObject(
            parts=[PartObject(
                key=Callback(
                    Play,
                    session=JSON.StringFromObject(item['variants'][k]['session'])
                ),
            )],
            video_resolution=720,
            container='mpegts',
            video_codec=VideoCodec.H264,
            audio_codec=AudioCodec.AAC,
            optimized_for_streaming=True,
            audio_channels=2
        ))

    return obj


###############################################################################
# Common
###############################################################################

def ContentNotFound():
    return MessageContainer(
        L('Ошибка'),
        L('Контент не найден')
    )


def ParsePage(path):
    if Data.Exists('parse_cache'):
        ret = Data.LoadObject('parse_cache')
        if ret and 'path' in ret and ret['path'] == path:
            Log.Debug('Return from cache %s' % path)
            return ret

    page = GetPage(path).xpath(
        '//div[@id="k2Container"]'
    )[0]

    data = {'variants': {}}
    try:
        for url in page.xpath(
            '//div[@class="itemFullText"]//iframe[@src]'
        ):
            Log.Debug('Found variant %s', url)
            variant = GetInfoByURL(url.get('src'))
            if variant:
                data['variants'][variant['url']] = variant

        if len(data['variants']) == 0:
            return None
    except:
        return None

    ret = {
        'path': path,
        'rating': 0.00,
        'thumb': '%s%s' % (
            HDSERIALS_URL,
            page.xpath(
                '//div[@class="itemImageBlock"]//a'
            )[0].get('href')
        ),
    }

    title = [
        l.strip() for l in page.xpath(
            '//h2[@class="itemTitle"]'
        )[0].text_content().split('/')
    ]

    ret['original_title'] = title.pop() if len(title) > 1 else None
    ret['title'] = ' / '.join(title)

    meta = page.xpath(
        '//div[@class="itemFullText"]//text() ' +
        '| //div[@class="itemFullText"]//span ' +
        '| //div[@class="itemFullText"]//strong ' +
        '| //div[@class="itemFullText"]//p[@style="text-align: center;"]'
    )

    tmap = {
        u'Описание': 'summary',
        u'Год выпуска': 'year',
        u'Страна': 'countries',
        u'Жанр': 'genres',
        u'Продолжительность': 'duration',
        u'Режиссер': 'directors',
        u'В ролях': 'roles',
    }

    current = None
    variants_names = []
    for desc in meta:
        if not isinstance(desc, basestring):
            if desc.tag == 'p' and u'Перевод' in desc.text_content():
                variants_names.append(desc.text_content())
                current = None
            continue
        if not desc:
            continue

        if desc in tmap:
            current = desc
        elif current:
            if desc[:1] == ':':
                desc = desc[2:]

            if tmap[current] in data:
                data[tmap[current]] = data[tmap[current]]+' '+unicode(desc)
            else:
                data[tmap[current]] = unicode(desc)

    for current in ('countries', 'genres', 'directors', 'roles'):
        if current in data:
            data[current] = [l.strip() for l in data[current].split(',')]

    # TODO
    data['duration'] = None
    # data['duration'] = Datetime.MillisecondsFromString(data['duration'])
    # data['rating'] = float(Regex('width\s?:\s?([\d\.]+)').search(
    #     page.xpath(
    #         '//div[@class="itemRatingBlock"]//li[@class="itemCurrentRating"]'
    #     )[0].get('class')
    # ).group(1)) * 10
    if 'year' in data:
        data['year'] = int(data['year'])

    for k in data['variants']:
        data['variants'][k]['variant_title'] = unicode(
            variants_names.pop(0)
        ) if variants_names else ''

    data.update(data['variants'].itervalues().next())

    ret.update(data)
    Data.SaveObject('parse_cache', ret)

    return ret


# TODO
# Нет первого сезона /Serialy/Sverh-estestvennoe/Sverh-estestvennoe-/-Supernatural.html
# Не все сезоны / серии есть в разных переводах /Serialy/Podpolnaya-Imperiya-/-Boardwalk-Empire/Podpolnaya-Imperiya.html
# Content not found /Anime/Romantika/Volchitsa-i-pryanosti-3-sezon-/-Spice-and-Wolf-3.html

def UpdateItemInfo(item, season, episode):
    update = GetInfoByURL(GetEpisodeURL(
        item['url'],
        season,
        episode
    ), item['url'])
    if not update:
        return None

    item.update(update)
    item['variants'][item['url']].update(update)

    Data.SaveObject('parse_cache', item)

    return item


def GetInfoByURL(url, parent=None):

    headers = {}
    if parent:
        headers['Referer'] = parent
        if 'Referer' in HTTP.Headers:
            url = '%s&%s' % (
                url,
                urlencode({'referer': HTTP.Headers['Referer']})
            )

    elif 'Referer' in HTTP.Headers:
        headers['Referer'] = HTTP.Headers['Referer']

    try:
        page = HTTP.Request(
            url,
            cacheTime=CACHE_1HOUR,
            headers=headers
        ).content
    except Ex.HTTPError, e:
        Log.Debug(e.hdrs)
        Log.Debug(e.msg)
        return None

    data = Regex(
        ('\$\.post\(\'/sessions\/create_session\', {((?:.|\n)+)}\)\.success')
    ).search(page, Regex.MULTILINE)

    if not data:
        return None

    ret = {
        'url': parent if parent else url,
        'session': JSON.ObjectFromString('{%s}' % data.group(1)),
    }

    if ret['session']['content_type'] == 'serial':
        res = HTML.ElementFromString(page)
        ret['seasons'] = {}
        ret['episodes'] = {}
        for item in res.xpath('//select[@id="season"]/option'):
            value = item.get('value')
            ret['seasons'][value] = unicode(item.text_content())
            if item.get('selected'):
                ret['current_season'] = value

        for item in res.xpath('//select[@id="episode"]/option'):
            value = item.get('value')
            ret['episodes'][value] = unicode(item.text_content())
            if item.get('selected'):
                ret['current_episode'] = value

    return ret


def GetEpisodeURL(url, season, episode):
    if season:
        return '%s?season=%d&episode=%d' % (url, int(season), int(episode))
    return url


def GetPage(uri, cacheTime=CACHE_1HOUR):
    try:
        if HDSERIALS_URL not in uri:
            uri = HDSERIALS_URL+uri

        res = HTML.ElementFromURL(uri, cacheTime=cacheTime)
        HTTP.Headers['Referer'] = uri
    except:
        res = HTML.Element('error')

    return res
