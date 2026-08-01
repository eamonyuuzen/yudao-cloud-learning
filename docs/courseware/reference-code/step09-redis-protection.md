# Step 09 Reference：幂等、限流与锁

```text
status: READY-DESIGN
depends_on: Step 07 claim + Step 08 job
```

## 0. 集成前置

当前 `yudao-module-system-server/pom.xml` 中 protection starter 仍被注释。
使用 `@Idempotent`、`@RateLimiter` 前必须显式启用：

```xml
<dependency>
    <groupId>cn.iocoder.cloud</groupId>
    <artifactId>yudao-spring-boot-starter-protection</artifactId>
</dependency>
```

同步修改：

```text
InternshipTaskJobDO.requestId
createJob 的 ReqVO、Service 参数与 insert 赋值
重复键后的稳定错误/既有 job 查询
Controller 的 @Idempotent
ErrorCodeConstants
src/test/resources/sql/create_tables.sql
src/test/resources/sql/clean.sql
```

## 1. 认领请求改成显式幂等契约

```java
@Data
public class InternshipTaskClaimReqVO {

    @NotNull(message = "实习任务编号不能为空")
    private Long id;

    @NotBlank(message = "请求编号不能为空")
    @Size(max = 64, message = "请求编号长度不能超过 64")
    private String requestId;
}
```

客户端每次新的业务意图生成一个 UUID；同一任务的同一次超时重试复用同一个
`requestId`。本阶段采用现有 `UserIdempotentKeyResolver`，所以“同一请求”
严格定义为：同一方法、同一用户身份、同一任务参数和同一 `requestId`。

Controller：

```java
@PutMapping("/claim")
@PreAuthorize("@ss.hasPermission('internship:task:claim')")
@Idempotent(
        timeout = 30,
        timeUnit = TimeUnit.SECONDS,
        keyResolver = UserIdempotentKeyResolver.class)
public CommonResult<Boolean> claimInternshipTask(
        @Valid @RequestBody InternshipTaskClaimReqVO reqVO) {
    internshipTaskService.claimInternshipTask(reqVO.getId(), getLoginUserId());
    return CommonResult.success(true);
}
```

当前 `UserIdempotentKeyResolver` 使用“方法 + 全部参数 + userId + userType”，
能把不同用户和参数分开。因此同一用户复用同一 `requestId` 却更换 `taskId`，
会被视为另一个请求并放行；当前契约只保证“完整参数相同的重试”幂等，不把
`requestId` 定义成该用户全局唯一意图。若产品需要后者，应改用专用 Resolver，
并把 `tenantId + userId + requestId` 作为稳定身份，必要时持久化该意图。

### 语义边界

当前 Yudao `@Idempotent`：

- Redis Key 只短期存在；
- 默认业务异常时删除 Key；
- 成功后等待 TTL；
- 它返回“重复请求”，不会自动重放第一次的响应。

如果产品要求重复 `requestId` 返回完全相同响应，需要单独的幂等记录表/响应缓存，不应误称当前注解已经实现。

## 2. 创建异步 job 的幂等

ReqVO：

```java
@Data
public class InternshipTaskJobCreateReqVO {

    @NotBlank
    @Size(max = 64)
    private String requestId;

    @NotBlank
    @InEnum(InternshipTaskJobTypeEnum.class)
    private String jobType;
}
```

`@InEnum` 没有 `property` 属性；枚举必须实现 Yudao 的 `ArrayValuable`：

```java
@Getter
@AllArgsConstructor
public enum InternshipTaskJobTypeEnum implements ArrayValuable<String> {

    TASK_REPORT("TASK_REPORT");

    public static final String[] ARRAYS = Arrays.stream(values())
            .map(InternshipTaskJobTypeEnum::getType)
            .toArray(String[]::new);

    private final String type;

    @Override
    public String[] array() {
        return ARRAYS;
    }
}
```

数据库增加最终约束：

```sql
ALTER TABLE system_internship_task_job
    ADD COLUMN request_id varchar(64) NULL COMMENT '幂等请求编号';

-- 回填旧数据并验证 tenant + requester + requestId 唯一后：
ALTER TABLE system_internship_task_job
    MODIFY request_id varchar(64) NOT NULL,
    ADD UNIQUE KEY uk_tenant_user_request
        (tenant_id, requester_user_id, request_id);
```

已有表不能直接假设没有旧数据；`nullable → 回填 → 验证 → NOT NULL → 唯一索引`
才是可回滚的真实迁移顺序。

