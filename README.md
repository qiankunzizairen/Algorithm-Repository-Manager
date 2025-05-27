# Algorithm Repository Manager

**Algorithm Repository Manager** 是一个使用 Python 全栈（SQLAlchemy + PyQt5）开发的本地化算法库管理工具，支持算法上传、检索、评分、评论、审核、下载、统计等全流程功能。

## 目录结构

```
Algorithm Repository Manager/
│
├── config.py      # 全局配置：数据库凭据、默认账号、常量
├── db.py          # 数据库连接与初始化逻辑
├── models.py      # ORM 模型定义：User、Algorithm、Comment、DownloadLog、ScoringStrategy、AdminLog 等
├── dao.py         # 数据访问对象（DAO）：对 models 执行增删改查操作，并包含事务回滚、预加载等逻辑
├── logic.py       # 业务逻辑层：封装权限检查、事务调用、跨 DAO 操作，如上传算法、审核、评论、下载、统计、策略更新等
├── gui.py         # GUI 层：基于 PyQt5 实现的多页面应用，包括登录/注册、上传/检索/审核/详情/统计/策略等各功能模块
├── main.py        # 启动脚本：初始化数据库（建表、默认账号）后，创建并运行 QApplication
└── teardown.py*   # 可选：测试用脚本，清空或重建数据库环境 (*未列出)
```

## 功能概览

- **用户管理**：注册、登录；角色区分（普通用户 / 管理员）。
- **算法上传**：支持标题、分类、标签、描述、源码输入；自动计算函数/注释得分。
- **算法检索**：关键词 + 分类过滤，卡片式展示算法标题、作者、标签、评分；详情页预览代码、描述。
- **评论与评分**：用户可对算法打分 (1–5) 并发表评论；评论实时展示。
- **下载**：用户可将算法源码导出到 `.py` 文件。
- **管理员审核**：管理员可查看待审核算法详情，执行通过/驳回/删除操作。
- **删除评论/算法**：管理员可在详情页删除违规评论或在列表页删除算法条目。
- **评分策略管理** ：管理员可查看/修改函数和注释权重，保存后批量重算所有算法分数，并可查看历史记录。
- **平台统计** ：支持查看算法总数、用户总数、待审核/已通过算法数、评论总数、下载总数；可按日期区间刷新并导出 CSV。

## 快速开始

1. **安装依赖**：
   ```bash
   pip install PyQt5 sqlalchemy pymysql bcrypt mysql-connector-python
   ```
2. **配置数据库**：在 `config.py` 中填入：
   ```python
   DB_ROOT_USER = 'root'#请使用root身份
   DB_ROOT_PWD  = 'root_password'#这里请替换为你的MySQL密码
   ```
3. **初始化数据库**：
   ```bash
   python main.py
   ```
   - 程序会自动创建数据库表并插入默认评分策略、管理员帐号等。
4. **运行应用**：
   - 在登录界面使用默认管理员 `admin/admin123` 或注册新用户。
   - 普通用户可上传、检索、评论、下载算法；管理员可审核、删除、修改策略、查看统计。
5. **测试用例**：
   - 在attachments文件目录中

| 标题                   | 分类     | 标签               | 描述                                                                                                 |
|------------------------|----------|--------------------|------------------------------------------------------------------------------------------------------|
| SelectionSort          | 排序     | 小规模数据排序     | 这段代码实现了选择排序算法，通过每次从未排序部分选出最小值并交换到已排序部分的末尾，逐步完成升序排列。 |
| Kruskal                | 图算法   | 最小生成树         | 这段代码使用 Kruskal 算法实现了无向图的最小生成树求解。                                             |
| BinarySearch           | 查找     | 有序数组查找       | 这段代码实现了二分查找算法，用于在已排序的数组中高效查找目标值。                                     |
| DynamicProgramming     | 动态规划 | 背包问题           | 这段代码实现了经典的 0-1 背包问题动态规划解法，用于在给定背包容量限制下计算能装入物品的最大总价值。     |
    

## 模块说明

### config.py
- 定义所有环境相关常量与凭据，且不依赖其他模块。用于统一管理。

### db.py
- `init_db()`：连接 MySQL，创建 `algodb` 数据库（如果不存在），并调用 `models.init_models()` 初始化表结构。

### models.py
- 使用 SQLAlchemy 定义模型：
  - `User`、`Algorithm`、`Comment`、`DownloadLog`、`ScoringStrategy`、`AdminLog`。
  - 每个模型对应数据库表，并封装关系、默认值、时间戳等。

### dao.py
- DAO 层封装：
  - `UserDAO`、`AlgorithmDAO`、`CommentDAO`、`DownloadLogDAO`、`ScoringStrategyDAO`、`StatsDAO`。
  - 每个静态方法包含：创建会话、执行查询/更新、事务 rollback、session.close()，保证安全。
  - `AlgorithmDAO.recalculate_all_scores()` 用于重新批量计算算法得分。

### logic.py
- 业务逻辑层：
  - 封装用户注册、认证，调用 `UserDAO`。
  - 封装算法上传、检索、详情，调用 `AlgorithmDAO`。
  - 审核、删除算法调用 `AlgorithmDAO.delete()` 和 `CommentDAO.delete()`。
  - 评论提交与删除调用 `CommentDAO`。
  - 策略管理调用 `ScoringStrategyDAO` 并触发 `recalculate_all_scores()`。
  - 统计数据调用 `StatsDAO.get_stats()`，并导出 CSV。

### gui.py
- PyQt5 界面：
  - `App` 类管理多页面切换（登录、主菜单、上传、检索、审核、策略、统计）。
  - `DetailDialog` 弹窗展示算法详情、代码预览、评论列表、评论提交、下载、审核/删除等操作。
  - 页面的控件布局、信号槽连接、角色显隐逻辑等均在此实现。

### main.py
- 程序启动入口：
  1. 读取 `config.py`，调用 `db.init_db()` 初始化数据库。
  2. 创建 `QApplication`、`App` 窗口并启动事件循环。

## 测试与清理

- **清理脚本**：`teardown.py`（可手动创建）支持删除所有表或重建数据库，保证测试环境干净。

---

## 附录：如果你使用的是windows系统，也许需要一些额外的配置工作
- 预先创建普通用户/数据库：
  1. 进入MySQL：
  ```bash
  mysql -u root -p
  ```
  2. 创建用户和数据库：
  ```sql
  CREATE USER 'algouser'@'localhost' IDENTIFIED BY 'password';
  CREATE DATABASE algodb;
  ```
  3. 授予权限：
  ```sql
  GRANT ALL PRIVILEGES ON algodb.* TO 'algouser'@'localhost';
  ALTER USER 'algouser'@'localhost' IDENTIFIED BY 'password';
  FLUSH PRIVILEGES;
  ```
- 对于 `MySQL8.0` 及以上版本：
  使用 `caching_sha2_password` 认证方式，你需要确保你的客户端支持该认证插件。否则，你可能会遇到认证失败的情况。

  - 在 MySQL 8.0 中，默认的认证插件是 `caching_sha2_password`，但如果你的客户端不支持该插件，可以考虑切换到 `mysql_native_password`，或者升级客户端以支持新的认证方式。
- 常见错误：`cryptography' package is required for sha256_password or caching_sha2_password auth methods`

  - 这个错误表明你需要安装 `cryptography` 包来支持 `MySQL` 的加密连接。你可以通过以下命令安装该包：
  ```bash
  pip install cryptography
  ```