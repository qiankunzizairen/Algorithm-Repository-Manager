# gui.py
"""
所有 GUI 相关内容，整合为 APP 类，使用 PyQt5 实现。
"""
import sys
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QComboBox, QSpinBox, QMessageBox,
    QFileDialog, QScrollArea, QFrame, QDialog, QDateEdit
)
import logic

CATEGORY_LIST = ["排序", "查找", "图算法", "动态规划"]
ALL_CATEGORIES = ["全部"] + CATEGORY_LIST



class DetailDialog(QDialog):
    def __init__(self, parent, algo, is_review=False, review_callback=None):
        super().__init__(parent)
        self.algo = algo
        self.review_callback = review_callback
        self.setWindowTitle(f"算法详情 — {algo.title}")
        self.resize(700, 600)

        main_layout = QVBoxLayout()

        # 1. 标题 & 分类
        main_layout.addWidget(QLabel(f"<b>{algo.title}</b>  分类: {algo.category}"))

        # 2. 描述展示
        desc_text = algo.description or "<无描述>"
        desc_label = QLabel(f"描述: {desc_text}")
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)

        # 3. 代码预览
        code_edit = QTextEdit()
        text = algo.code.decode('utf-8') if isinstance(algo.code, (bytes, bytearray)) else algo.code
        code_edit.setPlainText(text)
        code_edit.setReadOnly(True)
        main_layout.addWidget(code_edit, stretch=3)

        # 4. 评论列表区（滚动）
        main_layout.addWidget(QLabel("— 评论列表 —"))
        self._comments_container = QWidget()
        self._comments_layout = QVBoxLayout(self._comments_container)
        comments_scroll = QScrollArea()
        comments_scroll.setWidgetResizable(True)
        comments_scroll.setWidget(self._comments_container)
        main_layout.addWidget(comments_scroll, stretch=2)
        self._load_comments()  # 首次加载

        # 5. 提交新评论区域（所有用户可见）
        form = QHBoxLayout()
        form.addWidget(QLabel("打分："))
        self.rating_spin = QSpinBox()
        self.rating_spin.setRange(1, 5)
        self.rating_spin.setValue(3)
        form.addWidget(self.rating_spin)
        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText("输入评论")
        form.addWidget(self.comment_edit)
        post_btn = QPushButton("提交评论")
        post_btn.clicked.connect(self._do_comment)
        form.addWidget(post_btn)
        main_layout.addLayout(form)

        # 6. 审核 / 删除 算法 （仅管理员可见）
        if is_review:
            btns = QHBoxLayout()
            approve = QPushButton("通过")
            approve.clicked.connect(lambda: self._do_review("approved"))
            reject = QPushButton("驳回")
            reject.clicked.connect(lambda: self._do_review("rejected"))
            delete_algo = QPushButton("删除算法")
            delete_algo.clicked.connect(self._do_delete)
            btns.addWidget(approve)
            btns.addWidget(reject)
            btns.addWidget(delete_algo)
            main_layout.addLayout(btns)

        # 7. 统一添加下载按钮
        down_btn = QPushButton("📥 下载")
        down_btn.clicked.connect(self._do_download)
        main_layout.addWidget(down_btn, alignment=QtCore.Qt.AlignRight)

        self.setLayout(main_layout)

    def _load_comments(self):
        """加载并展示评论，每条评论管理员可删除"""
        # 清空旧条目
        for i in reversed(range(self._comments_layout.count())):
            w = self._comments_layout.itemAt(i).widget()
            w.setParent(None)

        # 从父窗口拿到当前登录用户
        parent_user = getattr(self.parent(), "user", None)

        # 获取新评论
        for c in logic.get_comments(self.algo.id):
            row = QHBoxLayout()
            lbl = QLabel(f"{c['username']}  {c['rating']}⭐  {c['content']}")
            row.addWidget(lbl)

            # 仅管理员可见“删除评论”按钮
            if parent_user and parent_user.role == 'admin':
                del_btn = QPushButton("删除评论")
                del_btn.clicked.connect(lambda _, cid=c['id']: self._do_delete_comment(cid))
                row.addWidget(del_btn)

            container = QWidget()
            container.setLayout(row)
            self._comments_layout.addWidget(container)

    def _do_comment(self):
        rating = self.rating_spin.value()
        content = self.comment_edit.text().strip()
        if not content:
            QMessageBox.warning(self, "提示", "评论内容不能为空")
            return
        try:
            logic.comment_algo(self.parent().user.id, self.algo.id, rating, content)
            QMessageBox.information(self, "成功", "评论已提交")
            self.comment_edit.clear()
            self._load_comments()
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def _do_delete_comment(self, comment_id: int):
        if QMessageBox.question(self, "删除确认", "确定要删除此评论？") != QMessageBox.Yes:
            return
        try:
            logic.delete_comment(self.parent().user, comment_id)
            self._load_comments()
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def _do_download(self):
        code = logic.download_algo(self.parent().user, self.algo.id)
        path, _ = QFileDialog.getSaveFileName(self, "下载代码", f"{self.algo.title}.py", "Python Files (*.py)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(code)
            QMessageBox.information(self, "完成", "已下载")

    def _do_review(self, action: str):
        try:
            logic.review_algo(self.parent().user, self.algo.id, action)
            QMessageBox.information(self, "完成", f"{action} 成功")
            if self.review_callback:
                self.review_callback(self.algo.id)
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def _do_delete(self):
        try:
            logic.delete_algo(self.parent().user, self.algo.id)
            QMessageBox.information(self, "完成", "算法已删除")
            if self.review_callback:
                self.review_callback(self.algo.id)
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))




