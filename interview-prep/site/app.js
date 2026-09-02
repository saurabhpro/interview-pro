(() => {
  const search = document.querySelector('#search');
  const cards = [...document.querySelectorAll('.card')];
  const empty = document.querySelector('#empty');
  const filters = [...document.querySelectorAll('.filter')];
  let activeFilter = 'all';

  function applyFilters() {
    const query = (search?.value || '').trim().toLowerCase();
    let visible = 0;
    cards.forEach((card) => {
      const section = (card.dataset.section || '').trim().toLowerCase();
      const matchesFilter = activeFilter === 'all' || section === activeFilter.toLowerCase();
      const matchesQuery = !query || (card.dataset.search || '').includes(query);
      const show = matchesFilter && matchesQuery;
      card.hidden = !show;
      card.classList.toggle('is-filtered-out', !show);
      card.setAttribute('aria-hidden', String(!show));
      if (show) visible += 1;
    });
    if (empty) empty.hidden = visible !== 0;
  }

  search?.addEventListener('input', applyFilters);
  filters.forEach((filter) => {
    filter.addEventListener('click', () => {
      activeFilter = (filter.dataset.filter || 'all').trim();
      filters.forEach((candidate) => {
        const selected = candidate === filter;
        candidate.classList.toggle('active', selected);
        candidate.setAttribute('aria-pressed', String(selected));
      });
      applyFilters();
    });
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === '/' && document.activeElement !== search) {
      event.preventDefault();
      search?.focus();
    }
  });
})();
