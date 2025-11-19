import React, { createContext, useState, useContext, useEffect } from 'react';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // 從 localStorage 獲取用戶資訊
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
            try {
                const parsedUser = JSON.parse(storedUser);
                setUser(parsedUser);
                setIsAuthenticated(true);
            } catch (error) {
                console.error('Failed to parse stored user:', error);
                localStorage.removeItem('user');
                setUser(null);
                setIsAuthenticated(false);
            }
        } else {
            // 未登入用戶必須先登入
            setUser(null);
            setIsAuthenticated(false);
        }
        setLoading(false);
    }, []);

    const login = async (credentials) => {
        try {
            // 獲取 CSRF token
            const getCsrfToken = () => {
                const name = 'csrftoken';
                const cookies = document.cookie.split(';');
                for (let cookie of cookies) {
                    const trimmed = cookie.trim();
                    if (trimmed.startsWith(name + '=')) {
                        return trimmed.substring(name.length + 1);
                    }
                }
                return null;
            };

            const csrfToken = getCsrfToken();
            
            const response = await fetch('/api/users/login/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(csrfToken && { 'X-CSRFToken': csrfToken }),
                },
                credentials: 'include',  // 重要：包含 cookies
                body: JSON.stringify(credentials),
            });

            const data = await response.json();

            if (!response.ok) {
                return { 
                    success: false, 
                    message: data.error || '登入失敗' 
                };
            }

            const user = data.user;
            setUser(user);
            setIsAuthenticated(true);
            localStorage.setItem('user', JSON.stringify(user));
            return { success: true };
        } catch (error) {
            console.error('Login error:', error);
            return { 
                success: false, 
                message: '連接伺服器失敗' 
            };
        }
    };

    const register = async (userData) => {
        try {
            // 獲取 CSRF token
            const getCsrfToken = () => {
                const name = 'csrftoken';
                const cookies = document.cookie.split(';');
                for (let cookie of cookies) {
                    const trimmed = cookie.trim();
                    if (trimmed.startsWith(name + '=')) {
                        return trimmed.substring(name.length + 1);
                    }
                }
                return null;
            };

            const csrfToken = getCsrfToken();

            const response = await fetch('/api/users/register/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(csrfToken && { 'X-CSRFToken': csrfToken }),
                },
                credentials: 'include',  // 重要：包含 cookies
                body: JSON.stringify(userData),
            });

            const data = await response.json();

            if (!response.ok) {
                return { 
                    success: false, 
                    message: data.error || '註冊失敗' 
                };
            }

            return { 
                success: true, 
                message: data.message || '註冊成功',
                user: data.user
            };
        } catch (error) {
            console.error('Register error:', error);
            return { 
                success: false, 
                message: '連接伺服器失敗' 
            };
        }
    };

    const logout = () => {
        setUser(null);
        setIsAuthenticated(false);
        localStorage.removeItem('user');
    };

    const value = {
        user,
        isAuthenticated,
        loading,
        login,
        register,
        logout,
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
