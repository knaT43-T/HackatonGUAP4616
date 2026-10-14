import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";
import NotFound from "../views/NotFound.vue";

const routes = [
  { path: "/", name: "home", component: HomeView },
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    component: NotFound,
  },
];

export default createRouter({
  history: createWebHistory(),
  routes,
});
