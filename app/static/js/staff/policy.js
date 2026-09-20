async function loadEducationPolicy() {
      const container = document.getElementById('policy-toggles-container');
      if (!container) return;
      try {
        const resp = await fetch('/api/v1/appeals/policy/education-forms');
        currentPolicy = await resp.json();
        renderPolicyToggles(currentPolicy);
      } catch (e) {
        container.innerHTML = '<p class="text-xs text-rose-400">Siyosatni yuklab bo\'lmadi.</p>';
      }
    }

    function renderPolicyToggles(policy) {
      const container = document.getElementById('policy-toggles-container');
      if (!container) return;
      container.innerHTML = '';
      policy.items.forEach(item => {
        const isChecked = item.allowed ? 'checked' : '';
        const badgeClass = item.allowed ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20';
        const badgeText = item.allowed ? "Onlayn ruxsat berilgan" : "Cheklangan (Kelib hal etish)";

        container.innerHTML += `
          <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 flex items-center justify-between gap-4">
            <div class="flex-1">
              <div class="flex items-center gap-2 flex-wrap mb-1">
                <span class="font-bold text-white text-sm">${item.title}</span>
                <span class="px-2 py-0.5 rounded-full text-[10px] font-medium border ${badgeClass}">${badgeText}</span>
              </div>
              <p class="text-xs text-slate-400 leading-relaxed">${item.description}</p>
            </div>
            <div>
              <input
                type="checkbox"
                id="toggle-${item.code}"
                ${isChecked}
                onchange="toggleEducationForm('${item.code}')"
                class="w-5 h-5 accent-emerald-600 rounded cursor-pointer"
              >
            </div>
          </div>
        `;
      });
    }

    async function toggleEducationForm(code) {
      if (!currentPolicy) return;
      const checkbox = document.getElementById('toggle-' + code);
      const isAllowed = checkbox.checked;

      let newAllowed = [...currentPolicy.allowed_forms];
      if (isAllowed && !newAllowed.includes(code)) {
        newAllowed.push(code);
      } else if (!isAllowed && newAllowed.includes(code)) {
        newAllowed = newAllowed.filter(x => x !== code);
      }

      try {
        const resp = await fetch('/api/v1/appeals/policy/education-forms', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
          },
          body: JSON.stringify({ allowed_forms: newAllowed })
        });
        if (resp.ok) {
          currentPolicy = await resp.json();
          renderPolicyToggles(currentPolicy);
          showToast(`Sozlama saqlandi: ${code} ta'lim shakliga onlayn murojaat ${isAllowed ? 'ruxsat berildi' : 'cheklandi'}.`, 'success');
        } else {
          const err = await resp.json();
          showToast(err.detail || "Siyosatni o'zgartirib bo'lmadi", "error");
          checkbox.checked = !isAllowed;
        }
      } catch (e) {
        showToast("Ulanish xatosi: " + e, "error");
        checkbox.checked = !isAllowed;
      }
    }

    // 11. TAB: KPI OVERVIEW
    function setKpiPeriodCurrent() {
      const curMonth = new Date().toISOString().slice(0, 7);
      const input = document.getElementById('kpi-period-filter');
      if (input) input.value = curMonth;
      loadKPIOverview();
    }
