# Step 10 Reference：任务状态事件

```text
status: READY-DESIGN
transport: Yudao Redis Stream
known_gap: DB commit 后 Redis send 失败需要第 14 步 Outbox 解决
```

## 1. 目标文件

```text
mq/message/internship/InternshipTaskStatusChangedMessage.java
mq/producer/internship/InternshipTaskStatusChangedProducer.java
mq/consumer/internship/InternshipTaskStatusChangedConsumer.java
controller/admin/internship/InternshipTaskController.java
service/internship/InternshipTaskService.java
service/internship/InternshipTaskServiceImpl.java
service/internship/InternshipTaskEventConsumeService.java
service/internship/InternshipTaskEventConsumeServiceImpl.java
dal/dataobject/internship/InternshipTaskEventAuditDO.java
dal/mysql/internship/InternshipTaskMapper.java
dal/mysql/internship/InternshipTaskEventAuditMapper.java
enums/ErrorCodeConstants.java
src/test/resources/sql/create_tables.sql
src/test/resources/sql/clean.sql
原 InternshipTask Service/Controller 测试
```

## 2. Message

```java
@Data
@EqualsAndHashCode(callSuper = true)
public class InternshipTaskStatusChangedMessage
        extends AbstractRedisStreamMessage {

    private String eventId;
    private Long taskId;
    private Integer oldStatus;
    private Integer newStatus;
    private Long operatorUserId;
    private LocalDateTime occurredAt;
}
```

默认 Stream Key 是类名。若以后重命名类但要求兼容旧 stream，需显式覆盖 `getStreamKey()`。

租户上下文由现有 `TenantRedisMessageInterceptor` 写入/恢复消息 Header；不要
把用户 access token 塞进消息长期保存。若消费者还需要业务操作者，使用事件中
明确的 `operatorUserId`，并重新执行必要授权规则。

## 3. Producer

```java
@Component
@Slf4j
public class InternshipTaskStatusChangedProducer {

    @Resource
    private RedisMQTemplate redisMQTemplate;

    public void sendAfterCommit(
            Long taskId,
            Integer oldStatus,
            Integer newStatus,
            Long operatorUserId) {
        InternshipTaskStatusChangedMessage message = new InternshipTaskStatusChangedMessage();
        message.setEventId(IdUtil.fastSimpleUUID());
        message.setTaskId(taskId);
        message.setOldStatus(oldStatus);
        message.setNewStatus(newStatus);
        message.setOperatorUserId(operatorUserId);
        message.setOccurredAt(LocalDateTime.now());

        Runnable sendAction = () -> {
            try {
                redisMQTemplate.send(message);
            } catch (Exception ex) {
                log.error("[sendAfterCommit][eventId({}) taskId({}) 发送失败]",
                        message.getEventId(), taskId, ex);
                // 当前阶段只留下明确故障证据。
                // 第 14 步改为 Outbox，避免提交后发送失败导致事件永久丢失。
            }
        };

        if (TransactionSynchronizationManager.isActualTransactionActive()) {
            TransactionSynchronizationManager.registerSynchronization(
                    new TransactionSynchronization() {
                        @Override
                        public void afterCommit() {
                            sendAction.run();
                        }
                    });
        } else {
            sendAction.run();
        }
    }
}
```

它避免“数据库最终回滚但消息先发出”，但不能解决“数据库已提交、Redis 发送失败”。
`afterCommit` 回调仍在提交请求的原线程中同步执行 Redis `send`；异步的是消费
端，不应把 Producer 也描述成已经脱离主线程。

## 4. Service 调用点

普通状态更新方法获得 `operatorUserId` 后，只负责完成任务：

```java
@Transactional(rollbackFor = Exception.class)
public void updateInternshipTaskStatus(
        Long id,
        Integer targetStatus,
        Long operatorUserId) {
    InternshipTaskDO task = internshipTaskMapper.selectById(id);
    if (task == null) {
        throw exception(INTERNSHIP_TASK_NOT_EXISTS);
    }
    Integer oldStatus = task.getStatus();

    // 同状态是业务 no-op，不写库，也不产生“伪变化”事件。
    if (Objects.equals(oldStatus, targetStatus)) {
        return;
    }

    Integer inProgress = InternshipTaskStatusEnum.IN_PROGRESS.getStatus();
    Integer done = InternshipTaskStatusEnum.DONE.getStatus();
    boolean allowed = Objects.equals(oldStatus, inProgress)
            && Objects.equals(targetStatus, done);
    if (!allowed) {
        throw exception(
                INTERNSHIP_TASK_STATUS_TRANSITION_INVALID,
                oldStatus, targetStatus);
    }

    // 先按当前状态做条件更新，只有一个并发请求能成为赢家。
    int updateCount = internshipTaskMapper.updateStatusIfCurrent(
            id, oldStatus, targetStatus);
    if (updateCount == 0) {
        throw exception(INTERNSHIP_TASK_STATUS_CHANGED);
    }

    statusChangedProducer.sendAfterCommit(
            id, oldStatus, targetStatus, operatorUserId);
}
```

