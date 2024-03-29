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
    '1.18.4': 'cd452b0f316b16d5a9dab1983795a3cc'
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

# Fallback to curl
def get_link_contents (url, data_to_post=None, http_header=None, user_agent=None, url_redir=False):
    name = 'get_link_contents()'
    #xbmc.log('[%s] %s' % (name, 'url={' + url + '}'), xbmc.LOGNOTICE)
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
        #xbmc.log('[%s] %s' % (name, 'before -- response = urllib2.urlopen(request)'), xbmc.LOGNOTICE)
        response = urllib2.urlopen(request)
        #xbmc.log('[%s] %s' % (name, 'response.code={' + str(response.getcode()) + '}'), xbmc.LOGNOTICE)
        if (200 == response.getcode()):
            if (url_redir):
                # not sure why 200 (should be 302 here)
                url_redir = response.geturl()
            else:
                contents = response.read()
    #except urllib2.HTTPError, e:
        #xbmc.log('[%s] %s' % (name, 'HTTPError={' + str(e.code) + '}'), xbmc.LOGNOTICE)
    #except urllib2.URLError, e:
        #xbmc.log('[%s] %s' % (name, 'URLError={' + str(e.reason) + '}'), xbmc.LOGNOTICE)
    #except httplib.HTTPException, e:
        #xbmc.log('[%s] %s' % (name, 'HTTPException'), xbmc.LOGNOTICE)
    #except Exception as e:
        #xbmc.log('[%s] %s' % (name, 'e={' + str(e) + '}'), xbmc.LOGNOTICE)
    finally:
        #xbmc.log('[%s] %s' % (name, 'finally'), xbmc.LOGNOTICE)
        if (url_redir):
            return url_redir
        else:
            if (0 < len(contents)):
                #xbmc.log('[%s] %s' % (name, 'finally -- if (0 < len(contents))'), xbmc.LOGNOTICE)
                return contents
            else:
                # a very bad plan B
                #xbmc.log('[%s] %s' % (name, 'finally -- if (0 >= len(contents))'), xbmc.LOGNOTICE)
                import subprocess
                prog_curl = ''
                if not addon.getSetting('curl'):
                    prog_curl = '/usr/bin/curl'
                    xbmc.log('[%s] %s' % (name, 'if not addon.getSetting(curl): [' + prog_curl + ']'), xbmc.LOGNOTICE)
                else:
                    prog_curl = addon.getSetting('curl')
                    xbmc.log('[%s] %s' % (name, 'else (getSetting(curl) ok): [' + prog_curl + ']'), xbmc.LOGNOTICE)
                return subprocess.check_output([prog_curl, '--output', '-', url])

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
        'title': '劇迷 gimy.cc',
        'action': 'list_items',
        'callback': 'gimycc_id()',
        'isFolder': True,
        'siteVisible': 'siteVisible = True'
    },
    {
        'title': '劇迷 gimytv.com',
        'action': 'list_items',
        'callback': 'gimytv_id()',
        'isFolder': True,
        'siteVisible': 'siteVisible = True'
    },
    {
        'title': '劇迷 135mov.com / gimyvod.cc',
        'action': 'list_items',
        'callback': 'mov135_id()',
        'isFolder': True,
        'siteVisible': 'siteVisible = True'
    },
    {
        'title': '酷播 99KUBO',
        'action': 'list_items',
        'callback': 'kubo_id()',
        'isFolder': True,
        'siteVisible': 'siteVisible = True'
    },
]
# ----- ims -----

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

def read_program (python_program):
    python_program_text = ''
    if os.path.isfile(python_program):
        with open(python_program, 'r') as f:
            python_program_text = f.read()
    return (python_program_text)

def read_site_order ():
    python_file = 'site_order.py'
    return read_program(os.path.join(get_tempdir(), python_file))

def read_youtube_channels ():
    python_file = 'YouTube_Channels.py'
    # 1st: try /tmp
    python_program_text = read_program(os.path.join(get_tempdir(), python_file))
    if (0 >= len(python_program_text)):
        # 2nd: try /userdata
        python_program_text = read_program(os.path.join(xbmc.translatePath('special://masterprofile'), 'addon_data/plugin.video.hdp_ims', python_file))
    return (python_program_text)

def list_sites (params):
    name = 'list_sites()'
    site_order = []
    youtube_channels = []

#    xbmc.log('[%s] %s' % (name, '0. site_order={' + ', '.join(map(str, site_order)) + '}'), xbmc.LOGNOTICE)
#    xbmc.log('[%s] %s' % (name, '0. youtube_channels={' + ', '.join(map(str, youtube_channels)) + '}'), xbmc.LOGNOTICE)

    # read user-defined site order
    exec read_site_order()
    # check if site_order is valid
    if (len(site_order) != len(sites)):
        site_order = range(len(sites))
#    xbmc.log('[%s] %s' % (name, '1. site_order={' + ', '.join(map(str, site_order)) + '}'), xbmc.LOGNOTICE)

    # read user-defined youtube channels
    exec read_youtube_channels()
#    xbmc.log('[%s] %s' % (name, '2. youtube_channels={' + ', '.join(youtube_channels) + '}'), xbmc.LOGNOTICE)

    for site_index in site_order:
        site = sites[site_index]
        exec site['siteVisible']
        if (siteVisible):
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

# -----------------
# ----- sites -----
# -----------------

# -- gimy.cc --
def gimycc_id ():
    # hard-coded top level menu items
    # link is the -id-- in the search criteria
    return [
        {
            'title': '電視劇', 'link': 'https://gimy.cc/vodshow/drama---time.html', 'action': 'list_items',
                'callback': 'gimycc_drama_category(params)', 'isFolder': True
        },
        {
            'title': '電影', 'link': 'https://gimy.cc/vodshow/1---.html', 'action': 'list_items',
                'callback': 'gimycc_movie_category(params)', 'isFolder': True
        },
        {
            'title': '動漫', 'link': 'https://gimy.cc/vodshow/anime---.html', 'action': 'list_items',
                'callback': 'gimycc_area(params)', 'isFolder': True
        },
        {
            'title': '綜藝', 'link': 'https://gimy.cc/vodshow/variety---.html', 'action': 'list_items',
                'callback': 'gimycc_area(params)', 'isFolder': True
        }
    ]

