/**
 * useTableState Hook
 * 
 * 管理 Ant Design Table 的排序、篩選狀態，並持久化到 LocalStorage
 * 支援 F5 刷新後保持排序設定
 * 
 * @example
 * const { tableState, handleTableChange, getSortProps } = useTableState('my_table_key', {
 *     sortField: 'created_at',
 *     sortOrder: 'descend',
 * });
 * 
 * // 在 Table columns 中使用
 * {
 *     title: '創建時間',
 *     dataIndex: 'created_at',
 *     sorter: true,
 *     ...getSortProps('created_at'),
 * }
 * 
 * // Table onChange
 * <Table onChange={handleTableChange} ... />
 */

import { useState, useEffect, useCallback, useMemo } from 'react';

/**
 * 自訂 Hook：管理表格排序/篩選狀態的持久化
 * 
 * @param {string} storageKey - LocalStorage 的 key
 * @param {object} defaultState - 預設狀態
 * @param {string} [defaultState.sortField] - 預設排序欄位
 * @param {string} [defaultState.sortOrder] - 預設排序方向 ('ascend' | 'descend')
 * @param {object} [defaultState.filters] - 預設篩選條件
 * @param {number} [defaultState.pageSize] - 預設每頁筆數
 * @returns {object} Hook 返回值
 */
const useTableState = (storageKey, defaultState = {}) => {
    // 合併預設狀態
    const initialDefault = useMemo(() => ({
        sortField: null,
        sortOrder: null,
        filters: {},
        pageSize: 10,
        current: 1,
        ...defaultState,
    }), []);  // eslint-disable-line react-hooks/exhaustive-deps

    // 初始化時從 LocalStorage 讀取
    const [tableState, setTableState] = useState(() => {
        try {
            const saved = localStorage.getItem(storageKey);
            if (saved) {
                const parsed = JSON.parse(saved);
                return { ...initialDefault, ...parsed };
            }
            return initialDefault;
        } catch (error) {
            console.warn(`[useTableState] 讀取 LocalStorage 失敗 (${storageKey}):`, error);
            return initialDefault;
        }
    });

    // 狀態變化時自動保存到 LocalStorage
    useEffect(() => {
        try {
            // 只保存排序相關的狀態，不保存分頁（分頁通常不需要持久化）
            const stateToSave = {
                sortField: tableState.sortField,
                sortOrder: tableState.sortOrder,
                // pageSize: tableState.pageSize,  // 可選：是否保存每頁筆數
            };
            localStorage.setItem(storageKey, JSON.stringify(stateToSave));
        } catch (error) {
            console.warn(`[useTableState] 保存 LocalStorage 失敗 (${storageKey}):`, error);
        }
    }, [storageKey, tableState.sortField, tableState.sortOrder]);

    /**
     * 處理 Ant Design Table 的 onChange 事件
     * @param {object} pagination - 分頁資訊
     * @param {object} filters - 篩選條件
     * @param {object} sorter - 排序資訊
     */
    const handleTableChange = useCallback((pagination, filters, sorter) => {
        setTableState(prev => ({
            ...prev,
            sortField: sorter.field || sorter.columnKey || null,
            sortOrder: sorter.order || null,
            filters: filters || {},
            pageSize: pagination?.pageSize || prev.pageSize,
            current: pagination?.current || prev.current,
        }));
    }, []);

    /**
     * 獲取特定欄位的排序屬性（用於 Table columns 配置）
     * @param {string} field - 欄位名稱
     * @returns {object} 包含 sortOrder 的物件，可直接展開到 column 配置
     */
    const getSortProps = useCallback((field) => {
        return {
            sortOrder: tableState.sortField === field ? tableState.sortOrder : null,
        };
    }, [tableState.sortField, tableState.sortOrder]);

    /**
     * 重置表格狀態
     */
    const resetTableState = useCallback(() => {
        setTableState(initialDefault);
        try {
            localStorage.removeItem(storageKey);
        } catch (error) {
            console.warn(`[useTableState] 清除 LocalStorage 失敗 (${storageKey}):`, error);
        }
    }, [storageKey, initialDefault]);

    /**
     * 手動設置排序
     * @param {string} field - 排序欄位
     * @param {string} order - 排序方向 ('ascend' | 'descend' | null)
     */
    const setSorting = useCallback((field, order) => {
        setTableState(prev => ({
            ...prev,
            sortField: field,
            sortOrder: order,
        }));
    }, []);

    return {
        tableState,
        setTableState,
        handleTableChange,
        getSortProps,
        resetTableState,
        setSorting,
    };
};

export default useTableState;
