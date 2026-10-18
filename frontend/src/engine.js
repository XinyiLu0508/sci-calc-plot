// engine.js —— 统一桥接层
// 抽象两种计算通道：HTTP（FastAPI 后端）与 WASM（Pyodide）。
// 前端业务代码只 import 这里，不感知底层实现；HTTP 不可达时自动降级 WASM。
// 架构铁律：本文件不包含任何数学/采样逻辑，只把字符串参数透传给 Python 核心引擎。

const HTTP_TIMEOUT = 4000;
const PYODIDE_CDN = 'https://cdn.jsdelivr.net/pyodide/v0.26.4/full/';

let pyodidePromise = null;

async function httpCall(path, payload) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), HTTP_TIMEOUT);
  try {
    const res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: ctrl.signal,
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

function injectScript(src) {
  return new Promise((resolve, reject) => {
    if (window.loadPyodide) return resolve(window.loadPyodide);
    const s = document.createElement('script');
    s.src = src;
    s.onload = () => resolve(window.loadPyodide);
    s.onerror = () => reject(new Error('Pyodide 脚本加载失败'));
    document.head.appendChild(s);
  });
}

async function loadPyodideEngine() {
  if (!pyodidePromise) {
    pyodidePromise = (async () => {
      const loadPyodide = await injectScript(PYODIDE_CDN + 'pyodide.js');
      const pyodide = await loadPyodide({ indexURL: PYODIDE_CDN });
      // 按依赖顺序写入 core 模块（模块间为相对 import，需组成 core 包）
      const modules = [
        '__init__.py', 'errors.py', 'tokenizer.py', 'parser.py',
        'evaluator.py', 'sampler.py', 'engine.py',
      ];
      for (const m of modules) {
        const text = await (await fetch('/core/' + m)).text();
        pyodide.FS.writeFile('/home/pyodide/core/' + m, text);
      }
      await pyodide.runPython('import core.engine');
      return pyodide;
    })();
  }
  return pyodidePromise;
}

async function wasmCall(fn, argsJson) {
  const pyodide = await loadPyodideEngine();
  // Pyodide 自动把 Python dict/list/float/str 转换成 JS 对象
  return pyodide.runPython(`core.engine.${fn}(${argsJson})`);
}

async function call(fn, argsObj, argsJson) {
  const path = {
    evaluate: '/api/evaluate',
    validate: '/api/validate',
    sample_function: '/api/sample',
  }[fn];
  try {
    return await httpCall(path, argsObj);
  } catch (e) {
    try {
      return await wasmCall(fn, argsJson);
    } catch (e2) {
      return {
        ok: false,
        error: { code: 'ENGINE_UNAVAILABLE', message: '计算引擎不可用：请检查网络或稍后重试', position: -1 },
      };
    }
  }
}

export async function evaluate(expr, angle = 'rad') {
  return call('evaluate', { expr, angle }, `(${JSON.stringify(expr)}, ${JSON.stringify(angle)})`);
}

export async function validate(expr) {
  return call('validate', { expr }, `(${JSON.stringify(expr)})`);
}

export async function sampleFunction(expr, xMin, xMax, steps, angle = 'rad') {
  return call(
    'sample_function',
    { expr, x_min: xMin, x_max: xMax, steps },
    `(${JSON.stringify(expr)}, ${xMin}, ${xMax}, ${steps}, ${JSON.stringify(angle)})`
  );
}
