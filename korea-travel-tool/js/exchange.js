const API_URL = 'https://api.frankfurter.dev/v2/rate/TWD/KRW';
const CACHE_KEY = 'korea-travel-rate-v1';
const CACHE_MAX_AGE = 6 * 60 * 60 * 1000;

const krwFormat = new Intl.NumberFormat('zh-TW', { maximumFractionDigits: 0 });
const twdFormat = new Intl.NumberFormat('zh-TW', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const rateFormat = new Intl.NumberFormat('zh-TW', { maximumFractionDigits: 4 });

// 本機保留上次成功取得的匯率，供離線時換算。
function readCachedRate() {
  try {
    const data = JSON.parse(localStorage.getItem(CACHE_KEY));
    if (data && Number.isFinite(data.rate) && data.rate > 0 && /^\d{4}-\d{2}-\d{2}$/.test(data.date)) return data;
  } catch {
    // 停用本機儲存時仍可線上使用。
  }
  return null;
}

function saveRate(data) {
  try { localStorage.setItem(CACHE_KEY, JSON.stringify(data)); } catch { /* 儲存空間不可用時略過。 */ }
}

export function initExchange(onRateChange) {
  const amountInput = document.getElementById('amount');
  const result = document.getElementById('converted-amount');
  const fromCurrency = document.getElementById('from-currency');
  const toCurrencyLabel = document.getElementById('to-currency-label');
  const rateSummary = document.getElementById('rate-summary');
  const rateStatus = document.getElementById('rate-status');
  const refreshButton = document.getElementById('refresh-rate');
  let direction = 'TWD';
  let rateData = readCachedRate();

  function render() {
    fromCurrency.textContent = direction;
    toCurrencyLabel.textContent = direction === 'TWD' ? '換算為韓元 KRW' : '換算為台幣 TWD';
    const amount = Number(amountInput.value);
    if (!amountInput.value || !Number.isFinite(amount) || amount < 0) {
      result.textContent = '請輸入非負金額';
    } else if (!rateData) {
      result.textContent = '等待匯率資料';
    } else {
      const converted = direction === 'TWD' ? amount * rateData.rate : amount / rateData.rate;
      result.textContent = direction === 'TWD' ? `₩ ${krwFormat.format(converted)}` : `NT$ ${twdFormat.format(converted)}`;
    }
    rateSummary.textContent = rateData ? `1 TWD ≈ ${rateFormat.format(rateData.rate)} KRW` : '尚無可用匯率';
    if (rateData) onRateChange(rateData.rate, rateData.date, !navigator.onLine);
  }

  // API 匯率以 TWD 為基準，雙向換算共用同一數值。
  async function refreshRate(force = false) {
    if (!force && rateData && Date.now() - rateData.fetchedAt < CACHE_MAX_AGE) {
      rateStatus.textContent = `資料日期：${rateData.date}${navigator.onLine ? '' : ' · 離線使用上次匯率'}`;
      return;
    }
    if (!navigator.onLine) {
      rateStatus.textContent = rateData ? `資料日期：${rateData.date} · 離線使用上次匯率` : '目前離線，連線後才能取得匯率';
      return;
    }
    refreshButton.disabled = true;
    rateStatus.textContent = '正在更新匯率…';
    try {
      const response = await fetch(API_URL, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (data.base !== 'TWD' || data.quote !== 'KRW' || !Number.isFinite(data.rate) || data.rate <= 0 || !/^\d{4}-\d{2}-\d{2}$/.test(data.date)) {
        throw new Error('Invalid rate');
      }
      rateData = { rate: data.rate, date: data.date, fetchedAt: Date.now() };
      saveRate(rateData);
      rateStatus.textContent = `資料日期：${rateData.date}`;
      render();
    } catch {
      rateStatus.textContent = rateData ? `更新失敗 · 使用 ${rateData.date} 的匯率` : '暫時無法取得匯率，請稍後重試';
    } finally {
      refreshButton.disabled = false;
    }
  }

  amountInput.addEventListener('input', render);
  document.getElementById('swap-currency').addEventListener('click', () => {
    direction = direction === 'TWD' ? 'KRW' : 'TWD';
    render();
  });
  refreshButton.addEventListener('click', () => refreshRate(true));
  window.addEventListener('online', () => refreshRate());
  window.addEventListener('offline', () => {
    rateStatus.textContent = rateData ? `資料日期：${rateData.date} · 離線使用上次匯率` : '目前離線，連線後才能取得匯率';
    render();
  });

  render();
  refreshRate();

  return {
    setKrwAmount(amount) {
      direction = 'KRW';
      amountInput.value = String(amount);
      render();
    }
  };
}
