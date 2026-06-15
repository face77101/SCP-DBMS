// 當整個 HTML 網頁的結構（DOM）全部載入完成後，才開始執行裡面的 JavaScript
// 這樣可以確保後面用 getElementById 找畫面元件時，不會因為元件還沒長出來而報錯
document.addEventListener('DOMContentLoaded', () => {
    
    // 【選取畫面元件】從 HTML 中把表單、輸入框、卡片等元素抓出來，存進變數裡
    const loginForm = document.getElementById('login-form');     // 登入表單整體
    const usernameInput = document.getElementById('username');   // 帳號輸入框
    const passwordInput = document.getElementById('password');   // 密碼輸入框
    const loginCard = document.querySelector('.login-card');     // 登入卡片的容器

    // 【優化：預先建立提示標籤】在記憶體中先建立好一個 <p> 標籤，用來顯示「連線中」或「登入成功」
    // 這樣做可以避免每次點擊按鈕都重複創立新的標籤，造成畫面混亂
    const statusNotice = document.createElement('p');
    statusNotice.id = 'status-notice';        // 為這個標籤設定 ID
    statusNotice.style.marginTop = '15px';     // 設定外邊距，讓它跟上方保持距離
    statusNotice.style.fontSize = '12px';      // 設定字體大小

    // 【監聽提交事件】當使用者按下登入按鈕，或者在輸入框按 Enter 送出表單時，觸發此 function
    // 使用 async 是因為裡面會用到 await 來等待伺服器（非同步）的回傳結果
    loginForm.addEventListener('submit', async (event) => {
        
        // 阻止表單的預設行為（因為傳統表單送出會導致整個網頁重新整理重新載入，我們要用 AJAX 處理）
        event.preventDefault();

        // 讀取使用者輸入的帳號與密碼
        // .trim() 負責自動刪除帳號前後不小心按到的「空白鍵」，避免使用者輸入錯誤
        const username = usernameInput.value.trim();
        const password = passwordInput.value;

        // 【前端基本防禦】檢查使用者是不是根本沒輸入就按送出
        // 如果帳號或密碼是空的，直接跳出警告並利用 return 終止程式，不浪費網路資源去發送請求
        if (!username || !password) {
            alert('欄位不可為空');
            return; 
        }

        // 【執行鎖定】呼叫下方定義好的 lockForm()，把輸入框鎖住，防止使用者在等待時重複狂點按鈕
        lockForm();

        // 【嘗試與伺服器通訊】使用 try...catch 結構，包裹可能因為網路斷線而失敗的程式碼
        try {
            // 使用 fetch 發送網路請求到後端的網址 '/api/login'，並等待（await）其回應
            const response = await fetch('/api/login', {
                method: 'POST', // 使用 POST 方法，將敏感的帳號密碼放在「請求主體（Body）」中傳輸，不放在網址列
                headers: { 
                    'Content-Type': 'application/json', // 告訴後端伺服器，我們傳過去的資料格式是 JSON 字串
                },
                // 將 JavaScript 的物件 { username, password } 轉成 JSON 字串格式，才能在網路傳輸
                body: JSON.stringify({ username, password }), 
                // credentials: 'include' 允許瀏覽器在通訊時攜帶安全憑證（如 Cookie）
                // 這對於後端設定 HttpOnly Cookie 建立安全登入狀態至關重要
                credentials: 'include' 
            });

            // 等待伺服器將回傳的原始資料解析成 JavaScript 可以讀取的 JSON 物件
            const data = await response.json();

            // response.ok 代表後端回傳的 HTTP 狀態碼在 200~299 之間（代表後端認證成功）
            if (response.ok) {
                
                // 【狀態 A：登入成功】
                statusNotice.innerText = 'ACCESS GRANTED. REDIRECTING...'; // 更改提示文字
                statusNotice.style.color = '#00ff00';                      // 將文字顏色改成綠色

                // 【🚨 安全大改造：捨棄 localStorage】
                // 絕對不要把 clearance_lv (權限等級) 存進 localStorage！
                // 實務上：後端在上面的 response 中，已經偷偷把「加密且無法用 JS 讀取的 Session/JWT Token」寫進瀏覽器的 Cookie 了。
                // 前端（這裡）只需要紀錄純顯示用的資訊就好，例如把當前特工代號存入 sessionStorage（分頁關閉就會自動消失）
                sessionStorage.setItem('current_agent', username); 

                // 刻意延遲 1 秒鐘（1000 毫秒）再執行網頁跳轉，讓使用者看得到成功的提示動畫
                setTimeout(() => {
                    // 優先使用後端回傳建議的跳轉網址（data.redirect），若無則預設跳到主儀表板（/dashboard）
                    window.location.href = data.redirect || '/dashboard';
                }, 1000);

            } else {
                // 【狀態 B：驗證失敗】（例如密碼打錯，後端回傳 401 或 403 錯誤碼）
                // 🔒【安全細節】：不直接用後端的 data.message，因為可能暴露伺服器內部錯誤（如 SQL 錯誤）
                // 如果狀態碼是 401，顯示統一的模糊提示，這能防止駭客透過錯誤訊息來測試（列舉）哪些帳號是真實存在的
                alert(response.status === 401 ? '認證失敗：代號或密碼錯誤。' : '系統異常，請稍後再試。');
                
                // 認證失敗，呼叫解除鎖定函式，讓使用者可以重新輸入
                unlockForm();
            }

        } catch (error) {
            // 【狀態 C：連線異常】（例如伺服器掛了、Docker 沒開、使用者沒網路）
            // catch 會抓到 fetch 噴出的網路錯誤
            console.error('Security Network Error:', error); // 在開發者工具的 Console 印出詳細錯誤，方便工程師排查
            alert('無法連接至安全伺服器，請檢查網路或系統狀態。'); // 對使用者顯示友好的提示
            
            // 連線失敗，同樣解除鎖定，允許重新嘗試
            unlockForm();
        }
    });

    // ========================================================
    // 【Helper Function 1：鎖定表單的工具】
    // ========================================================
    function lockForm() {
        usernameInput.disabled = true;           // 禁用帳號輸入框
        passwordInput.disabled = true;           // 禁用密碼輸入框
        document.body.style.cursor = 'wait';     // 將全網頁的滑鼠游標變成「漏斗/旋轉等待」狀態
        loginCard.style.opacity = '0.7';         // 讓登入卡片變透明度 0.7（微微變暗），提示正在通訊中
        
        statusNotice.innerText = 'CONNECTING TO SERVER...'; // 設定提示文字為連線中
        statusNotice.style.color = '#7c1a1a';               // 設定為暗紅色
        loginForm.appendChild(statusNotice);                 // 把這個提示標籤，塞進表單的最後面顯示出來
    }

    // ========================================================
    // 【Helper Function 2：解除鎖定的工具】
    // ========================================================
    function unlockForm() {
        usernameInput.disabled = false;          // 重新啟用帳號輸入框
        passwordInput.disabled = false;          // 重新啟用密碼輸入框
        document.body.style.cursor = 'default';  // 還原滑鼠游標為一般箭頭
        loginCard.style.opacity = '1';           // 還原卡片亮度
        statusNotice.remove();                   // 把畫面上的「提示標籤」整行拔掉、移除
        
        passwordInput.value = '';                // 💡 基於安全與貼心，把輸入錯的密碼欄位清空
        passwordInput.focus();                   // 自動把輸入游標聚焦到密碼框，方便使用者直接重新輸入
    }
});