#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam
# @Email  : sepinetam@gmail.com
# @File   : headless.py

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def setup_headless_browser() -> webdriver.Chrome:
    """
    设置并返回无头Chrome浏览器实例

    Returns:
        webdriver.Chrome: 浏览器实例
    """
    # 设置Chrome选项，启用无头模式
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # 初始化浏览器
    driver = webdriver.Chrome(options=chrome_options)

    # 设置页面加载超时
    driver.set_page_load_timeout(30)

    return driver


if __name__ == "__main__":
    driver = setup_headless_browser()
