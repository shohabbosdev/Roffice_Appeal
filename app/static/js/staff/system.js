async function loadSystemMetrics() {
      const token = localStorage.getItem('roffice_token');
      if (!token) return;

      try {
        const res = await fetch(apiUrl('/api/v1/system/metrics'), {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) {
          if (res.status === 403) return;
          throw new Error("Tizim ko'rsatkichlarini yuklab bo'lmadi");
        }
        const data = await res.json();

        // 1. Vaqt va holat
        const nowStr = new Date().toLocaleTimeString();
        const lastCheckedEl = document.getElementById('sys-last-checked-time');
        if (lastCheckedEl) lastCheckedEl.innerText = `Oxirgi tekshiruv: ${nowStr}`;

        const badgeEl = document.getElementById('sys-overall-status-badge');
        if (badgeEl) {
          if (data.status === 'healthy') {
            badgeEl.className = "px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5";
            badgeEl.innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> Barcha tizimlar barqaror';
          } else {
            badgeEl.className = "px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1.5";
            badgeEl.innerHTML = '<span class="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span> Diqqat: Yuqori yuklama';
          }
        }

        // 2. CPU
        if (data.cpu) {
          const cpuVal = document.getElementById('sys-cpu-val');
          const cpuCores = document.getElementById('sys-cpu-cores');
          const cpuLoad = document.getElementById('sys-cpu-load');
          const cpuBar = document.getElementById('sys-cpu-bar');

          const pct = data.cpu.percent_load || 0;
          if (cpuVal) cpuVal.innerText = `${pct}%`;
          if (cpuCores) cpuCores.innerText = `Cores: ${data.cpu.cores || 1}`;
          if (cpuLoad) cpuLoad.innerText = `Load: ${data.cpu.load_1m || 0.0}`;
          if (cpuBar) {
            cpuBar.style.width = `${Math.min(100, Math.max(2, pct))}%`;
            cpuBar.className = pct > 85 ? "h-full bg-rose-500 transition-all duration-500" : (pct > 60 ? "h-full bg-amber-500 transition-all duration-500" : "h-full bg-blue-500 transition-all duration-500");
          }
        }

        // 3. RAM
        if (data.ram) {
          const ramVal = document.getElementById('sys-ram-val');
          const ramUsage = document.getElementById('sys-ram-usage');
          const ramStatus = document.getElementById('sys-ram-status');
          const ramBar = document.getElementById('sys-ram-bar');

          const pct = data.ram.percent_used || 0;
          if (ramVal) ramVal.innerText = `${pct}%`;
          if (ramUsage) ramUsage.innerText = `${data.ram.used_human} / ${data.ram.total_human}`;
          if (ramStatus) {
            ramStatus.innerText = data.ram.status === 'healthy' ? 'Normal' : 'Yuqori';
            ramStatus.className = data.ram.status === 'healthy' ? 'text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400' : 'text-[10px] font-semibold px-2 py-0.5 rounded bg-rose-500/10 text-rose-400';
          }
          if (ramBar) {
            ramBar.style.width = `${Math.min(100, Math.max(2, pct))}%`;
            ramBar.className = pct > 85 ? "h-full bg-rose-500 transition-all duration-500" : "h-full bg-emerald-500 transition-all duration-500";
          }
        }

        // 4. Disk
        if (data.disk) {
          const diskVal = document.getElementById('sys-disk-val');
          const diskUsage = document.getElementById('sys-disk-usage');
          const diskFree = document.getElementById('sys-disk-free');
          const diskBar = document.getElementById('sys-disk-bar');

          const pct = data.disk.percent_used || 0;
          if (diskVal) diskVal.innerText = `${pct}%`;
          if (diskUsage) diskUsage.innerText = `${data.disk.used_human} / ${data.disk.total_human}`;
          if (diskFree) diskFree.innerText = `Free: ${data.disk.free_human}`;
          if (diskBar) {
            diskBar.style.width = `${Math.min(100, Math.max(2, pct))}%`;
            diskBar.className = pct > 85 ? "h-full bg-rose-500 transition-all duration-500" : "h-full bg-indigo-500 transition-all duration-500";
          }
        }

        // 5. Uptime & Env
        if (data.uptime) {
          const uptimeVal = document.getElementById('sys-uptime-val');
          if (uptimeVal) uptimeVal.innerText = data.uptime.uptime_str || 'Ishga tushgan';
        }
        if (data.environment) {
          const envOs = document.getElementById('sys-env-os');
          const envPy = document.getElementById('sys-env-python');
          if (envOs) envOs.innerText = `${data.environment.os} ${data.environment.os_release || ''}`;
          if (envPy) envPy.innerText = `Python ${data.environment.python_version || ''}`;
        }
        if (data.uptime && data.uptime.started_at) {
          const startedAt = document.getElementById('sys-started-at');
          try {
            const st = new Date(data.uptime.started_at);
            if (startedAt) startedAt.innerText = `Ishga tushdi: ${st.toLocaleDateString()} ${st.toLocaleTimeString()}`;
          } catch (e) { }
        }

        // 6. DB Stats
        if (data.database) {
          const db = data.database;
          const setTxt = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val !== undefined ? val : 0; };
          setTxt('sys-db-appeals', db.total_appeals);
          setTxt('sys-db-active-appeals', db.active_appeals);
          setTxt('sys-db-resolved-appeals', db.resolved_appeals);
          setTxt('sys-db-appointments', db.total_appointments);
          setTxt('sys-db-users', db.total_users);
          setTxt('sys-db-audits', db.total_audit_logs);
        }

      } catch (err) {
        console.error("loadSystemMetrics xatosi:", err);
      }
    }

    async function loadBackupsList() {
      const token = localStorage.getItem('roffice_token');
      const role = localStorage.getItem('roffice_role');
      if (!token || role !== 'admin') {
        const tbody = document.getElementById('backups-table-body');
        if (tbody) {
          tbody.innerHTML = '<tr><td colspan="4" class="p-8 text-center text-xs font-sans text-slate-500">Zaxira nusxalarini faqat Administrator boshqara oladi.</td></tr>';
        }
        return;
      }

      try {
        const res = await fetch(apiUrl('/api/v1/system/backups'), {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error("Zaxiralar ro'yxatini yuklab bo'lmadi");
        const backups = await res.json();

        const badge = document.getElementById('sys-backups-count-badge');
        if (badge) badge.innerText = `Jami zaxiralar: ${backups.length}`;

        const tbody = document.getElementById('backups-table-body');
        if (!tbody) return;

        if (!backups || backups.length === 0) {
          tbody.innerHTML = '<tr><td colspan="4" class="p-8 text-center text-xs font-sans text-slate-500">Hozircha zaxira nusxalari mavjud emas. "Hozir zaxira yaratish" tugmasini bosing.</td></tr>';
          return;
        }

        tbody.innerHTML = backups.map(b => {
          let dateStr = b.created_at || '';
          try {
            const d = new Date(b.created_at);
            dateStr = `${d.toLocaleDateString()} ${d.toLocaleTimeString()}`;
          } catch (e) { }

          return `
            <tr class="hover:bg-slate-800/40 transition">
              <td class="p-3 font-semibold text-white flex items-center gap-2">
                <svg class="w-4 h-4 text-amber-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"/>
                </svg>
                <span class="truncate max-w-xs sm:max-w-md">${escapeHtml(b.filename)}</span>
              </td>
              <td class="p-3 text-emerald-400 font-bold">${escapeHtml(b.size_human)}</td>
              <td class="p-3 text-slate-400 font-sans text-xs">${dateStr}</td>
              <td class="p-3 text-right">
                <button
                  onclick="downloadBackupFile('${escapeHtml(b.filename)}')"
                  class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-blue-400 hover:text-white border border-slate-700 transition inline-flex items-center gap-1.5 cursor-pointer"
                  title="Yuklab olish"
                >
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                  </svg>
                  <span>Yuklab olish</span>
                </button>
              </td>
            </tr>
          `;
        }).join('');

      } catch (err) {
        console.error("loadBackupsList xatosi:", err);
        const tbody = document.getElementById('backups-table-body');
        if (tbody) {
          tbody.innerHTML = `<tr><td colspan="4" class="p-8 text-center text-xs font-sans text-rose-400">${escapeHtml(err.message)}</td></tr>`;
        }
      }
    }

    async function triggerManualBackup() {
      if (!confirm("Haqiqatan ham hozir tizim ma'lumotlar bazasi va yuklangan hujjatlarning to'liq zaxira nusxasini (Backup) yaratmoqchimisiz?")) {
        return;
      }

      const token = localStorage.getItem('roffice_token');
      const btn = document.getElementById('btn-trigger-backup');
      const originalText = btn ? btn.innerHTML : '';

      if (btn) {
        btn.disabled = true;
        btn.innerHTML = `
          <svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
          </svg>
          <span>Zaxiralanmoqda...</span>
        `;
      }

      try {
        const res = await fetch(apiUrl('/api/v1/system/backups'), {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || "Zaxira yaratish jarayonida xatolik yuz berdi");
        }

        showToast(`Zaxira nusxasi muvaffaqiyatli yaratildi: ${data.filename} (${data.size_human})`, "success");
        await loadBackupsList();
        await loadSystemMetrics();

      } catch (err) {
        showToast(err.message, "error");
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = originalText;
        }
      }
    }

    async function downloadBackupFile(filename) {
      const token = localStorage.getItem('roffice_token');
      if (!token) return;

      try {
        showToast("Zaxira fayli yuklab olinmoqda...", "info");
        const res = await fetch(apiUrl(`/api/v1/system/backups/${encodeURIComponent(filename)}/download`), {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Faylni yuklab bo'lmadi");
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast("Zaxira fayli muvaffaqiyatli yuklab olindi!", "success");
      } catch (e) {
        showToast(e.message, "error");
      }
    }

    // 18. E'lonlar va Xabarnomalar Markazi Funksiyalari
