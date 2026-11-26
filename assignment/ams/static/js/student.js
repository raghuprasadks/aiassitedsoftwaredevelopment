async function loadStudentDashboard() {
  try {
    const [dashboardBody, resultsBody] = await Promise.all([
      api('/api/dashboard'),
      api('/api/my-results')
    ]);
    const data = dashboardBody.data;
    document.getElementById('total-count').textContent = data.total;
    document.getElementById('pending-count').textContent = data.pending;
    document.getElementById('submitted-count').textContent = data.submitted;
    document.getElementById('results-count').textContent = resultsBody.data.length;
    const body = document.getElementById('student-assignment-list');
    if (!data.assignments.length) {
      body.innerHTML = '<tr><td colspan="4" class="text-center py-4">No assignments found.</td></tr>';
      return;
    }
    body.innerHTML = data.assignments.map(assignment => `
      <tr>
        <td class="fw-semibold">${escapeHtml(assignment.title)}</td>
        <td>${escapeHtml(assignment.subject || '—')}</td>
        <td>${new Date(assignment.due_date).toLocaleString()}</td>
        <td><button class="btn btn-sm btn-outline-primary submit-open" data-id="${assignment.assignment_id}">Submit</button></td>
      </tr>`).join('');
  } catch (error) {
    showToast(error.message, true);
  }
}

document.getElementById('student-assignment-list').addEventListener('click', event => {
  const button = event.target.closest('.submit-open');
  if (!button) return;
  document.getElementById('submission-assignment-id').value = button.dataset.id;
  new bootstrap.Modal(document.getElementById('submitModal')).show();
});

document.getElementById('submission-form').addEventListener('submit', async event => {
  event.preventDefault();
  const assignmentId = document.getElementById('submission-assignment-id').value;
  const form = new FormData();
  const files = document.getElementById('submission-files').files;
  for (const file of files) form.append('files', file);
  form.append('comments', document.getElementById('submission-comments').value);
  try {
    const body = await api(`/api/assignments/${assignmentId}/submissions`, { method: 'POST', body: form });
    bootstrap.Modal.getInstance(document.getElementById('submitModal')).hide();
    showToast(`Submission recorded. Receipt: ${body.data.submission_id}`);
    loadStudentDashboard();
  } catch (error) {
    showToast(error.message, true);
  }
});

loadStudentDashboard();
