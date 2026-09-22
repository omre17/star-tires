const initialState = {
  role: 'manager',
  working: false,
  shiftStartedAt: null,
  hours: 8,
  inventory: [
    { size: '195/65R15', quantity: 24, updated: 'היום, 09:42' },
    { size: '205/55R16', quantity: 16, updated: 'אתמול, 18:10' },
    { size: '225/45R17', quantity: 8, updated: '20 בספט׳' },
    { size: '185/65R15', quantity: 31, updated: '19 בספט׳' }
  ],
  activities: [
    { title: 'עודכנו 4 יחידות במלאי', detail: '195/65R15 · לפני 12 דקות' },
    { title: 'העובד סיים משמרת', detail: '8:00 שעות · אתמול' },
    { title: 'דוח השכר חושב מחדש', detail: '2 עובדים · אתמול' }
  ],
  attendance: [
    { action: 'יציאה', day: 'יום שני', time: '16:00' },
    { action: 'כניסה', day: 'יום שני', time: '08:00' }
  ]
};

let state = loadState();
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem('starTiresDemo'));
    return saved && Array.isArray(saved.inventory) ? { ...structuredClone(initialState), ...saved } : structuredClone(initialState);
  } catch (_) {
    return structuredClone(initialState);
  }
}

function saveState() {
  localStorage.setItem('starTiresDemo', JSON.stringify(state));
}

function showToast(message) {
  const toast = $('#toast');
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove('show'), 2600);
}

function navigate(view) {
  const allowed = state.role === 'manager' ? ['dashboard', 'inventory', 'reports', 'assistant'] : ['dashboard', 'attendance', 'reports', 'assistant'];
  if (!allowed.includes(view)) view = 'dashboard';
  $$('.view').forEach(panel => panel.classList.toggle('active', panel.dataset.viewPanel === view));
  $$('.nav-item').forEach(item => item.classList.toggle('active', item.dataset.view === view));
  const labels = { dashboard: 'סקירה כללית', inventory: 'ניהול מלאי', attendance: 'דיווח נוכחות', reports: state.role === 'manager' ? 'דוח שכר' : 'הדוח האישי שלי', assistant: 'עוזר AI' };
  $('#pageTitle').textContent = labels[view];
  $('#sidebar').classList.remove('open');
  $('#mobileMenu').setAttribute('aria-expanded', 'false');
}

function renderRole() {
  document.body.dataset.role = state.role;
  $('#roleSelect').value = state.role;
  const manager = state.role === 'manager';
  $('#profileName').textContent = manager ? 'מנהל דמו' : 'עובד דמו';
  $('#profileRole').textContent = manager ? 'הרשאת מנהל' : 'הרשאת עובד';
  $('#avatar').textContent = manager ? 'מ' : 'ע';
  $('#welcomeTitle').textContent = manager ? 'בוקר טוב, מנהל הדמו' : 'בוקר טוב, עובד הדמו';
  $('#welcomeCopy').textContent = manager ? 'המלאי, הנוכחות ואומדן השכר מרוכזים במקום אחד.' : 'כאן אפשר לדווח נוכחות ולצפות בשעות ובאומדן השכר.';
  $('.role-report-label').textContent = manager ? 'דוח שכר' : 'הדוח האישי שלי';
  $('#reportsTitle').textContent = manager ? 'אומדן שכר' : 'הדוח האישי שלי';
  navigate('dashboard');
  renderAll();
}

function renderInventory() {
  const query = $('#inventorySearch').value.trim().toLowerCase();
  const items = state.inventory.filter(item => item.size.toLowerCase().includes(query));
  $('#inventoryTable').innerHTML = items.map(item => {
    const low = item.quantity < 10;
    return `<tr><td><strong dir="ltr">${escapeHtml(item.size)}</strong></td><td>${item.quantity}</td><td><span class="pill ${low ? 'warning' : 'success'}">${low ? 'מלאי נמוך' : 'תקין'}</span></td><td>${escapeHtml(item.updated)}</td></tr>`;
  }).join('') || '<tr><td colspan="4">לא נמצאו מידות מתאימות.</td></tr>';

  const total = state.inventory.reduce((sum, item) => sum + item.quantity, 0);
  $('#totalStock').textContent = total;
  $('#activeSizes').textContent = state.inventory.length;
  $('#lowStock').textContent = state.inventory.filter(item => item.quantity < 10).length;
  const max = Math.max(...state.inventory.map(item => item.quantity), 1);
  $('#stockBars').innerHTML = [...state.inventory].sort((a,b) => b.quantity-a.quantity).slice(0,4).map(item => `<div class="stock-row"><strong>${escapeHtml(item.size)}</strong><div class="bar-track"><div class="bar-fill ${item.quantity < 10 ? 'low' : ''}" style="width:${Math.max(8, item.quantity/max*100)}%"></div></div><span>${item.quantity}</span></div>`).join('');
}

function renderActivity() {
  $('#activityList').innerHTML = state.activities.slice(0,4).map(item => `<li><div><strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(item.detail)}</span></div></li>`).join('');
}