gimycc_filter_URL_prefix = 'https://gimy.cc'
gimycc_filter_insert_all = '全部'
gimycc_filter_insert_at = '2020'
gimycc_filter_insert_this = '2021'
gimycc_filter_insert_pre = '-'
gimycc_filter_insert_post = '-'
gimycc_filter_str1 = '</ul>'
gimycc_filter_str2 = '<a '
gimycc_filter_str3 = '>'
gimycc_filter_str4 = '</a'
gimycc_filter_str5 = 'href="'
gimycc_filter_str6 = '"'
def gimycc_filter (params, url, explodeStart, nextCallback):
    html = get_link_contents(url)
    if ('' == html):
        return []
    htmlToExplode = str_between(html, explodeStart, gimycc_filter_str1)
    videos = htmlToExplode.split(gimycc_filter_str2)
    videos.pop(0)
    siteURLprefix = gimycc_filter_URL_prefix
    items = []
    prevTitle = ''
    for video in videos:
        title = str_between(video, gimycc_filter_str3, gimycc_filter_str4).strip()
        # order asc
        if ((prevTitle == gimycc_filter_insert_at) and (title == gimycc_filter_insert_all)):
            items.append({'title': gimycc_filter_insert_this, 'link': link.replace(gimycc_filter_insert_pre + gimycc_filter_insert_at + gimycc_filter_insert_post, gimycc_filter_insert_pre + gimycc_filter_insert_this + gimycc_filter_insert_post), 'action': 'list_items', 'callback': nextCallback, 'isFolder': True})
        link = siteURLprefix + str_between(video, gimycc_filter_str5, gimycc_filter_str6).strip()
        # order desc
        if ((prevTitle == gimycc_filter_insert_all) and (title == gimycc_filter_insert_at)):
            items.append({'title': gimycc_filter_insert_this, 'link': link.replace(gimycc_filter_insert_pre + gimycc_filter_insert_at + gimycc_filter_insert_post, gimycc_filter_insert_pre + gimycc_filter_insert_this + gimycc_filter_insert_post), 'action': 'list_items', 'callback': nextCallback, 'isFolder': True})
        items.append({'title': title, 'link': link, 'action': 'list_items', 'callback': nextCallback, 'isFolder': True})
        prevTitle = title
    return items

def gimycc_drama_category (params):
    return gimycc_filter (params, params['link'], '<span class="text-muted">類型', 'gimycc_year(params)')

def gimycc_movie_category (params):
    return gimycc_filter (params, params['link'], '<span class="text-muted">類型', 'gimycc_area(params)')

def gimycc_year (params):
    return gimycc_filter (params, params['link'], '<span class="text-muted">年份', 'gimycc_videos(params)')

def gimycc_area (params):
    return gimycc_filter (params, params['link'], '<span class="text-muted">地區', 'gimycc_year(params)')

gimycc_videos_str1 = '<ul class="stui-page text-center clearfix">'
gimycc_videos_str2 = '</ul>'
#gimycc_videos_str3 = ''
#gimycc_videos_str4 = ''
gimycc_videos_str5 = '<span class="num">'
gimycc_videos_str6 = '</span>'
#gimycc_videos_str7 = '下一頁</a>'
#gimycc_videos_str8 = '</ul>'
#gimycc_videos_str9 = 'pagegbk" data="p-'
#gimycc_videos_strA = '">尾頁</a>'
gimycc_videos_strB = '<ul class="stui-vodlist '
gimycc_videos_strC = '<ul class="stui-page '
gimycc_videos_strD = '<div class="stui-vodlist__box'
gimycc_videos_strE = 'https://gimy.cc'
gimycc_videos_strF = '</li>'
gimycc_videos_strG = '上一頁'
gimycc_videos_strH = '">'
gimycc_videos_strI = '</a'
gimycc_videos_strJ = 'href="'
gimycc_videos_strK = '"'
gimycc_videos_strL = 'title="'
gimycc_videos_strM = '"'
gimycc_videos_strN = 'href="'
gimycc_videos_strO = '"'
gimycc_videos_strP = 'data-original="'
gimycc_videos_strQ = '"'
gimycc_videos_strR = 'pic-text text-right">'
gimycc_videos_strS = '</span>'
gimycc_videos_strT = '下一頁'
gimycc_videos_strU = '">'
gimycc_videos_strV = '</a'
gimycc_videos_strW = 'href="'
gimycc_videos_strX = '"'
gimycc_videos_strY = 'text-muted hidden-xs">'
gimycc_videos_strZ = '</p>'
def gimycc_videos (params):
    data = json.loads(base64.b64decode(params['data']), 'utf-8')
    try:
        page = int(data['page'])
    except:
        page = 1
    html = get_link_contents(params['link'])
    if ('' == html):
        return []
#    pageHtml = str_between(str_between(html, gimycc_videos_str1, gimycc_videos_str2), gimycc_videos_str3, gimycc_videos_str4)
    pageHtml = str_between(html, gimycc_videos_str1, gimycc_videos_str2)
    pages = str_between(pageHtml, gimycc_videos_str5, gimycc_videos_str6).split('/')
