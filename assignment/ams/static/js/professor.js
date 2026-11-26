async function loadProfessorAssignments() {
  try {
    const body = await api('/api/assignments');
    const rows = document.getElementById('professor-assignment-list');
    rows.innerHTML = body.data.map(assignment => `
      <tr>
        <td class="fw-semibold">${escapeHtml(assignment.title)}</td>
        <td>${escapeHtml(assignment.subject || '—')}</td>
        <td><span class="badge text-bg-secondary">${escapeHtml(assignment.status)}</span></td>
        <td>${new Date(assignment.due_date).toLocaleString()}</td>
        <td>${assignment.status === 'DRAFT'
          ? `<button class="btn btn-sm btn-outline-primary assignment-action" data-id="${assignment.assignment_id}" data-action="publish">Publish</button>`
          : assignment.status === 'PUBLISHED'
            ? `<button class="btn btn-sm btn-outline-secondary assignment-action" data-id="${assignment.assignment_id}" data-action="close">Close</button>`
            : ''}</td>
      </tr>`).join('') || '<tr><td colspan="5" class="text-center py-4">No assignments found.</td></tr>';
  } catch (error) {
    showToast(error.message, true);
  }
}

document.getElementById('assignment-form').addEventListener('submit', async event => {
  event.preventDefault();
  const due = document.getElementById('due-date').value;
  try {
    await api('/api/assignments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        course_offering_id: Number(document.getElementById('offering').value),
        title: document.getElementById('assignment-title').value,
        description: document.getElementById('assignment-description').value,
        instructions: document.getElementById('assignment-instructions').value,
        max_marks: Number(document.getElementById('max-marks').value),
        due_date: due ? new Date(due).toISOString() : '',
        allow_late: document.getElementById('allow-late').checked,
        allow_resubmission: document.getElementById('allow-resubmit').checked
      })
    });
    bootstrap.Modal.getInstance(document.getElementById('assignmentModal')).hide();
    event.target.reset();
    showToast('Assignment saved as draft');
    loadProfessorAssignments();
  } catch (error) {
    showToast(error.message, true);
  }
});

document.getElementById('professor-assignment-list').addEventListener('click', async event => {
  const button = event.target.closest('.assignment-action');
  if (!button) return;
  try {
    await api(`/api/assignments/${button.dataset.id}/${button.dataset.action}`, { method: 'PATCH' });
    showToast(`Assignment ${button.dataset.action}ed`);
    loadProfessorAssignments();
  } catch (error) {
    showToast(error.message, true);
  }
});

loadProfessorAssignments();
