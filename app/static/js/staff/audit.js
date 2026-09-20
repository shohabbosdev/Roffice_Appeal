    // 15. Centralized Audit Logs Management System with Full Server-Side Pagination
    let auditLogsData = [];
    let auditCurrentPage = 1;
    let auditPerPage = 15;
    let auditTotalCount = 0;

    async function loadAuditLogs(page = 1) {
      auditCurrentPage = page;
      const entityFilter = document.getElementById('audit-entity-filter');
      const actionFilter = document.getElementById('audit-action-filter');
      const searchInput = document.getElementById('audit-search-input');

      const entityVal = entityFilter ? entityFilter.value.trim() : '';
      const actionVal = actionFilter ? actionFilter.value.trim() : '';
      const searchVal = searchInput ? searchInput.value.trim() : '';

      const btn = document.getElementById('refresh-audit-btn');
      const icon = document.getElementById('refresh-audit-icon');
      if (btn) btn.disabled = true;
      if (icon) icon.classList.add('animate-spin');

      try {
        const queryParams = new URLSearchParams();
        queryParams.set('limit', String(auditPerPage));
        queryParams.set('offset', String((auditCurrentPage - 1) * auditPerPage));
        if (entityVal) queryParams.set('entity_type', entityVal);
        if (actionVal) queryParams.set('action', actionVal);
        if (searchVal) queryParams.set('search', searchVal);

        const resp = await fetch(`/api/v1/audit-logs?${queryParams.toString()}`, {
          headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });

        if (!resp.ok) {
          if (resp.status === 403) {
            showToast("Audit jurnali faqat Admin, Boshliq va Prorektor uchun ochiq.", "warning");
          } else {
            showToast("Audit jurnalini yuklab bo'lmadi.", "error");
          }
          return;
        }

        const totalHeader = resp.headers.get('X-Total-Count');
        const data = await resp.json();
        auditLogsData = data || [];

        auditTotalCount = totalHeader !== null ? parseInt(totalHeader, 10) : auditLogsData.length;

        // 1. Stat kartalarini yangilash
        loadAuditStatsSummary(auditTotalCount);

        // 2. Jadvalni chizish
        renderAuditLogsTable(auditLogsData);

        // 3. Sahifalash kontrollerlarini render qilish
        renderAuditPagination();

      } catch (err) {
        console.error("Audit logs error:", err);
        showToast("Audit loglarini yuklashda xatolik yuz berdi.", "error");
      } finally {
        if (btn) btn.disabled = false;
        if (icon) icon.classList.remove('animate-spin');
      }
    }

    async function loadAuditStatsSummary(currentFilteredTotal) {
      const totalEl = document.getElementById('audit-stat-total');
      const authEl = document.getElementById('audit-stat-auth');
      const appealsEl = document.getElementById('audit-stat-appeals');
      const queueEl = document.getElementById('audit-stat-queue');

      try {
        const resp = await fetch('/api/v1/audit-logs/weekly-summary', {
          headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        if (resp.ok) {
          const report = await resp.json();
          const eb = report.entities_breakdown || {};
          if (totalEl) totalEl.innerText = (currentFilteredTotal !== undefined ? currentFilteredTotal : report.total_audit_records || 0).toLocaleString();
          if (authEl) authEl.innerText = ((eb.auth || 0) + (eb.user || 0) + (eb.role || 0)).toLocaleString();
          if (appealsEl) appealsEl.innerText = (eb.appeal || 0).toLocaleString();
          if (queueEl) queueEl.innerText = ((eb.appointment || 0) + (eb.service || 0) + (eb.department || 0)).toLocaleString();
        } else {
          if (totalEl) totalEl.innerText = (currentFilteredTotal || 0).toLocaleString();
        }
      } catch (e) {
        if (totalEl) totalEl.innerText = (currentFilteredTotal || 0).toLocaleString();
      }
    }

    function renderAuditLogsTable(logs) {
      const tbody = document.getElementById('audit-logs-table-body');
      if (!tbody) return;

      if (!logs || logs.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="6" class="p-8 text-center text-xs font-sans text-slate-500">
              Ushbu filtr bo'yicha hech qanday audit yozuvi topilmadi.
            </td>
          </tr>
        `;
        return;
      }

      const rows = logs.map(l => {
        const dateStr = l.created_at ? formatDateTime(l.created_at) : '—';

        const act = (l.action || '').toUpperCase();
        let actClass = 'bg-slate-800 text-slate-300 border-slate-700';
        if (act.includes('LOGIN')) actClass = 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20';
        else if (act.includes('CREATE')) actClass = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
        else if (act.includes('UPDATE') || act.includes('RESOLVE')) actClass = 'bg-blue-500/10 text-blue-400 border-blue-500/20';
        else if (act.includes('DISPUTE') || act.includes('REJECT')) actClass = 'bg-rose-500/10 text-rose-400 border-rose-500/20';
        else if (act.includes('CALL')) actClass = 'bg-amber-500/10 text-amber-400 border-amber-500/20';
        else if (act.includes('COMPLETE')) actClass = 'bg-teal-500/10 text-teal-400 border-teal-500/20';

        const ent = escapeHtml(l.entity_type || '—');
        const entId = l.entity_id ? ` <span class="text-slate-500 font-mono text-[10px]">#${escapeHtml(String(l.entity_id))}</span>` : '';

        const userName = escapeHtml(l.user_full_name || 'Tizim / Noma\'lum');
        const userRole = l.user_role ? `<span class="px-1.5 py-0.5 rounded text-[9px] font-sans uppercase font-bold bg-slate-800 text-slate-400 border border-slate-700 ml-1.5">${escapeHtml(l.user_role)}</span>` : '';

        const ip = escapeHtml(l.ip_address || '—');

        let detailsText = '';
        if (l.changes) {
          try {
            const parsed = typeof l.changes === 'string' ? JSON.parse(l.changes) : l.changes;
            const keys = Object.keys(parsed);
            if (keys.length > 0) {
              detailsText = keys.map(k => `<span class="text-slate-400">${escapeHtml(k)}:</span> <span class="text-slate-200">${escapeHtml(String(parsed[k]))}</span>`).join(', ');
            }
          } catch (e) {
            detailsText = escapeHtml(String(l.changes));
          }
        }
        if (!detailsText) detailsText = '<span class="text-slate-600 italic">Qo\'shimcha tafsilot yo\'q</span>';

        return `
          <tr class="hover:bg-slate-800/30 transition">
            <td class="p-3 text-slate-400 whitespace-nowrap">${dateStr}</td>
            <td class="p-3 font-sans font-medium text-white whitespace-nowrap">${userName}${userRole}</td>
            <td class="p-3 text-center whitespace-nowrap">
              <span class="inline-block px-2.5 py-1 rounded-lg text-[10px] font-extrabold border uppercase ${actClass}">
                ${escapeHtml(act)}
              </span>
            </td>
            <td class="p-3 whitespace-nowrap">
              <span class="px-2 py-0.5 rounded bg-slate-800/80 border border-slate-700/60 text-slate-300">${ent}</span>${entId}
            </td>
            <td class="p-3 text-slate-400 font-mono text-[10px] whitespace-nowrap">${ip}</td>
            <td class="p-3 text-slate-300 font-sans text-xs max-w-xs sm:max-w-md truncate" title="${escapeHtml(typeof l.changes === 'object' ? JSON.stringify(l.changes) : String(l.changes || ''))}">
              ${detailsText}
            </td>
          </tr>
        `;
      }).join('');

      tbody.innerHTML = rows;
    }

    function changeAuditPage(newPage) {
      if (newPage < 1) return;
      const totalPages = Math.ceil(auditTotalCount / auditPerPage) || 1;
      if (newPage > totalPages) return;
      loadAuditLogs(newPage);
    }

    function changeAuditPerPage(val) {
      auditPerPage = parseInt(val, 10) || 15;
      auditCurrentPage = 1;
      loadAuditLogs(1);
    }

    function renderAuditPagination() {
      const paginationBar = document.getElementById('audit-pagination-bar');
      const pageInfo = document.getElementById('audit-page-info');
      const paginationButtons = document.getElementById('audit-pagination-buttons');

      if (!paginationBar) return;

      const total = auditTotalCount;
      const totalPages = Math.ceil(total / auditPerPage) || 1;

      if (total === 0) {
        paginationBar.classList.remove('flex');
        paginationBar.classList.add('hidden');
        return;
      }

      paginationBar.classList.remove('hidden');
      paginationBar.classList.add('flex');

      const startIdx = (auditCurrentPage - 1) * auditPerPage;
      const endIdx = Math.min(startIdx + auditPerPage, total);

      if (pageInfo) {
        pageInfo.textContent = `${startIdx + 1}-${endIdx} / ${total}`;
      }

      if (paginationButtons) {
        let btnsHtml = '';

        // Oldingi tugmasi
        btnsHtml += `
          <button 
            type="button" 
            onclick="changeAuditPage(${auditCurrentPage - 1})" 
            ${auditCurrentPage <= 1 ? 'disabled class="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-950 text-slate-600 text-xs cursor-not-allowed"' : 'class="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-950 text-slate-300 hover:text-white hover:border-slate-700 text-xs cursor-pointer transition"'}
          >
            ◀ Oldingi
          </button>
        `;

        if (totalPages <= 7) {
          for (let p = 1; p <= totalPages; p++) {
            const isActive = p === auditCurrentPage;
            btnsHtml += `
              <button 
                type="button" 
                onclick="changeAuditPage(${p})" 
                class="w-7 h-7 flex items-center justify-center rounded-lg text-xs font-semibold transition cursor-pointer ${isActive ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30' : 'border border-slate-800 bg-slate-950 text-slate-400 hover:text-white hover:border-slate-700'}"
              >
                ${p}
              </button>
            `;
          }
        } else {
          btnsHtml += `
            <button 
              type="button" 
              onclick="changeAuditPage(1)" 
              class="w-7 h-7 flex items-center justify-center rounded-lg text-xs font-semibold transition cursor-pointer ${auditCurrentPage === 1 ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30' : 'border border-slate-800 bg-slate-950 text-slate-400 hover:text-white hover:border-slate-700'}"
            >
              1
            </button>
          `;

          let startPage = Math.max(2, auditCurrentPage - 1);
          let endPage = Math.min(totalPages - 1, auditCurrentPage + 1);

          if (startPage > 2) {
            btnsHtml += `<span class="text-slate-600 text-xs px-1">...</span>`;
          }

          for (let p = startPage; p <= endPage; p++) {
            const isActive = p === auditCurrentPage;
            btnsHtml += `
              <button 
                type="button" 
                onclick="changeAuditPage(${p})" 
                class="w-7 h-7 flex items-center justify-center rounded-lg text-xs font-semibold transition cursor-pointer ${isActive ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30' : 'border border-slate-800 bg-slate-950 text-slate-400 hover:text-white hover:border-slate-700'}"
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
              onclick="changeAuditPage(${totalPages})" 
              class="w-7 h-7 flex items-center justify-center rounded-lg text-xs font-semibold transition cursor-pointer ${auditCurrentPage === totalPages ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30' : 'border border-slate-800 bg-slate-950 text-slate-400 hover:text-white hover:border-slate-700'}"
            >
              ${totalPages}
            </button>
          `;
        }

        // Keyingi tugmasi
        btnsHtml += `
          <button 
            type="button" 
            onclick="changeAuditPage(${auditCurrentPage + 1})" 
            ${auditCurrentPage >= totalPages ? 'disabled class="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-950 text-slate-600 text-xs cursor-not-allowed"' : 'class="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-950 text-slate-300 hover:text-white hover:border-slate-700 text-xs cursor-pointer transition"'}
          >
            Keyingi ▶
          </button>
        `;

        paginationButtons.innerHTML = btnsHtml;
      }
    }

    async function exportAuditLogsToExcel() {
      const entityFilter = document.getElementById('audit-entity-filter');
      const actionFilter = document.getElementById('audit-action-filter');
      const searchInput = document.getElementById('audit-search-input');

      const entityVal = entityFilter ? entityFilter.value.trim() : '';
      const actionVal = actionFilter ? actionFilter.value.trim() : '';
      const searchVal = searchInput ? searchInput.value.trim() : '';

      showToast("Audit hisoboti Excel fayliga yuklanmoqda...", "info");

      let exportList = auditLogsData;
      try {
        const queryParams = new URLSearchParams();
        queryParams.set('limit', '500');
        queryParams.set('offset', '0');
        if (entityVal) queryParams.set('entity_type', entityVal);
        if (actionVal) queryParams.set('action', actionVal);
        if (searchVal) queryParams.set('search', searchVal);

        const resp = await fetch(`/api/v1/audit-logs?${queryParams.toString()}`, {
          headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        if (resp.ok) {
          const freshData = await resp.json();
          if (freshData && freshData.length > 0) {
            exportList = freshData;
          }
        }
      } catch (e) {
        console.warn("Kengaytirilgan eksport yuklab bo'lmadi, joriy sahifa olinmoqda:", e);
      }

      if (!exportList || exportList.length === 0) {
        showToast("Eksport qilish uchun audit ma'lumotlari mavjud emas.", "warning");
        return;
      }

      const headers = ["Log ID", "Sana va vaqt", "Foydalanuvchi", "Tizimdagi roli", "Amal (Action)", "Obyekt turi", "Obyekt ID", "IP manzil", "Amal tafsilotlari"];
      const rows = exportList.map(l => {
        let dateStr = l.created_at || '—';
        try {
          const d = new Date(l.created_at);
          dateStr = d.toLocaleString('uz-UZ');
        } catch (e) { }

        let changesStr = '—';
        if (l.changes) {
          changesStr = typeof l.changes === 'string' ? l.changes : JSON.stringify(l.changes);
        }

        return [
          `#${l.id || ''}`,
          dateStr,
          l.user_full_name || 'Tizim / Anonim',
          l.user_role || '—',
          l.action || '—',
          l.entity_type || '—',
          l.entity_id || '—',
          l.ip_address || '—',
          changesStr
        ];
      });

      const safeDate = new Date().toISOString().slice(0, 10);
      const filename = `Registrator_Ofisi_Audit_Jurnali_${safeDate}.xls`;

      exportToExcelXls(
        filename,
        "Audit Jurnali",
        "JIZZAX DAVLAT PEDAGOGIKA UNIVERSITETI - AXBOROT XAVFSIZLIGI VA AUDIT JURNALI",
        [
          `Hujjat turi: Tizim xavfsizlik harakatlari va tranzaksiyalar auditi`,
          `Shakllantirilgan sana: ${new Date().toLocaleString('uz-UZ')} | Jami yozuvlar: ${rows.length} ta`
        ],
        headers,
        rows
      );

      showToast("Audit jurnali formatlangan Excel (.xls) fayliga muvaffaqiyatli yuklab olindi!", "success");
    }

    window.loadAuditLogs = loadAuditLogs;
    window.changeAuditPage = changeAuditPage;
    window.changeAuditPerPage = changeAuditPerPage;
    window.exportAuditLogsToExcel = exportAuditLogsToExcel;
    window.exportAuditLogsToCsv = exportAuditLogsToExcel;