function renderAttendance() {
  const label = state.working ? 'בעבודה' : 'לא בעבודה';
  const note = state.working ? `המשמרת התחילה ב־${state.shiftStartedAt}` : 'אפשר להתחיל משמרת חדשה';
  $('#workerStatus').textContent = label;
  $('#workerStatusNote').textContent = note;
  $('#shiftDescription').textContent = state.working ? note : 'אין כרגע משמרת פתוחה.';
  $('#attendanceState').textContent = label;
  $('#attendanceTime').textContent = note;
  $('#workerHours').textContent = state.hours.toFixed(1);
  $('#workerPay').textContent = `₪${Math.round(state.hours * 50)}`;
  [$('#dashboardClockButton'), $('#attendanceClockButton')].forEach(button => {
    button.textContent = state.working ? 'סיום עבודה' : 'התחלת עבודה';
    button.classList.toggle('clocked-in', state.working);
  });
  $('#attendanceTable').innerHTML = state.attendance.map(item => `<tr><td><strong>${escapeHtml(item.action)}</strong></td><td>${escapeHtml(item.day)}</td><td>${escapeHtml(item.time)}</td></tr>`).join('');
}

function toggleClock() {
  const now = new Date();
  const time = now.toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' });
  if (!state.working) {
    state.working = true;
    state.shiftStartedAt = time;
    state.attendance.unshift({ action: 'כניסה', day: 'היום', time });
    showToast('הכניסה לעבודה נרשמה בהצלחה');
  } else {
    state.working = false;
    state.shiftStartedAt = null;
    state.hours = Math.round((state.hours + 0.1) * 10) / 10;
    state.attendance.unshift({ action: 'יציאה', day: 'היום', time });
    showToast('היציאה מהעבודה נרשמה בהצלחה');
  }
  saveState();
  renderAttendance();
}

function addStock(event) {
  event.preventDefault();
  const size = $('#tireSize').value.trim().toUpperCase();
  const quantity = Number($('#tireQuantity').value);
  if (!size || !Number.isInteger(quantity) || quantity < 1 || quantity > 1000) return;
  const existing = state.inventory.find(item => item.size === size);
  if (existing) {
    existing.quantity += quantity;
    existing.updated = 'עכשיו';
  } else {
    state.inventory.unshift({ size, quantity, updated: 'עכשיו' });
  }
  state.activities.unshift({ title: `עודכנו ${quantity} יחידות במלאי`, detail: `${size} · עכשיו` });
  saveState();
  event.target.reset();
  $('#tireQuantity').value = 4;
  renderInventory();
  renderActivity();
  showToast(`${quantity} יחידות נוספו למידה ${size}`);
}

function answerQuestion(question) {
  const normalized = question.toLowerCase();
  if (/מלאי|מידות|חסר/.test(normalized) && state.role === 'manager') {
    const low = state.inventory.filter(item => item.quantity < 10);
    return low.length ? `כרגע יש ${low.length} מידות במלאי נמוך: ${low.map(item => `${item.size} (${item.quantity} יחידות)`).join(', ')}.` : 'כל מידות הצמיגים נמצאות כרגע בכמות תקינה.';
  }
  if (/שעות|עבדתי|נוכחות/.test(normalized)) return `השבוע הושלמו ${state.hours.toFixed(1)} שעות עבודה. משמרת פתוחה אינה נכללת בחישוב עד לדיווח יציאה.`;
  if (/שכר|כסף|אומדן/.test(normalized)) return `אומדן השכר לפי ${state.hours.toFixed(1)} שעות ובתעריף של ₪50 לשעה הוא ₪${Math.round(state.hours * 50)}.`;
  return 'בדמו אפשר לשאול על שעות העבודה ואומדן השכר' + (state.role === 'manager' ? ', וגם על מצב המלאי.' : '.');
}

function sendQuestion(event, suggestedQuestion) {
  if (event) event.preventDefault();
  const input = $('#chatInput');
  const question = (suggestedQuestion || input.value).trim();
  if (!question) return;
  const log = $('#chatLog');
  log.insertAdjacentHTML('beforeend', `<div class="message user"><div><p>${escapeHtml(question)}</p></div></div>`);
  input.value = '';
  setTimeout(() => {
    log.insertAdjacentHTML('beforeend', `<div class="message assistant"><span class="ai-mark">✦</span><div><strong>עוזר הכוכב</strong><p>${escapeHtml(answerQuestion(question))}</p></div></div>`);
    log.scrollTop = log.scrollHeight;
  }, 260);
  log.scrollTop = log.scrollHeight;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, char => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;' })[char]);
}

function renderAll() {
  renderInventory();
  renderActivity();
  renderAttendance();
}

$$('.nav-item').forEach(item => item.addEventListener('click', () => navigate(item.dataset.view)));
$$('[data-go]').forEach(button => button.addEventListener('click', () => navigate(button.dataset.go)));
$('#roleSelect').addEventListener('change', event => { state.role = event.target.value; saveState(); renderRole(); });
$('#stockForm').addEventListener('submit', addStock);
$('#inventorySearch').addEventListener('input', renderInventory);
$('#dashboardClockButton').addEventListener('click', toggleClock);
$('#attendanceClockButton').addEventListener('click', toggleClock);
$('#chatForm').addEventListener('submit', sendQuestion);
$$('#suggestions button').forEach(button => button.addEventListener('click', () => sendQuestion(null, button.dataset.question)));
$('#resetButton').addEventListener('click', () => { state = structuredClone(initialState); saveState(); renderRole(); showToast('נתוני הדמו אופסו'); });
$('#mobileMenu').addEventListener('click', event => { const open = $('#sidebar').classList.toggle('open'); event.currentTarget.setAttribute('aria-expanded', String(open)); });
document.addEventListener('keydown', event => { if (event.key === 'Escape') $('#sidebar').classList.remove('open'); });

renderRole();