H2 每次从空库建表，不执行上面的生产迁移。直接修改 Step 08 的
`create_tables.sql` job 表：

```sql
-- 紧跟 "requester_user_id" 字段之后加入
"request_id" varchar(64) NOT NULL,

-- 把原 PRIMARY KEY ("id") 改为
PRIMARY KEY ("id"),
CONSTRAINT "uk_internship_job_tenant_user_request"
    UNIQUE ("tenant_id", "requester_user_id", "request_id")
```

`clean.sql` 继续保留：

```sql
DELETE FROM "system_internship_task_job";
```

Redis 注解负责快速拒绝；数据库唯一索引负责 Redis 丢失或 TTL 过期后的最终不重复。

`InternshipTaskJobDO` 和 Mapper：

```java
// InternshipTaskJobDO
private String requestId;

// InternshipTaskJobMapper
default InternshipTaskJobDO selectByRequest(
        Long requesterUserId, String requestId) {
    return selectOne(
            InternshipTaskJobDO::getRequesterUserId, requesterUserId,
            InternshipTaskJobDO::getRequestId, requestId);
}
```

Controller 必须把 `requestId` 真正送入 Service，而不是只在 VO 中声明：

```java
@PostMapping("/job/create")
@PreAuthorize("@ss.hasPermission('internship:task:job:create')")
@Idempotent(
        timeout = 60,
        timeUnit = TimeUnit.SECONDS,
        keyResolver = UserIdempotentKeyResolver.class)
public CommonResult<Long> createJob(
        @Valid @RequestBody InternshipTaskJobCreateReqVO reqVO) {
    return CommonResult.success(internshipTaskJobService.createJob(
            reqVO.getJobType(), reqVO.getRequestId(), getLoginUserId()));
}
```

Step 08 的 `createJob` 替换为下面的入口；只有新插入成功的调用才提交 Worker：

```java
@Override
public Long createJob(
        String jobType, String requestId, Long requesterUserId) {
    Long tenantId = TenantContextHolder.getRequiredTenantId();
    InternshipTaskJobDO job = new InternshipTaskJobDO();
    job.setJobType(jobType);
    job.setRequestId(requestId);
    job.setRequesterUserId(requesterUserId);
    job.setTenantId(tenantId);
    job.setStatus(InternshipTaskJobStatusEnum.PENDING.getStatus());
    job.setProgress(0);
    try {
        jobMapper.insert(job);
    } catch (DuplicateKeyException ex) {
        InternshipTaskJobDO existing =
                jobMapper.selectByRequest(requesterUserId, requestId);
        if (existing != null) {
            throw exception(
                    INTERNSHIP_TASK_JOB_REQUEST_DUPLICATE,
                    existing.getId());
        }
        // 不是本业务唯一键的冲突，不能伪装成“重复请求”。
        throw ex;
    }

    try {
        jobWorker.execute(job.getId(), tenantId);
    } catch (TaskRejectedException ex) {
        jobMapper.rejectJob(
                job.getId(), "QUEUE_FULL", "后台任务队列已满");
    }
    return job.getId();
}
```

快速重复通常先被 Redis 切面拒绝；Redis Key 过期或丢失后的重复由数据库唯一
索引裁决，并返回包含既有 `jobId` 的稳定业务错误。第一版不自动重放第一次的
HTTP 成功响应。

本阶段新增错误码：

```java
ErrorCode INTERNSHIP_TASK_BUSY =
        new ErrorCode(1_002_029_005, "实习任务正在处理中，请稍后重试");
ErrorCode INTERNSHIP_TASK_JOB_REQUEST_DUPLICATE =
        new ErrorCode(1_002_029_006, "请求已提交，对应 Job 编号为 {}");
```

## 3. 查询限流

Controller 的分页查询：

```java
@GetMapping("/page")
@PreAuthorize("@ss.hasPermission('internship:task:query')")
@RateLimiter(
        time = 1,
        timeUnit = TimeUnit.SECONDS,
        count = 10,
        keyResolver = InternshipTaskQueryUserRateLimiterKeyResolver.class,
        message = "实习任务查询过于频繁，请稍后重试")
public CommonResult<PageResult<InternshipTaskRespVO>> getInternshipTaskPage(
        @Validated InternshipTaskPageReqVO reqVO) {
    // 原有实现
}
```

Yudao 自带的 `UserRateLimiterKeyResolver` 会把全部方法参数也加入 Key，改变
`pageNo/title` 就会换桶。若契约是“同一用户对整个分页接口共用一个桶”，使用
不含业务参数的自定义 Resolver：

