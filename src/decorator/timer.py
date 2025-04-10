#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam
# @Email  : sepinetam@gmail.com
# @File   : timer.py

import time
from functools import wraps

def timeit(func):
    @wraps(func)  # 保留原始函数的元信息
    def wrapper(*args, **kwargs):
        start_time = time.time()  # 记录开始时间
        result = func(*args, **kwargs)  # 调用原始函数
        end_time = time.time()  # 记录结束时间
        print(f"函数 {func.__name__} 执行耗时: {end_time - start_time:.4f} 秒")
        return result
    return wrapper
