import { describe, it, expect } from 'vitest';
import { keyToAction, FUNCTION_NAMES, CONSTANT_NAMES } from './keys.js';

describe('键盘映射', () => {
  it('Enter → 计算', () => expect(keyToAction('Enter')).toBe('evaluate'));
  it('Escape → 清空', () => expect(keyToAction('Escape')).toBe('clear'));
  it('Backspace → 退格', () => expect(keyToAction('Backspace')).toBe('backspace'));
  it('未知键返回 null', () => expect(keyToAction('F5')).toBeNull());
  it('包含基础科学函数', () => {
    expect(FUNCTION_NAMES).toContain('sin');
    expect(FUNCTION_NAMES).toContain('cos');
    expect(FUNCTION_NAMES).toContain('sqrt');
    expect(FUNCTION_NAMES).toContain('factorial');
  });
  it('包含常量', () => {
    expect(CONSTANT_NAMES).toContain('π');
    expect(CONSTANT_NAMES).toContain('e');
  });
});
