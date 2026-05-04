<template>
    <v-row justify="center">
        <v-col cols="12" md="6" lg="5">
            <v-card rounded="xl" elevation="3">
                <v-card-title class="text-h5"> Регистрация </v-card-title>

                <v-card-text>
                    <v-alert
                        v-if="successMessage"
                        type="success"
                        variant="tonal"
                        class="mb-4"
                    >
                        {{ successMessage }}
                    </v-alert>

                    <v-alert
                        v-if="errorMessage"
                        type="error"
                        variant="tonal"
                        class="mb-4"
                    >
                        {{ errorMessage }}
                    </v-alert>

                    <v-form @submit.prevent="register">
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

                        <v-text-field
                            v-model="passwordConfirm"
                            label="Подтверждение пароля"
                            type="password"
                            prepend-inner-icon="mdi-lock-check"
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
                            Зарегистрироваться
                        </v-btn>
                    </v-form>

                    <div class="text-center mt-4">
                        Уже есть аккаунт?
                        <router-link to="/login">Войти</router-link>
                    </div>
                </v-card-text>
            </v-card>
        </v-col>
    </v-row>
</template>

<script setup>
import { ref } from "vue";
import api from "../api/api";

const email = ref("");
const password = ref("");
const passwordConfirm = ref("");
const loading = ref(false);
const successMessage = ref("");
const errorMessage = ref("");

async function register() {
    loading.value = true;
    successMessage.value = "";
    errorMessage.value = "";

    try {
        const response = await api.post("/auth/register/", {
            email: email.value,
            password: password.value,
            password_confirm: passwordConfirm.value,
        });

        successMessage.value =
            response.data.message || "Письмо с ключом отправлено на почту.";

        email.value = "";
        password.value = "";
        passwordConfirm.value = "";
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

    if (typeof data === "string") {
        return data;
    }

    if (data.detail) {
        return data.detail;
    }

    return JSON.stringify(data, null, 2);
}
</script>
