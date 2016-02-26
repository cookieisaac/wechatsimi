import logging
import ssl
import re
import time
import os
import xml.dom.minidom
import json
import requests
try:
    from urllib import urlencode, quote_plus
    from cookielib import CookieJar
except ImportError:
    from urllib.parse import urlencode, quote_plus
    from http.cookiejar import CookieJar
    
try:
    import urllib2 as urllib
except ImportError:
    import urllib.request as urllib


uuid = '' #declare uuid as a global variable
tip = 1 #whether the qr is scanned(0) or not(1)
baseuri = ''
redirecturi = ''
push_uri = ''

skey = ''
wxsid = ''
wxuin = ''
pass_ticket = ''
deviceId = 'e000000000000000'

BaseRequest = {}
ContactList = []
My = []
SyncKey = []

QRImagePath = os.path.join(os.getcwd(), 'qrcode'+str(time.time())+'.jpg')
    
def configure_logger():
    FORMAT = '[%(asctime)-15s][%(process)d][%(name)s][%(levelname)s][%(message)s]'
    logging.basicConfig(format=FORMAT, level=logging.DEBUG, filename='WechatSimi.log')
    logger = logging.getLogger()


def syncKey():
    SyncKeyItems = ['%s_%s' % (item['Key'], item['Val'])
                    for item in SyncKey['List']] #SyncKey is set in initWebWechat
    SyncKeyStr = '|'.join(SyncKeyItems)
    return SyncKeyStr
    
def syncCheck():
    url = push_uri + '/synccheck?'
    params = {
        'skey': BaseRequest['Skey'],
        'sid': BaseRequest['Sid'],
        'uin': BaseRequest['Uin'],
        'deviceId': BaseRequest['DeviceID'],
        'synckey': syncKey(),
        'r': int(time.time()),
    }
    request = getRequest(url=url + urlencode(params))
    response = urllib.urlopen(request)
    data = response.read().decode('utf-8', 'replace')
    logging.debug("Data received in syncCheck: " + data)
    
    regx = r'window.synccheck={retcode:"(\d+)",selector:"(\d+)"}'
    match = re.search(regx, data)

    retcode = match.group(1)
    selector = match.group(2)
    
    return selector
    
def syncWebWechat():
    global SyncKey
    url = base_uri + '/webwxsync?lang=zh_CN&skey=%s&sid=%s&pass_ticket=%s' % (
        BaseRequest['Skey'], BaseRequest['Sid'], quote_plus(pass_ticket))
    params = {
        'BaseRequest': BaseRequest,
        'SyncKey': SyncKey,
        'rr': ~int(time.time()),
    }
    request = getRequest(url=url, data=json.dumps(params))
    request.add_header('ContentType', 'application/json; charset=UTF-8')
    response = urllib.urlopen(request)
    data = response.read().decode('utf-8', 'replace')
    logging.debug("Data received in syncWebWechat: " + data)
    
    dict = json.loads(data)
    SyncKey = dict['SyncKey']

    ErrMsg = dict['BaseResponse']['ErrMsg']
    Ret = dict['BaseResponse']['Ret']
    logging.debug('synWebWechat: Ret: %d, ErrMsg: %s' % (Ret, ErrMsg))

    return dict
    
def heartBeatLoop():
    logging.info('Start heart beat loop...')
    while True:
        selector = syncCheck()
        if selector == '2': #New Message
            result = syncWebWechat()
            if result:
                handleMessage(result)
        else:
            time.sleep(1)
            

def getUserRemarkName(self, id):
        return "test"
        
        name = 'Unknown group' if id[:2] == '@@' else 'Stranger'
        
        if id == My['UserName']: return My['NickName']  #Self

        if id[:2] == '@@':
            # group
            name = getGroupName(id) 
        else:
            for member in SpecialUsersList:
                if member['UserName'] == id:
                    name = member['RemarkName'] if member['RemarkName'] else member['NickName']
            # Public User
            for member in PublicUsersList:
                if member['UserName'] == id:
                    name = member['RemarkName'] if member['RemarkName'] else member['NickName']

            # Contact List
            for member in self.ContactList:
                if member['UserName'] == id:
                    name = member['RemarkName'] if member['RemarkName'] else member['NickName']
            # Group Member List
            for member in self.GroupMemeberList:
                if member['UserName'] == id:
                    name = member['DisplayName'] if member['DisplayName'] else member['NickName']

        if name == 'Unknown group' or name == 'Stranger': 
            logging.debug("Cannot resolve the following id: " + id)
            
        return name
            
