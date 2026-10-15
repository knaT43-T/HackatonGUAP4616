<template>
  <footer class="footer">
    <p class="footer__text">
      © 2026 Слушаем вместе · Совместное прослушивание музыки
    </p>
    <a :href="docsUrl" target="_blank" rel="noopener" class="footer__link">
      API Docs
    </a>
  </footer>
</template>

<script setup>
import { API_URL } from "../config";

const docsUrl = `${API_URL}/docs`;
</script>

<style scoped>
.footer {
  background: var(--bg-elevated);
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

.footer__text {
  margin: 0;
}

.footer__link {
  color: var(--accent);
  text-decoration: none;
  font-weight: 500;
}

.footer__link:hover {
  text-decoration: underline;
}
</style>
