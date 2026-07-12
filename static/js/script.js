/* ==========================================================================
   Vitalis — Smart Healthcare Assistant — script.js
   Handles: navbar scroll state + mobile toggle, smooth scroll, scroll-to-top,
   FAQ accordion, dark/light theme toggle, form validation + loading overlay,
   confidence-ring animation on result page, AJAX chatbot requests,
   personalized diet plan generator on result page.
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initNavbar();
  initScrollTop();
  initFaq();
  initTheme();
  initFormValidation();
  initConfidenceRing();
  initChatbot();
  initDietPlanGenerator();
  initDoctorFinder();
});

/* ---------------- Navbar ---------------- */
function initNavbar() {
  const navbar = document.getElementById('navbar');
  const toggle = document.getElementById('navToggle');
  const links = document.getElementById('navLinks');

  if (toggle && links) {
    toggle.addEventListener('click', () => {
      links.classList.toggle('open');
    });
    links.querySelectorAll('a').forEach(a => a.addEventListener('click', () => links.classList.remove('open')));
  }

  window.addEventListener('scroll', () => {
    if (!navbar) return;
    if (window.scrollY > 20) navbar.style.boxShadow = '0 6px 24px rgba(0,0,0,0.25)';
    else navbar.style.boxShadow = 'none';
  });
}

/* ---------------- Scroll to top ---------------- */
function initScrollTop() {
  const btn = document.getElementById('scrollTopBtn');
  if (!btn) return;
  window.addEventListener('scroll', () => {
    if (window.scrollY > 500) btn.classList.add('visible');
    else btn.classList.remove('visible');
  });
  btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
}

/* ---------------- FAQ accordion ---------------- */
function initFaq() {
  document.querySelectorAll('.faq-item').forEach(item => {
    const question = item.querySelector('.faq-question');
    if (!question) return;
    question.addEventListener('click', () => {
      const wasOpen = item.classList.contains('open');
      document.querySelectorAll('.faq-item').forEach(i => i.classList.remove('open'));
      if (!wasOpen) item.classList.add('open');
    });
  });
}

/* ---------------- Theme toggle (persisted) ---------------- */
function initTheme() {
  const root = document.documentElement;
  const saved = localStorage.getItem('vitalis-theme');
  if (saved) root.setAttribute('data-theme', saved);

  document.querySelectorAll('.theme-toggle').forEach(btn => {
    updateToggleIcon(btn, root.getAttribute('data-theme'));
    btn.addEventListener('click', () => {
      const current = root.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
      const next = current === 'light' ? 'dark' : 'light';
      root.setAttribute('data-theme', next);
      localStorage.setItem('vitalis-theme', next);
      updateToggleIcon(btn, next);
    });
  });
}
function updateToggleIcon(btn, theme) {
  btn.textContent = theme === 'light' ? '\u263E' : '\u2600';
}

/* ---------------- Form validation + loading overlay ---------------- */
function initFormValidation() {
  const forms = document.querySelectorAll('form[data-validate]');
  forms.forEach(form => {
    form.addEventListener('submit', (e) => {
      let valid = true;
      form.querySelectorAll('input[required], select[required]').forEach(field => {
        const errorEl = field.parentElement.querySelector('.field-error');
        const val = field.value.trim();
        let msg = '';

        if (val === '') {
          msg = 'This field is required.';
        } else if (field.type === 'number') {
          const num = parseFloat(val);
          const min = field.hasAttribute('min') ? parseFloat(field.min) : null;
          const max = field.hasAttribute('max') ? parseFloat(field.max) : null;
          if (isNaN(num)) msg = 'Enter a valid number.';
          else if (min !== null && num < min) msg = `Minimum value is ${min}.`;
          else if (max !== null && num > max) msg = `Maximum value is ${max}.`;
        }

        if (msg) {
          valid = false;
          field.classList.add('invalid');
          if (errorEl) errorEl.textContent = msg;
        } else {
          field.classList.remove('invalid');
          if (errorEl) errorEl.textContent = '';
        }
      });

      if (!valid) {
        e.preventDefault();
        const firstInvalid = form.querySelector('.invalid');
        if (firstInvalid) firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }

      const overlay = document.getElementById('loadingOverlay');
      if (overlay) overlay.classList.add('active');
    });

    // live-clear error on input
    form.querySelectorAll('input, select').forEach(field => {
      field.addEventListener('input', () => {
        field.classList.remove('invalid');
        const errorEl = field.parentElement.querySelector('.field-error');
        if (errorEl) errorEl.textContent = '';
      });
    });
  });
}

