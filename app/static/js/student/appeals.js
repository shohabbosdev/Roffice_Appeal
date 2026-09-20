let allStudentAppeals = [];
let currentStudentStatusFilter = 'all';

function setStudentAppealsStatusFilter(status) {
  currentStudentStatusFilter = status;
  document.querySelectorAll('.student-status-tab').forEach(tab => {
    const f = tab.getAttribute('data-filter');
    if (f === status) {
      tab.className = 'student-status-tab px-3 py-1 rounded-lg bg-blue-600 text-white font-semibold transition cursor-pointer whitespace-nowrap shadow-sm shadow-blue-600/30';
    } else {
      tab.className = 'student-status-tab px-3 py-1 rounded-lg bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800 transition cursor-pointer whitespace-nowrap';
    }
  });
  applyStudentAppealsFilter();
}

function applyStudentAppealsFilter() {
  const searchInput = document.getElementById('student-appeal-search');
  const query = (searchInput ? searchInput.value : '').toLowerCase().trim();
  const countEl = document.getElementById('student-appeals-filtered-count');

  let filtered = allStudentAppeals;

  // Status filter
  if (currentStudentStatusFilter === 'in_progress') {
    filtered = filtered.filter(a => a.status === 'submitted' || a.status === 'in_progress');
  } else if (currentStudentStatusFilter === 'resolved') {
    filtered = filtered.filter(a => a.status === 'resolved');
  } else if (currentStudentStatusFilter === 'completed') {
    filtered = filtered.filter(a => a.status === 'completed');
  } else if (currentStudentStatusFilter === 'disputed') {
    filtered = filtered.filter(a => a.status === 'disputed' || a.status === 'escalated_head' || a.status === 'escalated_prorektor');
  }

  // Live search filter
  if (query) {
    filtered = filtered.filter(a => {
      const tCode = (a.ticket_number || '').toLowerCase();
      const subj = (a.subject || '').toLowerCase();
      const sTitle = (a.service?.title || '').toLowerCase();
      const msg = (a.message || '').toLowerCase();
      return tCode.includes(query) || subj.includes(query) || sTitle.includes(query) || msg.includes(query);
    });
  }

  if (countEl) countEl.innerText = filtered.length;
  renderStudentAppealsList(filtered);
}

