#-*- coding:utf-8 -*-
import requests
import json
import pandas as pd
import re
import pymongo
from multiprocessing import Pool
#建立数据库以及表的连接
client = pymongo.MongoClient('localhost',27017)
music = client.music
s_list_id = music.s_list_id
s_list_song = music.s_list_song
music_detail = music.music_detail

#获取歌词内容
def getLyric(musicid,songmid):
    url = 'https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric.fcg'
    header = {
        'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36',
        'referer':'https://y.qq.com/n/yqq/song/{}.html'.format(songmid)
    }
    paramters = {
        'nobase64':1,
        'musicid':musicid, #传入之前获取到的id
        'callback':'jsonp1',
        'g_tk':'1134533366',
        'jsonpCallback':'jsonp1',
        'loginUin':'0',
        'hostUin':'0',
        'format':'jsonp',
        'inCharset':'utf8',
        'outCharset':'utf-8',
        'notice':'0',
        'platform':'yqq',
        'needNewCode':'0'
    }
    html = requests.get(url=url,params=paramters,headers=header)
    res = json.loads(html.text.lstrip('jsonp1(').rstrip(')'))
    #由于一部分歌曲是没有上传歌词，因此没有默认为空
    if res.has_key('lyric'):
        lyric = json.loads(html.text.lstrip('jsonp1(').rstrip(')'))['lyric']
        #对歌词内容做稍微清洗
        dr1 = re.compile(r'&#\d.;',re.S)
        dr2 = re.compile(r'\[\d+\]',re.S)
        dd = dr1.sub(r'',lyric)
        dd = dr2.sub(r'\n',dd).replace('\n\n','\n')
        return dd
    else:
        return ""

#获取歌曲详细信息
def getDetail(songid,songmid):
    spp = ['c.y.qq.com','59.37.96.220','101.227.139.217','59.37.96.220','59.37.96.220']
    url = 'https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg'
    sp = ['103.18.209.26','y.qq.com','103.18.209.25','106.38.181.141','180.153.105.167']
    header = {
        'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36',
        'referer':'https://y.qq.com/n/yqq/song/{}.html'.format(songid)
    }
    paramters = {
        'songmid':songmid,
        'tpl':'yqq_song_detail',
        'format':'jsonp',
        'callback':'getOneSongInfoCallback',
        'g_tk':'1134533366',
        'jsonpCallback':'getOneSongInfoCallback',
        'loginUin':'0',
        'hostUin':'0',
        'inCharset':'utf8',
        'outCharset':'utf-8',
        'notice':0,
        'platform':'yqq',
        'needNewCode':0
    }
    #html = requests.get(url=url,params=paramters,headers=header,proxies=getProxies("HOOF09GO4963E22D","7ED29B96EFC8AA19"))
    html = requests.get(url=url,params=paramters,headers=header,verify=True)
    detail = json.loads(html.text.lstrip('getOneSongInfoCallback(').rstrip(')'))['data']
    data = {}
    if len(detail)>0:
        detail = detail[0]
        data['subtitle'] = detail['subtitle']
        data['title'] = detail['title']
        data['time_public'] = detail['time_public']
        try:
            data['url'] = json.loads(html.text.lstrip('getOneSongInfoCallback(').rstrip(')'))['url'][str(songid)]
        except:
            data['url'] = ""
    return data

#爬取并且存入MongoDB数据库
def insertDetail(item):
    if item.has_key('songmid'):
        lyric = getLyric(item['songid'],item['songmid']).encode('utf-8')
        s_detail = getDetail(item['songid'],item['songmid'])
        s_detail['lyric'] = lyric
        s_detail['singer'] = item['singer']
        s_detail['tags'] = item['tags']
        s_detail['size128'] = item['size128']
        s_detail['albumname'] = item['albumname']
        s_detail['songname'] = item['songname']
        music_detail.insert_one(s_detail)
    else:
        print '...'

if __name__ == "__main__":
    #开启4进程爬取
    pool  = Pool(4)
    #为了防止爬取中途停止，设置记录数
    count = 0
    while True:
        try:
            print count
            #以每次100个的数量从数据表拿出来
            data = s_list_song.find({},{'_id':0}).skip(count).limit(100)
            pool.map(insertDetail,data)
            count = count + 100
        except:
            continue
