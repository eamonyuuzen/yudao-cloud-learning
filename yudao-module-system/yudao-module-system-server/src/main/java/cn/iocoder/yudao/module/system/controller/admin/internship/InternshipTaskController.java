package cn.iocoder.yudao.module.system.controller.admin.internship;

import cn.iocoder.yudao.framework.common.pojo.CommonResult;
import cn.iocoder.yudao.framework.common.pojo.PageResult;
import cn.iocoder.yudao.framework.common.util.object.BeanUtils;
import cn.iocoder.yudao.module.system.controller.admin.internship.vo.InternshipTaskPageReqVO;
import cn.iocoder.yudao.module.system.controller.admin.internship.vo.InternshipTaskRespVO;
import cn.iocoder.yudao.module.system.controller.admin.internship.vo.InternshipTaskSaveReqVO;
import cn.iocoder.yudao.module.system.controller.admin.internship.vo.InternshipTaskUpdateStatusReqVO;
import cn.iocoder.yudao.module.system.service.internship.InternshipTaskService;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.annotation.Resource;
import jakarta.validation.Valid;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "管理后台 - 实习任务")
@RestController
@RequestMapping("/system/internship-task")
@Validated
public class InternshipTaskController {
    @Resource
    private InternshipTaskService internshipTaskService;

    @PostMapping("/create")
    @PreAuthorize("@ss.hasPermission('internship:task:create')")
    public CommonResult<Long> createInternshipTask(@Valid @RequestBody InternshipTaskSaveReqVO reqVO) {
        return CommonResult.success(internshipTaskService.createInternshipTask(reqVO));
    }

    @PutMapping("/update")
    @PreAuthorize("@ss.hasPermission('internship:task:update')")
    public CommonResult<Boolean> updateInternshipTask(@Valid @RequestBody InternshipTaskSaveReqVO reqVO) {
        internshipTaskService.updateInternshipTask(reqVO);
        return CommonResult.success(true);
    }

    @PutMapping("/update-status")
    @PreAuthorize("@ss.hasPermission('internship:task:update-status')")
    public CommonResult<Boolean> updateInternshipTaskStatus(
            @Valid @RequestBody InternshipTaskUpdateStatusReqVO reqVO) {
        internshipTaskService.updateInternshipTaskStatus(reqVO.getId(), reqVO.getStatus());
        return CommonResult.success(true);
    }

    @DeleteMapping("/delete")
    @PreAuthorize("@ss.hasPermission('internship:task:delete')")
    public CommonResult<Boolean> deleteInternshipTask(@RequestParam("id") Long id) {
        internshipTaskService.deleteInternshipTask(id);
        return CommonResult.success(true);
    }

    @GetMapping("/page")
    @PreAuthorize("@ss.hasPermission('internship:task:query')")
    public CommonResult<PageResult<InternshipTaskRespVO>> getInternshipTaskPage(
            @Validated InternshipTaskPageReqVO reqVO) {
        return CommonResult.success(
                BeanUtils.toBean(internshipTaskService.getInternshipTaskPage(reqVO),
                        InternshipTaskRespVO.class));
    }

    @GetMapping("/get")
    @PreAuthorize("@ss.hasPermission('internship:task:query')")
    public CommonResult<InternshipTaskRespVO> getInternshipTask(@RequestParam("id") Long id) {
        return CommonResult.success(BeanUtils.toBean(internshipTaskService.getInternshipTask(id),
                InternshipTaskRespVO.class));
    }
}
