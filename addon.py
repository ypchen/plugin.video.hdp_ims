# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin

import json
import base64

import urllib
import urllib2
import urlparse

import os
import os.path
import tempfile
import time

import re
import copy
import collections

# ----- Version Information -----
# Hard coded the quickfix gist hash corresponding to each addon version
version_gist_hash = {
    '1.18.1': '3312e9f0ee2e9268d849057364c7fa9f'
}
def my_version ():
    return xbmcaddon.Addon().getAddonInfo('version')

# ----- Utilities -----
def str_between (s, start, end):
    pos1 = s.find(start)
    if ((-1) == pos1):
        return ''
    pos1 += len(start)
    pos2 = s.find(end, pos1)
    if ((-1) == pos2):
        return s[pos1:]
    else:
        return s[pos1:pos2]

def get_link_contents (url, data_to_post=None, http_header=None, user_agent=None, url_redir=False):
    contents = ''
    if data_to_post is None:
        request = urllib2.Request(url)
    else:
        request = urllib2.Request(url, data_to_post)
    if user_agent is None:
        user_agent = 'Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.1 (KHTML, like Gecko) Ubuntu/11.04 Chromium/14.0.825.0 Chrome/14.0.825.0 Safari/535.1'
    request.add_header('User-Agent', user_agent)
    if http_header is not None:
        for key, val in http_header.iteritems():
            request.add_header(key, val)
    try:
        response = urllib2.urlopen(request)
        if (200 == response.getcode()):
            if (url_redir):
                # not sure why 200 (should be 302 here)
                url_redir = response.geturl()
            else:
                contents = response.read()
    finally:
        if (url_redir):
            return url_redir
        else:
            return contents

def show_notification (notify, exec_command):
    if ('true' == notify):
        xbmc.executebuiltin(exec_command)

def download_lastest_gist (gist_hash):
    try:
        commit_url = 'https://api.github.com/gists/' + gist_hash + '/commits'
        commit_info = urllib.urlopen(commit_url)
        if (200 != commit_info.getcode()):
            return '# INFO-CODE-' + commit_info.getcode() + ' download_lastest_gist() error'
        commit_latest = json.loads(commit_info.read())[0]
        gist_url = 'https://gist.githubusercontent.com/' + commit_latest['user']['login'] + '/' + gist_hash + '/raw/' + commit_latest['version']
        gist_commit = urllib.urlopen(gist_url)
        if (200 != gist_commit.getcode()):
            return '# TEXT-CODE-' + gist_commit.getcode() + ' download_lastest_gist() error'
        gist_text = gist_commit.read()
    except:
        gist_text = '# EXCEPT download_lastest_gist() error'
    return gist_text

def build_url_dict (params):
    return '{0}?{1}'.format(addon_url, urllib.urlencode(params))

def build_url_kvpairs (**kvpairs):
    return '{0}?{1}'.format(addon_url, urllib.urlencode(kvpairs))

def get_tempdir ():
    try:
        tempdir = tempfile.gettempdir()
    except:
        tempdir = xbmc.translatePath('special://temp')
    return tempdir

def get_installed_addon_list ():
    file_installed_addons = os.path.join(get_tempdir(), 'list_installed_addons')
    json_data = ''
    if os.path.isfile(file_installed_addons):
        with open(file_installed_addons, 'r') as f:
            json_data = f.read()
    if ('' == json_data):
        json_data = get_link_contents(
            'http://127.0.0.1:8080/jsonrpc', '{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params":{}, "id":1}', {
                'Content-Type': 'application/json'})
        if ('' == json_data):
            # Fake the json_data for some platforms, such as Android based systems
            json_data = '{"id":1,"jsonrpc":"2.0","result":{"addons":[{"addonid":"plugin.video.dailymotion_com","type":"xbmc.python.pluginsource"},{"addonid":"plugin.video.youtube","type":"xbmc.python.pluginsource"}],"limits":{"end":64,"start":0,"total":64}}}'
        with open(file_installed_addons, 'w') as f:
            f.write(json_data)
    return json.loads(json_data)

# ----- ims -----
sites = [
    {
        'title': '楓林網',
        'action': 'list_items',
        'callback': 'maplestage_top()',
        'isFolder': True
    },
    {
        'title': '劇迷 gimy.tv',
        'action': 'list_items',
        'callback': 'gimy_id()',
        'isFolder': True
    },
    {
        'title': '酷播 99KUBO',
        'action': 'list_items',
        'callback': 'kubo_id()',
        'isFolder': True
    },
    {
        'title': '全景中国 (即：众遥、不卡、网星)',
        'action': 'list_items',
        'callback': 'aibuka_level_1()',
        'isFolder': True
    }
]

hidden_sites = []

supported_providers = {
    'youtube': {
        'image_url': 'https://img.youtube.com/vi/{0}/hqdefault.jpg',
        'resolvers': [{
            'description': '以 plugin 處理',
            'plugin_url': 'plugin://plugin.video.youtube/play/?video_id={0}',
            'addonid': 'plugin.video.youtube'
        }]
    },
    'dailymotion': {
        'image_url': 'https://www.dailymotion.com/thumbnail/video/{0}',
        'resolvers': [{
            'description': '以 plugin 處理',
            'plugin_url': 'plugin://plugin.video.dailymotion_com/?mode=playVideo&url={0}',
            'addonid': 'plugin.video.dailymotion_com'
        }]
    }
}

def get_provider_info (provider, id):
    if provider in supported_providers:
        provider_info = copy.deepcopy(supported_providers[provider])
        provider_info['image_url'] = provider_info['image_url'].format(urllib.quote(id), addon_url)
        for resolver in provider_info['resolvers']:
            resolver['plugin_url'] = resolver['plugin_url'].format(urllib.quote(id), addon_url)
        return provider_info
    else:
        return {}

def input_password_to_show_hidden_sites (params):
    input_text = xbmcgui.Dialog().input('請輸入密碼', str(''), type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT)
    params['action'] = 'list_sites'
    params['show_hidden_sites'] = ((input_text) and (input_text == addon.getSetting('hs_pass')))
    list_sites(params)

def list_sites (params):
    for site in sites:
        li = xbmcgui.ListItem(site['title'])
        params['action'] = site['action']
        params['callback'] = site['callback']
        params['data'] = base64.b64encode(json.dumps(site).encode('utf-8'))
        url = build_url_dict(params)
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=site['isFolder'])
    if params['show_hidden_sites']:
        # Separator
        xbmcplugin.addDirectoryItem(handle=addon_handle, url='', listitem=xbmcgui.ListItem('----------'), isFolder=False)
        for site in hidden_sites:
            li = xbmcgui.ListItem(site['title'])
            params['action'] = site['action']
            params['callback'] = site['callback']
            params['data'] = base64.b64encode(json.dumps(site).encode('utf-8'))
            url = build_url_dict(params)
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=site['isFolder'])
    # Separator
    xbmcplugin.addDirectoryItem(handle=addon_handle, url='', listitem=xbmcgui.ListItem('=========='), isFolder=False)
    # Version
    if ((not params['show_hidden_sites']) and ('1' == addon.getSetting('hs_show'))):
        params['action'] = 'input_password_to_show_hidden_sites'
        url = build_url_dict(params)
        isFolder = True
    else:
        url = ''
        isFolder = False
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=xbmcgui.ListItem('[版本資訊] hdp_ims: ' + my_version()), isFolder=isFolder)
    # Separator
    xbmcplugin.addDirectoryItem(handle=addon_handle, url='', listitem=xbmcgui.ListItem('=========='), isFolder=False)
    xbmcplugin.endOfDirectory(addon_handle)

