import axios from 'axios';

/**
 * Axios 全局配置
 * - 支持 Django SessionAuthentication
 * - 自動處理 CSRF token
 * - 發送 credentials (cookies)
 */

// 配置 axios 全局設置
axios.defaults.withCredentials = true;  // 重要：發送 cookies (session)
axios.defaults.xsrfCookieName = 'csrftoken';  // Django CSRF cookie 名稱
axios.defaults.xsrfHeaderName = 'X-CSRFToken';  // Django CSRF header 名稱

/**
 * 從 cookie 中獲取 CSRF token
 * @param {string} name - cookie 名稱
 * @returns {string|null} - cookie 值
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// 請求攔截器：自動添加 CSRF token
axios.interceptors.request.use(
    (config) => {
        // 對於非 GET 請求，添加 CSRF token
        if (config.method !== 'get') {
            const csrfToken = getCookie('csrftoken');
            if (csrfToken) {
                config.headers['X-CSRFToken'] = csrfToken;
            }
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// 響應攔截器：處理認證錯誤
axios.interceptors.response.use(
    (response) => {
        return response;
    },
    (error) => {
        // 401 或 403 錯誤：可能是未登入或 session 過期
        if (error.response?.status === 401 || error.response?.status === 403) {
            console.warn('Authentication error:', error.response?.status);
            // 可以在這裡添加自動跳轉到登入頁面的邏輯
        }
        return Promise.reject(error);
    }
);

export default axios;
