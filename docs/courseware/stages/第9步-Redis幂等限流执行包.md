# 第 9 步：Redis、幂等、限流与分布式锁执行包

> 建议用时：6～7 个有效学习日。
> 业务升级：保护任务认领和异步 job 入口，防止重复、并发冲突和短时洪峰。
> 完整参考实现由导师在用户完成建模/尝试后按规则解锁。

5 个核心 Session：第 1+2 日合并、3、4、6、7；第 5 日缓存专题是
OPTIONAL/附录，不阻塞第 10 步。

## 开工命令卡

前置状态：第 8 步 Job 测试通过；使用隔离的学习 Redis，先确认端口：

```powershell
Test-NetConnection localhost -Port 6379
```

AI 先创建 `InternshipTaskProtectionIntegrationTest` 骨架。第一条测试命令：

```powershell
mvn -pl yudao-module-system/yudao-module-system-server -am `
  "-Dtest=InternshipTaskProtectionIntegrationTest" `
  "-Dsurefire.failIfNoSpecifiedTests=false" test
```

第一轮预期 RED：protection 依赖/切面或业务 Key 尚未接好。完成后同一命令至少
证明：完整参数相同的 requestId 重试只产生一次副作用、同用户换分页参数仍共用限流桶、锁失败不破坏
数据库底线。Redis 实验前后记录准确 Key；只删除带本轮随机 requestId 的 Key，
不执行共享环境的广泛清库。

## 0. 先分清三个问题

### 锁

```text
问题：同一时刻有多个执行者争用同一资源
目标：同一锁粒度下暂时只允许一个执行
```

### 幂等

```text
问题：同一个业务意图因为重试、双击、超时再次提交
目标：重复执行不产生额外业务结果
```

### 限流

```text
问题：单位时间内请求过多，系统或下游承受不住
目标：控制进入速率，保护容量
```

现实比喻：

- 锁：卫生间门锁，同一时间只进一个人；
- 幂等：同一张取件码扫两次，只能取走同一个包裹一次；
- 限流：地铁闸机每分钟只放一定人数。

比喻边界：

- 有门锁不代表同一个人不能反复排队；
- 取件码幂等不限制很多不同取件码同时涌入；
- 闸机限流不保证进站后不会争抢同一个座位。

## 1. Redis 在本阶段扮演什么

Redis 适合保存：

```text
短期幂等键
限流计数/令牌
跨 JVM 协调锁
短期任务状态缓存
```

MySQL 仍保存：

```text
任务认领人
任务状态
job 最终状态
认领记录
审计事实
```

一句话：

> Redis 是门口的快速协调台，MySQL 是最终业务档案。协调台丢了不能让档案的基本不变量失效。

## 2. 第 1 日：用真实 Key 建立 Redis 模型

### 根问题

> Redis 中一条 Key 到底代表哪个业务事实，什么时候可以消失？

为三个机制设计 Key：

```text
幂等：
框架实际维度：{method}:{userType}:{userId}:{taskId}:{requestId}

锁：
internship:lock:task:{taskId}

限流：
由 RateLimiter KeyResolver 生成 user/IP/接口维度 Key
```

每个 Key 必须回答：

```text
谁创建？
谁读取？
值是什么？
TTL 多久？
TTL 到期后意味着什么？
是否能从 MySQL 恢复？
不同租户是否会冲突？
```

### Redis 数据结构只选够用的

| 结构 | 本阶段用途 |
|---|---|
| String | 幂等标记、简单缓存 |
| Hash | 可选的 job 状态摘要 |
| ZSet | 滑动窗口限流概念 |
| Stream | 第 10 步消息队列 |

List、Set、Bitmap、HyperLogLog 只知道用途，不做本阶段实验。

### 验收

能在 Redis CLI 中：

```text
GET
SET NX EX
TTL
DEL
SCAN
```

不使用生产环境 `KEYS *` 作为默认排查命令。

## 3. 第 2 日：幂等不是“加一个锁”

