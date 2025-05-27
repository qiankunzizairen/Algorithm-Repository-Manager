# config.py
"""
配置文件：定义数据库凭据、默认管理员及评分策略常量
"""

# MySQL 管理员账号（用于初始化数据库）
DB_ROOT_USER = 'root'
DB_ROOT_PWD  = '123456//lxy'
DB_HOST      = 'localhost'

# 应用数据库名称及应用账号（业务层和GUI层使用）
DB_NAME      = 'algodb'
APP_DB_USER  = 'algouser'
APP_DB_PWD   = 'password'

# 默认管理员账号（初始化时自动创建）
DEFAULT_ADMIN = {
    'username': 'admin',
    'password': 'admin123'
}

# 默认评分策略权重
SCORING_DEFAULT_FUNC_WEIGHT    = 10  # 每个函数定义分值
SCORING_DEFAULT_COMMENT_WEIGHT =  1  # 每个注释符号分值
