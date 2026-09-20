function selectSlot(btnEl, slotTime) {
  document.querySelectorAll('.slot-btn').forEach(b => {
    b.className = 'slot-btn px-2.5 py-2 rounded-lg border text-[11px] font-mono font-medium transition cursor-pointer text-center bg-slate-900/80 border-slate-700/80 text-slate-200 hover:border-blue-500 hover:bg-slate-800';
  });
  btnEl.className = 'slot-btn px-2.5 py-2 rounded-lg border text-[11px] font-mono font-medium transition cursor-pointer text-center bg-blue-600 border-blue-500 text-white shadow-md ring-2 ring-blue-500/30';
  selectedSlot = slotTime;
}

function selectNextAvailableDate() {
  const isKunduzgi = currentUser && currentUser.education_form && currentUser.education_form.trim().toLowerCase() === 'kunduzgi';
  if (isKunduzgi) {
    showToast("Kunduzgi ta'lim talabalari elektron navbatni faqat joriy kun (bugun) uchun olishlari mumkin.", "warning");
    return;
  }
  const qDateInput = document.getElementById('queue-date');
  const d = new Date();
  d.setDate(d.getDate() + 1);
  if (d.getDay() === 0) d.setDate(d.getDate() + 1); // Yakshanba bo'lsa dushanbaga
  qDateInput.value = d.toISOString().split('T')[0];
  loadAvailableSlots();
}

