let token = localStorage.getItem('roffice_token');
    let userRole = localStorage.getItem('roffice_role') || "office_head";
    let currentUser = null;
    let currentPolicy = null;
    let departmentsList = [];
    let nizomDutiesCatalog = [];

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

    // 1. Core Tab Router with URL Hash and LocalStorage Persistence
    function switchStaffTab(tabId, updateHash = true) {
      document.querySelectorAll('.nav-item').forEach(b => {
        b.className = 'nav-item w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800/60 transition cursor-pointer';
        const svg = b.querySelector('svg');
        if (svg) svg.className = 'w-4 h-4 text-slate-400';
      });

      const activeBtn = document.querySelector(`.nav-item[data-tab="${tabId}"]`);
      if (activeBtn) {
        activeBtn.className = 'nav-item w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-medium text-white bg-emerald-600 shadow-sm transition cursor-pointer';
        const svg = activeBtn.querySelector('svg');
        if (svg) svg.className = 'w-4 h-4 text-white';
      }

      document.querySelectorAll('.tab-pane').forEach(p => p.classList.add('hidden'));
      const activePane = document.getElementById('tab-' + tabId);
      if (activePane) activePane.classList.remove('hidden');

      const titles = {
        'appeals': "Murojaatlar monitoringi",
        'services': "Xizmatlar va bo'limlar boshqaruvi",
        'policy': "Ta'lim shakli cheklovlari",
        'queue': "Darcha qabuli (elektron navbat)",
        'users': "Xodimlarni boshqarish va rollar biriktirish",
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

      if (tabId === 'appeals') loadStaffAppeals();
      if (tabId === 'services') loadAllServicesAndDepts();
      if (tabId === 'queue') loadQueueAppointments();
      if (tabId === 'policy') loadEducationPolicy();
      if (tabId === 'users') loadStaffUsers();
      if (tabId === 'kpi') loadKPIOverview();
      if (tabId === 'calendar') loadHolidays();
      if (tabId === 'analytics') loadExecutiveAnalytics();
      if (tabId === 'audit') loadAuditLogs();
      if (tabId === 'system') {
        loadSystemMetrics();
        loadBackupsList();
      }
      if (tabId === 'announcements') loadStaffAnnouncements();
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
            openFirstLoginModal();
          }
        }
      } catch (e) {
        console.error("Profil yuklash xatosi:", e);
      }
    }

    function dismissTelegramReminder() {
      sessionStorage.setItem('roffice_dismiss_staff_tg', 'true');
      const b = document.getElementById('telegram-reminder-banner');
      if (b) b.classList.add('hidden');
    }

    function applyRolePermissions(role) {
      const policyBtn = document.getElementById('nav-policy-btn');
      const kpiBtn = document.getElementById('nav-kpi-btn');
      const calendarBtn = document.getElementById('nav-calendar-btn');
      const queueBtn = document.getElementById('nav-queue-btn');
      const usersBtn = document.getElementById('nav-users-btn');
      const analyticsBtn = document.getElementById('nav-analytics-btn');
      const auditBtn = document.getElementById('nav-audit-btn');
      const systemBtn = document.getElementById('nav-system-btn');
      const backupBtn = document.getElementById('btn-trigger-backup');
      const addServiceBtn = document.getElementById('add-service-btn');
      const addDeptBtn = document.getElementById('add-dept-btn');

      if (role === 'front_staff') {
        if (policyBtn) policyBtn.style.display = 'none';
        if (kpiBtn) kpiBtn.style.display = 'flex';
        if (calendarBtn) calendarBtn.style.display = 'none';
        if (queueBtn) queueBtn.style.display = 'flex';
        if (usersBtn) usersBtn.style.display = 'none';
        if (analyticsBtn) analyticsBtn.style.display = 'none';
        if (auditBtn) auditBtn.style.display = 'none';
        if (systemBtn) systemBtn.style.display = 'none';
        if (addServiceBtn) { addServiceBtn.classList.add('hidden'); addServiceBtn.style.display = 'none'; }
        if (addDeptBtn) { addDeptBtn.classList.add('hidden'); addDeptBtn.style.display = 'none'; }
      } else if (role === 'back_staff') {
        if (policyBtn) policyBtn.style.display = 'none';
        if (kpiBtn) kpiBtn.style.display = 'flex';
        if (calendarBtn) calendarBtn.style.display = 'none';
        if (queueBtn) queueBtn.style.display = 'none';
        if (usersBtn) usersBtn.style.display = 'none';
        if (analyticsBtn) analyticsBtn.style.display = 'none';
        if (auditBtn) auditBtn.style.display = 'none';
        if (systemBtn) systemBtn.style.display = 'none';
        if (addServiceBtn) { addServiceBtn.classList.add('hidden'); addServiceBtn.style.display = 'none'; }
        if (addDeptBtn) { addDeptBtn.classList.add('hidden'); addDeptBtn.style.display = 'none'; }
      } else if (role === 'vice_rector') {
        if (policyBtn) policyBtn.style.display = 'none';
        if (kpiBtn) kpiBtn.style.display = 'flex';
        if (calendarBtn) calendarBtn.style.display = 'flex';
        if (queueBtn) queueBtn.style.display = 'none';
        if (usersBtn) usersBtn.style.display = 'none';
        if (analyticsBtn) analyticsBtn.style.display = 'flex';
        if (auditBtn) auditBtn.style.display = 'flex';
        if (systemBtn) systemBtn.style.display = 'none';
        if (addServiceBtn) { addServiceBtn.classList.add('hidden'); addServiceBtn.style.display = 'none'; }
        if (addDeptBtn) { addDeptBtn.classList.add('hidden'); addDeptBtn.style.display = 'none'; }
      } else if (role === 'office_head') {
        // Registrator ofisi boshlig'i
        if (policyBtn) policyBtn.style.display = 'flex';
        if (kpiBtn) kpiBtn.style.display = 'flex';
        if (calendarBtn) calendarBtn.style.display = 'flex';
        if (queueBtn) queueBtn.style.display = 'none';
        if (usersBtn) usersBtn.style.display = 'flex';
        if (analyticsBtn) analyticsBtn.style.display = 'flex';
        if (auditBtn) auditBtn.style.display = 'flex';
        if (systemBtn) systemBtn.style.display = 'flex';
        if (backupBtn) backupBtn.style.display = 'none'; // Boshliq faqat ko'radi, zaxira olmaydi
        if (addServiceBtn) { addServiceBtn.classList.remove('hidden'); addServiceBtn.style.display = 'inline-flex'; }
        if (addDeptBtn) { addDeptBtn.classList.remove('hidden'); addDeptBtn.style.display = 'inline-flex'; }
      } else {
        // Tizim administratori (admin)
        if (policyBtn) policyBtn.style.display = 'flex';
        if (kpiBtn) kpiBtn.style.display = 'flex';
        if (calendarBtn) calendarBtn.style.display = 'flex';
        if (queueBtn) queueBtn.style.display = 'none';
        if (usersBtn) usersBtn.style.display = 'flex';
        if (analyticsBtn) analyticsBtn.style.display = 'flex';
        if (auditBtn) auditBtn.style.display = 'flex';
        if (systemBtn) systemBtn.style.display = 'flex';
        if (backupBtn) backupBtn.style.display = 'inline-flex';
        if (addServiceBtn) { addServiceBtn.classList.remove('hidden'); addServiceBtn.style.display = 'inline-flex'; }
        if (addDeptBtn) { addDeptBtn.classList.remove('hidden'); addDeptBtn.style.display = 'inline-flex'; }
      }
    }

    function handleLogout() {
      localStorage.removeItem('roffice_token');
      localStorage.removeItem('roffice_role');
      localStorage.removeItem('roffice_fullname');
      localStorage.removeItem('roffice_user_id');
      localStorage.removeItem('roffice_must_change_password');
      window.location.href = pageUrl('/login');
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
