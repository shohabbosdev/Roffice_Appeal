let token = localStorage.getItem('roffice_token');
let currentUser = null;
let currentPolicy = null;
let selectedSlot = "";
let allServices = [];

// === STANDART O'ZBEKCHA SANA VA VAQT FORMATLASH ===
function formatDateTime(dateInput) {
  if (!dateInput) return '—';
  const d = new Date(dateInput);
  if (isNaN(d.getTime())) return '—';
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  return `${day}.${month}.${year} ${hours}:${minutes}`;
}

function formatDateOnly(dateInput) {
  if (!dateInput) return '—';
  const d = new Date(dateInput);
  if (isNaN(d.getTime())) return '—';
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();
  return `${day}.${month}.${year}`;
}

// === GLOBAL RESPONSIVE TOAST NOTIFICATION SYSTEM ===
function showToast(message, type = 'info') {
  let container = document.getElementById('student-toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'student-toast-container';
    container.className = 'fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none max-w-sm w-full px-4';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  const typeStyles = {
    success: 'bg-emerald-950/95 border-emerald-500/40 text-emerald-200 shadow-emerald-950/50',
    error: 'bg-rose-950/95 border-rose-500/40 text-rose-200 shadow-rose-950/50',
    warning: 'bg-amber-950/95 border-amber-500/40 text-amber-200 shadow-amber-950/50',
    info: 'bg-slate-900/95 border-slate-700/60 text-slate-200 shadow-slate-950/50'
  };

  const icons = {
    success: '✅',
    error: '❌',
    warning: '⚠️',
    info: 'ℹ️'
  };

  toast.className = `flex items-center gap-2.5 px-4 py-3 rounded-xl border backdrop-blur-md text-xs font-medium shadow-xl pointer-events-auto transition-all duration-300 transform translate-y-2 opacity-0 ${typeStyles[type] || typeStyles.info}`;
  toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span class="flex-1">${message}</span>`;

  container.appendChild(toast);
  requestAnimationFrame(() => {
    toast.classList.remove('translate-y-2', 'opacity-0');
  });

  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-y-2');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
const showNotification = showToast;
window.showNotification = showToast;
window.alert = function(msg) {
  showToast(String(msg), 'info');
};

if (!token) {
  window.location.href = '/login';
}

function handleLogout(reason = null) {
  localStorage.removeItem('roffice_token');
  localStorage.removeItem('roffice_role');
  localStorage.removeItem('roffice_fullname');
  localStorage.removeItem('roffice_user_id');
  const target = reason ? pageUrl(`/login?reason=${encodeURIComponent(reason)}`) : pageUrl('/login');
  window.location.href = target;
}

// === 30 DAQIQALIK HARAKATSIZLIK BO'YICHA AVTOMATIK LOGOUT TIZIMI ===
const IDLE_TIMEOUT_MS = 30 * 60 * 1000;
const WARNING_TIME_MS = 28 * 60 * 1000;
let lastUserActivityTime = Date.now();
let idleCheckIntervalId = null;
let countdownTimerId = null;
let isIdleWarningShown = false;

function resetIdleTimer() {
  if (isIdleWarningShown) return;
  lastUserActivityTime = Date.now();
}

function initIdleSessionTimeout() {
  let throttleTimer = false;
  const activityEvents = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart', 'click'];
  
  activityEvents.forEach(evt => {
    window.addEventListener(evt, () => {
      if (!throttleTimer) {
        resetIdleTimer();
        throttleTimer = true;
        setTimeout(() => { throttleTimer = false; }, 2000);
      }
    }, { passive: true });
  });

  if (idleCheckIntervalId) clearInterval(idleCheckIntervalId);
  idleCheckIntervalId = setInterval(checkSessionIdleState, 5000);
}

function checkSessionIdleState() {
  const elapsed = Date.now() - lastUserActivityTime;
  
  if (elapsed >= IDLE_TIMEOUT_MS) {
    if (countdownTimerId) clearInterval(countdownTimerId);
    if (idleCheckIntervalId) clearInterval(idleCheckIntervalId);
    handleLogout('idle_timeout');
    return;
  }

  if (elapsed >= WARNING_TIME_MS && !isIdleWarningShown) {
    showIdleWarningModal(Math.max(1, Math.round((IDLE_TIMEOUT_MS - elapsed) / 1000)));
  }
}

function showIdleWarningModal(remainingSeconds) {
  isIdleWarningShown = true;
  const modal = document.getElementById('session-timeout-modal');
  const countEl = document.getElementById('session-countdown-seconds');
  if (modal) {
    modal.classList.remove('hidden');
    modal.classList.add('flex');
  }

  let currentRemaining = remainingSeconds;
  if (countEl) countEl.innerText = currentRemaining;

  if (countdownTimerId) clearInterval(countdownTimerId);
  countdownTimerId = setInterval(() => {
    currentRemaining--;
    if (countEl) countEl.innerText = currentRemaining;
    if (currentRemaining <= 0) {
      clearInterval(countdownTimerId);
      handleLogout('idle_timeout');
    }
  }, 1000);
}

function extendSessionActivity() {
  isIdleWarningShown = false;
  lastUserActivityTime = Date.now();
  if (countdownTimerId) clearInterval(countdownTimerId);
  const modal = document.getElementById('session-timeout-modal');
  if (modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  }
  showToast("Sessiya xavfsiz davom ettirildi", "success");
}

function toggleSidebar() {
  const s = document.getElementById('sidebar');
  const o = document.getElementById('sidebar-overlay');
  if (s.classList.contains('mobile-open')) {
    s.classList.remove('mobile-open');
    o.classList.add('hidden');
  } else {
    s.classList.add('mobile-open');
    o.classList.remove('hidden');
  }
}

function closeSidebar() {
  const s = document.getElementById('sidebar');
  const o = document.getElementById('sidebar-overlay');
  s.classList.remove('mobile-open');
  o.classList.add('hidden');
}
// === GLOBAL DIALOG & NOTIFICATION SYSTEM ===
let appConfirmResolve = null;

function openAppConfirm({
  title = "Tasdiqlash",
  message = "Ushbu amalni bajarishga ishonchingiz komilmi?",
  confirmText = "Tasdiqlash",
  cancelText = "Bekor qilish",
  isDanger = true
} = {}) {
  return new Promise((resolve) => {
    appConfirmResolve = resolve;
    const modal = document.getElementById('app-confirm-modal');
    const titleEl = document.getElementById('confirm-modal-title');
    const msgEl = document.getElementById('confirm-modal-msg');
    const okBtn = document.getElementById('confirm-modal-ok');
    const cancelBtn = document.getElementById('confirm-modal-cancel');
    const iconWrap = document.getElementById('confirm-modal-icon-wrap');

    if (titleEl) titleEl.innerText = title;
    if (msgEl) msgEl.innerText = message;
    if (okBtn) {
      okBtn.innerText = confirmText;
      okBtn.className = isDanger
        ? "px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition cursor-pointer shadow-lg shadow-rose-600/20"
        : "px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition cursor-pointer shadow-lg shadow-emerald-600/20";
    }
    if (cancelBtn) cancelBtn.innerText = cancelText;
    if (iconWrap) {
      iconWrap.className = isDanger
        ? "w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center flex-shrink-0"
        : "w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center flex-shrink-0";
    }
    if (modal) modal.classList.remove('hidden');
  });
}

function closeAppConfirm(result) {
  const modal = document.getElementById('app-confirm-modal');
  if (modal) modal.classList.add('hidden');
  if (appConfirmResolve) {
    appConfirmResolve(Boolean(result));
    appConfirmResolve = null;
  }
}