```java
@Component
public class InternshipTaskQueryUserRateLimiterKeyResolver
        implements RateLimiterKeyResolver {

    @Override
    public String resolver(JoinPoint joinPoint, RateLimiter rateLimiter) {
        String method = joinPoint.getSignature().toString();
        Long userId = WebFrameworkUtils.getLoginUserId();
        Integer userType = WebFrameworkUtils.getLoginUserType();
        return SecureUtil.md5(method + ":" + userId + ":" + userType);
    }
}
```

运行时必须验证不同用户互不影响、同用户改变分页参数仍共用一个桶。

Agent Python 入口可以另设更低速率，但 Java 接口仍保留自己的保护，不信任所有调用方都会自律。

## 4. 分布式锁 DAO（仅对照实验）

```java
@Repository
public class InternshipTaskLockRedisDAO {

    private static final String LOCK_KEY = "internship:task:lock:%d";

    @Resource
    private RedissonClient redissonClient;

    public void runWithTaskLock(
            Long taskId,
            Duration wait,
            Duration lease,
            Runnable action) {
        RLock lock = redissonClient.getLock(
                String.format(LOCK_KEY, taskId));
        boolean acquired;
        try {
            acquired = lock.tryLock(
                    wait.toMillis(),
                    lease.toMillis(),
                    TimeUnit.MILLISECONDS);
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw exception(INTERNSHIP_TASK_BUSY);
        }
        if (!acquired) {
            throw exception(INTERNSHIP_TASK_BUSY);
        }
        try {
            action.run();
        } finally {
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }
}
```

锁包装 Service 与事务 Service 必须是两个 Bean：

```java
@Service
public class InternshipTaskClaimLockService {

    @Resource
    private InternshipTaskLockRedisDAO lockRedisDAO;
    @Resource
    private InternshipTaskService internshipTaskService;

    public void claimWithRedisLock(Long taskId, Long userId) {
        lockRedisDAO.runWithTaskLock(
                taskId,
                Duration.ofMillis(200),
                Duration.ofSeconds(3),
                () -> internshipTaskService.claimInternshipTask(
                        taskId, userId));
    }
}
```

这样 `claimInternshipTask` 会经过另一个 Spring 代理，`@Transactional` 才生效。
若在同一个 Service 内 `this.claimInternshipTask(...)`，会绕过事务代理，可能
出现“任务已更新、认领记录失败却无法回滚”。

这段不是默认生产答案。即使加锁，事务 Service 中的数据库原子条件和唯一约束仍保留。

## 5. Key 清单

| 机制 | Key 示例 | TTL | 最终事实 |
|---|---|---:|---|
| claim 幂等 | 框架 Key：方法 + 用户 + taskId + requestId | 30s | Task/Claim MySQL |
| job 幂等 | `idempotent:job:uuid` | 60s | Job 唯一索引 |
| task 锁 | `internship:task:lock:10` | 3s | Task 原子条件 |
| query 限流 | 框架 resolver Key | 1s | 无写事实 |

实际框架会加统一前缀；用 Redis CLI 观察真实 Key 后再更新表格。

## 6. 测试矩阵

### 幂等

```text
同一 taskId + requestId 并发/顺序提交 10 次
→ Service 业务成功 1 次
→ Claim 记录 1 条
→ 重复请求得到明确重复语义

同一用户、同一 requestId、不同 taskId
→ 按本阶段契约视为两个不同完整请求
→ 两个任务仍分别由数据库不变量裁决
```

注意：切面测试必须让调用经过 Spring 代理；直接 `new Controller()` 或直接调用目标对象不能证明 `@Idempotent` 生效。

### 限流

```text
同用户 1 秒 20 次
→ 约 10 次放行，其余限流（按算法实际边界记录）
→ Service 调用次数与放行数一致

两个不同用户各请求
→ Key 不应互相挤占
```

### 锁

```text
10 worker 同 taskId
→ 最终认领成功 1
→ 即使将 lease 设置过短，数据库底线仍不允许覆盖
```

### Redis 停机

实验 A 整体停 Redis，只记录第一故障边界：

```text
Token 是否先失败
```

如果 Token 先失败，不能据此判断幂等/限流策略。实验 B 使用已认证测试上下文，
分别让幂等 DAO、限流 DAO 抛异常，一次只验证一个 fail-open/fail-closed 决策。

不能在同一轮同时把所有 Redis 用途改为降级；先观察真实第一故障边界。
