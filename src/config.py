import os
import sqlite3


is_download = True
SAVE_DIR = "/Volumes/Papers/10.3386/"
os.makedirs(SAVE_DIR, exist_ok=True)

# sql_base_path = "./src/dataset"
# os.makedirs(sql_base_path, exist_ok=True)
#
# sql_path = os.path.abspath(os.path.join(sql_base_path, "Economics.db"))
#
# if not os.path.exists(sql_path):
#     print(f"数据库文件 {sql_path} 不存在，正在初始化...")
#     conn = sqlite3.connect(sql_path)
#     cursor = conn.cursor()
#
#     # 其中authors用json存储
#     cursor.execute('''
#     CREATE TABLE IF NOT EXISTS NBER (
#         id TEXT PRIMARY KEY,
#         url TEXT,
#         title TEXT,
#         authors TEXT,
#         doi TEXT,
#         download_link TEXT,
#         local_save_path TEXT,
#         issue_date TEXT,
#         abstract TEXT
#     )
#     ''')
#
#     # 提交事务
#     conn.commit()
#     print(f"数据库初始化完成：{sql_path}")
#     conn.close()
# else:
#     print(f"可以使用现有数据库：{sql_path}")
