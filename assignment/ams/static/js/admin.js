async function loadAdminDashboard() {
  try {
    const [dashboardBody, reportBody] = await Promise.all([
      api('/api/dashboard'),
      api('/api/reports/submissions')
    ]);
    const data = dashboardBody.data;
    document.getElementById('admin-students').textContent = data.students;
    document.getElementById('admin-professors').textContent = data.professors;
    document.getElementById('admin-subjects').textContent = data.subjects;
    document.getElementById('admin-assignments').textContent = data.assignments;
    const rows = document.getElementById('admin-report');
    rows.innerHTML = reportBody.data.map(item => `
      <tr><td>${escapeHtml(item.title)}</td><td>${item.total_students}</td>
      <td>${item.submitted}</td><td>${item.pending}</td></tr>`).join('') ||
      '<tr><td colspan="4" class="text-center py-4">No report data.</td></tr>';
  } catch (error) {
    showToast(error.message, true);
  }
}
loadAdminDashboard();
