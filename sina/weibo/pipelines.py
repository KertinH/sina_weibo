# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.htmlfrom twisted.enterprise import adbapi
from .settings import MYSQL_HOST,MYSQL_DBNAME,MYSQL_USER,MYSQL_PASSWORD
from twisted.enterprise import adbapi
import MySQLdb
import MySQLdb.cursors


class TestSinaPipeline(object):
    def __init__(self):
        '''传递settings中设置的数据库参数
           并初始化配置'''
        db_parameters = dict(
                    host = MYSQL_HOST,
                    db = MYSQL_DBNAME,
                    user = MYSQL_USER,
                    password = MYSQL_PASSWORD,
                    charset = 'utf8',
                    cursorclass=MySQLdb.cursors.DictCursor,
                    use_unicode = True
        )
        self.db_pool = adbapi.ConnectionPool('MySQLdb',**db_parameters)

    def process_item(self,item,spider):
        '''使用twisted将数据插入变为异步执行'''
        query = self.db_pool.runInteraction(self.insert,item)
        query.addErrback(self.handle_error) #异常处理

    def handle_error(self,failure):
        print(failure)

    def insert(self,cursor,item):
        '''执行插入语句'''
        insert_sql,param = item.insert()
        cursor.execute(insert_sql,param)
