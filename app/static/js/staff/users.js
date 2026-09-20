async function loadDepartmentsDropdown() {
      try {
        const resp = await fetch('/api/v1/services/departments');
        departmentsList = await resp.json();
        const sel = document.getElementById('new-staff-department');
        if (sel) {
          sel.innerHTML = '<option value="">Bo\'limni tanlang (ixtiyoriy)</option>' +
            departmentsList.map(d => `<option value="${d.id}">${d.name} (${d.code})</option>`).join('');
        }
      } catch (e) {
        console.error("Bo'limlarni yuklab bo'lmadi:", e);
      }
    }

    async function loadNizomDutiesForCreate() {
      try {
        const resp = await fetch('/api/v1/users/nizom-duties', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        nizomDutiesCatalog = await resp.json();
        const role = document.getElementById('new-staff-role').value;
        const matching = nizomDutiesCatalog.filter(c => c.role === role);
        if (matching.length > 0) {
          const duties = matching.flatMap(m => m.duties).slice(0, 3);
          document.getElementById('new-staff-duties').value = duties.join('\n');
        }
      } catch (e) {
        console.error("Nizom vazifalarini yuklab bo'lmadi:", e);
      }
    }

    async function handleCreateStaff(e) {
      e.preventDefault();
      const fullName = document.getElementById('new-staff-name').value.trim();
      const username = document.getElementById('new-staff-username').value.trim();
      const role = document.getElementById('new-staff-role').value;
      const deptId = document.getElementById('new-staff-department').value ? parseInt(document.getElementById('new-staff-department').value) : null;
      const email = document.getElementById('new-staff-email').value.trim() || null;
      const phone = document.getElementById('new-staff-phone').value.trim() || null;
      const duties = document.getElementById('new-staff-duties').value.trim() || null;

      const pwdMode = document.querySelector('input[name="new_staff_pwd_mode"]:checked')?.value || 'auto';
      const customPwd = pwdMode === 'custom' ? (document.getElementById('new-staff-custom-password')?.value.trim() || null) : null;

      if (pwdMode === 'custom' && (!customPwd || customPwd.length < 6)) {
        showToast("Maxsus parol kamida 6 belgidan iborat bo'lishi kerak.", "warning");
        return;
      }

      try {
        const resp = await fetch('/api/v1/users/staff', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            full_name: fullName,
            username: username,
            role: role,
            department_id: deptId,
            email: email,
            phone: phone,
            assigned_duties: duties,
            custom_password: customPwd
          })
        });
        const data = await resp.json();
        if (resp.ok) {
          toggleAddStaffForm();
          e.target.reset();

          // Show generated temporary OTP modal
          document.getElementById('temp-username-val').innerText = data.user.username;
          document.getElementById('temp-password-val').innerText = data.temporary_password;
          document.getElementById('temp-password-modal').classList.remove('hidden');

          showToast("Yangi xodim muvaffaqiyatli qo'shildi!", "success");
          loadStaffUsers();
        } else {
          showToast(data.detail || "Xodim qo'shishda xatolik yuz berdi.", "error");
        }
      } catch (err) {
        showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
      }
    }

    function copyTempPassword() {
      const p = document.getElementById('temp-password-val').innerText;
      navigator.clipboard.writeText(p);
      showToast("Parol nusxalandi: " + p, "success");
    }

    function closeTempPasswordModal() {
      document.getElementById('temp-password-modal').classList.add('hidden');
    }

    let staffCurrentPage = 1;
    let staffPerPage = 10;

    async function loadStaffUsers() {
      const tbody = document.getElementById('staff-users-table-body');
      if (!tbody) return;

      try {
        const resp = await fetch('/api/v1/users/staff', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!resp.ok) {
          tbody.innerHTML = `<tr><td colspan="6" class="p-8 text-center text-rose-400">Xodimlarni ko'rish huquqi yetarli emas (faqat Administrator va Boshliq).</td></tr>`;
          renderStaffPagination(0);
          return;
        }
        allStaffList = await resp.json();
        renderStaffUsersTable();
      } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" class="p-8 text-center text-rose-400">Server bilan aloqa o'rnatib bo'lmadi.</td></tr>`;
        renderStaffPagination(0);
      }
    }

    function renderStaffUsersTable() {
      const tbody = document.getElementById('staff-users-table-body');
      if (!tbody) return;

      if (!allStaffList || allStaffList.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="p-8 text-center text-slate-500">Xodimlar mavjud emas.</td></tr>`;
        renderStaffPagination(0);
        return;
      }

      const total = allStaffList.length;
      const totalPages = Math.ceil(total / staffPerPage) || 1;
      if (staffCurrentPage > totalPages) staffCurrentPage = totalPages;
      if (staffCurrentPage < 1) staffCurrentPage = 1;

      const startIdx = (staffCurrentPage - 1) * staffPerPage;
      const endIdx = Math.min(startIdx + staffPerPage, total);
      const pageItems = allStaffList.slice(startIdx, endIdx);

      tbody.innerHTML = pageItems.map(u => {
        const dutiesSummary = u.assigned_duties ? u.assigned_duties.split('\n')[0] : "Biriktirilmagan";
        const dept = allDepartmentsList.find(d => d.id === u.department_id);
        const deptLabel = dept ? `${dept.name} (${dept.window_number || dept.code})` : 'Bo\'limsiz';
        const assignedServices = u.assigned_services || [];
        const servicesCount = assignedServices.length;

        let servicesBadgesHtml = '';
        if (servicesCount > 0) {
          servicesBadgesHtml = `
            <div class="mt-1 flex flex-wrap gap-1 items-center">
              ${assignedServices.slice(0, 3).map(s => `<span class="px-1.5 py-0.5 rounded bg-sky-500/10 border border-sky-500/20 text-sky-300 text-[10px] font-mono" title="${s.title}">${s.code}</span>`).join('')}
              ${servicesCount > 3 ? `<span class="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px] font-mono">+${servicesCount - 3}</span>` : ''}
            </div>
          `;
        } else {
          servicesBadgesHtml = `<div class="mt-1 text-[10px] text-slate-500 italic">Barcha xizmatlar (bo'lim)</div>`;
        }

        return `
          <tr class="hover:bg-slate-950/40 transition">
            <td class="p-3.5 font-mono text-slate-400">${u.id}</td>
            <td class="p-3.5">
              <div class="font-semibold text-white">${u.full_name}</div>
              <div class="text-[11px] text-slate-400">${u.email || u.phone || '-'} • <span class="text-blue-400 font-medium">${deptLabel}</span></div>
              ${servicesBadgesHtml}
            </td>
            <td class="p-3.5 font-mono text-blue-400 font-medium">${u.username}</td>
            <td class="p-3.5">
              <span class="inline-block px-2.5 py-0.5 rounded-full text-[10px] font-medium border ${roleBadgeColor[u.role] || 'border-slate-800'}">
                ${roleNameMap[u.role] || u.role}
              </span>
              ${u.must_change_password ? '<span class="ml-1 text-[10px] text-amber-400 font-medium">(Vaqtinchalik OTP)</span>' : ''}
            </td>
            <td class="p-3.5 text-slate-300 text-xs max-w-xs truncate" title="${u.assigned_duties || ''}">
              ${dutiesSummary}
            </td>
            <td class="p-3.5 text-right space-x-1 whitespace-nowrap">
              ${(u.role === 'admin' || u.username === 'admin') ? `
                <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-semibold select-none shadow-sm" title="Bosh Administrator hisobi o'zgarmas va himoyalangan">
                  <span>🛡️</span> <span>Tizim Admini (Himoyalangan)</span>
                </span>
              ` : `
                <button onclick="openStaffServicesModal(${u.id})" class="px-2.5 py-1 rounded-lg bg-sky-600/20 hover:bg-sky-600 text-sky-300 hover:text-white text-xs font-medium transition cursor-pointer" title="Xizmatlarni biriktirish">
                  Xizmatlar (${servicesCount})
                </button>
                <button onclick="openEditStaffModal(${u.id})" class="px-2.5 py-1 rounded-lg bg-indigo-600/20 hover:bg-indigo-600 text-indigo-300 hover:text-white text-xs font-medium transition cursor-pointer">
                  Tahrirlash
                </button>
                <button onclick="openKpiAwardModal(${u.id})" class="px-2.5 py-1 rounded-lg bg-emerald-600/20 hover:bg-emerald-600 text-emerald-300 hover:text-white text-xs font-medium transition cursor-pointer">
                  KPI & Vazifa
                </button>
                <button onclick="deleteStaffMember(${u.id})" class="px-2 py-1 rounded-lg border border-slate-800 hover:border-rose-500/40 hover:bg-rose-500/10 text-slate-400 hover:text-rose-400 text-xs transition cursor-pointer">
                  O'chirish
                </button>
              `}
            </td>
          </tr>
        `;
      }).join('');

      renderStaffPagination(total);
    }

    function changeStaffPage(newPage) {
      if (newPage < 1) return;
      const total = allStaffList ? allStaffList.length : 0;
      const totalPages = Math.ceil(total / staffPerPage) || 1;
      if (newPage > totalPages) return;
      staffCurrentPage = newPage;
      renderStaffUsersTable();
    }

    function changeStaffPerPage(val) {
      staffPerPage = parseInt(val, 10) || 10;
      staffCurrentPage = 1;
      renderStaffUsersTable();
    }

    function renderStaffPagination(total) {
      const paginationBar = document.getElementById('staff-pagination-bar');
      const pageInfo = document.getElementById('staff-page-info');
      const paginationButtons = document.getElementById('staff-pagination-buttons');

      if (!paginationBar) return;

      if (!total || total === 0) {
        paginationBar.classList.remove('flex');
        paginationBar.classList.add('hidden');
        return;
      }

      paginationBar.classList.remove('hidden');
      paginationBar.classList.add('flex');

      const totalPages = Math.ceil(total / staffPerPage) || 1;
      const startIdx = (staffCurrentPage - 1) * staffPerPage;
      const endIdx = Math.min(startIdx + staffPerPage, total);

      if (pageInfo) {
        pageInfo.textContent = `${startIdx + 1}-${endIdx} / ${total}`;
      }

      if (paginationButtons) {
        let btnsHtml = '';

        btnsHtml += `
          <button 
            type="button" 
            onclick="changeStaffPage(${staffCurrentPage - 1})" 
            ${staffCurrentPage <= 1 ? 'disabled class="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-950 text-slate-600 text-xs cursor-not-allowed"' : 'class="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-950 text-slate-300 hover:text-white hover:border-slate-700 text-xs cursor-pointer transition"'}
          >
            ◀ Oldingi
          </button>
        `;

        for (let p = 1; p <= totalPages; p++) {
          const isActive = p === staffCurrentPage;
          btnsHtml += `
            <button 
              type="button" 
              onclick="changeStaffPage(${p})" 
              class="w-7 h-7 flex items-center justify-center rounded-lg text-xs font-semibold transition cursor-pointer ${isActive ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30' : 'border border-slate-800 bg-slate-950 text-slate-400 hover:text-white hover:border-slate-700'}"
            >
              ${p}
            </button>
          `;
        }

        btnsHtml += `
          <button 
            type="button" 
            onclick="changeStaffPage(${staffCurrentPage + 1})" 
            ${staffCurrentPage >= totalPages ? 'disabled class="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-950 text-slate-600 text-xs cursor-not-allowed"' : 'class="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-950 text-slate-300 hover:text-white hover:border-slate-700 text-xs cursor-pointer transition"'}
          >
            Keyingi ▶
          </button>
        `;

        paginationButtons.innerHTML = btnsHtml;
      }
    }

    window.changeStaffPage = changeStaffPage;
    window.changeStaffPerPage = changeStaffPerPage;

    // === XODIMGA XIZMATLARNI BIRIKTIRISH MODAL BOSHQARUVI ===
    let currentStaffAssigningServices = null;

    async function openStaffServicesModal(userId) {
      const u = allStaffList.find(item => item.id === userId);
      if (!u) return;

      currentStaffAssigningServices = u;
      document.getElementById('assign-services-staff-id').value = u.id;
      const roleName = roleNameMap[u.role] || u.role;
      document.getElementById('assign-services-staff-badge').innerText = `${u.full_name} (${roleName})`;
      document.getElementById('assign-services-search').value = "";

      if (!allServicesList || allServicesList.length === 0) {
        try {
          const resp = await fetch('/api/v1/services', { headers: { 'Authorization': `Bearer ${token}` } });
          if (resp.ok) allServicesList = await resp.json();
        } catch (e) {
          console.error("Xizmatlarni yuklashda xatolik:", e);
        }
      }

      const assignedIds = (u.assigned_services || []).map(s => s.id);
      renderServicesChecklist(assignedIds);

      document.getElementById('staff-services-modal').classList.remove('hidden');
    }

    function closeStaffServicesModal() {
      document.getElementById('staff-services-modal').classList.add('hidden');
      currentStaffAssigningServices = null;
    }

    function renderServicesChecklist(selectedIds = []) {
      const container = document.getElementById('assign-services-list-container');
      if (!container) return;

      if (!allServicesList || allServicesList.length === 0) {
        container.innerHTML = `<div class="p-8 text-center text-slate-500">Tizimda faol xizmatlar mavjud emas.</div>`;
        updateModalSelectedCount();
        return;
      }

      const deptsMap = {};
      allServicesList.forEach(s => {
        const dId = s.department_id || 0;
        const dName = s.department ? `${s.department.name} (${s.department.window_number || s.department.code})` : 'Umumiy xizmatlar';
        if (!deptsMap[dId]) {
          deptsMap[dId] = { name: dName, services: [] };
        }
        deptsMap[dId].services.push(s);
      });

      let html = '';
      Object.keys(deptsMap).forEach(dId => {
        const group = deptsMap[dId];
        html += `
          <div class="service-dept-group bg-slate-950/60 rounded-xl border border-slate-800/80 p-3 space-y-2">
            <div class="flex items-center justify-between pb-1.5 border-b border-slate-800/60">
              <span class="text-xs font-bold text-sky-400 flex items-center gap-1.5">
                <span class="w-1.5 h-1.5 rounded-full bg-sky-400"></span>
                ${group.name}
              </span>
              <span class="text-[11px] text-slate-500 font-mono">${group.services.length} ta xizmat</span>
            </div>
            <div class="grid grid-cols-1 gap-1.5">
        `;

        group.services.forEach(s => {
          const isChecked = selectedIds.includes(s.id) ? 'checked' : '';
          const modeLabels = {
            'online_only': '<span class="text-[10px] text-sky-400 bg-sky-500/10 px-1.5 py-0.5 rounded border border-sky-500/20">Onlayn</span>',
            'in_person_only': '<span class="text-[10px] text-purple-400 bg-purple-500/10 px-1.5 py-0.5 rounded border border-purple-500/20">Navbat</span>',
            'both': '<span class="text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">Onlayn & Navbat</span>'
          };

          html += `
            <label class="service-item-row flex items-start gap-3 p-2 rounded-lg hover:bg-slate-900 border border-transparent hover:border-slate-800 transition cursor-pointer" data-title="${(s.title + ' ' + s.code).toLowerCase()}">
              <input type="checkbox" value="${s.id}" ${isChecked} onchange="updateModalSelectedCount()" class="service-assign-checkbox mt-1 rounded border-slate-700 bg-slate-900 text-sky-600 focus:ring-0 cursor-pointer">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="font-mono text-xs font-semibold text-slate-300">${s.code}</span>
                  <span class="text-xs font-medium text-white">${s.title}</span>
                  ${modeLabels[s.resolution_mode] || ''}
                </div>
                <div class="text-[11px] text-slate-400 mt-0.5 flex items-center gap-3">
                  <span>Reglament: <strong class="text-slate-300 font-mono">${s.sla_hours} soat</strong></span>
                  <span>KPI: <strong class="text-emerald-400 font-mono">+${s.kpi_points} ball</strong></span>
                </div>
              </div>
            </label>
          `;
        });

        html += `
            </div>
          </div>
        `;
      });

      container.innerHTML = html;
      updateModalSelectedCount();
    }

    function updateModalSelectedCount() {
      const checkboxes = document.querySelectorAll('.service-assign-checkbox:checked');
      const countEl = document.getElementById('assign-services-selected-count');
      if (countEl) countEl.innerText = checkboxes.length;
    }

    function selectAllServicesInModal(state) {
      const checkboxes = document.querySelectorAll('.service-assign-checkbox');
      checkboxes.forEach(cb => {
        const row = cb.closest('.service-item-row');
        if (row && row.style.display !== 'none') {
          cb.checked = state;
        }
      });
      updateModalSelectedCount();
    }

    function filterServicesModalList() {
      const query = (document.getElementById('assign-services-search').value || '').trim().toLowerCase();
      const rows = document.querySelectorAll('.service-item-row');
      const groups = document.querySelectorAll('.service-dept-group');

      rows.forEach(r => {
        const text = r.getAttribute('data-title') || '';
        if (!query || text.includes(query)) {
          r.style.display = 'flex';
        } else {
          r.style.display = 'none';
        }
      });

      groups.forEach(g => {
        const visibleRows = g.querySelectorAll('.service-item-row[style="display: flex;"], .service-item-row:not([style*="display: none"])');
        g.style.display = visibleRows.length > 0 ? 'block' : 'none';
      });
    }

    async function saveStaffAssignedServices() {
      const staffId = document.getElementById('assign-services-staff-id').value;
      if (!staffId) return;

      const checkedBoxes = document.querySelectorAll('.service-assign-checkbox:checked');
      const selectedIds = Array.from(checkedBoxes).map(cb => parseInt(cb.value));

      const btn = document.getElementById('save-staff-services-btn');
      const origText = btn.innerHTML;
      btn.innerHTML = `<span class="inline-block w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span> Saqlanmoqda...`;
      btn.disabled = true;

      try {
        const resp = await fetch(`/api/v1/users/${staffId}/services`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ service_ids: selectedIds })
        });

        if (!resp.ok) {
          const err = await resp.json();
          showToast(err.detail || "Xizmatlarni biriktirishda xatolik yuz berdi.", "error");
          return;
        }

        showToast(`Xodimga ${selectedIds.length} ta xizmat muvaffaqiyatli biriktirildi!`, "success");
        closeStaffServicesModal();
        await loadStaffUsers();
      } catch (e) {
        showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
      } finally {
        btn.innerHTML = origText;
        btn.disabled = false;
      }
    }

    function openEditStaffModal(userId) {
      const u = allStaffList.find(item => item.id === userId);
      if (!u) return;

      if (u.role === 'admin' || u.username === 'admin') {
        showToast("Administrator hisobini tahrirlash qat'iyan taqiqlanadi.", "warning");
        return;
      }

      document.getElementById('edit-staff-id').value = u.id;
      document.getElementById('edit-staff-name').value = u.full_name;
      document.getElementById('edit-staff-username').value = u.username;
      document.getElementById('edit-staff-role').value = u.role;
      document.getElementById('edit-staff-dept').value = u.department_id || "";
      document.getElementById('edit-staff-email').value = u.email || "";
      document.getElementById('edit-staff-phone').value = u.phone || "";
      document.getElementById('edit-staff-duties').value = u.assigned_duties || "";
      document.getElementById('edit-staff-reset-otp').checked = false;
      document.getElementById('edit-staff-new-password').value = "";

      document.getElementById('edit-staff-modal').classList.remove('hidden');
    }

    function closeEditStaffModal() {
      document.getElementById('edit-staff-modal').classList.add('hidden');
    }

    function generateRandomPassword(targetInputId, length = 8) {
      const upper = "ABCDEFGHJKLMNPQRSTUVWXYZ";
      const lower = "abcdefghjkmnpqrstuvwxyz";
      const digits = "23456789";
      const special = "#$@!%";
      const all = upper + lower + digits + special;
      
      let pwd = "";
      pwd += upper[Math.floor(Math.random() * upper.length)];
      pwd += lower[Math.floor(Math.random() * lower.length)];
      pwd += digits[Math.floor(Math.random() * digits.length)];
      pwd += special[Math.floor(Math.random() * special.length)];
      for (let i = 4; i < length; i++) {
        pwd += all[Math.floor(Math.random() * all.length)];
      }
      // Tasodifiy almashtirish
      pwd = pwd.split('').sort(() => 0.5 - Math.random()).join('');
      
      if (targetInputId === 'new-staff-custom-password') {
        const customRadio = document.querySelector('input[name="new_staff_pwd_mode"][value="custom"]');
        if (customRadio) customRadio.checked = true;
        const wrap = document.getElementById('new-staff-custom-pwd-wrap');
        if (wrap) wrap.classList.remove('hidden');
      } else if (targetInputId === 'edit-staff-new-password') {
        const resetOtp = document.getElementById('edit-staff-reset-otp');
        if (resetOtp) resetOtp.checked = false;
      }

      if (targetInputId) {
        const input = document.getElementById(targetInputId);
        if (input) {
          input.value = pwd;
          input.setAttribute('value', pwd);
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
          input.focus();
          input.select();
        }
      }
      showToast("Yangi xavfsiz parol generatsiya qilindi: " + pwd, "info");
      return pwd;
    }
    window.generateRandomPassword = generateRandomPassword;

    async function handleUpdateStaff(e) {
      e.preventDefault();
      const userId = document.getElementById('edit-staff-id').value;
      const fullName = document.getElementById('edit-staff-name').value.trim();
      const username = document.getElementById('edit-staff-username').value.trim();
      const role = document.getElementById('edit-staff-role').value;
      const deptId = document.getElementById('edit-staff-dept').value ? parseInt(document.getElementById('edit-staff-dept').value) : null;
      const email = document.getElementById('edit-staff-email').value.trim() || null;
      const phone = document.getElementById('edit-staff-phone').value.trim() || null;
      const duties = document.getElementById('edit-staff-duties').value.trim() || null;
      const resetOtp = document.getElementById('edit-staff-reset-otp').checked;
      const newPassword = document.getElementById('edit-staff-new-password').value.trim() || null;

      if (newPassword && newPassword.length < 6) {
        showToast("Yangi parol kamida 6 ta belgidan iborat bo'lishi kerak.", "warning");
        return;
      }

      const payload = {
        full_name: fullName,
        username: username,
        role: role,
        department_id: deptId,
        email: email,
        phone: phone,
        assigned_duties: duties,
        reset_password: resetOtp,
        new_password: newPassword
      };

      try {
        const resp = await fetch(`/api/v1/users/staff/${userId}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(payload)
        });
        const data = await resp.json();

        if (resp.ok) {
          closeEditStaffModal();
          if (data.new_temporary_password) {
            const uName = (data.user && data.user.username) ? data.user.username : username;
            document.getElementById('temp-username-val').innerText = uName;
            document.getElementById('temp-password-val').innerText = data.new_temporary_password;
            document.getElementById('temp-password-modal').classList.remove('hidden');
          } else {
            showToast("Xodim ma'lumotlari muvaffaqiyatli yangilandi!", "success");
          }
          loadStaffUsers();
        } else {
          showToast(data.detail || "Xodimni yangilashda xatolik yuz berdi.", "error");
        }
      } catch (err) {
        showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
      }
    }

    async function deleteStaffMember(userId) {
      const u = (allStaffList || []).find(item => item.id === userId);
      if (u && (u.role === 'admin' || u.username === 'admin')) {
        showToast("Administrator hisobini tizimdan o'chirish qat'iyan taqiqlanadi!", "error");
        return;
      }
      const name = u ? u.full_name : "Xodim";
      const ok = await openAppConfirm({
        title: "Xodimni o'chirish",
        message: `Haqiqatan ham "${name}" xodimini tizimdan o'chirmoqchimisiz?\n\nAgar xodimga bog'langan murojaatlar bo'lmasa, u butkul o'chiriladi. Aks holda nofaol holatga o'tkaziladi.`,
        confirmText: "O'chirish",
        cancelText: "Bekor qilish",
        isDanger: true
      });
      if (!ok) return;

      try {
        const resp = await fetch(`/api/v1/users/staff/${userId}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();
        if (resp.ok) {
          showToast(res.message || "Xodim muvaffaqiyatli o'chirildi.", "success");
          loadStaffUsers();
        } else {
          showToast(res.detail || "Xodimni o'chirishda xatolik yuz berdi.", "error");
        }
      } catch (e) {
        showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
      }
    }
    window.deleteStaffMember = deleteStaffMember;

    // 8. KPI AWARD MODAL
    function openKpiAwardModal(empId) {
      const u = (allStaffList || []).find(item => item.id === empId);
      const empName = u ? u.full_name : "Xodim";
      const duties = u ? (u.assigned_duties || "") : "";
      document.getElementById('kpi-target-employee-id').value = empId;
      document.getElementById('kpi-modal-staff-name').innerText = empName;
      const listEl = document.getElementById('kpi-modal-duties-list');
      if (duties && duties.trim()) {
        listEl.innerHTML = duties.split('\n').map(d => `<div class="flex items-center gap-2"><span class="text-emerald-400">•</span> <span>${d}</span></div>`).join('');
      } else {
        listEl.innerHTML = '<span class="text-slate-500">Nizom bo\'yicha alohida xizmat vazifalari biriktirilmagan. Standart registrator xizmatlari qo\'llaniladi.</span>';
      }
      document.getElementById('kpi-award-modal').classList.remove('hidden');
    }

    function closeKpiAwardModal() {
      document.getElementById('kpi-award-modal').classList.add('hidden');
    }

    async function handleAwardKpiPoints(e) {
      e.preventDefault();
      const empId = parseInt(document.getElementById('kpi-target-employee-id').value);
      const title = document.getElementById('kpi-duty-title').value.trim();
      const pts = parseInt(document.getElementById('kpi-duty-points').value);
      const rsn = document.getElementById('kpi-duty-reason').value.trim();

      try {
        const resp = await fetch('/api/v1/kpi/award-points', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            employee_id: empId,
            duty_title: title,
            points: pts,
            reason: rsn
          })
        });
        const res = await resp.json();
        if (resp.ok) {
          showToast(`Xodimga ${pts} KPI balli muvaffaqiyatli qo'shildi. Joriy foiz: ${res.kpi_percentage}%`, 'success');
          closeKpiAwardModal();
          e.target.reset();
        } else {
          showToast(res.detail || "KPI balli berishda xatolik yuz berdi.", 'error');
        }
      } catch (err) {
        showToast("Server bilan aloqa o'rnatib bo'lmadi.", 'error');
      }
    }

    // 9. TAB: MUROJAATLAR MONITORINGI & IJRO
    const STATUS_META = {
      'new': { label: 'Yangi', cls: 'bg-blue-500/10 text-blue-400 border-blue-500/20' },
      'assigned': { label: 'Biriktirilgan', cls: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
      'in_progress': { label: 'Ijroda', cls: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
      'clarification_needed': { label: "Ma'lumot so'raldi", cls: 'bg-purple-500/10 text-purple-400 border-purple-500/20' },
      'resolved': { label: 'Yakunlandi', cls: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
      'completed': { label: 'Tasdiqlandi', cls: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
      'auto_closed': { label: 'Avtoyopildi', cls: 'bg-slate-500/10 text-slate-400 border-slate-500/20' },
      'disputed': { label: "E'tiroz", cls: 'bg-rose-500/10 text-rose-400 border-rose-500/20' },
      'escalated_head': { label: 'Boshliqda', cls: 'bg-orange-500/10 text-orange-400 border-orange-500/20' },
      'escalated_prorektor': { label: 'Prorektorda', cls: 'bg-red-500/10 text-red-400 border-red-500/20' },
      'rejected': { label: 'Rad etildi', cls: 'bg-rose-500/10 text-rose-400 border-rose-500/20' },
      'cancelled': { label: 'Bekor qilindi', cls: 'bg-slate-500/10 text-slate-400 border-slate-500/20' },
    };

    let allStaffAppeals = [];
    let cachedStaffUsers = [];
    let filterOnlyOverdue = false;
    let filterOnlyDisputed = false;