#    pages.append(str_between(pageHtml, gimycc_videos_str5, gimycc_videos_str6))
#    pages.append(str_between(str_between(pageHtml, gimycc_videos_str7, gimycc_videos_str8), gimycc_videos_str9, gimycc_videos_strA))
    if ('' == pages[1]):
        pages[1] = str(page)
    htmlToExplode = str_between(html, gimycc_videos_strB, gimycc_videos_strC)
    videos = htmlToExplode.split(gimycc_videos_strD)
    videos.pop(0)
    siteURLprefix = gimycc_videos_strE
    items = []
    items.append({'title': '第 [COLOR limegreen]' + pages[0] + '[/COLOR] 頁/共 [COLOR limegreen]' + pages[1] + '[/COLOR] 頁', 'link': '', 'action': '', 'callback': '', 'isFolder': False})
    pageBlocks = pageHtml.split(gimycc_videos_strF)
    if (page > 1):
        for pageBlock in pageBlocks:
            if (gimycc_videos_strG == str_between(pageBlock, gimycc_videos_strH, gimycc_videos_strI).strip()):
                link = siteURLprefix + str_between(pageBlock, gimycc_videos_strJ, gimycc_videos_strK).strip()
                items.append({'title': '上一頁 (回第' + str(page-1) + '頁)', 'link': link, 'action': 'list_items', 'callback': 'gimycc_videos(params)', 'isFolder': True, 'page': (page-1)})
                break
    for video in videos:
        title = str_between(video, gimycc_videos_strL, gimycc_videos_strM).strip()
        if ('' != title):
            link = siteURLprefix + str_between(video, gimycc_videos_strN, gimycc_videos_strO).strip()
            image = str_between(video, gimycc_videos_strP, gimycc_videos_strQ).strip()
            note = '(' + str_between(video, gimycc_videos_strR, gimycc_videos_strS).strip() + ') ' + str_between(video, gimycc_videos_strY, gimycc_videos_strZ).strip()
            items.append({'title': title + ' -- ' + note, 'link': link, 'action': 'list_items', 'callback': 'gimycc_sources(params)', 'isFolder': True, 'image': image})
    if (int(page) < int(pages[1])):
        for pageBlock in pageBlocks:
            if (gimycc_videos_strT == str_between(pageBlock, gimycc_videos_strU, gimycc_videos_strV).strip()):
                link = siteURLprefix + str_between(pageBlock, gimycc_videos_strW, gimycc_videos_strX).strip()
                items.append({'title': '下一頁 (到第' + str(page+1) + '頁)', 'link': link, 'action': 'list_items', 'callback': 'gimycc_videos(params)', 'isFolder': True, 'page': (page+1)})
                break
    return items

gimycc_sources_str1 = '<ul class="nav nav-tabs'
gimycc_sources_str2 = '</ul>'
gimycc_sources_str3 = '"tabslist"'
gimycc_sources_str4 = '"tab">'
gimycc_sources_str5 = '</a>'
gimycc_sources_str6 = 'href="#'
gimycc_sources_str7 = '"'
gimycc_sources_str8 = '<div class="tab-content '
gimycc_sources_str9 = '<div class="stui-pannel-box">'
def gimycc_sources (params):
    name = 'gimycc_sources()'
    xbmc.log('[%s] %s' % (name, 'link={' + params['link'] + '}'), xbmc.LOGNOTICE)
    html = get_link_contents(params['link'])
    if ('' == html):
        return []
    htmlToExplode = str_between(html, gimycc_sources_str1, gimycc_sources_str2)
    videos = htmlToExplode.split(gimycc_sources_str3)
    videos.pop(0)
    items = []
    items.append({'title': '選擇來源：', 'link': '', 'action': '', 'callback': '', 'isFolder': False})
    for video in videos:
        title = str_between(video, gimycc_sources_str4, gimycc_sources_str5).strip()
        playlist_id = str_between(video, gimycc_sources_str6, gimycc_sources_str7).strip()
        items.append({'title': title, 'link': params['link'], 'action': 'list_items', 'callback': 'gimycc_episodes(params)', 'isFolder': True, 'playlist_id': playlist_id, 'playlist_title': title, 'html': str_between(html, gimycc_sources_str8, gimycc_sources_str9)})
    return items

gimycc_episodes_str_default_id = 'playlist1'
gimycc_episodes_str1 = ''
gimycc_episodes_str2 = '</ul>'
gimycc_episodes_str3 = 'id="'
gimycc_episodes_str4 = '"'
gimycc_episodes_str5 = '<li'
gimycc_episodes_str6 = 'https://gimy.cc'
gimycc_episodes_str7 = 'title="'
gimycc_episodes_str8 = '"'
gimycc_episodes_str9 = 'href="'
gimycc_episodes_strA = '"'
def gimycc_episodes (params):
    name = 'gimycc_episodes()'
    data = json.loads(base64.b64decode(params['data']), 'utf-8')
    try:
        playlist_id = data['playlist_id']
        playlist_title = data['playlist_title']
    except:
        playlist_id = gimycc_episodes_str_default_id
        playlist_title = '預設'
#   xbmc.log('[%s] %s' % (name, 'playlist_id={' + playlist_id + '}' + '; playlist_title={' + playlist_title + '}'), xbmc.LOGNOTICE)
    html = data['html']
    if (not gimycc_episodes_str1):
        local_gimycc_episodes_str1 = gimycc_episodes_str3 + playlist_id + gimycc_episodes_str4
    else:
        local_gimycc_episodes_str1 = gimycc_episodes_str1
    htmlToExplode = str_between(html, local_gimycc_episodes_str1, gimycc_episodes_str2)
    videos = htmlToExplode.split(gimycc_episodes_str5)
    videos.pop(0)
    siteURLprefix = gimycc_episodes_str6
    items = []
    for video in videos:
        title = playlist_title + ': ' + str_between(video, gimycc_episodes_str7, gimycc_episodes_str8).strip()
        link = siteURLprefix + str_between(video, gimycc_episodes_str9, gimycc_episodes_strA).strip()
#       xbmc.log('[%s] %s' % (name, 'link={' + link + '}'), xbmc.LOGNOTICE)
        link = build_url_dict({'action': 'gimycc_episode', 'link': link})
        items.append({'title': title, 'link': link, 'isFolder': False, 'IsPlayable': 'True'})
    return items

# Unknown: JB, Qw
gimycc_episode_url_code_dict = {'JT':'', 'JC':'+', 'JD':',', 'JE':'-', 'JF':'.', 'JG':'/', 'Mw':'0', 'Mx':'1', 'My':'2', 'Mz':'3', 'M0':'4', 'M1':'5', 'M2':'6', 'M3':'7', 'M4':'8', 'M5':'9', 'NB':':', 'NC':';', 'ND':'<', 'NE':'=', 'NF':'>', 'NG':'?', 'VC':'[', 'VD':'\\', 'VE':']', 'VF':'^', 'VG':'_', 'Yx':'a', 'Yy':'b', 'Yz':'c', 'Y0':'d', 'Y1':'e', 'Y2':'f', 'Y3':'g', 'Y4':'h', 'Y5':'i', 'ZB':'j', 'ZC':'k', 'ZD':'l', 'ZE':'m', 'ZF':'n', 'ZG':'o', 'cw':'p', 'cx':'q', 'cy':'r', 'cz':'s', 'c0':'t', 'c1':'u', 'c2':'v', 'c3':'w', 'c4':'x', 'c5':'y', 'dB':'z', 'Qx':'A', 'Qy':'B', 'Qz':'C', 'Q0':'D', 'Q1':'E', 'Q2':'F', 'Q3':'G', 'Q4':'H', 'Q5':'I', 'RB':'J', 'RC':'K', 'RD':'L', 'RE':'M', 'RF':'N', 'RG':'O', 'Uw':'P', 'Ux':'Q', 'Uy':'R', 'Uz':'S', 'U0':'T', 'U1':'U', 'U2':'V', 'U3':'W', 'U4':'X', 'U5':'Y', 'VB':'Z'}

