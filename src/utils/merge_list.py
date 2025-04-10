#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam
# @Email  : sepinetam@gmail.com
# @File   : merge_list.py

def merge_results(lists_of_dicts):
    """
    Merge multiple lists of dictionaries, removing any duplicate dictionaries.

    Args:
        lists_of_dicts: A list containing multiple lists of dictionaries
                       Format: [[dict1, dict2, ...], [dict3, ...], ...]

    Returns:
        list: A new list containing unique dictionaries from all input lists
    """
    # Convert dictionaries to a hashable format to use set for deduplication
    unique_dicts = set()
    result = []

    # Process all lists
    for lst in lists_of_dicts:
        for item in lst:
            # Convert dict to a tuple of sorted items for hashing
            dict_key = tuple(sorted(item.items()))

            # Add to result if we haven't seen this dict before
            if dict_key not in unique_dicts:
                unique_dicts.add(dict_key)
                result.append(item)

    return result


if __name__ == "__main__":
    # 示例
    dict1 = {"id": 1, "name": "John"}
    dict2 = {"id": 2, "name": "Mary"}
    dict3 = {"id": 3, "name": "Tom"}
    dict4 = {"id": 4, "name": "Lisa"}
    dict5 = {"id": 5, "name": "Mike"}
    dict6 = {"id": 5, "name": "Mikes"}

    # 构建输入列表
    lists = [[dict1, dict2, dict3], [dict2, dict4], [dict5, dict6]]

    # 合并并去重
    merged_list = merge_results(lists)
    print(merged_list)
