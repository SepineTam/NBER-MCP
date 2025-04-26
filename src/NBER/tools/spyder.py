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
import random
import orjson  # 比json更快的JSON库
from fake_useragent import UserAgent
from typing import List, Set, Dict, Any
import logging
from aiohttp_retry import RetryClient, ExponentialRetry
import functools
import concurrent.futures

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
MAX_PAPER = 20000
START = 16000
MAX_CONCURRENT_REQUESTS = 50  # 增加并发请求数量
DELAY_BETWEEN_REQUESTS = 0.1  # 减少延迟
CHUNK_SIZE = 1000  # 分批处理的大小
MAX_RETRIES = 3  # 最大重试次数
DB_POOL_SIZE = 20  # 数据库连接池大小

DB_PATH = os.path.abspath(os.path.join(SAVE_DIR, "paper_state.db"))

# 内存缓存，减少数据库操作
ID_CACHE = {
    "ok_ids": set(),
    "all_ids": set(),
    "last_update": 0
}

# 创建数据库连接池
db_pool = None


async def create_db_pool():
    """创建数据库连接池"""
    global db_pool
    db_pool = []
    for _ in range(DB_POOL_SIZE):
        conn = await aiosqlite.connect(DB_PATH)
        # 启用WAL模式提高写入效率
        await conn.execute("PRAGMA journal_mode = WAL")
        # 禁用同步以提高性能（小心使用）
        await conn.execute("PRAGMA synchronous = NORMAL")
        # 增加缓存大小
        await conn.execute("PRAGMA cache_size = 10000")
        db_pool.append(conn)
    return db_pool


async def get_db_conn():
    """从连接池获取数据库连接"""
    if not db_pool:
        await create_db_pool()
    # 简单轮询方式分配连接
    conn = random.choice(db_pool)
    return conn


async def initialize_db():
    """初始化数据库并优化配置"""
    if not os.path.exists(DB_PATH):
        logger.info(f"数据库文件 {DB_PATH} 不存在，正在初始化...")
        async with aiosqlite.connect(DB_PATH) as db:
            # 启用WAL模式提高并发写入效率
            await db.execute("PRAGMA journal_mode = WAL")
            # 创建表
            await db.execute('''
            CREATE TABLE IF NOT EXISTS NBER (
                id TEXT PRIMARY KEY,
                url TEXT,
                doi TEXT,
                save_path TEXT,
                state INTEGER DEFAULT 0
            )
            ''')
            # 创建索引加速查询
            await db.execute('CREATE INDEX IF NOT EXISTS idx_state ON NBER(state)')
            await db.commit()
        logger.info("数据库初始化完成")

    # 创建连接池
    await create_db_pool()


async def refresh_cache() -> None:
    """刷新ID缓存"""
    global ID_CACHE
    current_time = time.time()

    # 如果缓存存在且更新时间不超过5分钟，则跳过更新
    if ID_CACHE["last_update"] > 0 and current_time - ID_CACHE["last_update"] < 300:
        return

    conn = await get_db_conn()
    # 获取表的所有列名
    cursor = await conn.execute("SELECT * FROM NBER LIMIT 0")
    columns = [desc[0] for desc in cursor.description]

    # 排除ID和state列
    other_columns = [col for col in columns if col.lower() != 'id' and col.lower() != 'state']

    # 构建查询语句获取成功的ID
    query = f"""
    SELECT id FROM NBER 
    WHERE state = 200
    AND {" AND ".join([f"{col} IS NOT NULL" for col in other_columns])}
    """

    # 执行查询获取成功ID
    cursor = await conn.execute(query)
    ok_results = await cursor.fetchall()
    ID_CACHE["ok_ids"] = {row[0] for row in ok_results}

    # 获取所有ID
    cursor = await conn.execute("SELECT id FROM NBER")
    all_results = await cursor.fetchall()
    ID_CACHE["all_ids"] = {row[0] for row in all_results}

    # 更新缓存时间
    ID_CACHE["last_update"] = current_time
    logger.info(f"缓存已更新: 成功ID数量={len(ID_CACHE['ok_ids'])}, 所有ID数量={len(ID_CACHE['all_ids'])}")


async def get_ok_ids() -> List[str]:
    """获取已成功下载的ID列表（使用缓存）"""
    await refresh_cache()
    ok_ids = list(ID_CACHE["ok_ids"])
    return ok_ids


async def get_all_ids_in_db() -> Set[str]:
    """获取数据库中所有ID（使用缓存）"""
    await refresh_cache()
    return ID_CACHE["all_ids"]


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


def write_file_sync(path: str, content: bytes) -> None:
    """同步写入文件（用于线程池）"""
    with open(path, 'wb') as f:
        f.write(content)


async def save_file_to_disk(path: str, content: bytes, loop=None) -> None:
    """使用线程池异步写入文件"""
    if loop is None:
        loop = asyncio.get_event_loop()

    # 确保目录存在
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # 使用线程池执行文件I/O操作
    await loop.run_in_executor(
        None,
        functools.partial(write_file_sync, path, content)
    )


async def insert_db_record(paper_id: str, status_code: int, download_link: str = None,
                           save_path: str = None, doi: str = None) -> None:
    """插入数据库记录"""
    conn = await get_db_conn()
    try:
        if status_code == 200 and download_link and save_path and doi:
            await conn.execute(
                "INSERT OR REPLACE INTO NBER (id, state, url, save_path, doi) VALUES (?, ?, ?, ?, ?)",
                (paper_id, status_code, download_link, save_path, doi)
            )
        else:
            await conn.execute(
                "INSERT OR REPLACE INTO NBER (id, state) VALUES (?, ?)",
                (paper_id, status_code)
            )
        await conn.commit()
    except Exception as e:
        logger.error(f"数据库操作失败 {paper_id}: {str(e)}")
        # 不要关闭连接，因为它属于连接池