Controller 传当前登录用户：

```java
internshipTaskService.updateInternshipTaskStatus(
        reqVO.getId(), reqVO.getStatus(), getLoginUserId());
```

Step 07 的认领事务必须在任务原子更新和 claim 记录都成功后注册同一事件：

```java
Integer todo = InternshipTaskStatusEnum.TODO.getStatus();
Integer inProgress = InternshipTaskStatusEnum.IN_PROGRESS.getStatus();

// 前面已经完成：任务条件更新 + claim 记录插入
statusChangedProducer.sendAfterCommit(
        taskId, todo, inProgress, userId);
```

这样两条合法业务道路各自只有一个入口：

```text
claim：
TODO → IN_PROGRESS + assignee + claim + afterCommit 事件

update-status：
IN_PROGRESS → DONE + afterCommit 事件
```

不要让 Controller 自己判断是否发事件，也不要重新开放一个只修改 status 的
`TODO → IN_PROGRESS` 入口。

Mapper 的核心裁决：

```java
default int updateStatusIfCurrent(
        Long id, Integer expectedStatus, Integer targetStatus) {
    return update(new InternshipTaskDO(),
            new LambdaUpdateWrapper<InternshipTaskDO>()
                    .eq(InternshipTaskDO::getId, id)
                    .eq(InternshipTaskDO::getStatus, expectedStatus)
                    .set(InternshipTaskDO::getStatus, targetStatus));
}
```

如果仍是“先查再普通 `updateById`”，两个并发请求可能都发出不同 `eventId`，
消费幂等无法把它们识别成重复。只有 `updateCount == 1` 的赢家才能发事件；
同状态 no-op 不发事件。

并发冲突使用一个独立错误码，不能与“不合法状态流转”混为一类：

```java
ErrorCode INTERNSHIP_TASK_STATUS_CHANGED =
        new ErrorCode(1_002_029_007, "实习任务状态已变化，请刷新后重试");
```

## 5. 第一版审计副作用 SQL

```sql
CREATE TABLE system_internship_task_event_audit (
    id bigint NOT NULL AUTO_INCREMENT,
    event_id varchar(64) NOT NULL COMMENT '事件编号',
    consumer_name varchar(128) NOT NULL COMMENT '消费者名称',
    task_id bigint NOT NULL COMMENT '任务编号',
    old_status tinyint NOT NULL COMMENT '原状态',
    new_status tinyint NOT NULL COMMENT '新状态',
    operator_user_id bigint NOT NULL COMMENT '操作用户',
    occurred_at datetime NOT NULL COMMENT '事件发生时间',
    consume_time datetime NOT NULL COMMENT '消费时间',
    creator varchar(64) DEFAULT '',
    create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updater varchar(64) DEFAULT '',
    update_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    deleted bit(1) NOT NULL DEFAULT b'0',
    tenant_id bigint NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_event_consumer (event_id, consumer_name)
) COMMENT='实习任务状态事件审计';
```

第一版只做一个可证明的小副作用：写审计行。这一行同时承担审计结果与消费
幂等底线，避免先引入一个尚不存在的第二套 Audit 类型。

DO 与 Mapper 的最小形状：

```java
@TableName("system_internship_task_event_audit")
@Data
@EqualsAndHashCode(callSuper = true)
public class InternshipTaskEventAuditDO extends TenantBaseDO {
    private Long id;
    private String eventId;
    private String consumerName;
    private Long taskId;
    private Integer oldStatus;
    private Integer newStatus;
    private Long operatorUserId;
    private LocalDateTime occurredAt;
    private LocalDateTime consumeTime;
}

@Mapper
public interface InternshipTaskEventAuditMapper
        extends BaseMapperX<InternshipTaskEventAuditDO> {
}
```

## 6. 事务消费者业务

```java
@Service
public class InternshipTaskEventConsumeServiceImpl
        implements InternshipTaskEventConsumeService {

    private static final String CONSUMER_NAME =
            "internship-task-audit-consumer";

    @Resource
    private InternshipTaskEventAuditMapper auditMapper;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void recordAudit(InternshipTaskStatusChangedMessage message) {
        InternshipTaskEventAuditDO audit =
                BeanUtils.toBean(message, InternshipTaskEventAuditDO.class);
        audit.setConsumerName(CONSUMER_NAME);
        audit.setConsumeTime(LocalDateTime.now());
        auditMapper.insert(audit);
    }

    @Override
    public boolean hasRecorded(String eventId) {
        return auditMapper.selectCount(
                new LambdaQueryWrapperX<InternshipTaskEventAuditDO>()
                        .eq(InternshipTaskEventAuditDO::getEventId, eventId)
                        .eq(InternshipTaskEventAuditDO::getConsumerName,
                                CONSUMER_NAME)) > 0;
    }
}
```

如果审计插入失败，本次事务回滚，下次重投可以重新执行。

## 7. Consumer

