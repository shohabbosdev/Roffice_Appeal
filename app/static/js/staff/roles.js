// ============================================================================
// DINAMIK ROLLAR VA HUQUQLAR MATRITSASI (PBAC) BOSHQARUVI
// ============================================================================

let rolesList = [];
let permissionsCatalog = [];
let currentEditingRoleId = null;
let currentEditingStaffId = null;

function getStaffToken() {
  if (typeof token !== 'undefined' && token) return token;
  return localStorage.getItem('roffice_token') || '';
}

// Xodimlar tarkibi va Rollar matritsasi o'rtasida sub-tab almashish
function switchUsersSubTab(subTab) {
  const staffPane = document.getElementById('users-subpane-staff');
  const rolesPane = document.getElementById('users-subpane-roles');
  const staffBtn = document.getElementById('subtab-users-staff-btn');
  const rolesBtn = document.getElementById('subtab-users-roles-btn');

  if (subTab === 'roles') {
    if (staffPane) staffPane.classList.add('hidden');
    if (rolesPane) rolesPane.classList.remove('hidden');
    if (staffBtn) {
      staffBtn.className = 'px-4 py-2 rounded-xl bg-slate-900 text-slate-400 hover:text-white text-xs font-medium transition cursor-pointer border border-slate-800 hover:border-slate-700';
    }
    if (rolesBtn) {
      rolesBtn.className = 'px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-semibold transition cursor-pointer shadow-md';
    }
    const heading = document.getElementById('page-heading');
    if (heading) heading.innerText = "Rollar va Granulyar Huquqlar Matritsasi (PBAC)";
    window.location.hash = '#roles';
    localStorage.setItem('roffice_staff_tab', 'roles');
    loadRolesAndCatalog();
  } else {
    if (rolesPane) rolesPane.classList.add('hidden');
    if (staffPane) staffPane.classList.remove('hidden');
    if (rolesBtn) {
      rolesBtn.className = 'px-4 py-2 rounded-xl bg-slate-900 text-slate-400 hover:text-white text-xs font-medium transition cursor-pointer border border-slate-800 hover:border-slate-700';
    }
    if (staffBtn) {
      staffBtn.className = 'px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-semibold transition cursor-pointer shadow-md';
    }
    const heading = document.getElementById('page-heading');
    if (heading) heading.innerText = "Xodimlarni boshqarish va rollar biriktirish";
    window.location.hash = '#users';
    localStorage.setItem('roffice_staff_tab', 'users');
    if (typeof loadStaffUsers === 'function') loadStaffUsers();
  }
}
window.switchUsersSubTab = switchUsersSubTab;

// Ruxsatlar katalogini va rollarni yuklash
async function loadRolesAndCatalog() {
  const container = document.getElementById('roles-cards-container');
  if (container) {
    container.innerHTML = `
      <div class="col-span-full p-8 text-center bg-slate-900/60 border border-slate-800 rounded-2xl text-slate-400 text-xs flex items-center justify-center gap-2">
        <svg class="animate-spin h-4 w-4 text-blue-500" viewBox="0 0 24 24" fill="none">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
        </svg>
        <span>Rollar va huquqlar matritsasi yuklanmoqda...</span>
      </div>
    `;
  }

  try {
    const curToken = getStaffToken();
    const [rolesResp, catalogResp] = await Promise.all([
      fetch(apiUrl('/api/v1/roles'), {
        headers: { 'Authorization': `Bearer ${curToken}` }
      }),
      fetch(apiUrl('/api/v1/roles/catalog'), {
        headers: { 'Authorization': `Bearer ${curToken}` }
      })
    ]);

    if (rolesResp.ok) {
      rolesList = await rolesResp.json();
      renderRolesGrid();
      if (typeof roleNameMap !== 'undefined') {
        rolesList.forEach(r => {
          roleNameMap[r.code] = r.name;
        });
      }
      populateRolesDropdowns(rolesList);
    } else {
      const err = await rolesResp.json().catch(() => ({}));
      if (container) {
        container.innerHTML = `
          <div class="col-span-full p-6 text-center bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-400 text-xs">
            Rollar ma'lumotlarini yuklab bo'lmadi: ${escapeHtml(err.detail || rolesResp.statusText)}
          </div>
        `;
      }
    }

    if (catalogResp.ok) {
      const catData = await catalogResp.json();
      permissionsCatalog = catData.catalog || [];
    }
  } catch (err) {
    console.error("Rollar va katalog ma'lumotlarini yuklashda xatolik:", err);
    if (container) {
      container.innerHTML = `
        <div class="col-span-full p-6 text-center bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-400 text-xs">
          Server bilan aloqa uzildi. Iltimos qayta urinib ko'ring.
        </div>
      `;
    }
  }
}

