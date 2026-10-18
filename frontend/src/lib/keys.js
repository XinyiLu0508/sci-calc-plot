// 键盘与科学函数面板的共享定义。
// 说明：数字、运算符等可打印字符由 <input> 原生处理，
// 这里只定义需要特殊拦截的动作键，以及函数名/常量列表（供面板与测试共用）。

export const FUNCTION_NAMES = [
  'sin', 'cos', 'tan', 'asin', 'acos', 'atan',
  'log', 'ln', 'exp', 'sqrt', 'abs', 'factorial',
];

export const CONSTANT_NAMES = ['π', 'e'];

// 物理键盘特殊键 → 动作
export function keyToAction(key) {
  const map = {
    Enter: 'evaluate',
    Escape: 'clear',
    Backspace: 'backspace',
    Delete: 'clear',
  };
  return map[key] ?? null;
}
