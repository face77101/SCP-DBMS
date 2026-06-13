/**
 * =========================================================================
 * 🛡️ SCP FOUNDATION SYSTEM CONTROL INTERFACE (REFACTORED)
 * =========================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
    // 0. 身分驗證安保機制
    const clearanceLv = localStorage.getItem('clearance_lv');
    if (!clearanceLv) {
        alert("ACCESS DENIED: No clearance token found.");
        window.location.href = "index.html";
        return;
    }
    document.getElementById('current-clearance').innerText = `CLEARANCE: LEVEL ${clearanceLv}`;

    // ========================================================
    // 🎯 【核心共用工具函式庫 (Helpers)】
    // ========================================================
    
    // 🔌 統一 API 請求元件：自動引渡憑證與狀態碼攔截
    async function requestAPI(url, options = {}) {
        const defaultOptions = { credentials: 'include' };
        const response = await fetch(url, { ...defaultOptions, ...options });
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

    // ========================================================
    // 【功能一：🧭 Navbar 頁籤切換控制與全自動資料引渡】
    // ========================================================
    const navButtons = document.querySelectorAll('.nav-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    // 🗺️ 動態映射矩陣：當特定分頁被切換時，自動觸發對應的渲染函式
    const tabFetchRegistry = {
        'scp-view-section': () => fetchAndRenderSCPs(),
        'sites-section': () => fetchAndRenderSiteStatus(),
        'members-section': () => fetchAndRenderMembers()
    };

    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            navButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const targetId = btn.getAttribute('data-target');
            tabContents.forEach(content => {
                content.classList.toggle('active', content.id === targetId);
            });

            // 🔀 核心連動：如果切換的分頁有註冊在矩陣中，自動喚醒 Fetch
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

    // 啟動 SCP 模糊搜尋
    bindLocalSearch('scp-search', '#scp-table-body tr', ['no-data-text', 'error-text']);
    // 初始化首頁
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
                setTimeout(() => setButtonLoading(btnSubmitReport, false, "", "EXECUTE MySQL DATA INJECTION"), 2000);
            } catch (err) {
                setButtonLoading(btnSubmitReport, false, "", "EXECUTE MySQL DATA INJECTION");
                responseLog.textContent = err.message.includes('401') 
                    ? "401 UNAUTHORIZED: SESSION EXPIRED OR INVALID CREDENTIALS."
                    : "CRITICAL CONTAMINATION ERROR:\n" + err;
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

            // 樓層拆分分組
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
            memberErrorMsg.textContent = 'CRITICAL CORRUPTION: FAILED TO FETCH AGENT DIRECTORY. ' + err;
        }
    }

    async function executeStatusPatch(memID, newStatus, selectElement) {
        const statusCell = document.getElementById(`status-${memID}`);
        const originalText = statusCell ? statusCell.textContent : 'normal';
        const originalColor = statusCell ? statusCell.style.color : '#00e676';

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
                alert(`[SECURE COMPLIANCE] OPERATIVE ${memID} STATUS UPDATED TO: ${newStatus.toUpperCase()}`);
            }
        } catch (err) {
            alert('TRANSMISSION CONTAMINATION: ' + err.message);
            if (statusCell) {
                statusCell.textContent = originalText;
                statusCell.style.color = originalColor;
            }
        } finally {
            if (selectElement) {
                selectElement.value = ""; 
                selectElement.disabled = false;
            }
        }
    }

    // 啟動成員名單模糊搜尋
    bindLocalSearch('member-search', '#member-table-body tr');

    // ========================================================
    // 【功能六：🎭 子檢視區切換與新特工數據注入】
    // ========================================================
    const memberListSubview = document.getElementById('member-list-subview');
    const memberAddSubview  = document.getElementById('member-add-subview');
    const btnSwitchToAdd    = document.getElementById('btn-switch-to-add');
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
            }
        });
    }
});