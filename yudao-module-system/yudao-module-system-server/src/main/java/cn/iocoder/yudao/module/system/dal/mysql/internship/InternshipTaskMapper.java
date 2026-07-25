package cn.iocoder.yudao.module.system.dal.mysql.internship;

import cn.iocoder.yudao.framework.common.pojo.PageResult;
import cn.iocoder.yudao.framework.mybatis.core.mapper.BaseMapperX;
import cn.iocoder.yudao.framework.mybatis.core.query.LambdaQueryWrapperX;
import cn.iocoder.yudao.module.system.controller.admin.internship.vo.InternshipTaskPageReqVO;
import cn.iocoder.yudao.module.system.dal.dataobject.internship.InternshipTaskDO;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import org.apache.ibatis.annotations.Mapper;

import java.time.LocalDateTime;

@Mapper
public interface InternshipTaskMapper extends BaseMapperX<InternshipTaskDO> {

    default int updateEditableFields(Long id, String title, String description, LocalDateTime deadline) {
        return update(new InternshipTaskDO(), new LambdaUpdateWrapper<InternshipTaskDO>()
                .eq(InternshipTaskDO::getId, id)
                .set(InternshipTaskDO::getTitle, title)
                .set(InternshipTaskDO::getDescription, description)
                .set(InternshipTaskDO::getDeadline, deadline));
    }

    default PageResult<InternshipTaskDO> selectPage(InternshipTaskPageReqVO reqVO) {
        return selectPage(reqVO, new LambdaQueryWrapperX<InternshipTaskDO>()
                .likeIfPresent(InternshipTaskDO::getTitle, reqVO.getTitle())
                .eqIfPresent(InternshipTaskDO::getStatus, reqVO.getStatus())
                .orderByDesc(InternshipTaskDO::getId));
    }
}