function populateRolesDropdowns(roles) {
  if (!roles || roles.length === 0) return;
  const newRoleSel = document.getElementById('new-staff-role');
  const editRoleSel = document.getElementById('edit-staff-role');

  const optionsHtml = roles
    .filter(r => r.code !== 'student')
    .map(r => `<option value="${r.code}">${escapeHtml(r.name)} (${r.code})</option>`)
    .join('');

  if (newRoleSel) newRoleSel.innerHTML = optionsHtml;
  if (editRoleSel) {
    const curVal = editRoleSel.value;
    editRoleSel.innerHTML = optionsHtml;
    if (curVal) editRoleSel.value = curVal;
  }
}

// Sub-tablarni almashtirish (Xodimlar ro'yxati <-> Rollar matritsasi)
function switchUsersSubtab(tabName) {
  const staffSubtab = document.getElementById('subtab-staff-list');
  const rolesSubtab = document.getElementById('subtab-roles-matrix');
  const btnStaff = document.getElementById('subtab-btn-staff');
  const btnRoles = document.getElementById('subtab-btn-roles');

  if (tabName === 'roles-matrix') {
    if (staffSubtab) staffSubtab.classList.add('hidden');
    if (rolesSubtab) rolesSubtab.classList.remove('hidden');

    if (btnStaff) {
      btnStaff.classList.remove('bg-blue-600', 'text-white');
      btnStaff.classList.add('bg-slate-900', 'text-slate-400', 'hover:text-white');
    }
    if (btnRoles) {
      btnRoles.classList.remove('bg-slate-900', 'text-slate-400', 'hover:text-white');
      btnRoles.classList.add('bg-blue-600', 'text-white');
    }

    loadRolesAndCatalog();
  } else {
    if (rolesSubtab) rolesSubtab.classList.add('hidden');
    if (staffSubtab) staffSubtab.classList.remove('hidden');

    if (btnRoles) {
      btnRoles.classList.remove('bg-blue-600', 'text-white');
      btnRoles.classList.add('bg-slate-900', 'text-slate-400', 'hover:text-white');
    }
    if (btnStaff) {
      btnStaff.classList.remove('bg-slate-900', 'text-slate-400', 'hover:text-white');
      btnStaff.classList.add('bg-blue-600', 'text-white');
    }
  }
}