def handleMessage(messageDict):
    logging.debug('handleMessage is processing the following dictionary: ' + str(messageDict))
    for msg in r['AddMsgList']:
        print ('New Message Received!')
        msgType = msg['MsgType']
        name = getUserRemarkName(msg['FromUserName'])
        content =  msg['Content'].replace('&lt;','<').replace('&gt;','>')
        msgId = msg['MsgId']
        
        if msgType == 1:
            raw_msg = {'raw_msg': msg}
            print ('Received msg %s from user %s' % (raw_msg, name))
    

def getRequest(url, data=None):
    try:
        data = data.encode('utf-8')
    except:
        pass
    finally:
        return urllib.Request(url=url, data=data)
        

    
def getUUID():
    global uuid
    
    logging.info("Retrieving UUID...")
    url = 'https://login.weixin.qq.com/jslogin'
    params = {
        'appid': 'wx782c26e4c19acffb', #application ID of WebWechat
        'fun': 'new', #function type
        'lang': 'zh_CN', #language
        '_': int(time.time()), #timestamp
    }
    
    request = getRequest(url=url, data=urlencode(params))
    logging.debug("URL is " + url + " and params is " + str(params))
    response = urllib.urlopen(request)
    data = response.read().decode('utf-8', 'replace')
    logging.debug("Data received in getUUID response: " + data)
    # Parse the return data
    # window.QRLogin.code = 200; window.QRLogin.uuid = "oZwt_bFfRg==";
    regx = r'window.QRLogin.code = (\d+); window.QRLogin.uuid = "(\S+?)"'
    
    match = re.search(regx, data)
    if not match:
        logging.warning('Cannot parse the return data with following pattern: ' + regx)
        raise Exception('No code and uuid can be parsed')
    else:
        code = match.group(1)
        uuid = match.group(2)
        logging.debug("Return code is " + str(code) + " and uuid is " + str(uuid))
        
        if code == '200':
            return True
        else:
            return False
        
def showQRCode():
    
    #Generate QR code
    url = 'https://login.weixin.qq.com/qrcode/' + uuid
    params = {
        't':'webwx',
        '_': int(time.time()),
    }
    request = getRequest(url=url, data=urlencode(params))
    response = urllib.urlopen(request)
    
    global tip
    tip = 1
    
    try:
        with open(QRImagePath, 'wb') as fp:
            fp.write(response.read())
        logging.info('QRImage is saved at ' + QRImagePath)
        print ('Please scan QR code to login: ' + QRImagePath)
    except Exception as e:
        raise e
        
def waitForLogin():
    global tip, base_uri, redirect_uri, push_uri
    url = 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?tip=%s&uuid=%s&_=%s' % (
        tip, uuid, int(time.time()))
    request = getRequest(url=url)
    response = urllib.urlopen(request)
    data = response.read().decode('utf-8','replace')
    logging.debug('Data retrieved from waitForLogin request: ' + str(data))
    
    regx = r'window.code=(\d+);'
    match = re.search(regx, data)
    if not match:
        logging.warning('Cannot parse the return data with following pattern: ' + regx)
        raise Exception('No code and uuid can be parsed')
    else:
        code = match.group(1)
        logging.debug("Return code is " + str(code))
        
        if code == '201': #Scanned
            print('Success! Please confirm on your phone to login')
            tip = 0
        elif code == '200': #Logged in
            print('Logging in...')
            regx = r'window.redirect_uri="(\S+?)";'
            match = re.search(regx, data)
            redirect_uri = match.group(1) + '&fun=new'
            base_uri = redirect_uri[:redirect_uri.rfind('/')]
            
            # Mapping between push_uri and base_uri
            services = [
                ('wx2.qq.com', 'webpush2.weixin.qq.com'),
                ('qq.com', 'webpush.weixin.qq.com'),
                ('web1.wechat.com', 'webpush1.wechat.com'),
                ('web2.wechat.com', 'webpush2.wechat.com'),
                ('wechat.com', 'webpush.wechat.com'),
                ('web1.wechatapp.com', 'webpush1.wechatapp.com'),
            ]
            push_uri = baseuri
            for (searchUrl, pushUrl) in services:
                if base_uri.find(searchUrl) >= 0:
                    push_uri = 'https://%s/cgi-bin/mmwebwx-bin' % pushUrl
                    break            
        elif code == '408': #Timeout
            print ('Timeout, during login...')
            
        return code
    
