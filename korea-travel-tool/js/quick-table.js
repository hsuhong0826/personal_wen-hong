const AMOUNTS_KRW = [1000, 3000, 5000, 10000, 20000, 30000, 50000, 100000];
const krwFormat = new Intl.NumberFormat('zh-TW', { maximumFractionDigits: 0 });
const twdFormat = new Intl.NumberFormat('zh-TW', { maximumFractionDigits: 2 });

// 對照表僅由換算器提供的匯率計算，不另發 API 請求。
export function initQuickTable(onPick) {
  const container = document.getElementById('quick-table');
  const status = document.getElementById('table-status');

  function render(rate, date, cached) {
    container.replaceChildren();
    if (!Number.isFinite(rate) || rate <= 0) {
      const empty = document.createElement('p');
      empty.className = 'table-empty';
      empty.textContent = '取得匯率後，這裡會顯示常見金額。';
      container.append(empty);
      status.textContent = '目前沒有可用匯率。';
      return;
    }
    for (const amount of AMOUNTS_KRW) {
      const row = document.createElement('button');
      row.type = 'button';
      row.className = 'table-row';
      row.setAttribute('aria-label', `${krwFormat.format(amount)} 韓元，約 ${twdFormat.format(amount / rate)} 台幣，帶入換算器`);
      const krw = document.createElement('span');
      const twd = document.createElement('span');
      krw.textContent = `₩ ${krwFormat.format(amount)}`;
      twd.textContent = `NT$ ${twdFormat.format(amount / rate)}`;
      row.append(krw, twd);
      row.addEventListener('click', () => onPick(amount));
      container.append(row);
    }
    status.textContent = `依 ${date} 的參考匯率估算${cached ? '；目前離線' : ''}。`;
  }

  render(null);
  return { render };
}
