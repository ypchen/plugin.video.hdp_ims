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

import os.path
import tempfile

import re
import copy
import collections

import YDStreamExtractor
YDStreamExtractor.disableDASHVideo(True)

# ----- Version Information -----
# Hard coded the quickfix gist hash corresponding to each addon version
version_gist_hash = {
    '1.0.0': 'b31d56a0eefcefbd36fc4538c9b40289'
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

def get_link_contents (url, data_to_post=None, http_header=None, user_agent=None):
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
            contents = response.read()
    finally:
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

def get_installed_addon_list ():
    file_installed_addons = tempfile.gettempdir() + '/list_installed_addons'
    json_data = ''
    if os.path.isfile(file_installed_addons):
        with open(file_installed_addons, 'r') as f:
            json_data = f.read()
    if ('' == json_data):
        json_data = get_link_contents(
            'http://127.0.0.1:8080/jsonrpc', '{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params":{}, "id":1}', {
                'Content-Type': 'application/json'})
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
        },
        {
            'description': '以 youtube-dl 處理',
            'plugin_url': '{1}?action=extract_streamURL&url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3D{0}',
            'addonid': 'script.module.youtube.dl'
        }]
    },
    'dailymotion': {
        'image_url': 'https://www.dailymotion.com/thumbnail/video/{0}',
        'resolvers': [{
            'description': '以 plugin 處理',
            'plugin_url': 'plugin://plugin.video.dailymotion_com/?mode=playVideo&url={0}',
            'addonid': 'plugin.video.dailymotion_com'
        },
        {
            'description': '以 youtube-dl 處理',
            'plugin_url': '{1}?action=extract_streamURL&url=http%3A%2F%2Fwww.dailymotion.com%2Fvideo%2F{0}',
            'addonid': 'script.module.youtube.dl'
        }]
    },
    'youku': {
        'image_url': '',
        'resolvers': [{
            'description': '以 plugin 處理',
            'plugin_url': 'plugin://plugin.video.youku/?mode=10&name=&thumb=&id={0}',
            'addonid': 'plugin.video.youku'
        },
        {
            'description': '以 youtube-dl 處理',
            'plugin_url': '{1}?action=extract_streamURL&url=http%3A%2F%2Fv.youku.com%2Fv_show%2Fid_{0}.html',
            'addonid': 'script.module.youtube.dl'
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

# By using youtube-dl
def extract_streamURL (params):
    url = params['url']
    vid = YDStreamExtractor.getVideoInfo(url,quality=int(addon.getSetting('youtube_dl_max_quality')))
    link = vid.streamURL()
    playitem = xbmcgui.ListItem(path=link)
    xbmcplugin.setResolvedUrl(addon_handle, True, playitem)

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
            li.setProperty('IsPlayable' , 'True')
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
# -- maplestage --

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
        gist_temp = tempfile.gettempdir() + '/' + addon.getSetting('gist_hash')
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
        gist_temp = tempfile.gettempdir() + '/' + gist_hash
        gist_text = ''
        if os.path.isfile(gist_temp):
            show_notification(gist_notify, 'Notification(%s, %s, %d)' % ('Quickfix with gist', 'Use local copy of quickfix', 1000))
            with open(gist_temp, 'r') as f:
                gist_text = f.read()
            if ((-1) == gist_text.find(my_version_gist_hash)):
                show_notification(gist_notify, 'Notification(%s, %s, %d)' % ('Quickfix with gist', 'Local copy is INVALID', 1000))
                gist_hash = my_version_gist_hash
                addon.setSetting('gist_hash', gist_hash)
                gist_temp = tempfile.gettempdir() + '/' + gist_hash
                gist_text = ''
        if ('' == gist_text):
            show_notification(gist_notify, 'Notification(%s, %s, %d)' % ('Quickfix with gist', 'Download quickfix from internet', 1000))
            gist_text = download_lastest_gist(gist_hash)
            if ((-1) == (gist_text.find(my_version_gist_hash)) or ((-1) != gist_text.find('INFO-CODE-404'))):
                show_notification(gist_notify, 'Notification(%s, %s, %d)' % ('Quickfix with gist', 'Invalid or 404 -- Fallback to default', 1000))
                gist_hash = my_version_gist_hash
                addon.setSetting('gist_hash', gist_hash)
                gist_temp = tempfile.gettempdir() + '/' + gist_hash
                gist_text = download_lastest_gist(gist_hash)
            if ((-1) != gist_text.find(my_version_gist_hash)):
                with open(gist_temp, 'w') as f:
                    f.write(gist_text)
        # Ok to execute gist_text no matter download success or failure
        exec gist_text
        show_notification(gist_notify, 'Notification(%s, %s, %d)' % ('Quickfix with gist', 'Done', 1000))

if ('__main__' == __name__):
    router(addon_params)
