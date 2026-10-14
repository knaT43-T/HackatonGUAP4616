import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./styles/index.css";

createApp(App).use(router).mount("#app");
console.log("VITE_API_URL:", import.meta.env.VITE_API_URL);
console.log("Все переменные:", import.meta.env);
