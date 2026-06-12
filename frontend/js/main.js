document.addEventListener('DOMContentLoaded', () => {
    const clearanceLv = localStorage.getItem('clearance_lv');
    if (!clearanceLv) {
        alert("ACCESS DENIED: No clearance token found.");
        window.location.href = "index.html";
        return;
    }

    document.getElementById('current-clearance').innerText = `CLEARANCE: LEVEL ${clearanceLv}`;

    // ========================================================
    // 【功能一：🧭 Navbar 頁籤切換控制邏輯】
    // ========================================================
    const navButtons = document.querySelectorAll('.nav-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            navButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const targetId = btn.getAttribute('data-target');
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === targetId) {
                    content.classList.add('active');
                }
            });
        });
    });

    // ========================================================
    // 【功能二：SCP 列表動態渲染與搜尋】(加入安全防卡死鎖)
    // ========================================================
    const searchInput = document.getElementById('scp-search');
    const btnSubmitReport = document.getElementById('btn-submit-report');
    const tableBody = document.getElementById('scp-table-body');
    
    // 🔒 宣告一個全域控制器，用來取消上一次還沒跑完的 Fetch
    let currentAbortController = null;

    async function fetchAndRenderSCPs(keyword = '') {
        const currentClearance = localStorage.getItem('clearance_lv') || '0'; 

        // 1. 🛑 【核心優化：中斷先前的請求】如果上一次的搜尋還在跑，直接把它捏碎，防止疊加當機
        if (currentAbortController) {
            currentAbortController.abort();
        }
        // 建立本輪請求的專屬控制器
        currentAbortController = new AbortController();
        const { signal } = currentAbortController;

        // 2. 👁️‍🗨️ 【視覺反饋】立刻清空表格，並塞入高對比的禁止/掃描中提示
        tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="loading-text" style="color: #ffc107; font-weight: bold; text-align: center; padding: 20px; background: rgba(0,0,0,0.5);">
                    📡 [SYSTEM] ENGAGING DATABASE SCAN FOR LEVEL ${currentClearance}... PLEASE HOLD
                </td>
            </tr>
        `;

        try {
            const url = `http://localhost:5000/api/scp/search?clearance_lv=${currentClearance}&scpID=${encodeURIComponent(keyword)}`;
            
            // 將 signal 餵給 fetch
            const response = await fetch(url, { 
                method: 'GET',
                credentials: 'include',
                signal: signal 
            });

            const result = await response.json();

            if (!response.ok) {
                tableBody.innerHTML = `<tr><td colspan="8" class="error-text">ERROR: ${result.message}</td></tr>`;
                return;
            }

            // 3. 渲染新數據
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
            // 如果是被我們主動 abort 的，不需要噴錯，靜悄悄跳過即可
            if (error.name === 'AbortError') {
                return; 
            }
            console.error('Fetch Error:', error);
            tableBody.innerHTML = `<tr><td colspan="8" class="error-text" style="color: #ff3333; font-weight: bold; text-align: center;">CRITICAL: FAILED TO COMMUNICATE WITH DATABASE</td></tr>`;
        }
    }

    // ========================================================
    // 🧠 【極速優化】將 SCP 搜尋改為純前端本地 DOM 過濾！
    // ========================================================
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const keyword = e.target.value.toLowerCase().trim();
            
            // 抓取表格中目前所有的 SCP 資料列
            document.querySelectorAll('#scp-table-body tr').forEach(row => {
                // 如果這行不是無資料提示，且文字包含關鍵字，就顯示，否則隱藏
                if (!row.classList.contains('no-data-text') && !row.classList.contains('error-text')) {
                    row.style.display = row.textContent.toLowerCase().includes(keyword) ? '' : 'none';
                }
            });
        });
    }

    // 初始化讀取：開網頁時「只打一次」API 撈完所有允許查閱的 SCP
    fetchAndRenderSCPs();

    // ========================================================
    // 【功能三：接管組員的 Report 提交邏輯】
    // ========================================================
    if (btnSubmitReport) {
        btnSubmitReport.addEventListener('click', () => {
            const membersStr = document.getElementById('involvedMembers').value;
            const membersArray = membersStr ? membersStr.split(',').map(s => s.trim()) : [];

            const reportData = {
                title: document.getElementById('title').value,
                scpID: document.getElementById('scpID').value,
                abilities: document.getElementById('abilities').value,
                weakness: document.getElementById('weakness').value,
                appearance: document.getElementById('appearance').value,
                others: document.getElementById('others').value,
                involved_members: membersArray,
                required_lv: "1"
            };

            // 🔒 【啟用安保鎖】按鈕變暗、滑鼠變圓圈
            btnSubmitReport.disabled = true;
            btnSubmitReport.textContent = "⚡ TRANSMITTING ENCRYPTED DATA...";
            responseLog.textContent = "TRANSMITTING ENCRYPTED DATA PACKET TO BACKEND...";

            fetch('http://localhost:5000/api/reports/upload', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(reportData),
                credentials: 'include'
            })
            .then(res => {
                if (res.status === 401) {
                    responseLog.textContent = "401 UNAUTHORIZED: SESSION EXPIRED OR INVALID CREDENTIALS.";
                    throw new Error("401");
                }
                return res.json();
            })
            .then(data => {
                responseLog.textContent = "SUCCESSFULLY WRITTEN TO MYSQL DATABASE!\n\nRESPONSE:\n" + JSON.stringify(data, null, 2);
                btnSubmitReport.textContent = "✔ INJECTION SUCCESS";
                // 成功後，過 2 秒復原按鈕（如果不希望它永久鎖死）
                setTimeout(() => {
                    btnSubmitReport.disabled = false;
                    btnSubmitReport.textContent = "EXECUTE MySQL DATA INJECTION";
                }, 2000);
            })
            .catch(err => {
                // 🔓 【例外釋放】如果失敗了，解除鎖定，讓特工可以修改再試一次
                btnSubmitReport.disabled = false;
                btnSubmitReport.textContent = "EXECUTE MySQL DATA INJECTION";
                if (err.message !== "401") {
                    responseLog.textContent = "CRITICAL CONTAMINATION ERROR:\n" + err;
                }
            });
        });
    }

    // ========================================================
    // 【功能四：🚨 站點收容與結構動態監控】
    // ========================================================
    async function fetchAndRenderSiteStatus() {
        const grid = document.getElementById('site-grid');
        const errorMsg = document.getElementById('site-error-msg');
        
        if (!grid) return; // 防呆：如果不在對應頁面就跳出

        try {
            // 🔌 修正一：精準打向 Port 5000，並開啟憑證引渡 Session
            const response = await fetch('http://localhost:5000/api/admin/sites', {
                method: 'GET',
                credentials: 'include' 
            });

            if (!response.ok) {
                throw new Error(`HTTP 錯誤！狀態碼: ${response.status}`);
            }

            const data = await response.json();
            
            // 樓層分組邏輯 (保持原樣)
            const floors = {};
            data.forEach(row => {
                const floor = row.siteID.split('-')[0];
                if (!floors[floor]) floors[floor] = [];
                floors[floor].push(row);
            });

            grid.innerHTML = ''; // 清空舊畫面
            const floorKeys = Object.keys(floors).sort();

            floorKeys.forEach(floor => {
                const rows = floors[floor];
                const isBroken = row => row.door_status == 1 && row.structure === 'Broken';

                const tbody = rows.map(row => `
                    <tr class="${isBroken(row) ? 'broken' : ''}" style="${isBroken(row) ? 'background: #7a1a1a;' : ''}">
                        <td>${row.siteID}</td>
                        <td>${row.scpID ?? '-'}</td>
                        <td class="${row.site_status == 1 ? 'status-inuse' : 'status-idl'}" style="color: ${row.site_status == 1 ? '#00e676' : '#e0e0e0'}; font-weight: ${row.site_status == 1 ? '500' : 'normal'};">
                            ${row.site_status == 1 ? 'INUSE' : 'IDL'}
                        </td>
                        <td>${row.door_status == 1 ? 'LOCK' : 'OPEN'}</td>
                        <td class="${row.structure === 'Broken' ? 'struct-broke' : 'struct-funct'}" style="color: ${row.structure === 'Broken' ? '#ff5252' : '#e0e0e0'}; font-weight: ${row.structure === 'Broken' ? '500' : 'normal'};">
                            ${row.structure === 'Broken' ? 'BROKE' : 'FUNCT.'}
                        </td>
                    </tr>
                `).join('');

                const table = `
                    <div class="floor-block" style="background: #222; padding: 1rem; border-radius: 4px; border: 1px solid #333;">
                        <h3 style="margin-bottom: 0.5rem; color: #00bcd4;">FLOOR: ${floor}</h3>
                        <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                            <thead>
                                <tr style="background: #00bcd4; color: #1a1a1a;">
                                    <th style="padding: 8px;">SITE_ID</th>
                                    <th style="padding: 8px;">SCP_ID</th>
                                    <th style="padding: 8px;">STAT.</th>
                                    <th style="padding: 8px;">DOOR STAT.</th>
                                    <th style="padding: 8px;">STRUCT.</th>
                                </tr>
                            </thead>
                            <tbody>${tbody}</tbody>
                        </table>
                    </div>
                `;
                grid.innerHTML += table;
            });
        } catch (err) {
            errorMsg.textContent = '站點監控數據載入失敗：' + err;
        }
    }

    // ========================================================
    // 【功能五：👥 基金會成員清單加載與精神狀態校準 (PATCH)】
    // ========================================================
    const memberTableBody = document.getElementById('member-table-body');
    const memberSubtitle = document.getElementById('member-subtitle');
    const memberSearchInput = document.getElementById('member-search');
    const memberErrorMsg = document.getElementById('member-error-msg');

    async function fetchAndRenderMembers() {
        if (!memberTableBody) return;

        try {
            const response = await fetch('http://localhost:5000/api/admin/members', {
                method: 'GET',
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error(`HTTP AUTHENTICATION ERROR: ${response.status}`);
            }

            const data = await response.json();
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

            // 🧠 偵聽選單變更，並將 select 元素本體 (e.target) 當作第三個參數送進去
            document.querySelectorAll('.status-updater').forEach(selectElement => {
                selectElement.addEventListener('change', (e) => {
                    const targetId = e.target.getAttribute('data-id');
                    const selectedStatus = e.target.value;
                    if (selectedStatus) {
                        executeStatusPatch(targetId, selectedStatus, e.target); 
                    }
                });
            });

        } catch (err) {
            memberErrorMsg.textContent = 'CRITICAL CORRUPTION: FAILED TO FETCH AGENT DIRECTORY. ' + err;
        }
    }

    // ⚡ 【全新優化版】發送 PATCH 請求並執行狀態鎖定
    async function executeStatusPatch(memID, newStatus, selectElement) {
        const statusCell = document.getElementById(`status-${memID}`);
        
        // 備份原始狀態，若後端寫入失敗時可以用來復原
        const originalText = statusCell ? statusCell.textContent : 'normal';
        const originalColor = statusCell ? statusCell.style.color : '#00e676';

        // 🔒 [1/3 狀態鎖定]：強制禁用選單防止連打，並在表格內打出正在處理的黃色視覺反饋
        if (selectElement) selectElement.disabled = true;
        if (statusCell) {
            statusCell.textContent = "⏳ CALIBRATING...";
            statusCell.style.color = "#ffc107"; 
        }

        try {
            const response = await fetch(`http://localhost:5000/api/admin/members/${memID}/status`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mem_status: newStatus }),
                credentials: 'include'
            });

            const data = await response.json();
            
            if (response.ok && data.message) {
                // 🎉 [2/3 更新成功]：將表格內部的文字與顏色真正切換
                if (statusCell) {
                    statusCell.textContent = newStatus;
                    statusCell.style.color = newStatus === 'normal' ? '#00e676' : '#ff5252';
                }
                alert(`[SECURE COMPLIANCE] OPERATIVE ${memID} STATUS UPDATED TO: ${newStatus.toUpperCase()}`);
            } else {
                alert('CALIBRATION FAILED: ' + (data.error || 'Access Denied'));
                if (statusCell) {
                    statusCell.textContent = originalText;
                    statusCell.style.color = originalColor;
                }
            }
        } catch (err) {
            alert('TRANSMISSION CONTAMINATION: ' + err);
            if (statusCell) {
                statusCell.textContent = originalText;
                statusCell.style.color = originalColor;
            }
        } finally {
            // 🔄 [3/3 釋放與歸位]：不管成功或失敗，無條件執行解除鎖定，並把選單洗回預設的 "-- SELECT --"
            if (selectElement) {
                selectElement.value = "";     // 👈 強制跳回第一個預設選項
                selectElement.disabled = false; // 👈 重新開放操作
            }
        }
    }

    // 成員名單本地即時模糊搜尋 (保持原樣)
    if (memberSearchInput) {
        memberSearchInput.addEventListener('input', (e) => {
            const keyword = e.target.value.toLowerCase();
            document.querySelectorAll('#member-table-body tr').forEach(row => {
                row.style.display = row.textContent.toLowerCase().includes(keyword) ? '' : 'none';
            });
        });
    }

    // 初始化成員名單
    fetchAndRenderMembers();

    // ========================================================
    // 【功能六：🎭 子檢視區切換與全新特工數據注入 (POST)】
    // ========================================================
    const memberListSubview = document.getElementById('member-list-subview');
    const memberAddSubview  = document.getElementById('member-add-subview');
    const btnSwitchToAdd    = document.getElementById('btn-switch-to-add');
    const btnCancelAdd      = document.getElementById('btn-cancel-add');
    const btnExecuteAdd     = document.getElementById('btn-execute-add');
    const addMemberLog      = document.getElementById('add-member-log');

    // 1. 本地子畫面切換
    if (btnSwitchToAdd && memberListSubview && memberAddSubview) {
        btnSwitchToAdd.addEventListener('click', () => {
            memberListSubview.style.display = 'none';
            memberAddSubview.style.display = 'block';
            addMemberLog.textContent = "SYSTEM IDLE. AWAITING INJECTION OPERATION...";
            addMemberLog.style.color = "#e0e0e0";
            
            // 🔄 每次打開表單，確保按鈕狀態是重置好的
            if (btnExecuteAdd) {
                btnExecuteAdd.disabled = false;
                btnExecuteAdd.textContent = "EXECUTE REGISTRY INJECTION";
            }
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

    // 2. ⚡ 【全動態鎖優化版】表單提交安全注入連線
    if (btnExecuteAdd) {
        btnExecuteAdd.addEventListener('click', async () => {
            const dept_name    = document.getElementById('add-dept-name').value.trim();
            const clearance_lv = document.getElementById('add-clearance-lv').value;
            const permission   = document.getElementById('add-permission').value;
            const mem_status   = document.getElementById('add-mem-status').value;
            const password     = document.getElementById('add-password').value;

            // 欄位防呆驗證
            if (!dept_name || !password) {
                addMemberLog.textContent = "[X] INJECTION CRITICAL ERROR:\nDEPARTMENT ACRONYM AND PASSWORD CANNOT BE VACANT.";
                addMemberLog.style.color = "#ff5252";
                return;
            }

            // 🔒 【第一階段：觸發安保鎖】
            btnExecuteAdd.disabled = true;                          // 👈 物理禁用「新增」按鈕，防止連打
            if (btnCancelAdd) btnCancelAdd.disabled = true;         // 👈 同步禁用「取消」按鈕，防止中途切換網頁斷線
            btnExecuteAdd.textContent = "⚡ INJECTING DATASTREAM..."; // 👈 改變按鈕文字，給予強烈的載入反饋
            
            addMemberLog.textContent = "⚙️ INITIALIZING DATABASE INJECTION PROTOCOL...";
            addMemberLog.style.color = "#ffc107";

            try {
                const response = await fetch('http://localhost:5000/api/admin/members', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ dept_name, clearance_lv, permission, mem_status, password }),
                    credentials: 'include' 
                });

                const data = await response.json();

                if (response.ok && data.message) {
                    // 🎉 【狀況 A：寫入成功】
                    addMemberLog.textContent = `🎉 SUCCESSFULLY INJECTED TO MYSQL DATABASE!\n\nGENERATED REGISTRY ID: ${data.memID}\nSTATUS: ${data.message.toUpperCase()}`;
                    addMemberLog.style.color = "#00e676";
                    btnExecuteAdd.textContent = "✔ INJECTION COMPLETED"; // 👈 成功視覺提示
                    
                    // 清空欄位
                    document.getElementById('add-dept-name').value = '';
                    document.getElementById('add-password').value = '';
                    
                    // 保持按鈕鎖定狀態，2 秒後自動優雅地彈回特工名單
                    setTimeout(() => {
                        if (memberAddSubview && memberListSubview) {
                            memberAddSubview.style.display = 'none';
                            memberListSubview.style.display = 'block';
                            fetchAndRenderMembers(); // 強刷新名單
                        }
                    }, 2000);

                } else {
                    // ❌ 【狀況 B：後端拒絕（如欄位衝突）】
                    addMemberLog.textContent = `[X] INJECTION REFUSED:\n${data.error || 'Access Denied by Server.'}`;
                    addMemberLog.style.color = "#ff5252";
                    
                    // 🔓 注入失敗，立刻釋放按鈕鎖，讓特工可以當場修正表單
                    btnExecuteAdd.disabled = false;
                    if (btnCancelAdd) btnCancelAdd.disabled = false;
                    btnExecuteAdd.textContent = "EXECUTE REGISTRY INJECTION";
                }

            } catch (err) {
                // 💥 【狀況 C：網路物理崩潰】
                addMemberLog.textContent = `[🔥 TERMINAL CRITICAL ERROR]:\n${err}`;
                addMemberLog.style.color = "#ff5252";
                
                // 🔓 釋放按鈕鎖
                btnExecuteAdd.disabled = false;
                if (btnCancelAdd) btnCancelAdd.disabled = false;
                btnExecuteAdd.textContent = "EXECUTE REGISTRY INJECTION";
            }
        });
    }

});