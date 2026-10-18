import { useEffect, useState } from 'react';
import CalculatorPanel from './components/CalculatorPanel.jsx';
import PlotPanel from './components/PlotPanel.jsx';

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('sci-theme') || 'dark');
  const [angle, setAngle] = useState('rad');
  const [tab, setTab] = useState('calc');

  useEffect(() => {
    localStorage.setItem('sci-theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-icon" aria-hidden="true">🧮</span>
          <span className="brand-text">SciCalc <em>· 函数图像</em></span>
        </div>
        <div className="header-controls">
          <button
            className="chip"
            onClick={() => setAngle(a => (a === 'rad' ? 'deg' : 'rad'))}
            aria-pressed={angle === 'deg'}
            aria-label="切换角度/弧度"
          >
            {angle === 'rad' ? 'RAD 弧度' : 'DEG 角度'}
          </button>
          <button
            className="chip"
            onClick={() => setTheme(t => (t === 'dark' ? 'light' : 'dark'))}
            aria-label="切换深色/浅色主题"
          >
            {theme === 'dark' ? '☀️ 浅色' : '🌙 深色'}
          </button>
        </div>
      </header>

      <nav className="tabbar" aria-label="面板切换">
        <button className={`tab ${tab === 'calc' ? 'active' : ''}`} onClick={() => setTab('calc')}>计算器</button>
        <button className={`tab ${tab === 'plot' ? 'active' : ''}`} onClick={() => setTab('plot')}>函数图像</button>
      </nav>

      <main className="layout">
        <section className={`panel calc-panel ${tab === 'calc' ? 'show' : ''}`} aria-label="科学计算器">
          <CalculatorPanel angle={angle} />
        </section>
        <section className={`panel plot-panel ${tab === 'plot' ? 'show' : ''}`} aria-label="函数图像">
          <PlotPanel angle={angle} />
        </section>
      </main>
    </div>
  );
}