async function loadAvailableSlots() {
  const serviceId = document.getElementById('queue-service-select').value;
  const dateVal = document.getElementById('queue-date').value;
  const container = document.getElementById('slots-container');

  if (!serviceId || !dateVal) return;

  selectedSlot = null;
  container.innerHTML = '<p class="text-xs text-slate-400 py-3">Slotlar yuklanmoqda...</p>';
  try {
    const resp = await fetch(`/api/v1/appointments/available-slots?service_id=${serviceId}&appointment_date=${dateVal}&detailed=true`);
    const data = await resp.json();

    const isKunduzgi = (currentUser && currentUser.education_form && currentUser.education_form.trim().toLowerCase() === 'kunduzgi') || Boolean(data.is_kunduzgi);

    // 1. Agar dam olish yoki bayram bo'lsa
    if (!data.is_working_day) {
      const nextDate = data.next_available_date || '';
      container.innerHTML = `
        <div class="w-full p-4 rounded-xl bg-amber-500/10 border border-amber-500/25 text-amber-300 text-xs space-y-2">
          <div class="font-semibold flex items-center gap-1.5 text-amber-400">
            <i class="ph ph-warning-circle text-base"></i> Qabul mavjud emas
          </div>
          <p class="text-slate-300 leading-relaxed">${data.message || "Dam olish yoki bayram kuni."}</p>
          ${!isKunduzgi && nextDate ? `
            <button type="button" onclick="document.getElementById('queue-date').value='${nextDate}'; loadAvailableSlots();" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-xs font-semibold cursor-pointer transition">
              Keyingi ish kuniga o'tish (${nextDate}) ➜
            </button>
          ` : (isKunduzgi ? `<p class="text-[11px] text-amber-400/90 pt-1 font-medium">Navbatdagi ish kuni ertalab soat 08:30 dan boshlab navbat olishingiz mumkin.</p>` : '')}
        </div>
      `;
      return;
    }

    // 2. Agar bugungi ish vaqtlari to'liq yakunlangan bo'lsa
    if (data.is_today && data.total_available === 0) {
      if (isKunduzgi) {
        container.innerHTML = `
          <div class="w-full p-4 rounded-xl bg-slate-900/90 border border-slate-800 text-center space-y-2">
            <div class="font-bold text-amber-400 text-xs flex items-center justify-center gap-1.5">
              <i class="ph ph-clock-countdown text-base"></i> Bugungi qabul soatlari yakunlangan
            </div>
            <p class="text-xs text-slate-300 max-w-md mx-auto leading-relaxed">
              Registrator ofisi qabul soatlari dushanba-shanba kunlari <b>09:00 dan 17:00 gacha</b>. Kunduzgi ta'lim talabalari navbat talonini navbatdagi ish kuni ertalab soat 08:30 dan boshlab olishlari mumkin.
            </p>
          </div>
        `;
        return;
      } else if (data.next_available_date) {
        const nextDate = data.next_available_date;
        document.getElementById('queue-date').value = nextDate;
        container.innerHTML = `
          <div class="w-full p-3.5 mb-2 rounded-xl bg-blue-500/10 border border-blue-500/25 text-blue-300 text-xs space-y-1">
            <div class="font-semibold flex items-center gap-1.5 text-blue-400">
              <i class="ph ph-info text-base"></i> Eng yaqin qabul kuni
            </div>
            <p class="text-slate-300 leading-relaxed">Bugungi barcha qabul soatlari yakunlangan. Sizga eng yaqin qabul kuni (<b>${nextDate}</b>) ochilmoqda...</p>
          </div>
        `;
        setTimeout(() => loadAvailableSlots(), 600);
        return;
      }
    }

    const slots = data.slots || [];
    const activeSlots = slots.filter(s => s.status !== 'past');

    if (activeSlots.length === 0) {
      container.innerHTML = `
        <div class="w-full p-4 text-center text-xs text-slate-400 bg-slate-950/60 rounded-xl border border-slate-800">
          Ushbu kunga bo'sh qabul vaqtlari qolmagan.
          ${!isKunduzgi && data.next_available_date ? `
            <div class="mt-2">
              <button type="button" onclick="document.getElementById('queue-date').value='${data.next_available_date}'; loadAvailableSlots();" class="text-blue-400 hover:text-blue-300 font-semibold underline cursor-pointer">
                Keyingi ish kunini tanlash (${data.next_available_date}) ➜
              </button>
            </div>
          ` : ''}
        </div>
      `;
      return;
    }

    const morningSlots = activeSlots.filter(s => s.session === 'morning');
    const afternoonSlots = activeSlots.filter(s => s.session === 'afternoon');

    let html = '<div class="space-y-4 w-full">';

    // 🌅 Ertalabki seans
    if (morningSlots.length > 0) {
      html += `
        <div>
          <div class="flex items-center justify-between text-xs font-semibold text-slate-300 mb-2">
            <span class="flex items-center gap-1.5">🌅 Ertalabki qabul (09:00 — 13:00)</span>
            <span class="text-[11px] text-slate-500 font-normal">${morningSlots.filter(s => s.is_available).length} ta bo'sh</span>
          </div>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
      `;
      morningSlots.forEach(s => {
        html += renderSlotItem(s);
      });
      html += '</div></div>';
    }

    // 🌇 Tushdan keyingi seans
    if (afternoonSlots.length > 0) {
      html += `
        <div>
          <div class="flex items-center justify-between text-xs font-semibold text-slate-300 mb-2 pt-2 border-t border-slate-800/60">
            <span class="flex items-center gap-1.5">🌇 Tushdan keyingi qabul (14:00 — 17:00)</span>
            <span class="text-[11px] text-slate-500 font-normal">${afternoonSlots.filter(s => s.is_available).length} ta bo'sh</span>
          </div>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
      `;
      afternoonSlots.forEach(s => {
        html += renderSlotItem(s);
      });
      html += '</div></div>';
    }

    html += '</div>';

    // Izoh ko'rsatgichi
    html += `
      <div class="w-full flex items-center justify-between text-[11px] text-slate-400 pt-3 border-t border-slate-800/80 mt-1">
        <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block"></span> Bo'sh (ochiq)</span>
        <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-rose-500/80 inline-block"></span> Band qilingan</span>
      </div>
    `;

    container.innerHTML = html;

    // Birinchi bo'sh slotni avtomatik tanlash
    const firstFree = activeSlots.find(s => s.is_available);
    if (firstFree) {
      selectedSlot = firstFree.time_slot;
      const firstBtn = container.querySelector(`[data-slot="${firstFree.time_slot}"]`);
      if (firstBtn) {
        firstBtn.className = 'slot-btn px-2.5 py-2.5 rounded-xl border text-xs font-mono font-medium transition cursor-pointer text-center bg-blue-600 border-blue-500 text-white shadow-lg shadow-blue-600/25 ring-2 ring-blue-500/30';
      }
    }
  } catch (e) {
    container.innerHTML = '<p class="text-xs text-rose-400 py-3">Navbat vaqtlarini yuklab bo\'lmadi.</p>';
  }
}