def gimycc_episode (params):
    name = 'gimycc_episode()'
    link_orig = params['link']
    xbmc.log('[%s] %s' % (name, 'input: link={' + link_orig + '}'), xbmc.LOGNOTICE)
    html = get_link_contents(link_orig)
    if ('' == html):
        return []
    htmlToExplode = str_between(html, 'player_data={', '</script>')
# https://stackoverflow.com/questions/9475241/split-string-every-nth-character
    link = ''
    line = str_between(htmlToExplode, '"url":"', '"')
    exception_num = 0
    n = 2
    lineSplit = [line[i:i+n] for i in range(0, len(line), n)]
    for s in lineSplit:
        try:
            link = link + gimycc_episode_url_code_dict[s]
        except KeyError:
            link = link + '?'+s+'#'
            exception_num += 1
    if (0 < exception_num):
        xbmc.log('[%s] %s' % (name, 'if (0 < exception_num): [' + link_orig + '#%#' + link + ']'), xbmc.LOGERROR)
    xbmc.log('[%s] %s' % (name, 'playing: link={' + link + '}'), xbmc.LOGNOTICE)
    playitem = xbmcgui.ListItem(path=link)
    playitem.setProperty('inputstreamaddon','inputstream.adaptive')
    playitem.setProperty('inputstream.adaptive.manifest_type','hls')
    playitem.setMimeType('application/vnd.apple.mpegurl')
    playitem.setContentLookup(False)
    xbmcplugin.setResolvedUrl(addon_handle, True, playitem)
# -- gimy.cc --

# -- gimytv.com --
gimytv_site = 'gimytv.com'
def gimytv_id ():
    # hard-coded top level menu items
    # link is the -id-- in the search criteria
    return [
        {
            'title': '電視劇', 'link': 'https://' + gimytv_site + '/genre/2-----------.html', 'action': 'list_items',
                'callback': 'gimytv_drama_category(params)', 'isFolder': True
        },
        {
            'title': '電影', 'link': 'https://' + gimytv_site + '/genre/1-----------.html', 'action': 'list_items',
                'callback': 'gimytv_movie_category(params)', 'isFolder': True
        },
        {
            'title': '動漫', 'link': 'https://' + gimytv_site + '/genre/4-----------.html', 'action': 'list_items',
                'callback': 'gimytv_area(params)', 'isFolder': True
        },
        {
            'title': '綜藝', 'link': 'https://' + gimytv_site + '/genre/3-----------.html', 'action': 'list_items',
                'callback': 'gimytv_area(params)', 'isFolder': True
        }
    ]

gimytv_filter_URL_prefix = 'https://' + gimytv_site
gimytv_filter_insert_all = '全部'
gimytv_filter_insert_at = '2020'
gimytv_filter_insert_this = '2021'
gimytv_filter_insert_pre = '-'
gimytv_filter_insert_post = '.'
gimytv_filter_str1 = '</ul>'
gimytv_filter_str2 = '<a '
gimytv_filter_str3 = '>'
gimytv_filter_str4 = '</a'
gimytv_filter_str5 = 'href="'
gimytv_filter_str6 = '"'
def gimytv_filter (params, url, explodeStart, nextCallback):
    html = get_link_contents(url)
    if ('' == html):
        return []
    htmlToExplode = str_between(html, explodeStart, gimytv_filter_str1)
    videos = htmlToExplode.split(gimytv_filter_str2)
    videos.pop(0)
    siteURLprefix = gimytv_filter_URL_prefix
    items = []
    prevTitle = ''
    for video in videos:
        title = str_between(video, gimytv_filter_str3, gimytv_filter_str4).strip()
        # order asc
        if ((prevTitle == gimytv_filter_insert_at) and (title == gimytv_filter_insert_all)):
            items.append({'title': gimytv_filter_insert_this, 'link': link.replace(gimytv_filter_insert_pre + gimytv_filter_insert_at + gimytv_filter_insert_post, gimytv_filter_insert_pre + gimytv_filter_insert_this + gimytv_filter_insert_post), 'action': 'list_items', 'callback': nextCallback, 'isFolder': True})
        link = siteURLprefix + str_between(video, gimytv_filter_str5, gimytv_filter_str6).strip()
        # order desc
        if ((prevTitle == gimytv_filter_insert_all) and (title == gimytv_filter_insert_at)):
            items.append({'title': gimytv_filter_insert_this, 'link': link.replace(gimytv_filter_insert_pre + gimytv_filter_insert_at + gimytv_filter_insert_post, gimytv_filter_insert_pre + gimytv_filter_insert_this + gimytv_filter_insert_post), 'action': 'list_items', 'callback': nextCallback, 'isFolder': True})
        items.append({'title': title, 'link': link, 'action': 'list_items', 'callback': nextCallback, 'isFolder': True})
        prevTitle = title
    return items

def gimytv_drama_category (params):
    return gimytv_filter (params, params['link'], '">类型', 'gimytv_year(params)')

def gimytv_movie_category (params):
    return gimytv_filter (params, params['link'], '">类型', 'gimytv_area(params)')

def gimytv_area (params):
    return gimytv_filter (params, params['link'], '">地区', 'gimytv_year(params)')

def gimytv_year (params):
    return gimytv_filter (params, params['link'], '">年份', 'gimytv_videos(params)')

