package cn.iocoder.yudao.module.system.controller.admin.internship;

import cn.iocoder.yudao.framework.common.biz.infra.logger.ApiErrorLogCommonApi;
import cn.iocoder.yudao.framework.test.core.ut.BaseMockitoUnitTest;
import cn.iocoder.yudao.framework.web.core.handler.GlobalExceptionHandler;
import cn.iocoder.yudao.module.system.service.internship.InternshipTaskService;

import org.springframework.http.MediaType;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import static org.mockito.Mockito.verifyNoInteractions;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class InternshipTaskControllerTest extends BaseMockitoUnitTest {

    @InjectMocks
    private InternshipTaskController internshipTaskController;

    @Mock
    private InternshipTaskService internshipTaskService;
    @Mock
    private ApiErrorLogCommonApi apiErrorLogCommonApi;

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        GlobalExceptionHandler globalExceptionHandler = new GlobalExceptionHandler("yudao-module-system",
                apiErrorLogCommonApi);
        mockMvc = MockMvcBuilders.standaloneSetup(internshipTaskController)
                .setControllerAdvice(globalExceptionHandler)
                .build();
    }

    @Test
    void testCreateInternshipTask_titleMissing() throws Exception {
        // TODO 1：准备一个缺少 title 的 JSON 请求体
        String requestBody = """
                {
                "description": "学习测试",
                "deadline": "2026-07-31T18:00:00"
                }
                    """;
        // TODO 2：使用 mockMvc 向 /system/internship-task/create 发送 POST 请求
        mockMvc.perform(post("/system/internship-task/create")
                .contentType(MediaType.APPLICATION_JSON)
                .content(requestBody))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.msg")
                        .value("请求参数不正确:任务标题不能为空"));
        verifyNoInteractions(internshipTaskService);
        // TODO 3：断言 HTTP status

        // TODO 4：断言 JSON 中的 code 和 msg
        // TODO 5：验证 internshipTaskService 一次也没有被调用

    }

}
