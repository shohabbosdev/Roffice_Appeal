async function loadAllServicesAndDepts() {
      const btn = document.getElementById('refresh-services-btn');
      const icon = document.getElementById('refresh-services-icon');
      const text = document.getElementById('refresh-services-text');
      if (btn) btn.disabled = true;
      if (icon) icon.classList.add('animate-spin');
      if (text) text.innerText = "Yangilanmoqda...";

      try {
        await Promise.all([loadDepartmentsList(), loadServicesCatalog()]);
        showToast("Xizmatlar va bo'limlar katalogi muvaffaqiyatli yangilandi!", "success");
      } catch (e) {
        console.error("Katalog ma'lumotlarini yuklashda xatolik:", e);
        showToast("Katalogni yangilashda xatolik yuz berdi.", "error");
      } finally {
        if (btn) btn.disabled = false;
        if (icon) icon.classList.remove('animate-spin');
        if (text) text.innerText = "Yangilash";
      }
    }

    function switchServicesSubtab(tab) {
      const sPane = document.getElementById('services-view-pane');
      const dPane = document.getElementById('departments-view-pane');
      const sBtn = document.getElementById('subtab-services-btn');
      const dBtn = document.getElementById('subtab-departments-btn');
      const filterBar = document.getElementById('services-filter-bar');

      if (tab === 'services') {
        sPane?.classList.remove('hidden');
        dPane?.classList.add('hidden');
        filterBar?.classList.remove('hidden');
        if (sBtn) sBtn.className = "px-3.5 py-2 rounded-xl text-xs font-semibold bg-emerald-600 text-white transition cursor-pointer";
        if (dBtn) dBtn.className = "px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer";
      } else {
        sPane?.classList.add('hidden');
        dPane?.classList.remove('hidden');
        filterBar?.classList.add('hidden');
        if (dBtn) dBtn.className = "px-3.5 py-2 rounded-xl text-xs font-semibold bg-blue-600 text-white transition cursor-pointer";
        if (sBtn) sBtn.className = "px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer";
      }
    }

    async function loadDepartmentsList() {
      try {
        const resp = await fetch('/api/v1/services/departments', {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });
        if (!resp.ok) return;
        allDepartmentsList = await resp.json();

        // Update counts
        const cntEl = document.getElementById('total-depts-count');
        if (cntEl) cntEl.innerText = allDepartmentsList.length;

        // Populate dropdowns in modals & filters
        const deptFilter = document.getElementById('services-dept-filter');
        if (deptFilter) {
          const curVal = deptFilter.value;
          deptFilter.innerHTML = '<option value="">Barcha bo\'limlar</option>' +
            allDepartmentsList.map(d => `<option value="${d.id}">${d.name}</option>`).join('');
          deptFilter.value = curVal;
        }

        const serviceDeptSelect = document.getElementById('service-dept');
        if (serviceDeptSelect) {
          serviceDeptSelect.innerHTML = '<option value="">Bo\'limni tanlang</option>' +
            allDepartmentsList.map(d => `<option value="${d.id}">${d.name} (${d.dept_type === 'front_office' ? 'Front: ' + (d.window_number || 'Darcha') : 'Back: Ijro'})</option>`).join('');
        }

        const newStaffDeptSelect = document.getElementById('new-staff-department');
        if (newStaffDeptSelect) {
          newStaffDeptSelect.innerHTML = '<option value="">Bo\'limni tanlang (ixtiyoriy)</option>' +
            allDepartmentsList.map(d => `<option value="${d.id}">${d.name} (${d.code})</option>`).join('');
        }

        const editStaffDeptSelect = document.getElementById('edit-staff-dept');
        if (editStaffDeptSelect) {
          editStaffDeptSelect.innerHTML = '<option value="">Bo\'lim biriktirilmagan</option>' +
            allDepartmentsList.map(d => `<option value="${d.id}">${d.name} (${d.code})</option>`).join('');
        }

        // Render departments grid with pagination
        renderDepartmentsGrid();
      } catch (e) {
        console.error("Bo'limlarni yuklashda xatolik:", e);
      }
    }

    let deptsCurrentPage = 1;
    let deptsPerPage = 6;

    function renderDepartmentsGrid() {
      const grid = document.getElementById('all-departments-grid');
      const pageInfo = document.getElementById('depts-page-info');
      const paginationButtons = document.getElementById('departments-pagination-buttons');
      if (!grid) return;

      const total = allDepartmentsList.length;
      const totalPages = Math.ceil(total / deptsPerPage) || 1;
      if (deptsCurrentPage > totalPages) deptsCurrentPage = totalPages;
      if (deptsCurrentPage < 1) deptsCurrentPage = 1;

      const start = (deptsCurrentPage - 1) * deptsPerPage;
      const end = Math.min(start + deptsPerPage, total);
      const pageItems = allDepartmentsList.slice(start, end);

      if (pageInfo) {
        pageInfo.innerText = total === 0 ? "0-0 / 0" : `${start + 1}-${end} / ${total}`;
      }

      // Render pagination buttons
      if (paginationButtons) {
        let btnsHtml = '';
        btnsHtml += `
          <button 
            type="button" 
            onclick="changeDeptsPage(${deptsCurrentPage - 1})" 
            ${deptsCurrentPage <= 1 ? 'disabled class="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-950 text-slate-600 text-xs cursor-not-allowed"' : 'class="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-950 text-slate-300 hover:text-white hover:border-slate-700 text-xs cursor-pointer"'}
          >
            ◀ Oldingi
          </button>
        `;

        for (let p = 1; p <= totalPages; p++) {
          if (totalPages > 7 && Math.abs(p - deptsCurrentPage) > 2 && p !== 1 && p !== totalPages) {
            if (p === 2 || p === totalPages - 1) btnsHtml += `<span class="px-1 text-slate-600">...</span>`;
            continue;
          }
          const isActive = p === deptsCurrentPage;
          btnsHtml += `
            <button 
              type="button" 
              onclick="changeDeptsPage(${p})" 
              class="px-2.5 py-1 rounded-lg text-xs font-semibold transition cursor-pointer ${isActive ? 'bg-blue-600 text-white shadow-sm' : 'bg-slate-950 border border-slate-800 text-slate-400 hover:text-white'}"
            >
              ${p}
            </button>
          `;
        }

        btnsHtml += `
          <button 
            type="button" 
            onclick="changeDeptsPage(${deptsCurrentPage + 1})" 
            ${deptsCurrentPage >= totalPages ? 'disabled class="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-950 text-slate-600 text-xs cursor-not-allowed"' : 'class="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-950 text-slate-300 hover:text-white hover:border-slate-700 text-xs cursor-pointer"'}
          >
            Keyingi ▶
          </button>
        `;
        paginationButtons.innerHTML = btnsHtml;
      }

      if (total === 0) {
        grid.innerHTML = '<div class="p-8 text-center text-xs text-slate-500 col-span-3 border border-slate-800/80 rounded-2xl bg-slate-900/40">Bo\'limlar mavjud emas.</div>';
        return;
      }

      grid.innerHTML = pageItems.map(d => `
        <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-3 relative group hover:border-slate-700 transition">
          <div class="flex items-center justify-between">
            <span class="font-mono text-xs font-bold text-blue-400">${d.code}</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-semibold ${d.dept_type === 'front_office' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'}">
              ${d.dept_type === 'front_office' ? 'Front-ofis (Darcha)' : 'Back-ofis (Ijro)'}
            </span>
          </div>
          <div>
            <h5 class="text-sm font-bold text-white">${d.name}</h5>
            <p class="text-xs text-slate-400 mt-1">Darcha: <strong class="text-slate-200">${d.window_number || 'Belgilanmagan'}</strong></p>
          </div>
          <div class="pt-3 border-t border-slate-800 flex items-center justify-end gap-2">
            <button type="button" onclick="openEditDeptModal(${d.id})" class="px-2.5 py-1 rounded-lg bg-blue-600/20 hover:bg-blue-600 text-blue-300 hover:text-white text-xs font-medium transition cursor-pointer">
              Tahrirlash
            </button>
            <button type="button" onclick="deleteDepartment(${d.id})" class="px-2.5 py-1 rounded-lg border border-slate-800 hover:border-rose-500/40 hover:bg-rose-500/10 text-slate-400 hover:text-rose-400 text-xs transition cursor-pointer">
              O'chirish
            </button>
          </div>
        </div>
      `).join('');
    }

    function changeDeptsPage(page) {
      deptsCurrentPage = page;
      renderDepartmentsGrid();
    }

    function changeDeptsPerPage(val) {
      deptsPerPage = parseInt(val) || 6;
      deptsCurrentPage = 1;
      renderDepartmentsGrid();
    }

    async function loadServicesCatalog() {
      try {
        const resp = await fetch('/api/v1/services?include_inactive=true', {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });
        if (!resp.ok) return;
        allServicesList = await resp.json();

        const cntEl = document.getElementById('total-services-count');
        if (cntEl) cntEl.innerText = allServicesList.length;

        filterServicesCatalog();
      } catch (e) {
        console.error("Xizmatlarni yuklashda xatolik:", e);
      }
    }

    let filteredServicesList = [];
    let servicesCurrentPage = 1;
    let servicesPerPage = 6;

    function filterServicesCatalog() {
      const q = document.getElementById('services-search-input')?.value.toLowerCase().trim() || "";
      const deptId = document.getElementById('services-dept-filter')?.value;

      filteredServicesList = allServicesList.filter(s => {
        const matchesQ = !q || s.title.toLowerCase().includes(q) || s.code.toLowerCase().includes(q);
        const matchesDept = !deptId || s.department_id == deptId;
        return matchesQ && matchesDept;
      });

      servicesCurrentPage = 1;
      renderServicesCatalog();
    }

    function renderServicesCatalog() {
      const grid = document.getElementById('all-services-grid');
      const pageInfo = document.getElementById('services-page-info');
      const paginationButtons = document.getElementById('services-pagination-buttons');
      if (!grid) return;

      const total = filteredServicesList.length;
      const totalPages = Math.ceil(total / servicesPerPage) || 1;
      if (servicesCurrentPage > totalPages) servicesCurrentPage = totalPages;
      if (servicesCurrentPage < 1) servicesCurrentPage = 1;

      const start = (servicesCurrentPage - 1) * servicesPerPage;
      const end = Math.min(start + servicesPerPage, total);
      const pageItems = filteredServicesList.slice(start, end);

      if (pageInfo) {
        pageInfo.innerText = total === 0 ? "0-0 / 0" : `${start + 1}-${end} / ${total}`;
      }

      // Render pagination buttons
      if (paginationButtons) {
        let btnsHtml = '';
        btnsHtml += `
          <button 
            type="button" 
            onclick="changeServicesPage(${servicesCurrentPage - 1})" 
            ${servicesCurrentPage <= 1 ? 'disabled class="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-950 text-slate-600 text-xs cursor-not-allowed"' : 'class="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-950 text-slate-300 hover:text-white hover:border-slate-700 text-xs cursor-pointer"'}
          >
            ◀ Oldingi
          </button>
        `;

        for (let p = 1; p <= totalPages; p++) {
          if (totalPages > 7 && Math.abs(p - servicesCurrentPage) > 2 && p !== 1 && p !== totalPages) {
            if (p === 2 || p === totalPages - 1) btnsHtml += `<span class="px-1 text-slate-600">...</span>`;
            continue;
          }
          const isActive = p === servicesCurrentPage;
          btnsHtml += `
            <button 
              type="button" 
              onclick="changeServicesPage(${p})" 
              class="px-2.5 py-1 rounded-lg text-xs font-semibold transition cursor-pointer ${isActive ? 'bg-emerald-600 text-white shadow-sm shadow-emerald-600/30' : 'bg-slate-950 border border-slate-800 text-slate-400 hover:text-white'}"
            >
              ${p}
            </button>
          `;
        }

        btnsHtml += `
          <button 
            type="button" 
            onclick="changeServicesPage(${servicesCurrentPage + 1})" 
            ${servicesCurrentPage >= totalPages ? 'disabled class="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-950 text-slate-600 text-xs cursor-not-allowed"' : 'class="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-950 text-slate-300 hover:text-white hover:border-slate-700 text-xs cursor-pointer"'}
          >
            Keyingi ▶
          </button>
        `;
        paginationButtons.innerHTML = btnsHtml;
      }

      if (total === 0) {
        grid.innerHTML = '<div class="p-8 text-center text-xs text-slate-500 col-span-2 border border-slate-800/80 rounded-2xl bg-slate-900/40">Mos keluvchi xizmatlar topilmadi.</div>';
        return;
      }

      grid.innerHTML = pageItems.map(s => {
        const dept = allDepartmentsList.find(d => d.id === s.department_id);
        const deptName = dept ? dept.name : (s.department ? s.department.name : "Bo'lim belgilanmagan");

        let modeLabel = "Onlayn va Darcha";
        if (s.resolution_mode === 'in_person_only') modeLabel = "Faqat Darchada";
        else if (s.resolution_mode === 'online_only') modeLabel = "Faqat Onlayn";

        const isActive = s.is_active !== false;

        return `
          <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-3.5 relative group hover:border-slate-700 transition">
            <div class="flex items-center justify-between flex-wrap gap-2">
              <div class="flex items-center gap-2">
                <span class="font-mono text-xs font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded">${s.code}</span>
                <span class="text-xs text-slate-400">• ${deptName}</span>
              </div>
              <div class="flex items-center gap-1.5">
                <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  KPI: +${s.kpi_points || 3} ball
                </span>
                <button
                  type="button"
                  onclick="toggleServiceActive(${s.id})"
                  title="Xizmat holatini o'zgartirish uchun bosing"
                  class="px-2 py-0.5 rounded text-[10px] font-semibold cursor-pointer transition flex items-center gap-1 ${isActive ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20'}"
                >
                  <span class="w-1.5 h-1.5 rounded-full ${isActive ? 'bg-emerald-400' : 'bg-rose-400'}"></span>
                  <span>${isActive ? 'Faol' : 'Nofaol'}</span>
                </button>
              </div>
            </div>

            <div>
              <h5 class="text-sm font-bold text-white leading-snug">${s.title}</h5>
              <p class="text-xs text-slate-400 mt-1 leading-relaxed">${s.description || 'Nizomiy reglament asosidagi standart xizmat'}</p>
            </div>

            <div class="grid grid-cols-2 gap-2 text-xs bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
              <div>
                <span class="text-slate-500">SLA reglamenti:</span>
                <span class="font-semibold text-white ml-1">${s.sla_hours} soat</span>
              </div>
              <div>
                <span class="text-slate-500">Ijro formati:</span>
                <span class="font-semibold text-white ml-1">${modeLabel}</span>
              </div>
              ${s.required_docs ? `
              <div class="col-span-2 pt-1 border-t border-slate-800/60 text-[11px]">
                <span class="text-slate-500">Hujjatlar:</span>
                <span class="text-slate-300 ml-1">${s.required_docs}</span>
              </div>` : ''}
            </div>

            <div class="pt-2 border-t border-slate-800 flex items-center justify-end gap-2">
              <button type="button" onclick="openEditServiceModal(${s.id})" class="px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600 text-emerald-300 hover:text-white text-xs font-medium transition cursor-pointer">
                Tahrirlash (SLA/KPI)
              </button>
              <button type="button" onclick="deleteService(${s.id})" class="px-3 py-1.5 rounded-lg border border-slate-800 hover:border-rose-500/40 hover:bg-rose-500/10 text-slate-400 hover:text-rose-400 text-xs transition cursor-pointer">
                O'chirish
              </button>
            </div>
          </div>
        `;
      }).join('');
    }

    function changeServicesPage(page) {
      servicesCurrentPage = page;
      renderServicesCatalog();
    }

    function changeServicesPerPage(val) {
      servicesPerPage = parseInt(val) || 6;
      servicesCurrentPage = 1;
      renderServicesCatalog();
    }

    // Modal Service CRUD
    async function openCreateServiceModal() {
      const heading = document.getElementById('service-modal-heading');
      if (heading) heading.innerText = "Yangi xizmat qo'shish";
      const idEl = document.getElementById('service-crud-id');
      if (idEl) idEl.value = "";
      const codeEl = document.getElementById('service-code');
      if (codeEl) codeEl.value = "";
      const titleEl = document.getElementById('service-title');
      if (titleEl) titleEl.value = "";
      const slaEl = document.getElementById('service-sla-hours');
      if (slaEl) slaEl.value = "24";
      const kpiEl = document.getElementById('service-kpi-points');
      if (kpiEl) kpiEl.value = "3";
      const modeEl = document.getElementById('service-resolution-mode');
      if (modeEl) modeEl.value = "both";
      const reqEl = document.getElementById('service-required-docs');
      if (reqEl) reqEl.value = "";
      const descEl = document.getElementById('service-desc');
      if (descEl) descEl.value = "";

      const modal = document.getElementById('service-crud-modal');
      if (modal) {
        modal.classList.remove('hidden');
        modal.style.display = 'flex';
      }

      if (!allDepartmentsList || allDepartmentsList.length === 0) {
        await loadDepartmentsList();
      }
    }

    async function openEditServiceModal(id) {
      let s = (allServicesList || []).find(item => item.id == id);
      if (!s) {
        try {
          const resp = await fetch(`/api/v1/services/${id}`, {
            headers: token ? { 'Authorization': `Bearer ${token}` } : {}
          });
          if (resp.ok) s = await resp.json();
        } catch (e) { }
      }
      if (!s) {
        showToast("Xizmat ma'lumotlari topilmadi.", "error");
        return;
      }

      const heading = document.getElementById('service-modal-heading');
      if (heading) heading.innerText = "Xizmatni tahrirlash (SLA va KPI)";
      const idEl = document.getElementById('service-crud-id');
      if (idEl) idEl.value = s.id;
      const codeEl = document.getElementById('service-code');
      if (codeEl) codeEl.value = s.code || "";
      const deptEl = document.getElementById('service-dept');
      if (deptEl) deptEl.value = s.department_id || "";
      const titleEl = document.getElementById('service-title');
      if (titleEl) titleEl.value = s.title || "";
      const slaEl = document.getElementById('service-sla-hours');
      if (slaEl) slaEl.value = s.sla_hours || 24;
      const kpiEl = document.getElementById('service-kpi-points');
      if (kpiEl) kpiEl.value = s.kpi_points || 3;
      const modeEl = document.getElementById('service-resolution-mode');
      if (modeEl) modeEl.value = s.resolution_mode || 'both';
      const reqEl = document.getElementById('service-required-docs');
      if (reqEl) reqEl.value = s.required_docs || "";
      const descEl = document.getElementById('service-desc');
      if (descEl) descEl.value = s.description || "";

      const modal = document.getElementById('service-crud-modal');
      if (modal) {
        modal.classList.remove('hidden');
        modal.style.display = 'flex';
      }

      if (!allDepartmentsList || allDepartmentsList.length === 0) {
        await loadDepartmentsList();
        if (deptEl && s.department_id) deptEl.value = s.department_id;
      }
    }

    function closeServiceModal() {
      const modal = document.getElementById('service-crud-modal');
      if (modal) {
        modal.classList.add('hidden');
        modal.style.display = 'none';
      }
    }

    async function handleSaveService(e) {
      e.preventDefault();
      const id = document.getElementById('service-crud-id')?.value;
      const code = document.getElementById('service-code')?.value.trim().toUpperCase();
      const deptId = parseInt(document.getElementById('service-dept')?.value);
      const title = document.getElementById('service-title')?.value.trim();
      const slaHours = parseInt(document.getElementById('service-sla-hours')?.value) || 24;
      const kpiPoints = parseInt(document.getElementById('service-kpi-points')?.value) || 3;
      const mode = document.getElementById('service-resolution-mode')?.value || 'both';
      const reqDocs = document.getElementById('service-required-docs')?.value.trim() || null;
      const desc = document.getElementById('service-desc')?.value.trim() || null;

      if (!deptId) {
        showToast("Iltimos, xizmat biriktiriladigan bo'limni tanlang!", "warning");
        return;
      }
      if (!title || !code) {
        showToast("Xizmat kodi va nomi majburiy!", "warning");
        return;
      }

      const payload = {
        code: code,
        title: title,
        department_id: deptId,
        sla_hours: slaHours,
        kpi_points: kpiPoints,
        resolution_mode: mode,
        required_docs: reqDocs,
        description: desc
      };

      try {
        const url = id ? `/api/v1/services/${id}` : `/api/v1/services`;
        const method = id ? 'PUT' : 'POST';
        const resp = await fetch(url, {
          method: method,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(payload)
        });

        const data = await resp.json();
        if (resp.ok) {
          showToast(id ? "Xizmat muvaffaqiyatli yangilandi!" : "Yangi xizmat muvaffaqiyatli yaratildi!", "success");
          closeServiceModal();
          await loadServicesCatalog();
        } else {
          showToast(extractErrorMessage(data, "Xizmatni saqlashda xatolik yuz berdi."), "error");
        }
      } catch (err) {
        showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
      }
    }

    async function toggleServiceActive(id) {
      try {
        const resp = await fetch(`/api/v1/services/${id}/toggle-active`, {
          method: 'PATCH',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        const data = await resp.json();
        if (resp.ok) {
          const statusText = data.is_active ? "faollashtirildi" : "nofaol qilindi";
          showToast(`Xizmat muvaffaqiyatli ${statusText}!`, "success");
          await loadServicesCatalog();
        } else {
          showToast(extractErrorMessage(data, "Xizmat holatini o'zgartirishda xatolik."), "error");
        }
      } catch (e) {
        showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
      }
    }

    async function deleteService(id) {
      const s = (allServicesList || []).find(item => item.id == id);
      const title = s ? s.title : "Xizmat";
      const ok = await openAppConfirm({
        title: "Xizmatni o'chirish",
        message: `Haqiqatan ham "${title}" xizmatini o'chirmoqchimisiz? Agar ushbu xizmat bo'yicha murojaatlar bo'lmasa butunlay o'chiriladi, aks holda nofaol holatga o'tkaziladi.`,
        confirmText: "O'chirish",
        cancelText: "Bekor qilish",
        isDanger: true
      });
      if (!ok) return;

      try {
        const resp = await fetch(`/api/v1/services/${id}?hard_delete=true`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await resp.json();
        if (resp.ok) {
          showToast(data.message || "Xizmat muvaffaqiyatli o'chirildi.", "success");
          await loadServicesCatalog();
        } else {
          showToast(extractErrorMessage(data, "Xizmatni o'chirishda xatolik yuz berdi."), "error");
        }
      } catch (e) {
        showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
      }
    }

    // Modal Department CRUD
    function openCreateDeptModal() {
      const heading = document.getElementById('dept-modal-heading');
      if (heading) heading.innerText = "Yangi bo'lim yaratish";
      const idEl = document.getElementById('dept-crud-id');
      if (idEl) idEl.value = "";
      const nameEl = document.getElementById('dept-name');
      if (nameEl) nameEl.value = "";
      const codeEl = document.getElementById('dept-code');
      if (codeEl) codeEl.value = "";
      const typeEl = document.getElementById('dept-type');
      if (typeEl) typeEl.value = "front_office";
      const winEl = document.getElementById('dept-window');
      if (winEl) winEl.value = "";

      const modal = document.getElementById('dept-crud-modal');
      if (modal) {
        modal.classList.remove('hidden');
        modal.style.display = 'flex';
      }
    }

    async function openEditDeptModal(id) {
      let d = (allDepartmentsList || []).find(item => item.id == id);
      if (!d) {
        try {
          const resp = await fetch('/api/v1/services/departments', {
            headers: token ? { 'Authorization': `Bearer ${token}` } : {}
          });
          if (resp.ok) {
            allDepartmentsList = await resp.json();
            d = allDepartmentsList.find(item => item.id == id);
          }
        } catch (e) { }
      }
      if (!d) {
        showToast("Bo'lim ma'lumotlari topilmadi.", "error");
        return;
      }

      const heading = document.getElementById('dept-modal-heading');
      if (heading) heading.innerText = "Bo'limni tahrirlash";
      const idEl = document.getElementById('dept-crud-id');
      if (idEl) idEl.value = d.id;
      const nameEl = document.getElementById('dept-name');
      if (nameEl) nameEl.value = d.name || "";
      const codeEl = document.getElementById('dept-code');
      if (codeEl) codeEl.value = d.code || "";
      const typeEl = document.getElementById('dept-type');
      if (typeEl) typeEl.value = d.dept_type || "front_office";
      const winEl = document.getElementById('dept-window');
      if (winEl) winEl.value = d.window_number || "";

      const modal = document.getElementById('dept-crud-modal');
      if (modal) {
        modal.classList.remove('hidden');
        modal.style.display = 'flex';
      }
    }

    function closeDeptModal() {
      const modal = document.getElementById('dept-crud-modal');
      if (modal) {
        modal.classList.add('hidden');
        modal.style.display = 'none';
      }
    }

    async function handleSaveDepartment(e) {
      e.preventDefault();
      const id = document.getElementById('dept-crud-id')?.value;
      const name = document.getElementById('dept-name')?.value.trim();
      const code = document.getElementById('dept-code')?.value.trim();
      const deptType = document.getElementById('dept-type')?.value || 'front_office';
      const windowNum = document.getElementById('dept-window')?.value.trim() || null;

      if (!name || !code) {
        showToast("Bo'lim nomi va kodi majburiy!", "warning");
        return;
      }

      const payload = {
        name: name,
        code: code,
        dept_type: deptType,
        window_number: windowNum
      };

      try {
        const url = id ? `/api/v1/services/departments/${id}` : `/api/v1/services/departments`;
        const method = id ? 'PUT' : 'POST';
        const resp = await fetch(url, {
          method: method,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(payload)
        });

        const data = await resp.json();
        if (resp.ok) {
          showToast(id ? "Bo'lim muvaffaqiyatli yangilandi!" : "Yangi bo'lim muvaffaqiyatli yaratildi!", "success");
          closeDeptModal();
          await loadDepartmentsList();
        } else {
          showToast(extractErrorMessage(data, "Bo'limni saqlashda xatolik yuz berdi."), "error");
        }
      } catch (err) {
        showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
      }
    }

    async function deleteDepartment(id) {
      const d = (allDepartmentsList || []).find(item => item.id == id);
      const name = d ? d.name : "Bo'lim";
      const ok = await openAppConfirm({
        title: "Bo'limni o'chirish",
        message: `Haqiqatan ham "${name}" bo'limini o'chirmoqchimisiz?`,
        confirmText: "O'chirish",
        cancelText: "Bekor qilish",
        isDanger: true
      });
      if (!ok) return;

      try {
        const resp = await fetch(`/api/v1/services/departments/${id}?hard_delete=true`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await resp.json();
        if (resp.ok) {
          showToast("Bo'lim muvaffaqiyatli o'chirildi.", "success");
          await loadDepartmentsList();
        } else {
          showToast(extractErrorMessage(data, "Bo'limni o'chirishda xatolik."), "error");
        }
      } catch (e) {
        showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
      }
    }

    // 4.1. TAB: DARCHA QABUL NAVBATI (FRONT OFIS OPERATORLARI UCHUN)
    function setQueueDateToday() {
      const today = new Date().toISOString().slice(0, 10);
      const input = document.getElementById('queue-filter-date');
      if (input) input.value = today;
      loadQueueAppointments();
    }

    function clearQueueDateFilter() {
      const input = document.getElementById('queue-filter-date');
      if (input) input.value = '';
      loadQueueAppointments();
    }
