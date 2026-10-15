<template>
  <div id="app">
    <Header />

    <main class="main-content">
      <router-view />
    </main>

    <Footer />
  </div>
</template>

<script setup>
import Header from "./components/AppHeader.vue";
import Footer from "./components/AppFooter.vue";
</script>

<style>
/* Общие стили для прижатия футера к низу, если страница короткая */
#app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
.main-content {
  flex: 1; /* Растягивает контент на свободное место */
}
</style>
