-- ========
-- DDL
-- ========

-- 基金會成員資料
create table if not exists Member (
    memID VARCHAR(10) COMMENT '成員代號',
    dept_name VARCHAR(50) NOT NULL COMMENT '所屬部門',
    clearance_lv CHAR(1) DEFAULT '0' COMMENT '安保等級',
    permission CHAR(1) DEFAULT 'D' COMMENT '人員編級',
    mem_status VARCHAR(20) DEFAULT 'normal' COMMENT '精神狀態',
    password_hash VARCHAR(255) NOT NULL COMMENT '加密後的登入密碼',
    PRIMARY KEY (memID),
    CONSTRAINT chk_mem_clealv_format check (clearance_lv in ('0', '1', '2', '3')),
    CONSTRAINT chk_mem_perm_format check (permission in ('D', 'C', 'B', 'A')),
    CONSTRAINT chk_mem_status_format check (mem_status in('normal', 'abnormal', 'treating'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- SCP資料
create table if not exists SCP (
    scpID VARCHAR(5) COMMENT 'SCP代號',
    scp_status VARCHAR(20) COMMENT 'SCP的當前狀態',
    threat_level VARCHAR(10) COMMENT '威脅等級',
    appearance TEXT COMMENT '外型描述', 
    abilities TEXT COMMENT '特殊能力', 
    weakness TEXT COMMENT '弱點', 
    others TEXT COMMENT '其他', 
    PRIMARY KEY (scpID),
    CONSTRAINT chk_scp_status_format check (scp_status in ('contained', 'free', 'breached', 'uncontained')),
    CONSTRAINT chk_scp_threat_format check (threat_level in ('Safe', 'Euclid', 'Keter'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 任務資料
create table if not exists Mission (
    misID VARCHAR(10) COMMENT '任務代號',
    mis_status VARCHAR(20) COMMENT '任務狀態',
    memID VARCHAR(10) COMMENT '成員代號',
    scpID VARCHAR(5) COMMENT 'SCP代號',
    PRIMARY KEY (misID),
    FOREIGN KEY (memID) REFERENCES Member (memID) ON DELETE RESTRICT,
    FOREIGN KEY (scpID) REFERENCES SCP (scpID) ON DELETE RESTRICT,
    CONSTRAINT chk_mis_status_format check (mis_status in ('processing', 'completed', 'failed'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Site (收容措施) 實體表
CREATE TABLE if not exists Site (
    siteID VARCHAR(5) NOT NULL COMMENT '樓層分區編號',
    site_status BOOLEAN DEFAULT FALSE COMMENT '使用狀態',
    door_status BOOLEAN DEFAULT FALSE COMMENT '門禁狀態',
    structure VARCHAR(12) NOT NULL COMMENT '結構完整度',
    PRIMARY KEY (siteID),
    CONSTRAINT chk_site_structure CHECK (structure IN ('Functional 正常', 'Broken 已損壞'))  --只能是正常 或損壞
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Report (研究報告) 實體表
CREATE TABLE if not exists Report (
    reportID DATETIME NOT NULL COMMENT '事件編號', 
    required_lv CHAR(1) DEFAULT '1' COMMENT '查閱所需安保等級', 
    title VARCHAR(100) NOT NULL COMMENT '報告標題', 
    appearance TEXT COMMENT '外型描述', 
    abilities TEXT COMMENT '特殊能力', 
    weakness TEXT COMMENT '弱點', 
    others TEXT COMMENT '其他', 
    scpID VARCHAR(5) NOT NULL COMMENT 'SCP編號',  -- 待確認 involved_scp 為1對多關係無額外欄位直接將scpID合併到Report表中
    PRIMARY KEY (reportID),
    CONSTRAINT chk_report_lv CHECK (required_lv IN ('1', '2', '3')), --安保許可等級1 2 3 預設1
    FOREIGN KEY (scpID) REFERENCES SCP(scpID) ON UPDATE CASCADE ON DELETE CASCADE --scpID 必然存在於SCP表中 跟隨更新或刪除
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--------------------------------

-- research_leader (研究關係表) 
CREATE TABLE if not exists research_leader (
    reportID DATETIME NOT NULL COMMENT '事件編號', 
    memID VARCHAR(10) NOT NULL COMMENT '成員代號', --待確認
    role VARCHAR(20) NOT NULL COMMENT '身分角色', --待確認
    PRIMARY KEY (reportID, memID),
    CONSTRAINT chk_member_role CHECK (role IN ('leader', 'involved_member')), --成員所扮演角色 負責人或涉及成員
    FOREIGN KEY (reportID) REFERENCES Report(reportID) ON UPDATE CASCADE ON DELETE CASCADE, --ReportID 必然存在於Report表中 跟隨更新或刪除
    FOREIGN KEY (memID) REFERENCES Member(memID) ON UPDATE CASCADE ON DELETE RESTRICT --memID 必然存在於Member表中 跟隨更新 限制刪除 待確認
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- contained_in (收容關係表) 
CREATE TABLE if not exists contained_in (
    scpID VARCHAR(5) NOT NULL COMMENT 'SCP編號', 
    siteID VARCHAR(5) NOT NULL COMMENT '樓層分區編號', 
    PRIMARY KEY (scpID),
    FOREIGN KEY (scpID) REFERENCES SCP(scpID) ON UPDATE CASCADE ON DELETE CASCADE, --scpID 必然存在於SCP表中 跟隨更新或刪除
    FOREIGN KEY (siteID) REFERENCES Site(siteID) ON UPDATE CASCADE ON DELETE RESTRICT  --siteID 必然存在於Site表中 跟隨更新 待確認
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ========
-- Trigger
-- ========
delimiter //
create Trigger update_scp_status
AFTER update on Site for each row
BEGIN
    if new.door_status = TRUE and new.structure = 'Broken' then
        update scp set scp_status = 'breached'
        where scpID in (select scpID from contained_in where siteID = new.siteID);
    end if;
END //
delimiter ;
