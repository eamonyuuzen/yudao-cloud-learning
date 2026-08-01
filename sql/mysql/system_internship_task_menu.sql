-- 实习任务菜单与按钮权限。
-- 只定义权限资源，不自动给普通角色授权，避免环境初始化时意外扩权。

SET @system_menu_parent_id = (
    SELECT `id`
    FROM `system_menu`
    WHERE `deleted` = b'0'
      AND `type` = 1
      AND `path` = '/system'
    LIMIT 1
);

INSERT INTO `system_menu`
    (`name`, `permission`, `type`, `sort`, `parent_id`, `path`, `icon`, `component`,
     `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`,
     `create_time`, `updater`, `update_time`, `deleted`)
SELECT '实习任务', 'internship:task:query', 2, 10, @system_menu_parent_id,
       'internship-task', 'ep:list', 'internship/task/index', 'InternshipTask',
       0, b'1', b'1', b'1', 'admin', NOW(), 'admin', NOW(), b'0'
WHERE @system_menu_parent_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM `system_menu`
      WHERE `deleted` = b'0'
        AND `permission` = 'internship:task:query'
  );

SET @internship_task_menu_id = (
    SELECT `id`
    FROM `system_menu`
    WHERE `deleted` = b'0'
      AND `permission` = 'internship:task:query'
    LIMIT 1
);

INSERT INTO `system_menu`
    (`name`, `permission`, `type`, `sort`, `parent_id`, `path`, `icon`, `component`,
     `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`,
     `create_time`, `updater`, `update_time`, `deleted`)
SELECT '任务新增', 'internship:task:create', 3, 1, @internship_task_menu_id,
       '', '', '', NULL, 0, b'1', b'1', b'1', 'admin', NOW(), 'admin', NOW(), b'0'
WHERE @internship_task_menu_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM `system_menu`
      WHERE `deleted` = b'0'
        AND `permission` = 'internship:task:create'
  );

INSERT INTO `system_menu`
    (`name`, `permission`, `type`, `sort`, `parent_id`, `path`, `icon`, `component`,
     `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`,
     `create_time`, `updater`, `update_time`, `deleted`)
SELECT '任务修改', 'internship:task:update', 3, 2, @internship_task_menu_id,
       '', '', '', NULL, 0, b'1', b'1', b'1', 'admin', NOW(), 'admin', NOW(), b'0'
WHERE @internship_task_menu_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM `system_menu`
      WHERE `deleted` = b'0'
        AND `permission` = 'internship:task:update'
  );

INSERT INTO `system_menu`
    (`name`, `permission`, `type`, `sort`, `parent_id`, `path`, `icon`, `component`,
     `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`,
     `create_time`, `updater`, `update_time`, `deleted`)
SELECT '任务删除', 'internship:task:delete', 3, 3, @internship_task_menu_id,
       '', '', '', NULL, 0, b'1', b'1', b'1', 'admin', NOW(), 'admin', NOW(), b'0'
WHERE @internship_task_menu_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM `system_menu`
      WHERE `deleted` = b'0'
        AND `permission` = 'internship:task:delete'
  );

INSERT INTO `system_menu`
    (`name`, `permission`, `type`, `sort`, `parent_id`, `path`, `icon`, `component`,
     `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`,
     `create_time`, `updater`, `update_time`, `deleted`)
SELECT '任务状态变更', 'internship:task:update-status', 3, 4, @internship_task_menu_id,
       '', '', '', NULL, 0, b'1', b'1', b'1', 'admin', NOW(), 'admin', NOW(), b'0'
WHERE @internship_task_menu_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM `system_menu`
      WHERE `deleted` = b'0'
        AND `permission` = 'internship:task:update-status'
  );

INSERT INTO `system_menu`
    (`name`, `permission`, `type`, `sort`, `parent_id`, `path`, `icon`, `component`,
     `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`,
     `create_time`, `updater`, `update_time`, `deleted`)
SELECT '任务认领', 'internship:task:claim', 3, 5, @internship_task_menu_id,
       '', '', '', NULL, 0, b'1', b'1', b'1', 'admin', NOW(), 'admin', NOW(), b'0'
WHERE @internship_task_menu_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM `system_menu`
      WHERE `deleted` = b'0'
        AND `permission` = 'internship:task:claim'
  );

INSERT INTO `system_menu`
    (`name`, `permission`, `type`, `sort`, `parent_id`, `path`, `icon`, `component`,
     `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`,
     `create_time`, `updater`, `update_time`, `deleted`)
SELECT '异步任务提交', 'internship:task:job:create', 3, 6, @internship_task_menu_id,
       '', '', '', NULL, 0, b'1', b'1', b'1', 'admin', NOW(), 'admin', NOW(), b'0'
WHERE @internship_task_menu_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM `system_menu`
      WHERE `deleted` = b'0'
        AND `permission` = 'internship:task:job:create'
  );

INSERT INTO `system_menu`
    (`name`, `permission`, `type`, `sort`, `parent_id`, `path`, `icon`, `component`,
     `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`,
     `create_time`, `updater`, `update_time`, `deleted`)
SELECT '异步任务查询', 'internship:task:job:query', 3, 7, @internship_task_menu_id,
       '', '', '', NULL, 0, b'1', b'1', b'1', 'admin', NOW(), 'admin', NOW(), b'0'
WHERE @internship_task_menu_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM `system_menu`
      WHERE `deleted` = b'0'
        AND `permission` = 'internship:task:job:query'
  );