function renderSlotItem(s) {
  if (s.status === 'past') {
    return `
      <div title="Ushbu vaqt oralig'i o'tib ketgan" class="px-2.5 py-2.5 rounded-xl border border-slate-800 bg-slate-950/40 text-slate-500 text-xs font-mono text-center opacity-40 cursor-not-allowed select-none">
        ${s.time_slot}
        <span class="block text-[10px] font-sans text-slate-500 font-normal">Vaqt o'tgan</span>
      </div>
    `;
  }
  if (!s.is_available) {
    return `
      <div title="Ushbu vaqt band qilingan" class="px-2.5 py-2.5 rounded-xl border border-rose-950/40 bg-rose-950/20 text-rose-400 text-xs font-mono text-center opacity-60 cursor-not-allowed select-none">
        ${s.time_slot}
        <span class="block text-[10px] font-sans text-rose-400/80 font-normal">Band</span>
      </div>
    `;
  }
  return `
    <button type="button" data-slot="${s.time_slot}" onclick="selectSlot(this, '${s.time_slot}')" class="slot-btn px-2.5 py-2.5 rounded-xl border text-xs font-mono font-medium transition cursor-pointer text-center bg-slate-900/80 border-slate-700/80 text-slate-200 hover:border-blue-500 hover:bg-slate-800">
      ${s.time_slot}
      <span class="block text-[10px] font-sans text-emerald-400 font-normal">Bo'sh</span>
    </button>
  `;
}

async function bookQueueTicket() {
  const serviceId = document.getElementById('queue-service-select').value;
  const dateVal = document.getElementById('queue-date').value;
  const todayStr = getTashkentTodayStr();

  const isKunduzgi = currentUser && currentUser.education_form && currentUser.education_form.trim().toLowerCase() === 'kunduzgi';
  if (isKunduzgi && dateVal !== todayStr) {
    showToast("Kunduzgi ta'lim talabalari elektron navbatni faqat joriy kun (bugun) uchun olishlari mumkin.", "error");
    document.getElementById('queue-date').value = todayStr;
    loadAvailableSlots();
    return;
  }

  if (!selectedSlot) {
    showToast("Iltimos, qabul vaqt oralig'ini tanlang.", "warning");
    return;
  }

  try {
    const resp = await fetch('/api/v1/appointments/book', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
      body: JSON.stringify({
        service_id: parseInt(serviceId),
        appointment_date: dateVal,
        time_slot: selectedSlot
      })
    });
    const res = await resp.json();
    if (resp.ok) {
      const box = document.getElementById('ticket-display');
      document.getElementById('ticket-code-val').innerText = res.ticket_code;
      document.getElementById('ticket-window-val').innerText = res.window_number;
      document.getElementById('ticket-date-val').innerText = res.appointment_date;
      document.getElementById('ticket-time-val').innerText = res.time_slot;
      
      const sTitle = res.service ? res.service.title : "Registrator ofisi xizmati";
      const printBtn = document.getElementById('print-active-ticket-btn');
      if (printBtn) {
        printBtn.onclick = () => printQueueTicket(res.ticket_code, res.window_number, res.appointment_date, res.time_slot, sTitle);
      }

      box.classList.remove('hidden');
      loadAvailableSlots();
      loadStudentAppointments();
      showToast("Elektron navbat taloni muvaffaqiyatli olindi!", "success");
    } else {
      showToast(res.detail || "Navbat olishda xatolik yuz berdi.", "error");
    }
  } catch (e) {
    showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
  }
}

