<template>
  <v-app>
    <v-app-bar color="primary" density="comfortable">
      <v-app-bar-title>Proxy Access Service</v-app-bar-title>

      <v-spacer />

      <v-btn
        v-if="!isAuthenticated"
        variant="text"
        to="/login"
      >
        Вход
      </v-btn>

      <v-btn
        v-if="!isAuthenticated"
        variant="text"
        to="/register"
      >
        Регистрация
      </v-btn>

      <v-btn
        v-if="isAuthenticated"
        variant="text"
        to="/profile"
      >
        Кабинет
      </v-btn>

      <v-btn
        v-if="isAuthenticated"
        variant="text"
        @click="logout"
      >
        Выйти
      </v-btn>
    </v-app-bar>

    <v-main class="main-bg">
      <v-container class="py-8">
        <router-view />
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const isAuthenticated = computed(() => {
  return Boolean(localStorage.getItem('auth_token'))
})

function logout() {
  localStorage.removeItem('auth_token')
  router.push('/login')
}
</script>

<style>
.main-bg {
  min-height: 100vh;
  background: #f5f7fb;
}
</style>
