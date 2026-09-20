// --- REGISTRATOR OFISI E'LONLARI VA FILTRLI ARXIV TIZIMI ---
let cachedStudentAnnouncements = [];
let currentAnnouncementFilter = 'active'; // 'active' | 'archived'

function setAnnouncementFilter(filter) {
  currentAnnouncementFilter = filter;
  renderStudentAnnouncements();
}

async function loadStudentAnnouncements() {
  if (!token) return;
  const box = document.getElementById('student-announcements-container');
  if (!box) return;
  try {
    const res = await fetch(apiUrl('/api/v1/announcements/my'), {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (!res.ok) return;
    cachedStudentAnnouncements = await res.json();
    renderStudentAnnouncements();
  } catch (e) {
    console.error("E'lonlarni yuklashda xatolik:", e);
  }
}

function renderStudentAnnouncements() {
  const box = document.getElementById('student-announcements-container');
  if (!box) return;
  if (!cachedStudentAnnouncements || cachedStudentAnnouncements.length === 0) {
    box.classList.add('hidden');
    box.innerHTML = '';
    return;
  }

  box.classList.remove('hidden');

  const activeList = cachedStudentAnnouncements.filter(a => !a.is_read || !a.is_acknowledged);
  const archivedList = cachedStudentAnnouncements.filter(a => a.is_read && a.is_acknowledged);

  // Update sidebar badge
  const sidebarBadge = document.getElementById('student-announcements-sidebar-badge');
  if (sidebarBadge) {
    if (activeList.length > 0) {
      sidebarBadge.innerText = activeList.length;
      sidebarBadge.classList.remove('hidden');
    } else {
      sidebarBadge.classList.add('hidden');
    }
  }

  // Update home page (tab-appeals) quick announcement banner
  const urgentStrip = document.getElementById('student-urgent-announcement-strip');
  if (urgentStrip) {
    if (activeList.length > 0) {
      urgentStrip.classList.remove('hidden');
      urgentStrip.innerHTML = `
        <div class="p-3.5 rounded-2xl bg-gradient-to-r from-blue-950/70 via-indigo-950/50 to-slate-900 border border-blue-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-lg">
          <div class="flex items-center gap-2.5">
            <span class="flex h-2.5 w-2.5 relative">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
            </span>
            <span class="text-xs text-slate-200">Registrator ofisidan <b>${activeList.length} ta</b> yangi rasmiy e'lon mavjud.</span>
          </div>
          <button type="button" onclick="switchStudentTab('announcements')" class="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition cursor-pointer shadow-sm shadow-blue-600/30 self-start sm:self-auto">
            <span>E'lonlar markaziga o'tish</span>
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
          </button>
        </div>
      `;
    } else {
      urgentStrip.classList.add('hidden');
      urgentStrip.innerHTML = '';
    }
  }

  const currentList = currentAnnouncementFilter === 'active' ? activeList : archivedList;

  let html = `
    <div class="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-3.5 backdrop-blur-xl">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-slate-800/80">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z"/></svg>
          </div>
          <div>
            <h3 class="text-sm font-bold text-white tracking-tight">Registrator ofisi e'lonlari</h3>
            <p class="text-[11px] text-slate-400">Filial va fakultet miqyosidagi rasmiy bildirishnomalar</p>
          </div>
        </div>
        <div class="flex items-center gap-1.5 p-1 bg-slate-950/80 rounded-xl border border-slate-800 self-start sm:self-auto">
          <button type="button" onclick="setAnnouncementFilter('active')" class="px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer flex items-center gap-1.5 ${currentAnnouncementFilter === 'active' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'}">
            <span>Faol e'lonlar</span>
            <span class="px-1.5 py-0.5 rounded-full text-[10px] ${currentAnnouncementFilter === 'active' ? 'bg-blue-800 text-white' : 'bg-slate-800 text-slate-400'}">${activeList.length}</span>
          </button>
          <button type="button" onclick="setAnnouncementFilter('archived')" class="px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer flex items-center gap-1.5 ${currentAnnouncementFilter === 'archived' ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'}">
            <span>O'qilganlar arxivi</span>
            <span class="px-1.5 py-0.5 rounded-full text-[10px] bg-slate-800 text-slate-400">${archivedList.length}</span>
          </button>
        </div>
      </div>

      <div class="space-y-3">
  `;

  if (currentList.length === 0) {
    if (currentAnnouncementFilter === 'active') {
      html += `
        <div class="py-6 text-center text-xs text-slate-400 bg-slate-950/40 rounded-xl border border-dashed border-slate-800 flex flex-col items-center gap-1.5">
          <svg class="w-6 h-6 text-emerald-400/70" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          <span>Hozirda yangi o'qilmagan e'lonlar yo'q. Barcha e'lonlar bilan tanishilgansiz.</span>
        </div>
      `;
    } else {
      html += `
        <div class="py-6 text-center text-xs text-slate-400 bg-slate-950/40 rounded-xl border border-dashed border-slate-800">
          Hozircha o'qilgan e'lonlar arxivi mavjud emas.
        </div>
      `;
    }
  } else {
    html += currentList.map(a => {
      let prioStyle = "border-blue-500/30 bg-blue-950/30 text-blue-300";
      let prioBadge = "bg-blue-500/20 text-blue-300 border-blue-500/30";
      let prioTitle = "E'lon";

      if (a.priority === 'urgent') {
        prioStyle = "border-rose-500/40 bg-rose-950/40 text-rose-200";
        prioBadge = "bg-rose-500/20 text-rose-300 border-rose-500/30";
        prioTitle = "Shoshilinch ogohlantirish";
      } else if (a.priority === 'important') {
        prioStyle = "border-amber-500/40 bg-amber-950/30 text-amber-200";
        prioBadge = "bg-amber-500/20 text-amber-300 border-amber-500/30";
        prioTitle = "Muhim xabar";
      }

      const escTitle = (a.title || '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      const escContent = (a.content || '').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br/>');

      return `
        <div class="p-4 rounded-xl border ${prioStyle} backdrop-blur-xl relative transition space-y-2">
          <div class="flex items-center justify-between gap-2">
            <div class="flex items-center gap-2">
              <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${prioBadge}">
                ${prioTitle}
              </span>
              <span class="text-[11px] text-slate-400">${formatDateOnly(a.created_at)}</span>
            </div>
            ${a.is_read ? `
              <span class="text-[11px] font-semibold text-emerald-400 flex items-center gap-1">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                <span>O'qildi ${a.read_at ? '(' + formatDateTime(a.read_at) + ')' : ''}</span>
              </span>
            ` : `
              <span class="text-[11px] font-bold text-amber-400 animate-pulse">● Yangi</span>
            `}
          </div>
          <div>
            <h4 class="text-sm font-bold text-white tracking-tight">${escTitle}</h4>
            <p class="text-xs text-slate-300 mt-1 leading-relaxed">${escContent}</p>
          </div>
          <div class="flex items-center justify-end pt-1 border-t border-white/5">
            ${!a.is_acknowledged ? `
              <button type="button" onclick="acknowledgeAnnouncement(${a.id})" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white transition cursor-pointer shadow-sm shadow-blue-600/20">
                <svg class="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                <span>${a.requires_ack ? "Tanishdim va qabul qildim" : "Tanishdim"}</span>
              </button>
            ` : `
              <span class="text-[11px] text-slate-400 italic flex items-center gap-1">
                <svg class="w-3.5 h-3.5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                <span>Tanishilgan va tasdiqlangan</span>
              </span>
            `}
          </div>
        </div>
      `;
    }).join('');
  }

  html += `
      </div>
    </div>
  `;

  box.innerHTML = html;
}

async function acknowledgeAnnouncement(id) {
  try {
    const res = await fetch(apiUrl(`/api/v1/announcements/${id}/read?is_ack=true`), {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (res.ok) {
      showToast("E'lon bilan tanishganingiz tasdiqlandi", "success");
      loadStudentAnnouncements();
    }
  } catch (e) {
    showToast("Xatolik yuz berdi", "error");
  }
}

