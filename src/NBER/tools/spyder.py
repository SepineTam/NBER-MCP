#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam
# @Email  : sepinetam@gmail.com
# @File   : async_spyder.py

import aiohttp
import asyncio
import aiosqlite
import os
import time
from fake_useragent import UserAgent
from typing import List, Set
import logging

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("async_spyder.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 假设从原始代码导入
from src.config import SAVE_DIR

# 配置参数
MAX_PAPER = 10000
START = 0
MAX_CONCURRENT_REQUESTS = 20  # 控制并发请求数量
DELAY_BETWEEN_REQUESTS = 0.5  # 每个请求之间的延迟（秒）

DB_PATH = os.path.abspath(os.path.join(SAVE_DIR, "paper_state.db"))


async def initialize_db():
    """初始化数据库"""
    if not os.path.exists(DB_PATH):
        logger.info(f"数据库文件 {DB_PATH} 不存在，正在初始化...")
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
            CREATE TABLE IF NOT EXISTS NBER (
                id TEXT PRIMARY KEY,
                url TEXT,
                doi TEXT,
                save_path TEXT,
                state INTEGER DEFAULT 0
            )
            ''')
            await db.commit()
        logger.info("数据库初始化完成")


async def get_ok_ids() -> List[str]:
    """获取已成功下载的ID列表"""
    async with aiosqlite.connect(DB_PATH) as db:
        # 获取表的所有列名
        cursor = await db.execute("SELECT * FROM NBER LIMIT 0")
        columns = [desc[0] for desc in cursor.description]

        # 排除ID和state列
        other_columns = [col for col in columns if col.lower() != 'id' and col.lower() != 'state']

        # 构建查询语句
        query = f"""
        SELECT id FROM NBER 
        WHERE state = 200
        AND {" AND ".join([f"{col} IS NOT NULL" for col in other_columns])}
        """

        # 执行查询
        cursor = await db.execute(query)
        results = await cursor.fetchall()

    ok_ids = [row[0] for row in results]
    logger.info(f"已成功下载的论文数量: {len(ok_ids)}")
    return ok_ids


async def get_all_ids_in_db() -> Set[str]:
    """获取数据库中所有ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id FROM NBER")
        results = await cursor.fetchall()

    return {row[0] for row in results}


def soon_list(n=MAX_PAPER, start=START, ok_ids=None, all_ids=None):
    """创建待下载的论文ID列表"""
    # 创建一个包含 "w0" 到 "w(n-1)" 的列表
    all_possible = [f"w{i}" for i in range(start, n)]

    # 移除已在数据库中的ID
    if all_ids:
        result = [item for item in all_possible if item not in all_ids]
    else:
        # 移除已成功下载的ID
        ok_set = set(ok_ids) if ok_ids else set()
        result = [item for item in all_possible if item not in ok_set]

    return result


def gen_doi(code):
    """生成DOI"""
    return f"10.3386/{code}"


def pdf_url(code):
    """生成PDF URL"""
    return f"https://www.nber.org/system/files/working_papers/{code}/{code}.pdf"


async def download_paper(paper_id: str, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore):
    """异步下载单个论文并更新数据库"""
    async with semaphore:  # 限制并发请求数
        # 添加小延迟防止请求过快
        await asyncio.sleep(DELAY_BETWEEN_REQUESTS)

        download_link = pdf_url(paper_id)
        doi = gen_doi(paper_id)

        ua = UserAgent()
        headers = {
            'User-Agent': ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.nber.org/papers/',
        }

        try:
            start_time = time.time()
            async with session.get(download_link, headers=headers) as resp:
                status_code = resp.status

                async with aiosqlite.connect(DB_PATH) as db:
                    if status_code == 200:
                        # 确保目录存在
                        save_dir = os.path.join(SAVE_DIR, paper_id)
                        os.makedirs(save_dir, exist_ok=True)
                        save_path = os.path.join(save_dir, f"{paper_id}.pdf")

                        # 下载PDF
                        content = await resp.read()
                        with open(save_path, 'wb') as f:
                            f.write(content)

                        # 更新数据库
                        await db.execute(
                            "INSERT INTO NBER (id, state, url, save_path, doi) VALUES (?, ?, ?, ?, ?)",
                            (paper_id, status_code, download_link, save_path, doi)
                        )
                        await db.commit()

                        logger.info(f"成功下载 {paper_id}, 耗时: {time.time() - start_time:.2f}秒")
                        return True
                    else:
                        # 状态码不是200，仅记录ID和状态
                        await db.execute(
                            "INSERT INTO NBER (id, state) VALUES (?, ?)",
                            (paper_id, status_code)
                        )
                        await db.commit()

                        logger.warning(f"下载失败 {paper_id}, 状态码: {status_code}")
                        return False

        except Exception as e:
            logger.error(f"下载 {paper_id} 时出错: {str(e)}")
            # 记录错误状态
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "INSERT INTO NBER (id, state) VALUES (?, ?)",
                    (paper_id, 0)
                )
                await db.commit()
            return False


async def main():
    """主异步函数"""
    start_time = time.time()

    # 初始化数据库
    await initialize_db()

    # 获取已成功下载的ID
    ok_ids = await get_ok_ids()

    # 获取数据库中的所有ID
    all_ids = await get_all_ids_in_db()

    # 获取待下载列表
    download_list = soon_list(all_ids=all_ids)
    total_papers = len(download_list)

    if not download_list:
        logger.info("没有新的论文需要下载")
        return

    logger.info(f"开始下载 {total_papers} 篇论文")

    # 创建信号量控制并发
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    # 创建异步下载任务
    async with aiohttp.ClientSession() as session:
        tasks = []
        for paper_id in download_list:
            task = asyncio.create_task(download_paper(paper_id, session, semaphore))
            tasks.append(task)

        # 等待所有任务完成并收集结果
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计结果
        success_count = sum(1 for r in results if r is True)
        failed_count = total_papers - success_count

    logger.info(f"下载完成! 总耗时: {time.time() - start_time:.2f}秒")
    logger.info(f"成功: {success_count}, 失败: {failed_count}")


if __name__ == "__main__":
    # 在Windows上需要设置事件循环策略
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # 运行异步主函数
    asyncio.run(main())