function renderStudentAppealsList(data) {
  const list = document.getElementById('student-appeals-list');
  if (!list) return;

  if (!data || data.length === 0) {
    list.innerHTML = '<div class="p-8 text-center text-xs text-slate-500 border border-slate-800/80 rounded-2xl bg-slate-900/40">Mos keluvchi murojaatlar topilmadi.</div>';
    return;
  }

  list.innerHTML = '';
  data.forEach(app => {
    let statusBadge = 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    let statusLabel = "Ko'rib chiqilmoqda";
    
    if (app.status === 'completed') {
      statusBadge = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      statusLabel = "Bajarildi (yakunlandi)";
    } else if (app.status === 'resolved') {
      statusBadge = 'bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse';
      statusLabel = "Javob berildi (tasdiqlash kutilmoqda)";
    } else if (app.status === 'disputed') {
      statusBadge = 'bg-rose-500/10 text-rose-400 border-rose-500/20';
      statusLabel = "E'tiroz bildirildi (Boshliq nazoratida)";
    } else if (app.status === 'escalated_head') {
      statusBadge = 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      statusLabel = "Ofis boshlig'i tomonidan ko'rib chiqilmoqda";
    } else if (app.status === 'escalated_prorektor') {
      statusBadge = 'bg-rose-500/15 text-rose-300 border-rose-500/30';
      statusLabel = "Prorektor nazoratida (3-bosqich)";
    }

    let ratingStarsHtml = '';
    if (app.rating) {
      const stars = '★'.repeat(app.rating) + '☆'.repeat(5 - app.rating);
      ratingStarsHtml = `
        <div class="mt-2.5 p-3 rounded-xl bg-slate-950/60 border border-slate-800/70 flex items-center justify-between gap-2 flex-wrap">
          <div class="flex items-center gap-1.5 text-xs text-slate-300">
            <span class="text-amber-400 font-bold tracking-widest">${stars}</span>
            <span class="font-semibold text-slate-200">(${app.rating}/5 ball)</span>
          </div>
          ${app.rating_comment ? `<span class="text-xs text-slate-400 italic">"${app.rating_comment}"</span>` : ''}
        </div>
      `;
    }

    list.innerHTML += `
      <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-3 hover:border-slate-700/80 transition">
        <div class="flex items-center justify-between flex-wrap gap-2">
          <div class="flex items-center gap-2">
            <span class="font-mono text-xs font-bold text-blue-400 bg-blue-950/40 px-2 py-0.5 rounded-lg border border-blue-800/40">#${app.ticket_number}</span>
            <span class="text-[11px] text-slate-400 font-mono">${app.created_at ? formatDateTime(app.created_at) : ''}</span>
          </div>
          <span class="px-2.5 py-0.5 rounded-full text-[11px] font-medium border ${statusBadge}">${statusLabel}</span>
        </div>

        <div>
          <h4 class="text-sm font-semibold text-white tracking-tight">${app.subject}</h4>
          <p class="text-xs text-slate-400 mt-0.5">${app.service ? app.service.title : 'Umumiy xizmat'}</p>
        </div>

        <p class="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/60">${app.message}</p>
        
        ${app.attachment_urls ? `
          <div class="pt-1">
            <a href="${app.attachment_urls}" target="_blank" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-blue-500/30 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 text-xs font-medium transition">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
              <span>Ilova qilingan hujjatni ko'rish</span>
            </a>
          </div>
        ` : ''}

        ${app.resolution_text ? `
          <div class="p-3.5 bg-emerald-500/5 border border-emerald-500/20 rounded-xl space-y-2">
            <span class="text-[11px] font-bold text-emerald-400 uppercase tracking-wider">Xizmat ijrosi natijasi:</span>
            <p class="text-xs text-slate-200 leading-relaxed">${app.resolution_text}</p>
            ${app.result_file_url ? `
              <div class="pt-1 flex flex-wrap items-center gap-2">
                <a href="${apiUrl(app.result_file_url)}" target="_blank" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-emerald-500/40 bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 text-xs font-medium transition">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                  <span>Rasmiy PDF ma'lumotnoma</span>
                </a>
                ${app.qr_hash ? `
                  <a href="${apiUrl('/verify/' + app.qr_hash)}" target="_blank" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-blue-500/40 bg-blue-500/15 hover:bg-blue-500/25 text-blue-300 text-xs font-medium transition">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M4 8h16M4 16h4m4 0h4"/></svg>
                    <span>QR-kod verifikatsiyasi</span>
                  </a>
                ` : ''}
              </div>
            ` : ''}
          </div>
        ` : ''}

        ${ratingStarsHtml}

        <div class="flex items-center justify-between flex-wrap gap-2 pt-2.5 border-t border-slate-800/80">
          <div class="flex items-center gap-2 flex-wrap">
            <button type="button" onclick="openAppealTracker(${app.id})" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-indigo-500/30 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 text-xs font-medium transition cursor-pointer">
              <svg class="w-3.5 h-3.5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
              <span>📍 Bosqichlar va kutish vaqti</span>
            </button>

            ${app.status === 'new' ? `
              <button type="button" onclick="cancelStudentAppeal(${app.id})" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 text-xs font-medium transition cursor-pointer">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                <span>Bekor qilish</span>
              </button>
            ` : ''}
          </div>

          ${app.status === 'resolved' ? `
            <div class="flex items-center gap-2">
              <button type="button" onclick="openRatingModal(${app.id})" class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition cursor-pointer shadow-md shadow-emerald-600/20">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                <span>Tasdiqlash</span>
              </button>
              <button type="button" onclick="openDisputeModal(${app.id})" class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl border border-rose-500/40 hover:bg-rose-500/10 text-rose-400 text-xs font-semibold transition cursor-pointer">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
                <span>E'tiroz</span>
              </button>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  });
}

async function loadStudentAppeals() {
  const list = document.getElementById('student-appeals-list');
  try {
    const resp = await fetch('/api/v1/appeals', {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (!resp.ok) {
      list.innerHTML = '<div class="p-8 text-center text-xs text-rose-400 border border-slate-800/80 rounded-2xl bg-slate-900/40">Murojaatlarni yuklab bo\'lmadi.</div>';
      return;
    }
    allStudentAppeals = await resp.json();
    applyStudentAppealsFilter();
  } catch (e) {
    list.innerHTML = '<div class="p-4 text-center text-xs text-rose-400">Ma\'lumotlarni yuklab bo\'lmadi.</div>';
  }
}

async function cancelStudentAppeal(appealId) {
  const confirmed = await openAppConfirm({
    title: "Murojaatni bekor qilish",
    message: "Haqiqatan ham ushbu murojaatni bekor qilmoqchimisiz? Ushbu amalni ortga qaytarib bo'lmaydi.",
    confirmText: "Ha, bekor qilinsin",
    cancelText: "Ortga",
    isDanger: true
  });
  if (!confirmed) return;

  try {
    const resp = await fetch(apiUrl(`/api/v1/appeals/${appealId}/cancel`), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token
      },
      body: JSON.stringify({ reason: "Talaba tomonidan bekor qilindi" })
    });
    if (resp.ok) {
      showToast("Murojaat muvaffaqiyatli bekor qilindi.", "success");
      loadStudentAppeals();
    } else {
      const data = await resp.json();
      showToast(data.detail || "Murojaatni bekor qilishda xatolik yuz berdi.", "error");
    }
  } catch (err) {
    showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
  }
}

