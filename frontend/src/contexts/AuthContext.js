import React, { createContext, useState, useContext, useEffect } from 'react';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // 模擬從 localStorage 或 API 獲取用戶資訊
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
            const parsedUser = JSON.parse(storedUser);
            setUser(parsedUser);
            setIsAuthenticated(true);
        } else {
            // 預設管理員用戶 (開發環境)
            const defaultUser = {
                username: 'admin',
                email: 'admin@network-toolbox.local',
                is_staff: true,
                is_superuser: true,
            };
            setUser(defaultUser);
            setIsAuthenticated(true);
            localStorage.setItem('user', JSON.stringify(defaultUser));
        }
        setLoading(false);
    }, []);

    const login = async (credentials) => {
        // TODO: 實現真實的登入邏輯
        const user = {
            username: credentials.username,
            email: credentials.email || 'user@network-toolbox.local',
            is_staff: true,
        };
        setUser(user);
        setIsAuthenticated(true);
        localStorage.setItem('user', JSON.stringify(user));
        return { success: true };
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
