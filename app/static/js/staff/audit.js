async function loadAuditLogs() {
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
        queryParams.set('limit', '100');
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

        const data = await resp.json();
        auditLogsData = data || [];

        // 1. Stat kartalarini hisoblash
        updateAuditStats(auditLogsData);

        // 2. Jadvalni chizish
        renderAuditLogsTable(auditLogsData);

      } catch (err) {
        console.error("Audit logs error:", err);
        showToast("Audit loglarini yuklashda xatolik yuz berdi.", "error");
      } finally {
        if (btn) btn.disabled = false;
        if (icon) icon.classList.remove('animate-spin');
      }
    }

    function updateAuditStats(logs) {
      const totalEl = document.getElementById('audit-stat-total');
      const authEl = document.getElementById('audit-stat-auth');
      const appealsEl = document.getElementById('audit-stat-appeals');
      const queueEl = document.getElementById('audit-stat-queue');

      const total = logs.length;
      let authCount = 0;
      let appealsCount = 0;
      let queueCount = 0;

      logs.forEach(l => {
        const ent = (l.entity_type || '').toLowerCase();
        if (ent === 'auth' || ent === 'user' || ent === 'role') authCount++;
        else if (ent === 'appeal') appealsCount++;
        else if (ent === 'appointment' || ent === 'service' || ent === 'department') queueCount++;
      });

      if (totalEl) totalEl.innerText = total.toLocaleString();
      if (authEl) authEl.innerText = authCount.toLocaleString();
      if (appealsEl) appealsEl.innerText = appealsCount.toLocaleString();
      if (queueEl) queueEl.innerText = queueCount.toLocaleString();
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
        // Date formatting
        const dateStr = l.created_at ? formatDateTime(l.created_at) : '—';

        // Action badge styling
        const act = (l.action || '').toUpperCase();
        let actClass = 'bg-slate-800 text-slate-300 border-slate-700';
        if (act.includes('LOGIN')) actClass = 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20';
        else if (act.includes('CREATE')) actClass = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
        else if (act.includes('UPDATE') || act.includes('RESOLVE')) actClass = 'bg-blue-500/10 text-blue-400 border-blue-500/20';
        else if (act.includes('DISPUTE') || act.includes('REJECT')) actClass = 'bg-rose-500/10 text-rose-400 border-rose-500/20';
        else if (act.includes('CALL')) actClass = 'bg-amber-500/10 text-amber-400 border-amber-500/20';
        else if (act.includes('COMPLETE')) actClass = 'bg-teal-500/10 text-teal-400 border-teal-500/20';

        // Entity formatting
        const ent = escapeHtml(l.entity_type || '—');
        const entId = l.entity_id ? ` <span class="text-slate-500 font-mono text-[10px]">#${escapeHtml(String(l.entity_id))}</span>` : '';

        // User formatting
        const userName = escapeHtml(l.user_full_name || 'Tizim / Noma\'lum');
        const userRole = l.user_role ? `<span class="px-1.5 py-0.5 rounded text-[9px] font-sans uppercase font-bold bg-slate-800 text-slate-400 border border-slate-700 ml-1.5">${escapeHtml(l.user_role)}</span>` : '';

        // IP address
        const ip = escapeHtml(l.ip_address || '—');

        // Details / Changes formatting
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

    function exportAuditLogsToCsv() {
      if (!auditLogsData || auditLogsData.length === 0) {
        showToast("Eksport qilish uchun audit ma'lumotlari mavjud emas.", "warning");
        return;
      }

      let csv = "\uFEFF"; // UTF-8 BOM
      csv += `"ID","Sana va vaqt","Foydalanuvchi","Rol","Amal (Action)","Obyekt turi","Obyekt ID","IP manzil","Tafsilotlar"\n`;

      auditLogsData.forEach(l => {
        let dateStr = l.created_at || '';
        try {
          const d = new Date(l.created_at);
          dateStr = d.toISOString().replace('T', ' ').slice(0, 19);
        } catch (e) { }

        let changesStr = '';
        if (l.changes) {
          changesStr = typeof l.changes === 'string' ? l.changes : JSON.stringify(l.changes);
        }

        const row = [
          l.id || '',
          dateStr,
          (l.user_full_name || '').replace(/"/g, '""'),
          (l.user_role || '').replace(/"/g, '""'),
          (l.action || '').replace(/"/g, '""'),
          (l.entity_type || '').replace(/"/g, '""'),
          l.entity_id || '',
          (l.ip_address || '').replace(/"/g, '""'),
          changesStr.replace(/"/g, '""')
        ];
        csv += `"${row.join('","')}"\n`;
      });

      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.setAttribute("href", url);
      const safeDate = new Date().toISOString().slice(0, 10);
      link.setAttribute("download", `Registrator_Ofisi_Audit_Jurnali_${safeDate}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      showToast("Audit jurnali CSV formatida muvaffaqiyatli yuklab olindi!", "success");
    }

    // ================= 16. SYSTEM MONITORING & BACKUPS =================
