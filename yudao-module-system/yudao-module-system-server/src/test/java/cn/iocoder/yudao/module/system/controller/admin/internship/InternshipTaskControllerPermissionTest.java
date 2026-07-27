package cn.iocoder.yudao.module.system.controller.admin.internship;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.test.context.junit.jupiter.SpringJUnitConfig;

import cn.iocoder.yudao.framework.security.core.service.SecurityFrameworkService;
import cn.iocoder.yudao.module.system.controller.admin.internship.vo.InternshipTaskSaveReqVO;
import cn.iocoder.yudao.module.system.service.internship.InternshipTaskService;

@SpringJUnitConfig(InternshipTaskControllerPermissionTest.TestConfig.class)
class InternshipTaskControllerPermissionTest {

    @Autowired
    private InternshipTaskController internshipTaskController;

    @Autowired
    private InternshipTaskService internshipTaskService;

    @Autowired
    private SecurityFrameworkService securityFrameworkService;

    @Configuration(proxyBeanMethods = false)
    @EnableMethodSecurity
    static class TestConfig {

        @Bean
        InternshipTaskController internshipTaskController() {
            return new InternshipTaskController();
        }

        @Bean
        InternshipTaskService internshipTaskService() {
            return mock(InternshipTaskService.class);
        }

        @Bean("ss")
        SecurityFrameworkService securityFrameworkService() {
            return mock(SecurityFrameworkService.class);
        }
    }

    @Test
    void testCreateInternshipTask_withoutPermission() {
        // 1. 准备一个参数合法的请求
        InternshipTaskSaveReqVO reqVO = new InternshipTaskSaveReqVO();
        reqVO.setTitle("学习权限测试");

        // 2. 模拟当前用户没有创建权限
        when(securityFrameworkService.hasPermission("internship:task:create"))
                .thenReturn(false);

        // 3. 调用Controller代理，预期被权限系统拒绝
        assertThrows(AccessDeniedException.class,
                () -> internshipTaskController.createInternshipTask(reqVO));

        // 4. 证明权限检查确实执行过
        verify(securityFrameworkService)
                .hasPermission("internship:task:create");

        // 5. 证明原Controller业务没有走到Service
        verifyNoInteractions(internshipTaskService);
    }
}