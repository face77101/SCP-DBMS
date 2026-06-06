document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const loginCard = document.querySelector('.login-card');

    loginForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const username = usernameInput.value.trim();
        const password = passwordInput.value;

        // ========================================================
        // 【核心優化 1：進入鎖定狀態，防止重複輸入與點擊】
        // ========================================================
        usernameInput.disabled = true;
        passwordInput.disabled = true;
        document.body.style.cursor = 'wait'; // 讓滑鼠游標變成漏斗/轉圈狀態
        loginCard.style.opacity = '0.7';     // 讓卡片微微變暗，提示正在通訊中
        
        // 可選：在畫面上動態加入一個小小的終端機提示字眼
        let statusNotice = document.createElement('p');
        statusNotice.id = 'status-notice';
        statusNotice.innerText = 'CONNECTING TO SERVER...';
        statusNotice.style.color = '#7c1a1a';
        statusNotice.style.marginTop = '15px';
        statusNotice.style.fontSize = '12px';
        loginForm.appendChild(statusNotice);

        try {
            const response = await fetch('http://localhost:5000/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (response.ok) {
                // 【狀況 A：登入成功】
                statusNotice.innerText = 'ACCESS GRANTED. REDIRECTING...';
                statusNotice.style.color = '#00ff00'; // 變綠色
                
                localStorage.setItem('clearance_lv', data.clearance_lv);
                
                // 延遲 1 秒再跳轉，讓特工看得到「成功放行」的科幻爽感
                setTimeout(() => {
                    window.location.href = data.redirect;
                }, 1000);

            } else {
                // 【狀況 B：驗證失敗】
                alert(data.message);
                // 失敗了，解除鎖定，讓使用者可以重新輸入
                unlockForm();
            }

        } catch (error) {
            // 【狀況 C：伺服器斷聯】
            console.error('基金會連線錯誤:', error);
            alert('無法連線至基金會安全伺服器，請檢查網路或 Docker 狀態。');
            unlockForm();
        }

        // ========================================================
        // 【核心優化 2：解除鎖定的 Helper Function】
        // ========================================================
        function unlockForm() {
            usernameInput.disabled = false;
            passwordInput.disabled = false;
            document.body.style.cursor = 'default';
            loginCard.style.opacity = '1';
            if (statusNotice) statusNotice.remove(); // 移除提示字
            
            // 自動清空密碼欄位，並把焦點留給密碼，方便直接重新輸入
            passwordInput.value = '';
            passwordInput.focus();
        }
    });
});