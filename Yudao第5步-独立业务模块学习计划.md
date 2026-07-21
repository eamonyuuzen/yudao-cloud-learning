# Yudao 第 5 步：独立业务模块学习计划

> 目标：从“能跟着现有源码理解一条链”进入“能自己建模、定位参考、实现、验证并解释一个完整业务纵向切片”。

## 1. 为什么第 5 步要这样安排

第 4 步的价值不是记住所有 Filter、Adapter 和缓存函数，而是建立了一个请求进入复杂系统后的初步模型：

```text
外部请求
→ 公共入口与进门检查
→ 协议/对象转换
→ 业务决策
→ 数据访问或外部副作用
→ 返回结果
```

暴露的问题也很明确：模块多、组件更多，如果每遇到一个类就向下追到底，主线会被框架细节淹没；如果只画一张大图，又无法独立写出真实功能。

因此第 5 步采用：

```text
先建立可工作的粗模型
→ 每轮只完成一个可验证的纵向切片
→ 只进入会改变业务规则、状态、信任或失败结果的细节
→ 每轮结束立即回到整体图
→ 最后由自己重新抽象，而不是复制调用链
```

## 2. 业务范围与架构决策

### 2.1 第一版业务

实现“后台实习任务台账”：

```text
任务分页
查看详情
新增任务
编辑任务
删除任务
状态流转
按标题、状态、创建时间筛选
权限控制
```

第一版只有授权后台用户管理任务，不做：

```text
导师分派任务给实习生
个人任务数据隔离
评论、附件、提醒、审批
消息队列、WebSocket、定时任务
```

这些不是功能不存在，而是进入停车场，等核心闭环完成后再决定是否升级。

### 2.2 放在哪里

第一版放进现有 `system-server`，作为一个边界清楚的业务包：

```text
yudao-module-system
├─ yudao-module-system-api
│  └─ enums/internship
└─ yudao-module-system-server
   ├─ controller/admin/internship
   ├─ service/internship
   ├─ dal/dataobject/internship
   └─ dal/mysql/internship
```

数据库表暂定：

```text
system_internship_task
```

这样选择的原因：

- 当前目标是独立完成业务纵向切片，不是提前学习新微服务接入；
- 复用已经跑通的 Gateway、认证、权限、Nacos 和 system-server 进程；
- 未来若任务领域变复杂，可以依据包和表边界迁移为独立服务；
- “未来可拆”不等于“现在就拆”。新服务注册、路由、Feign 和容错留到第 11 步。

## 3. 业务模型先于代码

### 3.1 核心对象

```text
InternshipTask
├─ id：身份
├─ title：任务标题，必填
├─ description：任务说明
├─ status：当前状态
├─ deadline：截止时间，可空
└─ BaseDO 字段：创建者、创建时间、更新者、更新时间、逻辑删除
```

### 3.2 状态模型

第一版只允许向前流转：

```text
TODO
→ IN_PROGRESS
→ DONE
```

业务规则：

```text
新任务默认 TODO
TODO 只能开始为 IN_PROGRESS
IN_PROGRESS 只能完成为 DONE
DONE 是第一版终态
重复提交相同状态不产生新变化
非法跨越状态要返回明确业务错误
```

状态值暂定：

```text
0 → TODO
1 → IN_PROGRESS
2 → DONE
```

具体数字是项目实现；“状态迁移必须受控”才是可迁移的业务规则。

### 3.3 权限模型

```text
internship:task:query
internship:task:create
internship:task:update
internship:task:delete
internship:task:update-status
```

冒号只是命名约定。每个字符串是否真正保护了对应动作，要由 Controller 注解、菜单权限记录和普通角色验证共同证明。

## 4. 一次请求的整体模型

```text
用户在页面操作
→ Vue 页面收集输入并展示状态
→ 前端 API 把数据转换为 HTTP 请求
→ Gateway / Security 负责已有的通用进门检查
→ Controller 接收请求、校验格式、检查动作权限
→ Service 判断任务是否存在、状态是否允许变化
→ Mapper 把查询或写入交给 MySQL
→ DO / RespVO 转换
→ CommonResult 返回前端
→ 页面刷新或显示错误
```

责任分类：

| 层 | 本轮主要职责 | 是否做业务决策 |
|---|---|---:|
| Gateway / Filter | 通用身份运输和认证 | 否，复用黑盒 |
| Controller | HTTP 边界、参数校验、动作权限 | 少量边界决策 |
| Service | 存在性、状态迁移、业务错误 | 是，核心 |
| Mapper | 查询条件与持久化 | 只表达数据访问 |
| MySQL | 保存任务事实 | 状态事实来源 |
| 前端 API | 运输请求/响应 | 否 |
| Vue 页面 | 用户交互、展示、基础表单提示 | 不替代后端规则 |

以后组件再多，也先把它放进：

