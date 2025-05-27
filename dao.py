# dao.py
"""
数据访问对象 (DAO)：对 ORM 模型进行增删改查，包含事务回滚逻辑，预加载关联以避免 DetachedInstance 错误。
"""
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
import bcrypt
import ast



from models import (
    SessionLocal,
    User,
    Algorithm,
    Comment,
    AdminLog,
    DownloadLog,
    ScoringStrategy,
    init_models
)

# 确保模型已初始化（创建表）
init_models()

# 用户数据访问对象
class UserDAO:
    @staticmethod
    def create_user(username: str, password: str, role: str = 'user') -> User:
        session = SessionLocal()
        try:
            pwd_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            user = User(username=username, password_hash=pwd_hash, role=role)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def get_by_username(username: str) -> User:
        session = SessionLocal()
        try:
            return session.query(User).filter_by(username=username).first()
        finally:
            session.close()

    @staticmethod
    def authenticate(username: str, password: str) -> User:
        user = UserDAO.get_by_username(username)
        if user and bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            return user
        return None

# 算法数据访问对象
class AlgorithmDAO:
    @staticmethod
    def upload(owner_id: int, title: str, description: str,
               tags: str, category: str, code_text: str) -> Algorithm:
        session = SessionLocal()
        try:
            strat = session.query(ScoringStrategy).get(1)
            tree = ast.parse(code_text)
            func_cnt = sum(isinstance(n, ast.FunctionDef) for n in ast.walk(tree))
            comment_cnt = code_text.count('#')
            score = func_cnt * strat.func_weight + comment_cnt * strat.comment_weight
            algo = Algorithm(
                owner_id=owner_id,
                title=title,
                description=description,
                tags=tags,
                category=category,
                code=code_text,
                score=score,
                status='pending'
            )
            session.add(algo)
            session.commit()
            session.refresh(algo)
            return algo
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def get_approved(query: str = None, tags: str = None, category: str = None) -> list[Algorithm]:
        session = SessionLocal()
        try:
            q = session.query(Algorithm).options(joinedload(Algorithm.owner)).filter(Algorithm.status == 'approved')
            if query:
                q = q.filter(Algorithm.title.ilike(f"%{query}%"))
            if tags:
                q = q.filter(Algorithm.tags.ilike(f"%{tags}%"))
            if category:
                q = q.filter(Algorithm.category == category)
            return q.all()
        finally:
            session.close()

    @staticmethod
    def get_pending() -> list[Algorithm]:
        session = SessionLocal()
        try:
            return (
                session.query(Algorithm)
                .options(joinedload(Algorithm.owner))
                .filter_by(status='pending')
                .all()
            )
        finally:
            session.close()

    @staticmethod
    def get_detail(algo_id: int) -> Algorithm:
        session = SessionLocal()
        try:
            return (
                session.query(Algorithm)
                .options(joinedload(Algorithm.owner))
                .get(algo_id)
            )
        finally:
            session.close()

    @staticmethod
    def review(admin_id: int, algo_id: int, action: str):
        session = SessionLocal()
        try:
            algo = session.query(Algorithm).get(algo_id)
            algo.status = action
            log = AdminLog(
                admin_id=admin_id,
                action=f"{action}",
                target_type='algorithm',
                target_id=algo_id
            )
            session.add(log)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def delete(algo_id: int):
        session = SessionLocal()
        try:
            algo = session.query(Algorithm).get(algo_id)
            session.delete(algo)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def recalculate_all_scores():
        """
        遍历所有算法，根据最新策略重新计算并保存 score。
        """
        session = SessionLocal()
        try:
            strat = session.query(ScoringStrategy).get(1)
            all_algos = session.query(Algorithm).all()
            for algo in all_algos:
                tree = ast.parse(algo.code)
                func_cnt = sum(isinstance(n, ast.FunctionDef) for n in ast.walk(tree))
                comment_cnt = algo.code.count('#')
                algo.score = func_cnt * strat.func_weight + comment_cnt * strat.comment_weight
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

# 评论数据访问对象
class CommentDAO:
    @staticmethod
    def add(user_id: int, algo_id: int, rating: int, content: str) -> Comment:
        session = SessionLocal()
        try:
            c = Comment(
                user_id=user_id,
                algorithm_id=algo_id,
                rating=rating,
                content=content
            )
            session.add(c)
            session.commit()
            session.refresh(c)
            return c
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def get_by_algo(algo_id: int) -> list[Comment]:
        """
        拉取某算法下的所有评论，预加载 user。
        """
        session = SessionLocal()
        try:
            return (
                session.query(Comment)
                .options(joinedload(Comment.user))
                .filter_by(algorithm_id=algo_id)
                .order_by(Comment.created_at.asc())
                .all()
            )
        finally:
            session.close()

    @staticmethod
    def delete(comment_id: int):
        """
        删除指定评论
        """
        session = SessionLocal()
        try:
            c = session.query(Comment).get(comment_id)
            if c:
                session.delete(c)
                session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

# 下载日志数据访问对象
class DownloadLogDAO:
    @staticmethod
    def record(user_id: int, algo_id: int) -> DownloadLog:
        session = SessionLocal()
        try:
            dl = DownloadLog(user_id=user_id, algorithm_id=algo_id)
            session.add(dl)
            session.commit()
            session.refresh(dl)
            return dl
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()



# 平台统计数据访问对象
class StatsDAO:
    @staticmethod
    def get_stats() -> dict:
        session = SessionLocal()
        try:
            stats = {
                'total_users': session.query(User).count(),
                'total_algorithms': session.query(Algorithm).count(),
                'pending_algorithms': session.query(Algorithm).filter(Algorithm.status=='pending').count(),
                'approved_algorithms': session.query(Algorithm).filter(Algorithm.status=='approved').count(),
                'rejected_algorithms': session.query(Algorithm).filter(Algorithm.status=='rejected').count(),
                'total_comments': session.query(Comment).count(),
                'total_downloads': session.query(DownloadLog).count()
            }
            return stats
        finally:
            session.close()




class ScoringStrategyDAO:
    @staticmethod
    def get_strategy():
        """
        返回 ScoringStrategy 对象
        """
        session = SessionLocal()
        try:
            return session.query(ScoringStrategy).get(1)
        finally:
            session.close()

    @staticmethod
    def update(admin_id: int, func_weight: int, comment_weight: int):
        """
        更新评分策略，并在 admin_logs 中记录这次操作
        """
        session = SessionLocal()
        try:
            strat = session.query(ScoringStrategy).get(1)
            strat.func_weight    = func_weight
            strat.comment_weight = comment_weight
            log = AdminLog(
                admin_id=admin_id,
                action=f"update_scoring(func={func_weight}, comment={comment_weight})",
                target_type='scoring_strategy',
                target_id=1
            )
            session.add(log)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def get_history() -> list[AdminLog]:
        """
        拉取所有针对 scoring_strategy 的操作日志，按时间倒序，并预加载 admin 关系
        """
        session = SessionLocal()
        try:
            return (
                session.query(AdminLog)
                .options(joinedload(AdminLog.admin))
                .filter(AdminLog.target_type == 'scoring_strategy')
                .order_by(AdminLog.timestamp.desc())
                .all()
            )
        finally:
            session.close()
