package cn.iocoder.yudao.module.system.service.internship;

import org.springframework.stereotype.Service;

import static cn.iocoder.yudao.framework.common.exception.util.ServiceExceptionUtil.exception;
import static cn.iocoder.yudao.module.system.enums.ErrorCodeConstants.INTERNSHIP_TASK_NOT_EXISTS;
import cn.iocoder.yudao.framework.common.util.object.BeanUtils;
import cn.iocoder.yudao.framework.common.pojo.PageResult;
import cn.iocoder.yudao.module.system.controller.admin.internship.vo.InternshipTaskPageReqVO;
import cn.iocoder.yudao.module.system.controller.admin.internship.vo.InternshipTaskSaveReqVO;
import cn.iocoder.yudao.module.system.dal.dataobject.internship.InternshipTaskDO;
import cn.iocoder.yudao.module.system.dal.mysql.internship.InternshipTaskMapper;
import cn.iocoder.yudao.module.system.enums.internship.InternshipTaskStatusEnum;
import jakarta.annotation.Resource;

@Service
public class InternshipTaskServiceImpl implements InternshipTaskService {

    @Resource
    private InternshipTaskMapper internshipTaskMapper;

    @Override
    public Long createInternshipTask(InternshipTaskSaveReqVO reqVO) {
        InternshipTaskDO internshipTaskDO = BeanUtils.toBean(reqVO, InternshipTaskDO.class);
        internshipTaskDO.setId(null);
        internshipTaskDO.setStatus(InternshipTaskStatusEnum.TODO.getStatus());
        internshipTaskMapper.insert(internshipTaskDO);
        return internshipTaskDO.getId();
    }

    @Override
    public void updateInternshipTask(InternshipTaskSaveReqVO reqVO) {
        InternshipTaskDO task = internshipTaskMapper.selectById(reqVO.getId());
        if (task == null) {
            throw exception(INTERNSHIP_TASK_NOT_EXISTS);
        }
        internshipTaskMapper.updateById(BeanUtils.toBean(reqVO, InternshipTaskDO.class));
    }

    @Override
    public void deleteInternshipTask(Long id) {
        InternshipTaskDO task = internshipTaskMapper.selectById(id);
        if (task == null) {
            throw exception(INTERNSHIP_TASK_NOT_EXISTS);
        }
        internshipTaskMapper.deleteById(id);
    }

    @Override
    public PageResult<InternshipTaskDO> getInternshipTaskPage(InternshipTaskPageReqVO reqVO) {
        return internshipTaskMapper.selectPage(reqVO);
    }

    @Override
    public InternshipTaskDO getInternshipTask(Long id) {
        InternshipTaskDO task = internshipTaskMapper.selectById(id);
        if (task == null) {
            throw exception(INTERNSHIP_TASK_NOT_EXISTS);
        }
        return task;
    }
}
