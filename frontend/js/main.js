document.addEventListener('DOMContentLoaded', () => {
    // 1. 從快取中翻出登入成功時儲存的權限等級
    const clearanceLv = localStorage.getItem('clearance_lv');
    
    // 安全防線：如果口袋裡沒有權限標籤，代表是偷渡者，強制踢回登入頁
    if (!clearanceLv) {
        alert("ACCESS DENIED: No clearance token found.");
        window.location.href = "index.html";
        return;
    }

    // 在頂部顯示目前的權限等級
    document.getElementById('current-clearance').innerText = `CLEARANCE: LEVEL ${clearanceLv}`;

    const searchInput = document.getElementById('scp-search');
    const tableBody = document.getElementById('scp-table-body');

    // ========================================================
    // 【核心函數】向後端 API 請求資料並渲染表格
    // ========================================================
    async function fetchAndRenderSCPs(keyword = '') {
        try {
            // 後端同學寫好的 API，我們要把權限與關鍵字作為 Query Parameters 帶過去
            // 例如: http://localhost:5000/api/scps?clearance_lv=2&search=682
            const url = `http://localhost:5000/api/scps?clearance_lv=${clearanceLv}&search=${encodeURIComponent(keyword)}`;
            
            const response = await fetch(url, { method: 'GET' });
            const result = await response.json();

            if (!response.ok) {
                tableBody.innerHTML = `<tr><td colspan="8" class="error-text">ERROR: ${result.message}</td></tr>`;
                return;
            }

            // 清空舊的表格列
            tableBody.innerHTML = '';

            if (result.length === 0) {
                tableBody.innerHTML = `<tr><td colspan="8" class="no-data-text">NO REGISTRIES FOUND WITHIN LEVEL ${clearanceLv}</td></tr>`;
                return;
            }

            // 遍歷所有 SCP 對象，組裝成 HTML 標籤
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
            console.error('Fetch Error:', error);
            tableBody.innerHTML = `<tr><td colspan="8" class="error-text">CRITICAL: FAILED TO COMMUNICATE WITH SECURE DATABASE</td></tr>`;
        }
    }

    // ========================================================
    // 【事件監聽】打字時即時動態搜尋（免點按鈕）
    // ========================================================
    searchInput.addEventListener('input', (e) => {
        const keyword = e.target.value.trim();
        fetchAndRenderSCPs(keyword);
    });

    // 初始化頁面：一進網頁自動載入所有可看資料
    fetchAndRenderSCPs();
});