def loginWechat():
    global skey, wxsid, wxuin, pass_ticket, BaseRequest
    request = getRequest(url=redirect_uri)
    response = urllib.urlopen(request)
    data = response.read().decode('utf-8', 'replace')
    logging.debug('Data retrieved from login request: ' + str(data))
    
    doc = xml.dom.minidom.parseString(data)
    root = doc.documentElement
    
    for node in root.childNodes:
        if node.nodeName == 'skey':
            skey = node.childNodes[0].data
        elif node.nodeName == 'wxsid':
            wxsid = node.childNodes[0].data
        elif node.nodeName == 'wxuin':
            wxuin = node.childNodes[0].data
        elif node.nodeName == 'pass_ticket':
            pass_ticket = node.childNodes[0].data
            
    logging.debug('skey: %s, wxsid: %s, wxuin: %s, pass_ticket: %s' % (skey, wxsid,
                   wxuin, pass_ticket))
                   
    if not all((skey, wxsid, wxuin, pass_ticket)):
        return False
        
    BaseRequest = {
        'Uin': int(wxuin),
        'Sid': wxsid,
        'Skey': skey,
        'DeviceID': deviceId,
    }

    return True
    
    
def initWebWechat():
    print ('Initializing Web Wechat...')
    logging.info('Start to init web wechat')
    url = base_uri + \
        '/webwxinit?pass_ticket=%s&skey=%s&r=%s' % (
            pass_ticket, skey, int(time.time())
        )    
    params = {
        'BaseRequest': BaseRequest
    }

    request = getRequest(url=url, data=json.dumps(params))
    request.add_header('ContentType', 'application/json; charset=UTF-8')
    response = urllib.urlopen(request)
    data = response.read()
    data = data.decode('utf-8', 'replace')
    dict = json.loads(data)
    logging.debug('Data retrieved from initWebWechat request: ' + str(dict))
    
    global ContactList, My, SyncKey
    ContactList = dict['ContactList']
    My = dict['User']
    SyncKey = dict['SyncKey']

    ErrMsg = dict['BaseResponse']['ErrMsg']
    Ret = dict['BaseResponse']['Ret']
    logging.debug('synWebWechat: Ret: %d, ErrMsg: %s' % (Ret, ErrMsg))

    state = (Ret == 0)
    return state

def getSimiReply(text):
    key="89406ec6-3acb-4e04-ae7f-f00b32289e9f" #Valid for 7 days
    url='http://sandbox.api.simsimi.com/request.p?key=%s&lc=ch&ft=0.0&text=%s'%(key, text)
    try:
        r=requests.get(url)
        data = r.json()
        logging.debug("Return result for text "+text+" is " + data)
        if data['result'] == 100:
            return data['response']
        else:
            return "Hehe, I need to go take a shower now"
    except Exception as e:
        loggine.error("Exception occurs during simi reply " + e)
        return "That's interesting"
    
def main():
    configure_logger()
    logging.info('Start logging...')
    
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
        opener = urllib.build_opener(urllib.HTTPCookieProcessor(CookieJar()))
        opener.addheaders = [
            ('User-agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.125 Safari/537.36')]
        urllib.install_opener(opener)
    except Exception as e:
        logging.warning("Exception found during Opener construction: " + str(e))
        return
        
    if not getUUID():
        logging.error("Getting UUID failed...")
        return
   
    print('Retrieving QR code...')
    showQRCode()
    time.sleep(1)
    
    while waitForLogin() != '200':
        pass
    
    if not loginWechat():
        logging.error('Fail to login to Web Wechat....')
        return
        
    if not initWebWechat():
        logging.error("Initializing Web Wechat failed...")
        return
    
    print('Start heart beat loop')
    thread.start_new_thread(heartBeatLoop, ())
    
    MemberList = getContactFromWebWechat()
    print('You have %s friends in contact list' % len(MemberList))
    
    
    
    

if __name__ == '__main__':
    main()