<template>
  <footer class="footer">
    <p>© 2026 Слушаем вместе · Совместное прослушивание музыки</p>
    <a href="http://localhost:8000/docs" target="_blank" class="api-link"
      >API Docs</a
    >
  </footer>
</template>

<style scoped>
.footer {
  background: var(--white);
  border-top: 1px solid var(--border);
  padding: 1.5rem;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.875rem;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1.5rem;
}

.api-link {
  color: var(--primary);
  text-decoration: none;
  font-weight: 500;
}

.api-link:hover {
  text-decoration: underline;
}
</style>
