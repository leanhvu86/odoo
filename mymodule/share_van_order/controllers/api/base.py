# -*- coding: utf-8 -*-


class BaseApi:

    objType = (list, dict)

    @staticmethod
    def getInstance(model, data):
        instance: dict = {}
        instance = {key: data[key] for key in data.keys() if BaseApi.isPrimitive(data[key])}
        for key in data.keys():
            if BaseApi.isPrimitive(data[key]):
                instance[key] = data[key]
        return instance

    @staticmethod
    def isPrimitive(obj):
        return not isinstance(obj, BaseApi.objType)




