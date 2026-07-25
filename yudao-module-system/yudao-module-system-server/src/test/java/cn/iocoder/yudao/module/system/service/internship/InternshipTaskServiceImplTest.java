package cn.iocoder.yudao.module.system.service.internship;

import cn.iocoder.yudao.framework.test.core.ut.BaseDbUnitTest;
import cn.iocoder.yudao.module.system.controller.admin.internship.vo.InternshipTaskSaveReqVO;
import cn.iocoder.yudao.module.system.dal.dataobject.internship.InternshipTaskDO;
import cn.iocoder.yudao.module.system.dal.mysql.internship.InternshipTaskMapper;
import cn.iocoder.yudao.module.system.enums.internship.InternshipTaskStatusEnum;
import jakarta.annotation.Resource;
import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;

import java.time.LocalDateTime;

import static cn.iocoder.yudao.framework.test.core.util.AssertUtils.assertServiceException;
import static cn.iocoder.yudao.framework.test.core.util.RandomUtils.randomLongId;
import static cn.iocoder.yudao.framework.test.core.util.RandomUtils.randomPojo;
import static cn.iocoder.yudao.module.system.enums.ErrorCodeConstants.INTERNSHIP_TASK_NOT_EXISTS;
import static cn.iocoder.yudao.module.system.enums.ErrorCodeConstants.INTERNSHIP_TASK_STATUS_TRANSITION_INVALID;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;

@Import(InternshipTaskServiceImpl.class)
class InternshipTaskServiceImplTest extends BaseDbUnitTest {

    @Resource
    private InternshipTaskServiceImpl internshipTaskService;

    @Resource
    private InternshipTaskMapper internshipTaskMapper;

    @Test
    void testCreateInternshipTask_defaultTodo() {
        InternshipTaskSaveReqVO reqVO = randomPojo(InternshipTaskSaveReqVO.class, o -> {
            o.setId(null);
            o.setDeadline(null);
        });

        Long id = internshipTaskService.createInternshipTask(reqVO);

        InternshipTaskDO task = internshipTaskMapper.selectById(id);
        assertNotNull(task);
        assertEquals(InternshipTaskStatusEnum.TODO.getStatus(), task.getStatus());
        assertNull(task.getDeadline());
    }

    @Test
    void testUpdateInternshipTask_clearNullableFields() {
        InternshipTaskDO task = insertTask(InternshipTaskStatusEnum.TODO.getStatus());
        InternshipTaskSaveReqVO reqVO = randomPojo(InternshipTaskSaveReqVO.class, o -> {
            o.setId(task.getId());
            o.setDescription(null);
            o.setDeadline(null);
        });

        internshipTaskService.updateInternshipTask(reqVO);

        InternshipTaskDO updatedTask = internshipTaskMapper.selectById(task.getId());
        assertEquals(reqVO.getTitle(), updatedTask.getTitle());
        assertNull(updatedTask.getDescription());
        assertNull(updatedTask.getDeadline());
        assertEquals(InternshipTaskStatusEnum.TODO.getStatus(), updatedTask.getStatus());
    }

    @Test
    void testUpdateInternshipTaskStatus_todoToInProgress() {
        InternshipTaskDO task = insertTask(InternshipTaskStatusEnum.TODO.getStatus());

        internshipTaskService.updateInternshipTaskStatus(
                task.getId(), InternshipTaskStatusEnum.IN_PROGRESS.getStatus());

        assertEquals(InternshipTaskStatusEnum.IN_PROGRESS.getStatus(),
                internshipTaskMapper.selectById(task.getId()).getStatus());
    }

    @Test
    void testUpdateInternshipTaskStatus_inProgressToDone() {
        InternshipTaskDO task = insertTask(InternshipTaskStatusEnum.IN_PROGRESS.getStatus());

        internshipTaskService.updateInternshipTaskStatus(
                task.getId(), InternshipTaskStatusEnum.DONE.getStatus());

        assertEquals(InternshipTaskStatusEnum.DONE.getStatus(),
                internshipTaskMapper.selectById(task.getId()).getStatus());
    }

    @Test
    void testUpdateInternshipTaskStatus_sameStatus() {
        InternshipTaskDO task = insertTask(InternshipTaskStatusEnum.TODO.getStatus());
        LocalDateTime originalUpdateTime = task.getUpdateTime();

        internshipTaskService.updateInternshipTaskStatus(
                task.getId(), InternshipTaskStatusEnum.TODO.getStatus());

        InternshipTaskDO unchangedTask = internshipTaskMapper.selectById(task.getId());
        assertEquals(InternshipTaskStatusEnum.TODO.getStatus(), unchangedTask.getStatus());
        assertEquals(originalUpdateTime, unchangedTask.getUpdateTime());
    }

    @Test
    void testUpdateInternshipTaskStatus_invalidTransition() {
        InternshipTaskDO task = insertTask(InternshipTaskStatusEnum.TODO.getStatus());

        assertServiceException(
                () -> internshipTaskService.updateInternshipTaskStatus(
                        task.getId(), InternshipTaskStatusEnum.DONE.getStatus()),
                INTERNSHIP_TASK_STATUS_TRANSITION_INVALID,
                InternshipTaskStatusEnum.TODO.getStatus(),
                InternshipTaskStatusEnum.DONE.getStatus());
        assertEquals(InternshipTaskStatusEnum.TODO.getStatus(),
                internshipTaskMapper.selectById(task.getId()).getStatus());
    }

    @Test
    void testUpdateInternshipTaskStatus_notExists() {
        assertServiceException(
                () -> internshipTaskService.updateInternshipTaskStatus(
                        randomLongId(), InternshipTaskStatusEnum.IN_PROGRESS.getStatus()),
                INTERNSHIP_TASK_NOT_EXISTS);
    }

    private InternshipTaskDO insertTask(Integer status) {
        InternshipTaskDO task = randomPojo(InternshipTaskDO.class, o -> {
            o.setId(null);
            o.setStatus(status);
            o.setDeleted(false);
            o.setDeadline(LocalDateTime.now().plusDays(1));
        });
        internshipTaskMapper.insert(task);
        return task;
    }

}
