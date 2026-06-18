// auth.js

// Hàm lấy token an toàn
export function getToken() {
    return localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
}

// Hàm kiểm tra và đá về login nếu không có token
export function checkAuthOrRedirect() {
    const token = getToken();
    if (!token) {
        window.location.href = '/login';
        return null;
    }
    return token;
}

// Hàm fetch đính kèm token
export async function fetchWithAuth(url, options = {}) {
    const currentToken = getToken();
    options.headers = {
        ...options.headers,
        'Authorization': `Bearer ${currentToken}`
    };
    const response = await fetch(url, options);
    if (response.status === 401) {
        localStorage.removeItem('access_token');
        sessionStorage.removeItem('access_token');
        window.location.href = "/login";
    }
    return response;
}

// Hàm logout dùng chung
export async function handleLogout() {
    try {
        await fetchWithAuth('/api/v1/logout', { method: 'POST' });
    } catch (err) {
        console.error("Lỗi gọi API logout:", err);
    } finally {
        localStorage.removeItem('access_token');
        sessionStorage.removeItem('access_token');
        window.location.href = "/login";
    }
}