```text
入口 / 转译 / 决策 / 存储 / 展示
```

只有无法归类或改变边界时，才进一步下钻。

## 5. 唯一参考模块

第一轮只参考“通知公告”，不同时打开三个 CRUD 模块比较。

后端：

```text
controller/admin/notice/NoticeController
controller/admin/notice/vo/*
service/notice/NoticeService + NoticeServiceImpl
dal/dataobject/notice/NoticeDO
dal/mysql/notice/NoticeMapper
```

前端：

```text
src/api/system/notice/index.ts
src/views/system/notice/index.vue
src/views/system/notice/NoticeForm.vue
```

只复用它的：

```text
CRUD 文件骨架
分页请求方式
VO / DO 转换
权限注解位置
页面、API、表单协作方式
```

明确忽略：

```text
NoticeController 的 WebSocket push
通知类型等任务领域不需要的字段
与当前问题无关的框架父类内部实现
```

目标是“看出模式后重新写”，不是复制并全局替换名称。

## 6. 目标文件地图

### 6.1 后端

```text
yudao-module-system-api/
└─ .../enums/internship/
   └─ InternshipTaskStatusEnum.java

yudao-module-system-server/
└─ .../system/
   ├─ controller/admin/internship/
   │  ├─ InternshipTaskController.java
   │  └─ vo/
   │     ├─ InternshipTaskPageReqVO.java
   │     ├─ InternshipTaskSaveReqVO.java
   │     ├─ InternshipTaskUpdateStatusReqVO.java
   │     └─ InternshipTaskRespVO.java
   ├─ service/internship/
   │  ├─ InternshipTaskService.java
   │  └─ InternshipTaskServiceImpl.java
   ├─ dal/dataobject/internship/
   │  └─ InternshipTaskDO.java
   └─ dal/mysql/internship/
      └─ InternshipTaskMapper.java
```

还会增量更新：

```text
ErrorCodeConstants.java
SQL 建表与菜单权限脚本
```

### 6.2 前端

```text
src/api/internship/task/
└─ index.ts

src/views/internship/task/
├─ index.vue
└─ InternshipTaskForm.vue
```

## 7. 七轮实施与学习计划

每轮都遵守：

```text
一个根问题
→ 一张局部组件图
→ 用户先预测或写伪代码
→ 实现最小切片
→ 用一个正常结果和一个边界结果验证
→ 回到总图压缩职责
```

### 第 0 轮：冻结业务模型，不写代码

根问题：**系统允许谁对什么任务做什么，哪些状态变化合法？**

产物：

- 字段表；
- 状态图；
- 5 个权限字符串；
- 第一版包含/不包含清单；
- 三条业务不变量。

完成证据：能预测“直接把 TODO 改成 DONE”应该在哪一层拒绝以及为什么。

### 第 1 轮：参考模块与文件骨架

根问题：**一个业务能力分别需要哪些角色，哪些文件只是运输，哪个文件负责决策？**

动作：

- 只读 Notice 的文件树和 create/page 两条方法链；
- 用户先写目标文件清单和每个文件一句话职责；
- 创建后端和前端空骨架，不填完整实现。

完成证据：不看参考文件，也能画出页面到数据库的目标链路。

### 第 2 轮：先跑通“新增 + 分页”最小闭环

根问题：**一条任务怎样写入数据库，又怎样被分页查回？**

实现顺序：

```text
SQL 表
→ DO
→ SaveReqVO / PageReqVO
→ Mapper
→ Service create/page
→ Controller create/page
→ HTTP 验证
```

只实现新增和分页，暂不实现所有按钮。

完成证据：新增一条任务后，分页接口能按标题和状态查到；空标题被参数校验拒绝。

### 第 3 轮：补齐详情、编辑、删除与状态规则

根问题：**CRUD 与真正业务规则的边界在哪里？**

动作：

- 详情、编辑、删除；
- `updateStatus` 独立入口；
- Service 校验存在性和合法状态迁移；
- 增加明确业务错误码。

完成证据：合法迁移成功；`TODO → DONE` 被 Service 拒绝；不存在 ID 返回明确错误。

### 第 4 轮：前端列表与表单

根问题：**查询链和展示/编辑链怎样协作，又在哪里保持独立？**

实现顺序：

```text
前端 API 类型和函数
→ 列表查询、分页、筛选
→ 新增/编辑表单
→ 删除与状态按钮
→ 成功后刷新列表
```

完成证据：页面能完成完整 CRUD；后端错误可以被用户看见；刷新页面后数据仍来自数据库。

### 第 5 轮：菜单与权限

根问题：**页面可见、按钮可见和后端真正允许执行分别由谁保护？**

动作：

- 添加菜单与按钮权限；
- Controller 加 `@PreAuthorize`；
- 超级管理员验证成功；
- 普通角色至少验证一个允许和一个拒绝动作。

