async function loadKPIOverview() {
      const container = document.getElementById('kpi-cards');
      if (!container) return;

      const btn = document.getElementById('refresh-kpi-btn');
      const icon = document.getElementById('refresh-kpi-icon');
      if (btn) btn.disabled = true;
      if (icon) icon.classList.add('animate-spin');

      container.innerHTML = '<div class="p-8 text-center text-xs text-slate-500 col-span-full border border-slate-800/80 rounded-2xl bg-slate-900/40">KPI ma\'lumotlari yuklanmoqda...</div>';

      try {
        let periodVal = document.getElementById('kpi-period-filter')?.value;
        if (!periodVal) {
          periodVal = new Date().toISOString().slice(0, 7);
          const filterInput = document.getElementById('kpi-period-filter');
          if (filterInput) filterInput.value = periodVal;
        }

        const resp = await fetch(`/api/v1/kpi/overview?period=${encodeURIComponent(periodVal)}`, {
          headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });
        const data = await resp.json();
        if (!data || data.length === 0) {
          container.innerHTML = `<div class="p-8 text-center text-xs text-slate-500 col-span-full border border-slate-800/80 rounded-2xl bg-slate-900/40">${periodVal} davri uchun KPI ma'lumotlari mavjud emas.</div>`;
          return;
        }

        container.innerHTML = data.map(k => {
          const empName = k.employee ? k.employee.full_name : `Xodim #${k.employee_id}`;
          const empRole = k.employee ? (roleNameMap[k.employee.role] || k.employee.role) : 'Xodim';
          const dept = allDepartmentsList.find(d => d.id === k.employee?.department_id);
          const deptName = dept ? dept.name : (k.employee?.department_id ? `Bo'lim #${k.employee.department_id}` : 'Bo\'limsiz');

          return `
            <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-3.5 hover:border-slate-700 transition">
              <div class="flex items-start justify-between gap-2">
                <div>
                  <h5 class="text-sm font-bold text-white">${empName}</h5>
                  <p class="text-xs text-slate-400 mt-0.5">${empRole} • <span class="text-emerald-400 font-medium">${deptName}</span></p>
                </div>
                <span class="px-2.5 py-1 rounded-full text-xs font-bold border border-emerald-500/20 bg-emerald-500/10 text-emerald-400 whitespace-nowrap">
                  ${k.kpi_percentage}%
                </span>
              </div>

              <div class="w-full bg-slate-950 rounded-full h-2 overflow-hidden">
                <div class="bg-emerald-500 h-2 rounded-full transition-all duration-500" style="width: ${Math.min(100, k.kpi_percentage)}%;"></div>
              </div>

              <div class="grid grid-cols-2 gap-2 text-xs text-slate-400 pt-1 bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
                <div>To'plangan: <span class="font-semibold text-white ml-1">${k.completed_points} ball</span></div>
                <div>Maqsad: <span class="font-semibold text-white ml-1">${k.target_points} ball</span></div>
                <div>Murojaatlar: <span class="font-semibold text-white ml-1">${k.total_appeals_completed} ta</span></div>
                <div>Qabullar: <span class="font-semibold text-white ml-1">${k.total_appointments_completed} ta</span></div>
                <div>O'rtacha baho: <span class="font-semibold text-white ml-1">${k.average_rating} ★</span></div>
                <div>Jarima: <span class="font-semibold text-rose-400 ml-1">-${k.penalty_points} ball</span></div>
              </div>
            </div>
          `;
        }).join('');
      } catch (e) {
        container.innerHTML = '<div class="p-8 text-center text-xs text-rose-400 col-span-full border border-slate-800/80 rounded-2xl bg-slate-900/40">KPI yuklashda xatolik yuz berdi.</div>';
      } finally {
        if (btn) btn.disabled = false;
        if (icon) icon.classList.remove('animate-spin');
      }
    }

    // 12. TAB: BAYRAMLAR TAQVIMI VA DAM OLISH KUNLARI
    function openAddHolidayModal() {
      const today = new Date().toISOString().slice(0, 10);
      document.getElementById('holiday-date-input').value = today;
      document.getElementById('holiday-title-input').value = "";
      document.getElementById('holiday-is-working-input').checked = false;
      document.getElementById('add-holiday-modal').classList.remove('hidden');
    }

    function closeAddHolidayModal() {
      document.getElementById('add-holiday-modal').classList.add('hidden');
    }

    async function handleSaveHoliday(e) {
      e.preventDefault();
      const dateVal = document.getElementById('holiday-date-input').value;
      const titleVal = document.getElementById('holiday-title-input').value.trim();
      const isWorking = document.getElementById('holiday-is-working-input').checked;

      if (!dateVal || !titleVal) {
        showToast("Sana va bayram nomini to'ldiring.", "warning");
        return;
      }

      const saveBtn = document.getElementById('save-holiday-btn');
      if (saveBtn) saveBtn.disabled = true;

      try {
        const resp = await fetch('/api/v1/calendar/holidays', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            holiday_date: dateVal,
            title: titleVal,
            is_working_day: isWorking
          })
        });

        const data = await resp.json();
        if (resp.ok) {
          showToast("Yangi bayram sanasi muvaffaqiyatli saqlandi!", "success");
          closeAddHolidayModal();
          loadHolidays();
        } else {
          showToast(extractErrorMessage(data, "Bayramni saqlashda xatolik yuz berdi."), "error");
        }
      } catch (err) {
        showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
      } finally {
        if (saveBtn) saveBtn.disabled = false;
      }
    }

    let allHolidaysList = [];

    async function deleteHoliday(id) {
      const h = (allHolidaysList || []).find(item => item.id === id);
      const title = h ? h.title : "Bayram";
      const ok = await openAppConfirm({
        title: "Bayramni o'chirish",
        message: `Haqiqatan ham "${title}" sanasini taqvimdan o'chirmoqchimisiz? Ushbu sanada SLA hisoblash qayta tiklanadi.`,
        confirmText: "O'chirish",
        cancelText: "Bekor qilish",
        isDanger: true
      });
      if (!ok) return;

      try {
        const resp = await fetch(`/api/v1/calendar/holidays/${id}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (resp.ok || resp.status === 204) {
          showToast("Bayram sanasi muvaffaqiyatli o'chirildi.", "success");
          loadHolidays();
        } else {
          showToast("Bayramni o'chirishda xatolik yuz berdi.", "error");
        }
      } catch (e) {
        showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
      }
    }
