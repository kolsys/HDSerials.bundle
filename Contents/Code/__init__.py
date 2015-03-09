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
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTLICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

Common = SharedCodeService.common

def Start():
    HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux i686; rv:32.0) Gecko/20100101 Firefox/32.0'
    DirectoryObject.art = R(Common.ART)


###############################################################################
# Video
###############################################################################

@handler(
    Common.PREFIX,
    L(Common.TITLE),
    R(Common.ART),
    R(Common.ICON)
)
def MainMenu():
    cats = Common.GetPage('/').xpath(
        '//div[@id="gkDropMain"]//a[contains(@href, ".html")]'
    )

    if not cats:
        return MessageContainer(
            L('Error'),
            L('Service not avaliable')
        )

    oc = ObjectContainer(title2=L(Common.TITLE), no_cache=True)

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

    oc.add(InputDirectoryObject(
        key=Callback(Search),
        title=u'Поиск', prompt=u'Искать на HDSerials'
    ))
    oc.add(DirectoryObject(
        key=Callback(History),
        title=u'История'
    ))

    return oc


@route(Common.PREFIX + '/news')
def ShowNews():
    page = Common.GetPage('/').xpath(
        '//div[@id="gkHeaderheader1"]//div[@class="custom"]/div'
    )
    if not page:
        return ContentNotFound()

    oc = ObjectContainer(title2=u'Новые серии')
    for item in page:
        title = u'%s' % item.text_content()
        try:
            info = Common.ParseNewsTitle(title)
            title = u'%s - S%dE%d (%s)' % (
                info['title'],
                int(info['season']),
                int(info['episode']),
                info['date']
            )
            season = info['season']
            episode = info['episode']
        except:
            season = None
            episode = None
            pass
        oc.add(DirectoryObject(
            key=Callback(
                ShowInfo,
                path=item.find('a').get('href'),
                season=season
            ),
            title=title
        ))

    return oc


@route(Common.PREFIX + '/popular')
def ShowPopular():
    page = Common.GetPage('/popular.html').xpath(
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


@route(Common.PREFIX + '/category')
def ShowCategory(path, title, show_items=False):
    page = Common.GetPage(path)

    if not page:
        return ContentNotFound()

    oc = ObjectContainer(title2=u'%s' % title)

    items = page.xpath(
        '//div[@class="itemList"]//div[@class="catItemBody"]//span[@class="catItemImage"]/a'
    )
    cats = None

    if not show_items:
        cats = page.xpath(
            '//div[@class="itemListSubCategories"]//div[contains(@class, "subCategory")]/h2/a'
        )

    if cats:
        # Add all items category
        if items:
            oc.add(DirectoryObject(
                title=u'Все %s' % title.lower(),
                key=Callback(ShowCategory, path=path, title=title, show_items=True)
            ))

        for item in cats:
            title = u'%s' % item.text_content()
            oc.add(DirectoryObject(
                title=title,
                key=Callback(ShowCategory, path=item.get('href'), title=title)
            ))
    elif items:
        # View subcategory with single item
        if not show_items and len(items) == 1:
            return ShowInfo(items[0].get('href'))

        for item in items:
            title = u'%s' % item.text_content()
            oc.add(DirectoryObject(
                title=u'%s' % item.get('title'),
                key=Callback(ShowInfo, path=item.get('href')),
                thumb='%s%s' % (
                    Common.HDSERIALS_URL,
                    item.find('img').get('src')
                ),
            ))
        next_page = page.xpath(
            '//div[@class="k2Pagination"]/ul/li[@class="pagination-next"]/a'
        )
        if next_page:
            oc.add(NextPageObject(
                title=u'%s' % next_page[0].text_content(),
                key=Callback(
                    ShowCategory,
                    path=next_page[0].get('href'),
                    title=title,
                    show_items=True
                )
            ))
    else:
        return ContentNotFound()

    return oc


@route(Common.PREFIX + '/history')
def History():
    history = Data.LoadObject(Common.KEY_HISTORY)

    if not history or not len(history):
        return ContentNotFound()

    oc = ObjectContainer(title2=u'История')

    for item in sorted(
        history.values(),
        key=lambda k: k['time'],
        reverse=True
    ):
        oc.add(DirectoryObject(
            key=Callback(
                ShowInfo,
                path=item['path']
            ),
            title=u'%s' % item['title'],
            thumb=item['thumb']
        ))

    return oc


@route(Common.PREFIX + '/info')
def ShowInfo(path, **kwargs):

    info = ParsePage(path)
    if not info:
        return ContentNotFound()

    PushToHistory(info)

    if 'seasons' in info:
        if 'season' in kwargs and kwargs['season'] in info['seasons']:
            return Episodes(info['path'], kwargs['season'])

        return Seasons(info['path'])

    try:
        vo = Common.GetVideoObject(info)
    except:
        return ContentNotFound()

    return ObjectContainer(objects=[vo], content=ContainerContent.Movies)


@route(Common.PREFIX + '/seasons')
def Seasons(path):

    data = ParsePage(path)
    if not data:
        return ContentNotFound()

    if len(data['seasons']) == 1:
        return Episodes(path, data['current_season'])

    oc = ObjectContainer(
        title2=data['title'],
        content=ContainerContent.Seasons,
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
            rating_key=Common.GetEpisodeURL(data['url'], season, 0),
            index=int(season),
            title=data['seasons'][season],
            source_title=L(Common.TITLE),
            thumb=data['thumb'],
            # summary=data['summary']
        ))

    return oc