完成证据：没有 `delete` 权限的用户即使手工发 HTTP 请求也被拒绝，证明后端是最终边界。

### 第 6 轮：测试与回归

根问题：**什么证据能证明功能不仅“当前点起来正常”？**

最小矩阵：

```text
Service：创建成功
Service：非法状态迁移失败
API：分页筛选成功
API/运行：无权限动作失败
前端：新增、筛选、编辑、状态、删除冒烟通过
回归：原用户分页和邮箱筛选仍正常
```

第 6A 步再系统学习测试框架；本轮只建立最低可靠证据。

### 第 7 轮：架构复盘、笔记与 Git 收尾

由用户先完成压缩：

```text
一句话能力
核心对象、状态与动作
哪些层做决策，哪些层只运输
一条正常链和一条失败链
当前项目选择与未来可替换部分
如果拆成独立微服务，边界在哪里
```

然后再校正、更新正式笔记、检查前后端 Git 范围并分别提交。

## 8. 学习量与下钻预算

这些是默认预算，不是僵硬限制；当真实问题需要时可以调整，但必须说明原因。

### 每轮预算

```text
同时保持 1 个根问题
第一遍最多打开 5 个核心文件
只参考 1 个相似模块
一个解释簇默认只向下钻 1 层
支线细节最多同时保留 2 个，其余进入停车场
每轮必须有 1 个可观察证据
```

### 进入细节的条件

只有当细节满足任一条件才进入：

- 决定业务规则或状态迁移；
- 改变信任、权限或数据范围；
- 改变持久化、事务、并发或外部副作用；
- 决定失败类型和恢复方式；
- 当前实现或验证被它阻塞。

否则先当黑盒，只记录：

```text
它属于谁
输入是什么
输出是什么
是否改变状态或作决定
```

### 停止下钻的条件

当前层已经能够回答下面四点，就先返回总图：

```text
谁调用它？
它负责什么决定？
输入如何变成输出？
正常和一个失败分支是什么？
```

不要求把父类、工具方法、自动配置和所有缓存实现逐行读完。

## 9. 组件账本

每轮只维护当前活跃组件，不建立百科全书：

| 组件 | 所属进程/模块 | 一句话职责 | 输入 | 输出 | 决策/状态 | 当前深度 |
|---|---|---|---|---|---|---|
| Vue 页面 | 前端 | 收集输入、展示结果 | 用户操作 | API 参数/页面状态 | 展示 | 当前轮细读 |
| 前端 API | 前端 | HTTP 运输 | TS 对象 | HTTP Promise | 否 | 看接口即可 |
| Gateway/Security | 通用基础设施 | 恢复可信身份 | HTTP Token | LoginUser | 信任边界 | 第 4 步已学，复用 |
| Controller | system-server | API 边界与动作权限 | ReqVO | CommonResult | 少量 | 当前轮细读 |
| Service | system-server | 任务业务规则 | 业务参数 | 结果/异常 | 核心决策 | 当前轮细读 |
| Mapper | system-server | 数据访问 | 查询条件/DO | DO/PageResult | 持久化适配 | 当前轮细读 |
| MySQL | 外部状态 | 保存任务事实 | SQL | 行数据 | 真相源 | 看表和结果 |

遇到新组件时，先加入表格并归类，再决定是否值得打开源码。

## 10. 完成标准

### 功能

- 前后端 CRUD、筛选、分页和状态流转可用；
- 参数、存在性、状态和权限失败有明确结果；
- 数据库、菜单和权限配置完整；
- 最小测试与回归通过；
- 前后端 Git 提交范围清晰。

### 独立开发能力

- 不由 AI 直接给出全部代码，能根据参考模块自己建立文件和方法；
- 能说明为什么业务规则放在 Service，而不只会照抄 Controller/Mapper；
- 能在新错误出现时先定位责任层，再进入具体函数；
- 能区分项目通用基础设施、业务新增组件和未来演进组件。

### 架构抽象

最终能够不用类名复述：

```text
用户动作
→ 输入边界
→ 业务规则
→ 状态改变
→ 持久化
→ 输出与失败
```

并回答：如果未来加入任务分派、个人数据范围、通知或独立微服务，分别会改变哪一层，而不是把所有功能堆进当前实现。

## 11. 当前停车场

```text
任务负责人和个人数据权限
状态撤回与操作历史
附件与评论
截止时间提醒
WebSocket / MQ 通知
跨服务 API、Feign、超时和降级
独立 yudao-module-internship 微服务
```

停车场不是遗忘清单。核心闭环完成后，只根据真实价值挑选一个进入下一轮。

## 12. 第一个动作

第 5 步不从创建 Java 文件开始，而从第 0 轮开始：

> 用自己的话说明“实习任务台账”的使用者、字段、三种状态、合法状态变化，以及第一版明确不做什么。

完成这张业务模型卡后，才进入 Notice 参考模块和文件骨架。