/* ---------------- Confidence ring animation (result.html) ---------------- */
function initConfidenceRing() {
  const arc = document.querySelector('.value-arc');
  if (!arc) return;
  const pct = parseFloat(arc.dataset.percent || '0');
  const radius = arc.r.baseVal.value;
  const circumference = 2 * Math.PI * radius;
  arc.style.strokeDasharray = `${circumference}`;
  arc.style.strokeDashoffset = `${circumference}`;
  requestAnimationFrame(() => {
    const offset = circumference - (pct / 100) * circumference;
    arc.style.strokeDashoffset = `${offset}`;
  });
}

/* ---------------- Chatbot AJAX ---------------- */
function initChatbot() {
  const form = document.getElementById('chatForm');
  const input = document.getElementById('chatInput');
  const windowEl = document.getElementById('chatWindow');
  if (!form || !input || !windowEl) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const question = input.value.trim();
    if (!question) return;

    appendMessage(windowEl, question, 'user');
    input.value = '';
    input.focus();

    const typingEl = appendTyping(windowEl);

    try {
      const res = await fetch('/api/chatbot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      });
      const data = await res.json();
      typingEl.remove();
      appendMessage(windowEl, data.answer || 'Sorry, something went wrong.', 'bot');
    } catch (err) {
      typingEl.remove();
      appendMessage(windowEl, 'Network error — please try again in a moment.', 'bot');
    }
  });
}

function appendMessage(windowEl, text, sender) {
  const div = document.createElement('div');
  div.className = `chat-msg ${sender}`;
  div.textContent = text;
  windowEl.appendChild(div);
  windowEl.scrollTop = windowEl.scrollHeight;
  return div;
}

function appendTyping(windowEl) {
  const div = document.createElement('div');
  div.className = 'chat-msg bot typing';
  div.innerHTML = '<span></span><span></span><span></span>';
  windowEl.appendChild(div);
  windowEl.scrollTop = windowEl.scrollHeight;
  return div;
}

/* Allow server-rendered pages to trigger a chat message programmatically,
   e.g. the "Ask AI Assistant" button on result.html */
function sendPrompt(text) {
  const input = document.getElementById('chatInput');
  const form = document.getElementById('chatForm');
  if (input && form) {
    input.value = text;
    form.dispatchEvent(new Event('submit'));
  }
}
/* ---------------- Doctor / health center finder (result.html) ---------------- */
function initDoctorFinder() {
  const btn = document.getElementById('findDoctorsBtn');
  const input = document.getElementById('doctorLocationInput');
  const loading = document.getElementById('doctorFinderLoading');
  const output = document.getElementById('doctorFinderOutput');
  if (!btn || !input || !output) return;

  const runSearch = async () => {
    const location = input.value.trim();
    if (!location) {
      output.innerHTML = `<div class="form-error-banner">Please enter a location.</div>`;
      return;
    }

    btn.disabled = true;
    output.innerHTML = '';
    loading.style.display = 'flex';

    try {
      const res = await fetch('/api/find-doctors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ location })
      });
      const data = await res.json();

      if (data.error) {
        output.innerHTML = `<div class="form-error-banner">${data.error}</div>`;
      } else {
        renderDoctorResults(data, output);
      }
    } catch (err) {
      output.innerHTML = `<div class="form-error-banner">Something went wrong searching that location. Please try again.</div>`;
    } finally {
      loading.style.display = 'none';
      btn.disabled = false;
    }
  };

  btn.addEventListener('click', runSearch);
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') runSearch(); });
}

