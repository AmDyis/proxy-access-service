<template>
    <v-row justify="center">
        <v-col cols="12" md="6" lg="5">
            <v-card rounded="xl" elevation="3">
                <v-card-title class="text-h5"> Вход </v-card-title>

                <v-card-text>
                    <v-alert
                        v-if="errorMessage"
                        type="error"
                        variant="tonal"
                        class="mb-4"
                    >
                        {{ errorMessage }}
                    </v-alert>

                    <v-form @submit.prevent="login">
                        <v-text-field
                            v-model="email"
                            label="Email"
                            type="email"
                            prepend-inner-icon="mdi-email"
                            variant="outlined"
                            required
                        />

                        <v-text-field
                            v-model="password"
                            label="Пароль"
                            type="password"
                            prepend-inner-icon="mdi-lock"
                            variant="outlined"
                            required
                        />

                        <v-btn
                            type="submit"
                            color="primary"
                            block
                            size="large"
                            :loading="loading"
                        >
                            Войти
                        </v-btn>
                    </v-form>

                    <div class="text-center mt-4">
                        Нет аккаунта?
                        <router-link to="/register"
                            >Зарегистрироваться</router-link
                        >
                    </div>
                </v-card-text>
            </v-card>
        </v-col>
    </v-row>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";

import api from "../api/api";

const router = useRouter();

const email = ref("");
const password = ref("");
const loading = ref(false);
const errorMessage = ref("");

async function login() {
    loading.value = true;
    errorMessage.value = "";

    try {
        const response = await api.post("/auth/login/", {
            email: email.value,
            password: password.value,
        });

        localStorage.setItem("auth_token", response.data.token);

        router.push("/profile");
    } catch (error) {
        errorMessage.value = extractError(error);
    } finally {
        loading.value = false;
    }
}

function extractError(error) {
    const data = error.response?.data;

    if (!data) {
        return "Ошибка соединения с backend.";
    }

    if (data.detail) {
        return data.detail;
    }

    if (Array.isArray(data.non_field_errors)) {
        return data.non_field_errors.join(", ");
    }

    return JSON.stringify(data, null, 2);
}
</script>
