package cn.iocoder.yudao.module.system.enums.internship;

import java.util.Arrays;

import cn.iocoder.yudao.framework.common.core.ArrayValuable;
import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum InternshipTaskStatusEnum implements ArrayValuable<Integer> {

    TODO(0),
    IN_PROGRESS(1),
    DONE(2);

    private final Integer status;

    public static final Integer[] ARRAYS = Arrays.stream(values())
            .map(InternshipTaskStatusEnum::getStatus)
            .toArray(Integer[]::new);

    @Override
    public Integer[] array() {
        return ARRAYS;
    }
}
