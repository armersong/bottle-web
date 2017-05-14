# coding:utf-8
'''
Mongodb service client wrapper
'''

import pymongo
import urllib

from bson import ObjectId
from service import Service

__all__ = [ "MongodbService" ]

COND_OP_MAPS=['$ne', '$lt', '$lte', '$gt', '$gte', '$in', '$nin', '$regex']
UPDATE_OP_MAPS=['$set', '$inc', '$push']

class MongodbService(Service):
    """mongodb client service"""
    FIELD_ORDER_ASC = pymongo.ASCENDING
    FIELD_ORDER_DSC = pymongo.DESCENDING

    COND_OP_NOT_EQUAL = 0
    COND_OP_LESS = 1
    COND_OP_LESS_EQUAL = 2
    COND_OP_GREAT = 3
    COND_OP_GREAT_EQUAL = 4
    COND_OP_IN = 5
    COND_OP_NOT_IN = 6
    COND_OP_LIKE = 7
    UPDATE_OP_SET = 0
    UPDATE_OP_INC = 1
    UPDATE_OP_PUSH = 2
    def __init__(self, env, url):
        super(MongodbService, self).__init__(env)
        self._url = url

    def get_connection_info(self):
        return self._url

    def get_connection(self):
        return pymongo.MongoClient(host=self._url)

    def get_collection(self, db_name, collection_name):
        return self.get_connection()[db_name][collection_name]

    def make_cond(self, op, field, value):
        if op == self.COND_OP_LIKE:
            value = '/%s/i' % value
        return {field : {COND_OP_MAPS[op] : value}}

    def make_update(self, op, info):
        return {UPDATE_OP_MAPS[op]: info}

    def make_or_cond(self, conds):
        '''
        :param conds: [ {},{} ]
        :return:
        '''
        return {'$or', conds }

    @classmethod
    def ObjectId(cls, objId):
        return ObjectId(objId)

    @classmethod
    def gen_id(cls):
        return str(ObjectId())