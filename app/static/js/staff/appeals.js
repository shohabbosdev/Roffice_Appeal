let appealsCurrentPage = 1;
let appealsPerPage = 10;
let currentFilteredAppeals = [];

async function loadStaffAppeals() {
      const container = document.getElementById('staff-appeals-list');
      container.innerHTML = '<div class="p-8 text-center text-xs text-slate-500">Murojaatlar yuklanmoqda...</div>';

      try {
        const resp = await fetch('/api/v1/appeals', {
          headers: { 'Authorization': 'Bearer ' + token }
        });
        const data = await resp.json();

        if (Array.isArray(data)) {
          allStaffAppeals = data;

          // 1. Update overall statistics
          const total = data.length;
          const newCount = data.filter(a => a.status === 'new').length;
          const inpCount = data.filter(a => ['assigned', 'in_progress', 'clarification_needed'].includes(a.status)).length;
          const doneCount = data.filter(a => ['resolved', 'completed', 'auto_closed'].includes(a.status)).length;
          const disputedCount = data.filter(a => ['disputed', 'escalated_prorektor', 'escalated_head'].includes(a.status)).length;

          document.getElementById('stat-total').textContent = total;
          document.getElementById('stat-new').textContent = newCount;
          document.getElementById('stat-inprogress').textContent = inpCount;
          document.getElementById('stat-done').textContent = doneCount;
          const statDisputedEl = document.getElementById('stat-disputed');
          if (statDisputedEl) statDisputedEl.textContent = disputedCount;

          // 2. SLA Risk Radar
          updateSlaRiskRadar(allStaffAppeals);

          // 3. 7-day trends chart
          renderTrendsChart(allStaffAppeals);

          // 4. Populate services filter
          populateServiceFilter(allStaffAppeals);

          // 5. Render filtered appeals
          applyAppealsFilter();
        } else {
          container.innerHTML = '<div class="p-8 text-center text-xs text-rose-400">Murojaatlarni yuklashda xatolik yuz berdi.</div>';
        }
      } catch (e) {
        container.innerHTML = '<div class="p-4 text-center text-xs text-rose-400">Server bilan aloqa uzildi.</div>';
      }
    }

    function updateSlaRiskRadar(appeals) {
      const banner = document.getElementById('sla-risk-banner');
      const badge = document.getElementById('sla-risk-badge');
      const desc = document.getElementById('sla-risk-desc');
      if (!banner) return;

      const now = new Date();
      const nonClosed = appeals.filter(a => !['resolved', 'completed', 'auto_closed', 'cancelled', 'rejected'].includes(a.status));

      const overdueList = nonClosed.filter(a => a.sla_deadline_at && new Date(a.sla_deadline_at) < now);
      const nearOverdueList = nonClosed.filter(a => {
        if (!a.sla_deadline_at) return false;
        const diffHours = (new Date(a.sla_deadline_at) - now) / (1000 * 60 * 60);
        return diffHours >= 0 && diffHours <= 24;
      });

      if (overdueList.length > 0 || nearOverdueList.length > 0) {
        banner.classList.remove('hidden');
        badge.textContent = `${overdueList.length} ta kechikkan, ${nearOverdueList.length} ta yaqinlashgan`;
        desc.innerHTML = `Sizda <strong>${overdueList.length} ta</strong> murojaatning SLA muddati o'tgan va <strong>${nearOverdueList.length} ta</strong> murojaatning muddati 24 soat ichida tugaydi. Iltimos, zudlik bilan ko'rib chiqing!`;
      } else {
        banner.classList.add('hidden');
      }
    }

    function toggleTrendsChart() {
      const wrap = document.getElementById('appeals-trend-chart-wrap');
      const icon = document.getElementById('trends-toggle-icon');
      if (!wrap) return;
      const isHidden = wrap.classList.contains('hidden');
      if (isHidden) {
        wrap.classList.remove('hidden');
        if (icon) icon.innerText = '▲';
      } else {
        wrap.classList.add('hidden');
        if (icon) icon.innerText = '▼';
      }
    }

    function renderTrendsChart(appeals) {
      const chartEl = document.getElementById('appeals-trend-chart');
      if (!chartEl) return;

      const days = [];
      const dayNames = ['Yak', 'Dush', 'Sesh', 'Chor', 'Pay', 'Jum', 'Shan'];
      const now = new Date();

      for (let i = 6; i >= 0; i--) {
        const d = new Date();
        d.setDate(now.getDate() - i);
        const ymd = d.toISOString().slice(0, 10);
        const label = `${d.getDate()}-${dayNames[d.getDay()]}`;

        const createdCount = appeals.filter(a => a.created_at && a.created_at.slice(0, 10) === ymd).length;
        const resolvedCount = appeals.filter(a => a.resolved_at && a.resolved_at.slice(0, 10) === ymd).length;

        days.push({ ymd, label, createdCount, resolvedCount });
      }

      const maxVal = Math.max(...days.map(d => Math.max(d.createdCount, d.resolvedCount, 1)), 5);

      chartEl.innerHTML = days.map(d => {
        const hCreated = Math.round((d.createdCount / maxVal) * 95);
        const hResolved = Math.round((d.resolvedCount / maxVal) * 95);

        return `
          <div class="flex flex-col items-center gap-2 h-full justify-end">
            <div class="flex items-end gap-1.5 w-full justify-center h-28">
              <div 
                class="w-3.5 sm:w-5 bg-gradient-to-t from-blue-600 to-blue-400 rounded-t-md transition-all hover:brightness-125 relative group cursor-pointer shadow-sm shadow-blue-500/20"
                style="height: ${Math.max(hCreated, 6)}px;"
                title="${d.ymd}: ${d.createdCount} ta kelib tushdi"
              >
                ${d.createdCount > 0 ? `<span class="absolute -top-5 left-1/2 -translate-x-1/2 text-[10px] font-bold text-blue-300 pointer-events-none">${d.createdCount}</span>` : ''}
              </div>
              <div 
                class="w-3.5 sm:w-5 bg-gradient-to-t from-emerald-600 to-emerald-400 rounded-t-md transition-all hover:brightness-125 relative group cursor-pointer shadow-sm shadow-emerald-500/20"
                style="height: ${Math.max(hResolved, 6)}px;"
                title="${d.ymd}: ${d.resolvedCount} ta bajarildi"
              >
                ${d.resolvedCount > 0 ? `<span class="absolute -top-5 left-1/2 -translate-x-1/2 text-[10px] font-bold text-emerald-300 pointer-events-none">${d.resolvedCount}</span>` : ''}
              </div>
            </div>
            <span class="text-[10px] sm:text-[11px] text-slate-400 font-medium">${d.label}</span>
          </div>
        `;
      }).join('');
    }

    function populateServiceFilter(appeals) {
      const select = document.getElementById('appeals-filter-service');
      if (!select) return;
      const currentVal = select.value;
      const serviceMap = new Map();
      appeals.forEach(a => {
        if (a.service) serviceMap.set(a.service.id, a.service.title);
      });

      let opts = '<option value="">Barcha xizmatlar</option>';
      serviceMap.forEach((title, id) => {
        opts += `<option value="${id}" ${currentVal == id ? 'selected' : ''}>${title}</option>`;
      });
      select.innerHTML = opts;
    }

    function toggleOverdueFilter(forceVal) {
      filterOnlyOverdue = forceVal !== undefined ? forceVal : !filterOnlyOverdue;
      const btn = document.getElementById('overdue-toggle-btn');
      if (btn) {
        if (filterOnlyOverdue) {
          btn.className = "px-3 py-1.5 rounded-xl border border-rose-500/60 bg-rose-500/20 text-rose-300 font-bold transition cursor-pointer text-xs flex items-center gap-1.5";
        } else {
          btn.className = "px-3 py-1.5 rounded-xl border border-slate-800 text-slate-400 hover:text-rose-400 hover:border-rose-500/40 transition cursor-pointer text-xs font-medium flex items-center gap-1.5";
        }
      }
      applyAppealsFilter();
    }

    function toggleDisputedFilter(forceVal) {
      filterOnlyDisputed = forceVal !== undefined ? forceVal : !filterOnlyDisputed;
      const btn = document.getElementById('disputed-toggle-btn');
      if (btn) {
        if (filterOnlyDisputed) {
          btn.className = "px-3 py-1.5 rounded-xl border border-purple-500/60 bg-purple-500/20 text-purple-300 font-bold transition cursor-pointer text-xs flex items-center gap-1.5";
        } else {
          btn.className = "px-3 py-1.5 rounded-xl border border-slate-800 text-slate-400 hover:text-purple-400 hover:border-purple-500/40 transition cursor-pointer text-xs font-medium flex items-center gap-1.5";
        }
      }
      applyAppealsFilter();
    }

    function filterDisputedAndEscalated() {
      filterOnlyOverdue = false;
      const overdueBtn = document.getElementById('overdue-toggle-btn');
      if (overdueBtn) overdueBtn.className = "px-3 py-1.5 rounded-xl border border-slate-800 text-slate-400 hover:text-rose-400 hover:border-rose-500/40 transition cursor-pointer text-xs font-medium flex items-center gap-1.5";
      toggleDisputedFilter(true);
      const listEl = document.getElementById('staff-appeals-list');
      if (listEl) listEl.scrollIntoView({ behavior: 'smooth' });
    }

    function handleAppealsFilter() {
      applyAppealsFilter(true);
    }

    function applyAppealsFilter(resetPage = true) {
      if (resetPage) {
        appealsCurrentPage = 1;
      }

      const searchQ = (document.getElementById('appeals-search')?.value || '').trim().toLowerCase();
      const statusQ = document.getElementById('appeals-filter-status')?.value || '';
      const serviceQ = document.getElementById('appeals-filter-service')?.value || '';

      const now = new Date();

      let filtered = allStaffAppeals.filter(app => {
        if (statusQ && app.status !== statusQ) return false;
        if (serviceQ && String(app.service_id) !== String(serviceQ)) return false;
        if (filterOnlyOverdue) {
          const isClosed = ['resolved', 'completed', 'auto_closed', 'cancelled', 'rejected'].includes(app.status);
          const isOverdue = app.sla_deadline_at && new Date(app.sla_deadline_at) < now;
          if (isClosed || !isOverdue) return false;
        }
        if (filterOnlyDisputed) {
          if (!['disputed', 'escalated_prorektor', 'escalated_head'].includes(app.status)) return false;
        }
        if (searchQ) {
          const ticketMatch = (app.ticket_number || '').toLowerCase().includes(searchQ);
          const subjMatch = (app.subject || '').toLowerCase().includes(searchQ);
          const msgMatch = (app.message || '').toLowerCase().includes(searchQ);
          const studentNameMatch = (app.student?.full_name || '').toLowerCase().includes(searchQ);
          const studentIdMatch = (app.student?.username || '').toLowerCase().includes(searchQ);
          const staffNameMatch = (app.assigned_staff?.full_name || '').toLowerCase().includes(searchQ);
          if (!ticketMatch && !subjMatch && !msgMatch && !studentNameMatch && !studentIdMatch && !staffNameMatch) {
            return false;
          }
        }
        return true;
      });

      currentFilteredAppeals = filtered;
      renderAppealsCurrentPage();
    }

    function renderAppealsCurrentPage() {
      const container = document.getElementById('staff-appeals-list');
      const countBadge = document.getElementById('filtered-count-badge');
      const paginationBar = document.getElementById('appeals-pagination-bar');
      const pageInfo = document.getElementById('appeals-page-info');
      const paginationButtons = document.getElementById('appeals-pagination-buttons');

      const total = currentFilteredAppeals.length;

      if (countBadge) {
        countBadge.textContent = `${total} ta topildi (Jami: ${allStaffAppeals.length})`;
      }

      if (total === 0) {
        if (paginationBar) {
          paginationBar.classList.remove('flex');
          paginationBar.classList.add('hidden');
        }
        container.innerHTML = '<div class="p-8 text-center text-xs text-slate-500 border border-slate-800/80 rounded-2xl bg-slate-900/40">Mos keluvchi murojaat topilmadi.</div>';
        return;
      }

      const totalPages = Math.ceil(total / appealsPerPage) || 1;
      if (appealsCurrentPage > totalPages) appealsCurrentPage = totalPages;
      if (appealsCurrentPage < 1) appealsCurrentPage = 1;

      const startIdx = (appealsCurrentPage - 1) * appealsPerPage;
      const endIdx = Math.min(startIdx + appealsPerPage, total);
      const pageItems = currentFilteredAppeals.slice(startIdx, endIdx);

      // Pagination boshqaruv elementlarini chizish
      if (paginationBar) {
        paginationBar.classList.remove('hidden');
        paginationBar.classList.add('flex');

        if (pageInfo) {
          pageInfo.textContent = `${startIdx + 1}-${endIdx} / ${total}`;
        }

        if (paginationButtons) {
          let btnsHtml = '';

          // Oldingi sahifa tugmasi
          btnsHtml += `
            <button 
              type="button" 
              onclick="changeAppealsPage(${appealsCurrentPage - 1})" 
              ${appealsCurrentPage <= 1 ? 'disabled class="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-950 text-slate-600 text-xs cursor-not-allowed"' : 'class="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-950 text-slate-300 hover:text-white hover:border-slate-700 text-xs cursor-pointer transition"'}
            >
              ◀ Oldingi
            </button>
          `;

          if (totalPages <= 7) {
            for (let p = 1; p <= totalPages; p++) {
              const isActive = p === appealsCurrentPage;
              btnsHtml += `
                <button 
                  type="button" 
                  onclick="changeAppealsPage(${p})" 
                  class="w-7 h-7 flex items-center justify-center rounded-lg text-xs font-semibold transition cursor-pointer ${isActive ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30' : 'border border-slate-800 bg-slate-950 text-slate-400 hover:text-white hover:border-slate-700'}"
                >
                  ${p}
                </button>
              `;
            }
          } else {
            btnsHtml += `
              <button 
                type="button" 
                onclick="changeAppealsPage(1)" 
                class="w-7 h-7 flex items-center justify-center rounded-lg text-xs font-semibold transition cursor-pointer ${appealsCurrentPage === 1 ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30' : 'border border-slate-800 bg-slate-950 text-slate-400 hover:text-white hover:border-slate-700'}"
              >
                1
              </button>
            `;

            let startPage = Math.max(2, appealsCurrentPage - 1);
            let endPage = Math.min(totalPages - 1, appealsCurrentPage + 1);

            if (startPage > 2) {
              btnsHtml += `<span class="text-slate-600 text-xs px-1">...</span>`;
            }

            for (let p = startPage; p <= endPage; p++) {
              const isActive = p === appealsCurrentPage;
              btnsHtml += `
                <button 
                  type="button" 
                  onclick="changeAppealsPage(${p})" 
                  class="w-7 h-7 flex items-center justify-center rounded-lg text-xs font-semibold transition cursor-pointer ${isActive ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30' : 'border border-slate-800 bg-slate-950 text-slate-400 hover:text-white hover:border-slate-700'}"
                >
                  ${p}
                </button>
              `;
            }

            if (endPage < totalPages - 1) {
              btnsHtml += `<span class="text-slate-600 text-xs px-1">...</span>`;
            }

            btnsHtml += `
              <button 
                type="button" 
                onclick="changeAppealsPage(${totalPages})" 
                class="w-7 h-7 flex items-center justify-center rounded-lg text-xs font-semibold transition cursor-pointer ${appealsCurrentPage === totalPages ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30' : 'border border-slate-800 bg-slate-950 text-slate-400 hover:text-white hover:border-slate-700'}"
              >
                ${totalPages}
              </button>
            `;
          }

          // Keyingi sahifa tugmasi
          btnsHtml += `
            <button 
              type="button" 
              onclick="changeAppealsPage(${appealsCurrentPage + 1})" 
              ${appealsCurrentPage >= totalPages ? 'disabled class="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-950 text-slate-600 text-xs cursor-not-allowed"' : 'class="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-950 text-slate-300 hover:text-white hover:border-slate-700 text-xs cursor-pointer transition"'}
            >
              Keyingi ▶
            </button>
          `;

          paginationButtons.innerHTML = btnsHtml;
        }
      }

      // Sahifaga tegishli arizalarni render qilish
      const now = new Date();
      const isAdminOrHead = ['admin', 'office_head', 'vice_rector'].includes(userRole);

      let html = '';
      pageItems.forEach(app => {
        const meta = STATUS_META[app.status] || { label: app.status, cls: 'bg-slate-500/10 text-slate-400 border-slate-500/20' };
        const deadline = app.sla_deadline_at ? new Date(app.sla_deadline_at) : null;
        const isClosed = ['resolved', 'completed', 'auto_closed', 'cancelled', 'rejected'].includes(app.status);
        const isOverdue = deadline && deadline < now && !isClosed;
        const slaStr = deadline ? formatDateTime(deadline) : '—';
        const createdStr = app.created_at ? formatDateTime(app.created_at) : '—';

        html += `
          <div class="bg-slate-900/80 border ${isOverdue ? 'border-rose-500/50 shadow-rose-950/20 bg-gradient-to-b from-rose-950/10 to-slate-900/80' : 'border-slate-800/90'} rounded-2xl p-5 space-y-4 shadow-lg hover:border-slate-700 transition">
            <!-- Top info: Ticket, Status, Date -->
            <div class="flex items-start justify-between gap-3">
              <div class="space-y-1.5 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="font-mono text-xs font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-0.5 rounded-lg">#${app.ticket_number}</span>
                  ${isOverdue ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30 uppercase tracking-wider animate-pulse">SLA Kechikkan</span>' : ''}
                  <span class="text-[11px] text-slate-500 flex items-center gap-1">
                    <svg class="w-3 h-3 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    ${createdStr}
                  </span>
                </div>
                <h5 class="text-sm sm:text-base font-bold text-white tracking-tight leading-snug">${app.subject}</h5>
              </div>
              <span class="px-3 py-1 rounded-full text-xs font-semibold border flex-shrink-0 ${meta.cls}">${meta.label}</span>
            </div>

            <!-- Student Profile Badge -->
            <div class="flex items-center gap-3 p-3 rounded-xl bg-slate-950/80 border border-slate-800/80 text-xs flex-wrap">
              <div class="flex items-center gap-2">
                <div class="w-6 h-6 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 text-xs font-bold">
                  ${(app.student?.full_name || 'T')[0]}
                </div>
                <strong class="text-white font-semibold">${app.student ? app.student.full_name : 'Noma\'lum talaba'}</strong>
              </div>
              ${app.student?.username ? `<span class="px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-300 border border-blue-500/20 font-mono text-[11px]">HEMIS ID: ${app.student.username}</span>` : ''}
              ${app.student?.education_form ? `<span class="text-slate-400 text-[11px] ml-auto">Ta'lim shakli: <strong class="text-slate-200 uppercase">${app.student.education_form}</strong></span>` : ''}
            </div>

            <!-- Appeal Message Content -->
            <div class="text-xs text-slate-300 leading-relaxed bg-slate-950/40 p-3.5 rounded-xl border border-slate-800/60 whitespace-pre-wrap">${app.message}</div>

            ${app.attachment_urls ? `
              <div>
                <a href="${app.attachment_urls}" target="_blank" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border border-blue-500/30 bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 text-xs font-medium transition">
                  <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                  <span>Talaba ilova qilgan hujjatni yuklab olish</span>
                </a>
              </div>
            ` : ''}

            <!-- Footer Details: Service, SLA & Assigned Staff in clean 3-col grid -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 p-3 rounded-xl bg-slate-950/40 border border-slate-800/60 text-xs">
              <div>
                <div class="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Xizmat</div>
                <div class="text-slate-200 font-medium truncate mt-0.5">${app.service ? app.service.title : '—'}</div>
              </div>
              <div>
                <div class="text-[10px] text-slate-500 uppercase tracking-wider font-bold">SLA Muhlati</div>
                <div class="font-medium mt-0.5 ${isOverdue ? 'text-rose-400 font-bold' : 'text-slate-200'}">${slaStr}</div>
              </div>
              <div>
                <div class="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Mas'ul Ijrochi</div>
                <div class="font-medium mt-0.5 text-indigo-300">${app.assigned_staff ? app.assigned_staff.full_name : '<span class="text-amber-400 font-normal italic">Biriktirilmagan</span>'}</div>
              </div>
            </div>

            ${app.resolution_text ? `
              <div class="p-4 bg-emerald-950/20 border border-emerald-500/30 rounded-xl space-y-2">
                <span class="text-[10px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                  Rasmiy ijro xulosasi:
                </span>
                <p class="text-xs text-slate-200 leading-relaxed">${app.resolution_text}</p>
                ${app.result_file_url ? `
                  <div class="pt-2 flex flex-wrap items-center gap-2 border-t border-emerald-500/20">
                    <a href="${apiUrl(app.result_file_url)}" target="_blank" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-emerald-500/40 bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 text-xs font-medium transition">
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                      <span>Rasmiy PDF hujjat</span>
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

            ${app.rating ? `
              <div class="flex items-center gap-2 p-2.5 rounded-xl bg-amber-950/20 border border-amber-500/20 text-xs text-amber-300">
                <span class="font-medium">Talaba bahosi:</span>
                <span class="font-bold text-amber-400 tracking-wider">${'★'.repeat(app.rating)}${'☆'.repeat(5 - app.rating)}</span>
                ${app.rating_comment ? `<span class="text-slate-400 italic">"${app.rating_comment}"</span>` : ''}
              </div>
            ` : ''}

            ${app.dispute_reason ? `
              <div class="p-3.5 bg-rose-950/30 border border-rose-500/40 rounded-xl space-y-1">
                <span class="text-[10px] font-bold text-rose-400 uppercase tracking-wider flex items-center gap-1.5">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
                  Talabaning e'tiroz / nizo sababi:
                </span>
                <p class="text-xs text-rose-200 leading-relaxed">${app.dispute_reason}</p>
              </div>
            ` : ''}

            ${app.status === 'escalated_prorektor' ? `
              <div class="p-3.5 bg-purple-950/30 border border-purple-500/40 rounded-xl space-y-1">
                <span class="text-[10px] font-bold text-purple-300 uppercase tracking-wider flex items-center gap-1.5">
                  <span class="w-2 h-2 rounded-full bg-purple-400 animate-ping"></span>
                  Prorektor nazoratiga eskalatsiya qilingan:
                </span>
                <p class="text-xs text-purple-200 leading-relaxed">${app.clarification_message || "Rahbariyat ko'rigi va yakuniy qarori talab etiladi."}</p>
              </div>
            ` : ''}

            <!-- Action buttons -->
            <div class="flex items-center gap-2.5 pt-2 flex-wrap border-t border-slate-800/80">
              <!-- Xronologiya va Audit Trail tugmasi -->
              <button
                onclick="openAppealAuditModal(${app.id})"
                class="px-3 py-2 rounded-xl border border-slate-700 hover:border-blue-500/50 bg-slate-950 text-slate-300 hover:text-blue-300 text-xs font-medium transition cursor-pointer flex items-center gap-1.5"
                title="Murojaatning to'liq xronologiyasi va audit ma'lumotlari"
              >
                <svg class="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                <span>Xronologiya / Audit</span>
              </button>

              ${isAdminOrHead ? `
                <button
                  onclick="openReassignModal(${app.id})"
                  class="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition cursor-pointer flex items-center gap-2 shadow-md shadow-indigo-600/20"
                  title="Murojaatni ijrochi xodimga biriktirish yoki boshqasiga o'tkazish"
                >
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
                  <span>${app.assigned_staff_id ? "Qayta biriktirish" : "Xodimga biriktirish"}</span>
                </button>
              ` : ''}

              ${app.status === 'new' && !isAdminOrHead ? `
                <button onclick="assignToMe(${app.id})" class="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition cursor-pointer shadow-md shadow-blue-600/20">
                  Menga biriktirish
                </button>
              ` : ''}

              ${['assigned', 'in_progress'].includes(app.status) ? `
                <button onclick="openResolveModal(${app.id})" class="px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition cursor-pointer flex items-center gap-1.5 shadow-md shadow-emerald-600/20">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                  <span>Javob berish va yakunlash</span>
                </button>
                <button onclick="openClarifyModal(${app.id})" class="px-3.5 py-2 rounded-xl border border-slate-700 hover:border-blue-500 bg-slate-950 text-slate-300 hover:text-blue-300 text-xs font-medium transition cursor-pointer flex items-center gap-1.5">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                  <span>Ma'lumot so'rash</span>
                </button>
              ` : ''}

              <!-- Prorektor yakuniy qarorini chiqarish tugmasi (Prorektor yoki Admin uchun) -->
              ${['vice_rector', 'admin'].includes(userRole) && ['disputed', 'escalated_prorektor'].includes(app.status) ? `
                <button
                  onclick="openProrektorDecisionModal(${app.id})"
                  class="px-3.5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold transition cursor-pointer flex items-center gap-1.5 shadow-md shadow-purple-600/20"
                >
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                  <span>Prorektor qarorini chiqarish</span>
                </button>
              ` : ''}

              <!-- Boshliq uchun eskalatsiya tugmasi -->
              ${userRole === 'office_head' && app.status === 'disputed' ? `
                <button onclick="openEscalateModal(${app.id})" class="px-3.5 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold transition cursor-pointer flex items-center gap-1.5 shadow-md shadow-amber-600/20">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>
                  <span>Prorektorga eskalatsiya</span>
                </button>
              ` : ''}
            </div>
          </div>
        `;
      });
      container.innerHTML = html;
    }

    function changeAppealsPage(page) {
      const totalPages = Math.ceil(currentFilteredAppeals.length / appealsPerPage) || 1;
      if (page < 1 || page > totalPages) return;
      appealsCurrentPage = page;
      renderAppealsCurrentPage();
      const listEl = document.getElementById('tab-appeals');
      if (listEl) {
        listEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }

    function changeAppealsPerPage(val) {
      appealsPerPage = parseInt(val) || 10;
      appealsCurrentPage = 1;
      renderAppealsCurrentPage();
    }

    // Export to Excel (.xls with formatting and styles)
    function exportAppealsToExcel() {
      if (!allStaffAppeals || allStaffAppeals.length === 0) {
        showToast("Eksport qilish uchun murojaatlar mavjud emas.", "warning");
        return;
      }

      const headers = [
        "Talon raqami",
        "Mavzu",
        "Xizmat nomi",
        "Talaba F.I.Sh.",
        "HEMIS ID",
        "Ta'lim shakli",
        "Holati",
        "Yaratilgan sana",
        "SLA muddati",
        "Mas'ul ijrochi",
        "Ijro javobi",
        "Talaba bahosi"
      ];

      const rows = allStaffAppeals.map(a => [
        a.ticket_number || '—',
        a.subject || '—',
        a.service?.title || '—',
        a.student?.full_name || '—',
        a.student?.username || '—',
        a.student?.education_form || '—',
        STATUS_META[a.status]?.label || a.status,
        a.created_at ? new Date(a.created_at).toLocaleString('uz-UZ') : '—',
        a.sla_deadline_at ? new Date(a.sla_deadline_at).toLocaleString('uz-UZ') : '—',
        a.assigned_staff?.full_name || 'Biriktirilmagan',
        a.resolution_text || '—',
        a.rating ? a.rating + ' yulduz' : 'Baholanmagan'
      ]);

      const now = new Date().toLocaleDateString('uz-UZ');
      const filename = `Registrator_Ofisi_Murojaatlar_${new Date().toISOString().slice(0, 10)}.xls`;
      
      exportToExcelXls(
        filename,
        "Murojaatlar",
        "JIZZAX DAVLAT PEDAGOGIKA UNIVERSITETI - REGISTRATOR OFISI MUROJAATLAR REYESTRI",
        [
          `Hujjat turi: Rasmiy murojaatlar va ijro monitoringi jurnali`,
          `Shakllantirilgan sana: ${now} | Jami yuklangan murojaatlar soni: ${rows.length} ta`
        ],
        headers,
        rows
      );
      showToast("Murojaatlar formati saqlangan Excel (.xls) fayliga yuklab olindi!", "success");
    }
    window.exportAppealsToExcel = exportAppealsToExcel;

    // Reassign Modal Logic
    async function openReassignModal(appealId) {
      const app = (allStaffAppeals || []).find(a => a.id === appealId);
      const ticket = app ? app.ticket_number : '—';
      const studentName = app && app.student ? app.student.full_name : 'Talaba';
      const serviceTitle = app && app.service ? app.service.title : '—';
      const currentStaffId = app ? app.assigned_staff_id : null;

      document.getElementById('reassign-appeal-id').value = appealId;
      document.getElementById('reassign-modal-ticket').textContent = 'Talon: #' + ticket;
      document.getElementById('reassign-info-student').textContent = studentName || '—';
      document.getElementById('reassign-info-service').textContent = serviceTitle || '—';
      document.getElementById('reassign-modal-alert').className = 'hidden p-3 rounded-xl text-xs font-medium border';

      const select = document.getElementById('reassign-staff-select');
      select.innerHTML = '<option value="">Xodimlar yuklanmoqda...</option>';

      document.getElementById('reassign-appeal-modal').classList.remove('hidden');

      try {
        if (!cachedStaffUsers || cachedStaffUsers.length === 0) {
          const resp = await fetch('/api/v1/users/staff', {
            headers: { 'Authorization': 'Bearer ' + token }
          });
          if (resp.ok) {
            cachedStaffUsers = await resp.json();
          }
        }

        let opts = '<option value="">-- Mas\'ul xodimni tanlang --</option>';
        cachedStaffUsers.forEach(u => {
          const sel = (currentStaffId && u.id === currentStaffId) ? 'selected' : '';
          opts += `<option value="${u.id}" ${sel}>${u.full_name} (${u.role || 'xodim'})</option>`;
        });
        select.innerHTML = opts;
      } catch (err) {
        select.innerHTML = '<option value="">Xodimlarni yuklab bo\'lmadi</option>';
      }
    }

    function closeReassignModal() {
      document.getElementById('reassign-appeal-modal').classList.add('hidden');
    }

    async function handleReassignSubmit(e) {
      e.preventDefault();
      const appealId = document.getElementById('reassign-appeal-id').value;
      const staffId = document.getElementById('reassign-staff-select').value;
      const alertBox = document.getElementById('reassign-modal-alert');
      const btn = document.getElementById('reassign-submit-btn');

      if (!staffId) {
        alertBox.className = 'p-3 rounded-xl text-xs font-medium border bg-rose-500/10 border-rose-500/30 text-rose-400 block';
        alertBox.textContent = 'Iltimos, xodimni tanlang.';
        return;
      }

      btn.disabled = true;
      btn.textContent = 'Biriktirilmoqda...';

      try {
        const resp = await fetch(`/api/v1/appeals/${appealId}/assign`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
          },
          body: JSON.stringify({ staff_id: parseInt(staffId) })
        });

        if (resp.ok) {
          closeReassignModal();
          loadStaffAppeals();
        } else {
          const err = await resp.json();
          alertBox.className = 'p-3 rounded-xl text-xs font-medium border bg-rose-500/10 border-rose-500/30 text-rose-400 block';
          alertBox.textContent = err.detail || 'Biriktirishda xatolik yuz berdi.';
        }
      } catch (err) {
        alertBox.className = 'p-3 rounded-xl text-xs font-medium border bg-rose-500/10 border-rose-500/30 text-rose-400 block';
        alertBox.textContent = 'Server bilan aloqa uzildi.';
      } finally {
        btn.disabled = false;
        btn.textContent = 'Biriktirishni tasdiqlash';
      }
    }

    async function assignToMe(id) {
      if (!currentUser) return;
      const resp = await fetch(`/api/v1/appeals/${id}/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
        body: JSON.stringify({ staff_id: currentUser.id })
      });
      if (resp.ok) {
        showToast('Murojaat sizga muvaffaqiyatli biriktirildi.', 'success');
        loadStaffAppeals();
      } else {
        const err = await resp.json();
        showToast(err.detail || 'Biriktirish xatosi', 'error');
      }
    }

    // Resolve Modal
    function openResolveModal(id) {
      const app = (allStaffAppeals || []).find(a => a.id === id);
      const ticket = app ? app.ticket_number : '—';
      const subject = app ? (app.subject || '—') : '—';
      const service = app && app.service ? app.service.title : '—';

      document.getElementById('resolve-appeal-id').value = id;
      document.getElementById('resolve-modal-ticket').textContent = `Talon: #${ticket}`;
      document.getElementById('resolve-info-subject').textContent = subject;
      document.getElementById('resolve-info-service').textContent = service;
      document.getElementById('resolve-resolution-text').value = '';
      document.getElementById('resolve-file-url').value = '';
      document.getElementById('resolve-modal-alert').classList.add('hidden');
      document.getElementById('resolve-appeal-modal').classList.remove('hidden');
    }

    function closeResolveModal() {
      document.getElementById('resolve-appeal-modal').classList.add('hidden');
      const fileInput = document.getElementById('staff-resolve-file-input');
      if (fileInput) fileInput.value = '';
      const label = document.getElementById('staff-upload-label');
      if (label) label.innerText = 'Faylni yuklash (PDF, DOCX)...';
      const statusEl = document.getElementById('staff-upload-status');
      if (statusEl) statusEl.innerText = '';
    }

    async function handleStaffFileUpload(inputEl) {
      const file = inputEl.files[0];
      if (!file) return;

      const label = document.getElementById('staff-upload-label');
      const statusEl = document.getElementById('staff-upload-status');
      const urlInput = document.getElementById('resolve-file-url');

      label.innerText = `Yuklanmoqda: ${file.name}...`;
      statusEl.innerText = "Yuklanmoqda...";
      statusEl.className = "text-[11px] text-blue-400";

      const formData = new FormData();
      formData.append('file', file);

      try {
        const resp = await fetch('/api/v1/uploads', {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + token },
          body: formData
        });
        const res = await resp.json();

        if (resp.ok && res.file_url) {
          urlInput.value = res.file_url;
          label.innerHTML = `<span class="text-emerald-400 font-medium">✓ ${file.name}</span>`;
          statusEl.innerText = `(${(res.size_bytes / 1024).toFixed(1)} KB)`;
          statusEl.className = "text-[11px] text-emerald-400";
        } else {
          label.innerText = 'Faylni yuklash (PDF, DOCX)...';
          statusEl.innerText = res.detail || "Xatolik";
          statusEl.className = "text-[11px] text-rose-400";
          inputEl.value = '';
        }
      } catch (err) {
        label.innerText = 'Faylni yuklash (PDF, DOCX)...';
        statusEl.innerText = "Server xatosi";
        statusEl.className = "text-[11px] text-rose-400";
        inputEl.value = '';
      }
    }

    async function handleResolveSubmit(e) {
      e.preventDefault();
      const id = document.getElementById('resolve-appeal-id').value;
      const text = document.getElementById('resolve-resolution-text').value.trim();
      const fileUrl = document.getElementById('resolve-file-url').value.trim() || null;
      const alertBox = document.getElementById('resolve-modal-alert');

      const submitBtn = e.target.querySelector('[type=submit]');
      submitBtn.disabled = true;
      submitBtn.textContent = 'Yuklanmoqda...';

      try {
        const resp = await fetch(`/api/v1/appeals/${id}/resolve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
          body: JSON.stringify({ resolution_text: text, result_file_url: fileUrl })
        });
        const data = await resp.json();
        if (resp.ok) {
          closeResolveModal();
          showToast('Murojaat muvaffaqiyatli yakunlandi. KPI bali avtomatik qo\'shildi.', 'success');
          loadStaffAppeals();
        } else {
          alertBox.className = 'p-3 rounded-xl text-xs font-medium border bg-rose-500/10 border-rose-500/30 text-rose-400 block';
          alertBox.textContent = data.detail || 'Xatolik yuz berdi.';
        }
      } catch (err) {
        alertBox.className = 'p-3 rounded-xl text-xs font-medium border bg-rose-500/10 border-rose-500/30 text-rose-400 block';
        alertBox.textContent = 'Server bilan aloqa o\'rnatib bo\'lmadi.';
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Javobni yuklash va yakunlash';
      }
    }

    // Escalate Modal
    function openEscalateModal(id) {
      document.getElementById('escalate-appeal-id').value = id;
      document.getElementById('escalate-note').value = '';
      document.getElementById('escalate-modal').classList.remove('hidden');
    }

    function closeEscalateModal() {
      document.getElementById('escalate-modal').classList.add('hidden');
    }

    async function handleEscalateSubmit(e) {
      e.preventDefault();
      const id = document.getElementById('escalate-appeal-id').value;
      const note = document.getElementById('escalate-note').value.trim();
      try {
        const resp = await fetch(`/api/v1/appeals/${id}/escalate-prorektor`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
          body: JSON.stringify({ head_note: note })
        });
        if (resp.ok) {
          closeEscalateModal();
          showToast('Murojaat prorektorga muvaffaqiyatli yo\'naltirildi.', 'success');
          loadStaffAppeals();
        } else {
          const err = await resp.json();
          showToast(err.detail || 'Eskalatsiya xatosi', 'error');
        }
      } catch (err) {
        showToast('Server bilan aloqa o\'rnatib bo\'lmadi.', 'error');
      }
    }

    // ======================================================
    // PROREKTOR FINAL DECISION MODAL HANDLERS
    // ======================================================
    function openProrektorDecisionModal(id) {
      const appeal = allStaffAppeals.find(a => a.id === id);
      if (!appeal) return;

      document.getElementById('prorektor-appeal-id').value = id;
      document.getElementById('prorektor-final-decision-text').value = '';

      const infoBox = document.getElementById('prorektor-modal-appeal-info');
      infoBox.innerHTML = `
        <div class="flex items-center justify-between pb-2 border-b border-slate-800">
          <strong class="font-mono text-emerald-400">#${appeal.ticket_number}</strong>
          <span class="text-slate-400">${appeal.service ? appeal.service.title : '—'}</span>
        </div>
        <div>
          <span class="text-slate-400 block text-[10px] uppercase font-bold">Talaba:</span>
          <span class="text-white font-medium">${appeal.student ? appeal.student.full_name : 'Talaba'} (${appeal.student?.username || ''})</span>
        </div>
        <div>
          <span class="text-slate-400 block text-[10px] uppercase font-bold">Murojaat mavzusi:</span>
          <span class="text-slate-200">${appeal.subject}</span>
        </div>
        ${appeal.resolution_text ? `
          <div class="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
            <span class="text-emerald-400 block text-[10px] uppercase font-bold">Ijrochining dastlabki xulosasi:</span>
            <span class="text-slate-300 text-[11px]">${appeal.resolution_text}</span>
          </div>
        ` : ''}
        ${appeal.dispute_reason ? `
          <div class="p-2.5 rounded-lg bg-rose-950/40 border border-rose-500/30 text-rose-200">
            <span class="text-rose-400 block text-[10px] uppercase font-bold">Talaba e'tirozi (vajlari):</span>
            <span class="text-[11px]">${appeal.dispute_reason}</span>
          </div>
        ` : ''}
        ${appeal.clarification_message ? `
          <div class="p-2.5 rounded-lg bg-purple-950/40 border border-purple-500/30 text-purple-200">
            <span class="text-purple-300 block text-[10px] uppercase font-bold">Boshliqning eskalatsiya yozuvi:</span>
            <span class="text-[11px]">${appeal.clarification_message}</span>
          </div>
        ` : ''}
      `;

      document.getElementById('prorektor-decision-modal').classList.remove('hidden');
    }

    function closeProrektorDecisionModal() {
      document.getElementById('prorektor-decision-modal').classList.add('hidden');
    }

    async function handleProrektorDecisionSubmit(e) {
      e.preventDefault();
      const id = document.getElementById('prorektor-appeal-id').value;
      const decision = document.getElementById('prorektor-final-decision-text').value.trim();
      const btn = document.getElementById('prorektor-submit-btn');

      btn.disabled = true;
      btn.innerHTML = '<span>Tasdiqlanmoqda...</span>';

      try {
        const resp = await fetch(`/api/v1/appeals/${id}/prorektor-decision`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
          body: JSON.stringify({ final_decision: decision })
        });
        const res = await resp.json();
        if (resp.ok) {
          closeProrektorDecisionModal();
          showToast('Prorektorning yakuniy qarori tasdiqlandi va murojaat yopildi.', 'success');
          loadStaffAppeals();
        } else {
          showToast(res.detail || 'Qaror chiqarishda xatolik', 'error');
        }
      } catch (err) {
        showToast('Server bilan aloqa uzildi: ' + err, 'error');
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>Qarorni tasdiqlash va yopish</span>';
      }
    }

    // ======================================================
    // APPEAL AUDIT TRAIL MODAL (XRONOLOGIYA & AUDIT)
    // ======================================================
    function openAppealAuditModal(id) {
      const appeal = allStaffAppeals.find(a => a.id === id);
      if (!appeal) return;

      document.getElementById('audit-modal-ticket-sub').innerText = `Talon: #${appeal.ticket_number} • ${appeal.service ? appeal.service.title : ''}`;
      const timeline = document.getElementById('audit-modal-timeline');

      const steps = [];

      // Step 1: Created
      if (appeal.created_at) {
        steps.push({
          title: "Murojaat yaratildi",
          time: formatDateTime(appeal.created_at),
          desc: `Talaba (${appeal.student ? appeal.student.full_name : 'Talaba'}) tizim orqali arizani yo'lladi.`,
          badge: "Kelib tushdi",
          borderCls: "border-blue-500",
          textCls: "text-blue-400"
        });
      }

      // Step 2: Assigned
      if (appeal.assigned_at || appeal.assigned_staff) {
        steps.push({
          title: "Xodimga biriktirildi",
          time: appeal.assigned_at ? formatDateTime(appeal.assigned_at) : '—',
          desc: `Mas'ul ijrochi: ${appeal.assigned_staff ? appeal.assigned_staff.full_name : 'Belgilanmagan'}`,
          badge: "Ijroda",
          borderCls: "border-amber-500",
          textCls: "text-amber-400"
        });
      }

      // Step 3: Resolved
      if (appeal.resolved_at || appeal.resolution_text) {
        steps.push({
          title: "Ijrochi xulosasi tayyorlandi",
          time: appeal.resolved_at ? formatDateTime(appeal.resolved_at) : '—',
          desc: appeal.resolution_text || "Xizmat ko'rsatildi.",
          badge: "Hal etildi",
          borderCls: "border-emerald-500",
          textCls: "text-emerald-400"
        });
      }

      // Step 4: Disputed
      if (appeal.dispute_reason) {
        steps.push({
          title: "Talaba tomonidan e'tiroz (nizo) bildirildi",
          time: "—",
          desc: appeal.dispute_reason,
          badge: "Nizoli",
          borderCls: "border-rose-500",
          textCls: "text-rose-400"
        });
      }

      // Step 5: Escalated
      if (appeal.status === 'escalated_prorektor' || (appeal.clarification_message && appeal.status === 'completed')) {
        steps.push({
          title: "Prorektor nazoratiga uzatildi (Eskalatsiya)",
          time: "—",
          desc: appeal.clarification_message || "Rahbariyat ko'rigiga yo'naltirildi.",
          badge: "Eskalatsiya",
          borderCls: "border-purple-500",
          textCls: "text-purple-300"
        });
      }

      // Step 6: Rating / Completed
      if (appeal.status === 'completed') {
        steps.push({
          title: "Murojaat to'liq yakunlandi",
          time: appeal.closed_at ? formatDateTime(appeal.closed_at) : '—',
          desc: appeal.rating ? `Talaba bahosi: ${'★'.repeat(appeal.rating)} (${appeal.rating}/5). Izoh: ${appeal.rating_comment || 'Izohsiz'}` : "Yakuniy qaror asosida yopildi.",
          badge: "Yakunlangan",
          borderCls: "border-emerald-500",
          textCls: "text-emerald-400"
        });
      }

      timeline.innerHTML = steps.map((s, idx) => `
        <div class="relative pl-6 pb-3 border-l-2 border-slate-800 last:border-l-0">
          <span class="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-slate-900 border-2 ${s.borderCls} flex items-center justify-center text-[9px] ${s.textCls} font-bold">
            ${idx + 1}
          </span>
          <div class="space-y-1">
            <div class="flex items-center justify-between gap-2 flex-wrap">
              <strong class="text-xs text-white font-semibold">${s.title}</strong>
              <span class="text-[10px] text-slate-500">${s.time}</span>
            </div>
            <p class="text-xs text-slate-300 leading-relaxed">${s.desc}</p>
          </div>
        </div>
      `).join('');

      document.getElementById('appeal-audit-modal').classList.remove('hidden');
    }

    function closeAppealAuditModal() {
      document.getElementById('appeal-audit-modal').classList.add('hidden');
    }

    // Clarify Modal
    function openClarifyModal(id) {
      document.getElementById('clarify-appeal-id').value = id;
      document.getElementById('clarify-message').value = '';
      document.getElementById('clarify-modal').classList.remove('hidden');
    }

    function closeClarifyModal() {
      document.getElementById('clarify-modal').classList.add('hidden');
    }

    async function handleClarifySubmit(e) {
      e.preventDefault();
      const id = document.getElementById('clarify-appeal-id').value;
      const msg = document.getElementById('clarify-message').value.trim();
      try {
        const resp = await fetch(`/api/v1/appeals/${id}/request-clarification`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
          body: JSON.stringify({ clarification_message: msg })
        });
        if (resp.ok) {
          closeClarifyModal();
          showToast("Ma'lumot so'rovi talabaga yuborildi. SLA taymeri to'xtatildi.", 'info');
          loadStaffAppeals();
        } else {
          const err = await resp.json();
          showToast(err.detail || 'Xatolik', 'error');
        }
      } catch (err) {
        showToast('Server bilan aloqa o\'rnatib bo\'lmadi.', 'error');
      }
    }
