// 把 ../core 下的 Python 源码同步到 frontend/public/core/，
// 供 Pyodide（WASM 降级通道）在浏览器里通过 fetch('/core/*.py') 加载。
// 单一数据源仍是 ../core/，本脚本只做拷贝，避免两处维护。
import { cpSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const src = join(frontendRoot, '..', 'core');
const dest = join(frontendRoot, 'public', 'core');

mkdirSync(dest, { recursive: true });

const files = [
  '__init__.py',
  'errors.py',
  'tokenizer.py',
  'parser.py',
  'evaluator.py',
  'sampler.py',
  'engine.py',
];

for (const f of files) {
  cpSync(join(src, f), join(dest, f));
}

console.log('[sync-core] core/*.py -> frontend/public/core/');
