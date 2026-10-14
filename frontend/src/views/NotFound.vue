<template>
  <div class="nf">
    <div class="nf__code">404</div>
    <h1 class="nf__title">Страница не найдена</h1>
    <p class="nf__text">
      Такой страницы нет. Возможно, ссылка устарела или в адресе опечатка.
    </p>
    <div class="nf__actions">
      <RouterLink to="/" class="nf__btn nf__btn--primary">
        На главную
      </RouterLink>
    </div>
  </div>
</template>

<style scoped>
.nf {
  min-height: calc(100vh - 128px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  text-align: center;
}

.nf__code {
  font-size: 96px;
  font-weight: 800;
  line-height: 1;
  background: linear-gradient(135deg, var(--accent), #9c8cff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  margin-bottom: 8px;
}

.nf__title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 12px;
}

.nf__text {
  max-width: 420px;
  color: var(--text-muted);
  font-size: 15px;
  line-height: 1.5;
  margin: 0 0 28px;
}

.nf__actions {
  display: flex;
  gap: 10px;
}

.nf__btn {
  padding: 10px 18px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  transition:
    background 0.15s,
    transform 0.1s;
}

.nf__btn--primary {
  background: var(--accent);
  color: #fff;
}

.nf__btn--primary:hover {
  background: var(--accent-hover);
  transform: translateY(-1px);
}
</style>
