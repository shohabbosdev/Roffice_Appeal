async function initNotifications() {
  const ind = document.getElementById('notif-status-indicator');
  const lbl = document.getElementById('notif-status-label');
  if (!("Notification" in window)) {
    if (ind) ind.className = 'w-2 h-2 rounded-full bg-slate-500';
    if (lbl) lbl.innerText = "Qo'llab-quvvatlanmaydi";
    return;
  }

  if (Notification.permission === 'granted') {
    if (ind) ind.className = 'w-2 h-2 rounded-full bg-emerald-400';
    if (lbl) lbl.innerText = "Faol";
  } else if (Notification.permission === 'denied') {
    if (ind) ind.className = 'w-2 h-2 rounded-full bg-rose-400';
    if (lbl) lbl.innerText = "Cheklangan";
  } else {
    if (ind) ind.className = 'w-2 h-2 rounded-full bg-amber-400 animate-pulse';
    if (lbl) lbl.innerText = "Yoqish";
  }
}

async function toggleBrowserNotifications() {
  if (!("Notification" in window)) {
    showToast("Sizning brauzeringiz bildirishnomalarni qo'llab-quvvatlamaydi.", "warning");
    return;
  }

  const permission = await Notification.requestPermission();
  initNotifications();

  if (permission === 'granted') {
    showToast("Bildirishnomalar muvaffaqiyatli yoqildi!", "success");
    new Notification("Registrator ofisi axborot tizimi", {
      body: "Bildirishnomalar muvaffaqiyatli yoqildi. Murojaatingiz ko'rib chiqilganda sizga xabar beriladi.",
      icon: apiUrl('/static/img/logo.png')
    });
  }
}

