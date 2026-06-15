/**
 * =========================================================================
 * 🛡️ SCP FOUNDATION SYSTEM CONTROL INTERFACE (SECURITY OPTIMIZED v2.5)
 * =========================================================================
 */

document.addEventListener('DOMContentLoaded', async () => {
    // =========================================================================
    // 👑 0. 【變數宣告陣列】集中宣告，杜絕 ReferenceError 與暫時性死區 (TDZ)
    // =========================================================================
    
    // 零信任前置防禦矩陣相關 DOM
    const currentClearanceSpan = document.getElementById('current-clearance');
    const psychIndicator = document.getElementById('psych-status-indicator');
    const abnormalOverlay = document.getElementById('abnormal-overlay');
    const btnSwitchToAdd = document.getElementById('btn-switch-to-add');
    const lockdownOverlay = document.getElementById('lockdown-overlay'); // 全域遮罩

    // 功能一：Navbar 頁籤切換控制相關 DOM 與動態路由註冊表
    const navButtons = document.querySelectorAll('.nav-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    const tabFetchRegistry = {
        'scp-view-section': () => fetchAndRenderSCPs(),
        'sites-section': () => fetchAndRenderSiteStatus(),
        'members-section': () => fetchAndRenderMembers(),
        // 完美同步：報告頁籤動態加載阻斷網關
        'report-upload-section': async () => {
            const isO5 = currentClearanceSpan?.innerText.includes('O5');
            if (isO5) {
                await fetchAndRenderO5ReportList();
            } else {
                // 常規特工節制：注入仿真動態安保校準訊號
                await new Promise(resolve => setTimeout(resolve, 300));
            }
        }
    };

    // 功能二：SCP 列表動態渲染相關 DOM 與控制線
    const scpTableBody = document.getElementById('scp-table-body');
    let scpAbortController = null;

    // 功能三：特工提交研究報告相關 DOM
    const btnSubmitReport = document.getElementById('btn-submit-report');
    const responseLog = document.getElementById('responseLog');

    // 功能四：站點收容與動態監控相關 DOM
    const grid = document.getElementById('site-grid');
    const errorMsg = document.getElementById('site-error-msg');

    // 功能五：基金會成員清單相關 DOM
    const memberTableBody = document.getElementById('member-table-body');
    const memberSubtitle = document.getElementById('member-subtitle');

    // 功能六：新特工編制注入相關 DOM
    const memberListSubview = document.getElementById('member-list-subview');
    const memberAddSubview  = document.getElementById('member-add-subview');
    const btnCancelAdd      = document.getElementById('btn-cancel-add');
    const btnExecuteAdd     = document.getElementById('btn-execute-add');
    const addMemberLog      = document.getElementById('add-member-log');

    // 功能七：O5 審查決策核心相關 DOM 與暫存器
    const o5ListBody = document.getElementById('o5-report-list-body');
    const o5ListSubview = document.getElementById('subview-o5-list');
    const o5DetailWorkspace = document.getElementById('subview-o5-detail-workspace');
    const btnO5Save = document.getElementById('btn-o5-save');
    const btnO5Reject = document.getElementById('btn-o5-reject');
    let activeReviewReportID = null; 

    // 功能八：用戶選單顯示與登出相關 DOM
    const userTrigger = document.getElementById('user-menu-trigger');
    const userMenu = document.getElementById('user-dropdown-menu');
    const btnLogout = document.getElementById('btn-logout');


    // =========================================================================
    // 🎯 1. 【核心共用工具函式庫 (Helpers)】(優先宣告以供後續執行核心調用)
    // =========================================================================

    function initializeTerminalHelpers() {
        bindLocalSearch('search-input', '.agent-row', ['fixed-row']);
        bindLocalSearch('scp-search', '#scp-table-body tr', ['no-data-text', 'error-text']);
        bindLocalSearch('member-search', '#member-table-body tr');
    }

    async function requestAPI(url, options = {}) {
        const combinedOptions = { credentials: 'include', ...options };
        const response = await fetch(url, combinedOptions);
        
        if (response.status === 403) {
            console.error("🚨 [SECURITY BREACH] 偵測到越權請求 (403 Forbidden)！");
            if (abnormalOverlay) {
                abnormalOverlay.style.display = 'flex';
                abnormalOverlay.classList.add('active');
            }
        }

        if (!response.ok) {
            let backendMessage = `HTTP 通訊異常: ${response.status}`;
            try {
                const errorData = await response.json();
                if (errorData.message) backendMessage = errorData.message;
            } catch (e) {
                console.error('無法解析後端錯誤格式');
            }
            throw new Error(backendMessage);
        }
        
        return response.json();
    }

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

    function setButtonLoading(btnElement, isLoading, loadingText = "⚡ TRANSMITTING...", originalText = "") {
        if (!btnElement) return;
        btnElement.disabled = isLoading;
        btnElement.textContent = isLoading ? loadingText : originalText;
    }


    // ========================================================
    // 【功能一：🧭 Navbar 頁籤切換控制與全隔離柵欄】
    // ========================================================
    function dispatchReportTab(currentDeptName) {
        const agentUploadView = document.getElementById('subview-agent-upload');
        const o5ListSubview = document.getElementById('subview-o5-list');
        const o5DetailWorkspace = document.getElementById('subview-o5-detail-workspace');
        const navBtn = document.querySelector('.nav-btn[data-target="report-section"]');

        if (currentDeptName === 'O5') {
            if (navBtn) navBtn.textContent = "REPORTS";
            if (agentUploadView) agentUploadView.style.display = 'none';
            if (o5ListSubview) o5ListSubview.style.display = 'block'; 
            if (o5DetailWorkspace) o5DetailWorkspace.style.display = 'none';
            // 提示：主序引導時會統一 await 加載，此處不執行獨立非同步發射
        } else {
            if (navBtn) navBtn.textContent = "SUBMIT REPORT";
            if (agentUploadView) agentUploadView.style.display = 'block';
            if (o5ListSubview) o5ListSubview.style.display = 'none';
            if (o5DetailWorkspace) o5DetailWorkspace.style.display = 'none';
        }
    }

    navButtons.forEach(btn => {
        btn.addEventListener('click', async () => {
            const targetId = btn.getAttribute('data-target');
            
            // 開啟全域加載黑屏
            if (tabFetchRegistry[targetId] && lockdownOverlay) {
                lockdownOverlay.classList.add('active');
                const titleEl = lockdownOverlay.querySelector('.lockdown-title');
                const subEl = lockdownOverlay.querySelector('.lockdown-sub');
                if (titleEl) titleEl.textContent = `📡 QUERYING RECONNAISSANCE PROTOCOL: ${targetId.toUpperCase()}`;
                if (subEl) subEl.textContent = "DECRYPTION IN PROGRESS // FETCHING SECURE DATALINK...";
            }

            // UI 頁籤狀態轉換
            navButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            tabContents.forEach(content => {
                content.classList.toggle('active', content.id === targetId);
            });

            // 執行非同步數據同步，並實施強硬阻塞 (Barrier)
            try {
                if (tabFetchRegistry[targetId]) {
                    await tabFetchRegistry[targetId]();
                }
            } catch (err) {
                console.error("頁籤切換資料加載失敗:", err);
            } finally {
                // 完全加載完畢後開燈解除隔離
                if (lockdownOverlay) {
                    lockdownOverlay.classList.remove('active');
                }
            }
        });
    });


    // ========================================================
    // 【功能二：SCP 列表動態渲染】
    // ========================================================
    async function fetchAndRenderSCPs() {
        if (!scpTableBody) return;
        if (scpAbortController) scpAbortController.abort();
        scpAbortController = new AbortController();

        scpTableBody.innerHTML = `<tr><td colspan="8" class="loading-text" style="color: #ffc107; text-align: center; padding: 20px;">📡 [SYSTEM] ENGAGING DATABASE SCAN... PLEASE HOLD</td></tr>`;

        try {
            const result = await requestAPI('/api/scp/search', { signal: scpAbortController.signal });
            scpTableBody.innerHTML = '';
            
            if (result.length === 0) {
                scpTableBody.innerHTML = `<tr><td colspan="8" class="no-data-text" style="text-align: center; color: #ff3333;">NO REGISTRIES FOUND</td></tr>`;
                return;
            }

            result.forEach(scp => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="scp-id-col">${scp.scpID}</td>
                    <td><span class="status-badge ${scp.scp_status?.toLowerCase()}">${scp.scp_status}</span></td>
                    <td><span class="threat-badge ${scp.threat_level?.toLowerCase()}">${scp.threat_level}</span></td>
                    <td class="center-text">${scp.clearance_lv}</td>
                    <td class="text-left">${scp.appearance || 'N/A'}</td>
                    <td class="text-left">${scp.abilities || 'N/A'}</td>
                    <td class="text-left">${scp.weakness || 'N/A'}</td>
                    <td class="text-left">${scp.others || 'N/A'}</td>
                `;
                scpTableBody.appendChild(tr);
            });
        } catch (err) {
            if (err.name === 'AbortError') return; 
            scpTableBody.innerHTML = `<tr><td colspan="8" class="error-text" style="color: #ff3333; text-align: center;">CRITICAL: ${err.message}</td></tr>`;
        }
    }


    // ========================================================
    // 【功能三：特工提交研究報告】
    // ========================================================
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
                involved_members: membersStr ? membersStr.split(',').map(s => s.trim()) : []
            };

            if (lockdownOverlay) {
                lockdownOverlay.classList.add('active');
                const titleEl = lockdownOverlay.querySelector('.lockdown-title');
                const subEl = lockdownOverlay.querySelector('.lockdown-sub');
                if (titleEl) titleEl.textContent = "⚠️ CLASSIFIED DATA TRANSACTION IN PROGRESS";
                if (subEl) subEl.textContent = "AUTHORITY IDENTIFIED // COMMITTING...";
            }
            setButtonLoading(btnSubmitReport, true, "⚡ TRANSMITTING ENCRYPTED DATA...");

            try {
                const data = await requestAPI('/api/reports/upload', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(reportData)
                });
                
                if (responseLog) responseLog.textContent = `SUCCESS:\n${data.message}`;
                btnSubmitReport.textContent = "✔ INJECTION SUCCESS";
                alert(`[系統通知] ${data.message}`);
                
                setTimeout(() => setButtonLoading(btnSubmitReport, false, "", "EXECUTE MySQL DATA INJECTION"), 2000);
            } catch (err) {
                setButtonLoading(btnSubmitReport, false, "", "EXECUTE MySQL DATA INJECTION");
                if (responseLog) responseLog.textContent = `CRITICAL ERROR:\n${err.message}`;
                alert(err.message);
            } finally {
                if (lockdownOverlay) lockdownOverlay.classList.remove('active');
            }
        });
    }


    // ========================================================
    // 【功能四：🚨 站點收容與動態監控】
    // ========================================================
    async function fetchAndRenderSiteStatus() {
        if (!grid) return;
        try {
            const data = await requestAPI('/api/admin/sites');
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
                            <td style="padding: 10px; border-bottom: 1px solid #333;">${row.siteID}</td>
                            <td style="padding: 10px; border-bottom: 1px solid #333; font-weight: bold; color: #00bcd4;">${row.scpID ? `${row.scpID}` : '-'}</td>
                            <td style="padding: 10px; border-bottom: 1px solid #333; color: ${row.site_status == 1 ? '#00e676' : '#a0a0a0'};">${row.site_status == 1 ? 'INUSE' : 'IDL'}</td>
                            <td style="padding: 10px; border-bottom: 1px solid #333;">${row.door_status == 1 ? 'LOCK' : 'OPEN'}</td>
                            <td style="padding: 10px; border-bottom: 1px solid #333; color: ${row.structure === 'Broken' ? '#ff5252' : '#e0e0e0'};">${row.structure === 'Broken' ? 'BROKE' : 'FUNCT.'}</td>
                        </tr>
                    `;
                }).join('');

                const div = document.createElement('div');
                div.className = 'floor-block';
                div.style.marginBottom = '1.5rem';
                div.innerHTML = `
                    <div class="floor-title">FLOOR: ${floor}</div>
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
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
            grid.innerHTML = `<div class="loading-text" style="grid-column: span 2; color: #ff5252;">🚨 MONITOR CORRUPTED</div>`;
            if (errorMsg) errorMsg.textContent = `CRITICAL: ${err.message}`;
        }
    }


    // ========================================================
    // 【功能五：👥 基金會成員清單加載與核心去超連結】
    // ========================================================
    async function fetchAndRenderMembers() {
        if (!memberTableBody) return;
        try {
            const data = await requestAPI('/api/admin/members');
            if (memberSubtitle) memberSubtitle.textContent = `AUTHORIZED ACCESS: DEPLOYED OPERATIVES = ${data.length}`;
            memberTableBody.innerHTML = '';

            data.forEach(m => {
                const tr = document.createElement('tr');
                // 核心去超連結修正：直接輸出純文字 ${m.memID}，不再封裝 <a> 標籤
                tr.innerHTML = `
                    <td class="scp-id-col">${m.memID}</td>
                    <td>${m.dept_name || 'Unassigned'}</td>
                    <td class="center-text">LEVEL ${m.clearance_lv}</td>
                    <td>${m.permission || 'Class D'}</td>
                    <td id="status-${m.memID}" style="font-weight: bold; color: ${m.mem_status === 'normal' ? '#00e676' : '#ff5252'}">${m.mem_status}</td>
                    <td>
                        <select class="status-updater" data-id="${m.memID}">
                            <option value="">-- SELECT --</option>
                            <option value="normal">Normal</option>
                            <option value="abnormal">Abnormal</option>
                            <option value="treating">Treating</option>
                            <option value="dead">Dead</option>
                            <option value="suspended">Suspended</option>
                        </select>
                    </td>
                `;
                memberTableBody.appendChild(tr);
            });
        } catch (err) {
            memberTableBody.innerHTML = `<tr><td colspan="6" style="color:#ff5252; text-align:center;">${err.message}</td></tr>`;
        }
    }

    memberTableBody?.addEventListener('change', (e) => {
        if (e.target.classList.contains('status-updater')) {
            const targetId = e.target.getAttribute('data-id');
            const selectedStatus = e.target.value;
            if (selectedStatus) executeStatusPatch(targetId, selectedStatus, e.target);
        }
    });

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
            const data = await requestAPI(`/api/admin/members/${memID}/status`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mem_status: newStatus })
            });
            
            if (statusCell) {
                statusCell.textContent = newStatus;
                statusCell.style.color = newStatus === 'normal' ? '#00e676' : '#ff5252';
            }
            alert(`[狀態更新] ${data.message}`);
        } catch (err) {
            alert(`變更失敗: ${err.message}`);
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


    // ========================================================
    // 【功能六：🎭 新特工編制注入】
    // ========================================================
    if (btnSwitchToAdd && memberListSubview && memberAddSubview) {
        btnSwitchToAdd.addEventListener('click', () => {
            memberListSubview.style.display = 'none';
            memberAddSubview.style.display = 'block';
            if (addMemberLog) {
                addMemberLog.textContent = "SYSTEM IDLE. AWAITING INJECTION...";
                addMemberLog.style.color = "#e0e0e0";
            }
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
                if (addMemberLog) addMemberLog.textContent = "[X] ERROR: FIELDS REQUIRED.";
                return;
            }

            if (lockdownOverlay) lockdownOverlay.classList.add('active');
            setButtonLoading(btnExecuteAdd, true, "⚡ INJECTING...");

            try {
                const data = await requestAPI('/api/admin/members', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ dept_name, clearance_lv, permission, mem_status, password })
                });

                if (addMemberLog) {
                    addMemberLog.textContent = `🎉 SUCCESS! ID: ${data.memID}`;
                    addMemberLog.style.color = "#00e676";
                }
                alert(`[人員編制成功] 代號：${data.memID}`);
                
                setTimeout(() => {
                    if (memberAddSubview && memberListSubview) {
                        memberAddSubview.style.display = 'none';
                        memberListSubview.style.display = 'block';
                        fetchAndRenderMembers();
                    }
                }, 1000);
            } catch (err) {
                if (addMemberLog) {
                    addMemberLog.style.color = "#ff5252";
                    
                    if (err.message.includes('wrong clearance_lv') || err.message.includes('should be 0')) {
                        addMemberLog.textContent = "[X] INJECTION REFUSED: 操作不合法 (違反安保編制協議)。";
                        alert("操作不合法：此人員權限與職位編制不符，請修正後再試。");
                    } else {
                        addMemberLog.textContent = `[X] INJECTION REFUSED:\n${err.message}`;
                    }
                }
            } finally {
                setButtonLoading(btnExecuteAdd, false, "", "EXECUTE REGISTRY INJECTION");
                if (lockdownOverlay) lockdownOverlay.classList.remove('active');
            }
        });
    }


    // =========================================================================
    // 👑 【功能七：O5 審查決策核心】
    // =========================================================================
    async function fetchAndRenderO5ReportList() {
        if (!o5ListBody) return;
        try {
            const data = await requestAPI('/api/admin/reports');
            o5ListBody.innerHTML = '';

            if (data.length === 0) {
                o5ListBody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: #00e676; padding: 20px;">[CLEARED] 當前無待審查報告。</td></tr>`;
                return;
            }

            data.forEach(r => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="padding: 10px; border-bottom: 1px solid #333;">${r.reportID}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #333; color: #00bcd4;">${r.scpID}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #333;">${r.title}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #333; text-align: center;">
                        <button class="terminal-btn btn-go-review" data-payload='${JSON.stringify(r)}' style="padding: 3px 10px; margin: 0;">VIEW DETAILS</button>
                    </td>
                `;
                o5ListBody.appendChild(tr);
            });
        } catch (err) {
            o5ListBody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: #ff5252;">${err.message}</td></tr>`;
        }
    }

    o5ListBody?.addEventListener('click', (e) => {
        if (e.target.classList.contains('btn-go-review')) {
            const reportPayload = JSON.parse(e.target.getAttribute('data-payload'));
            openReviewWorkspace(reportPayload);
        }
    });

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

        if (o5ListSubview) o5ListSubview.style.display = 'none';
        if (o5DetailWorkspace) o5DetailWorkspace.style.display = 'block';

        try {
            const officialData = await requestAPI(`/api/scp/search?scpID=${report.scpID}`);
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

            const clearanceContainer = document.getElementById('view-official-clearance-container');
            if (clearanceContainer) {
                clearanceContainer.innerHTML = `
                    <select id="update-scp-clearance-lv" style="padding: 5px; background: #111; color: #00bcd4; border: 1px solid #333;">
                        <option value="0" ${currentLv === "0" ? "selected" : ""}>LEVEL 0</option>
                        <option value="1" ${currentLv === "1" ? "selected" : ""}>LEVEL 1</option>
                        <option value="2" ${currentLv === "2" ? "selected" : ""}>LEVEL 2</option>
                        <option value="3" ${currentLv === "3" ? "selected" : ""}>LEVEL 3</option>
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

    btnO5Save?.addEventListener('click', async () => {
        if (!activeReviewReportID) return;
        if (lockdownOverlay) lockdownOverlay.classList.add('active');
        setButtonLoading(btnO5Save, true, "⚡ MERGING PACKETS...");

        try {
            const data = await requestAPI('/api/O5/approve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    reportID: activeReviewReportID,
                    clearance_lv: document.getElementById('update-scp-clearance-lv')?.value || "0" 
                })
            });
            
            alert(`[審查完成] ${data.message}`);
            await fetchAndRenderO5ReportList();
            if (o5DetailWorkspace) o5DetailWorkspace.style.display = 'none';
            if (o5ListSubview) o5ListSubview.style.display = 'block';
            activeReviewReportID = null;
        } catch (err) {
            alert(`審查授權失敗: ${err.message}`);
        } finally {
            if (lockdownOverlay) lockdownOverlay.classList.remove('active');
            setButtonLoading(btnO5Save, false, "", "SAVE & MERGE (通過)");
        }
    });

    btnO5Reject?.addEventListener('click', async () => {
        if (!activeReviewReportID) return;
        if (!confirm('[WARNING] 確定要駁回並物理銷毀這篇研究報告嗎？此操作不可逆。')) return;
        
        if (lockdownOverlay) lockdownOverlay.classList.add('active');
        setButtonLoading(btnO5Reject, true, "🔥 ERASING LOGS...");

        try {
            const data = await requestAPI('/api/O5/reject', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reportID: activeReviewReportID })
            });
            
            alert(`[處置完畢] ${data.message}`);
            await fetchAndRenderO5ReportList();
            if (o5DetailWorkspace) o5DetailWorkspace.style.display = 'none';
            if (o5ListSubview) o5ListSubview.style.display = 'block';
            activeReviewReportID = null;
        } catch (err) {
            alert(`駁回執行失敗: ${err.message}`);
        } finally {
            if (lockdownOverlay) lockdownOverlay.classList.remove('active');
            setButtonLoading(btnO5Reject, false, "", "REJECT (駁回)");
        }
    });


    // ========================================================
    // 🎭 【功能八：用戶選單顯示與登出】
    // ========================================================
    userTrigger?.addEventListener('click', (e) => {
        e.stopPropagation(); 
        const isHidden = userMenu.style.display === 'none';
        userMenu.style.display = isHidden ? 'block' : 'none';
    });

    document.addEventListener('click', () => {
        if (userMenu) userMenu.style.display = 'none';
    });

    btnLogout?.addEventListener('click', async () => {
        try {
            await fetch('/api/logout', { method: 'POST', credentials: 'include' });
            alert("已解除安保連線。");
            window.location.href = "index.html";
        } catch (err) {
            console.error("登出失敗", err);
            window.location.href = "index.html"; 
        }
    });


    // =========================================================================
    // 🛡️ 2. 【安全網關自我校準 (執行起點)】
    // =========================================================================
    
    // 開機隔離：立刻激活暗色加載矩陣
    if (lockdownOverlay) {
        lockdownOverlay.classList.add('active');
        const titleEl = lockdownOverlay.querySelector('.lockdown-title');
        const subEl = lockdownOverlay.querySelector('.lockdown-sub');
        if (titleEl) titleEl.textContent = "📡 INITIALIZING SYSTEM SECURITY MATRIX";
        if (subEl) subEl.textContent = "SYNCHRONIZING WITH CENTRAL DATABASE // PLEASE HOLD...";
    }

    console.log("📡 [安保系統啟動] 正在向安全資料庫核對特工身分...");

    try {
        const response = await fetch('/api/user-profile', {
            method: 'GET',
            credentials: 'include' 
        });

        if (response.status === 401 || response.status === 403) {
            alert("ACCESS DENIED: 無效的安保憑證，請重新登入。");
            window.location.href = "index.html";
            return;
        }

        const agentData = await response.json();
        
        const clearanceLv = agentData.clearance_lv;
        const deptName = (agentData.dept_name || '').trim().toUpperCase();
        const permission = (agentData.permission || '').trim().toUpperCase();
        const memStatus = (agentData.mem_status || 'normal').trim().toLowerCase();

        console.log(`📡 [資料庫同步成功] 特工身分: ${deptName}_LV${clearanceLv}_${permission} // 精神指標: [${memStatus.toUpperCase()}]`);

        if (currentClearanceSpan) {
            currentClearanceSpan.innerText = `USER: ${deptName}_LV${clearanceLv}_${permission}`;
        }

        // 🩺 【精神異常硬阻斷系統】
        if (memStatus === 'abnormal') {
            console.error("☣️ [CRITICAL LOCKOUT] OPERATIVE STATUS IS ABNORMAL. TERMINAL BLOCK PROTOCOL ACTIVATED.");
            if (psychIndicator) {
                psychIndicator.classList.remove('status-green');
                psychIndicator.classList.add('status-red');
            }
            if (abnormalOverlay) {
                abnormalOverlay.style.display = 'flex';
                abnormalOverlay.classList.add('active');
            }
            if (lockdownOverlay) lockdownOverlay.classList.remove('active');
            return; 
        } else {
            console.log("🟢 [SECURITY AUDIT] SANITY CHECK PASSED. TERMINAL UNLOCKED.");
            if (psychIndicator) {
                psychIndicator.classList.remove('status-red');
                psychIndicator.classList.add('status-green');
            }
            if (abnormalOverlay) {
                abnormalOverlay.style.display = 'none';
                abnormalOverlay.classList.remove('active');
            }
        }

        // 🛡️ 人員管理按鈕控制矩陣
        if (btnSwitchToAdd) {
            if (deptName === 'O5' && parseInt(clearanceLv) >= 3) {
                btnSwitchToAdd.style.display = 'block'; 
            } else {
                btnSwitchToAdd.remove(); 
            }
        }

        // 核心模組開機初始化
        initializeTerminalHelpers();
        dispatchReportTab(deptName);
        
        // 核心同步柵欄：強迫系統在黑屏內載入完首頁數據
        await fetchAndRenderSCPs(); 

    } catch (error) {
        console.error('基金會內部網路連線錯誤:', error);
        alert('無法連線至中央安全資料庫，終端機即將強制鎖定。');
        if (abnormalOverlay) abnormalOverlay.style.display = 'flex';
        return; 
    } finally {
        // 完成全部渲染，解除隔離狀態
        if (lockdownOverlay) lockdownOverlay.classList.remove('active');
    }

});