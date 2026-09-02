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
      const matchesFilter = activeFilter === 'all' || card.dataset.section === activeFilter;
      const matchesQuery = !query || (card.dataset.search || '').includes(query);
      const show = matchesFilter && matchesQuery;
      card.hidden = !show;
      if (show) visible += 1;
    });
    if (empty) empty.hidden = visible !== 0;
  }

  search?.addEventListener('input', applyFilters);
  filters.forEach((filter) => {
    filter.addEventListener('click', () => {
      activeFilter = filter.dataset.filter || 'all';
      filters.forEach((candidate) => candidate.classList.toggle('active', candidate === filter));
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
