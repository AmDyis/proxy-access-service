<template>
    <v-row justify="center">
        <v-col cols="12" lg="9">
            <v-card rounded="xl" elevation="3">
                <v-card-title class="d-flex align-center">
                    <span class="text-h5">Личный кабинет</span>
                    <v-spacer />
                    <v-chip
                        :color="
                            profile?.connection_status === 'connected'
                                ? 'success'
                                : 'grey'
                        "
                        variant="tonal"
                    >
                        {{ statusText }}
                    </v-chip>
                </v-card-title>

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

                    <v-skeleton-loader v-if="loading" type="article" />

                    <template v-else-if="profile">
                        <v-row>
                            <v-col cols="12" md="6">
                                <v-card variant="tonal" rounded="lg">
                                    <v-card-title>Пользователь</v-card-title>
                                    <v-card-text>
                                        <p>
                                            <strong>ID:</strong>
                                            {{ profile.id }}
                                        </p>
                                        <p>
                                            <strong>Email:</strong>
                                            {{ profile.email }}
                                        </p>
                                        <p>
                                            <strong>Создан:</strong>
                                            {{ formatDate(profile.created_at) }}
                                        </p>
                                    </v-card-text>
                                </v-card>
                            </v-col>

                            <v-col cols="12" md="6">
                                <v-card variant="tonal" rounded="lg">
                                    <v-card-title>Ключ активации</v-card-title>
                                    <v-card-text>
                                        <template v-if="profile.activation_key">
                                            <v-textarea
                                                :model-value="
                                                    profile.activation_key
                                                "
                                                label="Текущий activation key"
                                                variant="outlined"
                                                rows="2"
                                                readonly
                                            />

                                            <p class="text-caption">
                                                Истекает:
                                                {{
                                                    formatDate(
                                                        profile.activation_key_expires,
                                                    )
                                                }}
                                            </p>
                                        </template>

                                        <template v-else>
                                            <v-alert
                                                type="info"
                                                variant="tonal"
                                            >
                                                Активного ключа нет. Он
                                                отсутствует или уже был
                                                использован.
                                            </v-alert>
                                        </template>

                                        <v-btn
                                            color="primary"
                                            class="mt-4"
                                            :loading="refreshingKey"
                                            @click="refreshKey"
                                        >
                                            Обновить ключ
                                        </v-btn>
                                    </v-card-text>
                                </v-card>
                            </v-col>

                            <v-col cols="12">
                                <v-card variant="tonal" rounded="lg">
                                    <v-card-title
                                        >Текущее подключение</v-card-title
                                    >

                                    <v-card-text>
                                        <template v-if="profile.active_proxy">
                                            <v-table>
                                                <tbody>
                                                    <tr>
                                                        <td>
                                                            <strong
                                                                >Название</strong
                                                            >
                                                        </td>
                                                        <td>
                                                            {{
                                                                profile
                                                                    .active_proxy
                                                                    .name
                                                            }}
                                                        </td>
                                                    </tr>
                                                    <tr>
                                                        <td>
                                                            <strong
                                                                >Host</strong
                                                            >
                                                        </td>
                                                        <td>
                                                            {{
                                                                profile
                                                                    .active_proxy
                                                                    .host
                                                            }}
                                                        </td>
                                                    </tr>
                                                    <tr>
                                                        <td>
                                                            <strong
                                                                >Port</strong
                                                            >
                                                        </td>
                                                        <td>
                                                            {{
                                                                profile
                                                                    .active_proxy
                                                                    .port
                                                            }}
                                                        </td>
                                                    </tr>
                                                    <tr>
                                                        <td>
                                                            <strong
                                                                >Protocol</strong
                                                            >
                                                        </td>
                                                        <td>
                                                            {{
                                                                profile
                                                                    .active_proxy
                                                                    .protocol
                                                            }}
                                                        </td>
                                                    </tr>
                                                    <tr>
                                                        <td>
                                                            <strong
                                                                >Last
                                                                used</strong
                                                            >
                                                        </td>
                                                        <td>
                                                            {{
                                                                formatDate(
                                                                    profile
                                                                        .active_proxy
                                                                        .last_used_at,
                                                                )
                                                            }}
                                                        </td>
                                                    </tr>
                                                </tbody>
                                            </v-table>

                                            <v-btn
                                                color="error"
                                                class="mt-4"
                                                :loading="disconnecting"
                                                @click="disconnect"
                                            >
                                                Отключиться
                                            </v-btn>
                                        </template>

                                        <template v-else>
                                            <v-alert
                                                type="info"
                                                variant="tonal"
                                            >
                                                Сейчас у пользователя нет
                                                активного прокси-подключения.
                                            </v-alert>
                                        </template>
                                    </v-card-text>
                                </v-card>
                            </v-col>

                            <v-col cols="12">
                                <v-card variant="outlined" rounded="lg">
                                    <v-card-title>Смена пароля</v-card-title>

                                    <v-card-text>
                                        <v-form
                                            @submit.prevent="changePassword"
                                        >
                                            <v-text-field
                                                v-model="oldPassword"
                                                label="Старый пароль"
                                                type="password"
                                                variant="outlined"
                                            />

                                            <v-text-field
                                                v-model="newPassword"
                                                label="Новый пароль"
                                                type="password"
                                                variant="outlined"
                                            />

                                            <v-text-field
                                                v-model="newPasswordConfirm"
                                                label="Подтверждение нового пароля"
                                                type="password"
                                                variant="outlined"
                                            />

                                            <v-btn
                                                type="submit"
                                                color="secondary"
                                                :loading="changingPassword"
                                            >
                                                Сменить пароль
                                            </v-btn>
                                        </v-form>
                                    </v-card-text>
                                </v-card>
                            </v-col>
                        </v-row>
                    </template>
                </v-card-text>
            </v-card>
        </v-col>
    </v-row>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import api from "../api/api";

