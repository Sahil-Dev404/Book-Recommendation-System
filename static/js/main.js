/* main.js — BookLens Frontend Logic */

const bookInput      = document.getElementById('bookInput');
const autocompleteEl = document.getElementById('autocompleteList');
const loader         = document.getElementById('loader');
const errorBanner    = document.getElementById('errorBanner');
const querySection   = document.getElementById('querySection');
const queryCard      = document.getElementById('queryCard');
const resultsSection = document.getElementById('resultsSection');
const resultsGrid    = document.getElementById('resultsGrid');
const searchBtn      = document.getElementById('searchBtn');

let autocompleteTimer = null;

// ── Autocomplete ────────────────────────────────────────────────────────
bookInput.addEventListener('input', () => {
  const q = bookInput.value.trim();
  clearTimeout(autocompleteTimer);
  if (q.length < 2) { hideAutocomplete(); return; }

  autocompleteTimer = setTimeout(async () => {
    try {
      const res  = await fetch(`/autocomplete?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      renderAutocomplete(data);
    } catch { hideAutocomplete(); }
  }, 250);
});

function renderAutocomplete(items) {
  if (!items || items.length === 0) { hideAutocomplete(); return; }
  autocompleteEl.innerHTML = items
    .map(title => `<div class="autocomplete-item" onclick="selectTitle('${escapeHtml(title)}')">${escapeHtml(title)}</div>`)
    .join('');
  autocompleteEl.classList.remove('hidden');
}

function selectTitle(title) {
  bookInput.value = title;
  hideAutocomplete();
  getRecommendations();
}

function hideAutocomplete() {
  autocompleteEl.classList.add('hidden');
  autocompleteEl.innerHTML = '';
}

// close autocomplete on outside click
document.addEventListener('click', e => {
  if (!bookInput.contains(e.target) && !autocompleteEl.contains(e.target)) {
    hideAutocomplete();
  }
});

// ── Enter key support ────────────────────────────────────────────────────
bookInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') { hideAutocomplete(); getRecommendations(); }
});

// ── Main recommendation fetch ────────────────────────────────────────────
async function getRecommendations() {
  const title = bookInput.value.trim();
  const topN  = parseInt(document.getElementById('topN').value);

  if (!title) { showError('Please enter a book title.'); return; }

  setLoading(true);
  clearResults();

  try {
    const res  = await fetch('/recommend', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ title, top_n: topN })
    });
    const data = await res.json();

    if (data.error) {
      let msg = data.error;
      if (data.suggestions && data.suggestions.length) {
        msg += `<br><br><strong>Did you mean?</strong> ${data.suggestions.map(s => `<em>${escapeHtml(s)}</em>`).join(', ')}`;
      }
      showError(msg);
    } else {
      renderQueryBook(data.query_book);
      renderRecommendations(data.recommendations);
    }
  } catch (err) {
    showError('Server error. Please try again.');
    console.error(err);
  } finally {
    setLoading(false);
  }
}

// ── Render query book ────────────────────────────────────────────────────
function renderQueryBook(book) {
  const genres = formatGenres(book.genres, 4);
  queryCard.innerHTML = `
    <div class="book-title">${escapeHtml(book.title)}</div>
    <div class="book-author">✍️ ${escapeHtml(book.authors)}</div>
    <div class="book-meta">
      ${book.rating ? `<span class="meta-chip rating">⭐ ${book.rating}</span>` : ''}
      ${book.rating_count ? `<span class="meta-chip">${formatNum(book.rating_count)} ratings</span>` : ''}
      ${book.pages ? `<span class="meta-chip">📄 ${book.pages} pages</span>` : ''}
      ${book.series ? `<span class="meta-chip">📚 ${escapeHtml(book.series)}</span>` : ''}
      ${book.award_count ? `<span class="meta-chip award">🏆 ${book.award_count} awards</span>` : ''}
    </div>
    ${genres ? `<div class="book-genres">🏷️ ${genres}</div>` : ''}
  `;
  querySection.classList.remove('hidden');
}

// ── Render recommendation cards ──────────────────────────────────────────
function renderRecommendations(books) {
  if (!books || books.length === 0) {
    resultsGrid.innerHTML = '<p style="color:var(--text-muted)">No recommendations found.</p>';
    resultsSection.classList.remove('hidden');
    return;
  }

  resultsGrid.innerHTML = books.map((book, i) => {
    const genres = formatGenres(book.genres, 3);
    const simPct = (book.similarity_score * 100).toFixed(1);
    return `
      <div class="book-card">
        <div class="book-card-title">${i + 1}. ${escapeHtml(book.title)}</div>
        <div class="book-card-author">✍️ ${escapeHtml(book.authors)}</div>
        <div class="book-meta">
          ${book.rating    ? `<span class="meta-chip rating">⭐ ${book.rating}</span>` : ''}
          <span class="meta-chip sim">🔗 ${simPct}% match</span>
          ${book.pages     ? `<span class="meta-chip">📄 ${book.pages}p</span>` : ''}
          ${book.publish_year ? `<span class="meta-chip">${book.publish_year}</span>` : ''}
          ${book.award_count  ? `<span class="meta-chip award">🏆 ${book.award_count}</span>` : ''}
        </div>
        ${genres ? `<div class="book-genres">🏷️ ${genres}</div>` : ''}
        ${book.description ? `<div class="book-desc">${escapeHtml(book.description)}</div>` : ''}
      </div>
    `;
  }).join('');

  resultsSection.classList.remove('hidden');
}

// ── Helpers ─────────────────────────────────────────────────────────────
function setLoading(on) {
  loader.classList.toggle('hidden', !on);
  searchBtn.disabled = on;
}

function showError(msg) {
  errorBanner.innerHTML = msg;
  errorBanner.classList.remove('hidden');
}

function clearResults() {
  errorBanner.classList.add('hidden');
  querySection.classList.add('hidden');
  resultsSection.classList.add('hidden');
  resultsGrid.innerHTML = '';
  queryCard.innerHTML   = '';
}

function formatGenres(genres, max = 4) {
  if (!genres) return '';
  return genres.split(',').slice(0, max).map(g => g.trim()).filter(Boolean).join(' · ');
}

function formatNum(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000)    return (n / 1000).toFixed(1) + 'K';
  return n;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
