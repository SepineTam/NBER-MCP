#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam
# @Email  : sepinetam@gmail.com
# @File   : search.py

import requests
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote import webelement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

from src.utils.headless import setup_headless_browser
from src.decorator.timer import timeit


def _search_url(page_i: int, q: str, startDate: str = None, endData: str = None) -> str:
    """
    Gen search url by page and question

    Args:
        page_i (int): the page of search result
        q (str): question
        startDate (str): the start date for example 2025-01-01
        endData (str): the end date for example 2025-01-01

    Returns:
        The url of search from NBER by page_i and question.
    """
    return f"https://nber.org/search?page={page_i}&perPage=50&q={q}"


def get_max_page(url: object) -> int:
    # 设置Chrome选项
    options = Options()
    options.add_argument("--headless")  # 无头模式，不显示浏览器窗口

    # 使用webdriver-manager自动下载合适的ChromeDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        # 加载网页
        driver.get(url)

        # 等待页面加载完成
        time.sleep(3)

        # 查找所有页码按钮
        page_buttons = driver.find_elements(By.CSS_SELECTOR, ".btn.btn--pager")

        page_numbers = []
        max_page = 1
        for button in page_buttons:
            try:
                # 尝试从按钮文本获取页码
                page_text = button.text.strip()
                if page_text and page_text.isdigit():
                    page_numbers.append(int(page_text))
                    continue

                # 如果按钮文本不是数字，尝试获取aria-label属性
                aria_label = button.get_attribute("aria-label")
                if aria_label and "Page" in aria_label:
                    page_num = int(aria_label.replace("Page", "").strip())
                    page_numbers.append(page_num)
            except Exception as e:
                print(f"处理按钮时出错: {e}")
                continue

        # 如果找到页码，返回最大值
        if page_numbers:
            max_page = max(page_numbers)
            return max_page
    except:
        driver.quit()
        return max_page


def _extract(card: webelement.WebElement) -> dict:
    card_info: dict = {}
    try:  # title
        title_element = card.find_element(By.CSS_SELECTOR, "div.digest-card")
        card_info["title"] = title_element.text
        card_info["url"] = title_element.get_attribute('href')
    except:
        pass

    try:  # date
        date_element = card.find_element(By.CLASS_NAME, "digest_card__date")
        card_info['date_info'] = date_element.text
        label_elements = date_element.find_element(By.CLASS_NAME, "digest-card__label")
        if label_elements:
            card_info['labels'] = [label.text for label in label_elements]
    except:
        pass

    try:  # authors
        authors_element = card.find_element(By.CLASS_NAME, "digest-card__items")
        author_links = authors_element.find_elements(By.TAG_NAME, "a")
        if author_links:
            card_info['authors'] = []
            for author_link in author_links:
                card_info['authors'].append({
                    'name': author_link.text,
                    'url': author_link.get_attribute('href')
                })
    except:
        pass

    # 检查是否有图片
    try:
        img_element = card.find_element(By.CLASS_NAME, "digest-card__image")
        card_info['image_url'] = img_element.get_attribute('src')
    except:
        pass

    return card_info


def get_page_result(url) -> list:
    container_class = "search__results"

    driver = setup_headless_browser()
    driver.get(url)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, container_class))
        )
    except Exception as e:
        print(f"等待页面加载时超时或未找到{container_class}元素: {str(e)}")

    driver.find_element(By.CLASS_NAME, container_class)
    digest_cards = driver.find_elements(By.CLASS_NAME, "digest-card")

    search_results_list: list = []
    for card in digest_cards:
        search_results_list.append(_extract(card))

    return search_results_list


@timeit
def get_search_result(q):
    ua = UserAgent()
    # 随机选择一个用户代理
    random_user_agent = ua.random

    headers = {
        'User-Agent': random_user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
        'Referer': 'https://www.nber.org/papers/',
    }

    # 获取最大页码
    max_page = get_max_page(_search_url(1, q=q))

    error_page: list = []
    search_result: list = []
    for page_index in range(max_page):
        _url = _search_url(page_index, q=q)
        response = requests.get(_url, headers)
        status_code = response.status_code
        if str(status_code) == "200":
            search_result += get_page_result(_url)  # TODO: write here
        else:
            error_page.append(page_index)
            print(f"Page: {page_index}, Error: {status_code}")
        time.sleep(3)
    return search_result


if __name__ == "__main__":
    surl = _search_url(1, "chinese")
    # get_page_result(surl)
    maxp = get_max_page(surl)