async function loadStudentAppointments() {
  const container = document.getElementById('student-appointments-list');
  const countEl = document.getElementById('student-tickets-count');
  if (!container) return;

  container.innerHTML = '<div class="p-6 text-center text-xs text-slate-500 border border-slate-800/80 rounded-2xl bg-slate-900/40">Talonlar yuklanmoqda...</div>';

  try {
    const resp = await fetch('/api/v1/appointments', {
      headers: token ? { 'Authorization': 'Bearer ' + token } : {}
    });
    if (!resp.ok) {
      container.innerHTML = '<div class="p-6 text-center text-xs text-rose-400 border border-slate-800/80 rounded-2xl bg-slate-900/40">Talonlarni yuklab bo\'lmadi.</div>';
      return;
    }

    const list = await resp.json();
    if (countEl) countEl.innerText = list.length;

    if (!list || list.length === 0) {
      container.innerHTML = '<div class="p-6 text-center text-xs text-slate-500 border border-slate-800/80 rounded-2xl bg-slate-900/40">Sizda hali navbat talonlari mavjud emas. Yuqoridagi shakl orqali navbat oling.</div>';
      return;
    }

    const statusBadges = {
      'booked': '<span class="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">Kutilmoqda</span>',
      'checked_in': '<span class="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">Yetib kelgan (Zalda)</span>',
      'in_service': '<span class="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">Qabul qilinmoqda</span>',
      'completed': '<span class="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Yakunlangan</span>',
      'cancelled': '<span class="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">Bekor qilingan</span>'
    };

    container.innerHTML = list.map(item => {
      const serviceTitle = item.service ? item.service.title : "Registrator ofisi xizmati";
      const windowNum = item.window_number || "1-darcha";
      const isBooked = item.status === 'booked';
      const safeServiceTitle = serviceTitle.replace(/'/g, "\\'");

      return `
        <div class="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3 hover:border-slate-700 transition">
          <div class="flex items-center justify-between gap-2 flex-wrap">
            <div class="flex items-center gap-2">
              <span class="font-mono text-sm font-bold text-white bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800">${item.ticket_code}</span>
              <span class="text-xs font-semibold text-slate-200">${serviceTitle}</span>
            </div>
            <div>${statusBadges[item.status] || item.status}</div>
          </div>

          <div class="flex items-center justify-between text-xs text-slate-400 pt-1 border-t border-slate-800/80 flex-wrap gap-2">
            <div>
              <span>Sana: <strong class="text-slate-200 font-mono">${item.appointment_date}</strong></span>
              <span class="mx-1.5">•</span>
              <span>Vaqt: <strong class="text-blue-400 font-mono">${item.time_slot}</strong></span>
            </div>
            <div>Darcha: <strong class="text-emerald-400 font-medium">${windowNum}</strong></div>
          </div>

          <div class="flex items-center justify-end gap-2 pt-2 border-t border-slate-800/60 flex-wrap">
            <button
              type="button"
              onclick="printQueueTicket('${item.ticket_code}', '${windowNum}', '${item.appointment_date}', '${item.time_slot}', '${safeServiceTitle}')"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-800 hover:border-slate-700 bg-slate-950 text-slate-300 hover:text-white text-xs font-medium transition cursor-pointer"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
              <span>Chop etish</span>
            </button>
            ${isBooked ? `
              <button
                type="button"
                onclick="handleStudentCheckIn(${item.id})"
                class="px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition cursor-pointer"
              >
                Yetib keldim (Check-in)
              </button>
              <button
                type="button"
                onclick="handleCancelMyAppointment(${item.id})"
                class="px-2.5 py-1.5 rounded-xl border border-slate-800 hover:border-rose-500/40 hover:bg-rose-500/10 text-slate-400 hover:text-rose-400 text-xs transition cursor-pointer"
              >
                Bekor qilish
              </button>
            ` : ''}
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    container.innerHTML = '<div class="p-6 text-center text-xs text-rose-400 border border-slate-800/80 rounded-2xl bg-slate-900/40">Talonlarni yuklashda xatolik.</div>';
  }
}

async function handleStudentCheckIn(id) {
  try {
    const resp = await fetch(`/api/v1/appointments/${id}/check-in`, {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + token }
    });
    const data = await resp.json();
    if (resp.ok) {
      showToast("Ofisga kelganingiz tasdiqlandi. Darcha xodimi navbatingizni qabul qiladi.", "success");
      loadStudentAppointments();
    } else {
      showToast(data.detail || "Xatolik yuz berdi.", "error");
    }
  } catch (e) {
    showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
  }
}

async function handleCancelMyAppointment(id) {
  const ok = await openAppConfirm({
    title: "Navbatni bekor qilish",
    message: "Haqiqatan ham navbat taloningizni bekor qilmoqchimisiz?",
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
    const data = await resp.json();
    if (resp.ok) {
      showToast("Navbat taloni bekor qilindi.", "info");
      loadStudentAppointments();
      loadAvailableSlots();
    } else {
      showToast(data.detail || "Xatolik yuz berdi.", "error");
    }
  } catch (e) {
    showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
  }
}

// === PRINT TICKET SYSTEM ===
function printQueueTicket(ticketCode, windowNumber, appointmentDate, timeSlot, serviceTitle) {
  const printWindow = window.open('', '_blank', 'width=450,height=600');
  if (!printWindow) {
    showToast("Chop etish oynasini ochib bo'lmadi. Brauzer pop-up oynalariga ruxsat bering.", "warning");
    return;
  }

  const html = `
    <!DOCTYPE html>
    <html lang="uz">
    <head>
      <meta charset="UTF-8">
      <title>Elektron navbat taloni - ${ticketCode}</title>
      <style>
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          padding: 24px;
          text-align: center;
          color: #111;
          background: #fff;
        }
        .ticket-box {
          border: 2px dashed #333;
          border-radius: 16px;
          padding: 24px;
          max-width: 340px;
          margin: 0 auto;
        }
        .header {
          font-size: 13px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: #444;
          border-bottom: 1px solid #eee;
          padding-bottom: 12px;
          margin-bottom: 16px;
        }
        .code {
          font-size: 38px;
          font-weight: 900;
          font-family: monospace;
          letter-spacing: 2px;
          margin: 8px 0;
          color: #0b2545;
        }
        .window {
          font-size: 16px;
          font-weight: 700;
          color: #1d4ed8;
          margin-bottom: 16px;
        }
        .details {
          text-align: left;
          font-size: 12px;
          background: #f8fafc;
          border-radius: 8px;
          padding: 12px;
          margin-bottom: 16px;
          line-height: 1.6;
        }
        .details div {
          display: flex;
          justify-content: space-between;
          border-bottom: 1px solid #e2e8f0;
          padding: 4px 0;
        }
        .details div:last-child {
          border-bottom: none;
        }
        .footer {
          font-size: 11px;
          color: #64748b;
          line-height: 1.4;
        }
      </style>
    </head>
    <body>
      <div class="ticket-box">
        <div class="header">
          O'zMU Jizzax filiali<br>Registrator ofisi
        </div>
        <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 1px;">Sizning navbatingiz:</div>
        <div class="code">${ticketCode}</div>
        <div class="window">Qabul darchasi: ${windowNumber || '1-darcha'}</div>
        
        <div class="details">
          <div><span>Xizmat:</span><strong>${serviceTitle || 'Xizmat'}</strong></div>
          <div><span>Qabul sanasi:</span><strong>${appointmentDate}</strong></div>
          <div><span>Qabul vaqti:</span><strong>${timeSlot}</strong></div>
        </div>

        <div class="footer">
          Iltimos, belgilangan vaqtdan 5-10 daqiqa oldin kelib, zal monitoridan navbatingiz chaqirilishini kuting.
        </div>
      </div>
      <script>
        window.onload = function() {
          window.print();
        };
      <\/script>
    </body>
    </html>
  `;

  printWindow.document.write(html);
  printWindow.document.close();
}
