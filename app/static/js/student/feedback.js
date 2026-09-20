// === RATING & EVALUATION SYSTEM ===
let activeRatingAppealId = null;
let currentRatingValue = 5;

const RATING_LABELS = {
  1: "1 - Juda qoniqarsiz (muammo hal bo'lmadi)",
  2: "2 - Qoniqarsiz (sifatsiz xizmat ko'rsatildi)",
  3: "3 - O'rtacha (qoniqarli)",
  4: "4 - Yaxshi (talab darajasida)",
  5: "5 - A'lo darajada (mukammal ijro)"
};

// --- MAJBURIY TASDIQLASH VA BAHOLASH DEVORI (FEEDBACK WALL) ---
let pendingFwAppeal = null;
let fwSelectedRating = 5;

async function checkPendingFeedback() {
  if (!token) return;
  try {
    const res = await fetch(apiUrl('/api/v1/appeals/pending-feedback'), {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (res.ok) {
      const appeal = await res.json();
      if (appeal && appeal.id) {
        pendingFwAppeal = appeal;
        showFeedbackWall(appeal);
      }
    }
  } catch (e) {
    console.error("Pending feedback tekshirishda xatolik:", e);
  }
}

function showFeedbackWall(appeal) {
  document.getElementById('fw-appeal-title').innerText = appeal.subject || "Arizangiz ko'rib chiqildi";
  document.getElementById('fw-ticket-number').innerText = appeal.ticket_number;
  document.getElementById('fw-resolved-date').innerText = appeal.resolved_at ? formatDateTime(appeal.resolved_at) : '';
  document.getElementById('fw-resolution-text').innerText = appeal.resolution_text || "Xizmat muvaffaqiyatli ko'rsatildi.";
  
  const docsBox = document.getElementById('fw-docs-container');
  const pdfLink = document.getElementById('fw-pdf-link');
  const qrLink = document.getElementById('fw-qr-link');
  if (appeal.result_file_url) {
    docsBox.classList.remove('hidden');
    pdfLink.href = apiUrl(appeal.result_file_url);
    if (appeal.qr_hash) {
      qrLink.href = apiUrl('/verify/' + appeal.qr_hash);
      qrLink.classList.remove('hidden');
    } else {
      qrLink.classList.add('hidden');
    }
  } else {
    docsBox.classList.add('hidden');
  }

  setFwRating(5);
  const wallModal = document.getElementById('feedback-wall-modal');
  if (wallModal) wallModal.classList.remove('hidden');
}

function setFwRating(val) {
  fwSelectedRating = val;
  const stars = document.querySelectorAll('.fw-star');
  stars.forEach((s, idx) => {
    if (idx < val) {
      s.classList.add('text-amber-400');
      s.classList.remove('text-slate-600');
    } else {
      s.classList.remove('text-amber-400');
      s.classList.add('text-slate-600');
    }
  });
  const labels = [
    "", "1 - Juda yomon", "2 - Qoniqarsiz", "3 - O'rtacha", "4 - Yaxshi", "5 - A'lo darajada"
  ];
  const descEl = document.getElementById('fw-rating-desc');
  if (descEl) descEl.innerText = labels[val] || '';
}

async function submitFwConfirm() {
  if (!pendingFwAppeal) return;
  const commentInput = document.getElementById('fw-comment-input');
  const comment = commentInput ? commentInput.value.trim() : '';
  const btn = document.getElementById('fw-confirm-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="animate-spin">⌛</span> Tasdiqlanmoqda...';

  try {
    const res = await fetch(apiUrl(`/api/v1/appeals/${pendingFwAppeal.id}/confirm`), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token
      },
      body: JSON.stringify({
        rating: fwSelectedRating || 5,
        rating_comment: comment
      })
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(err.detail || "Xatolik yuz berdi", "error");
      btn.disabled = false;
      btn.innerHTML = 'Tasdiqlayman (Muammo to\'liq hal bo\'ldi)';
      return;
    }

    showToast("Murojaat tasdiqlandi va xodimga baho berildi. Rahmat!", "success");
    const wallModal = document.getElementById('feedback-wall-modal');
    if (wallModal) wallModal.classList.add('hidden');
    pendingFwAppeal = null;
    loadStudentAppeals();
  } catch (e) {
    showToast("Tarmoq xatosi", "error");
    btn.disabled = false;
    btn.innerHTML = 'Tasdiqlayman (Muammo to\'liq hal bo\'ldi)';
  }
}

function openFwDispute() {
  if (!pendingFwAppeal) return;
  const wallModal = document.getElementById('feedback-wall-modal');
  if (wallModal) wallModal.classList.add('hidden');
  openDisputeModal(pendingFwAppeal.id);
}

function openRatingModal(appealId) {
  activeRatingAppealId = appealId;
  currentRatingValue = 5;
  selectStarRating(5);
  const commentInput = document.getElementById('rating-comment-input');
  if (commentInput) commentInput.value = "";
  const modal = document.getElementById('student-rating-modal');
  if (modal) modal.classList.remove('hidden');
}

function closeRatingModal() {
  activeRatingAppealId = null;
  const modal = document.getElementById('student-rating-modal');
  if (modal) modal.classList.add('hidden');
}

function selectStarRating(val) {
  currentRatingValue = val;
  updateStarDisplay(val);
  const label = document.getElementById('star-rating-label');
  if (label) label.innerText = RATING_LABELS[val] || `${val} yulduz`;
}

function previewStarRating(val) {
  updateStarDisplay(val);
  const label = document.getElementById('star-rating-label');
  if (label) label.innerText = RATING_LABELS[val] || `${val} yulduz`;
}

function resetStarPreview() {
  updateStarDisplay(currentRatingValue);
  const label = document.getElementById('star-rating-label');
  if (label) label.innerText = RATING_LABELS[currentRatingValue] || `${currentRatingValue} yulduz`;
}

function updateStarDisplay(val) {
  const buttons = document.querySelectorAll('#star-rating-buttons .star-btn');
  buttons.forEach(btn => {
    const starNum = parseInt(btn.getAttribute('data-star'));
    if (starNum <= val) {
      btn.className = 'star-btn text-2xl transition transform hover:scale-110 cursor-pointer text-amber-400';
    } else {
      btn.className = 'star-btn text-2xl transition transform hover:scale-110 cursor-pointer text-slate-700';
    }
  });
}

async function submitRating() {
  if (!activeRatingAppealId) return;
  const btn = document.getElementById('submit-rating-btn');
  const comment = document.getElementById('rating-comment-input')?.value?.trim() || null;
  
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="animate-spin">⏳</span> Saqlanmoqda...';
  }

  try {
    const resp = await fetch(`/api/v1/appeals/${activeRatingAppealId}/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
      body: JSON.stringify({
        rating: currentRatingValue,
        rating_comment: comment
      })
    });
    const data = await resp.json();
    if (resp.ok) {
      closeRatingModal();
      showToast("Xizmat ijrosi muvaffaqiyatli tasdiqlandi va baholandi!", "success");
      loadStudentAppeals();
    } else {
      showToast(data.detail || "Baholashda xatolik yuz berdi.", "error");
    }
  } catch (err) {
    showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<span>Tasdiqlash va baholash</span>';
    }
  }
}

// === DISPUTE SYSTEM ===
let activeDisputeAppealId = null;

function openDisputeModal(appealId) {
  activeDisputeAppealId = appealId;
  const input = document.getElementById('dispute-reason-input');
  if (input) input.value = "";
  const modal = document.getElementById('student-dispute-modal');
  if (modal) modal.classList.remove('hidden');
}

function closeDisputeModal() {
  activeDisputeAppealId = null;
  const modal = document.getElementById('student-dispute-modal');
  if (modal) modal.classList.add('hidden');
}

async function submitDispute() {
  if (!activeDisputeAppealId) return;
  const reason = document.getElementById('dispute-reason-input')?.value?.trim();
  if (!reason || reason.length < 5) {
    showToast("E'tiroz sababini batafsil yozing (kamida 5 ta belgi).", "warning");
    return;
  }

  const btn = document.getElementById('submit-dispute-btn');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="animate-spin">⏳</span> Yuborilmoqda...';
  }

  try {
    const resp = await fetch(`/api/v1/appeals/${activeDisputeAppealId}/dispute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
      body: JSON.stringify({ dispute_reason: reason })
    });
    const data = await resp.json();
    if (resp.ok) {
      closeDisputeModal();
      showToast("E'tirozingiz Registrator ofisi boshlig'i nazoratiga yuborildi.", "info");
      loadStudentAppeals();
    } else {
      showToast(data.detail || "E'tiroz yuborishda xatolik yuz berdi.", "error");
    }
  } catch (err) {
    showToast("Server bilan aloqa o'rnatib bo'lmadi.", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<span>E\'tirozni yuborish</span>';
    }
  }
}

