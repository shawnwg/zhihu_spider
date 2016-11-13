# -*- coding=utf8 -*-
import os
import re
import json

from urllib import urlencode
from scrapy import log
from scrapy.spiders import CrawlSpider
from scrapy.selector import Selector
from scrapy.http import Request, FormRequest

from zhihu.items import ZhihuPeopleItem, ZhihuRelationItem
from zhihu.constants import Gender, People, HEADER


class Zhihu2Sipder(CrawlSpider):
    name = "zhihu"
    allowed_domains = ["www.zhihu.com"]
    start_url = "https://www.zhihu.com/people/weizhi-xiazhi"

    def __init__(self, *args, **kwargs):
        super(Zhihu2Sipder, self).__init__(*args, **kwargs)
        #知乎的跨域访问
        self.xsrf = ''

    def start_requests(self):
        """
        登陆页面 获取xrsf
        """
        return [Request(
            "https://www.zhihu.com/#signin",
            meta={'cookiejar': 1},#用于Cookie传递吗？
            callback=self.post_login
        )]

    def post_login(self, response):
        """
        解析登陆页面，发送登陆表单
        """
        self.xsrf = Selector(response).xpath(
            '//input[@name="_xsrf"]/@value'
        ).extract()[0]
        return [FormRequest(
            'https://www.zhihu.com/login/email',
            method='POST',
            meta={'cookiejar': response.meta['cookiejar']},
            formdata={
                '_xsrf': self.xsrf,#将这个值post回去验证
                'email': '793061484@qq.com',
                'password': 'greyireland123',
                'remember_me': 'true'},
            callback=self.after_login
        )]

    def after_login(self, response):
        """
        登陆完成后从第一个用户开始爬数据
        """
        return [Request(
            self.start_url,
            meta={'cookiejar': response.meta['cookiejar']},
            callback=self.parse_people,
            errback=self.parse_err,
        )]

    def parse_people(self, response):
        """
        解析用户主页
        """
        selector = Selector(response)
        nickname=selector.xpath(
            '//div[@class="title-section ellipsis"]/span[@class="name"]/text()'
        ).extract_first()
        zhihu_id=os.path.split(response.url)[-1]
        location=selector.xpath(
            '//span[@class="location item"]/@title'
        ).extract_first()
        business=selector.xpath(
            '//span[@class="business item"]/@title'
        ).extract_first()
        gender = selector.xpath(
            '//span[@class="item gender"]/i/@class'
        ).extract_first()
        if gender is not None:
            gender = Gender.FEMALE if u'female' in gender else Gender.MALE
        employment =selector.xpath(
            '//span[@class="employment item"]/@title'
        ).extract_first()
        position = selector.xpath(
            '//span[@class="position item"]/@title'
        ).extract_first()
        education = selector.xpath(
            '//span[@class="education-extra item"]/@title'
        ).extract_first()
        followee_count, follower_count = tuple(selector.xpath(
            '//div[@class="zm-profile-side-following zg-clear"]/a[@class="item"]/strong/text()'
        ).extract())
        followee_count, follower_count = int(followee_count), int(follower_count)
        image_url = selector.xpath(
            '//div[@class="body clearfix"]/img/@srcset'
        ).extract_first('')[0:-3]

        #这里有两个URL，一个链接到关注我的人，一个链接到我关注的人
        #
        follow_urls = selector.xpath(
            '//div[@class="zm-profile-side-following zg-clear"]/a[@class="item"]/@href'
        ).extract()
        for url in follow_urls:
            #https://www.zhihu.com/people/weizhi-xiazhi/followees
            #https://www.zhihu.com/people/weizhi-xiazhi/followers
            complete_url = 'https://{}{}'.format(self.allowed_domains[0], url)
            #延迟执行或延迟加载？
            yield Request(complete_url,
                          meta={'cookiejar': response.meta['cookiejar']},
                          callback=self.parse_follow,
                          errback=self.parse_err)

        item = ZhihuPeopleItem(
            nickname=nickname,
            zhihu_id=zhihu_id,
            location=location,
            business=business,
            gender=gender,
            employment=employment,
            position=position,
            education=education,
            followee_count=followee_count,
            follower_count=follower_count,
            image_url=image_url,
        )
        yield item
    def parse_followee_and_follower(self, response):
        selector = Selector(response)


    def parse_follow(self, response):
        """
        解析follow数据
        """
        selector = Selector(response)
        #//*[@id="zh-profile-follows-list"]/div/div[1]/div[2]/h2/span/a
        people_links = selector.xpath('//a[@class="zg-link"]/@href').extract()
        people_info = selector.xpath(
            '//span[@class="zm-profile-section-name"]/text()').extract_first()
        #用参数控制显示的人数
        people_param = selector.xpath(
            '//div[@class="zh-general-list clearfix"]/@data-init').extract_first()

        #c=a if a>b else b 简写方式
        re_result = re.search(r'\d+', people_info) if people_info else None
        #关注的人数
        people_count = int(re_result.group()) if re_result else len(people_links)
        if not people_count:
            return
        #Deserialize s (a str or unicode instance containing a JSON document) to a Python object.
        people_param = json.loads(people_param)
        post_url = 'https://{}/node/{}'.format(
            self.allowed_domains[0], people_param['nodename'])

        # 去请求所有的用户数据
        start = 20
        while start < people_count:
            payload = {
                u'method': u'next',
                u'_xsrf': self.xsrf,
                u'params': people_param[u'params']
            }
            payload[u'params'][u'offset'] = start
            payload[u'params'] = json.dumps(payload[u'params'])#Serialize obj to a JSON formatted str.
            HEADER.update({'Referer': response.url})
            start += 20
            #鼠标下拉之后，它自动加载数据
            yield Request(post_url,
                          method='POST',
                          meta={'cookiejar': response.meta['cookiejar']},
                          headers=HEADER,
                          body=urlencode(payload),
                          priority=100,
                          callback=self.parse_post_follow)

        # 请求所有的人
        zhihu_ids = []
        for people_url in people_links:
            zhihu_ids.append(os.path.split(people_url)[-1])
            yield Request(people_url,
                          meta={'cookiejar': response.meta['cookiejar']},
                          callback=self.parse_people,
                          errback=self.parse_err)

        # 返回数据
        url, user_type = os.path.split(response.url)
        user_type = People.Follower if user_type == u'followers' else People.Followee
        item = ZhihuRelationItem(
            zhihu_id=os.path.split(url)[-1],
            user_type=user_type,
            user_list=zhihu_ids
        )
        yield item

    def parse_post_follow(self, response):
        """
        获取动态请求拿到的人员
        """
        body = json.loads(response.body)
        people_divs = body.get('msg', [])

        # 请求所有的人
        zhihu_ids = []
        for div in people_divs:
            selector = Selector(text=div)
            link = selector.xpath('//a[@class="zg-link"]/@href').extract_first()
            if not link:
                continue

            zhihu_ids.append(os.path.split(link)[-1])
            yield Request(link,
                          meta={'cookiejar': response.meta['cookiejar']},
                          callback=self.parse_people,
                          errback=self.parse_err)

        url, user_type = os.path.split(response.request.headers['Referer'])
        user_type = People.Follower if user_type == u'followers' else People.Followee
        zhihu_id = os.path.split(url)[-1]
        yield ZhihuRelationItem(
            zhihu_id=zhihu_id,
            user_type=user_type,
            user_list=zhihu_ids,
        )

    def parse_err(self, response):
        log.ERROR('crawl {} failed'.format(response.url))
