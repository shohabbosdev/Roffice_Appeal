let currentAnalyticsAnnId = null;

    async function loadStaffAnnouncements() {
      const token = localStorage.getItem('roffice_token');
      if (!token) return;

      const container = document.getElementById('staff-announcements-list');
      if (!container) return;

      try {
        const res = await fetch(apiUrl('/api/v1/announcements'), {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) {
          container.innerHTML = '<div class="p-6 text-center text-rose-400 text-xs bg-slate-900/40 rounded-2xl border border-slate-800">E\'lonlarni yuklashda xatolik yuz berdi</div>';
          return;
        }

        const list = await res.json();
        const badge = document.getElementById('announcements-total-badge');
        if (badge) badge.innerText = `Jami: ${list.length} ta e'lon`;

        if (!list || list.length === 0) {
          container.innerHTML = `
            <div class="p-12 text-center text-slate-500 bg-slate-900/40 rounded-2xl border border-slate-800 space-y-3">
              <div class="w-12 h-12 rounded-2xl bg-slate-800/80 text-slate-400 flex items-center justify-center mx-auto text-xl">
                📢
              </div>
              <p class="text-sm font-semibold text-slate-300">Hozircha hech qanday e'lon chiqarilmagan</p>
              <p class="text-xs text-slate-500">Talabalar uchun yangi e'lon yoki ogohlantirish yaratish uchun yuqoridagi tugmani bosing</p>
            </div>
          `;
          return;
        }

        container.innerHTML = list.map(a => {
          let prioStyle = "border-blue-500/30 bg-blue-950/20";
          let prioBadge = "bg-blue-500/15 text-blue-400 border-blue-500/30";
          let prioName = "Oddiy";
          if (a.priority === 'urgent') {
            prioStyle = "border-rose-500/30 bg-rose-950/20";
            prioBadge = "bg-rose-500/15 text-rose-400 border-rose-500/30";
            prioName = "Shoshilinch";
          } else if (a.priority === 'important') {
            prioStyle = "border-amber-500/30 bg-amber-950/20";
            prioBadge = "bg-amber-500/15 text-amber-400 border-amber-500/30";
            prioName = "Muhim";
          }

          const targetForm = a.target_education_form || "Barchasi";
          const targetFac = a.target_faculty || "Barcha fakultetlar";
          const targetCrs = a.target_course ? `${a.target_course}-kurs` : "Barcha kurslar";

          const escTitle = (a.title || '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
          const escContent = (a.content || '').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br/>');
          const authorName = a.author ? a.author.full_name : "Xodim";

          return `
            <div class="p-5 rounded-2xl border ${prioStyle} bg-slate-900/70 shadow-lg space-y-3">
              <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                <div class="flex items-center gap-2.5">
                  <span class="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${prioBadge}">
                    ${prioName}
                  </span>
                  <h4 class="text-sm font-bold text-white tracking-tight">${escTitle}</h4>
                </div>
                <div class="flex items-center gap-3 text-xs text-slate-400">
                  <span>Muallif: <b class="text-slate-200">${authorName}</b></span>
                  <span>•</span>
                  <span>${formatDateOnly(a.created_at)}</span>
                </div>
              </div>

              <div class="text-xs text-slate-300 leading-relaxed">
                ${escContent}
              </div>

              <!-- Target audience badges -->
              <div class="flex flex-wrap items-center gap-2 pt-1 text-[11px] text-slate-400">
                <span class="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 flex items-center gap-1.5">
                  <span class="text-slate-500">Ta'lim shakli:</span> <b class="text-sky-400">${targetForm}</b>
                </span>
                <span class="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 flex items-center gap-1.5">
                  <span class="text-slate-500">Fakultet:</span> <b class="text-indigo-400">${targetFac}</b>
                </span>
                <span class="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 flex items-center gap-1.5">
                  <span class="text-slate-500">Kurs:</span> <b class="text-purple-400">${targetCrs}</b>
                </span>
                ${a.requires_ack ? `
                  <span class="px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 font-semibold">
                    ✓ Tasdiqlash talab etiladi
                  </span>
                ` : ''}
              </div>

              <!-- Actions -->
              <div class="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-800">
                <button
                  onclick="openAnnouncementAnalytics(${a.id})"
                  class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-blue-600/15 hover:bg-blue-600/25 border border-blue-500/30 text-blue-300 text-xs font-semibold transition cursor-pointer"
                >
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
                  <span>O'qilganlik hisoboti & O'qimaganlar</span>
                </button>
                <button
                  onclick="deleteAnnouncement(${a.id})"
                  class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/25 text-rose-400 text-xs font-medium transition cursor-pointer"
                  title="E'lonni bekor qilish"
                >
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                  <span>O'chirish</span>
                </button>
              </div>
            </div>
          `;
        }).join('');

      } catch (err) {
        console.error("loadStaffAnnouncements xatosi:", err);
      }
    }

    async function openCreateAnnouncementModal() {
      // Fakultetlar selectini to'ldirish
      const facSelect = document.getElementById('ann-faculty-select');
      if (facSelect && facSelect.options.length <= 1) {
        try {
          const res = await fetch(apiUrl('/api/v1/auth/faculties'));
          if (res.ok) {
            const facs = await res.json();
            facs.forEach(f => {
              const opt = document.createElement('option');
              opt.value = f;
              opt.innerText = f;
              facSelect.appendChild(opt);
            });
          }
        } catch (e) { }
      }

      document.getElementById('ann-title-input').value = "";
      document.getElementById('ann-content-input').value = "";
      document.getElementById('ann-priority-select').value = "normal";
      document.getElementById('ann-edu-form-select').value = "ALL";
      document.getElementById('ann-course-select').value = "0";
      document.getElementById('ann-requires-ack-check').checked = false;
      document.getElementById('ann-send-telegram-check').checked = true;

      document.getElementById('modal-create-announcement').classList.remove('hidden');
    }

    function closeCreateAnnouncementModal() {
      document.getElementById('modal-create-announcement').classList.add('hidden');
    }

    async function submitCreateAnnouncement() {
      const token = localStorage.getItem('roffice_token');
      if (!token) return;

      const title = document.getElementById('ann-title-input').value.trim();
      const content = document.getElementById('ann-content-input').value.trim();
      const priority = document.getElementById('ann-priority-select').value;
      const eduForm = document.getElementById('ann-edu-form-select').value;
      const faculty = document.getElementById('ann-faculty-select').value;
      const courseVal = parseInt(document.getElementById('ann-course-select').value, 10);
      const requiresAck = document.getElementById('ann-requires-ack-check').checked;
      const sendTelegram = document.getElementById('ann-send-telegram-check').checked;

      if (!title || !content) {
        showToast("Iltimos, e'lon sarlavhasi va matnini to'liq kiriting", "warning");
        return;
      }

      const btn = document.getElementById('btn-submit-announcement');
      btn.disabled = true;
      btn.innerHTML = '<span class="animate-spin">⌛</span> Chiqarilmoqda...';

      try {
        const payload = {
          title: title,
          content: content,
          priority: priority,
          target_education_form: eduForm === "ALL" ? null : eduForm,
          target_faculty: faculty === "ALL" ? null : faculty,
          target_course: courseVal === 0 ? null : courseVal,
          requires_ack: requiresAck,
          send_telegram: sendTelegram
        };

        const res = await fetch(apiUrl('/api/v1/announcements'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || "E'lon yaratishda xatolik yuz berdi");
        }

        showToast("E'lon muvaffaqiyatli chiqarildi va talabalarga yo'naltirildi!", "success");
        closeCreateAnnouncementModal();
        await loadStaffAnnouncements();
      } catch (err) {
        showToast(err.message, "error");
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>E\'lonni chiqarish</span>';
      }
    }

    async function openAnnouncementAnalytics(annId) {
      const token = localStorage.getItem('roffice_token');
      if (!token) return;

      currentAnalyticsAnnId = annId;
      const modal = document.getElementById('modal-announcement-analytics');
      modal.classList.remove('hidden');

      document.getElementById('ana-modal-title').innerText = "Hisobot yuklanmoqda...";
      document.getElementById('ana-unread-table-body').innerHTML = '<tr><td colspan="4" class="p-6 text-center text-slate-500">Yuklanmoqda...</td></tr>';

      try {
        const res = await fetch(apiUrl(`/api/v1/announcements/${annId}/analytics`), {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error("Hisobotni yuklab bo'lmadi");
        const data = await res.json();

        const ann = data.announcement;
        document.getElementById('ana-modal-title').innerText = `"${ann.title}" e'loni monitoringi`;
        document.getElementById('ana-modal-sub').innerText = `Chiqarilgan sana: ${formatDateTime(ann.created_at)}`;

        document.getElementById('ana-total-students').innerText = data.total_target_students + " nafar";
        document.getElementById('ana-read-count').innerText = data.read_count + " nafar";
        document.getElementById('ana-read-pct').innerText = data.read_percentage + "%";
        document.getElementById('ana-ack-count').innerText = data.acknowledged_count + " nafar";

        document.getElementById('ana-progress-bar').style.width = `${Math.min(100, data.read_percentage)}%`;
        document.getElementById('ana-unread-count-badge').innerText = data.unread_students.length;

        const tbody = document.getElementById('ana-unread-table-body');
        if (!data.unread_students || data.unread_students.length === 0) {
          tbody.innerHTML = '<tr><td colspan="4" class="p-6 text-center text-emerald-400 font-semibold">Barcha maqsadli talabalar ushbu e\'lonni o\'qib bo\'lgan! 🎉</td></tr>';
          return;
        }

        tbody.innerHTML = data.unread_students.map(st => `
          <tr class="hover:bg-slate-900/60 transition">
            <td class="p-2.5 font-medium text-white">${escapeHtml(st.full_name)}</td>
            <td class="p-2.5 text-slate-300 font-mono">${escapeHtml(st.group_name)} (${st.course}-kurs)</td>
            <td class="p-2.5 text-slate-400">${escapeHtml(st.education_form)}</td>
            <td class="p-2.5 text-slate-300 font-mono">${escapeHtml(st.phone)}</td>
          </tr>
        `).join('');

      } catch (err) {
        showToast(err.message, "error");
      }
    }

    function closeAnnouncementAnalyticsModal() {
      document.getElementById('modal-announcement-analytics').classList.add('hidden');
      currentAnalyticsAnnId = null;
    }

    function exportUnreadStudentsCsv() {
      if (!currentAnalyticsAnnId) return;
      const token = localStorage.getItem('roffice_token');
      window.location.href = apiUrl(`/api/v1/announcements/${currentAnalyticsAnnId}/unread-export?token=${encodeURIComponent(token || '')}`);
    }

    async function deleteAnnouncement(annId) {
      if (!confirm("Haqiqatan ham ushbu e'lonni bekor qilmoqchimisiz?")) return;
      const token = localStorage.getItem('roffice_token');
      if (!token) return;

      try {
        const res = await fetch(apiUrl(`/api/v1/announcements/${annId}`), {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error("E'lonni o'chirib bo'lmadi");
        showToast("E'lon muvaffaqiyatli bekor qilindi", "success");
        await loadStaffAnnouncements();
      } catch (err) {
        showToast(err.message, "error");
      }
    }

    // 19. Page Initialization with Hash Recovery
    window.addEventListener('DOMContentLoaded', async () => {
      initNotifications();
      await loadCurrentUserProfile();
      startLiveBadgesPolling();

      // Determine initial tab from hash or localStorage
      const hashTab = window.location.hash.replace('#', '');
      const savedTab = localStorage.getItem('roffice_staff_tab');
      const initialTab = hashTab || savedTab || 'appeals';

      switchStaffTab(initialTab, false);
    });
