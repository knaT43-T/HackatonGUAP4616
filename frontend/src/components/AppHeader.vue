<template>
  <header class="header">
    <div class="header-inner">
      <RouterLink to="/" class="logo">
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
          <circle
            cx="16"
            cy="16"
            r="14"
            stroke="currentColor"
            stroke-width="2.5"
          />
          <path
            d="M10 16 C10 12, 22 12, 22 16 C22 20, 10 20, 10 16"
            stroke="currentColor"
            stroke-width="2.5"
            stroke-linecap="round"
          />
        </svg>
        <span>Слушаем вместе</span>
      </RouterLink>

      <nav v-if="auth.user" class="nav">
        <RouterLink to="/rooms">Комнаты</RouterLink>
        <span class="nav__nickname">@{{ auth.user.nickname }}</span>
        <button class="nav__logout" type="button" @click="handleLogout">
          Выйти
        </button>
      </nav>
    </div>
  </header>
</template>

<script setup>
import { useRouter } from "vue-router";

import { auth, signOut } from "../state/auth";

const router = useRouter();

function handleLogout() {
  signOut();
  router.push({ name: "home" });
}
</script>

<style scoped>
.header {
  background: var(--bg-elevated);
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
  gap: 16px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-weight: 700;
  font-size: 1.25rem;
  color: var(--accent);
  text-decoration: none;
}

.nav {
  display: flex;
  align-items: center;
  gap: 16px;
}

.nav a {
  text-decoration: none;
  color: var(--text-muted);
  font-weight: 500;
  transition: color 0.2s;
}

.nav a:hover,
.nav a.router-link-active {
  color: var(--accent);
}

.nav__nickname {
  color: var(--text);
  font-weight: 600;
}

.nav__logout {
  padding: 7px 14px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  transition:
    color 0.15s,
    border-color 0.15s;
}

.nav__logout:hover {
  color: var(--danger);
  border-color: var(--danger);
}
</style>
