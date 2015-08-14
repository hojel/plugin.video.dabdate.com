# -*- coding: utf-8 -*-
import urllib, urllib2
import cookielib
import os
import re
import json

root_url = "http://www.dabdate.com"

BrowserAgent = 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0)'
PlayerAgent  = 'Windows-Media-Player/12.0.7601.17514'

# http://www.dabdate.com
def parseTop( main_url, quality='1', localsrv='la'):
    result = {'video':[]}
    req = urllib2.Request(main_url)
    req.add_header('User-Agent', BrowserAgent)
    psrc = urllib2.urlopen(req).read().decode('euc-kr')
    # item list
    items = re.split("<td colspan=\d+ height=\d+>", psrc)
    for item in items[:-1]:
        is_free = False
        try:
            title = re.compile('''<a href[^>]*pr=1"><span [^>]*>(.*?)</span></a>''').search(item).group(1)
            title = re.compile("</?b>").sub("",title)
            if re.compile('<b>[^<]*Free').search(item):
                is_free = True
        except:
            continue

        img = ''
        match = re.compile('''<img src='([^']*)' ''').search(item)
        if match:
            img = match.group(1)

        match = re.compile("<a href='([^']*&pr={0:s}&local={1:s})'>".format(quality, localsrv)).search(item)
        if match:
            vurl = match.group(1)
            result['video'].append({'title':title, 'url':vurl, 'thumb':img, 'free':is_free})
        else:
            print "Video, {0:s}, doesn't exist on {1:s} server".format(title, quality)

    # navigation
    query = re.compile("<a href='([^']*)' class=navi>\[Prev\]</a>").search(psrc)
    if query:
        result['prevpage'] = query.group(1)
    query = re.compile("<a href='([^']*)' class=navi>\[Next\]</a>").search(psrc)
    if query:
        result['nextpage'] = query.group(1)
    return result

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
    psrc = resp.read().decode('euc-kr', 'ignore')
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
    print getStreamUrl( root_url+"/player.php?idx=30828&pr=1" )

# vim:sw=4:sts=4:et