const profile = ref(null);
const loading = ref(false);
const refreshingKey = ref(false);
const disconnecting = ref(false);
const changingPassword = ref(false);

const successMessage = ref("");
const errorMessage = ref("");

const oldPassword = ref("");
const newPassword = ref("");
const newPasswordConfirm = ref("");

const statusText = computed(() => {
    if (!profile.value) {
        return "Загрузка";
    }

    if (profile.value.connection_status === "connected") {
        return "Подключён";
    }

    return "Не подключён";
});

onMounted(() => {
    loadProfile();
});

async function loadProfile() {
    loading.value = true;
    successMessage.value = "";
    errorMessage.value = "";

    try {
        const response = await api.get("/profile/");
        profile.value = response.data;
    } catch (error) {
        errorMessage.value = extractError(error);
    } finally {
        loading.value = false;
    }
}

async function refreshKey() {
    refreshingKey.value = true;
    successMessage.value = "";
    errorMessage.value = "";

    try {
        const response = await api.post("/profile/refresh-key/");
        profile.value = response.data.user;
        successMessage.value = response.data.message || "Ключ обновлён.";
    } catch (error) {
        errorMessage.value = extractError(error);
    } finally {
        refreshingKey.value = false;
    }
}

async function disconnect() {
    disconnecting.value = true;
    successMessage.value = "";
    errorMessage.value = "";

    try {
        const response = await api.post("/disconnect/");
        successMessage.value = response.data.detail || "Пользователь отключён.";
        await loadProfile();
    } catch (error) {
        errorMessage.value = extractError(error);
    } finally {
        disconnecting.value = false;
    }
}

async function changePassword() {
    changingPassword.value = true;
    successMessage.value = "";
    errorMessage.value = "";

    try {
        const response = await api.post("/profile/change-password/", {
            old_password: oldPassword.value,
            new_password: newPassword.value,
            new_password_confirm: newPasswordConfirm.value,
        });

        successMessage.value = response.data.message || "Пароль изменён.";

        oldPassword.value = "";
        newPassword.value = "";
        newPasswordConfirm.value = "";
    } catch (error) {
        errorMessage.value = extractError(error);
    } finally {
        changingPassword.value = false;
    }
}

function formatDate(value) {
    if (!value) {
        return "-";
    }

    return new Date(value).toLocaleString("ru-RU");
}

function extractError(error) {
    const data = error.response?.data;

    if (!data) {
        return "Ошибка соединения с backend.";
    }

    if (data.detail) {
        return data.detail;
    }

    return JSON.stringify(data, null, 2);
}
</script>
