async function loadHolidays() {
      const container = document.getElementById('holidays-list');
      if (!container) return;

      const btn = document.getElementById('refresh-holidays-btn');
      const icon = document.getElementById('refresh-holidays-icon');
      if (btn) btn.disabled = true;
      if (icon) icon.classList.add('animate-spin');

      container.innerHTML = '<div class="p-8 text-center text-xs text-slate-500 col-span-full border border-slate-800/80 rounded-2xl bg-slate-900/40">Bayramlar yuklanmoqda...</div>';

      try {
        const resp = await fetch('/api/v1/calendar/holidays');
        const holidays = await resp.json();
        allHolidaysList = holidays || [];
        if (!holidays || holidays.length === 0) {
          container.innerHTML = '<div class="p-8 text-center text-xs text-slate-500 col-span-full border border-slate-800/80 rounded-2xl bg-slate-900/40">Taqvimda kiritilgan bayramlar mavjud emas.</div>';
          return;
        }

        container.innerHTML = holidays.map(h => `
          <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-3 relative group hover:border-slate-700 transition">
            <div class="flex items-center justify-between">
              <span class="inline-block font-mono text-xs font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-0.5 rounded-lg">${h.holiday_date}</span>
              <span class="px-2 py-0.5 rounded text-[10px] font-semibold ${h.is_working_day ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'}">
                ${h.is_working_day ? 'Ko\'chirilgan ish kuni' : 'Dam olish kuni'}
              </span>
            </div>
            <div>
              <h5 class="text-sm font-bold text-white leading-snug">${h.title}</h5>
              <p class="text-xs text-slate-400 mt-1">SLA taymerlari avtomatik to'xtatiladi</p>
            </div>
            <div class="pt-2 border-t border-slate-800 flex justify-end">
              <button
                type="button"
                onclick="deleteHoliday(${h.id})"
                class="px-2.5 py-1 rounded-lg border border-slate-800 hover:border-rose-500/40 hover:bg-rose-500/10 text-slate-400 hover:text-rose-400 text-xs transition cursor-pointer"
              >
                O'chirish
              </button>
            </div>
          </div>
        `).join('');
      } catch (e) {
        container.innerHTML = '<div class="p-8 text-center text-xs text-rose-400 col-span-full border border-slate-800/80 rounded-2xl bg-slate-900/40">Bayramlarni yuklab bo\'lmadi.</div>';
      } finally {
        if (btn) btn.disabled = false;
        if (icon) icon.classList.remove('animate-spin');
      }
    }

    // 13. TAB: RAHBARIYAT TAHLILIY INFOGRAFIKASI VA HISOBOTLAR (EXECUTIVE ANALYTICS)
    let executiveAnalyticsData = null;
    let chartFacultyInstance = null;
    let chartServicesInstance = null;
    let chartStatusInstance = null;
    let chartTrendInstance = null;