// Rollar kartochkalarini render qilish
function renderRolesGrid() {
  const container = document.getElementById('roles-cards-container');
  if (!container) return;

  if (!rolesList || rolesList.length === 0) {
    container.innerHTML = `
      <div class="col-span-full p-8 text-center bg-slate-900/60 border border-slate-800 rounded-2xl text-slate-400 text-xs">
        Rollar ro'yxati topilmadi.
      </div>
    `;
    return;
  }

  container.innerHTML = rolesList.map(r => {
    const isImmutable = r.is_immutable || r.code === 'admin';
    const isSystem = r.is_system;
    const permsCount = (r.permissions && r.permissions.includes('*')) ? 'Barcha ruxsatlar (*)' : `${r.permissions ? r.permissions.length : 0} ta ruxsat`;

    return `
      <div class="bg-slate-900/90 border ${isImmutable ? 'border-amber-500/40 shadow-amber-500/5' : 'border-slate-800'} rounded-2xl p-5 flex flex-col justify-between hover:border-slate-700 transition shadow-lg relative overflow-hidden group">
        ${isImmutable ? `
          <div class="absolute -top-6 -right-6 w-16 h-16 bg-amber-500/10 rounded-full flex items-end justify-start p-2 pointer-events-none">
            <span class="text-xs">🛡️</span>
          </div>
        ` : ''}

        <div class="space-y-3">
          <div class="flex items-start justify-between gap-2">
            <div>
              <div class="flex items-center gap-2 flex-wrap">
                <h4 class="text-sm font-bold text-white tracking-tight">${escapeHtml(r.name)}</h4>
                ${isImmutable ? `
                  <span class="px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[10px] font-semibold">
                    Daxlsiz (O'zgarmas)
                  </span>
                ` : isSystem ? `
                  <span class="px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[10px] font-semibold">
                    Tizim shabloni
                  </span>
                ` : `
                  <span class="px-2 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-400 text-[10px] font-semibold">
                    Maxsus rol
                  </span>
                `}
              </div>
              <p class="text-xs font-mono text-slate-400 mt-0.5">${r.code}</p>
            </div>
            <div class="text-right">
              <span class="px-2 py-1 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300">
                ${r.user_count || 0} xodim
              </span>
            </div>
          </div>

          <p class="text-xs text-slate-400 line-clamp-2 min-h-[32px]">
            ${escapeHtml(r.description || "Tavsif ko'rsatilmagan")}
          </p>

          <div class="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs">
            <span class="text-slate-400">Biriktirilgan huquqlar:</span>
            <span class="font-semibold text-emerald-400 font-mono text-[11px]">${permsCount}</span>
          </div>
        </div>

        <div class="mt-4 pt-3 border-t border-slate-800 flex items-center justify-end gap-2">
          ${isImmutable ? `
            <button onclick="openRoleModal(${r.id})" class="w-full px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-slate-700 text-slate-300 text-xs font-medium transition cursor-pointer flex items-center justify-center gap-1.5">
              <span>🛡️</span> Huquqlarni ko'rish
            </button>
          ` : `
            <button onclick="openRoleModal(${r.id})" class="px-3 py-1.5 rounded-xl bg-blue-600/20 hover:bg-blue-600 text-blue-300 hover:text-white text-xs font-medium transition cursor-pointer">
              Tahrirlash & Matritsa
            </button>
            ${!isSystem ? `
              <button onclick="deleteRole(${r.id})" class="px-3 py-1.5 rounded-xl border border-slate-800 hover:border-rose-500/40 hover:bg-rose-500/10 text-slate-400 hover:text-rose-400 text-xs transition cursor-pointer">
                O'chirish
              </button>
            ` : ''}
          `}
        </div>
      </div>
    `;
  }).join('');
}

// Rolni yaratish yoki tahrirlash modalini ochish
async function openRoleModal(roleId = null) {
  currentEditingRoleId = roleId;
  const modal = document.getElementById('role-matrix-modal');
  if (!modal) return;

  // Agar katalog yuklanmagan bo'lsa
  if (!permissionsCatalog || permissionsCatalog.length === 0) {
    await loadRolesAndCatalog();
  }

  const role = roleId ? rolesList.find(r => r.id === roleId) : null;
  const isImmutable = role ? (role.is_immutable || role.code === 'admin') : false;

  document.getElementById('role-modal-title').innerText = role
    ? (isImmutable ? "Bosh Administrator Huquqlari (Daxlsiz)" : `Rolni tahrirlash: ${role.name}`)
    : "Yangi maxsus rol yaratish";

  document.getElementById('role-modal-subtitle').innerText = isImmutable
    ? "Bosh administrator roli xavfsizlik nuqtai nazaridan daxlsiz bo'lib, barcha huquqlarga ega."
    : "Rolga mos atomik ruxsatlar matritsasini belgilang.";

  const codeInput = document.getElementById('role-input-code');
  const nameInput = document.getElementById('role-input-name');
  const descInput = document.getElementById('role-input-desc');
  const saveBtn = document.getElementById('role-modal-save-btn');
  const warningBanner = document.getElementById('role-immutable-warning');

  codeInput.value = role ? role.code : '';
  nameInput.value = role ? role.name : '';
  descInput.value = role ? (role.description || '') : '';

  // Agar admin bo'lsa yoki mavjud rol bo'lsa kod tahrirlanmaydi
  codeInput.disabled = !!role;
  nameInput.disabled = isImmutable;
  descInput.disabled = isImmutable;

  if (warningBanner) {
    if (isImmutable) warningBanner.classList.remove('hidden');
    else warningBanner.classList.add('hidden');
  }

  if (saveBtn) {
    saveBtn.style.display = isImmutable ? 'none' : 'inline-flex';
  }

  // Ruxsatlar matritsasini chizish
  renderPermissionsMatrix(role ? (role.permissions || []) : [], isImmutable);

  modal.classList.remove('hidden');
}

function closeRoleModal() {
  const modal = document.getElementById('role-matrix-modal');
  if (modal) modal.classList.add('hidden');
  currentEditingRoleId = null;
}

// 8 ta kategoriya bo'yicha ruxsatlar matritsasini chizish
function renderPermissionsMatrix(selectedCodes = [], disabled = false) {
  const container = document.getElementById('permissions-matrix-container');
  if (!container) return;

  const isAll = selectedCodes.includes('*');

  // Guruhlarga ajratish
  const groups = {};
  permissionsCatalog.forEach(p => {
    const cat = p.category_name || p.category || "Boshqa";
    if (!groups[cat]) groups[cat] = [];
    groups[cat].push(p);
  });

  let html = '';
  for (const [catName, perms] of Object.entries(groups)) {
    const catId = `cat_${Math.abs(catName.split('').reduce((a,b)=>{a=((a<<5)-a)+b.charCodeAt(0);return a&a},0))}`;

    html += `
      <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-3">
        <div class="flex items-center justify-between border-b border-slate-800/80 pb-2">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-blue-500"></span>
            <h5 class="text-xs font-bold text-white uppercase tracking-wider">${escapeHtml(catName)}</h5>
          </div>
          ${!disabled ? `
            <button type="button" onclick="toggleCategoryPermissions('${catId}')" class="text-[11px] text-blue-400 hover:text-blue-300 font-medium cursor-pointer">
              Barchasini belgilash / bekor qilish
            </button>
          ` : ''}
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-2.5" id="${catId}">
          ${perms.map(p => {
            const isChecked = isAll || selectedCodes.includes(p.code);
            return `
              <label class="flex items-start gap-2.5 p-2 rounded-lg bg-slate-900/60 hover:bg-slate-900 border border-slate-800/60 transition cursor-pointer ${disabled ? 'pointer-events-none opacity-80' : ''}">
                <input type="checkbox" name="role_perm_checkbox" value="${p.code}" ${isChecked ? 'checked' : ''} ${disabled ? 'disabled' : ''}
                  class="mt-0.5 rounded border-slate-700 bg-slate-950 text-blue-600 focus:ring-0">
                <div class="space-y-0.5">
                  <div class="text-xs font-semibold text-slate-200">${escapeHtml(p.name)}</div>
                  <div class="text-[10px] text-slate-400 line-clamp-1">${escapeHtml(p.description)}</div>
                  <div class="text-[9px] font-mono text-slate-500">${p.code}</div>
                </div>
              </label>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  container.innerHTML = html;
}

// Bitta kategoriyadagi barcha checkboxlarni yoqish/o'chirish
function toggleCategoryPermissions(catId) {
  const container = document.getElementById(catId);
  if (!container) return;
  const checkboxes = container.querySelectorAll('input[name="role_perm_checkbox"]');
  const anyUnchecked = Array.from(checkboxes).some(cb => !cb.checked);
  checkboxes.forEach(cb => { cb.checked = anyUnchecked; });
}

// Barcha ruxsatlarni belgilash yoki tozalash
function toggleAllRolePermissions(selectAll) {
  const checkboxes = document.querySelectorAll('input[name="role_perm_checkbox"]');
  checkboxes.forEach(cb => { if (!cb.disabled) cb.checked = selectAll; });
}

// Rolni saqlash (Yaratish yoki Yangilash)
async function handleSaveRole(e) {
  e.preventDefault();
  const code = document.getElementById('role-input-code').value.trim();
  const name = document.getElementById('role-input-name').value.trim();
  const description = document.getElementById('role-input-desc').value.trim();

  if (!name) {
    showToast("Rol nomini kiritish majburiy.", "warning");
    return;
  }

  const selectedPerms = Array.from(document.querySelectorAll('input[name="role_perm_checkbox"]:checked')).map(cb => cb.value);
  const curToken = getStaffToken();

  try {
    let resp;
    if (currentEditingRoleId) {
      // Update
      resp = await fetch(apiUrl(`/api/v1/roles/${currentEditingRoleId}`), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${curToken}`
        },
        body: JSON.stringify({
          name: name,
          description: description,
          permissions: selectedPerms
        })
      });
    } else {
      // Create
      if (!code) {
        showToast("Rol kodini kiritish majburiy (masalan, yurist).", "warning");
        return;
      }
      resp = await fetch(apiUrl('/api/v1/roles'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${curToken}`
        },
        body: JSON.stringify({
          code: code,
          name: name,
          description: description,
          permissions: selectedPerms
        })
      });
    }

    const data = await resp.json();
    if (resp.ok) {
      showToast(currentEditingRoleId ? "Rol muvaffaqiyatli yangilandi!" : "Yangi rol yaratildi!", "success");
      closeRoleModal();
      loadRolesAndCatalog();
    } else {
      showToast(data.detail || "Rolni saqlashda xatolik yuz berdi.", "error");
    }
  } catch (err) {
    console.error("Rolni saqlashda xatolik:", err);
    showToast("Server bilan aloqa uzildi.", "error");
  }
}

