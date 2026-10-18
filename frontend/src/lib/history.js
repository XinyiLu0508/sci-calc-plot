// 历史记录：localStorage 持久化，上限 200 条，超出自动裁剪（最新在前）。
// storage 参数可注入，便于测试脱离真实 localStorage。

const STORAGE_KEY = 'sci-calc-history';
export const MAX_ITEMS = 200;

export function loadHistory(storage = localStorage) {
  try {
    const raw = storage.getItem(STORAGE_KEY);
    const list = raw ? JSON.parse(raw) : [];
    return Array.isArray(list) ? list.slice(0, MAX_ITEMS) : [];
  } catch (e) {
    return [];
  }
}

export function saveHistory(list, storage = localStorage) {
  const trimmed = list.slice(0, MAX_ITEMS);
  storage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
  return trimmed;
}

export function addHistory(list, entry, storage = localStorage) {
  const next = [entry, ...list].slice(0, MAX_ITEMS);
  return saveHistory(next, storage);
}

export function clearHistory(storage = localStorage) {
  storage.removeItem(STORAGE_KEY);
  return [];
}