@route(Common.PREFIX + '/episodes')
def Episodes(path, season):

    Log.Debug('Get episodes for %s' % path)

    data = ParsePage(path)
    if not data:
        return ContentNotFound()

    if data['session'] == 'external':
        oc = ObjectContainer(
            title2=u'%s' % data['title'],
            content=ContainerContent.Episodes
        )
        for episode in data['episodes']:
            Log.Debug('Try to get metadata from external: %s' % episode)
            try:
                oc.add(URLService.MetadataObjectForURL(
                    data['episodes'][episode]['url']
                ))
            except:
                continue
        return oc if len(oc) else ContentNotFound()

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
        oc.add(Common.GetVideoObject(data, episode))

    return oc


def Search(query):
    return SearchService.Query(
        query=query,
        identifier=Plugin.Identifier,
        name='HDSerials'
    )


@route(Common.HDSERIALS_META_ROUTE)
def GetMeta(path, episode):
    episode = int(episode)

    item = ParsePage(path)
    if episode and episode != item['current_episode']:
        item = UpdateItemInfo(item, item['current_season'], episode)

    return JSON.StringFromObject(item)


###############################################################################
# Common
###############################################################################

def ContentNotFound():
    return MessageContainer(
        L('Ошибка'),
        L('Контент не найден')
    )


def ParsePage(path):

    if Common.HDSERIALS_URL not in path:
        path = Common.HDSERIALS_URL+path

    if Data.Exists(Common.KEY_CACHE):
        ret = Data.LoadObject(Common.KEY_CACHE)
        if ret and 'path' in ret and ret['path'] == path:
            Log.Debug('Return from cache %s' % path)
            return ret

    page = Common.GetPage(path).xpath(
        '//div[@id="k2Container"]'
    )[0]

    data = {'variants': {}}
    try:
        for url in page.xpath(
            '//div[@class="itemFullText"]//iframe[@src]'
        ):
            Log.Debug('Found variant %s', url)
            variant = Common.GetInfoByURL(url.get('src'))
            if variant:
                data['variants'][variant['url']] = variant
                if 'session' not in data:
                    data.update(variant)
                    if 'seasons' in data:
                        data['seasons'] = variant['seasons'].copy()
                else:
                    if 'seasons' in variant:
                        data['seasons'].update(variant['seasons'])


        if len(data['variants']) == 0:
            return None
    except:
        return None

    ret = {
        'path': path,
        'rating': 0.00,
        'thumb': '%s%s' % (
            Common.HDSERIALS_URL,
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

    data['rating'] = float(Regex('width\s?:\s?([\d\.]+)').search(
        page.xpath(
            '//div[@class="itemRatingBlock"]//li[@class="itemCurrentRating"]'
        )[0].get('style')
    ).group(1)) / 10

    if 'year' in data:
        if '-' in data['year']:
            data['year'] = data['year'].split('-')[0]

        data['year'] = int(data['year'])

    for k in data['variants']:
        data['variants'][k]['variant_title'] = unicode(
            variants_names.pop(0)
        ) if variants_names else ''

    if data['session'] == 'external':
        if len(data['variants']) > 1:
            data['seasons'] = {'1': ret['title']}
            data['current_season'] = 1
            data['episodes'] = data['variants']

    ret.update(data)
    Data.SaveObject(Common.KEY_CACHE, ret)

    return ret


def UpdateItemInfo(item, season, episode):
    url = item['url']
    season = str(season)

    if season not in item['variants'][url]['seasons']:
        # Try to search variant with season
        for variant in item['variants'].values():
            if season in variant['seasons']:
                url = variant['url']
                if int(season) == variant['current_season'] and int(episode) == variant['current_episode']:
                    update = variant.copy()
                    del update['seasons']
                    item.update(update)
                    return item
                break

    update = Common.GetInfoByURL(Common.GetEpisodeURL(
        url,
        season,
        episode
    ), url)
    if not update:
        return None

    item['variants'][url].update(update.copy())

    del update['seasons']
    item.update(update)

    Data.SaveObject(Common.KEY_CACHE, item)

    return item


def PushToHistory(item):
    history = Data.LoadObject(Common.KEY_HISTORY)

    if not history:
        history = {}

    history[item['path']] = {
        'path': item['path'],
        'title': item['title'],
        'thumb': item['thumb'],
        'time': Datetime.TimestampFromDatetime(Datetime.Now()),
    }

    # Trim old items
    if len(history) > Common.HISTORY_SIZE:
        items = sorted(
            history.values(),
            key=lambda k: k['time'],
            reverse=True
        )[:Common.HISTORY_SIZE]
        history = {}
        for item in items:
            history[item['path']] = item

    Data.SaveObject(Common.KEY_HISTORY, history)
