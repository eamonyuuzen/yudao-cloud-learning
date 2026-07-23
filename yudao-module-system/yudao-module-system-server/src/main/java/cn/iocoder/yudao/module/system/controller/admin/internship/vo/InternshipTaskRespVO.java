package cn.iocoder.yudao.module.system.controller.admin.internship.vo;

import java.time.LocalDateTime;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Schema(description = "管理后台 - 实习任务信息 Response VO")
@Data
public class InternshipTaskRespVO {
    @Schema(description = "任务编号", example = "1024")
    private Long id;

    @Schema(description = "任务标题", requiredMode = Schema.RequiredMode.REQUIRED,
            example = "完成用户管理模块")
    private String title;

    @Schema(description = "任务说明", example = "完成用户分页查询与邮箱筛选功能")
    private String description;

    @Schema(description = "任务状态，参见 InternshipTaskStatusEnum 枚举类", example = "1")
    private Integer status;

    @Schema(description = "创建时间", requiredMode = Schema.RequiredMode.REQUIRED, example = "时间戳格式")
    private LocalDateTime createTime;

    @Schema(description = "截止时间", example = "2026-07-31T18:00:00")
    private LocalDateTime deadline;
}