// --- APPEAL LIVE TRACKER (Vizual kuzatish va kutish vaqti) ---
async function openAppealTracker(appealId) {
  const modal = document.getElementById('modal-appeal-tracker');
  if (!modal) return;

  const ticketBadge = document.getElementById('tracker-ticket-badge');
  const statusBadge = document.getElementById('tracker-status-badge');
  const titleEl = document.getElementById('tracker-title');
  const progText = document.getElementById('tracker-progress-text');
  const progBar = document.getElementById('tracker-progress-bar');
  const estTimeEl = document.getElementById('tracker-est-time');
  const staffInfoEl = document.getElementById('tracker-staff-info');
  const stepsContainer = document.getElementById('tracker-steps-container');
  const resBox = document.getElementById('tracker-resolution-box');
  const resText = document.getElementById('tracker-resolution-text');
  const resFiles = document.getElementById('tracker-result-files');

  // Loading holati
  stepsContainer.innerHTML = '<div class="p-6 text-center text-xs text-slate-400">Yuklanmoqda...</div>';
  modal.classList.remove('hidden');

  try {
    const resp = await fetch(apiUrl(`/api/v1/appeals/${appealId}/track`), {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (!resp.ok) {
      showToast("Murojaat ma'lumotlarini yuklab bo'lmadi", "error");
      closeAppealTracker();
      return;
    }
    const data = await resp.json();

    ticketBadge.innerText = '#' + (data.ticket_number || '').replace('#', '');
    statusBadge.innerText = data.status_label || data.status;
    titleEl.innerText = data.subject || data.service_title;
    progText.innerText = data.progress_percentage + '%';
    progBar.style.width = data.progress_percentage + '%';
    estTimeEl.innerText = data.estimated_completion_text || "Ma'lumot yo'q";

    if (data.assigned_staff_name) {
      staffInfoEl.innerText = data.assigned_staff_name + (data.assigned_staff_window ? ` (${data.assigned_staff_window})` : '');
    } else {
      staffInfoEl.innerText = "Hali biriktirilmagan";
    }

    // Qadamlarni render qilish
    let stepsHtml = '';
    (data.steps || []).forEach((step, idx) => {
      let circleStyle = "bg-slate-800 border-slate-700 text-slate-400";
      let pulseEffect = "";

      if (step.status === 'completed') {
        circleStyle = "bg-emerald-500/20 border-emerald-500 text-emerald-400";
      } else if (step.status === 'current') {
        circleStyle = "bg-indigo-600 border-indigo-400 text-white shadow-lg shadow-indigo-500/40 ring-4 ring-indigo-500/20";
        pulseEffect = '<span class="absolute -top-1 -right-1 flex h-3 w-3"><span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span><span class="relative inline-flex rounded-full h-3 w-3 bg-indigo-500"></span></span>';
      } else if (step.status === 'rejected') {
        circleStyle = "bg-rose-500/20 border-rose-500 text-rose-400";
      }

      const timeStr = step.timestamp ? formatDateTime(step.timestamp) : '';

      stepsHtml += `
        <div class="relative flex items-start gap-3.5 pl-1 group">
          <div class="relative z-10 w-7 h-7 rounded-full border flex items-center justify-center text-xs font-bold shrink-0 transition-all ${circleStyle}">
            ${step.status === 'completed' ? '✓' : (step.status === 'rejected' ? '✕' : (idx + 1))}
            ${pulseEffect}
          </div>
          <div class="flex-1 pb-4 border-b border-slate-800/60 group-last:border-none">
            <div class="flex items-center justify-between flex-wrap gap-1">
              <span class="text-xs font-bold text-white">${step.title}</span>
              ${timeStr ? `<span class="text-[10px] font-mono text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">${timeStr}</span>` : ''}
            </div>
            <p class="text-[11px] text-slate-300 mt-1 leading-relaxed">${step.description}</p>
            ${step.actor_name ? `<span class="text-[10px] text-indigo-400/90 font-medium block mt-1">Ijrochi: ${step.actor_name} (${step.actor_role || 'Xodim'})</span>` : ''}
          </div>
        </div>
      `;
    });
    stepsContainer.innerHTML = stepsHtml;

    // Xulosa qismi
    if (data.resolution_text) {
      resBox.classList.remove('hidden');
      resText.innerText = data.resolution_text;
      let filesHtml = '';
      if (data.result_file_url) {
        filesHtml += `
          <a href="${apiUrl(data.result_file_url)}" target="_blank" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-emerald-500/40 bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 text-xs font-medium transition">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
            <span>Rasmiy PDF ma'lumotnoma</span>
          </a>
        `;
      }
      if (data.qr_hash) {
        filesHtml += `
          <a href="${apiUrl('/verify/' + data.qr_hash)}" target="_blank" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-blue-500/40 bg-blue-500/15 hover:bg-blue-500/25 text-blue-300 text-xs font-medium transition">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M4 8h16M4 16h4m4 0h4"/></svg>
            <span>QR-kod verifikatsiyasi</span>
          </a>
        `;
      }
      resFiles.innerHTML = filesHtml;
    } else {
      resBox.classList.add('hidden');
    }

  } catch (e) {
    showToast("Xatolik yuz berdi: " + e.message, "error");
    closeAppealTracker();
  }
}

function closeAppealTracker() {
  const modal = document.getElementById('modal-appeal-tracker');
  if (modal) modal.classList.add('hidden');
}

