async function loadExecutiveAnalytics() {
      const periodSelect = document.getElementById('analytics-period-select');
      const periodVal = periodSelect ? periodSelect.value : 'all';

      const btn = document.getElementById('refresh-analytics-btn');
      const icon = document.getElementById('refresh-analytics-icon');
      if (btn) btn.disabled = true;
      if (icon) icon.classList.add('animate-spin');

      try {
        const resp = await fetch(`/api/v1/appeals/analytics/executive?period_filter=${encodeURIComponent(periodVal)}`, {
          headers: token ? { 'Authorization': 'Bearer ' + token } : {}
        });

        if (!resp.ok) {
          if (resp.status === 403) {
            showToast("Ushbu ma'lumotlar faqat ofis rahbariyati va prorektor uchun ochiq.", "warning");
          } else {
            showToast("Tahliliy ma'lumotlarni yuklab bo'lmadi.", "error");
          }
          return;
        }

        const data = await resp.json();
        executiveAnalyticsData = data;

        // 1. KPI Kartochkalarini to'ldirish
        const s = data.summary || {};
        const total = s.total_appeals || 0;
        const completed = s.completed_appeals || 0;
        const compRate = total > 0 ? Math.round((completed / total) * 100) : 0;

        const elTotal = document.getElementById('exec-total-appeals');
        const elCompRate = document.getElementById('exec-completed-rate');
        const elSla = document.getElementById('exec-sla-percent');
        const elHours = document.getElementById('exec-avg-hours');
        const elRating = document.getElementById('exec-avg-rating');

        if (elTotal) elTotal.innerText = total.toLocaleString();
        if (elCompRate) elCompRate.innerText = `${compRate}% bajarildi (${completed} ta)`;
        if (elSla) elSla.innerText = `${s.sla_compliance_percent || 100}%`;
        if (elHours) elHours.innerText = `${s.avg_resolution_hours || 0}`;
        if (elRating) elRating.innerText = `${Number(s.avg_student_rating || 5.0).toFixed(1)}`;

        // 2. Chart.js diagrammalarini chizish
        renderExecutiveCharts(data);

        // 3. Fakultetlar jadvalini to'ldirish
        renderExecutiveFacultyTable(data.by_faculty || []);

      } catch (err) {
        console.error("Executive analytics error:", err);
        showToast("Server bilan aloqa o'rnatishda xatolik yuz berdi.", "error");
      } finally {
        if (btn) btn.disabled = false;
        if (icon) icon.classList.remove('animate-spin');
      }
    }

    function renderExecutiveCharts(data) {
      if (typeof Chart === 'undefined') {
        console.warn("Chart.js kutubxonasi yuklanmagan");
        return;
      }

      // Chart.js umumiy sozlamalari (Dark tema)
      Chart.defaults.color = '#94a3b8';
      Chart.defaults.font.family = 'system-ui, -apple-system, sans-serif';

      // 1. Fakultetlar diagrammasi (Bar)
      const facultyCanvas = document.getElementById('chart-faculty');
      if (facultyCanvas) {
        if (chartFacultyInstance) chartFacultyInstance.destroy();
        const facLabels = (data.by_faculty || []).map(f => f.faculty.length > 20 ? f.faculty.slice(0, 20) + '...' : f.faculty);
        chartFacultyInstance = new Chart(facultyCanvas, {
          type: 'bar',
          data: {
            labels: facLabels.length ? facLabels : ['Ma\'lumot yo\'q'],
            datasets: [
              {
                label: 'Jami arizalar',
                data: (data.by_faculty || []).map(f => f.total),
                backgroundColor: '#6366f1',
                borderRadius: 6
              },
              {
                label: 'Bajarilgan',
                data: (data.by_faculty || []).map(f => f.completed),
                backgroundColor: '#10b981',
                borderRadius: 6
              },
              {
                label: 'Nizoli',
                data: (data.by_faculty || []).map(f => f.disputed),
                backgroundColor: '#f43f5e',
                borderRadius: 6
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { position: 'bottom', labels: { boxWidth: 12, padding: 15 } }
            },
            scales: {
              x: { grid: { color: 'rgba(51, 65, 85, 0.4)' } },
              y: { beginAtZero: true, grid: { color: 'rgba(51, 65, 85, 0.4)' }, ticks: { stepSize: 1 } }
            }
          }
        });
      }

      // 2. Top-5 xizmatlar diagrammasi (Horizontal Bar)
      const servicesCanvas = document.getElementById('chart-services');
      if (servicesCanvas) {
        if (chartServicesInstance) chartServicesInstance.destroy();
        const sLabels = (data.top_services || []).map(s => s.title.length > 22 ? s.title.slice(0, 22) + '...' : s.title);
        chartServicesInstance = new Chart(servicesCanvas, {
          type: 'bar',
          data: {
            labels: sLabels.length ? sLabels : ['Ma\'lumot yo\'q'],
            datasets: [{
              label: 'Arizalar soni',
              data: (data.top_services || []).map(s => s.count),
              backgroundColor: '#06b6d4',
              borderRadius: 6
            }]
          },
          options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false }
            },
            scales: {
              x: { beginAtZero: true, grid: { color: 'rgba(51, 65, 85, 0.4)' }, ticks: { stepSize: 1 } },
              y: { grid: { display: false } }
            }
          }
        });
      }

      // 3. Holatlar taqsimoti (Doughnut)
      const statusCanvas = document.getElementById('chart-status');
      if (statusCanvas) {
        if (chartStatusInstance) chartStatusInstance.destroy();
        const s = data.summary || {};
        const comp = s.completed_appeals || 0;
        const prog = s.in_progress_appeals || 0;
        const rej = s.rejected_appeals || 0;
        const disp = s.disputed_appeals || 0;

        chartStatusInstance = new Chart(statusCanvas, {
          type: 'doughnut',
          data: {
            labels: ['Bajarilgan', 'Jarayonda', 'Rad etilgan', 'Nizoli / Eskalatsiya'],
            datasets: [{
              data: [comp, prog, rej, disp],
              backgroundColor: ['#10b981', '#3b82f6', '#64748b', '#f43f5e'],
              borderWidth: 2,
              borderColor: '#0f172a'
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
              legend: { position: 'bottom', labels: { boxWidth: 12, padding: 12 } }
            }
          }
        });
      }

      // 4. Oxirgi 14 kunlik trend (Line)
      const trendCanvas = document.getElementById('chart-trend');
      if (trendCanvas) {
        if (chartTrendInstance) chartTrendInstance.destroy();
        const trends = data.trends || [];
        chartTrendInstance = new Chart(trendCanvas, {
          type: 'line',
          data: {
            labels: trends.map(t => t.date.slice(5)),
            datasets: [
              {
                label: 'Kelib tushgan',
                data: trends.map(t => t.total),
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.15)',
                borderWidth: 2.5,
                fill: true,
                tension: 0.35,
                pointRadius: 3
              },
              {
                label: 'Bajarilgan',
                data: trends.map(t => t.completed),
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.15)',
                borderWidth: 2.5,
                fill: true,
                tension: 0.35,
                pointRadius: 3
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { position: 'bottom', labels: { boxWidth: 12, padding: 15 } }
            },
            scales: {
              x: { grid: { color: 'rgba(51, 65, 85, 0.3)' } },
              y: { beginAtZero: true, grid: { color: 'rgba(51, 65, 85, 0.3)' }, ticks: { stepSize: 1 } }
            }
          }
        });
      }
    }

    function renderExecutiveFacultyTable(faculties) {
      const tbody = document.getElementById('exec-faculty-table-body');
      if (!tbody) return;

      if (!faculties || faculties.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="p-8 text-center text-xs text-slate-500">Murojaatlar mavjud emas.</td></tr>';
        return;
      }

      tbody.innerHTML = faculties.map(f => {
        const pct = f.total > 0 ? Math.round((f.completed / f.total) * 100) : 0;
        return `
          <tr class="hover:bg-slate-850/50 transition">
            <td class="p-3 font-medium text-white flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-indigo-500"></span>
              <span>${f.faculty}</span>
            </td>
            <td class="p-3 text-center font-mono font-bold text-white">${f.total}</td>
            <td class="p-3 text-center font-mono font-semibold text-emerald-400">${f.completed}</td>
            <td class="p-3 text-center font-mono font-semibold ${f.disputed > 0 ? 'text-rose-400' : 'text-slate-500'}">${f.disputed}</td>
            <td class="p-3 text-center font-mono font-semibold text-amber-400">${Number(f.avg_rating || 5).toFixed(1)} ★</td>
            <td class="p-3 text-right">
              <div class="flex items-center justify-end gap-2">
                <div class="w-16 bg-slate-950 rounded-full h-1.5 overflow-hidden">
                  <div class="bg-emerald-500 h-1.5 rounded-full" style="width: ${pct}%"></div>
                </div>
                <span class="font-mono text-xs font-bold ${pct >= 80 ? 'text-emerald-400' : pct >= 50 ? 'text-amber-400' : 'text-slate-400'}">${pct}%</span>
              </div>
            </td>
          </tr>
        `;
      }).join('');
    }

    async function exportExecutiveAnalyticsToExcel() {
      if (!executiveAnalyticsData) {
        showToast("Avval hisobot ma'lumotlari yuklanmoqda...", "info");
        await loadExecutiveAnalytics();
      }

      const data = executiveAnalyticsData;
      if (!data) {
        showToast("Eksport qilish uchun ma'lumot topilmadi.", "warning");
        return;
      }

      const periodSelect = document.getElementById('analytics-period-select');
      const periodLabel = periodSelect ? periodSelect.options[periodSelect.selectedIndex].text : 'Barcha davr';
      const nowStr = new Date().toLocaleString('uz-UZ');

      let csv = "\uFEFF"; // UTF-8 BOM Excel kirill va lotin harflarini to'g'ri ko'rsatishi uchun
      csv += `"REGISTRATOR OFISI - RAHBARIYAT TAHLILIY HISOBOTI"\n`;
      csv += `"Hisobot davri:","${periodLabel}"\n`;
      csv += `"Shakllantirilgan sana:","${nowStr}"\n\n`;

      // 1. Asosiy ko'rsatkichlar
      csv += `"1. ASOSIY INTEGRAL KO'RSATKICHLAR"\n`;
      csv += `"Ko'rsatkich","Qiymat"\n`;
      csv += `"Jami murojaatlar soni","${data.summary.total_appeals || 0}"\n`;
      csv += `"Bajarilgan murojaatlar","${data.summary.completed_appeals || 0}"\n`;
      csv += `"Jarayondagi murojaatlar","${data.summary.in_progress_appeals || 0}"\n`;
      csv += `"Rad etilgan murojaatlar","${data.summary.rejected_appeals || 0}"\n`;
      csv += `"Nizoli / Rahbariyatga oshirilgan","${data.summary.disputed_appeals || 0}"\n`;
      csv += `"SLA ijro intizomi (%)","${data.summary.sla_compliance_percent || 100}%"\n`;
      csv += `"O'rtacha ijro vaqti (soat)","${data.summary.avg_resolution_hours || 0}"\n`;
      csv += `"Talabalar mamnuniyat reytingi","${Number(data.summary.avg_student_rating || 5).toFixed(1)} / 5.0"\n`;
      csv += `"Jami shaxsiy qabul navbatlari","${data.summary.total_appointments || 0}"\n\n`;

      // 2. Fakultetlar kesimida
      csv += `"2. FAKULTETLAR KESIMIDA TAHLIL"\n`;
      csv += `"Fakultet","Jami murojaat","Bajarilgan","Nizoli","O'rtacha baho","Bajarilish foizi"\n`;
      (data.by_faculty || []).forEach(f => {
        const pct = f.total > 0 ? Math.round((f.completed / f.total) * 100) : 0;
        const facName = (f.faculty || 'Boshqa / Belgilanmagan').replace(/"/g, '""');
        csv += `"${facName}","${f.total || 0}","${f.completed || 0}","${f.disputed || 0}","${f.avg_rating || 5.0}","${pct}%"\n`;
      });
      csv += `\n`;

      // 3. Top xizmatlar
      csv += `"3. TOP-5 TALABGIR XIZMATLAR"\n`;
      csv += `"Xizmat kodi","Xizmat nomi","Murojaatlar soni","Ulushi (%)"\n`;
      (data.top_services || []).forEach(s => {
        const sTitle = (s.title || 'Xizmat').replace(/"/g, '""');
        csv += `"${s.code || ''}","${sTitle}","${s.count || 0}","${s.percentage || 0}%"\n`;
      });

      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.setAttribute("href", url);
      const safeDate = new Date().toISOString().slice(0, 10);
      link.setAttribute("download", `Registrator_Ofisi_Tahliliy_Hisobot_${safeDate}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      showToast("Tahliliy hisobot Excel (CSV) fayli muvaffaqiyatli yuklab olindi!", "success");
    }

    // 15. Centralized Audit Logs Management System
    let auditLogsData = [];
