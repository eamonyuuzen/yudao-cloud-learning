package cn.iocoder.yudao.module.ai.tool.method;

import org.junit.jupiter.api.Test;
import org.springframework.ai.support.ToolCallbacks;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

import java.util.Arrays;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * {@link PersonServiceImpl} 工具注册的最小学习测试。
 *
 * <p>它不连接真实模型，只验证：</p>
 * <ol>
 *     <li>Spring AI 能从 {@code @Tool} 方法生成 {@link ToolCallback}；</li>
 *     <li>工具名称和输入 Schema 可被运行时读取；</li>
 *     <li>运行时可按工具名找到回调，并用 JSON 参数调用原 Java 方法。</li>
 * </ol>
 */
class PersonToolRegistrationTest {

    @Test
    void shouldRegisterAndInvokeGetPersonToolWithoutModel() {
        try (AnnotationConfigApplicationContext context =
                     new AnnotationConfigApplicationContext(PersonServiceImpl.class)) {
            PersonService personService = context.getBean(PersonService.class);
            ToolCallback[] callbacks = ToolCallbacks.from(personService);

            ToolCallback callback = Arrays.stream(callbacks)
                    .filter(item -> "ps_get_person_by_id"
                            .equals(item.getToolDefinition().name()))
                    .findFirst()
                    .orElseThrow();

            assertEquals("ps_get_person_by_id",
                    callback.getToolDefinition().name());
            assertTrue(callback.getToolDefinition().inputSchema()
                    .contains("\"id\""));

            String toolResult = callback.call("{\"id\":1}");
            assertTrue(toolResult.contains("Fons"));
        }
    }

}
