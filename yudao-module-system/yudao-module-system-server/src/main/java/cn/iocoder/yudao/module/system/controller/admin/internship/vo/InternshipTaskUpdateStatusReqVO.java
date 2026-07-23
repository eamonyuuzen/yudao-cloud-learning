package cn.iocoder.yudao.module.system.controller.admin.internship.vo;

import cn.iocoder.yudao.framework.common.validation.InEnum;
import cn.iocoder.yudao.module.system.enums.internship.InternshipTaskStatusEnum;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Schema(description = "管理后台 - 实习任务更新状态 Request VO")
@Data
public class InternshipTaskUpdateStatusReqVO {

    @Schema(description = "任务编号、必填", example = "1024")
    @NotNull(message = "任务编号不能为空")
    private Long id;

    @Schema(description = "目标状态、必填", example = "1")
    @NotNull(message = "目标状态不能为空")
    @InEnum(InternshipTaskStatusEnum.class)
    private Integer status;

}
