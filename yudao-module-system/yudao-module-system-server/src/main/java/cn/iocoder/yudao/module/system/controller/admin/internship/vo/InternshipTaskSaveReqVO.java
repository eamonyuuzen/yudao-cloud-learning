package cn.iocoder.yudao.module.system.controller.admin.internship.vo;

import java.time.LocalDateTime;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Schema(description = "管理后台 - 实习任务创建/修改 Request VO")
@Data
public class InternshipTaskSaveReqVO {

    @Schema(description = "任务编号", example = "1024")
    private Long id;

    @Schema(description = "任务标题", requiredMode = Schema.RequiredMode.REQUIRED,
            example = "完成用户管理模块")
    @NotBlank(message = "任务标题不能为空")
    @Size(max = 200, message = "任务标题不能超过200个字符")
    private String title;

    @Schema(description = "任务说明", example = "完成用户分页查询与邮箱筛选功能")
    private String description;

    @Schema(description = "截止时间", example = "2026-07-31T18:00:00")
    private LocalDateTime deadline;
}
