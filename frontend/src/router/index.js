import { createRouter, createWebHistory } from "vue-router";

import NotFound from "../views/NotFound.vue";
import RoomView from "../views/RoomView.vue";
import RoomsView from "../views/RoomsView.vue";
import HomeView from "../views/HomeView.vue";
import { ensureSession } from "../state/auth";

const routes = [
  { path: "/", name: "home", component: HomeView },
  {
    path: "/rooms",
    name: "rooms",
    component: RoomsView,
    meta: { requiresAuth: true },
  },
  {
    path: "/room/:inviteCode",
    name: "room",
    component: RoomView,
    props: true,
    meta: { requiresAuth: true },
  },
  { path: "/:pathMatch(.*)*", name: "not-found", component: NotFound },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Приватные страницы: пускаем только при живой сессии.
// Если сессии нет — на главную, запомнив, куда человек шёл.
router.beforeEach(async (to) => {
  if (!to.meta.requiresAuth) return true;
  const user = await ensureSession();
  if (user) return true;
  return { name: "home", query: { redirect: to.fullPath } };
});

export default router;
