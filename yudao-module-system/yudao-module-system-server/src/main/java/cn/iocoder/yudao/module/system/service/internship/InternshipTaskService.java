package cn.iocoder.yudao.module.system.service.internship;

import cn.iocoder.yudao.framework.common.pojo.PageResult;
import cn.iocoder.yudao.module.system.controller.admin.internship.vo.InternshipTaskPageReqVO;
import cn.iocoder.yudao.module.system.controller.admin.internship.vo.InternshipTaskSaveReqVO;
import cn.iocoder.yudao.module.system.dal.dataobject.internship.InternshipTaskDO;

public interface InternshipTaskService {
    Long createInternshipTask(InternshipTaskSaveReqVO reqVO);

    void updateInternshipTask(InternshipTaskSaveReqVO reqVO);

    void deleteInternshipTask(Long id);

    PageResult<InternshipTaskDO> getInternshipTaskPage(InternshipTaskPageReqVO reqVO);

    InternshipTaskDO getInternshipTask(Long id);
}
