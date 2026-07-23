package cn.iocoder.yudao.module.system.dal.dataobject.internship;

import java.time.LocalDateTime;

import com.baomidou.mybatisplus.annotation.TableName;

import cn.iocoder.yudao.framework.mybatis.core.dataobject.BaseDO;
import cn.iocoder.yudao.module.system.enums.internship.InternshipTaskStatusEnum;
import lombok.EqualsAndHashCode;
import lombok.Data;

@TableName("system_internship_task")
@Data
@EqualsAndHashCode(callSuper = true)
public class InternshipTaskDO extends BaseDO {
    private Long id;
    private String title;
    private String description;
    private LocalDateTime deadline;
    /**
     * 状态
     *
     * 枚举 {@link InternshipTaskStatusEnum}
     */
    private Integer status;
}
