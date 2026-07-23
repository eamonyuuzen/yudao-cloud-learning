package cn.iocoder.yudao.module.system.dal.mysql.internship;

import org.apache.ibatis.annotations.Mapper;

import cn.iocoder.yudao.framework.common.pojo.PageResult;
import cn.iocoder.yudao.framework.mybatis.core.mapper.BaseMapperX;
import cn.iocoder.yudao.framework.mybatis.core.query.LambdaQueryWrapperX;
import cn.iocoder.yudao.module.system.controller.admin.internship.vo.InternshipTaskPageReqVO;
import cn.iocoder.yudao.module.system.dal.dataobject.internship.InternshipTaskDO;

@Mapper
public interface InternshipTaskMapper extends BaseMapperX<InternshipTaskDO> {

    default PageResult<InternshipTaskDO> selectPage(InternshipTaskPageReqVO reqVO) {
        return selectPage(reqVO, new LambdaQueryWrapperX<InternshipTaskDO>()
                .likeIfPresent(InternshipTaskDO::getTitle, reqVO.getTitle())
                .eqIfPresent(InternshipTaskDO::getStatus, reqVO.getStatus())
                .orderByDesc(InternshipTaskDO::getId));
    }
}