async def download_paper(paper_id: str, retry_client: RetryClient, semaphore: asyncio.Semaphore,
                         loop=None) -> bool:
    """使用重试机制异步下载单个论文并更新数据库"""
    if loop is None:
        loop = asyncio.get_event_loop()

    async with semaphore:  # 限制并发请求数
        # 随机延迟防止请求模式被检测
        jitter = random.uniform(0, DELAY_BETWEEN_REQUESTS)
        await asyncio.sleep(jitter)

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

        # 添加随机引荐来源，进一步防止反爬
        if random.random() > 0.5:
            referers = [
                'https://www.google.com/search?q=nber+papers',
                'https://scholar.google.com/',
                'https://www.nber.org/papers',
                'https://www.nber.org/search?page=1&perPage=50'
            ]
            headers['Referer'] = random.choice(referers)

        try:
            start_time = time.time()
            async with retry_client.get(download_link, headers=headers,
                                        timeout=aiohttp.ClientTimeout(total=30)) as resp:
                status_code = resp.status

                if status_code == 200:
                    # 获取文件内容
                    content = await resp.read()

                    # 确保目录存在并保存文件（使用线程池）
                    save_dir = os.path.join(SAVE_DIR, paper_id)
                    save_path = os.path.join(save_dir, f"{paper_id}.pdf")
                    await save_file_to_disk(save_path, content, loop)

                    # 更新数据库
                    await insert_db_record(paper_id, status_code, download_link, save_path, doi)

                    elapsed = time.time() - start_time
                    logger.info(f"成功下载 {paper_id}, 耗时: {elapsed:.2f}秒")
                    return True
                else:
                    # 状态码不是200，仅记录ID和状态
                    logger.warning(f"下载失败 {paper_id}, 状态码: {status_code}")
                    await insert_db_record(paper_id, status_code)
                    return False

        except Exception as e:
            logger.error(f"下载 {paper_id} 时出错: {str(e)}")
            # 记录错误状态
            await insert_db_record(paper_id, 0)
            return False


async def process_chunk(chunk: List[str], retry_client: RetryClient,
                        semaphore: asyncio.Semaphore, loop=None) -> List[bool]:
    """处理一批论文ID"""
    tasks = []
    for paper_id in chunk:
        task = asyncio.create_task(download_paper(paper_id, retry_client, semaphore, loop))
        tasks.append(task)

    # 等待所有任务完成并收集结果
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 处理结果
    success_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"处理 {chunk[i]} 时发生异常: {result}")
            success_results.append(False)
        else:
            success_results.append(result)

    return success_results


async def cleanup_resources():
    """清理资源"""
    # 关闭数据库连接池
    if db_pool:
        for conn in db_pool:
            await conn.close()
    logger.info("资源已清理")


async def main():
    """主异步函数"""
    global db_pool
    start_time = time.time()

    # 设置更大的事件循环线程池
    loop = asyncio.get_event_loop()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=50)
    loop.set_default_executor(executor)

    try:
        # 初始化数据库
        await initialize_db()

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

        # 配置重试策略
        retry_options = ExponentialRetry(
            attempts=MAX_RETRIES,
            start_timeout=0.5,
            max_timeout=10,
            factor=2.0,
            statuses={500, 502, 503, 504}
        )

        # 将下载列表分成多个块
        chunks = [download_list[i:i + CHUNK_SIZE] for i in range(0, len(download_list), CHUNK_SIZE)]
        success_count = 0

        async with RetryClient(retry_options=retry_options) as retry_client:
            # 处理每个块
            for i, chunk in enumerate(chunks):
                logger.info(f"处理批次 {i + 1}/{len(chunks)}, 包含 {len(chunk)} 个文件")
                chunk_results = await process_chunk(chunk, retry_client, semaphore, loop)
                chunk_success = sum(1 for r in chunk_results if r is True)
                success_count += chunk_success

                # 显示进度
                progress = (i + 1) / len(chunks) * 100
                elapsed = time.time() - start_time
                est_total = elapsed / progress * 100 if progress > 0 else 0
                remaining = est_total - elapsed if est_total > 0 else 0

                logger.info(f"进度: {progress:.1f}%, 当前批次成功率: {chunk_success / len(chunk) * 100:.1f}%")
                logger.info(f"已用时间: {elapsed:.1f}秒, 预计剩余: {remaining:.1f}秒")

                # 每处理完一批，短暂暂停并刷新缓存
                if i < len(chunks) - 1:
                    await asyncio.sleep(1)
                    await refresh_cache()

        # 统计最终结果
        failed_count = total_papers - success_count
        success_rate = (success_count / total_papers) * 100 if total_papers > 0 else 0

        # 输出详细统计信息
        total_time = time.time() - start_time
        papers_per_second = total_papers / total_time if total_time > 0 else 0

        logger.info(f"下载完成! 总耗时: {total_time:.2f}秒")
        logger.info(f"成功: {success_count}, 失败: {failed_count}, 成功率: {success_rate:.2f}%")
        logger.info(f"平均速度: {papers_per_second:.2f} 篇/秒")

    finally:
        # 确保资源被正确清理
        await cleanup_resources()


if __name__ == "__main__":
    # 在Windows上需要设置事件循环策略
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # 设置更高的资源限制（仅在Unix/Linux系统）
    if hasattr(os, 'sysconf'):
        try:
            import resource

            # 增加文件描述符限制
            soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            resource.setrlimit(resource.RLIMIT_NOFILE, (min(4096, hard), hard))
            logger.info(f"文件描述符限制增加至: {min(4096, hard)}")
        except (ImportError, ValueError, resource.error):
            pass

    # 运行异步主函数
    asyncio.run(main())