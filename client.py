import socket
import threading
import tkinter as tk
from tkinter import simpledialog, scrolledtext

SERVER_IP = '127.0.0.1'
SERVER_PORT = 50123

class ChatClient:
    def __init__(self, master):
        self.master = master
        master.title("Chat Client (Local Test)")

        self.username = simpledialog.askstring("Username", "Enter your username:", parent=master)
        if not self.username:
            master.destroy()
            return

        self.chat_area = scrolledtext.ScrolledText(master, state='disabled', width=50, height=20)
        self.chat_area.pack(padx=10, pady=10)

        self.typing_label = tk.Label(master, text="", fg="gray")
        self.typing_label.pack(padx=10, pady=(0,10), anchor='w')

        self.msg_entry = tk.Entry(master, width=40)
        self.msg_entry.pack(side=tk.LEFT, padx=(10,0), pady=(0,10))
        self.msg_entry.bind("<Return>", self.send_message)
        self.msg_entry.bind("<KeyPress>", self.notify_typing)
        self.msg_entry.bind("<KeyRelease>", self.notify_stop_typing)

        self.send_button = tk.Button(master, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.LEFT, padx=10, pady=(0,10))

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((SERVER_IP, SERVER_PORT))
            self.client_socket.send(self.username.encode())  # Send username first
        except Exception as e:
            self.append_text(f"Error connecting to server: {e}")
            return

        self.typing = False
        self.typing_timer = None

        threading.Thread(target=self.receive_messages, daemon=True).start()

    def append_text(self, text):
        self.chat_area.configure(state='normal')
        self.chat_area.insert(tk.END, text + "\n")
        self.chat_area.configure(state='disabled')
        self.chat_area.see(tk.END)

    def send_message(self, event=None):
        msg = self.msg_entry.get().strip()
        if msg:
            try:
                self.client_socket.send(msg.encode())
                self.append_text(f"You: {msg}")
                self.msg_entry.delete(0, tk.END)
                self.stop_typing()
            except Exception as e:
                self.append_text(f"Error sending message: {e}")

    def notify_typing(self, event=None):
        if not self.typing:
            self.typing = True
            try:
                self.client_socket.send("__typing__".encode())
            except:
                pass
        if self.typing_timer:
            self.master.after_cancel(self.typing_timer)
        self.typing_timer = self.master.after(1500, self.stop_typing)  # stop typing after 1.5 sec no key

    def stop_typing(self):
        if self.typing:
            self.typing = False
            try:
                self.client_socket.send("__stoptyping__".encode())
            except:
                pass
            self.typing_label.config(text="")

    def notify_stop_typing(self, event=None):
        # We'll rely on timer to stop typing; you can optionally send __stoptyping__ here
        pass

    def receive_messages(self):
        typing_users = set()
        while True:
            try:
                msg = self.client_socket.recv(1024).decode()
                if not msg:
                    break
                # Check for typing notifications
                if msg.startswith("__typing__:"):
                    user = msg.split(":",1)[1]
                    typing_users.add(user)
                    self.update_typing_label(typing_users)
                elif msg.startswith("__stoptyping__:"):
                    user = msg.split(":",1)[1]
                    typing_users.discard(user)
                    self.update_typing_label(typing_users)
                else:
                    self.append_text(msg)
            except:
                break
        self.append_text("Disconnected from server")
        self.client_socket.close()

    def update_typing_label(self, users):
        users.discard(self.username)
        if users:
            text = ", ".join(users) + " typing..."
            self.typing_label.config(text=text)
        else:
            self.typing_label.config(text="")

def main():
    root = tk.Tk()
    client = ChatClient(root)
    root.mainloop()

if __name__ == "__main__":
    main()
