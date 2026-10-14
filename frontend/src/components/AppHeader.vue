<template>
  <header class="header">
    <div class="header-inner">
      <div class="logo">
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
          <circle
            cx="16"
            cy="16"
            r="14"
            stroke="var(--primary)"
            stroke-width="2.5"
          />
          <path
            d="M10 16 C10 12, 22 12, 22 16 C22 20, 10 20, 10 16"
            stroke="var(--primary)"
            stroke-width="2.5"
            stroke-linecap="round"
          />
        </svg>
        <span>Слушаем вместе</span>
      </div>
      <nav class="nav">
        <router-link to="/">Главная</router-link>
      </nav>
    </div>
  </header>
</template>

<style scoped>
.header {
  background: var(--white);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-inner {
  max-width: 960px;
  margin: 0 auto;
  padding: 1rem 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-weight: 700;
  font-size: 1.25rem;
  color: var(--primary);
}

.nav a {
  text-decoration: none;
  color: var(--text-muted);
  font-weight: 500;
  transition: color 0.2s;
}

.nav a:hover,
.nav a.router-link-active {
  color: var(--primary);
}
</style>