gimytv_videos_str1 = 'class="myui-page '
gimytv_videos_str2 = '</ul>'
gimytv_videos_str3 = 'class="visible-xs"'
gimytv_videos_str4 = '</li>'
gimytv_videos_str5 = '">'
gimytv_videos_str6 = '/'
gimytv_videos_str7 = '/'
gimytv_videos_str8 = '</a>'
#gimytv_videos_str9 = 'pagegbk" data="p-'
#gimytv_videos_strA = '">尾頁</a>'
gimytv_videos_strB = 'class="myui-vodlist '
gimytv_videos_strC = '<div class="myui-foot '
gimytv_videos_strD = '<li '
gimytv_videos_strE = 'https://' + gimytv_site
gimytv_videos_strF = '</li>'
gimytv_videos_strG = '上一页'
gimytv_videos_strH = '">'
gimytv_videos_strI = '</a'
gimytv_videos_strJ = 'href="'
gimytv_videos_strK = '"'
gimytv_videos_strL = 'title="'
gimytv_videos_strM = '"'
gimytv_videos_strN = 'href="'
gimytv_videos_strO = '"'
gimytv_videos_strP = 'data-original="'
gimytv_videos_strQ = '"'
gimytv_videos_strR = 'pic-text text-right">'
gimytv_videos_strS = '</span>'
gimytv_videos_strT = '下一页'
gimytv_videos_strU = '">'
gimytv_videos_strV = '</a'
gimytv_videos_strW = 'href="'
gimytv_videos_strX = '"'
gimytv_videos_strY = 'text-muted hidden-xs">'
gimytv_videos_strZ = '</p>'
def gimytv_videos (params):
    name = 'gimytv_videos()'
    data = json.loads(base64.b64decode(params['data']), 'utf-8')
    try:
        page = int(data['page'])
    except:
        page = 1
    html = get_link_contents(params['link'])
    if ('' == html):
        return []
    pageHtmlAll = str_between(html, gimytv_videos_str1, gimytv_videos_str2)
    pageHtml = str_between(pageHtmlAll, gimytv_videos_str3, gimytv_videos_str4)
    pages = []
    pages.append(str_between(pageHtml, gimytv_videos_str5, gimytv_videos_str6))
    pages.append(str_between(pageHtml, gimytv_videos_str7, gimytv_videos_str8))
#    xbmc.log('[%s] %s' % (name, 'pages={' + pages[0] + ',' + pages[1] + '}'), xbmc.LOGNOTICE)
    if ('' == pages[1]):
        pages[1] = str(page)
        pages[0] = pages[1]
    htmlToExplode = str_between(html, gimytv_videos_strB, gimytv_videos_strC)
    videos = htmlToExplode.split(gimytv_videos_strD)
    videos.pop(0)
    siteURLprefix = gimytv_videos_strE
    items = []
    items.append({'title': '第 [COLOR limegreen]' + pages[0] + '[/COLOR] 頁/共 [COLOR limegreen]' + pages[1] + '[/COLOR] 頁', 'link': '', 'action': '', 'callback': '', 'isFolder': False})
    pageBlocks = pageHtmlAll.split(gimytv_videos_strF)
    if (page > 1):
        for pageBlock in pageBlocks:
            if (gimytv_videos_strG == str_between(pageBlock, gimytv_videos_strH, gimytv_videos_strI).strip()):
                link = siteURLprefix + str_between(pageBlock, gimytv_videos_strJ, gimytv_videos_strK).strip()
                items.append({'title': '上一頁 (回第' + str(page-1) + '頁)', 'link': link, 'action': 'list_items', 'callback': 'gimytv_videos(params)', 'isFolder': True, 'page': (page-1)})
                break
    for video in videos:
        title = str_between(video, gimytv_videos_strL, gimytv_videos_strM).strip()
        if ('' != title):
            link = siteURLprefix + str_between(video, gimytv_videos_strN, gimytv_videos_strO).strip()
            image = str_between(video, gimytv_videos_strP, gimytv_videos_strQ).strip()
            note = '(' + str_between(video, gimytv_videos_strR, gimytv_videos_strS).strip() + ') ' + str_between(video, gimytv_videos_strY, gimytv_videos_strZ).strip()
            items.append({'title': title + ' -- ' + note, 'link': link, 'action': 'list_items', 'callback': 'gimytv_sources(params)', 'isFolder': True, 'image': image})
    if (int(page) < int(pages[1])):
        for pageBlock in pageBlocks:
            if (gimytv_videos_strT == str_between(pageBlock, gimytv_videos_strU, gimytv_videos_strV).strip()):
                link = siteURLprefix + str_between(pageBlock, gimytv_videos_strW, gimytv_videos_strX).strip()
                items.append({'title': '下一頁 (到第' + str(page+1) + '頁)', 'link': link, 'action': 'list_items', 'callback': 'gimytv_videos(params)', 'isFolder': True, 'page': (page+1)})
                break
    return items

gimytv_sources_str1 = '-- end 詳細信息--'
gimytv_sources_str2 = '-- 下載地址--'
gimytv_sources_str3 = '<h3 '
gimytv_sources_str4 = '"title">'
gimytv_sources_str5 = '</h3>'
gimytv_sources_str6 = '"title">'
gimytv_sources_str7 = '</h3>'
gimytv_sources_str8 = '-- end 詳細信息--'
gimytv_sources_str9 = '-- 下載地址--'
gimytv_sources_strA = '-->'
gimytv_sources_strB = '!--'
def gimytv_sources (params):
    name = 'gimytv_sources()'
    html = get_link_contents(params['link'])
    if ('' == html):
        return []
    htmlToExplode = str_between(html, gimytv_sources_str1, gimytv_sources_str2)
    videos = htmlToExplode.split(gimytv_sources_str3)
    videos.pop(0)
    items = []
    items.append({'title': '選擇來源：', 'link': '', 'action': '', 'callback': '', 'isFolder': False})
    for video in videos:
        title = str_between(video, gimytv_sources_str4, gimytv_sources_str5).strip()
        playlist_id = str_between(video, gimytv_sources_str6, gimytv_sources_str7).strip()
#        playlist_id = title
        items.append({'title': title, 'link': params['link'], 'action': 'list_items', 'callback': 'gimytv_episodes(params)', 'isFolder': True, 'playlist_id': playlist_id, 'playlist_title': title, 'html': str_between(str_between(html, gimytv_sources_str8, gimytv_sources_str9), gimytv_sources_strA, gimytv_sources_strB)})
    return items

gimytv_episodes_str_default_id = 'playlist1'
gimytv_episodes_str1 = 'fa-sort'
gimytv_episodes_str2 = '</ul>'
gimytv_episodes_str3 = '<li '
gimytv_episodes_str4 = 'https://' + gimytv_site
gimytv_episodes_str5 = '.html">'
gimytv_episodes_str6 = '<'
gimytv_episodes_str7 = 'href="'
gimytv_episodes_str8 = '"'
def gimytv_episodes (params):
    name = 'gimytv_episodes()'
    data = json.loads(base64.b64decode(params['data']), 'utf-8')
    try:
        playlist_id = data['playlist_id']
        playlist_title = data['playlist_title']
    except:
        playlist_id = gimytv_episodes_str_default_id
        playlist_title = '預設'
    html = data['html']
    htmlToExplode = html
    videoSources = htmlToExplode.split(gimytv_episodes_str1)
    videoSources.pop(0)
    for videoSource in videoSources:
        if ((-1) != videoSource.find(playlist_id)):
