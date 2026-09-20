window.addEventListener('DOMContentLoaded', async () => {
  initNotifications();
  initIdleSessionTimeout();

  const todayStr = getTashkentTodayStr();
  const qDateInput = document.getElementById('queue-date');
  qDateInput.min = todayStr;
  qDateInput.value = todayStr; // Har doim bugungi kun bilan initsializatsiya qilinadi

  await fetchUserProfile();
  await loadEducationPolicy();
  await loadServices();
  loadStudentAppointments();
  checkPendingFeedback();
  loadStudentAnnouncements();

  // Determine initial tab from hash or localStorage
  const hashTab = window.location.hash.replace('#', '');
  const savedTab = localStorage.getItem('roffice_student_tab');
  const initialTab = hashTab || savedTab || 'appeals';

  switchStudentTab(initialTab, false);
});

