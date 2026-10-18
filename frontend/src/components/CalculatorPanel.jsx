import { useCallback, useEffect, useRef, useState } from 'react';
import { evaluate, validate } from '../engine';
import { addHistory, loadHistory, clearHistory } from '../lib/history';
import { keyToAction, FUNCTION_NAMES } from '../lib/keys';

// 主键位（label 即显示文本；÷ × − 等符号经 TOKEN_MAP 映射为引擎运算符）
const GRID = [
  ['7', '8', '9', '÷', 'AC'],
  ['4', '5', '6', '×', '⌫'],
  ['1', '2', '3', '−', '^'],
  ['0', '.', 'π', '+', '%'],
  ['(', ')', 'e', '!', '='],
];

const TOKEN_MAP = { '÷': '/', '×': '*', '−': '-', 'π': 'π' };
const toToken = (label) => TOKEN_MAP[label] ?? label;

const FUNC_BUTTONS = FUNCTION_NAMES.map(name => ({ label: name, token: name + '(' }));

export default function CalculatorPanel({ angle }) {
  const [expr, setExpr] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState(() => loadHistory());
  const inputRef = useRef(null);

  // 实时校验（防抖 250ms，走引擎的 validate，避免在前端写解析逻辑）
  useEffect(() => {
    const timer = setTimeout(() => {
      if (expr.trim() === '') { setError(null); return; }
      validate(expr).then(r => setError(r.ok ? null : r.error));
    }, 250);
    return () => clearTimeout(timer);
  }, [expr]);

  const insert = useCallback((token) => {
    const el = inputRef.current;
    const start = el ? (el.selectionStart ?? expr.length) : expr.length;
    const end = el ? (el.selectionEnd ?? expr.length) : expr.length;
    setExpr(expr.slice(0, start) + token + expr.slice(end));
    requestAnimationFrame(() => {
      if (el) {
        el.focus();
        const pos = start + token.length;
        el.setSelectionRange(pos, pos);
      }
    });
  }, [expr]);

  const backspace = useCallback(() => {
    const el = inputRef.current;
    const start = el ? (el.selectionStart ?? expr.length) : expr.length;
    const end = el ? (el.selectionEnd ?? expr.length) : expr.length;
    if (start !== end) setExpr(expr.slice(0, start) + expr.slice(end));
    else if (start > 0) setExpr(expr.slice(0, start - 1) + expr.slice(start));
  }, [expr]);

  const doEvaluate = useCallback(async () => {
    const s = expr.trim();
    if (s === '') return;
    const r = await evaluate(s, angle);
    if (r.ok) {
      setResult(r);
      setError(null);
      setHistory(prev => addHistory(prev, { expr: s, result: r.display, ts: Date.now() }));
    } else {
      setResult(null);
      setError(r.error);
    }
  }, [expr, angle]);

  const clearAll = useCallback(() => { setExpr(''); setResult(null); setError(null); }, []);

  const handleKey = useCallback((e) => {
    const action = keyToAction(e.key);
    if (!action) return;
    e.preventDefault();
    if (action === 'evaluate') doEvaluate();
    else if (action === 'clear') clearAll();
    else if (action === 'backspace') backspace();
  }, [doEvaluate, clearAll, backspace]);

  const onButton = useCallback((label) => {
    if (label === 'AC') clearAll();
    else if (label === '⌫') backspace();
    else if (label === '=') doEvaluate();
    else insert(toToken(label));
  }, [clearAll, backspace, doEvaluate, insert]);

  const pickHistory = useCallback((item) => {
    setExpr(item.expr);
    setResult(null);
    setError(null);
    inputRef.current?.focus();
  }, []);

  return (
    <div className="calc">
      <div className="calc-display">
        <input
          ref={inputRef}
          className={`expr-input ${error ? 'invalid' : ''}`}
          value={expr}
          onChange={(e) => { setExpr(e.target.value); setResult(null); }}
          onKeyDown={handleKey}
          placeholder="输入表达式，如 sin(pi/2) + 1"
          aria-label="表达式输入框"
          spellCheck={false}
          autoComplete="off"
        />
        <div className="result" aria-live="polite">
          {result ? (
            <span className="result-value">= {result.display}</span>
          ) : error ? (
            <span className="result-error">
              ⚠ {error.message}
              {error.position >= 0 && <span className="err-pos">（位置 {error.position} 附近）</span>}
            </span>
          ) : (
            ' '
          )}
        </div>
      </div>

      <div className="func-row" role="group" aria-label="科学函数">
        {FUNC_BUTTONS.map(b => (
          <button key={b.label} className="key func" onClick={() => insert(b.token)} aria-label={`插入函数 ${b.label}`}>
            {b.label}
          </button>
        ))}
      </div>

      <div className="keypad" role="group" aria-label="键盘">
        {GRID.map((row, i) => (
          <div className="key-row" key={i}>
            {row.map(label => {
              const cls = [
                'key',
                label === '=' ? 'eq' : '',
                (label === 'AC' || label === '⌫') ? 'danger' : '',
                (label === 'π' || label === 'e') ? 'const' : '',
                ['+', '−', '×', '÷', '^', '%'].includes(label) ? 'op' : '',
              ].filter(Boolean).join(' ');
              return (
                <button key={label} className={cls} onClick={() => onButton(label)} aria-label={label}>
                  {label}
                </button>
              );
            })}
          </div>
        ))}
      </div>

      <div className="history">
        <div className="history-head">
          <span>历史记录</span>
          <button className="link" onClick={() => setHistory(clearHistory())} disabled={history.length === 0}>清空</button>
        </div>
        <ul className="history-list">
          {history.length === 0 && <li className="history-empty">暂无历史</li>}
          {history.map((h, i) => (
            <li key={i}>
              <button className="history-item" onClick={() => pickHistory(h)}>
                <span className="h-expr">{h.expr}</span>
                <span className="h-result">= {h.result}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
