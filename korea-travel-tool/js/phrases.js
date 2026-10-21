// 韓語清單由 JSON 載入，分類與搜尋共用同一批資料。
export async function initPhrases() {
  const search = document.getElementById('phrase-search');
  const filters = document.getElementById('phrase-filters');
  const list = document.getElementById('phrase-list');
  const status = document.getElementById('phrase-status');
  let phrases = [];
  let category = '全部';

  function speak(korean) {
    if (!('speechSynthesis' in window)) {
      status.textContent = '此瀏覽器不支援語音朗讀，仍可查看韓文與拼音。';
      return;
    }
    const voice = new SpeechSynthesisUtterance(korean);
    voice.lang = 'ko-KR';
    voice.rate = 0.85;
    const koreanVoice = speechSynthesis.getVoices().find((item) => item.lang.toLowerCase().startsWith('ko'));
    if (koreanVoice) voice.voice = koreanVoice;
    speechSynthesis.cancel();
    speechSynthesis.speak(voice);
  }

  function renderList() {
    const query = search.value.trim().toLocaleLowerCase();
    const matches = phrases.filter((item) =>
      (category === '全部' || item.category === category) &&
      [item.chinese, item.korean, item.romanization].some((value) => value.toLocaleLowerCase().includes(query))
    );
    list.replaceChildren();
    for (const item of matches) {
      const card = document.createElement('article');
      card.className = 'phrase-card';
      const top = document.createElement('div');
      top.className = 'phrase-top';
      const intro = document.createElement('div');
      const label = document.createElement('p');
      label.className = 'phrase-category';
      label.textContent = item.category;
      const chinese = document.createElement('p');
      chinese.className = 'phrase-chinese';
      chinese.textContent = item.chinese;
      intro.append(label, chinese);
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'speak-button';
      button.textContent = '▶ 發音';
      button.setAttribute('aria-label', `朗讀韓文：${item.korean}`);
      button.addEventListener('click', () => speak(item.korean));
      top.append(intro, button);
      const korean = document.createElement('p');
      korean.className = 'phrase-korean';
      korean.lang = 'ko';
      korean.textContent = item.korean;
      const romanization = document.createElement('p');
      romanization.className = 'phrase-romanization';
      romanization.textContent = item.romanization;
      card.append(top, korean, romanization);
      list.append(card);
    }
    if (!matches.length) {
      const empty = document.createElement('p');
      empty.className = 'empty-message';
      empty.textContent = '找不到符合的語句，試試其他關鍵字。';
      list.append(empty);
    }
    status.textContent = `顯示 ${matches.length} 句常用語。發音功能依裝置的韓語語音支援而定。`;
  }

  function renderFilters() {
    filters.replaceChildren();
    const categories = ['全部', ...new Set(phrases.map((item) => item.category))];
    for (const name of categories) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = `filter-button${name === category ? ' is-active' : ''}`;
      button.textContent = name;
      button.setAttribute('aria-pressed', String(name === category));
      button.addEventListener('click', () => {
        category = name;
        renderFilters();
        renderList();
      });
      filters.append(button);
    }
  }

  search.addEventListener('input', renderList);
  status.textContent = '正在載入常用語…';
  try {
    const response = await fetch('./data/korean.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (!Array.isArray(data)) throw new Error('Invalid phrase data');
    phrases = data.filter((item) => item && ['category', 'chinese', 'korean', 'romanization'].every((key) => typeof item[key] === 'string'));
    renderFilters();
    renderList();
  } catch {
    status.textContent = '無法載入常用語，請連線後重新整理。';
  }
}