### 根问题

> 请求超时后，客户端不知道成功没成功，再次提交时系统怎样识别“同一个意图”？

### 幂等键来源

优先级：

```text
业务天然唯一键
→ 客户端生成 requestId
→ 服务端根据稳定字段生成键
→ 最后才考虑用户+接口的粗粒度短锁
```

认领任务的业务天然约束：

```text
taskId 最多一个认领人
```

数据库原子更新已经保证最终不重复，但客户端仍可能需要同一任务、同一
`requestId` 的重试得到一致语义。

本阶段直接复用 `UserIdempotentKeyResolver`，所以幂等身份还包含方法和全部
参数。同一用户拿相同 `requestId` 去认领另一个 `taskId`，会被视为另一个完整
请求。这是刻意收窄的第一版契约，不等于“requestId 在用户范围内全局唯一”。
若业务将来要求全局意图编号，再实现专用 Resolver，并考虑持久化请求结果。

“一致语义”分三级：

```text
一级：不产生第二次副作用
二级：重复时返回明确的重复错误
三级：重复时重放第一次相同的业务响应
```

当前 Yudao `@Idempotent` 主要提供一、二级，不自动保存并重放第一次响应。

### 两层保护

```text
Redis 幂等：
快速识别短时间内、完整参数相同的 requestId 重试

数据库条件/唯一约束：
即使 Redis 丢失、过期或绕过，最终业务仍不能重复
```

### 先读 Yudao 框架

核心文件：

第一入口：

1. [IdempotentAspect.java](../../../yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/idempotent/core/aop/IdempotentAspect.java)

按问题再打开：

2. [Idempotent.java](../../../yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/idempotent/core/annotation/Idempotent.java)
3. [IdempotentRedisDAO.java](../../../yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/idempotent/core/redis/IdempotentRedisDAO.java)
4. [UserIdempotentKeyResolver.java](../../../yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/idempotent/core/keyresolver/impl/UserIdempotentKeyResolver.java)
5. [ExpressionIdempotentKeyResolver.java](../../../yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/idempotent/core/keyresolver/impl/ExpressionIdempotentKeyResolver.java)

机制闭环：

```text
启动：
配置注册 Aspect 和 KeyResolver

运行：
代理先接住带 @Idempotent 的方法调用
→ 解析注解和 SpEL/用户上下文形成 Key
→ Redis SET NX 成功则放行
→ 已存在则拒绝重复
→ 根据框架语义决定何时删除或等待 TTL
```

必须看当前源码确认：

- 成功后 Key 是否保留；
- 业务异常后是否删除；
- TTL 默认值；
- KeyResolver 维度；
- 注解作用在 Controller 还是 Service 更合理。

### 实验

同一个 taskId、同一个 requestId 连续提交 10 次：

```text
成功业务结果数
重复拒绝数
MySQL 认领记录数
Redis Key 与 TTL
```

再做一个边界反例：保持用户和 `requestId` 不变，只更换 `taskId`。现有 Resolver
应生成不同 Key；这个实验用来证明当前保证的是“完整请求重试幂等”，而不是
“requestId 单独全局唯一”。

## 4. 第 3 日：分布式锁的完整生命周期

### 根问题

> 拿到锁之后进程宕机，锁怎样不永久泄漏？业务执行太久，锁又怎样不提前过期？

生命周期：

```text
根据 taskId 生成锁 Key
→ 尝试在等待上限内获取
→ 获取成功
→ 执行业务
→ finally 中只释放自己持有的锁
→ 获取失败则返回繁忙/稍后重试
```

### 必须掌握

- waitTime：最多等多久拿锁；
- leaseTime：锁自动过期时间；
- 看门狗/自动续期的使用条件；
- 可重入；
- 锁粒度；
- 进程宕机后的租期释放；
- 网络抖动和长 GC 时“以为自己还持锁”的风险；
- 锁只协调遵守同一协议的参与者。

### Yudao 参考

