function getTashkentTodayStr() {
  const now = new Date();
  const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
  const tashkentDate = new Date(utc + (3600000 * 5));
  const year = tashkentDate.getFullYear();
  const month = String(tashkentDate.getMonth() + 1).padStart(2, '0');
  const day = String(tashkentDate.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

async function fetchUserProfile() {
  try {
    const resp = await fetch('/api/v1/auth/me', {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (resp.status === 401) {
      handleLogout();
      return;
    }
    currentUser = await resp.json();
    document.getElementById('student-name').innerText = currentUser.full_name;
    document.getElementById('student-id').innerText = currentUser.hemis_student_id || currentUser.username;
    document.getElementById('student-grp').innerText = (currentUser.group_name || "Guruh") + " (" + (currentUser.course || 1) + "-kurs)";

    const eduForm = currentUser.education_form || "Kunduzgi";
    document.getElementById('student-eduform').innerText = eduForm;

    // Kunduzgi talaba bo'lsa navbat sanasini faqat bugun bilan cheklash
    const isKunduzgi = currentUser.education_form && currentUser.education_form.trim().toLowerCase() === 'kunduzgi';
    const qDateInput = document.getElementById('queue-date');
    const todayStr = getTashkentTodayStr();
    if (isKunduzgi) {
      qDateInput.min = todayStr;
      qDateInput.max = todayStr;
      qDateInput.value = todayStr;
      const note = document.getElementById('kunduzgi-queue-note');
      if (note) note.classList.remove('hidden');
    } else {
      qDateInput.min = todayStr;
      // Sirtqi/masofaviy talabalar uchun 14 kunlik cheklov
      const maxD = new Date();
      maxD.setDate(maxD.getDate() + 14);
      qDateInput.max = maxD.toISOString().split('T')[0];
    }

    // Profile tab fields
    document.getElementById('prof-name').innerText = currentUser.full_name || "-";
    document.getElementById('prof-id').innerText = currentUser.hemis_student_id || currentUser.username || "-";
    document.getElementById('prof-faculty').innerText = currentUser.faculty || "-";
    document.getElementById('prof-specialty').innerText = currentUser.specialty || "-";
    const groupPart = currentUser.group_name || "-";
    const coursePart = currentUser.course ? `${currentUser.course}-kurs` : "";
    document.getElementById('prof-group').innerText = coursePart ? `${groupPart}, ${coursePart}` : groupPart;
    document.getElementById('prof-eduform').innerText = currentUser.education_type ? `${eduForm} (${currentUser.education_type})` : eduForm;

    // Telegram holatini tekshirish
    const tgStatusEl = document.getElementById('student-tg-status');
    const tgBannerEl = document.getElementById('telegram-reminder-banner');

    if (currentUser.telegram_chat_id) {
      if (tgBannerEl) tgBannerEl.classList.add('hidden');
      if (tgStatusEl) {
        const uName = currentUser.telegram_username ? `@${currentUser.telegram_username}` : 'Ulangan';
        tgStatusEl.innerHTML = `<span class="text-emerald-400 font-semibold">✓ ${uName}</span>`;
      }
    } else {
      try {
        const tgResp = await fetch('/api/v1/auth/telegram-info', {
          headers: { 'Authorization': 'Bearer ' + token }
        });
        if (tgResp.ok) {
          const tgInfo = await tgResp.json();
          const connectBtn = document.getElementById('telegram-connect-btn');
          if (connectBtn) connectBtn.href = tgInfo.deep_link;
          if (tgStatusEl) {
            tgStatusEl.innerHTML = `<a href="${tgInfo.deep_link}" target="_blank" class="text-blue-400 hover:underline">Ulanish</a>`;
          }
          if (tgBannerEl && !sessionStorage.getItem('roffice_dismiss_tg_reminder')) {
            tgBannerEl.classList.remove('hidden');
          }
        }
      } catch (tge) {
        console.error("Telegram info yuklashda xatolik:", tge);
      }
    }
  } catch (e) {
    console.error("Profil yuklash xatosi:", e);
  }
}

function dismissTelegramReminder() {
  sessionStorage.setItem('roffice_dismiss_tg_reminder', 'true');
  const b = document.getElementById('telegram-reminder-banner');
  if (b) b.classList.add('hidden');
}

async function loadEducationPolicy() {
  try {
    const resp = await fetch('/api/v1/appeals/policy/education-forms');
    currentPolicy = await resp.json();
    checkStudentFormRestriction();
  } catch (e) {
    console.error("Siyosat xatosi:", e);
  }
}

function checkStudentFormRestriction() {
  if (!currentUser) return;
  const eduForm = (currentUser.education_form || "Kunduzgi").toLowerCase();
  let isAllowed = false;
  if (currentPolicy && currentPolicy.allowed_forms) {
    isAllowed = currentPolicy.allowed_forms.some(f => eduForm.includes(f));
  } else {
    isAllowed = !eduForm.includes('kunduzgi');
  }

  const alertBox = document.getElementById('appeal-restriction-alert');
  const submitBtn = document.getElementById('appeal-submit-btn');

  if (!isAllowed) {
    alertBox.classList.remove('hidden');
    submitBtn.disabled = true;
    submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
    submitBtn.querySelector('span').innerText = `${currentUser.education_form || "Ushbu"} ta'lim shakli uchun onlayn murojaat cheklangan`;
  } else {
    alertBox.classList.add('hidden');
    submitBtn.disabled = false;
    submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
    submitBtn.querySelector('span').innerText = "Murojaatni yuborish";
  }
}