function renderDoctorResults(data, container) {
  const results = data.results || [];

  if (results.length === 0) {
    container.innerHTML = `<div class="form-error-banner">No results found for "${data.specialty}" near that location. Try a nearby city or a broader area.</div>`;
    return;
  }

  const cardsHtml = results.map(r => `
    <div class="doctor-card">
      <div class="doctor-card-main">
        <h4>${r.name}</h4>
        <p class="doctor-address">${r.address || ''}</p>
        ${r.phone ? `<p class="doctor-phone">${r.phone}</p>` : ''}
      </div>
      <div class="doctor-card-side">
        ${r.rating ? `<div class="doctor-rating">★ ${r.rating} <span>(${r.review_count || 0})</span></div>` : ''}
        ${r.maps_url ? `<a href="${r.maps_url}" target="_blank" rel="noopener" class="btn btn-outline doctor-map-btn">View on Maps</a>` : ''}
      </div>
    </div>
  `).join('');

  container.innerHTML = `
    <div class="doctor-results-label">Showing ${results.length} result(s) for "${data.specialty}"</div>
    <div class="doctor-results-grid">${cardsHtml}</div>
  `;
}

/* ---------------- Diet plan generator (result.html) ---------------- */
function initDietPlanGenerator() {
  const btn = document.getElementById('generateDietPlanBtn');
  const durationSelect = document.getElementById('dietDuration');
  const loading = document.getElementById('dietPlanLoading');
  const output = document.getElementById('dietPlanOutput');
  if (!btn || !durationSelect || !output) return;

  btn.addEventListener('click', async () => {
    const duration = durationSelect.value;
    btn.disabled = true;
    output.style.display = 'none';
    output.innerHTML = '';
    loading.style.display = 'flex';

    try {
      const res = await fetch('/api/diet-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ duration })
      });
      const plan = await res.json();

      if (plan.error) {
        output.innerHTML = `<div class="form-error-banner">${plan.error}</div>`;
      } else {
        renderDietPlan(plan, output);
      }
    } catch (err) {
      output.innerHTML = `<div class="form-error-banner">Something went wrong generating the plan. Please try again.</div>`;
    } finally {
      loading.style.display = 'none';
      output.style.display = 'block';
      btn.disabled = false;
    }
  });
}

function renderDietPlan(plan, container) {
  const days = plan.days || [];

  const tabsHtml = days.map((d, i) =>
    `<button class="diet-day-tab ${i === 0 ? 'active' : ''}" data-index="${i}">${d.day_label}</button>`
  ).join('');

  const panelsHtml = days.map((d, i) => `
    <div class="diet-day-content ${i === 0 ? 'active' : ''}" data-index="${i}">
      <div class="diet-meal-row"><span class="meal-label">Breakfast</span><span>${d.breakfast || ''}</span></div>
      <div class="diet-meal-row"><span class="meal-label">Lunch</span><span>${d.lunch || ''}</span></div>
      <div class="diet-meal-row"><span class="meal-label">Dinner</span><span>${d.dinner || ''}</span></div>
      <div class="diet-meal-row"><span class="meal-label">Snacks</span><span>${d.snacks || ''}</span></div>
    </div>
  `).join('');

  const shoppingTags = (plan.shopping_list_highlights || [])
    .map(item => `<span class="tag eat">${item}</span>`).join('');

  container.innerHTML = `
    <div class="diet-plan-summary">
      <p>${plan.summary || ''}</p>
      <div class="diet-calorie-badge">${plan.daily_calorie_target || ''}</div>
    </div>
    <div class="diet-day-tabs">${tabsHtml}</div>
    <div class="diet-day-panels">${panelsHtml}</div>
    <div class="diet-plan-footer">
      <h4>Shopping list highlights</h4>
      <div class="tag-list">${shoppingTags}</div>
      <p class="diet-plan-notes">${plan.general_notes || ''}</p>
    </div>
  `;

  container.querySelectorAll('.diet-day-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const idx = tab.dataset.index;
      container.querySelectorAll('.diet-day-tab').forEach(t => t.classList.remove('active'));
      container.querySelectorAll('.diet-day-content').forEach(c => c.classList.remove('active'));
      tab.classList.add('active');
      container.querySelector(`.diet-day-content[data-index="${idx}"]`).classList.add('active');
    });
  });
}