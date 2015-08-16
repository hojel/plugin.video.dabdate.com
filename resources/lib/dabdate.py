# -*- coding: utf-8 -*-
import urllib, urllib2
import cookielib
import os
import re
from bs4 import BeautifulSoup
import json

root_url = "http://www.dabdate.com"
RE_VIDEO_ID  = re.compile('idx=(\d+)')
RE_VIDEO_ID2 = re.compile('thumb/df_(\d+)\.jpg')
VIDEO_URL    = "/player.php?idx={vid:s}&pr={qual:s}&local={local:s}"

###------ direct video link
VIDEO_MAP_TABLE  = "vidmap.json"
DIRECT_URL       = "http://vod{host:d}.dabdate.com/video2/{name:s}{mon:02d}{date:02d}-{bitrate:d}.mp4?@"
RE_DATE          = re.compile('(.*) \d{4},(\d{2}),(\d{2})')
RE_EPISODE       = re.compile(u'(.*) (\d+|최종)회 *$')
RE_SUBTITLE      = re.compile('(.+\S)\((.+?)\) *$')

HOST_MAP = {
    'au1' : 48,   # au(medium)
    'au2' : 48,   # au(low)
    'eu1' : 33,   # eu(medium)
    'eu2' : 34,   # eu(low)
    'sa1' : 53,   # sa(medium)
    'sa2' : 54,   # sa(low)
    'la1' : 30,   # la(medium)
    'la2' : 31,   # la(low)
    'ny1' : 53,   # ny(medium)
    'ny2' : 55,   # ny(low)
}
BITRATE_MAP = {
    '1' : 640,    # medium
    '2' : 320,    # low
}

BrowserAgent = 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0)'
PlayerAgent  = 'Windows-Media-Player/12.0.7601.17514'

def parseTop( main_url, quality='1', localsrv='la'):
    result = {'video':[]}
    req = urllib2.Request(main_url)
    req.add_header('User-Agent', BrowserAgent)
    html = urllib2.urlopen(req).read()
    # item list
    soup = BeautifulSoup(html, from_encoding="cp949")
    for title_node in soup.findAll("b", {"class":"big"}):
        node = title_node.findParent("tr").findParent("tr")
        title = title_node.string
        thumb = node.find("img")["src"]
        #video_id = RE_VIDEO_ID.search(node.find('a')['href']).group(1)
        video_id = RE_VIDEO_ID2.search(thumb).group(1)
        video_url = VIDEO_URL.format(vid=video_id, qual=quality, local=localsrv)
        is_free = True if node.find("img", {"src": "/image/ico_free.gif"}) else False
        result['video'].append({'title':title, 'url':video_url, 'thumb':thumb, 'free':is_free})

    # navigation
    query = re.compile("<a href='([^']*)' class=navi>\[Prev\]</a>").search(html)
    if query:
        result['prevpage'] = query.group(1)
    query = re.compile("<a href='([^']*)' class=navi>\[Next\]</a>").search(html)
    if query:
        result['nextpage'] = query.group(1)
    return result

def getDirectUrl( vidmap, title, quality='1', localsrv='la' ):
    match = RE_DATE.search(title)
    title2, mon, dt = match.group(1,2,3) if match else ('unknown','13','13')
    match = RE_EPISODE.match(title2)
    if match: title2 = match.group(1)
    else:
        match = RE_SUBTITLE.match(title2)
        if match: title2 = match.group(1)

    if title2 in vidmap:
        return DIRECT_URL.format(host=HOST_MAP[localsrv+quality],
                                 name=vidmap[title2],
                                 mon=int(mon),
                                 date=int(dt),
                                 bitrate=BITRATE_MAP[quality])
    return None

def getStreamUrl( main_url, userid='', passwd='', cookiefile='cookie.lwp'):
    # 1. load cookie
    cj = cookielib.LWPCookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    urllib2.install_opener(opener)
    if os.path.isfile(cookiefile):
        cj.load(cookiefile)
        print "Cookie is loaded from "+cookiefile
    req = urllib2.Request(main_url)
    req.add_header('User-Agent', BrowserAgent)
    req.add_header('Referer', root_url)
    resp = urllib2.urlopen(req)
    newurl = resp.geturl()
    # 2. login page
    if 'login.php' in newurl:
        resp.close()
        if userid == '' or passwd == '':
            raise Exception('LoginRequired', newurl)
        values = {
            'mode':'login',
            'url' :main_url,
            'id'  :userid,
            'pass':passwd
        }
        # login
        req = urllib2.Request( root_url+'/login.php', urllib.urlencode(values) )
        req.add_header('User-Agent', BrowserAgent)
        req.add_header('Referer', newurl)
        resp = urllib2.urlopen(req)
        newurl = resp.geturl()
        if newurl.startswith('/'):
            newurl = root_url+newurl
        cj.save(cookiefile)
        print "LOGIN to "+newurl
        if 'login.php' in newurl:
            print "Login failed, "+newurl
            raise Exception('LoginFailed', newurl)
    # 3. accept payment
    if 'msg.php' in newurl:
        resp.close()
        values = {
            'mode':'auto',
            'mno' :'',
            'url' :main_url,
            'auto':'0'
        }
        req = urllib2.Request( root_url+'/msg.php', urllib.urlencode(values) )
        req.add_header('User-Agent', BrowserAgent)
        req.add_header('Referer', newurl)
        resp = urllib2.urlopen(req)
        newurl = resp.geturl()
        if newurl.startswith('/'):
            newurl = root_url+newurl
        cj.save(cookiefile)
        print "PAY to "+newurl
    if not newurl.startswith(main_url):
        print "Payment failed, "+newurl
        raise Exception('NotEnoughToken', newurl)
    # 4. video page
    psrc = resp.read().decode('cp949', 'ignore')
    resp.close()
    data = re.compile('data: *"([^"]*)"').search( psrc ).group(1)
    jstr = urllib2.urlopen(root_url+'/player.php', data).read()
    jobj = json.loads(jstr)
    vurl = jobj['fn']
    vtitle = re.compile("<font class=big>(.*?)</font>", re.U).search( psrc ).group(1)
    cookies = []
    for cookie in cj:
        cookies.append( cookie.name+'='+cookie.value )
    ckStr = ';'.join(cookies)
    return {'title':vtitle, 'url':vurl, 'useragent':PlayerAgent, 'cookie':ckStr}

if __name__ == "__main__":
    print parseTop( root_url )
    print parseTop( root_url+"/index.php?page=2&lang=0" )
    print getStreamUrl( root_url+"/player.php?idx=46687&pr=1&local=la" )
    vidmap = json.load(open(VIDEO_MAP_TABLE))
    print getDirectUrl( vidmap, u"삼시세끼 정선편 2015,08,14" ) 

# vim:sw=4:sts=4:et