class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Algorithm Repository Manager")
        self.resize(800, 600)
        self.user = None

        # 管理员专属按钮，登录后根据角色显隐
        self.review_btn   = QPushButton("审核算法", clicked=self._show_review_page)
        self.strategy_btn = QPushButton("调整评分策略", clicked=self._show_strategy_page)
        self.review_btn.hide()
        self.strategy_btn.hide()

        # 页面容器
        self.stack = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.stack)

        # 构造所有页面
        self._build_login()
        self._build_main()
        self._build_upload()
        self._build_search()
        self._build_review()
        self._build_stats()
        self._build_strategy()

        # 初始显示登录页
        self.stack.setCurrentWidget(self.login_page)

    # ─── 登录 / 注册 ───────────────────────────────────────────────
    def _build_login(self):
        self.login_page = QWidget()
        layout = QVBoxLayout(self.login_page)
        self.login_user = QLineEdit(); self.login_user.setPlaceholderText("用户名")
        self.login_pwd  = QLineEdit(); self.login_pwd.setPlaceholderText("密码")
        self.login_pwd.setEchoMode(QLineEdit.Password)
        layout.addStretch()
        layout.addWidget(self.login_user)
        layout.addWidget(self.login_pwd)
        btns = QHBoxLayout()
        btns.addWidget(QPushButton("登录", clicked=self._do_login))
        btns.addWidget(QPushButton("注册", clicked=self._do_register))
        layout.addLayout(btns)
        layout.addStretch()
        self.stack.addWidget(self.login_page)

    def _do_login(self):
        u, p = self.login_user.text().strip(), self.login_pwd.text().strip()
        try:
            user = logic.authenticate(u, p)
            if not user:
                raise ValueError("用户名或密码错误")
            self.user = user
            # 管理员按钮显隐
            if user.role == 'admin':
                self.review_btn.show()
                self.strategy_btn.show()
            else:
                self.review_btn.hide()
                self.strategy_btn.hide()
            self.stack.setCurrentWidget(self.main_page)
        except Exception as e:
            QMessageBox.warning(self, "登录失败", str(e))
            self.login_pwd.clear()

    def _do_register(self):
        u, p = self.login_user.text().strip(), self.login_pwd.text().strip()
        try:
            logic.register(u, p)
            QMessageBox.information(self, "成功", "注册成功，请登录")
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    # ─── 主 菜 单 ─────────────────────────────────────────────────
    def _build_main(self):
        self.main_page = QWidget()
        layout = QVBoxLayout(self.main_page)
        layout.addWidget(QPushButton("上传算法", clicked=lambda: self.stack.setCurrentWidget(self.upload_page)))
        layout.addWidget(QPushButton("算法列表", clicked=lambda: self.stack.setCurrentWidget(self.search_page)))
        layout.addWidget(self.review_btn)
        layout.addWidget(self.strategy_btn)
        layout.addWidget(QPushButton("平台统计", clicked=lambda: self.stack.setCurrentWidget(self.stats_page)))
        layout.addWidget(QPushButton("登出", clicked=lambda: self.stack.setCurrentWidget(self.login_page)))
        self.stack.addWidget(self.main_page)

    # ─── 上传 算 法 ───────────────────────────────────────────────
    def _build_upload(self):
        self.upload_page = QWidget()
        layout = QVBoxLayout(self.upload_page)
        layout.addWidget(QLabel("上传算法界面", alignment=QtCore.Qt.AlignCenter))

        form = QHBoxLayout()
        self.up_title = QLineEdit(); self.up_title.setPlaceholderText("算法标题")
        self.up_cat   = QComboBox();    self.up_cat.addItems(CATEGORY_LIST)
        self.up_tags  = QLineEdit();    self.up_tags.setPlaceholderText("标签 (逗号分隔)")
        self.up_desc  = QLineEdit();    self.up_desc.setPlaceholderText("简要描述")
        form.addWidget(QLabel("标题:")); form.addWidget(self.up_title)
        form.addWidget(QLabel("分类:")); form.addWidget(self.up_cat)
        form.addWidget(QLabel("标签:")); form.addWidget(self.up_tags)
        form.addWidget(QLabel("描述:")); form.addWidget(self.up_desc)
        layout.addLayout(form)

        self.up_code = QTextEdit()
        layout.addWidget(self.up_code)

        bottom = QHBoxLayout()
        bottom.addWidget(QPushButton("🔙 返回", clicked=lambda: self.stack.setCurrentWidget(self.main_page)))
        bottom.addWidget(QPushButton("📤 上传算法", clicked=self._submit_upload))
        self.up_score = QLabel("⭐ 得分: 0")
        bottom.addWidget(self.up_score)
        layout.addLayout(bottom)

        self.stack.addWidget(self.upload_page)

    def _submit_upload(self):
        title    = self.up_title.text().strip()
        category = self.up_cat.currentText()
        tags     = self.up_tags.text().strip()
        desc     = self.up_desc.text().strip()
        code     = self.up_code.toPlainText()
        if not title or not code:
            QMessageBox.warning(self, "提示", "标题和代码不能为空")
            return
        try:
            aid = logic.upload_algo(self.user.id, title, desc, tags, category, code)
            algo = logic.get_algo_detail(aid)
            self.up_score.setText(f"⭐ 得分: {algo.score:.1f}")
            QMessageBox.information(self, "成功", "上传成功，等待审核")
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    # ─── 算 法 列 表 ───────────────────────────────────────────────
    def _build_search(self):
        self.search_page = QWidget()
        layout = QVBoxLayout(self.search_page)
        layout.addWidget(QLabel("算法检索页面", alignment=QtCore.Qt.AlignCenter))

        top = QHBoxLayout()
        self.search_input = QLineEdit(); self.search_input.setPlaceholderText("🔍 输入关键词…")
        self.search_cat   = QComboBox(); self.search_cat.addItems(ALL_CATEGORIES)
        top.addWidget(self.search_input); top.addWidget(self.search_cat)
        top.addWidget(QPushButton("搜索", clicked=self._do_search))
        layout.addLayout(top)

        self.search_scroll    = QScrollArea(); self.search_scroll.setWidgetResizable(True)
        self.search_container = QWidget(); self.search_vbox = QVBoxLayout(self.search_container)
        self.search_scroll.setWidget(self.search_container)
        layout.addWidget(self.search_scroll)

        layout.addWidget(QPushButton("🔙 返回", clicked=lambda: self.stack.setCurrentWidget(self.main_page)))
        self.stack.addWidget(self.search_page)

    def _do_search(self):
        # 清空旧卡片
        for i in reversed(range(self.search_vbox.count())):
            self.search_vbox.itemAt(i).widget().deleteLater()
        q   = self.search_input.text().strip() or None
        cat = self.search_cat.currentText(); cat = None if cat == "全部" else cat
        algos = logic.list_algos(query=q, tags=None, category=cat)
        for a in algos:
            card = QFrame(); card.setFrameShape(QFrame.Box)
            c = QHBoxLayout(card)
            c.addWidget(QLabel(f"🧠 {a.title}    作者：{a.owner.username}"))
            c.addWidget(QLabel(f"标签：{a.tags or '—'}    评分：{a.score:.1f}"))
            detail_btn = QPushButton("详情")
            detail_btn.clicked.connect(lambda _, aid=a.id: self._show_detail(aid))
            c.addWidget(detail_btn)
            if self.user and self.user.role == 'admin':
                del_btn = QPushButton("删除")
                del_btn.clicked.connect(lambda _, aid=a.id, card=card: self._delete_algo(aid, card))
                c.addWidget(del_btn)
            self.search_vbox.addWidget(card)

    def _delete_algo(self, aid, card):
        if QMessageBox.question(self, "确认", "确定要删除此算法？") != QMessageBox.Yes:
            return
        try:
            logic.delete_algo(self.user, aid)
            card.deleteLater()
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    # ─── 待 审 核 列 表 ───────────────────────────────────────────
    def _build_review(self):
        self.review_page = QWidget()
        layout = QVBoxLayout(self.review_page)
        layout.addWidget(QLabel("待审核算法", alignment=QtCore.Qt.AlignCenter))
        self.review_scroll    = QScrollArea(); self.review_scroll.setWidgetResizable(True)
        self.review_container = QWidget(); self.review_vbox = QVBoxLayout(self.review_container)
        self.review_scroll.setWidget(self.review_container)
        layout.addWidget(self.review_scroll)
        layout.addWidget(QPushButton("🔙 返回", clicked=lambda: self.stack.setCurrentWidget(self.main_page)))
        self.stack.addWidget(self.review_page)

    def _show_review_page(self):
        self._do_review()
        self.stack.setCurrentWidget(self.review_page)

    def _do_review(self):
        for i in reversed(range(self.review_vbox.count())):
            self.review_vbox.itemAt(i).widget().deleteLater()
        pending = logic.list_pending()
        for a in pending:
            card = QFrame(); card.setFrameShape(QFrame.Box)
            c = QHBoxLayout(card)
            c.addWidget(QLabel(f"{a.id}. {a.title}    作者：{a.owner.username}"))
            detail_btn = QPushButton("审核详情")
            detail_btn.clicked.connect(lambda _, aid=a.id, card=card: self._show_review_detail(aid, card))
            c.addWidget(detail_btn)
            del_btn = QPushButton("删除")
            del_btn.clicked.connect(lambda _, aid=a.id, card=card: self._delete_algo(aid, card))
            c.addWidget(del_btn)
            self.review_vbox.addWidget(card)

    # ─── 详 情 弹 窗 ─────────────────────────────────────────────
    def _show_detail(self, aid):
        algo = logic.get_algo_detail(aid)
        dlg = DetailDialog(self, algo, is_review=False)
        dlg.exec_()

    def _show_review_detail(self, aid, parent_card):
        algo = logic.get_algo_detail(aid)
        dlg = DetailDialog(
            self, algo, is_review=True,
            review_callback=lambda _: parent_card.deleteLater()
        )
        dlg.exec_()

    # ─── 调 整 评 分 策 略 ────────────────────────────────────────
    def _build_strategy(self):
        self.strategy_page = QWidget()
        layout = QVBoxLayout(self.strategy_page)
        layout.addWidget(QLabel("调整评分策略", alignment=QtCore.Qt.AlignCenter))

        curr = logic.get_scoring_strategy()
        layout.addWidget(QLabel(f"当前权重 — 函数: {curr['func_weight']}  注释: {curr['comment_weight']}"))

        form = QHBoxLayout()
        self.strat_func = QSpinBox(); self.strat_func.setRange(0,100)
        self.strat_func.setValue(curr['func_weight'])
        self.strat_comm = QSpinBox(); self.strat_comm.setRange(0,100)
        self.strat_comm.setValue(curr['comment_weight'])
        form.addWidget(QLabel("函数权重:")); form.addWidget(self.strat_func)
        form.addWidget(QLabel("注释权重:")); form.addWidget(self.strat_comm)
        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addWidget(QPushButton("💾 保存策略", clicked=self._save_strategy))
        btns.addWidget(QPushButton("🔙 返回上一页", clicked=lambda: self.stack.setCurrentWidget(self.main_page)))
        btns.addWidget(QPushButton("📈 评分历史记录", clicked=self._show_strategy_history))
        layout.addLayout(btns)

        self.stack.addWidget(self.strategy_page)

    def _show_strategy_page(self):
        curr = logic.get_scoring_strategy()
        self.strat_func.setValue(curr['func_weight'])
        self.strat_comm.setValue(curr['comment_weight'])
        self.stack.setCurrentWidget(self.strategy_page)

    def _save_strategy(self):
        fw, cw = self.strat_func.value(), self.strat_comm.value()
        try:
            logic.update_scoring(self.user, fw, cw)
            QMessageBox.information(self, "完成", "评分策略已保存")
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def _show_strategy_history(self):
        history = logic.get_strategy_history()
        dlg = QDialog(self)
        dlg.setWindowTitle("评分策略历史")
        v = QVBoxLayout(dlg)
        for rec in history:
            v.addWidget(QLabel(f"{rec['time']}: 管理员 {rec['admin']} → {rec['action']}"))
        dlg.exec_()

    # ─── 平 台 统 计 ───────────────────────────────────────────────
    def _build_stats(self):
        # 统计页面
        self.stats_page = QWidget()
        layout = QVBoxLayout(self.stats_page)

        # 标题
        title = QLabel("查看平台统计数据", alignment=QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-size:16px; font-weight:bold;")
        layout.addWidget(title)

        # 1. 统计数据概览（静态展示区）
        overview = QPushButton("📊 统计数据概览")
        overview.setEnabled(False)
        overview.setStyleSheet("text-align:left; padding:10px;")
        layout.addWidget(overview)

        # 2. 选择数据类型
        tlay = QHBoxLayout()
        tlay.addWidget(QLabel("📈 数据类型："))
        self.stats_type = QComboBox()
        self.stats_type.addItems([
            "算法总数",
            "用户总数",
            "待审核算法",
            "已通过算法",
            "评论总数",
            "下载总数"
        ])
        self.stats_type.currentIndexChanged.connect(self._refresh_stats)
        tlay.addWidget(self.stats_type)
        layout.addLayout(tlay)

        # 3. 时间范围选择
        drlay = QHBoxLayout()
        drlay.addWidget(QLabel("📅 起始日期："))
        self.start_date = QDateEdit(QtCore.QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        drlay.addWidget(self.start_date)
        drlay.addWidget(QLabel("至"))
        self.end_date = QDateEdit(QtCore.QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        drlay.addWidget(self.end_date)
        self.start_date.dateChanged.connect(self._refresh_stats)
        self.end_date.dateChanged.connect(self._refresh_stats)
        layout.addLayout(drlay)

        # 4. 图表展示区（空白盒子，后续可嵌 matplotlib 图）
        self.chart_frame = QFrame()
        self.chart_frame.setFrameShape(QFrame.StyledPanel)
        self.chart_frame.setMinimumHeight(300)
        layout.addWidget(self.chart_frame)

        # 5. 底部按钮：刷新 & 导出
        blay = QHBoxLayout()
        refresh_btn = QPushButton("🔄 刷新数据")
        refresh_btn.clicked.connect(self._refresh_stats)
        blay.addWidget(refresh_btn)

        export_btn = QPushButton("📤 导出数据")
        export_btn.clicked.connect(self._export_stats)
        blay.addWidget(export_btn)

        blay.addWidget(QPushButton("🔙 返回", clicked=lambda: self.stack.setCurrentWidget(self.main_page)))

        layout.addLayout(blay)

        # 将该页面加入堆栈
        self.stack.addWidget(self.stats_page)

    def _show_stats(self):
        # 切到统计页面并首次加载
        self.stack.setCurrentWidget(self.stats_page)
        self._refresh_stats()

    def _refresh_stats(self):
        """
        根据当前选择的数据类型和日期范围，从 logic 获取数据并绘制到 chart_frame。
        目前先清空 chart_frame，并展示一个简单文本占位。
        """
        # 清空旧内容
        for w in self.chart_frame.children():
            w.deleteLater()

        dtype = self.stats_type.currentText()
        start = self.start_date.date().toPyDate()
        end   = self.end_date.date().toPyDate()

        # 调用逻辑层获取（示例接口，需在 logic.py 实现）
        try:
            data = logic.get_stats_data(dtype, start, end)
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
            return

        # 暂时用文本占位
        lbl = QLabel(f"{dtype} 从 {start} 到 {end} 的数据：\n{data}")
        lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.chart_frame.layout() or self.chart_frame.setLayout(QVBoxLayout())
        self.chart_frame.layout().addWidget(lbl)


    def _export_stats(self):
        """
        导出当前统计数据到 CSV
        """
        dtype = self.stats_type.currentText()
        start = self.start_date.date().toPyDate()
        end   = self.end_date.date().toPyDate()
        try:
            csv_text = logic.export_stats_csv(dtype, start, end)
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "导出 CSV", f"{dtype}_{start}_{end}.csv", "CSV Files (*.csv)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(csv_text)
                QMessageBox.information(self, "完成", "已成功导出数据")
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = App()
    win.show()
    sys.exit(app.exec_())