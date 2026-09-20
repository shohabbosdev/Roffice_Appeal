function switchStudentTab(tabId, updateHash = true) {
  document.querySelectorAll('.nav-item').forEach(b => {
    b.className = 'nav-item w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800/60 transition cursor-pointer';
    const svg = b.querySelector('svg');
    if (svg) svg.className = 'w-4 h-4 text-slate-400';
  });

  const activeBtn = document.querySelector(`.nav-item[data-tab="${tabId}"]`);
  if (activeBtn) {
    activeBtn.className = 'nav-item w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-medium text-white bg-blue-600 shadow-sm transition cursor-pointer';
    const svg = activeBtn.querySelector('svg');
    if (svg) svg.className = 'w-4 h-4 text-white';
  }

  document.querySelectorAll('.tab-pane').forEach(p => p.classList.add('hidden'));
  const activePane = document.getElementById('tab-' + tabId);
  if (activePane) activePane.classList.remove('hidden');

  const titles = {
    'appeals': "Mening murojaatlarim",
    'announcements': "E'lonlar markazi",
    'create': "Yangi murojaat yo'llash",
    'queue': "Kelib hal etish (navbat)",
    'profile': "Talaba profili"
  };
  const heading = document.getElementById('page-heading');
  if (heading && titles[tabId]) heading.innerText = titles[tabId];

  if (updateHash) {
    window.location.hash = '#' + tabId;
    localStorage.setItem('roffice_student_tab', tabId);
  }

  closeSidebar();

  if (tabId === 'appeals') loadStudentAppeals();
  if (tabId === 'announcements') loadStudentAnnouncements();
  if (tabId === 'create') {
    checkStudentFormRestriction();
    initAppealDraftAutoSave();
  }
  if (tabId === 'queue') {
    loadServices();
    loadStudentAppointments();
  }
}

window.addEventListener('hashchange', () => {
  const h = window.location.hash.replace('#', '');
  if (h) switchStudentTab(h, false);
});