def getLeveledInfo(key, defaultValue, levels):
    for level in levels:
        if key in level:
            return level[key]
    return defaultValue

def list_items (params):
    exec 'items = ' + params['callback']
    for item in items:
        title = getLeveledInfo('title', '[untitled]', [item, params])
        params['title'] = title
        image = getLeveledInfo('image', '', [item, params])
        params['image'] = image
        li = xbmcgui.ListItem(title, thumbnailImage=image)
        if (('IsPlayable' in item) and ('True' == item['IsPlayable'])):
            li.setProperty('IsPlayable', 'True')
            li.setInfo(type='video', infoLabels=None)
            url = item['link']
        else:
            params['link'] = item['link']
            params['action'] = item['action']
            params['callback'] = item['callback']
            params['data'] = base64.b64encode(json.dumps(item).encode('utf-8'))
            url = build_url_dict(params)
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=item['isFolder'])
    xbmcplugin.endOfDirectory(addon_handle)

# ----- sites -----
# -- maplestage --
def inc(int_array, by = 1000):
    int_array[0] += by
    return (int_array[0])

def maplestage_api (data):
    endpoint = 'http://maplestage.com/v1/query'
    headers = {
        'Referer': 'http://maplestage.com/',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    return get_link_contents(endpoint, data, headers)

def maplestage_top ():
    # hard-coded top level menu items
    return [
        {
            'title': '台灣綜藝', 'link': '"type":"variety","region":"tw"', 'action': 'list_items',
                'callback': 'maplestage_years(params)', 'isFolder': True
        },
        {
            'title': '大陸綜藝', 'link': '"type":"variety","region":"cn"', 'action': 'list_items',
                'callback': 'maplestage_years(params)', 'isFolder': True
        },
        {
            'title': '韓國綜藝', 'link': '"type":"variety","region":"kr"', 'action': 'list_items',
                'callback': 'maplestage_years(params)', 'isFolder': True
        },
        {
            'title': '台灣戲劇', 'link': '"type":"drama","region":"tw"', 'action': 'list_items',
                'callback': 'maplestage_years(params)', 'isFolder': True
        },
        {
            'title': '大陸戲劇', 'link': '"type":"drama","region":"cn"', 'action': 'list_items',
                'callback': 'maplestage_years(params)', 'isFolder': True
        },
        {
            'title': '韓國戲劇', 'link': '"type":"drama","region":"kr"', 'action': 'list_items',
                'callback': 'maplestage_years(params)', 'isFolder': True
        },
        {
            'title': '日本戲劇', 'link': '"type":"drama","region":"jp"', 'action': 'list_items',
                'callback': 'maplestage_years(params)', 'isFolder': True
        },
        {
            'title': '其他戲劇', 'link': '"type":"drama","region":"ot"', 'action': 'list_items',
                'callback': 'maplestage_years(params)', 'isFolder': True
        }
    ]

def maplestage_years (params):
    results = json.loads(
        maplestage_api(
            '{"queries":[{"name":"shows","query":{"sort":"top","take":99999,' + params['link'] + '}}]}'))
    shows = results['shows']
    years = {}
    showTotal = 0
    for show in shows:
        if show['year'] in years:
            years[show['year']] += 1
        else:
            years[show['year']] = 1
        showTotal += 1
    sorted_years = collections.OrderedDict(sorted(years.items(), reverse=True))
    items = []
    link = params['link']
    title = '不限年份 [名稱排序] (' + str(showTotal) + ' 個項目)'
    items.append({'title': title, 'link': link, 'action': 'list_items', 'callback': 'maplestage_shows(params)', 'isFolder': True, 'order': 'name'})
    title = '不限年份 [更新排序] (' + str(showTotal) + ' 個項目)'
    items.append({'title': title, 'link': link, 'action': 'list_items', 'callback': 'maplestage_shows(params)', 'isFolder': True, 'order': 'update'})
    for year, count in sorted_years.iteritems():
        link = params['link'] + ',"year":' + str(year)
        title = str(year) + ' [名稱排序]  (' + str(count) + ' 個項目)'
        items.append({'title': title, 'link': link, 'action': 'list_items', 'callback': 'maplestage_shows(params)', 'isFolder': True, 'order': 'name'})
        title = str(year) + ' [更新排序]  (' + str(count) + ' 個項目)'
        items.append({'title': title, 'link': link, 'action': 'list_items', 'callback': 'maplestage_shows(params)', 'isFolder': True, 'order': 'update'})
    return items

def maplestage_show_cmp (x, y):
    if len(x['slug']) < len(y['slug']):
        return -1
    elif len(x['slug']) > len(y['slug']):
        return 1
    else:
        return cmp(x['slug'], y['slug'])

def maplestage_shows (params):
    results = json.loads(
        maplestage_api(
            '{"queries":[{"name":"shows","query":{"sort":"top","take":99999,' + params['link'] + '}}]}'))
    data = json.loads(base64.b64decode(params['data']))
    if data['order'] == 'name':
        shows = sorted(results['shows'], maplestage_show_cmp)
    else:
        shows = sorted(results['shows'], key=lambda x: x['updatedAt'], reverse=True)
    items = []
    for show in shows:
        if 'updatedAt' in show:
            title = show['name'] + ' (' + re.sub('T.+\.[0-9]+Z', '', show['updatedAt']) + ' 更新)'
        else:
            title = show['name']
        link = params['link'] + ',"slug":"' + show['slug'] + '"'
        image = show['cover']
        items.append({'title': title, 'link': link, 'image': image, 'action': 'list_items', 'callback': 'maplestage_episodes(params)', 'isFolder': True, 'slug': show['slug']})
    return items

def maplestage_episodes (params):
    data = json.loads(base64.b64decode(params['data']))
    results = json.loads(
        maplestage_api(
            '{"queries":[{"name":"episodes","query":{"sort":"top","take":100,' + params['link'] + '}}]}'))
    siteURLprefix = 'http://maplestage.com'
    items = []
    episodes = results['episodes']
    for episode in episodes:
        title = episode['title']
        link = siteURLprefix + episode['href']
        items.append({'title': title, 'link': link, 'action': 'list_items', 'callback': 'maplestage_sources(params)', 'isFolder': True, 'slug': data['slug']})
    return items

def maplestage_sources (params):
    data = json.loads(base64.b64decode(params['data']))
    html = get_link_contents(params['link'], http_header={'Referer': 'http://maplestage.com/show/' + data['slug']})
    if ('' == html):
        return []
    if ((-1) == html.find('var pageData = {')):
        return []
    results = json.loads('{' + str_between(html, 'var pageData = {', '};').strip() + '}')
    items = []
    sources = results['props'][2]['value']['videoSources']
    iSourceNo = 0;
    addon_list = get_installed_addon_list ()
    addons = addon_list['result']['addons']
    for source in sources:
        videoProvider = source['name'].lower()
        if videoProvider in supported_providers:
            provider_info = supported_providers[videoProvider]
            videos = source['videos']
            iSourceNo += 1;
            for resolver in provider_info['resolvers']:
                addon_found = map(lambda addon: 1 if addon['addonid'] == resolver['addonid'] else 0, addons)
                if 1 in addon_found:
                    if 1 == len(videos):
                        vid = videos[0]['id']
                        image = provider_info['image_url'].format(urllib.quote(vid), addon_url)
                        title = '來源 #{0}: {1} -- 共 {2} 段 [直接播放] [{3}]'.format(iSourceNo, source['name'], len(videos), resolver['description'])
                        link = resolver['plugin_url'].format(urllib.quote(vid), addon_url)
                        if ('' == image):
                            items.append({'title': title, 'link': link, 'vid': vid, 'isFolder': False, 'IsPlayable': 'True'})
                        else:
                            items.append({'title': title, 'link': link, 'vid': vid, 'image': image, 'isFolder': False, 'IsPlayable': 'True'})
                    else:
                        title = '來源 #{0}: {1} -- 共 {2} 段 [進入播放] [{3}]'.format(iSourceNo, source['name'], len(videos), resolver['description'])
                        link = json.dumps({'videos': videos, 'resolver': resolver, 'image_url': provider_info['image_url']}).encode('utf-8')
                        items.append({'title': title, 'link': link, 'action': 'list_items', 'callback': 'maplestage_videos(params)', 'isFolder': True})
        elif 'html' == videoProvider:
            videos = source['videos']
            iSourceNo += 1;
            if 1 == len(videos):
                vid = str_between(videos[0]['id'], '?ref=', '"').strip()
                # try alternatives
                if ('' == vid):
                    vid = str_between(videos[0]['id'], 'video=', '&').strip()
                if ('' == vid):
                    vid = str_between(videos[0]['id'], 'src="', '"').strip()
                # unquote twice
                vid = urllib.unquote(vid).decode('utf-8')
                vid = urllib.unquote(vid).decode('utf-8')
                image = results['props'][2]['value']['thumb']
                title = '來源 #{0}: {1} -- 共 {2} 段 [直接播放] [{3}]'.format(iSourceNo, source['name'], len(videos), vid)
                link = build_url_dict({'action': 'maplestage_html', 'link': vid})
                if ('' == image):
                    items.append({'title': title, 'link': link, 'vid': vid, 'isFolder': False, 'IsPlayable': 'True'})
                else:
                    items.append({'title': title, 'link': link, 'vid': vid, 'image': image, 'isFolder': False, 'IsPlayable': 'True'})
    return items

def maplestage_videos (params):
    data = json.loads(params['link'])
    videos = data['videos']
    resolver = data['resolver']
    items = []
    i = 0
    for video in videos:
        vid = videos[i]['id']
        image = data['image_url'].format(urllib.quote(vid), addon_url)
        i += 1
        title = '第 {0} 段'.format(i)
        link = resolver['plugin_url'].format(urllib.quote(vid), addon_url)
        if ('' == image):
            items.append({'title': title, 'link': link, 'vid': vid, 'isFolder': False, 'IsPlayable': 'True'})
        else:
            items.append({'title': title, 'link': link, 'vid': vid, 'image': image, 'isFolder': False, 'IsPlayable': 'True'})
    return items


def maplestage_html_verystream_check (link):
    return ((-1) != link.find('verystream.com'))

def maplestage_html_verystream_exec (ifcase, link):
    provider = 'verystream'
    xbmc.log('[%s, %d, %s] %s' % ('hdp_ims', ifcase[0], provider, 'link={' + link + '}'), xbmc.LOGNOTICE)
    if ((-1) == link.find('http:')) and ((-1) == link.find('https:')) and ((-1) != link.find('//')):
        # E.g., link={//verystream.com/e/GYSotz7JcJi}
        link = 'https:' + link
    html = get_link_contents(link)
    if ('' == html):
        return []
    link = 'https://verystream.com/gettoken/' + str_between(html, 'id="videolink">', '<') + '?mime=true'
    inc(ifcase, 1)
    xbmc.log('[%s, %d, %s] %s' % ('hdp_ims', ifcase[0], provider, 'playing: link={' + link + '}'), xbmc.LOGNOTICE)
    playitem = xbmcgui.ListItem(path=link)
    return playitem

def maplestage_html_player_check (link):
    return ((-1) == link.find('http:')) and ((-1) == link.find('https:')) and ((-1) != link.find('//')) and ((-1) != link.find('/player/'))

def maplestage_html_player_exec (ifcase, link):
    provider = 'player'
    xbmc.log('[%s, %d, %s] %s' % ('hdp_ims', ifcase[0], provider, 'link={' + link + '}'), xbmc.LOGNOTICE)
    # E.g., link={//p.tiktak.tv/player/a0d08faa956f6b71}
    link = 'https:' + link
    urlHost = str_between(link, '://', '/')
    urlPrefix = 'https://' + urlHost
    inc(ifcase, 1)
    xbmc.log('[%s, %d, %s] %s' % ('hdp_ims', ifcase[0], provider, 'link={' + link + '}'), xbmc.LOGNOTICE)
    html = get_link_contents(link)
    if ('' == html):
        return []
    link = re.sub(r".+\|([0-9a-z]{100,240})\|.+", "\g<1>", html)
    if ('' == link):
        return []
    link = urlPrefix + '/player?url=' + link
    inc(ifcase, 1)
    xbmc.log('[%s, %d, %s] %s' % ('hdp_ims', ifcase[0], provider, 'link={' + link + '}'), xbmc.LOGNOTICE)
    html = get_link_contents(link)
    if ('' == html):
        return []
    link = urlPrefix + str_between(html, 'source src="', '"')
    inc(ifcase, 1)
    xbmc.log('[%s, %d, %s] %s' % ('hdp_ims', ifcase[0], provider, 'playing: link={' + link + '}'), xbmc.LOGNOTICE)
    playitem = xbmcgui.ListItem(path=link)
    return playitem

def maplestage_html_rapidvideo_check (link):
    return ((-1) != link.find('rapidvideo'))

def maplestage_html_rapidvideo_exec (ifcase, link):
    provider = 'rapidvideo'
    xbmc.log('[%s, %d, %s] %s' % ('hdp_ims', ifcase[0], provider, 'link={' + link + '}'), xbmc.LOGNOTICE)
    if ((-1) != link.find('?')):
        connector = '&'
    else:
        connector = '?'
    resolutionAttempts = [connector+'q=720p', connector+'q=480p', '']
    for resAtt in resolutionAttempts:
        inc(ifcase, 1)
        xbmc.log('[%s, %d, %s] %s' % ('hdp_ims', ifcase[0], provider, 'resAtt={' + resAtt + '}'), xbmc.LOGNOTICE)
        html = get_link_contents(link + resAtt)
        if ('' == html):
            return []
        if ((-1) != html.find('source src="')):
            break
    # It may still fail after the listed attempts
    link = str_between(html, 'source src="', '"')
    inc(ifcase, 1)
    xbmc.log('[%s, %d, %s] %s' % ('hdp_ims', ifcase[0], provider, 'playing: link={' + link + '}'), xbmc.LOGNOTICE)
    playitem = xbmcgui.ListItem(path=link)
    return playitem

def maplestage_html_dmembed_check (link):
    return ((-1) != link.find('dailymotion.com/embed'))

def maplestage_html_dmembed_exec (ifcase, link):
    provider = 'dmembed'
    xbmc.log('[%s, %d, %s] %s' % ('hdp_ims', ifcase[0], provider, 'link={' + link + '}'), xbmc.LOGNOTICE)
    if ((-1) == link.find('http:')) and ((-1) == link.find('https:')) and ((-1) != link.find('//')):
        link = 'https:' + link
    html = get_link_contents(link)
    if ('' == html):
        return []
    htmlToExplode = str_between(html, ',"owner":', ',"reporting":')
    videos = htmlToExplode.split('}],')
    prefRes = ['"720"', '"1080"', '"480"', '"380"', '"240"']
    urlFound = False
    for res in prefRes:
        for video in videos:
            if ((-1) != video.find(res)):
                urlFound = True
                link = str_between(video, '"type":"video\/mp4","url":"', '"')
                link = link.replace('\/', '/')
                inc(ifcase, 1)
                xbmc.log('[%s, %d, %s] %s' % ('hdp_ims', ifcase[0], provider, 'link={' + link + '} @ ' + res), xbmc.LOGNOTICE)
                break
        if (True == urlFound):
            break
    inc(ifcase, 1)
    xbmc.log('[%s, %d, %s] %s' % ('hdp_ims', ifcase[0], provider, 'playing: link={' + link + '}'), xbmc.LOGNOTICE)
    playitem = xbmcgui.ListItem(path=link)
    return playitem

def maplestage_html_ddppnew_check (link):
    return ((-1) != link.find('ddppnew'))

def maplestage_html_ddppnew_exec (ifcase, link):
    provider = 'ddppnew'
    xbmc.log('[%s, %d, %s] %s' % ('hdp_ims', ifcase[0], provider, 'link={' + link + '}'), xbmc.LOGNOTICE)
    html = get_link_contents(link)
    if ('' == html):
        return []
    redirecturl = str_between(html, 'var redirecturl = "', '"')
    main = str_between(html, 'var main = "', '"')
    link = redirecturl + main
    inc(ifcase, 1)
    xbmc.log('[%s, %d, %s] %s' % ('hdp_ims', ifcase[0], provider, 'playing: link={' + link + '}'), xbmc.LOGNOTICE)
    playitem = xbmcgui.ListItem(path=link)
    return playitem

def maplestage_html_share_Nom3u8_check (link):
    return ((-1) != link.find('/share/')) and ((-1) == link.find('.m3u8'))

def maplestage_html_share_Nom3u8_exec (ifcase, link):
    provider = '+share-.m3u8'
    xbmc.log('[%s, %d, %s] %s' % ('hdp_ims', ifcase[0], provider, 'link={' + link + '}'), xbmc.LOGNOTICE)
    html = get_link_contents(link)
    if ('' == html):
        return []
    parsed = urlparse.urlparse(link)
    replaced = parsed._replace(path=str_between(html, 'var main = "', '"').strip())
    link = replaced.geturl()
    inc(ifcase, 1)
    xbmc.log('[%s, %d, %s] %s' % ('hdp_ims', ifcase[0], provider, 'playing: link={' + link + '}'), xbmc.LOGNOTICE)
    playitem = xbmcgui.ListItem(path=link)
    playitem.setProperty('inputstreamaddon','inputstream.adaptive')
    playitem.setProperty('inputstream.adaptive.manifest_type','hls')
    playitem.setMimeType('application/vnd.apple.mpegurl')
    playitem.setContentLookup(False)
    return playitem

def maplestage_html_1drama_check (link):
    return ((-1) == link.find('//')) and ((-1) == link.find('.'))

def maplestage_html_1drama_exec (ifcase, link):
    provider = '1drama'
    xbmc.log('[%s, %d, %s] %s' % ('hdp_ims', ifcase[0], provider, 'link={' + link + '}'), xbmc.LOGNOTICE)
    # E.g., link={QTBBS1Q5RktNMUlsYUJkdTh6VWJLT2NBLXlvZ3JPbEdkNlBGUG42YXRIM1lfTVBTUkZ5UF9TNW52eTZRMDljal9LemFmUUVkb3FVdlJsOFRPOFdfYm5uc3FYNERzQzNwTnh2RGdPSklzSXlOekdUbFlxanpnSEVwaEEwamFXd24}
    html = get_link_contents('http://1drama.com/m3u8/?ref=' + link, http_header={'Referer': 'http://maplestage.com/episode/'})
    if ('' == html):
        return []
    link = str_between(str_between(html, 'var m3u8url =', 'var dp'), " '", "'")
    inc(ifcase, 1)
    xbmc.log('[%s, %d, %s] %s' % ('hdp_ims', ifcase[0], provider, 'playing: link={' + link + '}'), xbmc.LOGNOTICE)
    playitem = xbmcgui.ListItem(path=link)
    playitem.setProperty('inputstreamaddon','inputstream.adaptive')
    playitem.setProperty('inputstream.adaptive.manifest_type','hls')
    playitem.setMimeType('application/vnd.apple.mpegurl')
    playitem.setContentLookup(False)
    return playitem

def maplestage_html_default_check (link):
    return True

def maplestage_html_default_exec (ifcase, link):
    provider = 'default'
    xbmc.log('[%s, %d, %s] %s' % ('hdp_ims', ifcase[0], provider, 'playing: link={' + link + '}'), xbmc.LOGNOTICE)
    playitem = xbmcgui.ListItem(path=link)
    playitem.setProperty('inputstreamaddon','inputstream.adaptive')
    playitem.setProperty('inputstream.adaptive.manifest_type','hls')
    playitem.setMimeType('application/vnd.apple.mpegurl')
    playitem.setContentLookup(False)
    return playitem

html_providers = [
    {
        'check': maplestage_html_verystream_check,
        'exec':  maplestage_html_verystream_exec
    },
    {
        'check': maplestage_html_player_check,
        'exec':  maplestage_html_player_exec
    },
    {
        'check': maplestage_html_rapidvideo_check,
        'exec':  maplestage_html_rapidvideo_exec
    },
    {
        'check': maplestage_html_dmembed_check,
        'exec':  maplestage_html_dmembed_exec
    },
    {
        'check': maplestage_html_ddppnew_check,
        'exec':  maplestage_html_ddppnew_exec
    },
    {
        'check': maplestage_html_share_Nom3u8_check,
        'exec':  maplestage_html_share_Nom3u8_exec
    },
    {
        'check': maplestage_html_1drama_check,
        'exec':  maplestage_html_1drama_exec
    },
    {
        'check': maplestage_html_default_check,
        'exec':  maplestage_html_default_exec
    }
]

def maplestage_html (params):
    ifcase = [0]
    playitem = None
    link = params['link']
    if ((-1) != link.find('url=')):
        # Mark the 'url=' process
        inc(ifcase, 30000)
        link = str_between(link, 'url=', "<>")
    xbmc.log('[%s, %d] %s' % ('hdp_ims', ifcase[0], 'html: link={' + link + '}'), xbmc.LOGNOTICE)
    for html_provider in html_providers:
        if (0 < inc(ifcase)) and html_provider['check'](link):
            playitem = html_provider['exec'](ifcase, link)
            break
    xbmcplugin.setResolvedUrl(addon_handle, True, playitem)
# -- maplestage --

# -- gimy --
def gimy_id ():
    # hard-coded top level menu items
    # link is the -id-- in the search criteria
    return [
        {
            'title': '戲劇', 'link': 'https://v.gimy.tv/list/drama-----addtime.html', 'action': 'list_items',
                'callback': 'gimy_drama_category(params)', 'isFolder': True
        },
        {
            'title': '電影', 'link': 'https://v.gimy.tv/list/movies-----addtime.html', 'action': 'list_items',
                'callback': 'gimy_movie_category(params)', 'isFolder': True
        },
        {
            'title': '動漫', 'link': 'https://v.gimy.tv/list/anime-----addtime.html', 'action': 'list_items',
                'callback': 'gimy_area2(params)', 'isFolder': True
        },
        {
            'title': '綜藝', 'link': 'https://v.gimy.tv/list/tvshow-----addtime.html', 'action': 'list_items',
                'callback': 'gimy_area2(params)', 'isFolder': True
        }
    ]

gimy_filter_URL_prefix = 'http://v.gimy.tv'
gimy_filter_insert_all = '全部'
gimy_filter_insert_at = '2018'
gimy_filter_insert_this = '2019'
gimy_filter_insert_pre = '-'
gimy_filter_insert_post = '-'
gimy_filter_str1 = '</ul>'
gimy_filter_str2 = '<a '
gimy_filter_str3 = '>'
gimy_filter_str4 = '</a'
gimy_filter_str5 = 'href="'
gimy_filter_str6 = '"'
def gimy_filter (params, url, explodeStart, nextCallback):
    html = get_link_contents(url)
    if ('' == html):
        return []
    htmlToExplode = str_between(html, explodeStart, gimy_filter_str1)
    videos = htmlToExplode.split(gimy_filter_str2)
    videos.pop(0)
    siteURLprefix = gimy_filter_URL_prefix
    items = []
    prevTitle = ''
    for video in videos:
        title = str_between(video, gimy_filter_str3, gimy_filter_str4).strip()
        # order asc
        if ((prevTitle == gimy_filter_insert_at) and (title == gimy_filter_insert_all)):
            items.append({'title': gimy_filter_insert_this, 'link': link.replace(gimy_filter_insert_pre + gimy_filter_insert_at + gimy_filter_insert_post, gimy_filter_insert_pre + gimy_filter_insert_this + gimy_filter_insert_post), 'action': 'list_items', 'callback': nextCallback, 'isFolder': True})
        link = siteURLprefix + str_between(video, gimy_filter_str5, gimy_filter_str6).strip()
        # order desc
        if ((prevTitle == gimy_filter_insert_all) and (title == gimy_filter_insert_at)):
            items.append({'title': gimy_filter_insert_this, 'link': link.replace(gimy_filter_insert_pre + gimy_filter_insert_at + gimy_filter_insert_post, gimy_filter_insert_pre + gimy_filter_insert_this + gimy_filter_insert_post), 'action': 'list_items', 'callback': nextCallback, 'isFolder': True})
        items.append({'title': title, 'link': link, 'action': 'list_items', 'callback': nextCallback, 'isFolder': True})
        prevTitle = title
    return items

def gimy_year (params):
    return gimy_filter (params, params['link'], '<span class="text-muted">按年份', 'gimy_videos(params)')

def gimy_area (params):
    return gimy_filter (params, params['link'], '<span class="text-muted">按地區', 'gimy_year(params)')

def gimy_area2 (params):
    return gimy_filter (params, params['link'], '<span class="text-muted">選擇地區', 'gimy_year(params)')

def gimy_drama_category (params):
    return gimy_filter (params, params['link'], '<span class="text-muted">按分類', 'gimy_year(params)')

def gimy_movie_category (params):
    return gimy_filter (params, params['link'], '<span class="text-muted">按分類', 'gimy_area(params)')

gimy_videos_str1 = '<div class="box-page'
gimy_videos_str2 = 'iv>'
gimy_videos_str3 = '<ul>'
gimy_videos_str4 = '</d'
gimy_videos_str5 = 'active"><span>'
gimy_videos_str6 = '</span>'
gimy_videos_str7 = '下一頁</a>'
gimy_videos_str8 = '</ul>'
gimy_videos_str9 = 'pagegbk" data="p-'
gimy_videos_strA = '">尾頁</a>'
gimy_videos_strB = '<div class="box-video-list">'
gimy_videos_strC = '<div class="box-page'
gimy_videos_strD = '<li '
gimy_videos_strE = 'http://v.gimy.tv'
gimy_videos_strF = '</li>'
gimy_videos_strG = '上一頁'
gimy_videos_strH = '">'
gimy_videos_strI = '</a'
gimy_videos_strJ = 'href="'
gimy_videos_strK = '"'
gimy_videos_strL = 'title="'
gimy_videos_strM = '"'
gimy_videos_strN = 'href="'
gimy_videos_strO = '"'
gimy_videos_strP = 'data-original="'
gimy_videos_strQ = '"'
gimy_videos_strR = 'note text-bg-r">'
gimy_videos_strS = '</span>'
gimy_videos_strT = '下一頁'
gimy_videos_strU = '">'
gimy_videos_strV = '</a'
gimy_videos_strW = 'href="'
gimy_videos_strX = '"'
def gimy_videos (params):
    data = json.loads(base64.b64decode(params['data']), 'utf-8')
    try:
        page = int(data['page'])
    except:
        page = 1
    html = get_link_contents(params['link'])
    if ('' == html):
        return []
    pageHtml = str_between(str_between(html, gimy_videos_str1, gimy_videos_str2), gimy_videos_str3, gimy_videos_str4)
    pages = []
    pages.append(str_between(pageHtml, gimy_videos_str5, gimy_videos_str6))
    pages.append(str_between(str_between(pageHtml, gimy_videos_str7, gimy_videos_str8), gimy_videos_str9, gimy_videos_strA))
    if ('' == pages[1]):
        pages[1] = str(page)
    htmlToExplode = str_between(html, gimy_videos_strB, gimy_videos_strC)
    videos = htmlToExplode.split(gimy_videos_strD)
    videos.pop(0)
    siteURLprefix = gimy_videos_strE
    items = []
    items.append({'title': '第 [COLOR limegreen]' + pages[0] + '[/COLOR] 頁/共 [COLOR limegreen]' + pages[1] + '[/COLOR] 頁', 'link': '', 'action': '', 'callback': '', 'isFolder': False})
    pageBlocks = pageHtml.split(gimy_videos_strF)
    if (page > 1):
        for pageBlock in pageBlocks:
            if (gimy_videos_strG == str_between(pageBlock, gimy_videos_strH, gimy_videos_strI).strip()):
                link = siteURLprefix + str_between(pageBlock, gimy_videos_strJ, gimy_videos_strK).strip()
                items.append({'title': '上一頁 (回第' + str(page-1) + '頁)', 'link': link, 'action': 'list_items', 'callback': 'gimy_videos(params)', 'isFolder': True, 'page': (page-1)})
                break
    for video in videos:
        title = str_between(video, gimy_videos_strL, gimy_videos_strM).strip()
        if ('' != title):
            link = siteURLprefix + str_between(video, gimy_videos_strN, gimy_videos_strO).strip()
            image = str_between(video, gimy_videos_strP, gimy_videos_strQ).strip()
            note = str_between(video, gimy_videos_strR, gimy_videos_strS).strip()
            items.append({'title': title + ' -- ' + note, 'link': link, 'action': 'list_items', 'callback': 'gimy_sources(params)', 'isFolder': True, 'image': image})
    if (int(page) < int(pages[1])):
        for pageBlock in pageBlocks:
            if (gimy_videos_strT == str_between(pageBlock, gimy_videos_strU, gimy_videos_strV).strip()):
                link = siteURLprefix + str_between(pageBlock, gimy_videos_strW, gimy_videos_strX).strip()
                items.append({'title': '下一頁 (到第' + str(page+1) + '頁)', 'link': link, 'action': 'list_items', 'callback': 'gimy_videos(params)', 'isFolder': True, 'page': (page+1)})
                break
    return items

def gimy_sources (params):
    html = get_link_contents(params['link'])
    if ('' == html):
        return []
    htmlToExplode = str_between(html, '<div class="details-play-title">', '</div>')
    videos = htmlToExplode.split('class="gico')
    videos.pop(0)
    items = []
    items.append({'title': '選擇來源：', 'link': '', 'action': '', 'callback': '', 'isFolder': False})
    for video in videos:
        title = str_between(video, '">', '</a>').strip()
        playlist_id = str_between(video, 'href="#', '"').strip()
        items.append({'title': title, 'link': params['link'], 'action': 'list_items', 'callback': 'gimy_episodes(params)', 'isFolder': True, 'playlist_id': playlist_id, 'html': str_between(html, '<div class="playlist">', '<div class="layout-box clearfix"')})
    return items

def gimy_episodes (params):
    data = json.loads(base64.b64decode(params['data']), 'utf-8')
    try:
        playlist_id = data['playlist_id']
    except:
        playlist_id = 'con_playlist_1'
    html = data['html']
    htmlToExplode = str_between(html, 'id="' + playlist_id + '"', '</ul>')
    videos = htmlToExplode.split('<li>')
    videos.pop(0)
    siteURLprefix = 'http://v.gimy.tv'
    items = []
    for video in videos:
        title = str_between(video, '">', '<').strip()
        link = siteURLprefix + str_between(video, 'href="', '"').strip()
        link = build_url_dict({'action': 'gimy_episode', 'link': link})
        items.append({'title': title, 'link': link, 'isFolder': False, 'IsPlayable': 'True'})
    return items

def gimy_episode (params):
    html = get_link_contents(params['link'])
    if ('' == html):
        return []
    htmlToExplode = str_between(html, '_player = ', '</script>')
    link = str_between(htmlToExplode, '"url":"', '"').replace('\\/', '/')
    playitem = xbmcgui.ListItem(path=link)
    playitem.setProperty('inputstreamaddon','inputstream.adaptive')
    playitem.setProperty('inputstream.adaptive.manifest_type','hls')
    playitem.setMimeType('application/vnd.apple.mpegurl')
    playitem.setContentLookup(False)
    xbmcplugin.setResolvedUrl(addon_handle, True, playitem)
# -- gimy --

# -- kubo --
def kubo_id ():
    # hard-coded top level menu items
    # link is the -id-- in the search criteria
    return [
        {
            'title': '電視劇', 'link': 'http://www.99kubo.tv/vod-search-id-2-cid--area--tag--year--wd--actor--order-vod_addtime%20desc.html', 'action': 'list_items',
                'callback': 'kubo_cid_skip_area(params)', 'isFolder': True
        },
        {
            'title': '電影', 'link': 'http://www.99kubo.tv/vod-search-id-1-cid--area--tag--year--wd--actor--order-vod_addtime%20desc.html', 'action': 'list_items',
                'callback': 'kubo_cid(params)', 'isFolder': True
        },
        {
            'title': '動漫', 'link': 'http://www.99kubo.tv/vod-search-id-3-cid--area--tag--year--wd--actor--order-vod_addtime%20desc.html', 'action': 'list_items',
                'callback': 'kubo_area(params)', 'isFolder': True
        },
        {
            'title': '電視秀', 'link': 'http://www.99kubo.tv/vod-search-id-41-cid--area--tag--year--wd--actor--order-vod_addtime%20desc.html', 'action': 'list_items',
                'callback': 'kubo_cid(params)', 'isFolder': True
        },
        {
            'title': '紀錄片', 'link': 'http://www.99kubo.tv/vod-search-id-27-cid--area--tag--year--wd--actor--order-vod_addtime%20desc.html', 'action': 'list_items',
                'callback': 'kubo_area(params)', 'isFolder': True
        },
        {
            'title': '體育', 'link': 'http://www.99kubo.tv/vod-search-id-5-cid--area--tag--year--wd--actor--order-vod_addtime%20desc.html', 'action': 'list_items',
                'callback': 'kubo_cid(params)', 'isFolder': True
        },
        {
            'title': '教育', 'link': 'http://www.99kubo.tv/vod-search-id-49-cid--area--tag--year--wd--actor--order-vod_addtime%20desc.html', 'action': 'list_items',
                'callback': 'kubo_cid(params)', 'isFolder': True
        },
        {
            'title': '其他', 'link': 'http://www.99kubo.tv/vod-search-id-20-cid--area--tag--year--wd--actor--order-vod_addtime%20desc.html', 'action': 'list_items',
                'callback': 'kubo_cid(params)', 'isFolder': True
        }
    ]

kubo_filter_URL_prefix = 'http://www.99kubo.tv'
kubo_filter_insert_all = '全部'
kubo_filter_insert_at = '2018'
kubo_filter_insert_this = '2019'
kubo_filter_insert_pre = '-year-'
kubo_filter_insert_post = '-'
kubo_filter_str1 = '</dl>'
kubo_filter_str2 = '<a '
kubo_filter_str3 = '>'
kubo_filter_str4 = '</a'
kubo_filter_str5 = 'href="'
kubo_filter_str6 = '"'
def kubo_filter (params, url, explodeStart, nextCallback):
    html = get_link_contents(url)
    if ('' == html):
        return []
    htmlToExplode = str_between(html, explodeStart, kubo_filter_str1)
    videos = htmlToExplode.split(kubo_filter_str2)
    videos.pop(0)
    siteURLprefix = kubo_filter_URL_prefix
    items = []
    prevTitle = ''
    for video in videos:
        title = str_between(video, kubo_filter_str3, kubo_filter_str4).strip()
        # order asc
        if ((prevTitle == kubo_filter_insert_at) and (title == kubo_filter_insert_all)):
            items.append({'title': kubo_filter_insert_this, 'link': link.replace(kubo_filter_insert_pre + kubo_filter_insert_at + kubo_filter_insert_post, kubo_filter_insert_pre + kubo_filter_insert_this + kubo_filter_insert_post), 'action': 'list_items', 'callback': nextCallback, 'isFolder': True})
        link = siteURLprefix + str_between(video, kubo_filter_str5, kubo_filter_str6).strip()
        # order desc
        if ((prevTitle == kubo_filter_insert_all) and (title == kubo_filter_insert_at)):
            items.append({'title': kubo_filter_insert_this, 'link': link.replace(kubo_filter_insert_pre + kubo_filter_insert_at + kubo_filter_insert_post, kubo_filter_insert_pre + kubo_filter_insert_this + kubo_filter_insert_post), 'action': 'list_items', 'callback': nextCallback, 'isFolder': True})
        items.append({'title': title, 'link': link, 'action': 'list_items', 'callback': nextCallback, 'isFolder': True})
        prevTitle = title
    return items

def kubo_cid (params):
    return kubo_filter (params, params['link'], '<dt>子分類', 'kubo_area(params)')

def kubo_cid_skip_area (params):
    return kubo_filter (params, params['link'], '<dt>子分類', 'kubo_year(params)')

def kubo_area (params):
    return kubo_filter (params, params['link'], '<dt>地區', 'kubo_year(params)')

def kubo_year (params):
    return kubo_filter (params, params['link'], '<dt>年份', 'kubo_videos(params)')

kubo_order_description = {
    'vod_addtime': '更新時間',
    'vod_hits_day': '本日人氣',
    'vod_hits_week': '本週人氣',
    'vod_hits_month': '本月人氣',
    'vod_hits': '總人氣',
    'vod_gold': '得分',
    'vod_golder': '評分人數',
    'vod_up': '按讚數'
}

def kubo_order (params):
    items = []
    order = str_between(params['link'], '-order-', ' ').strip()
    for kod in kubo_order_description:
        title = '依' + kubo_order_description[kod] + '排序'
        link = params['link'].replace(order, kod)
        items.append({'title': title, 'link': link, 'action': 'list_items', 'callback': 'kubo_videos(params)', 'isFolder': True})
    return items

def kubo_videos (params):
    data = json.loads(base64.b64decode(params['data']), 'utf-8')
    try:
        page = int(data['page'])
    except:
        page = 1
    order = str_between(params['link'], '-order-', ' ').strip()
    html = get_link_contents(params['link'].replace('.html', '-p-' + str(page) + '.html' ))
    if ('' == html):
        return []
    pageInfo = str_between(html, '當前:', '頁')
    pages = pageInfo.split('/')
    htmlToExplode = str_between(html, '<div class="listlf">', '<div class="footer">')
    videos = htmlToExplode.split('<li>')
    videos.pop(0)
    siteURLprefix = 'http://www.99kubo.tv'
    items = []
    items.append({'title': '第 [COLOR limegreen]' + pages[0] + '[/COLOR] 頁/共 [COLOR limegreen]' + pages[1] + '[/COLOR] 頁    目前排序方式：[COLOR limegreen]' + kubo_order_description[order] + '[/COLOR] (可按此處變更)', 'link': params['link'], 'action': 'list_items', 'callback': 'kubo_order(params)', 'isFolder': True})
    if (page > 1):
        items.append({'title': '上一頁 (回第' + str(page-1) + '頁)', 'link': params['link'], 'action': 'list_items', 'callback': 'kubo_videos(params)', 'isFolder': True, 'page': (page-1)})
    for video in videos:
        title = str_between(video, 'title="', '"').strip()
        link = siteURLprefix + str_between(video, 'href="', '"').strip()
        image = str_between(video, 'data-original="', '"').strip()
        updateAt = str_between(video, '<p>更新：', '</p>').strip()
        score = str_between(video, '<p>得分：', '</p>').strip()
        items.append({'title': '[COLOR goldenrod]' + score + '[/COLOR] ' + title + ' (' + updateAt + ' 更新)', 'link': link, 'action': 'list_items', 'callback': 'kubo_episodes(params)', 'isFolder': True, 'image': image})
    if ((-1) != html.find('>下一页&gt;</a>')):
        items.append({'title': '下一頁 (到第' + str(page+1) + '頁)', 'link': params['link'], 'action': 'list_items', 'callback': 'kubo_videos(params)', 'isFolder': True, 'page': (page+1)})
    return items

kubo_episodes_URL_prefix = 'http://www.99kubo.tv'
kubo_episodes_str1 = '<div class="hideCont"'
kubo_episodes_str2 = '</ul>'
kubo_episodes_str3 = '<li>'
kubo_episodes_str4 = '">'
kubo_episodes_str5 = '</a>'
kubo_episodes_str6 = 'href="'
kubo_episodes_str7 = '"'
def kubo_episodes (params):
    html = get_link_contents(params['link'])
    if ('' == html):
        return []
    htmlToExplode = str_between(html, kubo_episodes_str1, kubo_episodes_str2)
    videos = htmlToExplode.split(kubo_episodes_str3)
    videos.pop(0)
    items = []
    for video in videos:
        title = str_between(video, kubo_episodes_str4, kubo_episodes_str5).strip()
        link = kubo_episodes_URL_prefix + str_between(video, kubo_episodes_str6, kubo_episodes_str7).strip()
        link = build_url_dict({'action': 'kubo_episode', 'link': link})
        items.append({'title': title, 'link': link, 'isFolder': False, 'IsPlayable': 'True'})
    return items

kubo_episode_str1 = 'ff_urls='
kubo_episode_str2 = '"Data'
kubo_episode_str3 = 'https'
kubo_episode_str4 = '.m3u8'
def kubo_episode (params):
    name = 'kubo_episode()'
    link = params['link']
    html = get_link_contents(link)
    xbmc.log('[%s] %s' % (name, 'input: link={' + link + '}'), xbmc.LOGNOTICE)
    if ('' == html):
        return []
    htmlToExplode = str_between(html, kubo_episode_str1, kubo_episode_str2)
    link = kubo_episode_str3 + str_between(htmlToExplode, kubo_episode_str3, kubo_episode_str4).strip() + kubo_episode_str4
    link = link.replace('\/', '/')
    playitem = xbmcgui.ListItem(path=link)
    xbmc.log('[%s] %s' % (name, 'playing: link={' + link + '}'), xbmc.LOGNOTICE)
    playitem = xbmcgui.ListItem(path=link)
    playitem.setProperty('inputstreamaddon','inputstream.adaptive')
    playitem.setProperty('inputstream.adaptive.manifest_type','hls')
    playitem.setMimeType('application/vnd.apple.mpegurl')
    playitem.setContentLookup(False)
    xbmcplugin.setResolvedUrl(addon_handle, True, playitem)
# -- kubo --

# -- aibuka --
def aibuka_level_1 ():
    html = get_link_contents('http://v.p2premote.com/')
    if ('' == html):
        return []
    htmlToExplode = str_between(html, '<ul class="nav"', '</ul>')
    videos = htmlToExplode.split('<li ')
    videos.pop(0)
    siteURLprefix = 'http://v.p2premote.com'
    items = []
    for video in videos:
        if ((-1) != video.find('class="dropdown"')):
            continue
        if ((-1) != video.find('role="presentation"')):
            continue
        title = str_between(video, '">', '</a>').strip()
        link = siteURLprefix + str_between(video, 'href="', '"').strip()
        items.append({'title': title, 'link': link, 'action': 'list_items', 'callback': 'aibuka_level_2(params)', 'isFolder': True})
    return items

def aibuka_level_2 (params):
    html = get_link_contents(params['link'])
    if ('' == html):
        return []
    videos = html.split('<div class="panel-heading"')
    videos.pop(0)
    siteURLprefix = 'http://v.p2premote.com'
    items = []
    for video in videos:
        title = str_between(video, '">', '</a>').strip()
        link = siteURLprefix + str_between(video, 'href="', '"').strip()
        items.append({'title': title, 'link': link, 'action': 'list_items', 'callback': 'aibuka_level_3(params)', 'isFolder': True, 'page': 1})
    return items

def aibuka_level_3 (params):
    data = json.loads(base64.b64decode(params['data']), 'utf-8')
    page = data['page']
    html = get_link_contents(params['link'] + '?page=' + str(page))
    if ('' == html):
        return []
    videos = html.split('<li class="grid-item col-xs-6 col-md-2 " ')
    videos.pop(0)
    siteURLprefix = 'http://v.p2premote.com'
    items = []
    if (page > 1):
        items.append({'title': '上一頁 (回第' + str(page-1) + '頁)', 'link': params['link'], 'action': 'list_items', 'callback': 'aibuka_level_3(params)', 'isFolder': True, 'page': (page-1)})
    for video in videos:
        year = ''
        if ((-1) != video.find('<i>(')):
            year = str_between(video, '<i>(', ')</i>').strip()
            if unicode(year, 'utf-8').isnumeric():
                year = '(' + year + ') '
            else:
                year = ''
        title = year + str_between(str_between(video, '<div class="name">', '</div>'), '">', '<').strip()
        link = siteURLprefix + str_between(video, ' href="', '"').strip()
        image = str_between(video, ' src="', '"').strip()
        items.append({'title': title, 'link': link, 'action': 'list_items', 'callback': 'aibuka_level_4(params)', 'isFolder': True, 'image': image})
    if ((-1) != html.find('>下一页 &raquo;</a>')):
        items.append({'title': '下一頁 (到第' + str(page+1) + '頁)', 'link': params['link'], 'action': 'list_items', 'callback': 'aibuka_level_3(params)', 'isFolder': True, 'page': (page+1)})
    return items

def aibuka_level_4 (params):
    # Get the play list for videos
    html = get_link_contents(params['link'])
    if ('' == html):
        return []
    # YouTube or Dailymotion (rare in aibuka)
    if ((-1) != html.find('dm_progress_')):
        videoProvider = 'dailymotion'
    else:
        videoProvider = 'youtube'
    playList = str_between(html, 'var playlist = [[', '];').strip()
    videos = playList.split('], [')
    items = []
    for video in videos:
        video_detail = video.split(', ')
        title = str_between(video_detail[0], '"', '"').strip()
        vid = str_between(video_detail[1], '"', '"').strip()
        provider_info = get_provider_info(videoProvider, vid)
        image = provider_info['image_url']
        # Use the first resolver
        link = provider_info['resolvers'][0]['plugin_url']
        if ('' == image):
            items.append({'title': title, 'link': link, 'vid': vid, 'isFolder': False, 'IsPlayable': 'True'})
        else:
            items.append({'title': title, 'link': link, 'vid': vid, 'image': image, 'isFolder': False, 'IsPlayable': 'True'})
    return items
# -- aibuka --

# ----- ENTRY POINT -----
entry_point = 'list_sites({"action": "list_sites", "show_hidden_sites": True}) if (addon.getSetting("hs_show") == "2") else list_sites({"action": "list_sites", "show_hidden_sites": False})'

def router (params):
    if params:
        # Called recursively by itself
        exec params['action'] + '(params)'
    else:
        # Called by Kodi UI
        # Start from here by executing entry_point
        exec entry_point

# ----- BEGIN -----
addon = xbmcaddon.Addon()
addon_url = sys.argv[0]
addon_handle = int(sys.argv[1])
addon_params = dict(urlparse.parse_qsl(sys.argv[2][1:]))
# Quickfix with gist
if ('true' == addon.getSetting('gist_quickfix')):
    gist_notify = addon.getSetting('gist_notify')
    if addon_params:
        # Called recursively by itself
        # Get the quickfix -- no error checking at this stage
        gist_temp = os.path.join(get_tempdir(), addon.getSetting('gist_hash'))
        if os.path.isfile(gist_temp):
            show_notification(gist_notify, 'Notification(%s, %s, %d)' % ('Quickfix with gist', 'Use local copy of quickfix', 1000))
            with open(gist_temp, 'r') as f:
                gist_text = f.read()
            exec gist_text
            show_notification(gist_notify, 'Notification(%s, %s, %d)' % ('Quickfix with gist', 'Done', 1000))
        else:
            show_notification(gist_notify, 'Notification(%s, %s, %d)' % ('Quickfix with gist', 'Local copy NOT FOUND', 1000))
    else:
        # Called by Kodi UI
        # Get the quickfix -- download from the internet if necessary
        my_version_gist_hash = version_gist_hash[my_version()]
        gist_hash = addon.getSetting('gist_hash')
        if ('' == gist_hash):
            gist_hash = my_version_gist_hash
            addon.setSetting('gist_hash', gist_hash)
        gist_temp = os.path.join(get_tempdir(), gist_hash)
        gist_text = ''
        if os.path.isfile(gist_temp):
            gist_temp_age = (time.time() - os.stat(gist_temp).st_mtime)
            if (float(addon.getSetting('gist_valid_duration')) > gist_temp_age):
                show_notification(gist_notify, 'Notification(%s, %s, %d)' % ('Quickfix with gist', 'Use local copy of quickfix', 1000))
                with open(gist_temp, 'r') as f:
                    gist_text = f.read()
                if ((-1) == gist_text.find(my_version_gist_hash)):
                    show_notification(gist_notify, 'Notification(%s, %s, %d)' % ('Quickfix with gist', 'Local copy is INVALID', 1000))
                    gist_hash = my_version_gist_hash
                    addon.setSetting('gist_hash', gist_hash)
                    gist_temp = os.path.join(get_tempdir(), gist_hash)
                    gist_text = ''
            else:
                show_notification(gist_notify, 'Notification(%s, %s, %d)' % ('Quickfix with gist', 'Local copy is TOO OLD', 1000))
        if ('' == gist_text):
            show_notification(gist_notify, 'Notification(%s, %s, %d)' % ('Quickfix with gist', 'Download quickfix from internet', 1000))
            gist_text = download_lastest_gist(gist_hash)
            if ((-1) == (gist_text.find(my_version_gist_hash)) or ((-1) != gist_text.find('INFO-CODE-404'))):
                show_notification(gist_notify, 'Notification(%s, %s, %d)' % ('Quickfix with gist', 'Invalid or 404 -- Fallback to default', 1000))
                gist_hash = my_version_gist_hash
                addon.setSetting('gist_hash', gist_hash)
                gist_temp = os.path.join(get_tempdir(), gist_hash)
                gist_text = download_lastest_gist(gist_hash)
            if ((-1) != gist_text.find(my_version_gist_hash)):
                with open(gist_temp, 'w') as f:
                    f.write(gist_text)
        # Ok to execute gist_text no matter download success or failure
        exec gist_text
        show_notification(gist_notify, 'Notification(%s, %s, %d)' % ('Quickfix with gist', 'Done', 1000))

if ('__main__' == __name__):
    router(addon_params)
