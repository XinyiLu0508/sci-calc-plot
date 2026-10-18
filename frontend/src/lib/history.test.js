import { describe, it, expect } from 'vitest';
import { loadHistory, addHistory, clearHistory } from './history.js';

function fakeStorage() {
  const m = {};
  return {
    getItem: (k) => (k in m ? m[k] : null),
    setItem: (k, v) => { m[k] = String(v); },
    removeItem: (k) => { delete m[k]; },
  };
}

describe('历史记录', () => {
  it('增加并回读', () => {
    const s = fakeStorage();
    const list = addHistory([], { expr: '1+1', result: '2', ts: 1 }, s);
    expect(list.length).toBe(1);
    expect(loadHistory(s).length).toBe(1);
  });

  it('上限 200 条裁剪，最新在前', () => {
    const s = fakeStorage();
    let list = [];
    for (let i = 0; i < 250; i++) {
      list = addHistory(list, { expr: String(i), result: String(i), ts: i }, s);
    }
    expect(list.length).toBe(200);
    expect(list[0].expr).toBe('249');
    expect(loadHistory(s).length).toBe(200);
  });

  it('清空', () => {
    const s = fakeStorage();
    addHistory([], { expr: '1', result: '1', ts: 0 }, s);
    expect(clearHistory(s).length).toBe(0);
    expect(loadHistory(s).length).toBe(0);
  });
});