#            xbmc.log('[%s] %s' % (name, 'playlist_id={' + playlist_id + '}'), xbmc.LOGNOTICE)
            html = videoSource
            htmlToExplode = str_between(html, playlist_id, gimytv_episodes_str2)
            videos = htmlToExplode.split(gimytv_episodes_str3)
            videos.pop(0)
            siteURLprefix = gimytv_episodes_str4
            items = []
            for video in videos:
                title = playlist_title + ': ' + str_between(video, gimytv_episodes_str5, gimytv_episodes_str6).strip()
                link = siteURLprefix + str_between(video, gimytv_episodes_str7, gimytv_episodes_str8).strip()
#                xbmc.log('[%s] %s' % (name, 'link={' + link + '}'), xbmc.LOGNOTICE)
                link = build_url_dict({'action': 'gimytv_episode', 'link': link})
                items.append({'title': title, 'link': link, 'isFolder': False, 'IsPlayable': 'True'})
            return items
    return []

def gimytv_episode (params):
    name = 'gimytv_episode()'
    link_orig = params['link']
    xbmc.log('[%s] %s' % (name, 'input: link={' + link_orig + '}'), xbmc.LOGNOTICE)
    html = get_link_contents(link_orig)
    if ('' == html):
        return []
    htmlToExplode = str_between(html, 'player_data=', '</script>')
    link = str_between(htmlToExplode, '"url":"', '"').replace('\\/', '/')
    xbmc.log('[%s] %s' % (name, 'playing: link={' + link + '}'), xbmc.LOGNOTICE)
    playitem = xbmcgui.ListItem(path=link)
    playitem.setProperty('inputstreamaddon','inputstream.adaptive')
    playitem.setProperty('inputstream.adaptive.manifest_type','hls')
    playitem.setMimeType('application/vnd.apple.mpegurl')
    playitem.setContentLookup(False)
    xbmcplugin.setResolvedUrl(addon_handle, True, playitem)
# -- gimytv.com --

# -- 135mov.com --
mov135_site = 'gimyvod.cc'
def mov135_id ():
    # hard-coded top level menu items
    # link is the -id-- in the search criteria
    return [
        {
            'title': '電視電影', 'link': 'http://' + mov135_site + '/list-select-id-16-type--area--year--star--state--order-addtime.html', 'action': 'list_items',
                'callback': 'mov135_channel(params)', 'isFolder': True
        },
        {
            'title': '動漫', 'link': 'http://' + mov135_site + '/list-select-id-3-type--area--year--star--state--order-addtime.html', 'action': 'list_items',
                'callback': 'mov135_area(params)', 'isFolder': True
        },
        {
            'title': '綜藝', 'link': 'http://' + mov135_site + '/list-select-id-4-type--area--year--star--state--order-addtime.html', 'action': 'list_items',
                'callback': 'mov135_area(params)', 'isFolder': True
        }
    ]

mov135_filter_URL_prefix = 'http://' + mov135_site
mov135_filter_insert_all = '全部'
mov135_filter_insert_at = '2020'
mov135_filter_insert_this = '2021'
mov135_filter_insert_pre = '-year-'
mov135_filter_insert_post = '-star-'
mov135_filter_str1 = '</dd>'
mov135_filter_str2 = '<a '
mov135_filter_str3 = '>'
mov135_filter_str4 = '</a'
mov135_filter_str5 = 'href="'
mov135_filter_str6 = '"'
def mov135_filter (params, url, explodeStart, nextCallback):
    name = 'mov135_filter()'
    xbmc.log('[%s] %s' % (name, '[' + explodeStart + ']; link={' + url + '}'), xbmc.LOGNOTICE)
    html = get_link_contents(url)
    if ('' == html):
        return []
    htmlToExplode = str_between(html, explodeStart, mov135_filter_str1)
    videos = htmlToExplode.split(mov135_filter_str2)
    videos.pop(0)
    siteURLprefix = mov135_filter_URL_prefix
    items = []
    prevTitle = ''
    for video in videos:
        title = str_between(video, mov135_filter_str3, mov135_filter_str4).strip()
        # Special for mov135 -- BEGIN
        if (('動漫' != title) and ('綜藝' != title)):
        # Special for mov135 -- END
            # order asc
            if ((prevTitle == mov135_filter_insert_at) and (title == mov135_filter_insert_all)):
                items.append({'title': mov135_filter_insert_this, 'link': link.replace(mov135_filter_insert_pre + mov135_filter_insert_at + mov135_filter_insert_post, mov135_filter_insert_pre + mov135_filter_insert_this + mov135_filter_insert_post), 'action': 'list_items', 'callback': nextCallback, 'isFolder': True})
            link = siteURLprefix + str_between(video, mov135_filter_str5, mov135_filter_str6).strip()
            # order desc
            if ((prevTitle == mov135_filter_insert_all) and (title == mov135_filter_insert_at)):
                items.append({'title': mov135_filter_insert_this, 'link': link.replace(mov135_filter_insert_pre + mov135_filter_insert_at + mov135_filter_insert_post, mov135_filter_insert_pre + mov135_filter_insert_this + mov135_filter_insert_post), 'action': 'list_items', 'callback': nextCallback, 'isFolder': True})
            items.append({'title': title, 'link': link, 'action': 'list_items', 'callback': nextCallback, 'isFolder': True})
            prevTitle = title
    return items

def mov135_channel (params):
    return mov135_filter (params, params['link'], '>頻道：', 'mov135_year(params)')

def mov135_area (params):
    return mov135_filter (params, params['link'], '>地區：', 'mov135_year(params)')

def mov135_year (params):
    return mov135_filter (params, params['link'], '>年代：', 'mov135_videos(params)')

