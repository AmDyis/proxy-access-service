import { createRouter, createWebHistory } from "vue-router";

import LoginView from "../views/LoginView.vue";
import ProfileView from "../views/ProfileView.vue";
import RegisterView from "../views/RegisterView.vue";

const routes = [
  {
    path: "/",
    redirect: "/profile",
  },
  {
    path: "/register",
    component: RegisterView,
  },
  {
    path: "/login",
    component: LoginView,
  },
  {
    path: "/profile",
    component: ProfileView,
    meta: {
      requiresAuth: true,
    },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  const token = localStorage.getItem("auth_token");

  if (to.meta.requiresAuth && !token) {
    return "/login";
  }

  if ((to.path === "/login" || to.path === "/register") && token) {
    return "/profile";
  }
});

export default router;