1. [PayWalletLockRedisDAO.java](../../../yudao-module-pay/yudao-module-pay-server/src/main/java/cn/iocoder/yudao/module/pay/dal/redis/wallet/PayWalletLockRedisDAO.java)
2. [PayNotifyLockRedisDAO.java](../../../yudao-module-pay/yudao-module-pay-server/src/main/java/cn/iocoder/yudao/module/pay/dal/redis/notify/PayNotifyLockRedisDAO.java)
3. Lock4j 配置与注解用例；
4. 当前钱包/支付 Service 怎样选择锁 Key。

### 本业务决策

任务认领的最终裁决仍用数据库条件更新。Redis 锁只作为对照实验，不成为唯一正确性来源。

原因：

```text
锁过期、Redis 故障或未遵守锁协议的代码仍可能进入
→ 数据库条件必须继续拒绝第二个认领者
```

### 实验

核心实验只用 10 个并发请求，比较两个版本：

| 版本 | 观察 |
|---|---|
| Redis 锁 + 数据库原子条件 | 最终不变量是否保持 |
| 只有数据库原子条件 | 正确性和性能是否已足够 |

通过结果决定是否保留锁，不因“分布式系统必须有锁”而增加复杂度。

“锁租期太短”另做两个请求的明确时间线；100 请求和“只有锁、普通更新”的
危险演示属于 OPTIONAL，避免一次改变并发数、锁和 SQL 三个变量。

## 5. 第 4 日：限流保护谁

### 根问题

> 允许每秒 10 次，是针对整个系统、某个接口、某个用户还是某个 IP？

维度：

```text
全局：保护整个服务
接口：保护特定昂贵能力
用户：防止单个账号占满容量
IP：保护匿名入口，但要考虑代理与共享出口
服务节点：保护单实例资源
```

任务查询/Agent 工具第一版建议：

```text
按 userId + 工具名限流
```

登录/注册可按 IP + 账号组合。

### Yudao 参考链

1. [RateLimiterAspect.java](../../../yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/ratelimiter/core/aop/RateLimiterAspect.java)
2. [RateLimiter.java](../../../yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/ratelimiter/core/annotation/RateLimiter.java)
3. [RateLimiterRedisDAO.java](../../../yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/ratelimiter/core/redis/RateLimiterRedisDAO.java)
4. [UserRateLimiterKeyResolver.java](../../../yudao-framework/yudao-spring-boot-starter-protection/src/main/java/cn/iocoder/yudao/framework/ratelimiter/core/keyresolver/impl/UserRateLimiterKeyResolver.java)
5. [AuthController.java](../../../yudao-module-system/yudao-module-system-server/src/main/java/cn/iocoder/yudao/module/system/controller/admin/auth/AuthController.java) 上的真实使用。

当前 `UserRateLimiterKeyResolver` 实际把“方法签名 + 全部参数 + userId +
userType”一起做成 Key。分页号或标题不同会换桶；它并不天然等于“该用户对
整个查询接口共用一个桶”。若业务要求 `userId + 工具名`，需实现自定义
Resolver，不能只改注解说明。

框架闭环：

```text
启动注册限流切面和 KeyResolver
→ 代理接住方法调用
→ 按注解选择 resolver
→ 生成限流 Key
→ Redis Lua 原子判断/扣令牌
→ 允许则 proceed
→ 拒绝则抛明确异常
```

### 实验

同一用户 1 秒请求 20 次：

记录：

```text
允许数
拒绝数
窗口恢复时间
HTTP/业务错误
不同用户是否互相影响
```

不要只看前端提示，要看后端实际执行次数。

## 6. 第 5 日：缓存问题只做四个代表案例

> OPTIONAL：第一次学习 Redis 保护时可整节跳过。本阶段只需记住“缓存不是
> 最终业务事实”；穿透、击穿、雪崩和复杂一致性以后另开专题。

本阶段不建设完整缓存层，只用任务详情缓存理解四个问题。

### 穿透

大量查询不存在的 taskId。

