document.getElementById('login-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const error = document.getElementById('login-error');
  error.textContent = '';
  try {
    await api('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: document.getElementById('email').value,
        password: document.getElementById('password').value
      })
    });
    window.location.assign('/dashboard');
  } catch (requestError) {
    error.textContent = requestError.message;
  }
});
