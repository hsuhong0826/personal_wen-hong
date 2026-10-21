import { initExchange } from './exchange.js';
import { initQuickTable } from './quick-table.js';
import { initPhrases } from './phrases.js';

// 共用頁面切換
const tabs = [...document.querySelectorAll('[data-view]')];

function showView(name) {
  for (const tab of tabs) {
    const active = tab.dataset.view === name;
    tab.classList.toggle('is-active', active);
    if (active) tab.setAttribute('aria-current', 'page');
    else tab.removeAttribute('aria-current');
    document.getElementById(`view-${tab.dataset.view}`).hidden = !active;
  }
}

tabs.forEach((tab) => tab.addEventListener('click', () => showView(tab.dataset.view)));

// 各功能共用同一筆匯率；從對照表可直接帶入換算器。
const quickTable = initQuickTable((amount) => {
  exchange.setKrwAmount(amount);
  showView('exchange');
  document.getElementById('amount').focus();
});
const exchange = initExchange((rate, date, cached) => quickTable.render(rate, date, cached));
initPhrases();

// PWA 的離線頁面快取需在 HTTPS 或 localhost 上啟用。
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch(() => {
      // 不支援時仍可在線上使用網頁。
    });
  });
}