mov135_videos_str1 = 'class="pagination pagination'
mov135_videos_str2 = '</ul>'
mov135_videos_str3 = 'disabled">'
mov135_videos_str4 = '</li>'
mov135_videos_str5 = '">'
mov135_videos_str6 = '</a>'
mov135_videos_str7 = '">...'
mov135_videos_str8 = '</a>'
#mov135_videos_str9 = 'pagegbk" data="p-'
#mov135_videos_strA = '">尾頁</a>'
mov135_videos_strB = '<ul class="thumbnail-group '
mov135_videos_strC = '</ul>'
mov135_videos_strD = '<li'
mov135_videos_strE = 'http://' + mov135_site
mov135_videos_strF = '</li>'
mov135_videos_strG = '&laquo;'
mov135_videos_strH = '">'
mov135_videos_strI = '</a'
mov135_videos_strJ = 'href="'
mov135_videos_strK = '"'
mov135_videos_strL = 'title="'
mov135_videos_strM = '"'
mov135_videos_strMx = '線上看'
mov135_videos_strN = 'href="'
mov135_videos_strO = '"'
mov135_videos_strP = 'data-original="'
mov135_videos_strQ = '"'
mov135_videos_strR = '"video-grade">'
mov135_videos_strS = '</span>'
mov135_videos_strT = '&raquo;'
mov135_videos_strU = '.html">'
mov135_videos_strV = '</a'
mov135_videos_strW = 'href="'
mov135_videos_strX = '"'
def mov135_videos (params):
    name = 'mov135_videos()'
    data = json.loads(base64.b64decode(params['data']), 'utf-8')
    try:
        page = int(data['page'])
    except:
        page = 1
    html = get_link_contents(params['link'])
    if ('' == html):
        return []
    pageHtmlAll = str_between(html, mov135_videos_str1, mov135_videos_str2)
    pages = []
    pages.append(str_between(str_between(pageHtmlAll, mov135_videos_str3, mov135_videos_str4), mov135_videos_str5, mov135_videos_str6))
    pages.append(str_between(pageHtmlAll, mov135_videos_str7, mov135_videos_str8))
    xbmc.log('[%s] %s' % (name, 'pages={' + pages[0] + ',' + pages[1] + '}'), xbmc.LOGNOTICE)
    if ('' == pages[1]):
        pages[1] = str(page)
        pages[0] = pages[1]
    htmlToExplode = str_between(html, mov135_videos_strB, mov135_videos_strC)
    videos = htmlToExplode.split(mov135_videos_strD)
    videos.pop(0)
    siteURLprefix = mov135_videos_strE
    items = []
    items.append({'title': '第 [COLOR limegreen]' + pages[0] + '[/COLOR] 頁/共 [COLOR limegreen]' + pages[1] + '[/COLOR] 頁', 'link': '', 'action': '', 'callback': '', 'isFolder': False})
    pageBlocks = pageHtmlAll.split(mov135_videos_strF)
    if (page > 1):
        for pageBlock in pageBlocks:
            if (mov135_videos_strG == str_between(pageBlock, mov135_videos_strH, mov135_videos_strI).strip()):
                link = siteURLprefix + str_between(pageBlock, mov135_videos_strJ, mov135_videos_strK).strip()
                items.append({'title': '上一頁 (回第' + str(page-1) + '頁)', 'link': link, 'action': 'list_items', 'callback': 'mov135_videos(params)', 'isFolder': True, 'page': (page-1)})
                break
    for video in videos:
        title = str_between(video, mov135_videos_strL, mov135_videos_strM).strip().replace(mov135_videos_strMx, '')
        if ('' != title):
            link = siteURLprefix + str_between(video, mov135_videos_strN, mov135_videos_strO).strip()
            image = siteURLprefix + str_between(video, mov135_videos_strP, mov135_videos_strQ).strip()
            note = ' -- (' + str_between(video, mov135_videos_strR, mov135_videos_strS).strip() + ')'
            items.append({'title': title + note, 'link': link, 'action': 'list_items', 'callback': 'mov135_sources(params)', 'isFolder': True, 'image': image})
    if (int(page) < int(pages[1])):
        for pageBlock in pageBlocks:
            if (mov135_videos_strT == str_between(pageBlock, mov135_videos_strU, mov135_videos_strV).strip()):
                link = siteURLprefix + str_between(pageBlock, mov135_videos_strW, mov135_videos_strX).strip()
                items.append({'title': '下一頁 (到第' + str(page+1) + '頁)', 'link': link, 'action': 'list_items', 'callback': 'mov135_videos(params)', 'isFolder': True, 'page': (page+1)})
                break
    return items

mov135_sources_str1 = '<ul class="detail-tab '
mov135_sources_str2 = '</ul>'
mov135_sources_str3 = '<li '
mov135_sources_str4 = 'tab">'
mov135_sources_str5 = '</a>'
mov135_sources_str6 = 'data-active="'
mov135_sources_str7 = '"'
mov135_sources_str8 = 'data-target="'
mov135_sources_str9 = '"'
mov135_sources_strA = '<div class="detail-content '
mov135_sources_strB = '</div>'
mov135_sources_strC = '<ul '
def mov135_sources (params):
    name = 'mov135_sources()'
    xbmc.log('[%s] %s' % (name, 'link={' + params['link'] + '}'), xbmc.LOGNOTICE)
    html = get_link_contents(params['link'])
    if ('' == html):
        return []
    ff_playurl = str_between(html, mov135_sources_str6, mov135_sources_str7)
    htmlToExplode = str_between(html, mov135_sources_str1, mov135_sources_str2)
    videos = htmlToExplode.split(mov135_sources_str3)
    videos.pop(0)
    htmlToExplodeDetail = str_between(html, mov135_sources_strA, mov135_sources_strB)
    videosDetail = htmlToExplodeDetail.split(mov135_sources_strC)
    videosDetail.pop(0)
    items = []
    items.append({'title': '選擇來源：', 'link': '', 'action': '', 'callback': '', 'isFolder': False})
    current_video_index = 0
    for video in videos:
        title = str_between(video, mov135_sources_str4, mov135_sources_str5).strip()
        playlist_id = str_between(video, mov135_sources_str8, mov135_sources_str9).strip().replace(ff_playurl, '')
        items.append({'title': title, 'link': params['link'], 'action': 'list_items', 'callback': 'mov135_episodes(params)', 'isFolder': True, 'playlist_id': playlist_id, 'playlist_title': title, 'html': videosDetail[current_video_index]})
        current_video_index = current_video_index + 1
    return items

