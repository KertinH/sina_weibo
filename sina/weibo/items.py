# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class TestSinaItem(scrapy.Item):
    # define the fields for your item here like:
    name = scrapy.Field()
    id = scrapy.Field()
    original_content = scrapy.Field()
    reprinted_content = scrapy.Field()
    reprinted_reason = scrapy.Field()
    publish_time = scrapy.Field()
    url = scrapy.Field()

    def insert(self):
        insert = '''
            insert into sina_weibo(nick_name,id,original_content,reprinted_content,reprinted_reason,publish_time,url)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
        '''
        param = (self['name'],self['id'],self['original_content'],self['reprinted_content'],self['reprinted_reason'],self['publish_time'],self['url'])
        return insert,param
    pass
