# Step 06B Reference：Spring AI Java Tool 注册闭环

```text
status: SOURCE-VERIFIED
verified_at: 2026-07-30
spring_ai: 1.1.5
```

这张卡只回答一个问题：

> `@Tool` 写在 Java 方法上后，谁把它变成可按名字调用的运行时能力？

## 1. 静态角色

```text
@Tool 方法
→ 保存名称、说明和参数元数据

ToolCallbacks.from(personService)
→ 启动期扫描方法并生成 ToolCallback[]

ToolCallback
→ 保存工具定义，并能接收 JSON 调回原 Java 方法

模型工具选项
→ 把允许选择的 ToolCallback 告诉模型

Runner / ToolCallingManager
→ 接住模型返回的 tool name + arguments，按名字匹配并执行
```

`@Tool` 不是执行者。它更像贴在方法上的“可扫描说明牌”；扫描器、注册表和
运行时调度器共同让说明牌产生行为。

## 2. 动态事件

```text
Spring 启动
→ ToolCallbacks.from 扫描 personService
→ 生成 name=ps_get_person_by_id 的 ToolCallback
→ ToolCallback 被加入本轮模型可选工具

模型返回：
name=ps_get_person_by_id
arguments={"id":1}

→ 运行器按 name 找到 ToolCallback
→ ToolCallback 把 JSON 转成 Java 参数
→ 调用 PersonServiceImpl.getPersonById(1)
→ 返回值序列化为 tool result
→ tool result 进入下一轮模型消息
```

## 3. 第一入口与可选证据

第一入口：

- [PersonServiceImpl.java](../../../yudao-module-ai/yudao-module-ai-server/src/main/java/cn/iocoder/yudao/module/ai/tool/method/PersonServiceImpl.java)

只在需要验证连接机制时再打开：

- [AiAutoConfiguration.java](../../../yudao-module-ai/yudao-module-ai-server/src/main/java/cn/iocoder/yudao/module/ai/framework/ai/config/AiAutoConfiguration.java)
- [AiChatMessageServiceImpl.java](../../../yudao-module-ai/yudao-module-ai-server/src/main/java/cn/iocoder/yudao/module/ai/service/chat/AiChatMessageServiceImpl.java)
- [AiUtils.java](../../../yudao-module-ai/yudao-module-ai-server/src/main/java/cn/iocoder/yudao/module/ai/util/AiUtils.java)
- [PersonToolRegistrationTest.java](../../../yudao-module-ai/yudao-module-ai-server/src/test/java/cn/iocoder/yudao/module/ai/tool/method/PersonToolRegistrationTest.java)

源码已核对的连接点：

```text
AiAutoConfiguration
→ ToolCallbacks.from(personService)

AiChatMessageServiceImpl
→ toolCallbackResolver.resolve(toolName)

AiUtils
→ 把 LoginUser、tenantId 放进 ToolContext
```

## 4. 不调用模型也能证明什么

最小测试直接执行：

```text
创建 PersonService Bean
→ ToolCallbacks.from
→ 在 ToolCallback[] 中按名称查找
→ 检查生成的 JSON Schema 含 id
→ callback.call("{\"id\":1}")
→ 断言结果含 Fons
```

这能证明：

- 注解方法能被扫描；
- 名称能匹配；
- JSON 参数能进入原方法；
- Java 返回值能变成工具结果。

它不能证明：

- 某个真实模型一定会选对工具；
- Provider 完整兼容 Tool Calling；
- 当前用户一定有业务权限。

验证命令：

```powershell
mvn -pl yudao-module-ai/yudao-module-ai-server -am `
  "-Dtest=PersonToolRegistrationTest" `
  "-Dsurefire.failIfNoSpecifiedTests=false" test
```

2026-07-30 的窄测试证据：

```text
Tests run: 1, Failures: 0, Errors: 0, Skipped: 0
```

## 5. 压缩结论

```text
注解提供元数据入口
→ 启动扫描生成运行时对象
→ 注册表保存 name 到 callback 的映射
→ 运行器按模型返回的 name 找到 callback
→ callback 借助反射/参数转换调回原方法
```

这与此前学过的 `@PreAuthorize` 共同抽象为：

```text
代码上的标签
→ 启动期注册某种处理器
→ Spring 代理或运行器在事件发生时读取元数据
→ 真正的处理器执行额外逻辑
```

不同点是：`@PreAuthorize` 拦住现有方法调用；`@Tool` 把方法加入模型可选能力。
