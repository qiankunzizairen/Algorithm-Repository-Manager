# logic.py
"""
核心业务逻辑：封装 DAO 操作，提供注册、登录、上传、检索、评论、审核、下载、统计等接口
"""
import dao
from dao import UserDAO, AlgorithmDAO, CommentDAO, DownloadLogDAO, ScoringStrategyDAO, StatsDAO
from models import User, Algorithm
from typing import Optional, List


import csv
from datetime import timedelta, date
from io import StringIO



# 用户注册
def register(username: str, password: str) -> int:
    user = UserDAO.create_user(username, password)
    return user.id

# 用户登录
def authenticate(username: str, password: str) -> User:
    user = UserDAO.authenticate(username, password)
    if not user:
        raise ValueError("用户名或密码错误")
    return user

# 上传算法
def upload_algo(user_id: int, title: str, description: str,
                tags: str, category: str, code_text: str) -> int:
    algo = AlgorithmDAO.upload(user_id, title, description, tags, category, code_text)
    return algo.id

# 查询已通过算法
def list_algos(query: str=None, tags: str=None, category: str=None) -> List[Algorithm]:
    return AlgorithmDAO.get_approved(query, tags, category)

def list_pending() -> list[Algorithm]:
    """
    获取所有待审核算法，仅管理员可调用。
    """
    return dao.AlgorithmDAO.get_pending()



# 获取算法详情
def get_algo_detail(algo_id: int) -> Algorithm:
    return AlgorithmDAO.get_detail(algo_id)

# 添加评论
def comment_algo(user_id: int, algo_id: int, rating: int, content: str) -> int:
    c = CommentDAO.add(user_id, algo_id, rating, content)
    return c.id

# 管理员审核算法
def review_algo(admin: User, algo_id: int, action: str):
    if admin.role != 'admin':
        raise PermissionError("必须为管理员才能审核")
    AlgorithmDAO.review(admin.id, algo_id, action)

# 下载算法
def download_algo(user: Optional[User], algo_id: int) -> str:
    code = AlgorithmDAO.get_detail(algo_id).code
    DownloadLogDAO.record(user.id if user else 0, algo_id)
    return code

# 更新评分策略
def update_scoring(admin: User, func_w: int, comment_w: int):
    if admin.role != 'admin':
        raise PermissionError("必须为管理员才能修改评分策略")
    ScoringStrategyDAO.update(admin.id, func_w, comment_w)

# 平台统计
def get_stats() -> dict:
    return StatsDAO.get_stats()

def delete_algo(admin, algo_id: int):
    """
    管理员删除算法
    """
    if admin.role != 'admin':
        raise PermissionError("必须为管理员才能删除算法")
    from dao import AlgorithmDAO
    AlgorithmDAO.delete(algo_id)



def get_comments(algo_id: int) -> list:
    comments = CommentDAO.get_by_algo(algo_id)
    return [{
        'id':       c.id,                 # ← 把评论的主键也返回
        'username': c.user.username,
        'rating':   c.rating,
        'content':  c.content,
        'time':     c.created_at
    } for c in comments]



def delete_algo(admin, algo_id: int):
    """
    管理员删除算法。
    """
    if admin.role != 'admin':
        raise PermissionError("必须为管理员才能删除算法")
    AlgorithmDAO.delete(algo_id)

def get_scoring_strategy() -> dict:
    """
    返回当前评分策略的 func 和 comment 权重
    """
    strat = ScoringStrategyDAO.get_strategy()
    return {
        'func_weight':    strat.func_weight,
        'comment_weight': strat.comment_weight
    }

def update_scoring(admin, func_weight: int, comment_weight: int):
    """
    管理员修改评分策略。
    """
    if admin.role != 'admin':
        raise PermissionError("必须为管理员才能修改评分策略")
    ScoringStrategyDAO.update(admin.id, func_weight, comment_weight)

def get_strategy_history() -> list:
    """
    返回评分策略修改的历史记录列表，
    每条为 {'time': ..., 'admin': ..., 'action': ...}
    """
    logs = ScoringStrategyDAO.get_history()
    history = []
    for log in logs:
        history.append({
            'time':  log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'admin': log.admin.username,
            'action': log.action
        })
    return history

def delete_comment(admin, comment_id: int):
    """
    管理员删除评论
    """
    if admin.role != 'admin':
        raise PermissionError("只有管理员可以删除评论")
    CommentDAO.delete(comment_id)



def update_scoring(admin, func_weight: int, comment_weight: int):
    if admin.role != 'admin':
        raise PermissionError("必须为管理员才能修改评分策略")
    # 1. 更新策略表并记日志
    ScoringStrategyDAO.update(admin.id, func_weight, comment_weight)
    # 2. 批量重新计算所有算法的 score
    AlgorithmDAO.recalculate_all_scores()



def get_stats_data(dtype: str, start: date, end: date):
    """
    根据 dtype 和日期区间，返回统计数据。
    目前只支持按日期区间内的汇总，也可扩展为返回每日明细。
    dtype 可选：
      - "算法总数"
      - "用户总数"
      - "待审核算法"
      - "已通过算法"
      - "评论总数"
      - "下载总数"
    返回一个简单的值或列表，GUI 当前只做文本展示。
    """
    stats = StatsDAO.get_stats()  # 返回 dict
    # 将中文类型映射到 stats 字段名
    mapping = {
        "算法总数":        "total_algorithms",
        "用户总数":        "total_users",
        "待审核算法":      "pending_algorithms",
        "已通过算法":      "approved_algorithms",
        "评论总数":        "total_comments",
        "下载总数":        "total_downloads",
    }
    key = mapping.get(dtype)
    if key is None:
        raise ValueError(f"未知的数据类型：{dtype}")

    # 这里我们暂时只返回区间内的汇总值，不按天拆分
    return stats[key]


def export_stats_csv(dtype: str, start: date, end: date) -> str:
    """
    导出当前统计为 CSV 文本。
    返回一个 CSV 格式的字符串，第一列为“指标”，第二列为值。
    """
    value = get_stats_data(dtype, start, end)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([ "数据类型", "起始日期", "结束日期", "数值" ])
    writer.writerow([ dtype, start.isoformat(), end.isoformat(), value ])
    return output.getvalue()