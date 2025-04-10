#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam
# @Email  : sepinetam@gmail.com
# @File   : spyder.py

# !/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam
# @Email  : sepinetam@gmail.com
# @File   : spyder.py

import requests
import time
import sqlite3
import os

from fake_useragent import UserAgent

from src.config import SAVE_DIR

max_paper = 100000
start = 0

DB_PATH = os.path.abspath(os.path.join(SAVE_DIR, "paper_state.db"))
# print(DB_PATH)

if not os.path.exists(DB_PATH):
    print(f"数据库文件 {DB_PATH} 不存在，正在初始化...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS NBER (
        id TEXT PRIMARY KEY,
        url TEXT,
        doi TEXT,
        save_path TEXT,
        state INTEGER DEFAULT 0
    )
    ''')
    conn.commit()
    conn.close()


def get_ok_ids() -> list:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 首先获取表的所有列名，以便我们知道哪些是"其他列"
    cursor.execute("SELECT * FROM NBER LIMIT 0")
    columns = [desc[0] for desc in cursor.description]

    # 排除ID和state列，因为我们有特定的条件
    other_columns = [col for col in columns if col.lower() != 'id' and col.lower() != 'state']

    # 构建查询语句：先筛选state=200的记录，然后确保其他所有列都不为NULL
    query = f"""
    SELECT id FROM NBER 
    WHERE state = 200
    AND {" AND ".join([f"{col} IS NOT NULL" for col in other_columns])}
    """

    # 执行查询
    cursor.execute(query)

    # 获取结果并整理成列表
    results = cursor.fetchall()
    conn.close()

    ok_ids = [row[0] for row in results]

    return ok_ids


def soon_list(n=max_paper, start=start, ok_list=None):
    if ok_list is None:
        ok_list = get_ok_ids()
    # 创建一个包含 "w0" 到 "w(n-1)" 的列表
    soon = [f"w{i}" for i in range(start, n)]

    # 将 ok_list 转换为集合，加速查找
    ok_set = set(ok_list)

    # 使用集合操作移除在 ok_list 中的元素
    result = [item for item in soon if item not in ok_set]

    return result


def gen_doi(code):
    return f"10.3386/{code}"


def pdf_url(code):
    return f"https://www.nber.org/system/files/working_papers/{code}/{code}.pdf"


def down(paper_id, conn):
    download_link = pdf_url(paper_id)

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
    try:
        resp = requests.get(download_link, headers=headers, stream=True)
        status_code = int(resp.status_code)  # 确保状态码是整数类型

        # 生成DOI
        doi = gen_doi(paper_id)

        # 创建cursor
        cursor = conn.cursor()

        # 准备插入数据库的信息
        if status_code == 200:
            # 如果状态码是200，下载文件并插入完整信息
            resp.raise_for_status()
            os.makedirs(
                (save_dir := os.path.join(SAVE_DIR, paper_id)),
                exist_ok=True
            )
            save_path = os.path.join(save_dir, f"{paper_id}.pdf")

            with open(save_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            # 插入完整信息到数据库，包括DOI
            # 修正：使用SQLite的?占位符而不是%s
            query = """
            INSERT INTO NBER (id, state, url, save_path, doi) 
            VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(query, (paper_id, status_code, download_link, save_path, doi))
        else:
            # 如果状态码不是200，只插入ID和状态码
            # 修正：使用SQLite的?占位符而不是%s
            query = """
            INSERT INTO NBER (id, state) 
            VALUES (?, ?)
            """
            cursor.execute(query, (paper_id, status_code))

        # 提交事务
        conn.commit()

        # 返回状态码
        return status_code

    except requests.exceptions.RequestException as e:
        print(f"下载过程中出错: {e}")
        # 出错时，状态码设为0，并插入数据库
        cursor = conn.cursor()
        # 修正：使用SQLite的?占位符而不是%s
        query = """
        INSERT INTO NBER (id, state) 
        VALUES (?, ?)
        """
        cursor.execute(query, (paper_id, 0))  # 0作为整数
        conn.commit()
        return 0


def main():
    soon = soon_list()
    conn = sqlite3.connect(DB_PATH)
    wrong = []
    for soon_i in soon:
        time.sleep(3)
        print(f"Begin {soon_i}")

        try:
            resp_code = down(paper_id=soon_i, conn=conn)
            if resp_code == 200:
                print(f"Successful, code = {soon_i}")
            else:
                wrong.append(soon_i)
                print(f"Wrong! response code = {resp_code}")
        except Exception as e:
            wrong.append(soon_i)
            print(f"Something went wrong, code = {soon_i}, error: {e}")
    conn.close()

    print(wrong if wrong else None)
    return wrong


if __name__ == "__main__":
    main()
