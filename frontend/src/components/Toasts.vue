<template>
  <div class="toasts" aria-live="polite">
    <TransitionGroup name="toast">
      <div
        v-for="toast in room.toasts"
        :key="toast.id"
        class="toasts__item"
        :class="`toasts__item--${toast.kind}`"
      >
        {{ toast.text }}
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { room } from "../state/room";
</script>

<style scoped>
.toasts {
  position: fixed;
  top: 76px;
  right: 20px;
  z-index: 1200;
  pointer-events: none; /* уведомления не должны перехватывать клики */
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: min(360px, calc(100vw - 40px));
}

.toasts__item {
  padding: 12px 16px;
  font-size: 13px;
  line-height: 1.4;
  color: var(--text);
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(26, 22, 51, 0.14);
}

.toasts__item--error {
  border-left-color: var(--danger);
  color: var(--danger);
}

.toast-enter-active,
.toast-leave-active {
  transition:
    opacity 0.2s,
    transform 0.2s;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(12px);
}
</style>
