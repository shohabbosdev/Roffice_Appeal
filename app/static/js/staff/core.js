let token = localStorage.getItem('roffice_token');
    let userRole = localStorage.getItem('roffice_role') || "office_head";
    let currentUser = null;
    let currentPolicy = null;
    let departmentsList = [];
    let nizomDutiesCatalog = [];

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
    window.formatDateTime = formatDateTime;
    window.formatDateOnly = formatDateOnly;

    if (!token) {
      window.location.href = pageUrl('/login');
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
        if (modal) {
          modal.classList.remove('hidden');
          modal.style.display = 'flex';
        }
      });
    }

    function closeAppConfirm(result) {
      const modal = document.getElementById('app-confirm-modal');
      if (modal) {
        modal.classList.add('hidden');
        modal.style.display = 'none';
      }
      if (appConfirmResolve) {
        appConfirmResolve(Boolean(result));
        appConfirmResolve = null;
      }
    }

    // Brauzer standart alert ini Tailwind toast ga almashtirish
    window.alert = function(msg) {
      showToast(String(msg), 'info');
    };

    function showToast(message, type = 'info') {
      const container = document.getElementById('app-toast-container');
      if (!container) return;

      const toast = document.createElement('div');
      const typeStyles = {
        success: 'bg-emerald-950/95 border-emerald-500/40 text-emerald-200',
        error: 'bg-rose-950/95 border-rose-500/40 text-rose-200',
        warning: 'bg-amber-950/95 border-amber-500/40 text-amber-200',
        info: 'bg-slate-900/95 border-slate-700 text-slate-200'
      };
      const typeIcons = {
        success: '✓',
        error: '✕',
        warning: '!',
        info: 'ℹ'
      };

      const styleCls = typeStyles[type] || typeStyles.info;
      const icon = typeIcons[type] || typeIcons.info;

      toast.className = `flex items-center gap-2.5 px-4 py-3 rounded-xl border shadow-xl backdrop-blur-md text-xs font-medium pointer-events-auto transition-all duration-300 transform translate-y-2 opacity-0 ${styleCls}`;
      toast.innerHTML = `
        <span class="w-5 h-5 rounded-full bg-white/10 flex items-center justify-center font-bold text-[11px] flex-shrink-0">${icon}</span>
        <span class="flex-1 leading-snug">${message}</span>
      `;

      container.appendChild(toast);
      requestAnimationFrame(() => {
        toast.classList.remove('translate-y-2', 'opacity-0');
      });

      setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-y-2');
        setTimeout(() => toast.remove(), 300);
      }, 4000);
    }

    function extractErrorMessage(data, fallback = "Xatolik yuz berdi.") {
      if (!data) return fallback;
      if (typeof data.detail === 'string') return data.detail;
      if (Array.isArray(data.detail)) {
        return data.detail.map(e => (e.loc ? e.loc.join(' -> ') + ': ' : '') + e.msg).join('; ');
      }
      if (data.message) return data.message;
      return fallback;
    }

    function toggleNewStaffPasswordInput() {
      const mode = document.querySelector('input[name="new_staff_pwd_mode"]:checked')?.value;
      const wrap = document.getElementById('new-staff-custom-pwd-wrap');
      if (wrap) {
        if (mode === 'custom') {
          wrap.classList.remove('hidden');
        } else {
          wrap.classList.add('hidden');
        }
      }
    }
    window.toggleNewStaffPasswordInput = toggleNewStaffPasswordInput;

    /**
     * Universal Excel (.xls) Formatter and Exporter
     * Creates professional, styled spreadsheets with colors, headers, and borders.
     */
    function exportToExcelXls(filename, sheetName, title, metaLines, headers, rows) {
      const colSpan = (headers && headers.length) ? headers.length : 6;
      let html = `
        <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
        <head>
          <meta charset="utf-8">
          <!--[if gte mso 9]>
          <xml>
            <x:ExcelWorkbook>
              <x:ExcelWorksheets>
                <x:ExcelWorksheet>
                  <x:Name>${sheetName || 'Hisobot'}</x:Name>
                  <x:WorksheetOptions>
                    <x:DisplayGridlines/>
                  </x:WorksheetOptions>
                </x:ExcelWorksheet>
              </x:ExcelWorksheets>
            </x:ExcelWorkbook>
          </xml>
          <![endif]-->
          <style>
            body { font-family: 'Calibri', 'Segoe UI', Arial, sans-serif; }
            .main-title { background-color: #1e3a8a; color: #ffffff; font-size: 13pt; font-weight: bold; text-align: center; height: 38px; vertical-align: middle; border: 1px solid #1e3a8a; }
            .sub-title { background-color: #f8fafc; color: #334155; font-size: 9.5pt; height: 24px; vertical-align: middle; padding: 4px 8px; border-bottom: 1px solid #e2e8f0; }
            .th-cell { background-color: #2563eb; color: #ffffff; font-size: 10pt; font-weight: bold; text-align: center; vertical-align: middle; border: 1px solid #1d4ed8; height: 30px; padding: 4px 8px; }
            .td-cell { font-size: 9.5pt; vertical-align: middle; border: 1px solid #cbd5e1; padding: 5px 8px; mso-number-format: "\\@"; }
            .td-badge-completed { background-color: #dcfce7; color: #15803d; font-weight: bold; text-align: center; border: 1px solid #cbd5e1; padding: 5px 8px; font-size: 9.5pt; }
            .td-badge-progress { background-color: #fef3c7; color: #b45309; font-weight: bold; text-align: center; border: 1px solid #cbd5e1; padding: 5px 8px; font-size: 9.5pt; }
            .td-badge-danger { background-color: #fee2e2; color: #b91c1c; font-weight: bold; text-align: center; border: 1px solid #cbd5e1; padding: 5px 8px; font-size: 9.5pt; }
            .zebra-even { background-color: #ffffff; }
            .zebra-odd { background-color: #f8fafc; }
          </style>
        </head>
        <body>
          <table>
      `;

      if (title) {
        html += `<tr><td colspan="${colSpan}" class="main-title">${title}</td></tr>`;
      }
      if (metaLines && metaLines.length) {
        metaLines.forEach(m => {
          html += `<tr><td colspan="${colSpan}" class="sub-title">${m}</td></tr>`;
        });
        html += `<tr><td colspan="${colSpan}" style="height: 10px;"></td></tr>`;
      }
      if (headers && headers.length) {
        html += `<tr>`;
        headers.forEach(h => {
          html += `<th class="th-cell">${h}</th>`;
        });
        html += `</tr>`;
      }
      if (rows && rows.length) {
        rows.forEach((r, idx) => {
          const zebra = (idx % 2 === 0) ? 'zebra-even' : 'zebra-odd';
          html += `<tr>`;
          r.forEach(cell => {
            let val = (cell === null || cell === undefined) ? '' : String(cell);
            let cls = `td-cell ${zebra}`;
            if (val.includes('Yakunlandi') || val.includes('Tasdiqlandi') || val.includes('100%')) {
              cls = `td-badge-completed`;
            } else if (val.includes('Ijroda') || val.includes('Biriktirilgan') || val.includes('Yangi')) {
              cls = `td-badge-progress`;
            } else if (val.includes('Rad etildi') || val.includes("E'tiroz") || val.includes("Muddati o'tgan")) {
              cls = `td-badge-danger`;
            }
            val = val.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            html += `<td class="${cls}">${val}</td>`;
          });
          html += `</tr>`;
        });
      }

      html += `
          </table>
        </body>
        </html>
      `;

      const blob = new Blob(['\uFEFF', html], { type: 'application/vnd.ms-excel;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', filename.endsWith('.xls') ? filename : `${filename}.xls`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    }
    window.exportToExcelXls = exportToExcelXls;

    // 1. Core Tab Router with URL Hash and LocalStorage Persistence
    function switchStaffTab(tabId, updateHash = true) {
      if (tabId === 'system' && !hasPerm('system:metrics') && !hasPerm('system:backups_manage') && userRole !== 'admin') {
        showToast("Tizim va zaxiralar bo'limi faqat Administrator uchun ochiq!", "warning");
        return;
      }
      if (tabId === 'audit' && !hasPerm('audit:view')) {
        showToast("Tizim audit jurnali bo'limiga kirish huquqingiz yo'q!", "warning");
        return;
      }
      if (tabId === 'analytics' && !hasPerm('analytics:view')) {
        showToast("Rahbariyat tahliliy hisobotlari bo'limiga kirish huquqingiz yo'q!", "warning");
        return;
      }
      if (tabId === 'users' && !hasPerm('users:view') && !hasPerm('users:create') && !hasPerm('users:edit') && !hasPerm('roles:manage')) {
        showToast("Xodimlarni boshqarish bo'limiga kirish huquqingiz yo'q!", "warning");
        return;
      }
      if (tabId === 'roles' && !hasPerm('roles:manage')) {
        showToast("Rollar va huquqlar matritsasiga kirish huquqingiz yo'q!", "warning");
        return;
      }
      if (tabId === 'policy' && !hasPerm('services:manage') && userRole !== 'office_head') {
        showToast("Ta'lim shakli cheklovlari bo'limiga kirish huquqingiz yo'q!", "warning");
        return;
      }
      if (tabId === 'queue' && !hasPerm('queue:call') && !hasPerm('queue:complete') && !hasPerm('queue:manage_windows') && !hasPerm('queue:view_board')) {
        showToast("Elektron navbat bo'limiga kirish huquqingiz yo'q!", "warning");
        return;
      }
      if (tabId === 'services' && !hasPerm('services:view') && !hasPerm('services:manage')) {
        showToast("Xizmatlar katalogi bo'limiga kirish huquqingiz yo'q!", "warning");
        return;
      }
      if (tabId === 'calendar' && !hasPerm('calendar:manage') && !['admin', 'office_head', 'vice_rector'].includes(userRole)) {
        showToast("Bayramlar taqvimi bo'limiga kirish huquqingiz yo'q!", "warning");
        return;
      }

      const isRolesRequested = (tabId === 'roles');
      const targetTabId = isRolesRequested ? 'users' : tabId;

      document.querySelectorAll('.nav-item').forEach(b => {
        b.className = 'nav-item w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800/60 transition cursor-pointer';
        const svg = b.querySelector('svg');
        if (svg) svg.className = 'w-4 h-4 text-slate-400';
      });

      const activeBtn = document.querySelector(`.nav-item[data-tab="${targetTabId}"]`);
      if (activeBtn) {
        activeBtn.className = 'nav-item w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-medium text-white bg-emerald-600 shadow-sm transition cursor-pointer';
        const svg = activeBtn.querySelector('svg');
        if (svg) svg.className = 'w-4 h-4 text-white';
      }

      document.querySelectorAll('.tab-pane').forEach(p => p.classList.add('hidden'));
      const activePane = document.getElementById('tab-' + targetTabId);
      if (activePane) activePane.classList.remove('hidden');

      const titles = {
        'appeals': "Murojaatlar monitoringi",
        'services': "Xizmatlar va bo'limlar boshqaruvi",
        'policy': "Ta'lim shakli cheklovlari",
        'queue': "Darcha qabuli (elektron navbat)",
        'users': "Xodimlarni boshqarish va rollar biriktirish",
        'roles': "Rollar va Granulyar Huquqlar Matritsasi (PBAC)",
        'kpi': "Xodimlar KPI reytingi",
        'calendar': "Bayramlar taqvimi",
        'analytics': "Rahbariyat tahliliy infografikasi",
        'audit': "Tizim audit jurnali",
        'system': "Tizim salomatligi va zaxiralar",
        'announcements': "E'lonlar va xabarnomalar markazi"
      };
      const heading = document.getElementById('page-heading');
      if (heading && titles[tabId]) heading.innerText = titles[tabId];

      if (updateHash) {
        window.location.hash = '#' + tabId;
        localStorage.setItem('roffice_staff_tab', tabId);
      }

      closeSidebar();

      if (targetTabId === 'appeals') loadStaffAppeals();
      if (targetTabId === 'services') loadAllServicesAndDepts();
      if (targetTabId === 'queue') loadQueueAppointments();
      if (targetTabId === 'policy') loadEducationPolicy();
      if (targetTabId === 'users') {
        if (isRolesRequested) {
          if (typeof switchUsersSubTab === 'function') {
            switchUsersSubTab('roles');
          } else {
            setTimeout(() => { if (typeof switchUsersSubTab === 'function') switchUsersSubTab('roles'); }, 100);
          }
        } else {
          if (typeof switchUsersSubTab === 'function') {
            switchUsersSubTab('staff');
          } else {
            loadStaffUsers();
          }
        }
      }
      if (targetTabId === 'kpi') loadKPIOverview();
      if (targetTabId === 'calendar') loadHolidays();
      if (targetTabId === 'analytics') loadExecutiveAnalytics();
      if (targetTabId === 'audit') loadAuditLogs();
      if (targetTabId === 'system') {
        loadSystemMetrics();
        loadBackupsList();
      }
      if (targetTabId === 'announcements') loadStaffAnnouncements();
    }

    window.addEventListener('hashchange', () => {
      const h = window.location.hash.replace('#', '');
      if (h) switchStaffTab(h, false);
    });

    // 2. Real-time Audio Alerts & Live Badges Notification System
    let isAudioAlertEnabled = localStorage.getItem('roffice_audio_alert') !== 'false';
    let lastKnownAppealId = 0;
    let liveBadgesInterval = null;

    function initAudioAlertUI() {
      const icon = document.getElementById('sound-toggle-icon');
      const lbl = document.getElementById('sound-toggle-label');
      if (icon) icon.innerText = isAudioAlertEnabled ? '🔔' : '🔕';
      if (lbl) lbl.innerText = isAudioAlertEnabled ? 'Ovoz yoqiq' : 'Ovoz o\'chiq';
    }

    function toggleAudioAlerts() {
      isAudioAlertEnabled = !isAudioAlertEnabled;
      localStorage.setItem('roffice_audio_alert', isAudioAlertEnabled ? 'true' : 'false');
      initAudioAlertUI();
      if (isAudioAlertEnabled) {
        playNotificationChime();
        showToast("Ovozli bildirishnomalar yoqildi", "info");
      } else {
        showToast("Ovozli bildirishnomalar o'chirildi", "info");
      }
    }

    function playNotificationChime() {
      if (!isAudioAlertEnabled) return;
      try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (!AudioContext) return;
        const ctx = new AudioContext();

        // 3-tonli executive shaffof chime: C5 (523Hz), E5 (659Hz), G5 (784Hz)
        const notes = [
          { freq: 523.25, start: 0.0, dur: 0.25 },
          { freq: 659.25, start: 0.1, dur: 0.30 },
          { freq: 783.99, start: 0.2, dur: 0.45 }
        ];

        notes.forEach(n => {
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.type = 'sine';
          osc.frequency.setValueAtTime(n.freq, ctx.currentTime + n.start);

          gain.gain.setValueAtTime(0.001, ctx.currentTime + n.start);
          gain.gain.exponentialRampToValueAtTime(0.18, ctx.currentTime + n.start + 0.03);
          gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + n.start + n.dur);

          osc.connect(gain);
          gain.connect(ctx.destination);

          osc.start(ctx.currentTime + n.start);
          osc.stop(ctx.currentTime + n.start + n.dur + 0.05);
        });
      } catch (err) {
        console.warn("Audio chime failed:", err);
      }
    }

    function initNotifications() {
      const btn = document.getElementById('notification-btn');
      const ind = document.getElementById('notif-indicator');
      const lbl = document.getElementById('notif-label');

      if (!("Notification" in window)) {
        if (btn) btn.style.display = 'none';
        return;
      }

      if (Notification.permission === 'granted') {
        if (ind) ind.className = 'w-2 h-2 rounded-full bg-emerald-400';
        if (lbl) lbl.innerText = "Xabarlar faol";
      } else if (Notification.permission === 'denied') {
        if (ind) ind.className = 'w-2 h-2 rounded-full bg-rose-400';
        if (lbl) lbl.innerText = "Cheklangan";
      } else {
        if (ind) ind.className = 'w-2 h-2 rounded-full bg-amber-400 animate-pulse';
        if (lbl) lbl.innerText = "Yoqish";
      }
    }

    async function toggleBrowserNotifications() {
      if (!("Notification" in window)) {
        showToast("Sizning brauzeringiz bildirishnomalarni qo'llab-quvvatlamaydi.", "warning");
        return;
      }

      const permission = await Notification.requestPermission();
      initNotifications();

      if (permission === 'granted') {
        new Notification("Registrator ofisi axborot tizimi", {
          body: "Bildirishnomalar muvaffaqiyatli yoqildi. Yangi murojaatlar haqida sizga xabar beriladi.",
          icon: "/favicon.ico"
        });
      }
    }

    async function fetchLiveBadges() {
      if (!token) return;

      try {
        const resp = await fetch('/api/v1/appeals/live-badges', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!resp.ok) return;

        const data = await resp.json();

        // 1. Murojaatlar menyusi ko'rsatkichi (Badge)
        const appealsBadge = document.getElementById('badge-appeals-count');
        const appealsCount = (currentUser && currentUser.role === 'back_staff')
          ? (data.my_assigned || 0)
          : (data.new_appeals || 0);

        if (appealsBadge) {
          if (appealsCount > 0) {
            appealsBadge.innerText = appealsCount > 99 ? '99+' : appealsCount;
            appealsBadge.classList.remove('hidden');
          } else {
            appealsBadge.classList.add('hidden');
          }
        }

        // 2. Darcha qabuli ko'rsatkichi (Badge)
        const queueBadge = document.getElementById('badge-queue-count');
        const queueCount = data.today_waiting_appointments || 0;
        if (queueBadge) {
          if (queueCount > 0) {
            queueBadge.innerText = queueCount > 99 ? '99+' : queueCount;
            queueBadge.classList.remove('hidden');
          } else {
            queueBadge.classList.add('hidden');
          }
        }

        // 3. Shoshilinch SLA ogohlantirish belgisi
        const urgentPill = document.getElementById('header-urgent-pill');
        const urgentCount = document.getElementById('header-urgent-count');
        if (urgentPill && urgentCount) {
          if (data.urgent_sla_appeals > 0) {
            urgentCount.innerText = data.urgent_sla_appeals;
            urgentPill.classList.remove('hidden');
            urgentPill.classList.add('flex');
          } else {
            urgentPill.classList.add('hidden');
            urgentPill.classList.remove('flex');
          }
        }

        // 4. Yangi ariza kelib tushishini aniqlash va ogohlantirish
        if (lastKnownAppealId > 0 && data.last_appeal_id > lastKnownAppealId) {
          playNotificationChime();
          showToast("Yangi murojaat kelib tushdi!", "info");

          if (Notification.permission === 'granted') {
            new Notification("Registrator ofisi axborot tizimi", {
              body: "Yangi talaba murojaati qabul qilindi.",
              icon: "/favicon.ico"
            });
          }

          // Agar foydalanuvchi "Murojaatlar" oynasida tursa, ro'yxatni avtomatik yangilash
          const currentTab = localStorage.getItem('roffice_staff_tab') || 'appeals';
          if (currentTab === 'appeals') {
            loadStaffAppeals();
          }
        }

        lastKnownAppealId = data.last_appeal_id || lastKnownAppealId;

      } catch (err) {
        console.warn("Live badges fetch failed:", err);
      }
    }

    function startLiveBadgesPolling() {
      initAudioAlertUI();
      fetchLiveBadges();

      if (liveBadgesInterval) clearInterval(liveBadgesInterval);
      liveBadgesInterval = setInterval(fetchLiveBadges, 30000);

      // Aqlli fon rejimi: tabga qaytilgan paytda darhol yangilash
      document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
          fetchLiveBadges();
        }
      });
    }

    // 3. Current User and Role Info
    async function loadCurrentUserProfile() {
      try {
        let resp = await fetch('/api/v1/users/me', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!resp.ok) {
          resp = await fetch('/api/v1/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` }
          });
        }
        if (resp.status === 401) {
          handleLogout();
          return;
        }
        if (resp.ok) {
          currentUser = await resp.json();
          userRole = currentUser.role || 'staff';
          localStorage.setItem('roffice_role', userRole);

          const fullName = currentUser.full_name || localStorage.getItem('roffice_fullname') || currentUser.username || 'Administrator';
          let roleTitle = roleNameMap[currentUser.role] || 'Xodim';
          let deptTitle = 'Registrator ofisi';

          if (currentUser.role === 'admin') {
            roleTitle = 'Administrator';
            deptTitle = 'Bosh ma\'muriyat';
          } else if (currentUser.role === 'office_head') {
            roleTitle = 'Ofis rahbari';
            deptTitle = 'Registrator ofisi rahbariyati';
          } else if (currentUser.role === 'vice_rector') {
            roleTitle = 'Prorektor';
            deptTitle = 'O\'quv ishlari bo\'yicha prorektorat';
          } else if (currentUser.role === 'front_staff') {
            roleTitle = 'Front Office';
            deptTitle = 'Talabalarga xizmat ko\'rsatish sektori';
          } else if (currentUser.role === 'back_staff') {
            roleTitle = 'Back Office';
            deptTitle = 'Hujjatlar va tahlil sektori';
          }

          const fnEl = document.getElementById('header-user-fullname');
          if (fnEl) fnEl.innerText = fullName;
          const deptEl = document.getElementById('header-user-dept');
          if (deptEl) deptEl.innerText = deptTitle;

          const badgeEl = document.getElementById('current-role-badge');
          if (badgeEl) {
            badgeEl.innerText = roleTitle;
            badgeEl.className = `inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${roleBadgeColor[currentUser.role] || 'bg-slate-800 text-slate-300 border-slate-700'}`;
          }

          applyRolePermissions(currentUser.role);

          // Telegram holatini tekshirish
          const tgHeaderEl = document.getElementById('header-telegram-status');
          const tgBannerEl = document.getElementById('telegram-reminder-banner');

          if (currentUser.telegram_chat_id) {
            if (tgBannerEl) tgBannerEl.classList.add('hidden');
            if (tgHeaderEl) {
              const uName = currentUser.telegram_username ? `@${currentUser.telegram_username}` : 'Ulangan';
              tgHeaderEl.className = 'hidden md:inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border border-emerald-500/30 bg-emerald-500/10 text-emerald-400';
              tgHeaderEl.innerText = `✓ TG: ${uName}`;
            }
          } else {
            // Admin uchun banner ko'rsatilmaydi, faqat xodimlar uchun
            if (currentUser.role === 'admin') {
              if (tgBannerEl) tgBannerEl.classList.add('hidden');
            } else {
              try {
                const tgResp = await fetch('/api/v1/auth/telegram-info', {
                  headers: { 'Authorization': `Bearer ${token}` }
                });
                if (tgResp.ok) {
                  const tgInfo = await tgResp.json();
                  const connectBtn = document.getElementById('telegram-connect-btn');
                  if (connectBtn) connectBtn.href = tgInfo.deep_link;
                  if (tgHeaderEl) {
                    tgHeaderEl.innerHTML = `<a href="${tgInfo.deep_link}" target="_blank" class="text-blue-400 hover:underline">TG ulash</a>`;
                  }
                  if (tgBannerEl && !sessionStorage.getItem('roffice_dismiss_staff_tg')) {
                    tgBannerEl.classList.remove('hidden');
                  }
                }
              } catch (tge) {
                console.error("Telegram info yuklashda xatolik:", tge);
              }
            }
          }

          // Majburiy birinchi parolni o'zgartirish
          if (currentUser.must_change_password) {
            localStorage.setItem('roffice_must_change_password', 'true');
            openFirstLoginModal();
          } else {
            localStorage.setItem('roffice_must_change_password', 'false');
            closeFirstLoginModal(true);
          }
        }
      } catch (e) {
        console.error("Profil yuklash xatosi:", e);
      }
    }

    // === KO'ZCHA (PAROLNI KO'RSATISH/YASHIRISH) HELPERI ===
    function toggleFieldPassword(inputId, eyeOpenId, eyeSlashId) {
      const input = document.getElementById(inputId);
      const eyeOpen = document.getElementById(eyeOpenId);
      const eyeSlash = document.getElementById(eyeSlashId);
      if (!input) return;
      if (input.type === 'password') {
        input.type = 'text';
        if (eyeOpen) eyeOpen.classList.add('hidden');
        if (eyeSlash) eyeSlash.classList.remove('hidden');
      } else {
        input.type = 'password';
        if (eyeOpen) eyeOpen.classList.remove('hidden');
        if (eyeSlash) eyeSlash.classList.add('hidden');
      }
    }
    window.toggleFieldPassword = toggleFieldPassword;

    // === MAJBURIY BIRINCHI PAROLNI O'ZGARTIRISH (FIRST LOGIN PASSWORD CHANGE) ===
    function openFirstLoginModal() {
      const modal = document.getElementById('first-login-modal');
      if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        modal.style.display = 'flex';
      }
    }
    window.openFirstLoginModal = openFirstLoginModal;

    function closeFirstLoginModal(force = false) {
      if (!force && localStorage.getItem('roffice_must_change_password') === 'true') {
        // Ushbu oyna majburiy: yangi parol o'rnatilmaguncha yopib bo'lmaydi
        return;
      }
      const modal = document.getElementById('first-login-modal');
      if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
        modal.style.display = 'none';
      }
    }
    window.closeFirstLoginModal = closeFirstLoginModal;

    // ESC tugmasi orqali modalni yopilishidan himoya qilish
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && localStorage.getItem('roffice_must_change_password') === 'true') {
        e.preventDefault();
        e.stopPropagation();
      }
    }, true);

    async function handleFirstLoginPasswordChange(e) {
      if (e) e.preventDefault();
      const cur = document.getElementById('fl-current-password')?.value || '';
      const newU = document.getElementById('fl-new-username')?.value.trim() || null;
      const newP = document.getElementById('fl-new-password')?.value || '';
      const conf = document.getElementById('fl-confirm-password')?.value || '';
      const alertBox = document.getElementById('first-login-alert');
      const submitBtn = document.getElementById('fl-submit-btn');

      if (!cur) {
        if (alertBox) {
          alertBox.className = 'p-3 rounded-xl text-xs font-medium border bg-rose-500/10 border-rose-500/30 text-rose-400 block';
          alertBox.innerText = "Amaldagi bir martalik parolni kiriting.";
        }
        return;
      }

      if (newP !== conf) {
        if (alertBox) {
          alertBox.className = 'p-3 rounded-xl text-xs font-medium border bg-rose-500/10 border-rose-500/30 text-rose-400 block';
          alertBox.innerText = "Yangi parol va tasdiqlovchi parol bir-biriga mos kelmadi.";
        }
        return;
      }

      if (newP.length < 6) {
        if (alertBox) {
          alertBox.className = 'p-3 rounded-xl text-xs font-medium border bg-rose-500/10 border-rose-500/30 text-rose-400 block';
          alertBox.innerText = "Yangi parol kamida 6 ta belgidan iborat bo'lishi shart.";
        }
        return;
      }

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerText = "Saqlanmoqda...";
      }

      try {
        const curToken = (typeof token !== 'undefined' && token) ? token : localStorage.getItem('roffice_token');
        const resp = await fetch('/api/v1/users/me/credentials', {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${curToken}`
          },
          body: JSON.stringify({
            current_password: cur,
            new_username: newU,
            new_password: newP
          })
        });
        const data = await resp.json();
        if (resp.ok) {
          if (data.access_token) {
            token = data.access_token;
            localStorage.setItem('roffice_token', token);
          }
          localStorage.setItem('roffice_must_change_password', 'false');
          closeFirstLoginModal(true);
          showToast("Parolingiz muvaffaqiyatli o'zgartirildi. Tizimga xush kelibsiz!", "success");
          await loadCurrentUserProfile();
        } else {
          if (alertBox) {
            alertBox.className = 'p-3 rounded-xl text-xs font-medium border bg-rose-500/10 border-rose-500/30 text-rose-400 block';
            alertBox.innerText = data.detail || "Parolni o'zgartirishda xatolik yuz berdi.";
          }
        }
      } catch (err) {
        if (alertBox) {
          alertBox.className = 'p-3 rounded-xl text-xs font-medium border bg-rose-500/10 border-rose-500/30 text-rose-400 block';
          alertBox.innerText = "Server bilan aloqa o'rnatib bo'lmadi.";
        }
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerText = "Parolni saqlash va tizimga o'tish";
        }
      }
    }
    window.handleFirstLoginPasswordChange = handleFirstLoginPasswordChange;

    // Sahifa ochilishi bilanoq darhol tekshirish
    if (localStorage.getItem('roffice_must_change_password') === 'true') {
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => openFirstLoginModal());
      } else {
        openFirstLoginModal();
      }
    }

    function dismissTelegramReminder() {
      sessionStorage.setItem('roffice_dismiss_staff_tg', 'true');
      const b = document.getElementById('telegram-reminder-banner');
      if (b) b.classList.add('hidden');
    }

    // === PBAC: FOYDALANUVCHIDA HUQUQ MAVJUDLIGINI TEKSHIRISH ===
    function hasPerm(permCode) {
      if (!currentUser) return false;
      if (currentUser.role === 'admin') return true;
      const perms = currentUser.effective_permissions || [];
      if (perms.includes('*')) return true;
      return perms.includes(permCode);
    }
    window.hasPerm = hasPerm;

    function applyRolePermissions(role) {
      const appealsBtn = document.getElementById('nav-appeals-btn');
      const servicesBtn = document.getElementById('nav-services-btn');
      const policyBtn = document.getElementById('nav-policy-btn');
      const queueBtn = document.getElementById('nav-queue-btn');
      const usersBtn = document.getElementById('nav-users-btn');
      const kpiBtn = document.getElementById('nav-kpi-btn');
      const analyticsBtn = document.getElementById('nav-analytics-btn');
      const calendarBtn = document.getElementById('nav-calendar-btn');
      const auditBtn = document.getElementById('nav-audit-btn');
      const announcementsBtn = document.getElementById('nav-announcements-btn');
      const systemBtn = document.getElementById('nav-system-btn');
      const backupBtn = document.getElementById('btn-trigger-backup');
      const addServiceBtn = document.getElementById('add-service-btn');
      const addDeptBtn = document.getElementById('add-dept-btn');
      const rolesSubtabBtn = document.getElementById('subtab-users-roles-btn');

      // 1. Murojaatlar - barcha xodimlar uchun ochiq
      if (appealsBtn) appealsBtn.style.display = 'flex';

      // 2. Xizmatlar va bo'limlar katalogi
      const canViewServices = hasPerm('services:view') || hasPerm('services:manage');
      if (servicesBtn) servicesBtn.style.display = canViewServices ? 'flex' : 'none';
      const canManageServices = hasPerm('services:manage');
      if (addServiceBtn) {
        addServiceBtn.style.display = canManageServices ? 'inline-flex' : 'none';
        if (!canManageServices) addServiceBtn.classList.add('hidden');
        else addServiceBtn.classList.remove('hidden');
      }
      if (addDeptBtn) {
        addDeptBtn.style.display = canManageServices ? 'inline-flex' : 'none';
        if (!canManageServices) addDeptBtn.classList.add('hidden');
        else addDeptBtn.classList.remove('hidden');
      }

      // 3. Ta'lim shakli cheklovlari
      const canManagePolicy = hasPerm('services:manage') || role === 'office_head';
      if (policyBtn) policyBtn.style.display = canManagePolicy ? 'flex' : 'none';

      // 4. Darcha qabuli (elektron navbat)
      const canAccessQueue = hasPerm('queue:call') || hasPerm('queue:complete') || hasPerm('queue:manage_windows') || hasPerm('queue:view_board');
      if (queueBtn) queueBtn.style.display = canAccessQueue ? 'flex' : 'none';

      // 5. Xodimlar tarkibi va rollar
      const canViewUsers = hasPerm('users:view') || hasPerm('users:create') || hasPerm('users:edit') || hasPerm('roles:manage');
      if (usersBtn) usersBtn.style.display = canViewUsers ? 'flex' : 'none';
      const canManageRoles = hasPerm('roles:manage');
      if (rolesSubtabBtn) rolesSubtabBtn.style.display = canManageRoles ? 'inline-block' : 'none';

      // 6. Xodimlar KPI reytingi
      if (kpiBtn) kpiBtn.style.display = 'flex';

      // 7. Rahbariyat tahliliy infografikasi
      const canViewAnalytics = hasPerm('analytics:view');
      if (analyticsBtn) analyticsBtn.style.display = canViewAnalytics ? 'flex' : 'none';

      // 8. Bayramlar taqvimi
      const canManageCalendar = hasPerm('calendar:manage') || ['admin', 'office_head', 'vice_rector'].includes(role);
      if (calendarBtn) calendarBtn.style.display = canManageCalendar ? 'flex' : 'none';

      // 9. Tizim audit jurnali
      const canViewAudit = hasPerm('audit:view');
      if (auditBtn) auditBtn.style.display = canViewAudit ? 'flex' : 'none';

      // 10. E'lonlar markazi
      if (announcementsBtn) announcementsBtn.style.display = 'flex';

      // 11. Tizim salomatligi va zaxiralar (Faqat tizim admini yoki system:* huquqlari borlar)
      const canAccessSystem = hasPerm('system:metrics') || hasPerm('system:backups_manage') || role === 'admin';
      if (systemBtn) systemBtn.style.display = canAccessSystem ? 'flex' : 'none';
      if (backupBtn) backupBtn.style.display = (hasPerm('system:backups_manage') || role === 'admin') ? 'inline-flex' : 'none';
    }

    function handleLogout(reason = null) {
      localStorage.removeItem('roffice_token');
      localStorage.removeItem('roffice_role');
      localStorage.removeItem('roffice_fullname');
      localStorage.removeItem('roffice_user_id');
      localStorage.removeItem('roffice_must_change_password');
      const target = reason ? pageUrl(`/login?reason=${encodeURIComponent(reason)}`) : pageUrl('/login');
      window.location.href = target;
    }

    // === 30 DAQIQALIK HARAKATSIZLIK BO'YICHA AVTOMATIK LOGOUT TIZIMI ===
    const IDLE_TIMEOUT_MS = 30 * 60 * 1000; // 30 daqiqa
    const WARNING_TIME_MS = 28 * 60 * 1000; // 28 daqiqa (yopilishdan 2 daqiqa oldin ogohlantirish)
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

    // 4. TAB: SERVICES & DEPARTMENTS FULL CRUD
    let allServicesList = [];
    let allDepartmentsList = [];
