#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam
# @Email  : sepinetam@gmail.com
# @File   : tiny.py

# 伟大的渺小，我们的方方面面总是由点点滴滴而成的，尽管世事难料，但是最好目前的自己就是最好。

from time import time
import os


def save(context, file_path=f"private/log/{int(time())}.log"):
    file_path = os.path.abspath(file_path)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(context)


if __name__ == "__main__":
    path = f"../../private/log/{int(time())}.log"
    file_path = os.path.abspath(path)
    print(file_path)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
