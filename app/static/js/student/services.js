async function loadServices() {
  try {
    const resp = await fetch('/api/v1/services');
    allServices = await resp.json();
    const select1 = document.getElementById('service-select');
    const select2 = document.getElementById('queue-service-select');
    select1.innerHTML = '<option value="">Xizmatni tanlang...</option>';
    select2.innerHTML = '<option value="">Xizmatni tanlang...</option>';

    allServices.forEach(s => {
      const opt = `<option value="${s.id}">${s.title} (SLA: ${s.sla_hours} soat)</option>`;
      select1.innerHTML += opt;
      select2.innerHTML += opt;
    });
    if (allServices.length > 0) {
      select2.value = allServices[0].id;
      loadAvailableSlots();
    }
  } catch (e) {
    console.error("Xizmatlar xatosi:", e);
  }
}
window.loadQueueServices = loadServices;

async function handleFileUpload(inputEl) {
  const file = inputEl.files[0];
  if (!file) return;

  const label = document.getElementById('upload-file-label');
  const statusText = document.getElementById('upload-status-text');
  const hiddenUrlInput = document.getElementById('appeal-attachment-url');
  const removeBtn = document.getElementById('remove-file-btn');

  label.innerText = `Yuklanmoqda: ${file.name}...`;
  statusText.innerText = "Fayl serverga yuklanmoqda, iltimos kuting...";
  statusText.className = "text-[11px] text-blue-400 mt-1";

  const formData = new FormData();
  formData.append('file', file);

  try {
    const resp = await fetch('/api/v1/uploads', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + token },
      body: formData
    });
    const res = await resp.json();

    if (resp.ok && res.file_url) {
      hiddenUrlInput.value = res.file_url;
      label.innerHTML = `<span class="text-emerald-400 font-medium">✓ ${file.name}</span>`;
      statusText.innerText = `Fayl muvaffaqiyatli biriktirildi (${(res.size_bytes / 1024).toFixed(1)} KB).`;
      statusText.className = "text-[11px] text-emerald-400 mt-1";
      removeBtn.classList.remove('hidden');
    } else {
      label.innerText = "Fayl tanlash (PDF, rasm, Word)...";
      statusText.innerText = res.detail || "Fayl yuklashda xatolik yuz berdi.";
      statusText.className = "text-[11px] text-rose-400 mt-1";
      inputEl.value = "";
    }
  } catch (err) {
    label.innerText = "Fayl tanlash (PDF, rasm, Word)...";
    statusText.innerText = "Serverga fayl yuklab bo'lmadi.";
    statusText.className = "text-[11px] text-rose-400 mt-1";
    inputEl.value = "";
  }
}

function clearUploadedFile() {
  document.getElementById('appeal-file-input').value = "";
  document.getElementById('appeal-attachment-url').value = "";
  document.getElementById('upload-file-label').innerText = "Fayl tanlash (PDF, rasm, Word)...";
  document.getElementById('upload-status-text').innerText = "Maksimal hajm: 10 MB. Formatlar: PDF, PNG, JPG, DOCX.";
  document.getElementById('upload-status-text').className = "text-[11px] text-slate-500 mt-1";
  document.getElementById('remove-file-btn').classList.add('hidden');
}

async function handleCreateAppeal(e) {
  e.preventDefault();
  const serviceId = document.getElementById('service-select').value;
  const subject = document.getElementById('appeal-subject').value;
  const message = document.getElementById('appeal-message').value;
  const attachmentUrl = document.getElementById('appeal-attachment-url').value;
  const resBox = document.getElementById('appeal-result-box');

  try {
    const resp = await fetch('/api/v1/appeals', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token
      },
      body: JSON.stringify({
        service_id: parseInt(serviceId),
        subject: subject,
        message: message,
        attachment_urls: attachmentUrl || null
      })
    });
    const res = await resp.json();
    if (resp.ok) {
      resBox.className = 'p-3.5 rounded-xl text-xs font-medium border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 block';
      resBox.innerHTML = `Murojaat qabul qilindi. <strong>Talon raqami: #${res.ticket_number}</strong><br>SLA ijro muddati: ${formatDateTime(res.sla_deadline_at)}`;
      document.getElementById('appeal-form').reset();
      clearUploadedFile();
      localStorage.removeItem('student_appeal_draft');
      loadStudentAppeals();
    } else {
      resBox.className = 'p-3.5 rounded-xl text-xs font-medium border border-rose-500/30 bg-rose-500/10 text-rose-400 block';
      resBox.innerText = res.detail || "Murojaat yuborishda xatolik yuz berdi.";
    }
  } catch (err) {
    resBox.className = 'p-3.5 rounded-xl text-xs font-medium border border-rose-500/30 bg-rose-500/10 text-rose-400 block';
    resBox.innerText = "Server bilan aloqa o'rnatib bo'lmadi.";
  }
}

function initAppealDraftAutoSave() {
  const subjEl = document.getElementById('appeal-subject');
  const msgEl = document.getElementById('appeal-message');
  const svcEl = document.getElementById('service-select');
  if (!subjEl || !msgEl) return;

  // Qoralamani tiklash
  try {
    const saved = localStorage.getItem('student_appeal_draft');
    if (saved) {
      const data = JSON.parse(saved);
      if (data.subject) subjEl.value = data.subject;
      if (data.message) msgEl.value = data.message;
      if (data.serviceId && svcEl) svcEl.value = data.serviceId;
    }
  } catch (e) {}

  // Avto-saqlash
  function saveDraft() {
    const payload = {
      subject: subjEl.value,
      message: msgEl.value,
      serviceId: svcEl ? svcEl.value : ''
    };
    localStorage.setItem('student_appeal_draft', JSON.stringify(payload));
  }

  subjEl.addEventListener('input', saveDraft);
  msgEl.addEventListener('input', saveDraft);
  if (svcEl) svcEl.addEventListener('change', saveDraft);
}

