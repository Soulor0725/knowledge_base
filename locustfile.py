#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Echo 知识库系统 - Locust 性能测试
模拟用户并发操作，测试系统吞吐量
"""
import random
import string
from locust import HttpUser, task, between, tag

API_URL = '/api'

def random_str(min_len=3, max_len=8):
    return ''.join(random.choices(string.ascii_lowercase, k=random.randint(min_len, max_len)))


class EchoUser(HttpUser):
    wait_time = between(1, 3)
    token = None
    headers = {}
    username = None
    password = None
    article_ids = []
    expense_ids = []
    overtime_ids = []
    kiwi_ids = []

    def on_start(self):
        """每个用户启动时注册并登录"""
        self.username = f'perf_{random_str()}_{random.randint(10000, 99999)}'
        self.password = 'PerfTest' + str(random.randint(100, 999))

        # 注册
        resp = self.client.post(f'{API_URL}/auth/register', json={
            'username': self.username,
            'password': self.password,
            'name': f'性能测试_{self.username}'
        })
        if resp.status_code == 201:
            data = resp.json()
            self.token = data['token']
            self.headers = {'Authorization': f'Bearer {self.token}'}
        else:
            # 重试登录（可能已存在）
            resp = self.client.post(f'{API_URL}/auth/login', json={
                'username': self.username,
                'password': self.password
            })
            if resp.status_code == 200:
                self.token = resp.json()['token']
                self.headers = {'Authorization': f'Bearer {self.token}'}

    # ---- 认证接口 ----
    @tag('auth')
    @task(1)
    def get_profile(self):
        self.client.get(f'{API_URL}/auth/me', headers=self.headers)

    # ---- 文章接口 ----
    @tag('articles')
    @task(3)
    def list_articles(self):
        self.client.get(f'{API_URL}/articles', headers=self.headers)

    @tag('articles')
    @task(2)
    def create_article(self):
        title = f'性能测试文章_{random_str()}'
        resp = self.client.post(f'{API_URL}/articles', headers=self.headers, json={
            'title': title,
            'content': f'## {title}\n这是性能测试生成的内容',
            'category': '技术',
            'tags': 'perf,test'
        }, name='/api/articles [POST]')
        if resp.status_code == 201:
            self.article_ids.append(resp.json()['id'])

    @tag('articles')
    @task(1)
    def get_article_detail(self):
        if self.article_ids:
            aid = random.choice(self.article_ids)
            self.client.get(f'{API_URL}/articles/{aid}', headers=self.headers,
                          name='/api/articles/[id] [GET]')

    @tag('articles')
    @task(1)
    def search_articles(self):
        self.client.get(f'{API_URL}/articles?search=性能', headers=self.headers,
                      name='/api/articles?search')

    # ---- 消费接口 ----
    CATEGORIES = ['餐饮', '交通', '购物', '娱乐', '住房', '医疗', '教育', '其他']

    @tag('expenses')
    @task(2)
    def list_expenses(self):
        self.client.get(f'{API_URL}/expenses', headers=self.headers)

    @tag('expenses')
    @task(2)
    def create_expense(self):
        cat = random.choice(self.CATEGORIES)
        resp = self.client.post(f'{API_URL}/expenses', headers=self.headers, json={
            'category': cat,
            'amount': round(random.uniform(10, 500), 2),
            'remark': f'perf_{random_str()}',
            'date': '2026-07-07'
        }, name='/api/expenses [POST]')
        if resp.status_code == 201:
            self.expense_ids.append(resp.json()['id'])

    @tag('expenses')
    @task(1)
    def expense_stats(self):
        self.client.get(f'{API_URL}/expenses/stats?year=2026', headers=self.headers,
                      name='/api/expenses/stats')

    # ---- 加班接口 ----
    @tag('overtime')
    @task(1)
    def list_overtime(self):
        self.client.get(f'{API_URL}/overtime', headers=self.headers)

    @tag('overtime')
    @task(1)
    def create_overtime(self):
        resp = self.client.post(f'{API_URL}/overtime', headers=self.headers, json={
            'overtime_type': 'weekday',
            'date': '2026-07-07',
            'start_time': '19:00',
            'end_time': '21:00',
            'remark': f'perf_{random_str()}'
        }, name='/api/overtime [POST]')

    @tag('overtime')
    @task(1)
    def overtime_stats(self):
        self.client.get(f'{API_URL}/overtime/stats', headers=self.headers)

    # ---- 销售接口 ----
    @tag('kiwi')
    @task(1)
    def list_kiwi(self):
        self.client.get(f'{API_URL}/kiwi-sales', headers=self.headers)

    @tag('kiwi')
    @task(1)
    def create_kiwi(self):
        resp = self.client.post(f'{API_URL}/kiwi-sales', headers=self.headers, json={
            'customer_name': f'perf_客户_{random_str()}',
            'phone': '13800138000',
            'address': '性能测试地址',
            'order_date': '2026-07-07',
            'quantity': random.randint(1, 50),
            'payment_amount': round(random.uniform(50, 2000), 2),
            'status': '未发货'
        }, name='/api/kiwi-sales [POST]')

    # ---- 统计数据 ----
    @tag('stats')
    @task(1)
    def get_stats(self):
        self.client.get(f'{API_URL}/stats', headers=self.headers,
                      name='/api/stats')

    @tag('categories')
    @task(1)
    def list_categories(self):
        self.client.get(f'{API_URL}/categories', headers=self.headers)

    @tag('tags')
    @task(1)
    def list_tags(self):
        self.client.get(f'{API_URL}/tags', headers=self.headers)