mov135_episodes_str_default_id = '1'
#mov135_episodes_str1 = ''
#mov135_episodes_str2 = ''
mov135_episodes_str3 = '<li '
mov135_episodes_str4 = 'http://' + mov135_site
mov135_episodes_str5 = 'title="'
mov135_episodes_str6 = '"'
mov135_episodes_str7 = 'href="'
mov135_episodes_str8 = '"'
def mov135_episodes (params):
    name = 'mov135_episodes()'
    data = json.loads(base64.b64decode(params['data']), 'utf-8')
    try:
        playlist_id = data['playlist_id']
        playlist_title = data['playlist_title']
    except:
        playlist_id = mov135_episodes_str_default_id
        playlist_title = '預設'
    html = data['html']
    htmlToExplode = html
    videos = htmlToExplode.split(mov135_episodes_str3)
    videos.pop(0)
    siteURLprefix = mov135_episodes_str4
    items = []
    for video in videos:
        title = playlist_title + ': ' + str_between(video, mov135_episodes_str5, mov135_episodes_str6).strip()
        link = siteURLprefix + str_between(video, mov135_episodes_str7, mov135_episodes_str8).strip()
#                xbmc.log('[%s] %s' % (name, 'link={' + link + '}'), xbmc.LOGNOTICE)
        link = build_url_dict({'action': 'mov135_episode', 'link': link})
        items.append({'title': title, 'link': link, 'isFolder': False, 'IsPlayable': 'True'})
    return items

def mov135_episode (params):
    name = 'mov135_episode()'
    link_orig = params['link']
    xbmc.log('[%s] %s' % (name, 'input: link={' + link_orig + '}'), xbmc.LOGNOTICE)
    html = get_link_contents(link_orig)
    if ('' == html):
        return []
    htmlToExplode = str_between(html, 'cms_player =', '</script>')
    link = str_between(htmlToExplode, '"url":"', '"')
    if ((-1) != link.find('http')):
        link = str_between(htmlToExplode, '"url":"', '"').replace('\\/', '/')
    else:
        xbmc.log('[%s] %s' % (name, 'reading: link={' + link + '}'), xbmc.LOGNOTICE)
        link = 'http://play.135mov.com/Aliplayer/Aliplayer-ld.php?videourl=' + link
        html = get_link_contents(link)
        if ('' == html):
            return []
        htmlToExplode = str_between(html, 'player =', '</script>')
        link = str_between(htmlToExplode, '"source": "', '"')
    xbmc.log('[%s] %s' % (name, 'playing: link={' + link + '}'), xbmc.LOGNOTICE)
    playitem = xbmcgui.ListItem(path=link)
    playitem.setProperty('inputstreamaddon','inputstream.adaptive')
    playitem.setProperty('inputstream.adaptive.manifest_type','hls')
    playitem.setMimeType('application/vnd.apple.mpegurl')
    playitem.setContentLookup(False)
    xbmcplugin.setResolvedUrl(addon_handle, True, playitem)
# -- 135mov.com --

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
kubo_filter_insert_at = '2020'
kubo_filter_insert_this = '2021'
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
    if ('' == pageInfo):
        pageInfo = '1/1'
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
kubo_episodes_str8 = '<ul id="tabber"'
kubo_episodes_str9 = '</ul>'
kubo_episodes_strA = '<li'
kubo_episodes_strB = '<b>'
kubo_episodes_strC = '</b>'
kubo_episodes_strD = '<ul>'
kubo_episodes_strE = '</ul>'
def kubo_episodes (params):
    name = 'kubo_episodes()'
    xbmc.log('[%s] %s' % (name, 'link={' + params['link'] + '}'), xbmc.LOGNOTICE)
    html = get_link_contents(params['link'])
    if ('' == html):
        return []
    htmlToExplode = str_between(html, kubo_episodes_str8, kubo_episodes_str9)
    fmts = htmlToExplode.split(kubo_episodes_strA)
    fmts.pop(0)
    fmtIndex = 0
    for fmt in fmts:
        title = str_between(fmt, kubo_episodes_strB, kubo_episodes_strC).strip()
        xbmc.log('[%s] %s' % (name, 'fmtIndex={' + str(fmtIndex) + '}' + '; title={' + title + '}'), xbmc.LOGNOTICE)
        if ('FLV66' == title):
            xbmc.log('[%s] %s' % (name, 'if (\'FLV66\' == title):'), xbmc.LOGNOTICE)
            break
        fmtIndex += 1
    if (fmtIndex >= len(fmts)):
        xbmc.log('[%s] %s' % (name, 'if (fmtIndex >= len(fmts)): {' + str(fmtIndex) + '}; {' + str(len(fmts)) + '}'), xbmc.LOGNOTICE)
        htmlToExplode = str_between(html, kubo_episodes_str1, kubo_episodes_str2)
        fmt_title = '預設'
    else:
        xbmc.log('[%s] %s' % (name, 'else: {' + str(fmtIndex) + '}; {' + str(len(fmts)) + '}'), xbmc.LOGNOTICE)
        fmtHTML = html.split(kubo_episodes_str1)
        fmtHTML.pop(0)
        htmlToExplode = str_between(fmtHTML[fmtIndex], kubo_episodes_strD, kubo_episodes_strE)
        fmt_title = title
    videos = htmlToExplode.split(kubo_episodes_str3)
    videos.pop(0)
    items = []
    for video in videos:
        title = fmt_title + ': ' + str_between(video, kubo_episodes_str4, kubo_episodes_str5).strip()
        link = kubo_episodes_URL_prefix + str_between(video, kubo_episodes_str6, kubo_episodes_str7).strip()
        link = build_url_dict({'action': 'kubo_episode', 'link': link})
        items.append({'title': title, 'link': link, 'isFolder': False, 'IsPlayable': 'True'})
    return items

kubo_episode_str1 = 'ff_urls='
kubo_episode_str2 = '"Data'
kubo_episode_str3 = 'http'
kubo_episode_str4 = '.m3u8'
def kubo_episode (params):
    name = 'kubo_episode()'
    link_orig = params['link']
    xbmc.log('[%s] %s' % (name, 'input: link={' + link_orig + '}'), xbmc.LOGNOTICE)
    html = get_link_contents(link_orig)
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



# -----------------------
# ----- ENTRY POINT -----
# -----------------------
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
