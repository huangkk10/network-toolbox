import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import './utils/axiosConfig';  // 導入 axios 配置（重要：必須在最早執行）

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
    <React.StrictMode>
        <App />
    </React.StrictMode>
);
