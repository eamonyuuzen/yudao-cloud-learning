package cn.iocoder.yudao.module.system.controller.admin.internship.vo;

import cn.iocoder.yudao.framework.common.pojo.PageParam;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Schema(description = "管理后台 - 实习任务分页 Request VO")
@Data
@EqualsAndHashCode(callSuper = true)
public class InternshipTaskPageReqVO extends PageParam {
    @Schema(description = "任务标题，模糊匹配", example = "用户管理")
    private String title;

    @Schema(description = "展示状态，参见 InternshipTaskStatusEnum 枚举类", example = "1")
    private Integer status;
}