```java
@Component
@Slf4j
public class InternshipTaskStatusChangedConsumer
        extends AbstractRedisStreamMessageListener<
                InternshipTaskStatusChangedMessage> {

    @Resource
    private InternshipTaskEventConsumeService consumeService;

    @Override
    public void onMessage(InternshipTaskStatusChangedMessage message) {
        try {
            consumeService.recordAudit(message);
        } catch (DuplicateKeyException ex) {
            if (consumeService.hasRecorded(message.getEventId())) {
                log.info("[onMessage][eventId({}) 已消费，直接确认]",
                        message.getEventId());
                return;
            }
            throw ex;
        }
    }
}
```

核心版只注册上面一个审计 Listener。当前抽象类默认把 group 设为
`spring.application.name`；若在同一 `system-server` 里再复制一个通知
Listener，两者会在同组竞争，不能保证都收到。加入第二种业务消费者前，必须先
扩展并测试显式 group（或拆分 stream/应用），测试证据是“一条事件令审计、通知
各执行恰好一次”。

关键点：

```text
第一次成功：
审计行提交

ACK 前宕机后重复：
唯一索引抛 DuplicateKeyException
→ Consumer 再查 exact eventId + consumerName 确认确实已完成
→ 正常返回
→ 框架 ACK

真正业务异常：
包括其他唯一键异常，都不能统一吞掉
→ 异常继续抛出
→ 框架不 ACK，消息进入 pending
```

## 8. 当前框架的重投事实

基线代码中：

- `AbstractRedisStreamMessageListener` 只有 `onMessage` 正常返回才 ACK；
- 异常会留下 pending；
- `RedisPendingMessageResendJob` 每分钟扫描；
- 在原消息体仍存在时，超过约 5 分钟未完成的 pending 会被重新写入 stream，
  并 ACK 原记录；
- 当前通用框架没有完整的最大重试次数与死信业务表。

当前 `RedisStreamMessageCleanupJob` 会把 Stream 裁剪到最近 10000 条。如果高
积压时 pending 对应消息体先被 trim，重投 Job 可能查不到原内容并留下悬挂
pending。核心实验只证明正常规模下的一次重投；高积压与清理交互必须专项验证。

因此第 10 步第一版：

```text
先验证 pending 与重投
→ 为学习业务增加明确错误日志/告警
→ 不宣称已经具备生产级死信治理
```

如果要加入最大重试：

```text
独立 REQUIRES_NEW 失败记录
→ 按 eventId + consumerName 递增
→ 达到上限后标 DEAD 并让 Consumer 正常返回以 ACK
→ 提供人工重放命令
```

这属于本阶段加分项，不应与最小 producer/consumer 同时第一次实现。

## 9. 测试

### Producer

```text
事务回滚
→ send 不应发生

claim 事务提交
→ TODO→IN_PROGRESS send 发生一次

完成任务事务提交
→ IN_PROGRESS→DONE send 发生一次

普通 update-status 尝试 TODO→IN_PROGRESS
→ 被状态机拒绝，send 不发生
```

### Consumer 正常

```text
一条消息
→ 审计一条
```

### 重复

```text
同 eventId 调用 10 次
→ 审计副作用仍一条
→ 只有 exact eventId + consumerName 的 DuplicateKey 被识别为已消费
```

### 失败

```text
让 auditMapper 抛异常
→ Listener 不 ACK
→ Redis pending 可观察
```

### 恢复

```text
修复失败条件
→ 等待重投或人工再次发送
→ 最终成功并 ACK
```

## 10. Redis 观察命令

具体 Stream Key 以运行时类名为准：

```text
XLEN <stream>
XINFO GROUPS <stream>
XPENDING <stream> <group>
XRANGE <stream> - +
```

先在学习环境使用；生产环境读取大量 Stream 内容要限制范围。

H2 `create_tables.sql` 使用测试方言：

```sql
CREATE TABLE IF NOT EXISTS "system_internship_task_event_audit" (
    "id" bigint NOT NULL GENERATED BY DEFAULT AS IDENTITY,
    "event_id" varchar(64) NOT NULL,
    "consumer_name" varchar(128) NOT NULL,
    "task_id" bigint NOT NULL,
    "old_status" tinyint NOT NULL,
    "new_status" tinyint NOT NULL,
    "operator_user_id" bigint NOT NULL,
    "occurred_at" timestamp NOT NULL,
    "consume_time" timestamp NOT NULL,
    "creator" varchar(64) DEFAULT '',
    "create_time" timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updater" varchar(64) DEFAULT '',
    "update_time" timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted" bit NOT NULL DEFAULT FALSE,
    "tenant_id" bigint NOT NULL DEFAULT '0',
    PRIMARY KEY ("id"),
    CONSTRAINT "uk_internship_event_consumer"
        UNIQUE ("event_id", "consumer_name")
);
```

`clean.sql` 在任务表之前增加：

```sql
DELETE FROM "system_internship_task_event_audit";
```

否则现有数据库测试只能证明“测试库结构没同步”，不能证明消费逻辑。
