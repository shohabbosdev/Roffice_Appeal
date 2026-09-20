async function loadQueueAppointments() {
      const container = document.getElementById('queue-appointments-list');
      if (!container) return;

      const btn = document.getElementById('refresh-queue-btn');
      const icon = document.getElementById('refresh-queue-icon');
      if (btn) btn.disabled = true;
      if (icon) icon.classList.add('animate-spin');

      container.innerHTML = '<div class="p-8 text-center text-xs text-slate-500 border border-slate-800/80 rounded-2xl bg-slate-900/40">Navbat ma\'lumotlari yuklanmoqda...</div>';

      try {
        const dateVal = document.getElementById('queue-filter-date')?.value;
        const queryParam = dateVal ? `?appointment_date=${encodeURIComponent(dateVal)}` : '';
        const resp = await fetch(`/api/v1/appointments${queryParam}`, {
          headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        if (!resp.ok) {
          container.innerHTML = '<div class="p-8 text-center text-xs text-rose-400 border border-slate-800/80 rounded-2xl bg-slate-900/40">Navbat ma\'lumotlarini yuklab bo\'lmadi.</div>';
          return;
        }
        const data = await resp.json();
        if (!data || data.length === 0) {
          const filterMsg = dateVal ? `${dateVal} sanasida` : "Joriy davrda";
          container.innerHTML = `<div class="p-8 text-center text-xs text-slate-500 border border-slate-800/80 rounded-2xl bg-slate-900/40">${filterMsg} darcha qabuliga yozilgan faol talabalar navbati mavjud emas.</div>`;
          return;
        }

        const statusLabels = {
          'booked': '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20">Kutilmoqda</span>',
          'checked_in': '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">Yetib kelgan (Zalda)</span>',
          'in_service': '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">Qabul qilinmoqda</span>',
          'completed': '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Yakunlangan</span>',
          'cancelled': '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-500/10 text-slate-400 border border-slate-500/20">Bekor qilingan</span>'
        };

        container.innerHTML = data.map(apt => {
          const studentName = apt.student ? apt.student.full_name : "Talaba";
          const studentHemis = apt.student ? apt.student.username : "";
          const serviceTitle = apt.service ? apt.service.title : "Nizomiy xizmat";
          const windowNum = apt.window_number || (apt.service?.department?.window_number || "1-darcha");
          const ticketCode = apt.ticket_code || "TALON";
          const timeSlot = apt.time_slot || "-";
          const aptDate = apt.appointment_date || "-";

          return `
            <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-3.5 hover:border-slate-700 transition">
              <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div class="flex items-center gap-2.5 flex-wrap">
                  <span class="inline-block px-2.5 py-1 rounded-lg text-xs font-mono font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20">${ticketCode}</span>
                  <div>
                    <span class="font-bold text-white text-sm">${studentName}</span>
                    ${studentHemis ? `<span class="text-xs text-slate-400 font-mono ml-1">(${studentHemis})</span>` : ''}
                  </div>
                </div>
                <div class="flex items-center gap-2 flex-wrap">
                  ${statusLabels[apt.status] || apt.status}
                  <span class="text-xs font-mono text-slate-300 bg-slate-950 px-2.5 py-0.5 rounded border border-slate-800">${aptDate} • ${timeSlot}</span>
                </div>
              </div>

              <div class="text-xs text-slate-400">
                Xizmat: <strong class="text-slate-200">${serviceTitle}</strong> • Darcha: <span class="text-emerald-400 font-medium">${windowNum}</span>
              </div>

              <div class="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                ${apt.status === 'booked' ? `
                  <button onclick="handleAppointmentCheckIn(${apt.id})" class="px-3.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition cursor-pointer">
                    Kelganini tasdiqlash (Check-in)
                  </button>
                ` : ''}
                ${apt.status === 'checked_in' ? `
                  <button onclick="handleAppointmentCall(${apt.id})" class="px-3.5 py-1.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold transition cursor-pointer shadow-md shadow-cyan-600/20 flex items-center gap-1.5">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z"/></svg>
                    Darchaga chaqirish
                  </button>
                ` : ''}
                ${apt.status === 'in_service' ? `
                  <button onclick="handleAppointmentCall(${apt.id})" class="px-2.5 py-1.5 rounded-xl border border-cyan-500/40 text-cyan-400 hover:bg-cyan-500/10 text-xs font-medium transition cursor-pointer" title="Tabloda qaytadan chaqirish">
                    Qayta chaqirish
                  </button>
                  <button onclick="handleAppointmentComplete(${apt.id})" class="px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition cursor-pointer shadow-md shadow-emerald-600/20">
                    Qabulni yakunlash (KPI)
                  </button>
                ` : ''}
                ${apt.status !== 'completed' && apt.status !== 'cancelled' ? `
                  <button onclick="handleAppointmentCancel(${apt.id})" class="px-2.5 py-1.5 rounded-xl border border-slate-800 hover:border-rose-500/40 hover:bg-rose-500/10 text-slate-400 hover:text-rose-400 text-xs transition cursor-pointer">
                    Bekor qilish
                  </button>
                ` : ''}
              </div>
            </div>
          `;
        }).join('');
      } catch (err) {
        container.innerHTML = '<div class="p-8 text-center text-xs text-rose-400 border border-slate-800/80 rounded-2xl bg-slate-900/40">Server bilan aloqa o\'rnatib bo\'lmadi.</div>';
      } finally {
        if (btn) btn.disabled = false;
        if (icon) icon.classList.remove('animate-spin');
      }
    }

    async function handleAppointmentCall(id) {
      try {
        const resp = await fetch(`/api/v1/appointments/${id}/call`, {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + token }
        });
        if (resp.ok) {
          const apt = await resp.json();
          showToast(`Talon ${apt.ticket_code} ${apt.window_number}ga chaqirildi! Jonli tabloda e'lon qilindi.`, "success");
          loadQueueAppointments();
        } else {
          const e = await resp.json();
          showToast(e.detail || "Chaqirishda xatolik yuz berdi", "error");
        }
      } catch (e) {
        showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
      }
    }

    async function handleAppointmentCheckIn(id) {
      try {
        const resp = await fetch(`/api/v1/appointments/${id}/check-in`, {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + token }
        });
        if (resp.ok) {
          showToast("Talabaning kelgani tasdiqlandi (Check-in).", "success");
          loadQueueAppointments();
        } else {
          const e = await resp.json();
          showToast(e.detail || "Xatolik yuz berdi", "error");
        }
      } catch (e) {
        showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
      }
    }

    async function handleAppointmentComplete(id) {
      const ok = await openAppConfirm({
        title: "Qabulni yakunlash",
        message: "Talabaga darchada xizmat ko'rsatib bo'lindimi? Qabul yakunlangach tegishli KPI balli beriladi.",
        confirmText: "Yakunlash",
        cancelText: "Bekor qilish",
        isDanger: false
      });
      if (!ok) return;

      try {
        const resp = await fetch(`/api/v1/appointments/${id}/complete`, {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + token }
        });
        if (resp.ok) {
          showToast("Darcha qabuli muvaffaqiyatli yakunlandi va KPI balli yozildi!", "success");
          loadQueueAppointments();
        } else {
          const e = await resp.json();
          showToast(e.detail || "Xatolik yuz berdi", "error");
        }
      } catch (e) {
        showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
      }
    }

    async function handleAppointmentCancel(id) {
      const ok = await openAppConfirm({
        title: "Navbatni bekor qilish",
        message: "Ushbu navbat talonini bekor qilishga ishonchingiz komilmi?",
        confirmText: "Bekor qilish",
        cancelText: "Ortga",
        isDanger: true
      });
      if (!ok) return;

      try {
        const resp = await fetch(`/api/v1/appointments/${id}/cancel`, {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + token }
        });
        if (resp.ok) {
          showToast("Navbat taloni bekor qilindi.", "info");
          loadQueueAppointments();
        } else {
          const e = await resp.json();
          showToast(e.detail || "Xatolik yuz berdi", "error");
        }
      } catch (e) {
        showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
      }
    }

    // 5. FIRST LOGIN PASSWORD CHANGE moved to core.js for global reliability

    // 6. VOLUNTARY CREDENTIALS MODAL
    function openCredentialsModal() {
      const modal = document.getElementById('self-profile-modal');
      if (modal && !modal.firstElementChild) {
        const tmpl = document.getElementById('self-profile-template');
        if (tmpl) modal.appendChild(tmpl.content.cloneNode(true));
      }
      if (modal) {
        modal.style.display = 'flex';
        modal.classList.remove('hidden');
        modal.classList.add('flex');
      }
      const alertBox = document.getElementById('self-cred-alert');
      if (alertBox) alertBox.classList.add('hidden');
    }

    function closeCredentialsModal() {
      const modal = document.getElementById('self-profile-modal');
      if (modal) {
        modal.style.display = 'none';
        modal.classList.add('hidden');
        modal.classList.remove('flex');
      }
    }

    async function handleSelfCredentialUpdate(e) {
      e.preventDefault();
      const cur = document.getElementById('self-current-password').value;
      const newU = document.getElementById('self-new-username').value.trim() || null;
      const newP = document.getElementById('self-new-password').value.trim() || null;
      const conf = document.getElementById('self-confirm-password').value.trim() || null;
      const alertBox = document.getElementById('self-cred-alert');

      if (newP && newP !== conf) {
        alertBox.className = 'p-3 rounded-xl text-xs font-medium border bg-rose-500/10 border-rose-500/30 text-rose-400 block';
        alertBox.innerText = "Yangi parol va tasdiqlovchi parol mos kelmadi.";
        return;
      }

      try {
        const resp = await fetch('/api/v1/users/me/credentials', {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            current_password: cur,
            new_username: newU,
            new_password: newP
          })
        });
        const data = await resp.json();
        if (resp.ok) {
          token = data.access_token;
          localStorage.setItem('roffice_token', token);
          alertBox.className = 'p-3 rounded-xl text-xs font-medium border bg-emerald-500/10 border-emerald-500/30 text-emerald-400 block';
          alertBox.innerText = "Xavfsizlik ma'lumotlari muvaffaqiyatli yangilandi.";
          showToast("Profil va parol ma'lumotlari yangilandi!", "success");
          setTimeout(() => {
            closeCredentialsModal();
            loadCurrentUserProfile();
          }, 1200);
        } else {
          alertBox.className = 'p-3 rounded-xl text-xs font-medium border bg-rose-500/10 border-rose-500/30 text-rose-400 block';
          alertBox.innerText = data.detail || "Xatolik yuz berdi.";
        }
      } catch (err) {
        showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
      }
    }

    // 7. TAB: XODIMLAR & ROLLAR & NIZOM VAZIFALARI
    let allStaffList = [];

    const roleNameMap = {
      'front_staff': "Front-ofis xodimi",
      'back_staff': "Back-ofis ijrochi",
      'office_head': "Registrator boshlig'i",
      'vice_rector': "O'quv prorektori",
      'admin': "Administrator"
    };

    const roleBadgeColor = {
      'front_staff': "bg-blue-500/10 text-blue-400 border-blue-500/20",
      'back_staff': "bg-slate-500/10 text-slate-300 border-slate-500/20",
      'office_head': "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
      'vice_rector': "bg-amber-500/10 text-amber-400 border-amber-500/20",
      'admin': "bg-rose-500/10 text-rose-400 border-rose-500/20"
    };

    function toggleAddStaffForm() {
      const f = document.getElementById('add-staff-form-wrap');
      if (f) {
        f.classList.toggle('hidden');
        if (!f.classList.contains('hidden')) {
          loadDepartmentsDropdown();
        }
      }
    }
