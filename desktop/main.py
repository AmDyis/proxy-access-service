import json
import threading
import tkinter as tk
from tkinter import messagebox

import requests
import websocket

API_BASE_URL = "http://localhost:8000"
WS_BASE_URL = "ws://localhost:8000"


class ProxyDesktopApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Proxy Access Desktop")
        self.root.geometry("520x430")
        self.root.resizable(False, False)

        self.ws_app = None
        self.ws_thread = None
        self.current_user_id = None
        self.current_proxy = None
        self.connection_token = None

        self.build_ui()

    def build_ui(self):
        title_label = tk.Label(
            self.root,
            text="Proxy Access Service",
            font=("Arial", 18, "bold"),
        )
        title_label.pack(pady=(20, 8))

        subtitle_label = tk.Label(
            self.root,
            text="Вставьте ключ активации для подключения к прокси",
            font=("Arial", 10),
        )
        subtitle_label.pack(pady=(0, 15))

        self.key_entry = tk.Entry(
            self.root,
            width=55,
            font=("Arial", 11),
            show="",
        )
        self.key_entry.pack(pady=5)

        self.connect_button = tk.Button(
            self.root,
            text="Подключиться",
            width=25,
            command=self.start_connect_thread,
        )
        self.connect_button.pack(pady=(15, 5))

        self.disconnect_button = tk.Button(
            self.root,
            text="Отключиться",
            width=25,
            command=self.start_disconnect_thread,
            state=tk.DISABLED,
        )
        self.disconnect_button.pack(pady=5)

        self.status_label = tk.Label(
            self.root,
            text="Статус: ожидание ключа",
            font=("Arial", 12, "bold"),
            fg="gray",
        )
        self.status_label.pack(pady=(20, 10))

        self.proxy_text = tk.Text(
            self.root,
            height=8,
            width=58,
            font=("Consolas", 10),
            state=tk.DISABLED,
        )
        self.proxy_text.pack(pady=10)

    def start_connect_thread(self):
        thread = threading.Thread(target=self.connect_to_proxy, daemon=True)
        thread.start()

    def connect_to_proxy(self):
        activation_key = self.key_entry.get().strip()

        if not activation_key:
            self.show_error("Введите ключ активации.")
            return

        self.set_status("Ожидание ответа backend...", "orange")
        self.set_buttons(connect_state=tk.DISABLED, disconnect_state=tk.DISABLED)

        try:
            response = requests.post(
                f"{API_BASE_URL}/api/activate-key/",
                json={"activation_key": activation_key},
                timeout=10,
            )
        except requests.RequestException as exc:
            self.set_status("Ошибка соединения с backend", "red")
            self.show_error(f"Не удалось подключиться к backend:\n{exc}")
            self.set_buttons(connect_state=tk.NORMAL, disconnect_state=tk.DISABLED)
            return

        try:
            data = response.json()
        except ValueError:
            self.set_status("Backend вернул некорректный ответ", "red")
            self.show_error(response.text)
            self.set_buttons(connect_state=tk.NORMAL, disconnect_state=tk.DISABLED)
            return

        if response.status_code != 200:
            detail = data.get("detail", "Неизвестная ошибка")
            status_value = data.get("status", "error")

            self.set_status(f"Ошибка: {status_value}", "red")
            self.show_error(detail)
            self.set_buttons(connect_state=tk.NORMAL, disconnect_state=tk.DISABLED)
            return

        self.current_user_id = data.get("user_id")
        self.current_proxy = data.get("proxy")
        self.connection_token = data.get("connection_token")

        if (
            not self.current_user_id
            or not self.current_proxy
            or not self.connection_token
        ):
            self.set_status("Некорректный ответ backend", "red")
            self.show_error("Backend не вернул user_id, proxy или connection_token.")
            self.set_buttons(connect_state=tk.NORMAL, disconnect_state=tk.DISABLED)
            return

        self.show_proxy_info(self.current_proxy)
        self.set_status("HTTP-подключение выполнено. Подключаем WebSocket...", "orange")

        self.start_websocket(self.current_user_id)

    def start_websocket(self, user_id):
        ws_url = f"{WS_BASE_URL}/ws/status/{user_id}/"

        self.ws_app = websocket.WebSocketApp(
            ws_url,
            on_open=self.on_ws_open,
            on_message=self.on_ws_message,
            on_error=self.on_ws_error,
            on_close=self.on_ws_close,
        )

        self.ws_thread = threading.Thread(
            target=self.ws_app.run_forever,
            daemon=True,
        )
        self.ws_thread.start()

    def on_ws_open(self, ws):
        self.root.after(
            0,
            lambda: self.set_status("WebSocket подключён", "green"),
        )
        self.root.after(
            0,
            lambda: self.set_buttons(
                connect_state=tk.DISABLED,
                disconnect_state=tk.NORMAL,
            ),
        )

    def on_ws_message(self, ws, message):
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            self.root.after(
                0,
                lambda: self.set_status(
                    "Получено некорректное WebSocket-сообщение", "red"
                ),
            )
            return

        status_value = data.get("status", "unknown")
        detail = data.get("detail", "")
        proxy = data.get("proxy")

        if status_value == "connected":
            color = "green"
        elif status_value == "disconnected":
            color = "gray"
        elif status_value == "no_free_vms":
            color = "red"
        elif status_value == "error":
            color = "red"
        else:
            color = "orange"

        self.root.after(
            0,
            lambda: self.set_status(f"Статус: {status_value}. {detail}", color),
        )

        if proxy:
            self.root.after(
                0,
                lambda: self.show_proxy_info(proxy),
            )

    def on_ws_error(self, ws, error):
        self.root.after(
            0,
            lambda: self.set_status("Ошибка WebSocket", "red"),
        )
        self.root.after(
            0,
            lambda: self.show_error(f"WebSocket error:\n{error}"),
        )

    def on_ws_close(self, ws, close_status_code, close_msg):
        self.root.after(
            0,
            lambda: self.set_status("WebSocket отключён", "gray"),
        )
        self.root.after(
            0,
            lambda: self.set_buttons(
                connect_state=tk.NORMAL,
                disconnect_state=tk.DISABLED,
            ),
        )

    def disconnect_websocket(self):
        if self.ws_app:
            self.ws_app.close()

        self.ws_app = None
        self.ws_thread = None
        self.set_status("WebSocket отключён локально", "gray")
        self.set_buttons(connect_state=tk.NORMAL, disconnect_state=tk.DISABLED)

    def set_status(self, text, color):
        self.status_label.config(text=text, fg=color)

    def set_buttons(self, connect_state, disconnect_state):
        self.connect_button.config(state=connect_state)
        self.disconnect_button.config(state=disconnect_state)

    def show_proxy_info(self, proxy):
        proxy_info = (
            f"Назначенный прокси:\n\n"
            f"ID: {proxy.get('id')}\n"
            f"Название: {proxy.get('name')}\n"
            f"Хост: {proxy.get('host')}\n"
            f"Порт: {proxy.get('port')}\n"
            f"Протокол: {proxy.get('protocol')}\n"
        )

        self.proxy_text.config(state=tk.NORMAL)
        self.proxy_text.delete("1.0", tk.END)
        self.proxy_text.insert(tk.END, proxy_info)
        self.proxy_text.config(state=tk.DISABLED)

    def show_error(self, message):
        self.root.after(
            0,
            lambda: messagebox.showerror("Ошибка", message),
        )

    def start_disconnect_thread(self):
        thread = threading.Thread(target=self.disconnect_from_proxy, daemon=True)
        thread.start()

    def disconnect_from_proxy(self):
        if not self.connection_token:
            self.show_error("Нет активной connection-сессии.")
            return

        self.set_status("Отключение от прокси...", "orange")
        self.set_buttons(connect_state=tk.DISABLED, disconnect_state=tk.DISABLED)

        try:
            response = requests.post(
                f"{API_BASE_URL}/api/desktop/disconnect/",
                json={"connection_token": self.connection_token},
                timeout=10,
            )
        except requests.RequestException as exc:
            self.set_status("Ошибка соединения с backend", "red")
            self.show_error(f"Не удалось отправить запрос отключения:\n{exc}")
            self.set_buttons(connect_state=tk.NORMAL, disconnect_state=tk.NORMAL)
            return

        try:
            data = response.json()
        except ValueError:
            self.set_status("Backend вернул некорректный ответ", "red")
            self.show_error(response.text)
            self.set_buttons(connect_state=tk.NORMAL, disconnect_state=tk.NORMAL)
            return

        if response.status_code != 200:
            detail = data.get("detail", "Неизвестная ошибка")
            self.set_status("Ошибка отключения", "red")
            self.show_error(detail)
            self.set_buttons(connect_state=tk.NORMAL, disconnect_state=tk.NORMAL)
            return

        self.connection_token = None
        self.current_user_id = None
        self.current_proxy = None

        if self.ws_app:
            self.ws_app.close()

        self.set_status("Отключено", "gray")
        self.clear_proxy_info()
        self.set_buttons(connect_state=tk.NORMAL, disconnect_state=tk.DISABLED)

    def clear_proxy_info(self):
        self.proxy_text.config(state=tk.NORMAL)
        self.proxy_text.delete("1.0", tk.END)
        self.proxy_text.config(state=tk.DISABLED)


def main():
    root = tk.Tk()
    app = ProxyDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
