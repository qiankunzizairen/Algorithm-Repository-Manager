# db.py
"""
数据库模块：
- init_db() 初始化数据库、表结构及默认用户/评分策略
- get_app_connection() 获取业务层可用连接
- 各用户故事对应接口函数
"""
import mysql.connector
from mysql.connector import Error
import bcrypt
import ast
import datetime
import config


def create_root_connection():
    """Root 用户连接，用于初始化数据库"""
    return mysql.connector.connect(
        host=config.DB_HOST,
        user=config.DB_ROOT_USER,
        password=config.DB_ROOT_PWD,
        charset='utf8mb4'
    )


def get_app_connection():
    """应用层连接，用于业务操作"""
    return mysql.connector.connect(
        host=config.DB_HOST,
        user=config.APP_DB_USER,
        password=config.APP_DB_PWD,
        database=config.DB_NAME,
        charset='utf8mb4'
    )


def init_db():
    """
    初始化数据库及表结构，创建应用用户及默认管理员与评分策略
    """
    # 1. root 连接 -> 创建库 & 应用账号
    root_conn = create_root_connection()
    root_conn.autocommit = True
    cursor = root_conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{config.DB_NAME}` CHARACTER SET utf8mb4;")
    cursor.execute(f"CREATE USER IF NOT EXISTS '{config.APP_DB_USER}'@'{config.DB_HOST}' IDENTIFIED BY '{config.APP_DB_PWD}';")
    cursor.execute(f"GRANT ALL PRIVILEGES ON `{config.DB_NAME}`.* TO '{config.APP_DB_USER}'@'{config.DB_HOST}';")
    cursor.execute("FLUSH PRIVILEGES;")
    cursor.close()
    root_conn.close()

    # 2. 应用连接 -> 创建表 & 默认数据
    conn = get_app_connection()
    cursor = conn.cursor()
    # users
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(60) NOT NULL,
            role ENUM('user','admin') DEFAULT 'user',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    # algorithms
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS algorithms (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(100) NOT NULL,
            description TEXT,
            owner_id INT NOT NULL,
            tags VARCHAR(255),
            category VARCHAR(50),
            version INT DEFAULT 1,
            code TEXT NOT NULL,
            score FLOAT DEFAULT 0,
            status ENUM('pending','approved','rejected') DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(owner_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    # comments
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            algorithm_id INT NOT NULL,
            user_id INT NOT NULL,
            rating TINYINT,
            content TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(algorithm_id) REFERENCES algorithms(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id)      REFERENCES users(id)      ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    # admin_logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            admin_id INT NOT NULL,
            action VARCHAR(100),
            target_type VARCHAR(50),
            target_id INT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(admin_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    # download_logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS download_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            algorithm_id INT NOT NULL,
            downloaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id)      REFERENCES users(id)      ON DELETE CASCADE,
            FOREIGN KEY(algorithm_id) REFERENCES algorithms(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    # scoring_strategy
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scoring_strategy (
            id INT PRIMARY KEY,
            func_weight INT,
            comment_weight INT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    # 默认插入一条策略
    cursor.execute("SELECT COUNT(*) FROM scoring_strategy;")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO scoring_strategy(id,func_weight,comment_weight) VALUES(1,%s,%s);",
            (config.SCORING_DEFAULT_FUNC_WEIGHT,
             config.SCORING_DEFAULT_COMMENT_WEIGHT)
        )
    # 默认管理员
    cursor.execute(
        "SELECT COUNT(*) FROM users WHERE username=%s;",
        (config.DEFAULT_ADMIN['username'],)
    )
    if cursor.fetchone()[0] == 0:
        pwd_hash = bcrypt.hashpw(
            config.DEFAULT_ADMIN['password'].encode(), bcrypt.gensalt()
        ).decode()
        cursor.execute(
            "INSERT INTO users(username,password_hash,role) VALUES(%s,%s,'admin');",
            (config.DEFAULT_ADMIN['username'], pwd_hash)
        )
    conn.commit()
    cursor.close()
    conn.close()


# ===== 接口定义 =====

def register_user(username: str, password: str) -> int:
    """
    用户注册，返回新用户ID
    """
    conn = get_app_connection()
    cursor = conn.cursor()
    pwd_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    cursor.execute(
        "INSERT INTO users(username,password_hash) VALUES(%s,%s);",
        (username, pwd_hash)
    )
    conn.commit()
    user_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return user_id


def authenticate_user(username: str, password: str) -> dict:
    """
    验证用户名/密码，成功返回用户记录，否则返回 None
    """
    conn = get_app_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM users WHERE username=%s;",
        (username,)
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user and bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
        return user
    return None


def get_scoring_strategy() -> dict:
    """
    获取当前评分策略权重
    """
    conn = get_app_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM scoring_strategy WHERE id=1;")
    strat = cursor.fetchone()
    cursor.close()
    conn.close()
    return strat


def score_algorithm(code_text: str) -> float:
    """
    按策略自动评分：函数定义数*func_weight + 注释数*comment_weight
    """
    strat = get_scoring_strategy()
    tree = ast.parse(code_text)
    func_cnt = sum(isinstance(n, ast.FunctionDef) for n in ast.walk(tree))
    comment_cnt = code_text.count('#')
    return func_cnt * strat['func_weight'] + comment_cnt * strat['comment_weight']


def upload_algorithm(owner_id: int, title: str, description: str,
                     tags: str, category: str, code_text: str) -> int:
    """
    算法上传，自动评分，初始状态 pending
    返回算法ID
    """
    score = score_algorithm(code_text)
    conn = get_app_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO algorithms
           (title,description,owner_id,tags,category, code,score,status)
           VALUES(%s,%s,%s,%s,%s,%s,%s,%s);''',
        (title, description, owner_id, tags, category,
         code_text, score, 'pending')
    )
    conn.commit()
    algo_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return algo_id


def search_algorithms(query: str=None, tags: str=None, category: str=None) -> list:
    """
    按条件检索已通过的算法，支持模糊匹配
    """
    conn = get_app_connection()
    cursor = conn.cursor(dictionary=True)
    sql = "SELECT * FROM algorithms WHERE status='approved'"
    params = []
    if query:
        sql += " AND title LIKE %s"; params.append(f"%{query}%")
    if tags:
        sql += " AND tags LIKE %s"; params.append(f"%{tags}%")
    if category:
        sql += " AND category=%s"; params.append(category)
    cursor.execute(sql + ";", tuple(params))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results


def get_algorithm_detail(algo_id: int) -> dict:
    """
    获取算法详情，不含 code 文本
    """
    conn = get_app_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM algorithms WHERE id=%s;", (algo_id,))
    algo = cursor.fetchone()
    cursor.close()
    conn.close()
    return algo


def get_algorithm_code(algo_id: int) -> str:
    """下载算法源码"""
    conn = get_app_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT code FROM algorithms WHERE id=%s;", (algo_id,))
    code = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    # 记录下载日志
    record_download(0, algo_id)  # 0 代表匿名或当前 user_id 后续再传入
    return code


def add_comment(user_id: int, algo_id: int, rating: int, content: str) -> int:
    """提交评论，返回 comment ID"""
    conn = get_app_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO comments(algorithm_id,user_id,rating,content)
           VALUES(%s,%s,%s,%s);''',
        (algo_id, user_id, rating, content)
    )
    conn.commit()
    cid = cursor.lastrowid
    cursor.close()
    conn.close()
    return cid


def review_algorithm(admin_id: int, algo_id: int, action: str):
    """管理员审核算法：approved/rejected"""
    conn = get_app_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE algorithms SET status=%s WHERE id=%s;", (action, algo_id))
    cursor.execute(
        '''INSERT INTO admin_logs(admin_id,action,target_type,target_id)
           VALUES(%s,%s,%s,%s);''',
        (admin_id, action, 'algorithm', algo_id)
    )
    conn.commit()
    cursor.close()
    conn.close()


def delete_algorithm(algo_id: int):
    """删除算法及关联评论"""
    conn = get_app_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM algorithms WHERE id=%s;", (algo_id,))
    conn.commit()
    cursor.close()
    conn.close()


def set_scoring_strategy(admin_id: int, func_weight: int, comment_weight: int):
    """更新评分策略并记录日志"""
    conn = get_app_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE scoring_strategy SET func_weight=%s, comment_weight=%s WHERE id=1;",
        (func_weight, comment_weight)
    )
    cursor.execute(
        "INSERT INTO admin_logs(admin_id,action,target_type,target_id) VALUES(%s,%s,%s,%s);",
        (admin_id, f"update_scoring({func_weight},{comment_weight})", 'scoring_strategy', 1)
    )
    conn.commit()
    cursor.close()
    conn.close()


def record_download(user_id: int, algo_id: int):
    """记录下载日志"""
    conn = get_app_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO download_logs(user_id,algorithm_id) VALUES(%s,%s);",
        (user_id, algo_id)
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_statistics() -> dict:
    """获取平台统计数据"""
    conn = get_app_connection()
    cursor = conn.cursor()
    stats = {}
    def count(q): cursor.execute(q); return cursor.fetchone()[0]
    stats['total_users']          = count("SELECT COUNT(*) FROM users;")
    stats['total_algorithms']     = count("SELECT COUNT(*) FROM algorithms;")
    stats['pending_algorithms']   = count("SELECT COUNT(*) FROM algorithms WHERE status='pending';")
    stats['approved_algorithms']  = count("SELECT COUNT(*) FROM algorithms WHERE status='approved';")
    stats['rejected_algorithms']  = count("SELECT COUNT(*) FROM algorithms WHERE status='rejected';")
    stats['total_comments']       = count("SELECT COUNT(*) FROM comments;")
    stats['total_downloads']      = count("SELECT COUNT(*) FROM download_logs;")
    cursor.close()
    conn.close()
    return stats
