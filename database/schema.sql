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
    CONSTRAINT chk_mem_status_format check (mem_status in('normal', 'abnormal', 'treating','dead')) --新增dead
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- SCP資料
create table if not exists SCP (
    scpID VARCHAR(5) COMMENT 'SCP代號',
    scp_status VARCHAR(20) COMMENT 'SCP的當前狀態',
    threat_level VARCHAR(10) COMMENT '威脅等級',
    clearance_lv CHAR(1) DEFAULT '0' COMMENT '安保等級', --新增安保等級
    appearance TEXT COMMENT '外型描述', 
    abilities TEXT COMMENT '特殊能力', 
    weakness TEXT COMMENT '弱點', 
    others TEXT COMMENT '其他', 
    PRIMARY KEY (scpID),
    CONSTRAINT chk_scp_clealv_format check (clearance_lv in ('0', '1', '2', '3')), --新增安保等級
    CONSTRAINT chk_scp_status_format check (scp_status in ('contained', 'free', 'breached', 'uncontained')),
    CONSTRAINT chk_scp_threat_format check (threat_level in ('Safe', 'Euclid', 'Keter'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 任務資料
create table if not exists Mission (
    misID VARCHAR(20) COMMENT '任務代號',
    mis_status VARCHAR(20) COMMENT '任務狀態',
    memID VARCHAR(10) not null COMMENT '成員代號',
    scpID VARCHAR(5) not null COMMENT 'SCP代號',
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
    CONSTRAINT chk_site_structure CHECK (structure IN ('Functional', 'Broken')) 
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
    scpID VARCHAR(5) NOT NULL COMMENT 'SCP代號', 
    PRIMARY KEY (reportID),
    FOREIGN KEY (scpID) REFERENCES SCP(scpID) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--------------------------------

-- research_leader (研究關係表) 
CREATE TABLE if not exists research_leader (
    reportID DATETIME NOT NULL COMMENT '事件編號', 
    memID VARCHAR(10) NOT NULL COMMENT '成員代號', 
    role VARCHAR(20) NOT NULL COMMENT '身分角色', 
    PRIMARY KEY (reportID, memID),
    CONSTRAINT chk_member_role CHECK (role IN ('leader', 'involved_member')), --成員所扮演角色 負責人或涉及成員 負責人一位待確認?
    FOREIGN KEY (reportID) REFERENCES Report(reportID) ON DELETE RESTRICT, 
    FOREIGN KEY (memID) REFERENCES Member(memID) ON DELETE RESTRICT 
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- contained_in (收容關係表) 
CREATE TABLE if not exists contained_in (
    scpID VARCHAR(5) NOT NULL COMMENT 'SCP編號', 
    siteID VARCHAR(5) NOT NULL COMMENT '樓層分區編號', 
    PRIMARY KEY (scpID),
    FOREIGN KEY (scpID) REFERENCES SCP(scpID) ON DELETE RESTRICT, 
    FOREIGN KEY (siteID) REFERENCES Site(siteID) ON DELETE RESTRICT  
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ========
-- Trigger
-- ========
delimiter //
--  Site 出問題，被關起來的 SCP 會變成逃脫
create Trigger update_scp_status
AFTER update on Site for each row
BEGIN
    if new.door_status = TRUE and new.structure = 'Broken' then
        update scp set scp_status = 'breached'
        where scpID in (select scpID from contained_in where siteID = new.siteID);
        delete from contained_in where siteID = new.siteID;
    end if;
END //
delimiter ;
