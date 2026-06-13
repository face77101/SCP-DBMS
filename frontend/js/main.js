/**
 * =========================================================================
 * 🛡️ SCP FOUNDATION SYSTEM CONTROL INTERFACE (SECURITY OPTIMIZED)
 * =========================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
    // 0. 身分驗證安保機制
    const clearanceLv = localStorage.getItem('clearance_lv');
    const deptName = (localStorage.getItem('dept_name') || '').trim().toUpperCase(); // 💡 撈取部門標籤並強制大寫

    if (!clearanceLv) {
        alert("ACCESS DENIED: No clearance token found.");
        window.location.href = "index.html";
        return;
    }
    document.getElementById('current-clearance').innerText = `CLEARANCE: LEVEL ${clearanceLv}`;
    // 💡 請將此段加在 main.js 內，0.身分驗證安保機制的下方
    const memStatus = localStorage.getItem('mem_status') || 'normal'; // 確保登入時有將狀態存入

    if (memStatus === 'abnormal') {
        const abnormalOverlay = document.getElementById('abnormal-overlay');
        if (abnormalOverlay) {
            abnormalOverlay.classList.add('active'); // 🟢 直接全螢幕暗紅鎖死，沒收全部操作！
            console.error("☣️ [CRITICAL LOCKOUT] OPERATIVE STATUS IS ABNORMAL. TERMINAL DISCONNECTED.");
            return; // 物理阻斷後面所有 API 的初始化加載
        }
    }

    // ========================================================
    // 🎯 【核心共用工具函式庫 (Helpers)】
    // ========================================================
    const lockdownOverlay = document.getElementById('lockdown-overlay'); // 📢 全域阻斷遮罩錨點
    const btnSwitchToAdd = document.getElementById('btn-switch-to-add');   // 📢 新增特工按鈕錨點
    
    // 🔌 統一 API 請求元件：自動引渡憑證與狀態碼攔截（加入 403 強制鎖定矩陣）
    async function requestAPI(url, options = {}) {
        const defaultOptions = { credentials: 'include' };
        const response = await fetch(url, { ...defaultOptions, ...options });
        
        // 💡 【核心優化】觸發 403 瞬間全螢幕封鎖
        if (response.status === 403) {
            console.error("🚨 [SECURITY BREACH] DETECTED 403 FORBIDDEN. INITIALIZING LOCKDOWN PROTOCOL.");
            const abnormalOverlay = document.getElementById('abnormal-overlay');
            if (abnormalOverlay) {
                abnormalOverlay.style.display = 'flex'; // 強制讓阻斷遮罩在畫面上顯示（遮蔽全螢幕）
                abnormalOverlay.classList.add('active'); // 啟用可能存在的 CSS 動態效果
            }
            throw new Error("CRITICAL SECURITY ERROR: 403 FORBIDDEN. TERMINAL LOCKED DOWN.");
        }

        if (!response.ok) {
            throw new Error(`HTTP AUTHENTICATION ERROR: ${response.status}`);
        }
        return response.json();
    }

    // 🧠 統一本地模糊搜尋元件
    function bindLocalSearch(inputId, tableRowsSelector, skipClasses = []) {
        const input = document.getElementById(inputId);
        if (!input) return;
        input.addEventListener('input', (e) => {
            const keyword = e.target.value.toLowerCase().trim();
            document.querySelectorAll(tableRowsSelector).forEach(row => {
                const isSkip = skipClasses.some(cls => row.classList.contains(cls));
                if (!isSkip) {
                    row.style.display = row.textContent.toLowerCase().includes(keyword) ? '' : 'none';
                }
            });
        });
    }

    // 🔒 統一按鈕狀態安全鎖
    function setButtonLoading(btnElement, isLoading, loadingText = "⚡ TRANSMITTING...", originalText = "") {
        if (!btnElement) return;
        btnElement.disabled = isLoading;
        btnElement.textContent = isLoading ? loadingText : originalText;
    }

    // 🛡️ 【安保隔離矩陣】高危人員編制按鈕審查網關
    function enforceAddPersonnelSecurity() {
        if (btnSwitchToAdd) {
            // 👑 只有當前登入者的部門精準等於 'O5'，且安保等級達到 LEVEL 3 時，才獲准解鎖按鈕
            if (deptName === 'O5' && parseInt(clearanceLv) >= 3) {
                console.log("👑 [SECURITY AUDIT] O5 最高議會成員身分核實。解鎖特工編制按鈕。");
                btnSwitchToAdd.style.display = 'block'; // 釋放按鈕現形
            } else {
                console.log("👤 [SECURITY AUDIT] 常規特工身分。沒收特工編制權限，從 DOM 物理移除按鈕實體。");
                btnSwitchToAdd.remove(); // 物理銷毀節點，防範 F12 修改 CSS 繞過
            }
        }
    }

    // ========================================================
    // 【功能一：🧭 Navbar 頁籤切換控制與全自動資料引渡】
    // ========================================================
    const navButtons = document.querySelectorAll('.nav-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    const tabFetchRegistry = {
        'scp-view-section': () => fetchAndRenderSCPs(),
        'sites-section': () => fetchAndRenderSiteStatus(),
        'members-section': () => fetchAndRenderMembers(),
        'report-upload-section': () => dispatchReportTab() 
    };
    
    function dispatchReportTab() {
        const agentUploadView = document.getElementById('subview-agent-upload');
        const o5ListSubview = document.getElementById('subview-o5-list');
        const o5DetailWorkspace = document.getElementById('subview-o5-detail-workspace');
        const navBtn = document.querySelector('.nav-btn[data-target="report-upload-section"]');

        console.log(`[AUTH WATCHDOG] 當前讀取到的特工部門標籤: "${deptName}"`);

        if (deptName === 'O5') {
            console.log("👑 [O5 IDENTIFIED] 成功偵測到最高議會權限，啟動雙階段審查矩陣。");
            if (navBtn) navBtn.textContent = "REPORTS";
            if (agentUploadView) agentUploadView.style.display = 'none';
            if (o5ListSubview) o5ListSubview.style.display = 'block'; 
            if (o5DetailWorkspace) o5DetailWorkspace.style.display = 'none';
            fetchAndRenderO5ReportList(); 
        } else {
            console.log("👤 [AGENT IDENTIFIED] 常規特工權限，開啟研究報告提交網關。");
            if (navBtn) navBtn.textContent = "SUBMIT REPORT";
            if (agentUploadView) agentUploadView.style.display = 'block';
            if (o5ListSubview) o5ListSubview.style.display = 'none';
            if (o5DetailWorkspace) o5DetailWorkspace.style.display = 'none';
        }
    }

    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            navButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const targetId = btn.getAttribute('data-target');
            tabContents.forEach(content => {
                content.classList.toggle('active', content.id === targetId);
            });
            if (tabFetchRegistry[targetId]) {
                console.log(`[NAVIGATOR] 自動引渡分頁數據鏈: ${targetId}`);
                tabFetchRegistry[targetId]();
            }
        });
    });

    // ========================================================
    // 【功能二：SCP 列表動態渲染】
    // ========================================================
    const tableBody = document.getElementById('scp-table-body');
    let scpAbortController = null;

    async function fetchAndRenderSCPs() {
        const currentClearance = localStorage.getItem('clearance_lv') || '0'; 
        if (scpAbortController) scpAbortController.abort();
        scpAbortController = new AbortController();

        tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="loading-text" style="color: #ffc107; text-align: center; padding: 20px; background: rgba(0,0,0,0.5);">
                    📡 [SYSTEM] ENGAGING DATABASE SCAN FOR LEVEL ${currentClearance}... PLEASE HOLD
                </td>
            </tr>
        `;

        try {
            const url = `http://localhost:5000/api/scp/search?clearance_lv=${currentClearance}`;
            const result = await requestAPI(url, { signal: scpAbortController.signal });

            tableBody.innerHTML = '';
            if (result.length === 0) {
                tableBody.innerHTML = `<tr><td colspan="8" class="no-data-text" style="text-align: center; color: #ff3333;">NO REGISTRIES FOUND WITHIN LEVEL ${currentClearance}</td></tr>`;
                return;
            }

            result.forEach(scp => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="scp-id-col">${scp.scpID}</td>
                    <td><span class="status-badge ${scp.scp_status.toLowerCase()}">${scp.scp_status}</span></td>
                    <td><span class="threat-badge ${scp.threat_level.toLowerCase()}">${scp.threat_level}</span></td>
                    <td class="center-text">${scp.clearance_lv}</td>
                    <td class="text-left">${scp.appearance || 'N/A'}</td>
                    <td class="text-left">${scp.abilities || 'N/A'}</td>
                    <td class="text-left">${scp.weakness || 'N/A'}</td>
                    <td class="text-left">${scp.others || 'N/A'}</td>
                `;
                tableBody.appendChild(tr);
            });
        } catch (error) {
            if (error.name === 'AbortError') return; 
            console.error('SCP Fetch Error:', error);
            tableBody.innerHTML = `<tr><td colspan="8" class="error-text" style="color: #ff3333; font-weight: bold; text-align: center;">CRITICAL: FAILED TO COMMUNICATE WITH DATABASE</td></tr>`;
        }
    }

    bindLocalSearch('scp-search', '#scp-table-body tr', ['no-data-text', 'error-text']);
    fetchAndRenderSCPs();

    // ========================================================
    // 【功能三：接管組員的 Report 提交邏輯】
    // ========================================================
    const btnSubmitReport = document.getElementById('btn-submit-report');
    const responseLog = document.getElementById('responseLog');

    if (btnSubmitReport) {
        btnSubmitReport.addEventListener('click', async () => {
            const membersStr = document.getElementById('involvedMembers').value;
            const reportData = {
                title: document.getElementById('title').value,
                scpID: document.getElementById('scpID').value,
                abilities: document.getElementById('abilities').value,
                weakness: document.getElementById('weakness').value,
                appearance: document.getElementById('appearance').value,
                others: document.getElementById('others').value,
                involved_members: membersStr ? membersStr.split(',').map(s => s.trim()) : [],
                required_lv: "1"
            };

            if (lockdownOverlay) lockdownOverlay.classList.add('active');
            setButtonLoading(btnSubmitReport, true, "⚡ TRANSMITTING ENCRYPTED DATA...");
            responseLog.textContent = "TRANSMITTING ENCRYPTED DATA PACKET TO BACKEND...";

            try {
                const data = await requestAPI('http://localhost:5000/api/reports/upload', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(reportData)
                });
                responseLog.textContent = "SUCCESSFULLY WRITTEN TO MYSQL DATABASE!\n\nRESPONSE:\n" + JSON.stringify(data, null, 2);
                btnSubmitReport.textContent = "✔ INJECTION SUCCESS";
                
                alert("[安保憑證已核可] 研究報告已成功上傳至待審查核心。");
                
                setTimeout(() => setButtonLoading(btnSubmitReport, false, "", "EXECUTE MySQL DATA INJECTION"), 2000);
            } catch (err) {
                setButtonLoading(btnSubmitReport, false, "", "EXECUTE MySQL DATA INJECTION");
                responseLog.textContent = err.message.includes('401') 
                    ? "401 UNAUTHORIZED: SESSION EXPIRED OR INVALID CREDENTIALS."
                    : "CRITICAL CONTAMINATION ERROR:\n" + err;
            } finally {
                if (lockdownOverlay) lockdownOverlay.classList.remove('active');
            }
        });
    }

    // ========================================================
    // 【功能四：🚨 站點收容與結構動態監控】
    // ========================================================
    const grid = document.getElementById('site-grid');
    const errorMsg = document.getElementById('site-error-msg');

    async function fetchAndRenderSiteStatus() {
        if (!grid) return;
        try {
            const data = await requestAPI('http://localhost:5000/api/admin/sites');
            grid.innerHTML = ''; 
            if (errorMsg) errorMsg.textContent = '';

            if (!data || data.length === 0) {
                grid.innerHTML = '<div class="loading-text" style="grid-column: span 2;">[INFO] NO SITE DETECTED.</div>';
                return;
            }

            const floors = {};
            data.forEach(row => {
                if (row && row.siteID) {
                    const floor = String(row.siteID).split('-')[0] || 'UNKNOWN';
                    if (!floors[floor]) floors[floor] = [];
                    floors[floor].push(row);
                }
            });

            Object.keys(floors).sort().forEach(floor => {
                const tbodyHTML = floors[floor].map(row => {
                    const isBroken = (row.door_status == 1 && row.structure === 'Broken');
                    return `
                        <tr class="${isBroken ? 'broken-containment' : ''}" style="${isBroken ? 'background: #5a1111 !important;' : ''}">
                            <td style="padding: 10px; border-bottom: 1px solid #333; font-family: monospace;">${row.siteID}</td>
                            <td style="padding: 10px; border-bottom: 1px solid #333; font-weight: bold; color: #00bcd4;">${row.scpID ? `${row.scpID}` : '-'}</td>
                            <td class="${row.site_status == 1 ? 'status-inuse' : 'status-idl'}" style="padding: 10px; border-bottom: 1px solid #333; color: ${row.site_status == 1 ? '#00e676' : '#a0a0a0'};">
                                ${row.site_status == 1 ? 'INUSE' : 'IDL'}
                            </td>
                            <td style="padding: 10px; border-bottom: 1px solid #333;">${row.door_status == 1 ? 'LOCK' : 'OPEN'}</td>
                            <td class="${row.structure === 'Broken' ? 'struct-broke' : 'struct-funct'}" style="padding: 10px; border-bottom: 1px solid #333; color: ${row.structure === 'Broken' ? '#ff5252' : '#e0e0e0'};">
                                ${row.structure === 'Broken' ? 'BROKE' : 'FUNCT.'}
                            </td>
                        </tr>
                    `;
                }).join('');

                const div = document.createElement('div');
                div.className = 'floor-block';
                div.style.marginBottom = '1.5rem';
                div.innerHTML = `
                    <div class="floor-title">FLOOR: ${floor}</div>
                    <table class="scp-table" style="width: 100%; border-collapse: collapse; font-size: 13px;">
                        <thead>
                            <tr style="background: rgba(0, 188, 212, 0.15); color: #00bcd4;">
                                <th style="padding: 10px; text-align: left;">SITE_ID</th><th style="padding: 10px; text-align: left;">SCP_ID</th>
                                <th style="padding: 10px; text-align: left;">STAT.</th><th style="padding: 10px; text-align: left;">DOOR STAT.</th>
                                <th style="padding: 10px; text-align: left;">STRUCT.</th>
                            </tr>
                        </thead>
                        <tbody>${tbodyHTML}</tbody>
                    </table>
                `;
                grid.appendChild(div);
            });
        } catch (err) {
            console.error('[Sites Matrix Error]', err);
            grid.innerHTML = `<div class="loading-text" style="grid-column: span 2; color: #ff5252;">🚨 MONITOR SYSTEM CORRUPTED: ${err.message}</div>`;
            if (errorMsg) errorMsg.textContent = 'CRITICAL CORRUPTION: FAILED TO FETCH SITE DIRECTORY. ' + err;
        }
    }

    // ========================================================
    // 【功能五：👥 基金會成員清單加載與狀態校準】
    // ========================================================
    const memberTableBody = document.getElementById('member-table-body');
    const memberSubtitle = document.getElementById('member-subtitle');
    const memberErrorMsg = document.getElementById('member-error-msg');

    async function fetchAndRenderMembers() {
        if (!memberTableBody) return;
        try {
            const data = await requestAPI('http://localhost:5000/api/admin/members');
            memberSubtitle.textContent = `AUTHORIZED ACCESS: DEPLOYED OPERATIVES IN FIELD = ${data.length}`;
            memberTableBody.innerHTML = '';

            data.forEach(m => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="scp-id-col"><a href="/member_detail.html?memID=${m.memID}">${m.memID}</a></td>
                    <td>${m.dept_name || 'Unassigned'}</td>
                    <td class="center-text">LEVEL ${m.clearance_lv}</td>
                    <td>${m.permission || 'Class D'}</td>
                    <td id="status-${m.memID}" style="font-weight: bold; color: ${m.mem_status === 'normal' ? '#00e676' : '#ff5252'}">${m.mem_status}</td>
                    <td>
                        <select class="status-updater" data-id="${m.memID}">
                            <option value="">-- SELECT --</option>
                            <option value="normal">Normal</option>
                            <option value="abnormal">Abnormal (Cognitohazard)</option>
                            <option value="treating">Treating (Amnestic)</option>
                            <option value="dead">Dead / Terminated</option>
                        </select>
                    </td>
                `;
                memberTableBody.appendChild(tr);
            });

            document.querySelectorAll('.status-updater').forEach(selectElement => {
                selectElement.addEventListener('change', (e) => {
                    const targetId = e.target.getAttribute('data-id');
                    const selectedStatus = e.target.value;
                    if (selectedStatus) executeStatusPatch(targetId, selectedStatus, e.target); 
                });
            });
        } catch (err) {
            if (memberErrorMsg) memberErrorMsg.textContent = 'CRITICAL CORRUPTION: FAILED TO FETCH AGENT DIRECTORY. ' + err;
        }
    }

    async function executeStatusPatch(memID, newStatus, selectElement) {
        const statusCell = document.getElementById(`status-${memID}`);
        const originalText = statusCell ? statusCell.textContent : 'normal';
        const originalColor = statusCell ? statusCell.style.color : '#00e676';

        if (lockdownOverlay) lockdownOverlay.classList.add('active');
        if (selectElement) selectElement.disabled = true;
        if (statusCell) {
            statusCell.textContent = "⏳ CALIBRATING...";
            statusCell.style.color = "#ffc107"; 
        }

        try {
            const data = await requestAPI(`http://localhost:5000/api/admin/members/${memID}/status`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mem_status: newStatus })
            });
            
            if (data.message) {
                if (statusCell) {
                    statusCell.textContent = newStatus;
                    statusCell.style.color = newStatus === 'normal' ? '#00e676' : '#ff5252';
                }
                alert(`[資格已確認] 特工編號 ${memID} 之生命/精神狀態已被成功同步校準。`);
            }
        } catch (err) {
            alert('TRANSMISSION CONTAMINATION: ' + err.message);
            if (statusCell) {
                statusCell.textContent = originalText;
                statusCell.style.color = originalColor;
            }
        } finally {
            if (lockdownOverlay) lockdownOverlay.classList.remove('active');
            if (selectElement) {
                selectElement.value = ""; 
                selectElement.disabled = false;
            }
        }
    }

    bindLocalSearch('member-search', '#member-table-body tr');

    // ========================================================
    // 【功能六：🎭 子檢視區切換與新特工數據注入】
    // ========================================================
    const memberListSubview = document.getElementById('member-list-subview');
    const memberAddSubview  = document.getElementById('member-add-subview');
    const btnCancelAdd      = document.getElementById('btn-cancel-add');
    const btnExecuteAdd     = document.getElementById('btn-execute-add');
    const addMemberLog      = document.getElementById('add-member-log');

    if (btnSwitchToAdd && memberListSubview && memberAddSubview) {
        btnSwitchToAdd.addEventListener('click', () => {
            memberListSubview.style.display = 'none';
            memberAddSubview.style.display = 'block';
            addMemberLog.textContent = "SYSTEM IDLE. AWAITING INJECTION OPERATION...";
            addMemberLog.style.color = "#e0e0e0";
            setButtonLoading(btnExecuteAdd, false, "", "EXECUTE REGISTRY INJECTION");
            if (btnCancelAdd) btnCancelAdd.disabled = false;
        });
    }

    if (btnCancelAdd && memberListSubview && memberAddSubview) {
        btnCancelAdd.addEventListener('click', () => {
            memberAddSubview.style.display = 'none';
            memberListSubview.style.display = 'block';
            fetchAndRenderMembers(); 
        });
    }

    if (btnExecuteAdd) {
        btnExecuteAdd.addEventListener('click', async () => {
            const dept_name    = document.getElementById('add-dept-name').value.trim();
            const clearance_lv = document.getElementById('add-clearance-lv').value;
            const permission   = document.getElementById('add-permission').value;
            const mem_status   = document.getElementById('add-mem-status').value;
            const password     = document.getElementById('add-password').value;

            if (!dept_name || !password) {
                addMemberLog.textContent = "[X] INJECTION CRITICAL ERROR:\nDEPARTMENT ACRONYM AND PASSWORD CANNOT BE VACANT.";
                addMemberLog.style.color = "#ff5252";
                return;
            }

            if (lockdownOverlay) lockdownOverlay.classList.add('active');
            setButtonLoading(btnExecuteAdd, true, "⚡ INJECTING DATASTREAM...");
            if (btnCancelAdd) btnCancelAdd.disabled = true;
            addMemberLog.textContent = "⚙️ INITIALIZING DATABASE INJECTION PROTOCOL...";
            addMemberLog.style.color = "#ffc107";

            try {
                const data = await requestAPI('http://localhost:5000/api/admin/members', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ dept_name, clearance_lv, permission, mem_status, password })
                });

                addMemberLog.textContent = `🎉 SUCCESSFULLY INJECTED TO MYSQL DATABASE!\n\nGENERATED REGISTRY ID: ${data.memID}\nSTATUS: ${data.message.toUpperCase()}`;
                addMemberLog.style.color = "#00e676";
                btnExecuteAdd.textContent = "✔ INJECTION COMPLETED";
                
                alert(`[資格已確認] 新進人員數據結構已順利生成。識別代號：${data.memID}`);

                document.getElementById('add-dept-name').value = '';
                document.getElementById('add-password').value = '';
                
                setTimeout(() => {
                    if (memberAddSubview && memberListSubview) {
                        memberAddSubview.style.display = 'none';
                        memberListSubview.style.display = 'block';
                        fetchAndRenderMembers();
                    }
                }, 2000);
            } catch (err) {
                addMemberLog.textContent = `[X] INJECTION REFUSED:\n${err.message}`;
                addMemberLog.style.color = "#ff5252";
                setButtonLoading(btnExecuteAdd, false, "", "EXECUTE REGISTRY INJECTION");
                if (btnCancelAdd) btnCancelAdd.disabled = false;
            } finally {
                if (lockdownOverlay) lockdownOverlay.classList.remove('active');
            }
        });
    }

    // =========================================================================
    // 👑 【審查決策核心程序 - 核心固化】
    // =========================================================================
    const o5ListBody = document.getElementById('o5-report-list-body');
    const o5ListSubview = document.getElementById('subview-o5-list');
    const o5DetailWorkspace = document.getElementById('subview-o5-detail-workspace');
    let activeReviewReportID = null; 

    async function fetchAndRenderO5ReportList() {
        if (!o5ListBody) return;
        try {
            const data = await requestAPI('http://localhost:5000/api/admin/reports');
            const subtitleEl = document.getElementById('o5-list-subtitle');
            if (subtitleEl) subtitleEl.textContent = `LEVEL 3 CLEARANCE GRANTED: PENDING FILES = ${data.length}`;
            o5ListBody.innerHTML = '';

            if (data.length === 0) {
                o5ListBody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: #00e676; padding: 20px;">[CLEARED] 當前無任何待審查之數據封包。</td></tr>`;
                return;
            }

            data.forEach(r => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="padding: 10px; border-bottom: 1px solid #333; font-family: monospace;">${r.reportID}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #333; font-weight: bold; color: #00bcd4;">${r.scpID}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #333;">${r.title}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #333; text-align: center;">
                        <button class="terminal-btn btn-go-review" data-payload='${JSON.stringify(r)}' style="padding: 3px 10px; margin: 0;">VIEW DETAILS (審查)</button>
                    </td>
                `;
                o5ListBody.appendChild(tr);
            });

            document.querySelectorAll('.btn-go-review').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const reportPayload = JSON.parse(e.target.getAttribute('data-payload'));
                    openReviewWorkspace(reportPayload);
                });
            });
        } catch (err) {
            console.error('Fetch report list failed:', err);
        }
    }

    async function openReviewWorkspace(report) {
        activeReviewReportID = report.reportID;
        document.getElementById('view-report-meta').textContent = `TIMESTAMP: ${report.reportID}`;
        document.getElementById('view-report-title').textContent = report.title;
        document.getElementById('view-report-scpid').textContent = report.scpID;
        document.getElementById('view-report-abl').textContent = report.abilities || 'N/A';
        document.getElementById('view-report-weak').textContent = report.weakness || 'N/A';
        document.getElementById('view-report-app').textContent = report.appearance || 'N/A';

        document.getElementById('view-official-scpid').textContent = report.scpID;
        document.getElementById('view-official-status').textContent = "SEARCHING...";
        document.getElementById('view-official-app').textContent = "LOADING...";
        document.getElementById('view-official-abl').textContent = "LOADING...";
        document.getElementById('view-official-weak').textContent = "LOADING...";

        const clearanceContainer = document.getElementById('view-official-clearance-container');
        if (o5ListSubview) o5ListSubview.style.display = 'none';
        if (o5DetailWorkspace) o5DetailWorkspace.style.display = 'block';

        try {
            const officialData = await requestAPI(`http://localhost:5000/api/scp/search?scpID=${report.scpID}`);
            let currentLv = "0"; 

            if (officialData && officialData.length > 0) {
                const official = officialData[0];
                currentLv = official.clearance_lv !== undefined ? String(official.clearance_lv) : "0";
                document.getElementById('view-official-status').textContent = official.scp_status || 'SECURE';
                document.getElementById('view-official-app').textContent = official.appearance || 'None recorded.';
                document.getElementById('view-official-abl').textContent = official.abilities || 'None recorded.';
                document.getElementById('view-official-weak').textContent = official.weakness || 'None recorded.';
            } else {
                document.getElementById('view-official-status').textContent = "NEW ANOMALY";
                document.getElementById('view-official-app').textContent = "[未登錄全新項目]";
                document.getElementById('view-official-abl').textContent = "[未登錄全新項目]";
                document.getElementById('view-official-weak').textContent = "[未登錄全新項目]";
            }

            if (clearanceContainer) {
                clearanceContainer.innerHTML = `
                    <select id="update-scp-clearance-lv" style="padding: 5px; background: #111; color: #00bcd4; border: 1px solid #333; font-family: monospace;">
                        <option value="0" ${currentLv === "0" ? "selected" : ""}>LEVEL 0 (Unrestricted)</option>
                        <option value="1" ${currentLv === "1" ? "selected" : ""}>LEVEL 1 (Restricted)</option>
                        <option value="2" ${currentLv === "2" ? "selected" : ""}>LEVEL 2 (Confidential)</option>
                        <option value="3" ${currentLv === "3" ? "selected" : ""}>LEVEL 3 (Secret)</option>
                    </select>
                `;
            }
        } catch (err) {
            console.error('Fetch official info failed:', err);
        }
    }

    document.getElementById('btn-back-to-o5-list')?.addEventListener('click', () => {
        if (o5DetailWorkspace) o5DetailWorkspace.style.display = 'none';
        if (o5ListSubview) o5ListSubview.style.display = 'block';
        fetchAndRenderO5ReportList();
    });

    // =========================================================================
    // 🕹️ 審查控制核心
    // =========================================================================
    const btnO5Save = document.getElementById('btn-o5-save');
    const btnO5Reject = document.getElementById('btn-o5-reject');

    btnO5Save?.addEventListener('click', async () => {
        if (!activeReviewReportID) return;
        if (lockdownOverlay) lockdownOverlay.classList.add('active');
        
        btnO5Save.disabled = true;
        btnO5Save.textContent = "⚡ MERGING PACKETS...";
        if (btnO5Reject) btnO5Reject.disabled = true;

        try {
            await requestAPI('http://localhost:5000/api/O5/approve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    reportID: activeReviewReportID,
                    clearance_lv: document.getElementById('update-scp-clearance-lv')?.value || "0" 
                })
            });
            
            alert(`[資格已確認] 報告數據已成功與核心主字典完成串接整併。`);
            
            await fetchAndRenderO5ReportList();
            if (o5DetailWorkspace) o5DetailWorkspace.style.display = 'none';
            if (o5ListSubview) o5ListSubview.style.display = 'block';
            activeReviewReportID = null;
        } catch (err) {
            alert('審查授權失敗: ' + err.message);
        } finally {
            if (lockdownOverlay) lockdownOverlay.classList.remove('active');
            if (btnO5Save) {
                btnO5Save.disabled = false;
                btnO5Save.textContent = "SAVE & MERGE (通過)";
            }
            if (btnO5Reject) btnO5Reject.disabled = false;
        }
    });

    btnO5Reject?.addEventListener('click', async () => {
        if (!activeReviewReportID) return;
        if (!confirm('[WARNING] 確定要駁回並物理銷毀這篇研究報告嗎？此操作不可逆。')) return;
        if (lockdownOverlay) lockdownOverlay.classList.add('active');
        
        btnO5Reject.disabled = true;
        btnO5Reject.textContent = "🔥 ERASING LOGS...";
        if (btnO5Save) btnO5Save.disabled = true;

        try {
            await requestAPI('http://localhost:5000/api/O5/reject', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reportID: activeReviewReportID })
            });
            
            alert(`[審查程序終止] 該報告封包已從暫存庫中完全物理銷毀。`);
            
            await fetchAndRenderO5ReportList();
            if (o5DetailWorkspace) o5DetailWorkspace.style.display = 'none';
            if (o5ListSubview) o5ListSubview.style.display = 'block';
            activeReviewReportID = null;
        } catch (err) {
            alert('駁回執行失敗: ' + err.message);
        } finally {
            if (lockdownOverlay) lockdownOverlay.classList.remove('active');
            if (btnO5Reject) {
                btnO5Reject.disabled = false;
                btnO5Reject.textContent = "REJECT (駁回)";
            }
            if (btnO5Save) btnO5Save.disabled = false;
        }
    });

    // =========================================================================
    // 📢 【全域初始化同步錨點】
    // =========================================================================
    console.log('[SYSTEM READY] 正在執行全域權限與分流初始化連線...');
    enforceAddPersonnelSecurity(); // 💡 初始化時立刻執行高危按鈕物理隔離審查
    dispatchReportTab();
});