// Maxsus rolni o'chirish
async function deleteRole(roleId) {
  const role = rolesList.find(r => r.id === roleId);
  if (!role) return;

  if (!confirm(`Haqiqatan ham '${role.name}' rolini o'chirmoqchimisiz?`)) return;

  const curToken = getStaffToken();
  try {
    const resp = await fetch(apiUrl(`/api/v1/roles/${roleId}`), {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${curToken}` }
    });
    const data = await resp.json();
    if (resp.ok) {
      showToast("Rol muvaffaqiyatli o'chirildi.", "success");
      loadRolesAndCatalog();
    } else {
      showToast(data.detail || "Rolni o'chirishda xatolik yuz berdi.", "error");
    }
  } catch (err) {
    console.error("Rolni o'chirishda xatolik:", err);
    showToast("Server xatosi.", "error");
  }
}

// ============================================================================
// XODIMGA INDIVIDUAL HUQUQLAR USTAMASI (STAFF PERMISSION OVERRIDES)
// ============================================================================

async function openStaffPermissionsModal(userId) {
  currentEditingStaffId = userId;
  const modal = document.getElementById('staff-override-modal');
  if (!modal) return;

  if (!permissionsCatalog || permissionsCatalog.length === 0) {
    await loadRolesAndCatalog();
  }

  const curToken = getStaffToken();
  try {
    const resp = await fetch(apiUrl(`/api/v1/roles/staff/${userId}/permissions`), {
      headers: { 'Authorization': `Bearer ${curToken}` }
    });
    if (!resp.ok) {
      const err = await resp.json();
      showToast(err.detail || "Xodim huquqlarini yuklab bo'lmadi.", "error");
      return;
    }

    const data = await resp.json();
    document.getElementById('staff-override-name').innerText = data.full_name;
    document.getElementById('staff-override-role').innerText = (typeof roleNameMap !== 'undefined' && roleNameMap[data.role]) ? roleNameMap[data.role] : data.role;

    renderStaffOverrideMatrix(data.role_permissions || [], data.custom_permissions || []);
    modal.classList.remove('hidden');
  } catch (err) {
    console.error("Xodim huquqlari yuklanmadi:", err);
    showToast("Server bilan aloqa xatosi.", "error");
  }
}

function closeStaffPermissionsModal() {
  const modal = document.getElementById('staff-override-modal');
  if (modal) modal.classList.add('hidden');
  currentEditingStaffId = null;
}

function renderStaffOverrideMatrix(rolePerms = [], customPerms = []) {
  const container = document.getElementById('staff-override-matrix-container');
  if (!container) return;

  const isRoleAll = rolePerms.includes('*');

  // Guruhlarga ajratish
  const groups = {};
  permissionsCatalog.forEach(p => {
    const cat = p.category_name || p.category || "Boshqa";
    if (!groups[cat]) groups[cat] = [];
    groups[cat].push(p);
  });

  let html = '';
  for (const [catName, perms] of Object.entries(groups)) {
    html += `
      <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-3">
        <div class="flex items-center gap-2 border-b border-slate-800/80 pb-2">
          <span class="w-2 h-2 rounded-full bg-purple-500"></span>
          <h5 class="text-xs font-bold text-white uppercase tracking-wider">${escapeHtml(catName)}</h5>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-2.5">
          ${perms.map(p => {
            const hasFromRole = isRoleAll || rolePerms.includes(p.code);
            const hasFromCustom = customPerms.includes(p.code);

            if (hasFromRole) {
              return `
                <div class="flex items-start gap-2.5 p-2 rounded-lg bg-blue-950/20 border border-blue-500/20 select-none">
                  <span class="mt-0.5 text-blue-400 text-xs">✓</span>
                  <div class="space-y-0.5">
                    <div class="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                      <span>${escapeHtml(p.name)}</span>
                      <span class="px-1.5 py-0.2 rounded bg-blue-500/10 text-blue-400 text-[9px] font-mono">Roldan meros</span>
                    </div>
                    <div class="text-[10px] text-slate-400 line-clamp-1">${escapeHtml(p.description)}</div>
                  </div>
                </div>
              `;
            }

            return `
              <label class="flex items-start gap-2.5 p-2 rounded-lg bg-slate-900/60 hover:bg-slate-900 border border-slate-800/60 transition cursor-pointer">
                <input type="checkbox" name="staff_override_checkbox" value="${p.code}" ${hasFromCustom ? 'checked' : ''}
                  class="mt-0.5 rounded border-slate-700 bg-slate-950 text-purple-600 focus:ring-0">
                <div class="space-y-0.5">
                  <div class="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                    <span>${escapeHtml(p.name)}</span>
                    <span class="px-1.5 py-0.2 rounded bg-purple-500/10 text-purple-400 text-[9px] font-mono">Individual ustama</span>
                  </div>
                  <div class="text-[10px] text-slate-400 line-clamp-1">${escapeHtml(p.description)}</div>
                  <div class="text-[9px] font-mono text-slate-500">${p.code}</div>
                </div>
              </label>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  container.innerHTML = html;
}

// Xodimga individual ustamalarni saqlash
async function handleSaveStaffPermissions(e) {
  e.preventDefault();
  if (!currentEditingStaffId) return;

  const checkedBoxes = Array.from(document.querySelectorAll('input[name="staff_override_checkbox"]:checked'));
  const customPermissions = checkedBoxes.map(cb => cb.value);
  const curToken = getStaffToken();

  try {
    const resp = await fetch(apiUrl(`/api/v1/roles/staff/${currentEditingStaffId}/permissions`), {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${curToken}`
      },
      body: JSON.stringify({ custom_permissions: customPermissions })
    });
    const data = await resp.json();
    if (resp.ok) {
      showToast("Xodim huquqlari muvaffaqiyatli saqlandi!", "success");
      closeStaffPermissionsModal();
      if (typeof loadStaffUsers === 'function') loadStaffUsers();
    } else {
      showToast(data.detail || "Xatolik yuz berdi.", "error");
    }
  } catch (err) {
    console.error("Xodim huquqlarini saqlashda xatolik:", err);
    showToast("Server xatosi.", "error");
  }
}

// Avtomatik faollashtirish (agar URL hash #roles bo'lsa)
if (window.location.hash === '#roles' || window.location.hash === 'roles') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      setTimeout(() => switchUsersSubTab('roles'), 50);
    });
  } else {
    setTimeout(() => switchUsersSubTab('roles'), 50);
  }
}

