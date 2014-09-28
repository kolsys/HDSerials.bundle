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


@route(PREFIX + '/category')
def ShowCategory(path, title):
    oc = ObjectContainer(title2=u'%s' % title)
    return oc


@route(PREFIX + '/info')
def ShowInfo(path):

    info = ParsePage(path)
    if not info:
        return ContentNotFound()

    oc = ObjectContainer(title2=info['title'])

    if info['seasons']:
        call = VideoSeasons
        if len(info['seasons']) == 1:
            call = VideoEpisodes
        oc.add(TVShowObject(
            key=Callback(
                call,
                info=JSON.StringFromObject(info)
            ),
            rating_key=path,
            title=u'%s' % info['title'],
            rating=info['rating'],
            summary=info['summary'],
            thumb=info['thumb'],
            source_icon=ICON,
            countries=info['countries'] if 'countries' in info else None,
        ))
    else:
        oc.add(GetVideoObject(info))

    return oc


@route(PREFIX + '/seasons')
def VideoSeasons(info):
    data = JSON.ObjectFromString(info)

    oc = ObjectContainer(title2=data['title'])
    seasons = data['seasons'].keys()

    seasons.sort(key=lambda k: int(k))
    for season in seasons:
        oc.add(SeasonObject(
            key=Callback(
                VideoEpisodes,
                info=info,
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
def VideoEpisodes(info, season='1'):

    data = JSON.ObjectFromString(info)

    if season != data['current_season']:
        update = GetInfoByURL(
            GetEpisodeURL(data['url'], season, 1),
            data['url']
        )
        if not update:
            return ContentNotFound()

        data.update(update)

    oc = ObjectContainer(title2=data['title'])

    episodes = data['episodes'].keys()
    episodes.sort(key=lambda k: int(k))

    for episode in episodes:
        oc.add(GetVideoObject(data, episode))

    return oc


@route(PREFIX + '/view')
def VideoView(info, episode):
    item = JSON.ObjectFromString(info)

    if not item:
        raise Ex.MediaNotAvailable

    if episode and episode != item['current_episode']:
        update = GetInfoByURL(GetEpisodeURL(
            item['url'],
            item['current_season'],
            episode
        ), item['url'])
        if not update:
            return ContentNotFound()
        item.update(update)

    return ObjectContainer(objects=[GetVideoObject(item, episode)])


# @route(PREFIX + '/view/extras')
# def VideoViewExtras():
#     return ObjectContainer()


@route(PREFIX + '/play.m3u')
def VideoPlay(session):
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
    except:
        raise Ex.MediaNotAvailable

    res = [line for line in res.split("\n") if line].pop()

    Log.Debug('Try to play %s' % res)

    # return IndirectResponse(VideoClipObject, key=HTTPLiveStreamURL(res))

    # Some players does not support gziped response
    path = res.split('/')
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

    if episode:
        obj = EpisodeObject(
        # obj = VideoClipObject(
            key=Callback(
                VideoView,
                info=JSON.StringFromObject(item),
                episode=episode
            ),
            rating_key=GetEpisodeURL(
                item['url'],
                item['current_season'],
                episode
            ),
            source_title=TITLE,
            # summary=item['summary'],
            thumb=item['thumb'],
            source_icon=ICON,
            rating=item['rating'],
            title=item['episodes'][episode],
            # season=int(item['current_season']),
            # index=int(episode),
            # show=item['title'],

            duration=2637000,
            originally_available_at=date.fromtimestamp(1380571200),

            directors=item['directors'] if 'directors' in item else None,
            # guest_stars=item['roles'] if 'roles' in item else None,
        )
    else:
        obj = MovieObject(
            key=Callback(
                VideoView,
                info=JSON.StringFromObject(item),
                episode=episode
            ),
            source_title=TITLE,
            summary=item['summary'],
            thumb=item['thumb'],
            source_icon=ICON,
            rating=item['rating'],
            title=item['title'],
            rating_key=item['url'],
            original_title=item['original_title'],
            roles=item['roles'] if 'roles' in item else None,
            countries=item['countries'] if 'countries' in item else None,
            directors=item['directors'] if 'directors' in item else None,
            genres=item['genres'] if 'genres' in item else None,
            year=int(item['year']) if 'year' in item else None,
        )

    obj.add(MediaObject(
        parts=[PartObject(
            key=HTTPLiveStreamURL(
                Callback(
                    VideoPlay,
                    session=JSON.StringFromObject(item['session'])
                )
            )
        )],
        video_resolution=720,
        container=Container.MP4,
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

    page = GetPage(path).xpath(
        '//div[@id="k2Container"]'
    )[0]

    try:
        url = page.xpath(
            '//div[@class="itemFullText"]/p/iframe[@src]'
        )[0].get('src')
    except:
        return None

    data = GetInfoByURL(url)

    if not data:
        return None

    ret = {
        'path': path,
        'rating': 0.00,
        'thumb': HDSERIALS_URL + page.xpath(
            '//div[@class="itemImageBlock"]//a'
        )[0].get('href'),
        'url': url,
    }

    title = [
        l.strip() for l in page.xpath(
            '//h2[@class="itemTitle"]'
        )[0].text_content().split('/')
    ]

    title.reverse()
    ret['title'] = title.pop()
    ret['original_title'] = title.pop() if len(title) else None


    # TODO
    meta = page.xpath(
        '//div[@class="itemFullText"]//text() | //span'
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
    for desc in meta:
        if not isinstance(desc, basestring):
            continue
        if not desc:
            current = None
            continue

        if desc in tmap:
            current = desc
        elif current:
            if desc[:1] == ':':
                desc = desc[2:]
            data[tmap[current]] = desc

    for current in ('countries', 'genres', 'directors', 'roles'):
        if current in data:
            data[current] = [l.strip() for l in data[current].split(',')]

    # rating = float(Regex('width\s?:\s?([\d\.]+)').search(
    #     page.xpath(
    #         '//div[@class="itemRatingBlock"]//li[@class="itemCurrentRating"]'
    #     )[0].get('class')
    # ).group(1)) * 10

    ret.update(data)

    return ret


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
        'session': JSON.ObjectFromString('{%s}' % data.group(1)),
    }

    if ret['session']['content_type'] == 'serial':
        res = HTML.ElementFromString(page)
        ret['seasons'] = {}
        ret['episodes'] = {}
        for item in res.xpath('//select[@id="season"]/option'):
            value = item.get('value')
            ret['seasons'][value] = item.text_content()
            if item.get('selected'):
                ret['current_season'] = value

        for item in res.xpath('//select[@id="episode"]/option'):
            value = item.get('value')
            ret['episodes'][value] = item.text_content()
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
