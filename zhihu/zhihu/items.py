# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field


class ZhihuPeopleItem(Item):
    """知乎用户属性

    Attributes:
        nickname 用户名
        zhihu_id 用户id
        location 位置
        business 行业
        gender 性别
        employment 公司
        position 职位
        education 教育情况
        image_url 头像图片url
    """
    nickname = Field()
    zhihu_id = Field()
    location = Field()
    business = Field()
    gender = Field()
    employment = Field()
    position = Field()
    education = Field()
    agree_count = Field()
    thanks_count = Field()
    followee_count = Field()
    follower_count = Field()
    image_url = Field()


class ZhihuRelationItem(Item):
    """知乎用户关系

    Attributes:
        zhihu_id 知乎id
        user_type 用户类型（1我关注的人 2关注我的人）
        user_list 用户列表,id集合

    """
    zhihu_id = Field()
    user_type = Field()
    user_list = Field()