可选：

- 缓存短期空值；
- 参数/权限前置；
- Bloom Filter 作为后续概念。

### 击穿

一个热点 Key 过期瞬间，大量请求同时查数据库。

可选：

- 互斥重建；
- 逻辑过期；
- 提前刷新。

### 雪崩

大量 Key 同一时刻过期或 Redis 整体不可用。

可选：

- TTL 加随机抖动；
- 分批预热；
- 限流降级；
- 数据库容量保护。

### 一致性

MySQL 更新任务后缓存仍是旧值。

第一版模型：

```text
先更新数据库
→ 删除缓存
→ 下次读取重建
```

理解它仍有竞态，不把“双删”等方案当口诀；关键业务读必须明确能否容忍短期旧数据。

## 7. 第 6 日：Redis 不可用时怎样降级

### 分类

| Redis 用途 | Redis 不可用时 |
|---|---|
| 最终正确性的唯一锁 | 危险设计，应避免 |
| 幂等快速层 | 回退数据库唯一约束/状态检查 |
| 限流 | 按风险选择 fail-open 或 fail-closed |
| 普通缓存 | 回源 MySQL，但要保护数据库 |
| Token/会话 | 可能无法认证，需要明确不可用 |

### fail-open / fail-closed

```text
fail-open：
保护组件故障时仍放行
→ 可用性高，保护能力降低

fail-closed：
保护组件故障时拒绝
→ 安全/一致性高，可用性降低
```

例如：

- 普通任务查询限流故障可在小流量学习环境临时 fail-open 并报警；
- 支付防重或权限状态不能随便 fail-open。

### 故障实验 A：整体第一故障边界

停止 Redis：

```text
查询接口
认领接口
重复请求
限流接口
Token 认证
```

此实验只证明请求最先在哪里失败。在当前系统中 Token/会话很可能先失败，
此时根本没有到达幂等、限流或缓存逻辑，不能拿它证明各组件的降级策略。

### 故障实验 B：组件隔离

在已认证测试上下文中，让一种依赖单独抛出 Redis 异常：

```text
幂等 DAO 异常
限流 DAO 异常
缓存 DAO 异常
```

每次只替换一个组件，并在实验前写清“预计到达哪一层”。这样得到的证据才能
区分 fail-open/fail-closed，而不是把上游认证失败误认成下游降级。

## 8. 第 7 日：综合收口

### 三个接口设计

```text
PUT /internship-task/claim
→ 同用户、同 taskId、同 requestId 的重试幂等 + 数据库原子条件

POST /internship-task/job/create
→ 用户维度幂等，必要时限流

POST /agent/query
→ userId + toolName 限流，不加业务锁
```

### 回归矩阵

| 场景 | 主要机制 | 数据库底线 |
|---|---|---|
| 同 taskId + requestId 10 次 | 幂等 | 唯一记录/状态 |
| 同 requestId 换 taskId | 当前视为新请求 | 每个任务各自满足认领不变量 |
| 两用户同时认领 | 原子 SQL，可选锁 | 条件更新 |
| 同用户 1 秒 20 次查询 | 限流 | 只读 |
| Redis Key 过期 | 再次执行契约 | 数据库仍正确 |
| Redis 停机 | 降级策略 | 不变量不破坏 |
| 锁持有者宕机 | 租期 | 数据库继续裁决 |

### 最终复述

```text
锁协调“同时”
幂等识别“同一次意图的重复”
限流控制“单位时间的数量”
缓存优化“读取成本”
数据库约束和状态保存“最终业务事实”
```

### 进入第 10 步门槛

- 能为每个 Redis Key 说清业务含义和 TTL；
- 能解释 `SET NX` 的原子性作用；
- 运行过重复、并发和洪峰三个实验；
- 能说明锁为何不能替代幂等和数据库约束；
- 能为 Redis 故障选择并解释 fail-open/fail-closed；
- 没有在日志、Redis 或 Git 中保存真实 Token。
