import sys
import scrapy
import base64
import rsa
import time
import re
import binascii
import bs4
import json
from ..items import TestSinaItem
from time import sleep
from ..settings import message
sys.setrecursionlimit(2500) #封印解除！


class sinaWeibo_spider(scrapy.Spider):
    name = 'sina'
    allowed_domain = ['https://weibo.com']
    start_urls = ['https://weibo.com']

    now = time.time()
    now = (int(now * 1000))
    su = base64.b64encode(bytes(message['username'], encoding='utf-8'))
    count = 0
    page_num = 1
    nick_name = []
    id = []
    domain = []

    def start_requests(self):
        try:
            url = 'https://login.sina.com.cn/sso/prelogin.php?entry=weibo&callback=sinaSSOController.preloginCallBack&su=' \
                  '{0}&rsakt=mod&checkpin=1&client=ssologin.js(v1.4.19)&_={1}'.format(self.su,self.now)
            yield scrapy.Request(url,callback=self.rsa_encryption)
        except:
            print('登录超时，位置：get_param')

    def rsa_encryption(self,response):
        try:
            servertime = re.match('.*time":?([\d]+),"pcid', response.text).group(1)
            nonce = re.match('.*nce":"(.*)","pubkey', response.text).group(1)
            pubkey = re.match('.*key":"(.*)","rsakv', response.text).group(1)
            rsa_e = int('10001', 16)  # 0x10001
            pw_string = str(servertime) + '\t' + str(nonce) + '\n' + str(message['password'])
            key = rsa.PublicKey(int(pubkey, 16), rsa_e)
            pw_encypted = rsa.encrypt(pw_string.encode('utf-8'), key)
            password = binascii.b2a_hex(pw_encypted)  # 将二进制编码转化为ascii/hex
            password = str(password, encoding='utf-8')
            data = {
                'entry': 'weibo',
                'gateway': '1',
                'from': 'null',
                'savestate': '0',
                'qrcode_flag': 'false',
                'useticket': '1',
                'pagerefer': 'https://www.baidu.com/link?url=q_xHGEAkSjGBzN_PIVDQ4WbfZZlryEo8qXpz0BtEN8W&wd=&eqid=bdfe64670001b8b9000000065abbb38c',
                'vsnf': '1',
                'su': self.su,
                'service': 'miniblog',
                'servertime': servertime,
                'nonce': nonce,
                'pwencode': 'rsa2',
                'rsakv': '1330428213',
                'sp': password,
                'sr': '1536*864',
                'encoding': 'UTF-8',
                'prelt': '35',
                'url': 'https://weibo.com/ajaxlogin.php?framelogin=1&callback=parent.sinaSSOController.feedBackUrlCallBack',
                'returntype': 'META'
            }
            url = 'https://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.19)'
            yield scrapy.FormRequest(url,formdata=data,callback=self.login_second)
        except:
            print('rsa加密失败，位置：rsa_encryption')

    def login_second(self,response):
        temp = response.body.decode('GBK')
        soup = bs4.BeautifulSoup(temp.split('location.repalce')[0],'html5lib')
        soup = soup.get_text()
        url = soup.split('location.replace')[1].split("('")[1].split("')")[0]
        yield scrapy.Request(url,callback=self.login_third)

    def login_third(self,response):
        url_html = bs4.BeautifulSoup(response.body.decode('gb2312'), 'html5lib')
        url_text = url_html.get_text()
        url_pro = json.loads(url_text.split('(')[1].split(')')[0])
        param = url_pro['userinfo']['userdomain']
        login_url = 'https://weibo.com/{}'.format(param)
        yield scrapy.Request(login_url,callback=self.login_in)

    def login_in(self,response):
        if '我的首页 微博' in response.body.decode('utf-8'):
            print('Login Succesful')
            url = response.urljoin('/{}/follow?rightmod=1&wvr=6'.format(re.match('.*\/u?([\d]+)\/.*',response.url).group(1)))
            yield scrapy.Request(url,callback=self.focus_list)
        else:
            print('登录失败，请重试')

    def focus_list(self,response):
        with open('focus.html', 'wb') as f:
            f.write(response.body)
            f.close()
        pt = re.compile('href=.*(\/.*from=myfollow_all)')
        li = []
        for i in response.text.split('relation_user_list')[1].split('</html>')[0].split('            '):
            lis = pt.findall(i)
            if lis:
                if lis[0] not in li:
                    li.append(lis[0])
        for url in li:
            yield scrapy.Request(response.urljoin(url),callback=self.focus_man)

    def focus_man(self,response):
        param = response.body.decode('utf-8').replace('\n','')
        # with open('focus.text', 'w',encoding='utf-8') as f:  #指定encoding很重要，不然会被系统当做gbk格式写入文件而导致报错
        #     f.write(param)
        #     f.close()
        id = re.match(".*page_id'\]='?([\d]+)'.*",param).group(1)
        domain = re.match(".*domain'\]='?([\d]+)'.*",param).group(1)
        nick_name = re.match(".*onick'\]='([^']+).*",param).group(1)
        print(id,domain,nick_name)
        self.id.append(id)
        self.domain.append(domain)
        self.nick_name.append(nick_name)
        url = 'https://weibo.com/p/aj/v6/mblog/mbloglist?ajwvr=6&domain={0}&is_all=1&profile_ftype=1&page=1&pagebar=0&pre_page=0&id={1}&feed_type=0&domain_op={2}'
        yield scrapy.Request(url.format(domain,id,domain),meta={'nick_name':nick_name,'id':id,'domain':domain},callback=self.next_page)

    def next_page(self,response):
        # page = response.body.decode('unicode_escape')
        # with open('page.json','w',encoding='utf-8') as f:
        #     f.write(page)
        #     f.close()
        page = response.body.decode('unicode_escape').split('WB_from S_txt2">')
        for i in page:
            a = '.*nick-name="{}">\n(.*)div.*'.format(response.meta['nick_name'])
            c = '.*list_content" >\n(.*)div.*'
            d = '.*_list_reason">\n(.*)div.*'
            content = re.findall(a,i)
            _content = re.findall(c,i)
            content_ = re.findall(d,i)
            if content:
                item = TestSinaItem()
                k = bs4.BeautifulSoup(i)
                time = k.a['title']
                url = 'https://weibo.com' + k.a['href'].replace('\\', '')
                content = bs4.BeautifulSoup(content[0]).get_text()
                item['name'] = response.meta['nick_name']
                item['id'] = response.meta['id']
                item['original_content'] = content
                item['reprinted_content'] = ' '
                item['reprinted_reason'] = ' '
                item['publish_time'] = time
                item['url'] = url
                yield item

            if _content and content_:
                item = TestSinaItem()
                k = bs4.BeautifulSoup(i)
                time = k.a['title']
                url = 'https://weibo.com'+k.a['href'].replace('\\','')
                _content = bs4.BeautifulSoup(_content[0]).get_text()
                content_ = bs4.BeautifulSoup(content_[0]).get_text()
                item['name'] = response.meta['nick_name']
                item['id'] = response.meta['id']
                item['original_content'] = ' '
                item['reprinted_content'] = _content
                item['reprinted_reason'] = content_
                item['publish_time'] = time
                item['url'] = url
                yield item

        if '正在加载中，请稍候...' in response.body.decode('unicode_escape') and 'pagebar=0&pre_page=0' in response.url:
            url = 'https://weibo.com/p/aj/v6/mblog/mbloglist?ajwvr=6&domain={0}&is_all=1&profile_ftype=1&page={1}&pagebar=0&pre_page={2}&id={3}&feed_type=0&domain_op={4}'
            yield scrapy.Request(url.format(response.meta['domain'],self.page_num,self.page_num,response.meta['id'],response.meta['domain']),
                                 meta={'nick_name':response.meta['nick_name'],'id':response.meta['id'],'domain':response.meta['domain']},dont_filter=True,
                                 callback=self.next_page)

        if '正在加载中，请稍候...' in response.body.decode('unicode_escape') and 'pagebar=0&pre_page={}'.format(self.page_num) in response.url:
            url = 'https://weibo.com/p/aj/v6/mblog/mbloglist?ajwvr=6&domain={0}&is_all=1&profile_ftype=1&page={1}&pagebar=1&pre_page={2}&id={3}&feed_type=0&domain_op={4}'
            yield scrapy.Request(url.format(response.meta['domain'], self.page_num, self.page_num, response.meta['id'],response.meta['domain']),
                                 meta={'nick_name': response.meta['nick_name'], 'id': response.meta['id'],'domain': response.meta['domain']},dont_filter=True,
                                 callback=self.next_page)

        if '下一页' in response.body.decode('unicode_escape') and 'pagebar=1&pre_page={}'.format(self.page_num) in response.url:
            self.page_num += 1
            url = 'https://weibo.com/p/aj/v6/mblog/mbloglist?ajwvr=6&domain={0}&is_all=1&profile_ftype=1&page={1}&pagebar=0&pre_page=0&id={3}&feed_type=0&domain_op={4}'
            yield scrapy.Request(url.format(response.meta['domain'], self.page_num, self.page_num, response.meta['id'],response.meta['domain']),
                                 meta={'nick_name': response.meta['nick_name'], 'id': response.meta['id'],'domain': response.meta['domain']},dont_filter=True,
                                 callback=self.next_page)

        if '下一页' not in response.body.decode('unicode_escape') and '正在加载中，请稍候...' not in response.body.decode('unicode_escape'):
            self.page_num = 1
            print('已进入微博跳转')
            i = ''
            j = ''
            index = ''
            for a,b in zip(self.id,self.nick_name):
                if a == response.meta['id'] and b == response.meta['nick_name']:
                    index = self.id.index(a)
                    i = a
                    j = b
                    break
            self.id.remove(i)
            self.nick_name.remove(j)
            self.domain.pop(index)
            print('已清除抓取完毕用户',j)
            print('尚未抓取完毕的用户：',self.nick_name)
            if len(self.id) == 0:
                print('抓取结束')
                pass
            else:
                url = 'https://weibo.com/p/aj/v6/mblog/mbloglist?ajwvr=6&domain={0}&is_all=1&profile_ftype=1&page=1&pagebar=0&pre_page=0&id={1}&feed_type=0&domain_op={2}'
                print('准备抓取下一用户')
                sleep(2)
                yield scrapy.Request(url.format(self.domain[0],self.id[0],self.domain[0]),
                                     meta={'nick_name': self.nick_name[0], 'id': self.id[0],'domain': self.domain[0]},dont_filter=True,callback=self.next_page)
