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

    // 4.🧠 偵聽輸入行為（使用者一打字，立刻啟動防禦機制）
    searchInput.addEventListener('input', (e) => fetchAndRenderSCPs(e.target.value.trim()));
    fetchAndRenderSCPs(); // 初始化讀取

    // ========================================================
    // 【功能三：接管組員的 Report 提交邏輯】
    // ========================================================
    const btnSubmitReport = document.getElementById('btn-submit-report');
    const responseLog = document.getElementById('responseLog');

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
            })
            .catch(err => {
                if (err.message !== "401") {
                    responseLog.textContent = "CRITICAL CONTAMINATION ERROR:\n" + err;
                }
            });
        });
    }
});