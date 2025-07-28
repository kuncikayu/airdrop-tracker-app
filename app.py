import customtkinter as ctk
from tkinter import ttk, messagebox, Menu, filedialog
import sqlite3
import hashlib
from datetime import datetime
from functools import partial
import webbrowser
import os
import shutil
import sys
import requests
import threading
import subprocess

GITHUB_REPO = "kuncikayu/airdrop-tracker-app" 
CURRENT_VERSION = "v1.0.0" 

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Login - Oryx Tracker")
        self.geometry("400x480")
        self.resizable(False, False)

        try:
            self.iconbitmap(resource_path("logo.ico"))
        except Exception as e:
            print(f"Error loading icon: {e}")

        ctk.set_appearance_mode("Light")
        
        self.db_conn = sqlite3.connect('oryx_tracker_main.db')
        self.create_user_table()
        self.ensure_default_user()

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(pady=40, padx=60, fill="both", expand=True)

        ctk.CTkLabel(main_frame, text="Oryx Tracker", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=12)
        ctk.CTkLabel(main_frame, text=f"Version {CURRENT_VERSION}", font=ctk.CTkFont(size=12), text_color="gray").pack()
        
        self.username_entry = ctk.CTkEntry(main_frame, placeholder_text="Username", width=220, height=40)
        self.username_entry.pack(pady=(40, 10))
        self.password_entry = ctk.CTkEntry(main_frame, placeholder_text="Password", show="*", width=220, height=40)
        self.password_entry.pack(pady=10)
        self.password_entry.bind("<Return>", self.login_event)
        self.error_label = ctk.CTkLabel(main_frame, text="", text_color="red")
        self.error_label.pack()
        login_button = ctk.CTkButton(main_frame, text="Login", command=self.login_event, width=220, height=40)
        login_button.pack(pady=20)
        
        update_thread = threading.Thread(target=self.check_for_updates, daemon=True)
        update_thread.start()

    def create_user_table(self):
        cursor = self.db_conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
        """)
        self.db_conn.commit()

    def ensure_default_user(self):
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            default_username = "admin"
            default_password = "admin"
            hashed_password = hashlib.sha256(default_password.encode()).hexdigest()
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (default_username, hashed_password))
            self.db_conn.commit()
            messagebox.showinfo("Welcome!", "Default user created:\n\nUsername: admin\nPassword: admin\n\nPlease log in.")

    def login_event(self, event=None):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if not username or not password: self.show_error("Username and password are required."); return
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        if result:
            stored_hash = result[0]
            entered_hash = hashlib.sha256(password.encode()).hexdigest()
            if stored_hash == entered_hash: self.launch_main_app(username)
            else: self.show_error("Invalid username or password.")
        else: self.show_error("Invalid username or password.")

    def show_error(self, message):
        self.error_label.configure(text=message)

    def launch_main_app(self, username):
        self.destroy()
        app = ctk.CTk()
        CryptoTrackerApp(app, username)
        app.mainloop()

    def check_for_updates(self):
        try:
            response = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest")
            response.raise_for_status()
            latest_version = response.json()["tag_name"]
            if latest_version > CURRENT_VERSION:
                download_url = next((asset["browser_download_url"] for asset in response.json().get("assets", []) if asset["name"].endswith(".exe")), None)
                if download_url: self.show_update_dialog(latest_version, download_url)
        except Exception as e:
            print(f"Failed to check for updates: {e}")

    def show_update_dialog(self, latest_version, download_url):
        if messagebox.askyesno("Update Available", f"A new version ({latest_version}) is available!\n\nDo you want to update now?"):
            self.start_update_process(download_url)
            
    def start_update_process(self, download_url):
        progress_window = ctk.CTkToplevel(self)
        progress_window.title("Updating..."); progress_window.geometry("300x100"); progress_window.transient(self); progress_window.grab_set()
        ctk.CTkLabel(progress_window, text="Downloading new version, please wait...").pack(pady=10)
        progress_bar = ctk.CTkProgressBar(progress_window, width=250); progress_bar.set(0); progress_bar.pack(pady=10)
        
        def do_update():
            try:
                response = requests.get(download_url, stream=True); response.raise_for_status()
                new_exe_path = "OryxTracker_new.exe"
                with open(new_exe_path, "wb") as f:
                    total_length = int(response.headers.get('content-length')); downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk); downloaded += len(chunk); progress = downloaded / total_length; progress_bar.set(progress); progress_window.update_idletasks()
                updater_script_content = f"""
@echo off
echo Waiting for Oryx Tracker to close...
timeout /t 4 /nobreak > NUL
echo Replacing application file...
del "{os.path.basename(sys.executable)}"
rename "{os.path.basename(new_exe_path)}" "{os.path.basename(sys.executable)}"
echo Update complete! Starting new version...
start "" "{os.path.basename(sys.executable)}"
del "%~f0"
"""
                with open("updater.bat", "w") as f: f.write(updater_script_content)
                subprocess.Popen("updater.bat", shell=True)
                self.quit()
            except Exception as e: messagebox.showerror("Update Failed", f"An error occurred during the update:\n{e}"); progress_window.destroy()
        threading.Thread(target=do_update, daemon=True).start()

class CryptoTrackerApp:
    def __init__(self, root, username):
        self.root = root
        self.root.title(f"Oryx Tracker - {CURRENT_VERSION}")
        self.root.geometry("1600x850")
        
        try:
            self.root.iconbitmap(resource_path("logo.ico"))
        except Exception as e:
            print(f"Error loading icon: {e}")

        self.logged_in_user = username
        self.db_conn = sqlite3.connect('oryx_tracker_main.db'); self.db_conn.execute("PRAGMA foreign_keys = ON")
        
        self.create_config_tables(); self.create_account_task_tables(); self.migrate_database(); self.ensure_default_configs(); self.ensure_default_accounts()

        self.current_account_id = None; self.account_widgets = {}; self.treeviews = {}; self.active_edit_entry = None
        self.status_context_menu = Menu(self.root, tearoff=0, relief="flat", bd=1)
        self.category_context_menu = Menu(self.root, tearoff=0, relief="flat", bd=1)
        self.cell_edit_menu = Menu(self.root, tearoff=0, relief="flat", bd=1)
        
        self.sort_column = "date_added"; self.sort_reverse = True
        self.search_var = ctk.StringVar(); self.search_var.trace_add("write", lambda *args: self.populate_task_list())
        
        self.root.grid_columnconfigure(1, weight=1); self.root.grid_rowconfigure(0, weight=1)
        self.sidebar_frame = ctk.CTkFrame(self.root, width=280, corner_radius=0); self.sidebar_frame.grid(row=0, column=0, sticky="nsw"); self.sidebar_frame.grid_rowconfigure(10, weight=1)
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=0); self.main_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=20); self.main_frame.grid_columnconfigure(0, weight=1); self.main_frame.grid_rowconfigure(2, weight=1)
        
        self.create_main_content()
        self.select_initial_account()
        self.redraw_sidebar()
        self.toggle_dark_mode(ctk.get_appearance_mode() == "Dark")
        
        self.update_main_title_and_tasks()

    def create_config_tables(self):
        cursor = self.db_conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS networks (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)")
        cursor.execute("CREATE TABLE IF NOT EXISTS wallets (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, address TEXT NOT NULL UNIQUE)")
        cursor.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)")
        self.db_conn.commit()
        
    def create_account_task_tables(self):
        cursor = self.db_conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, sort_order INTEGER)")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            project_name TEXT NOT NULL,
            website TEXT,
            description TEXT,
            category TEXT,
            ticker TEXT,
            network TEXT,
            wallet TEXT,
            status TEXT NOT NULL,
            reward REAL,
            date_added TEXT,
            account_id INTEGER,
            FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE
        )
        """)
        self.db_conn.commit()

    def migrate_database(self):
        cursor = self.db_conn.cursor()
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'date_added' not in columns: cursor.execute("ALTER TABLE tasks ADD COLUMN date_added TEXT")
        if 'website' not in columns: cursor.execute("ALTER TABLE tasks ADD COLUMN website TEXT")
        if 'category' not in columns: cursor.execute("ALTER TABLE tasks ADD COLUMN category TEXT")
        if 'description' not in columns: cursor.execute("ALTER TABLE tasks ADD COLUMN description TEXT")
        self.db_conn.commit()

    def ensure_default_configs(self):
        cursor = self.db_conn.cursor()
        if cursor.execute("SELECT COUNT(*) FROM networks").fetchone()[0] == 0: cursor.executemany("INSERT INTO networks (name) VALUES (?)", [('TON',), ('Ethereum',), ('Solana',), ('BSC',)])
        if cursor.execute("SELECT COUNT(*) FROM wallets").fetchone()[0] == 0: cursor.executemany("INSERT INTO wallets (name, address) VALUES (?, ?)", [('Main Wallet', 'UQdz...NC1p'), ('Test Wallet', '0x...1234')])
        if cursor.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0: cursor.executemany("INSERT INTO categories (name) VALUES (?)", [('Testnet',), ('Retro',), ('Node',)])
        self.db_conn.commit()
        
    def ensure_default_accounts(self):
        c = self.db_conn.cursor()
        if c.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0: c.executemany("INSERT INTO accounts (name, sort_order) VALUES (?, ?)", [('Account 1',0), ('Account 2',1), ('Account 3',2)]); self.db_conn.commit()

    def create_main_content(self):
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent"); header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(10,0)); header_frame.grid_columnconfigure(1, weight=1)
        self.title_label = ctk.CTkLabel(header_frame, text="", font=ctk.CTkFont(size=24, weight="bold")); self.title_label.grid(row=0, column=0, sticky="w")
        
        search_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        search_frame.grid(row=0, column=2, sticky="e")
        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=(0, 5))
        self.search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var, width=250); self.search_entry.pack(side="left")

        input_frame = ctk.CTkFrame(self.main_frame, border_width=1); input_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=20)
        
        ctk.CTkLabel(input_frame, text="Project Name").grid(row=0, column=0, padx=10, pady=(5,0), sticky="w")
        self.project_name_entry = ctk.CTkEntry(input_frame, placeholder_text="e.g., Oryx Coin", width=200); self.project_name_entry.grid(row=1, column=0, padx=10, pady=10)
        
        ctk.CTkLabel(input_frame, text="Website").grid(row=0, column=1, padx=10, pady=(5,0), sticky="w")
        self.website_entry = ctk.CTkEntry(input_frame, placeholder_text="https://example.com", width=200); self.website_entry.grid(row=1, column=1, padx=10, pady=10)
        
        ctk.CTkLabel(input_frame, text="Description").grid(row=0, column=2, padx=10, pady=(5,0), sticky="w")
        self.description_entry = ctk.CTkEntry(input_frame, placeholder_text="Airdrop details, tasks, etc.", width=350); self.description_entry.grid(row=1, column=2, columnspan=2, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(input_frame, text="Category").grid(row=2, column=0, padx=10, pady=(5,0), sticky="w")
        self.category_combo = ctk.CTkComboBox(input_frame, values=[]); self.category_combo.grid(row=3, column=0, padx=10, pady=10)
        
        ctk.CTkLabel(input_frame, text="Network").grid(row=2, column=1, padx=10, pady=(5,0), sticky="w")
        self.network_combo = ctk.CTkComboBox(input_frame, values=[]); self.network_combo.grid(row=3, column=1, padx=10, pady=10)
        
        ctk.CTkLabel(input_frame, text="Wallet").grid(row=2, column=2, padx=10, pady=(5,0), sticky="w")
        self.wallet_combo = ctk.CTkComboBox(input_frame, values=[], width=200); self.wallet_combo.grid(row=3, column=2, padx=10, pady=10)

        ctk.CTkLabel(input_frame, text="Reward").grid(row=2, column=3, padx=10, pady=(5,0), sticky="w")
        self.reward_entry = ctk.CTkEntry(input_frame, placeholder_text="1000.00"); self.reward_entry.grid(row=3, column=3, padx=10, pady=10)
        
        ctk.CTkLabel(input_frame, text="Ticker").grid(row=2, column=4, padx=10, pady=(5,0), sticky="w")
        self.ticker_entry = ctk.CTkEntry(input_frame, placeholder_text="$ORYX"); self.ticker_entry.grid(row=3, column=4, padx=10, pady=10)
        
        add_button = ctk.CTkButton(input_frame, text="Add Task", command=self.add_task); add_button.grid(row=3, column=5, padx=10, pady=10, sticky="e")
        input_frame.grid_columnconfigure(5, weight=1)

        self.refresh_config_combos()

        self.tab_view = ctk.CTkTabview(self.main_frame, border_width=1); self.tab_view.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 10))
        for status in ["On Going", "Ended", "Completed"]:
            tab = self.tab_view.add(status); tab.grid_columnconfigure(0, weight=1); tab.grid_rowconfigure(0, weight=1)
            tree = self.create_treeview(tab); self.treeviews[status] = tree

        button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent"); button_frame.grid(row=3, column=0, sticky="e", padx=20, pady=(0,10))
        delete_button = ctk.CTkButton(button_frame, text="Delete Selected", command=self.delete_task, fg_color="#D32F2F", hover_color="#B71C1C"); delete_button.pack()

    def create_treeview(self, parent_frame):
        style = ttk.Style(); style.theme_use("default")
        col_configs = {"No.": {"width": 50}, "Project Name": {"width": 180}, "Category": {"width": 120}, "Description": {"width": 250}, "Website": {"width": 180}, "Network": {"width": 120}, "Wallet": {"width": 200}, "Reward": {"width": 110}, "Ticker": {"width": 100}, "Date Added": {"width": 150}, "Update Status": {"width": 140, "sortable": False}}
        columns = tuple(col_configs.keys())
        tree = ttk.Treeview(parent_frame, style="Treeview", columns=columns, show="headings")

        for col_name in columns:
            config = col_configs[col_name]; col_id = col_name.replace(" ", "_").replace("($)", "").replace(".", "") 
            heading_options = {"text": col_name, "anchor": ctk.CENTER}
            if config.get("sortable", True): heading_options["command"] = partial(self.sort_by_column, col_id, tree)
            tree.heading(col_name, **heading_options)
            tree.column(col_name, width=config["width"], anchor=ctk.CENTER)
            
        tree.pack(side="left", fill="both", expand=True)
        scroll = ctk.CTkScrollbar(parent_frame, command=tree.yview); scroll.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scroll.set)
        tree.bind("<Button-3>", self.on_tree_right_click)
        tree.bind("<Button-1>", self.on_tree_left_click)
        return tree

    def refresh_config_combos(self):
        cursor = self.db_conn.cursor()
        networks = [r[0] for r in cursor.execute("SELECT name FROM networks ORDER BY name")]
        wallets = [r[0] for r in cursor.execute("SELECT address FROM wallets ORDER BY name")]
        categories = [r[0] for r in cursor.execute("SELECT name FROM categories ORDER BY name")]
        
        self.network_combo.configure(values=networks or ["No networks"]); self.wallet_combo.configure(values=wallets or ["No wallets"]); self.category_combo.configure(values=categories or ["No categories"])
        if networks: self.network_combo.set(networks[0])
        if wallets: self.wallet_combo.set(wallets[0])
        if categories: self.category_combo.set(categories[0])
        
    def populate_task_list(self):
        self.sort_column = "date_added" if self.sort_column is None else self.sort_column
        search_term = self.search_var.get().strip()
        for tree in self.treeviews.values(): tree.delete(*tree.get_children())
        if not self.current_account_id: return
        query = "SELECT id, project_name, website, description, category, ticker, network, wallet, status, reward, date_added FROM tasks WHERE account_id = ?"
        params = [self.current_account_id]
        if search_term: query += " AND project_name LIKE ?"; params.append(f"%{search_term}%")
        
        c = self.db_conn.cursor(); c.execute(query, params); all_records = c.fetchall()
        
        col_index_map = {name.replace(" ", "_").replace("($)", "").replace(".", ""): i for i, name in enumerate(["id", "project_name", "website", "description", "category", "ticker", "network", "wallet", "status", "reward", "date_added"])}
        sort_col_index = col_index_map.get(self.sort_column)
        if sort_col_index is not None:
            def sort_key(record):
                val = record[sort_col_index]
                if isinstance(val, (int, float)): return val
                if isinstance(val, str):
                    try: return float(val.replace(',', ''))
                    except (ValueError, TypeError): return val.lower()
                return val
            all_records.sort(key=sort_key, reverse=self.sort_reverse)
        
        for status, tree in self.treeviews.items():
            count = 1
            for record in all_records:
                if record[8] == status:
                    task_id = record[0]
                    display_data = (
                        count, record[1], record[4], record[3], record[2], record[6], record[7],
                        f"{record[9]:,.2f}", record[5], datetime.strptime(record[10], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y, %H:%M'),
                        f"{record[8]}  ▼"
                    )
                    tree.insert(parent='', index='end', iid=task_id, values=display_data)
                    count += 1
        self.update_heading_indicators(self.treeviews[self.tab_view.get()])

    def add_task(self):
        if not self.current_account_id: messagebox.showerror("Error","No account selected."); return
        project_name = self.project_name_entry.get()
        if not project_name: messagebox.showerror("Input Error", "Project Name is required."); return
        
        website = self.website_entry.get(); description = self.description_entry.get(); category = self.category_combo.get()
        ticker = self.ticker_entry.get()
        try: reward = float(self.reward_entry.get()) if self.reward_entry.get() else 0.0
        except ValueError: messagebox.showerror("Input Error", "Reward must be a valid number."); return
        
        c = self.db_conn.cursor(); date_added = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute("INSERT INTO tasks (project_name, website, description, category, ticker, network, wallet, status, reward, date_added, account_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (project_name, website, description, category, ticker, self.network_combo.get(), self.wallet_combo.get(), "On Going", reward, date_added, self.current_account_id))
        self.db_conn.commit()
        
        self.project_name_entry.delete(0, ctk.END); self.website_entry.delete(0, ctk.END); self.description_entry.delete(0, ctk.END)
        self.ticker_entry.delete(0, ctk.END); self.reward_entry.delete(0, ctk.END)
        self.populate_task_list()
        
    def on_tree_left_click(self, event):
        tree = event.widget; region = tree.identify_region(event.x, event.y)
        if region != "cell": return
        item_id = tree.identify_row(event.y)
        if not item_id: return
        column_id = tree.identify_column(event.x); column_index = int(column_id.replace("#", "")) - 1
        if 0 <= column_index < len(tree['columns']):
            clicked_col_name = tree['columns'][column_index]
            if clicked_col_name == 'Website': self.open_website_link(item_id)
            elif clicked_col_name == 'Update Status': self.show_status_menu(event, item_id)
            elif clicked_col_name == 'Category': self.show_category_menu(event, item_id)

    def show_status_menu(self, event, item_id):
        self.status_context_menu.delete(0, 'end'); 
        current_status_val = self.treeviews[self.tab_view.get()].set(item_id, "Update Status")
        current_status = current_status_val.replace("  ▼", "").strip()
        for option in [s for s in ["On Going", "Ended", "Completed"] if s != current_status]: self.status_context_menu.add_command(label=f"Set to {option}", command=partial(self.handle_status_selection, item_id, option))
        try: self.status_context_menu.tk_popup(event.x_root, event.y_root)
        finally: self.status_context_menu.grab_release()

    def show_category_menu(self, event, item_id):
        self.category_context_menu.delete(0, 'end')
        c = self.db_conn.cursor(); all_categories = [r[0] for r in c.execute("SELECT name FROM categories ORDER BY name")]
        for option in all_categories: self.category_context_menu.add_command(label=f"{option}", command=partial(self.handle_category_selection, item_id, option))
        try: self.category_context_menu.tk_popup(event.x_root, event.y_root)
        finally: self.category_context_menu.grab_release()

    def handle_category_selection(self, task_id, new_category):
        c = self.db_conn.cursor(); c.execute("UPDATE tasks SET category = ? WHERE id = ?", (new_category, task_id)); self.db_conn.commit(); self.populate_task_list()

    def start_inline_edit(self, item_id, col_name, tree):
        if self.active_edit_entry: self.active_edit_entry.destroy()
        x, y, width, height = tree.bbox(item_id, column=col_name)
        
        db_col_map = {"Project Name": "project_name", "Website": "website", "Description": "description", "Network": "network", "Wallet": "wallet", "Reward": "reward", "Ticker": "ticker"}
        db_column = db_col_map.get(col_name)
        if not db_column: return
        
        c = self.db_conn.cursor(); c.execute(f"SELECT {db_column} FROM tasks WHERE id = ?", (item_id,)); 
        current_value = c.fetchone()[0]

        entry = ctk.CTkEntry(tree, width=width, height=height)
        entry.place(x=x, y=y)
        entry.insert(0, "" if current_value is None else str(current_value))
        entry.focus_set()
        entry.bind("<Return>", lambda e: self.save_inline_edit(item_id, db_column, entry.get(), entry))
        entry.bind("<FocusOut>", lambda e: entry.destroy())
        self.active_edit_entry = entry
        
    def redraw_sidebar(self):
        for widget in self.sidebar_frame.winfo_children(): widget.destroy()
        ctk.CTkLabel(self.sidebar_frame, text="oryx.", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 10), padx=20, anchor="w")
        db_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent"); db_frame.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(db_frame, text="Database", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").pack(anchor="w")
        ctk.CTkButton(db_frame, text="Backup Database", command=self.backup_database).pack(fill="x", pady=5)
        ctk.CTkButton(db_frame, text="Restore Database", command=self.restore_database).pack(fill="x", pady=5)
        config_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent"); config_frame.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(config_frame, text="Configuration", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").pack(anchor="w")
        ctk.CTkButton(config_frame, text="Manage Configs", command=self.open_configuration_window).pack(fill="x", pady=5)
        ctk.CTkLabel(self.sidebar_frame, text="Account", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").pack(anchor="w", padx=20, pady=(10,5))
        self.account_scroll_frame = ctk.CTkScrollableFrame(self.sidebar_frame, fg_color="transparent", label_text=""); self.account_scroll_frame.pack(fill="x", expand=False, padx=15)
        self.populate_account_list_sidebar()
        ctk.CTkButton(self.sidebar_frame, text="+ Add Account", fg_color="transparent", text_color=("#007ACC", "#64B5F6"), hover_color=("#E0E2E5", "#404040"), command=self.add_account_popup).pack(fill="x", padx=20, pady=5)
        
        bottom_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent"); bottom_frame.pack(side="bottom", fill="x", pady=10, padx=20)
        self.user_label = ctk.CTkLabel(bottom_frame, text=f"👤 {self.logged_in_user}", anchor="w"); self.user_label.pack(fill="x")
        ctk.CTkButton(bottom_frame, text="Manage Users", fg_color="transparent", text_color="gray", hover=False, anchor="w", command=self.open_user_management, height=20).pack(fill="x")
        ctk.CTkButton(bottom_frame, text="Logout", fg_color="transparent", text_color="#EF4444", hover_color="#FECACA", anchor="w", command=self.logout, height=20).pack(fill="x")
        dark_mode_switch = ctk.CTkSwitch(bottom_frame, text="Dark Mode", command=lambda: self.toggle_dark_mode(dark_mode_switch.get())); dark_mode_switch.pack(anchor="w", pady=(10,0))
        if ctk.get_appearance_mode() == "Dark": dark_mode_switch.select()
        self.update_active_button_style()
    def populate_account_list_sidebar(self):
        for widget in self.account_scroll_frame.winfo_children(): widget.destroy()
        c = self.db_conn.cursor(); c.execute("SELECT id, name FROM accounts ORDER BY name"); accounts = c.fetchall(); self.account_widgets = {}
        for acc_id, acc_name in accounts:
            f = ctk.CTkFrame(self.account_scroll_frame, fg_color="transparent"); f.pack(fill="x", pady=2); f.grid_columnconfigure(0, weight=1)
            b = ctk.CTkButton(f, text=acc_name, anchor="w", command=partial(self.switch_account, acc_id)); b.grid(row=0, column=0, sticky="ew")
            r = ctk.CTkButton(f, text="✏️", width=30, fg_color="transparent", text_color=("gray", "lightgray"), hover_color="#D0D0D0", command=partial(self.rename_account_popup, acc_id, acc_name)); r.grid(row=0, column=1, padx=(5,2))
            d = ctk.CTkButton(f, text="🗑️", width=30, fg_color="transparent", text_color="#E53935", hover_color="#FECACA", command=partial(self.delete_account, acc_id, acc_name)); d.grid(row=0, column=2)
            self.account_widgets[acc_id] = b
        self.update_active_button_style()
    def toggle_dark_mode(self, is_dark):
        mode = "Dark" if is_dark else "Light"; ctk.set_appearance_mode(mode)
        self.update_treeview_style(); self.update_active_button_style()
    def update_treeview_style(self):
        bg_color, fg_color, heading_bg, heading_active_bg = ("#2B2B2B", "white", "#303030", "#404040") if ctk.get_appearance_mode() == "Dark" else ("white", "black", "#F0F2F5", "#E0E2E5")
        selected_color = "#205B85" if ctk.get_appearance_mode() == "Dark" else "#3B8ED0"
        style = ttk.Style()
        style.configure("Treeview", background=bg_color, foreground=fg_color, rowheight=28, fieldbackground=bg_color, borderwidth=0, font=('Calibri', 11)); style.map('Treeview', background=[('selected', selected_color)])
        style.configure("Treeview.Heading", background=heading_bg, foreground=fg_color, relief="flat", font=('Calibri', 12, 'bold')); style.map("Treeview.Heading", background=[('active', heading_active_bg)])
    def save_inline_edit(self, task_id, db_column, new_value, entry_widget):
        try:
            if db_column == 'reward': new_value = float(new_value)
            c = self.db_conn.cursor(); c.execute(f"UPDATE tasks SET {db_column} = ? WHERE id = ?", (new_value, task_id)); self.db_conn.commit()
        except ValueError: messagebox.showerror("Error", "Invalid number format for Reward.")
        except Exception as e: messagebox.showerror("Error", f"Could not save data: {e}")
        finally: entry_widget.destroy(); self.active_edit_entry = None; self.populate_task_list()
    def update_active_button_style(self):
        is_dark = ctk.get_appearance_mode() == "Dark"; active_fg = "#3B8ED0"; inactive_fg = "transparent"; inactive_text = ("#333333", "#DCE4EE")
        for acc_id, button in self.account_widgets.items():
            if acc_id == self.current_account_id: button.configure(fg_color=active_fg, text_color="white", hover=False)
            else: button.configure(fg_color=inactive_fg, text_color=inactive_text, hover=True, hover_color="#D0D0D0" if not is_dark else "#404040")
    def backup_database(self):
        backup_path = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("Database files", "*.db"), ("All files", "*.*")], title="Save Database Backup")
        if backup_path:
            try: shutil.copyfile('oryx_tracker_main.db', backup_path); messagebox.showinfo("Success", f"Database backed up to\n{backup_path}")
            except Exception as e: messagebox.showerror("Error", f"Failed to backup database: {e}")
    def restore_database(self):
        restore_path = filedialog.askopenfilename(defaultextension=".db", filetypes=[("Database files", "*.db"), ("All files", "*.*")], title="Select Database to Restore")
        if restore_path and messagebox.askyesno("Confirm Restore", "This will OVERWRITE all current data.\nAre you sure you want to continue?"):
            try: self.db_conn.close(); shutil.copyfile(restore_path, 'oryx_tracker_main.db'); messagebox.showinfo("Success", "Database restored successfully.\nThe application will now close. Please restart it."); self.root.quit()
            except Exception as e: messagebox.showerror("Error", f"Failed to restore database: {e}")
    def select_initial_account(self):
        if self.current_account_id is None:
            c = self.db_conn.cursor(); first_account = c.execute("SELECT id FROM accounts ORDER BY name LIMIT 1").fetchone()
            if first_account: self.current_account_id = first_account[0]
            else: self.ensure_default_accounts(); self.select_initial_account()
    def on_tree_right_click(self, event):
        tree = event.widget; region = tree.identify_region(event.x, event.y)
        if region != "cell": return
        item_id = tree.identify_row(event.y)
        if not item_id: return
        
        column_id_str = tree.identify_column(event.x)
        column_index = int(column_id_str.replace("#", "")) - 1
        
        if 0 <= column_index < len(tree['columns']):
            col_name = tree['columns'][column_index]
            self.cell_edit_menu.delete(0, 'end')
            self.cell_edit_menu.add_command(label="Edit", command=lambda: self.start_inline_edit(item_id, col_name, tree))
            self.cell_edit_menu.tk_popup(event.x_root, event.y_root)

    def open_website_link(self, item_id):
        c = self.db_conn.cursor(); c.execute("SELECT website FROM tasks WHERE id = ?", (item_id,)); result = c.fetchone()
        if result and result[0]:
            try: webbrowser.open_new_tab(result[0])
            except: messagebox.showerror("Error", "Could not open link. Make sure it's a valid URL.")
    def switch_account(self, account_id):
        self.current_account_id = account_id; self.search_var.set(""); self.update_active_button_style(); self.update_main_title_and_tasks()
    def update_main_title_and_tasks(self):
        if self.current_account_id:
            c = self.db_conn.cursor(); acc_name = c.execute("SELECT name FROM accounts WHERE id = ?", (self.current_account_id,)).fetchone()
            if acc_name: self.title_label.configure(text=acc_name[0])
            else: self.title_label.configure(text="No Account Selected")
        else: self.title_label.configure(text="No Account Selected")
        self.populate_task_list()
    def open_configuration_window(self):
        if not hasattr(self, 'config_window') or not self.config_window.winfo_exists(): self.config_window = ConfigurationWindow(self)
        else: self.config_window.focus()
    def open_user_management(self):
        if not hasattr(self, 'user_management_window') or not self.user_management_window.winfo_exists(): self.user_management_window = UserManagementWindow(self, self.logged_in_user)
        else: self.user_management_window.focus()
    def sort_by_column(self, col, tree):
        if self.sort_column == col: self.sort_reverse = not self.sort_reverse
        else: self.sort_column = col; self.sort_reverse = False
        self.populate_task_list()
    def update_heading_indicators(self, sorted_tree):
        for tree in self.treeviews.values():
            for col_name in tree["columns"]: tree.heading(col_name, text=tree.heading(col_name, "text").replace(" ▲", "").replace(" ▼", ""))
        if self.sort_column:
            col_name_map = {c.replace(" ", "_").replace("($)", "").replace(".", ""): c for c in sorted_tree["columns"]}
            display_col_name = col_name_map.get(self.sort_column)
            if display_col_name: indicator = " ▼" if self.sort_reverse else " ▲"; sorted_tree.heading(display_col_name, text=sorted_tree.heading(display_col_name, "text") + indicator)
    def handle_status_selection(self, task_id, new_status):
        c = self.db_conn.cursor(); c.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id)); self.db_conn.commit(); self.populate_task_list()
    def delete_task(self):
        selected_ids = []; [selected_ids.extend(tree.selection()) for tree in self.treeviews.values()]
        if not selected_ids: messagebox.showinfo("Selection Error", "Please select tasks to delete."); return
        if messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete the selected tasks?"):
            c = self.db_conn.cursor(); [c.execute("DELETE from tasks WHERE id = ?", (task_id,)) for task_id in selected_ids]; self.db_conn.commit()
            self.populate_task_list()
    def add_account_popup(self):
        d = ctk.CTkInputDialog(text="Enter new account name:", title="Add Account"); n = d.get_input()
        if n and n.strip():
            try: c = self.db_conn.cursor(); c.execute("INSERT INTO accounts (name) VALUES (?)", (n.strip(),)); self.db_conn.commit(); self.populate_account_list_sidebar()
            except sqlite3.IntegrityError: messagebox.showerror("Error", f"Account name '{n}' already exists.")
    def rename_account_popup(self, account_id, old_name):
        d = ctk.CTkInputDialog(text=f"Enter new name for '{old_name}':", title="Rename Account"); n = d.get_input()
        if n and n.strip() and n != old_name:
            try: c = self.db_conn.cursor(); c.execute("UPDATE accounts SET name = ? WHERE id = ?", (n.strip(), account_id)); self.db_conn.commit(); self.populate_account_list_sidebar(); self.update_main_title_and_tasks()
            except sqlite3.IntegrityError: messagebox.showerror("Error", f"Account name '{n}' already exists.")
    def delete_account(self, account_id, account_name):
        if messagebox.askyesno("Confirm Deletion", f"Delete '{account_name}'?\nALL tasks inside will also be deleted permanently."):
            c = self.db_conn.cursor(); c.execute("DELETE FROM accounts WHERE id = ?", (account_id,)); self.db_conn.commit()
            if self.current_account_id == account_id: self.select_initial_account()
            self.populate_account_list_sidebar(); self.update_main_title_and_tasks()
    def update_logged_in_user(self, new_username):
        self.logged_in_user = new_username
        self.user_label.configure(text=f"👤 {self.logged_in_user}")
    def logout(self): self.root.destroy(); app = LoginWindow(); app.mainloop()

class ConfigurationWindow(ctk.CTkToplevel):
    def __init__(self, master_app):
        super().__init__(master_app.root)
        self.master_app = master_app; self.db_conn = master_app.db_conn
        self.title("Configuration"); self.geometry("600x500"); self.transient(master_app.root); self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        tab_view = ctk.CTkTabview(self, border_width=1); tab_view.pack(pady=20, padx=20, fill="both", expand=True)
        self.networks_tab = tab_view.add("Manage Networks"); self.wallets_tab = tab_view.add("Manage Wallets"); self.categories_tab = tab_view.add("Manage Categories")
        self.populate_networks_tab(); self.populate_wallets_tab(); self.populate_categories_tab()
    def populate_networks_tab(self):
        for widget in self.networks_tab.winfo_children(): widget.destroy()
        list_frame = ctk.CTkScrollableFrame(self.networks_tab, label_text="Existing Networks"); list_frame.pack(pady=10, padx=10, fill="x")
        c = self.db_conn.cursor(); c.execute("SELECT id, name FROM networks ORDER BY name");
        for net_id, net_name in c.fetchall():
            item_frame = ctk.CTkFrame(list_frame, fg_color="transparent"); item_frame.pack(fill="x", pady=2); item_frame.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(item_frame, text=net_name).grid(row=0, column=0, sticky="w")
            ctk.CTkButton(item_frame, text="Delete", width=60, fg_color="#D32F2F", hover_color="#B71C1C", command=partial(self.delete_item, "networks", net_id, self.populate_networks_tab)).grid(row=0, column=1)
        add_frame = ctk.CTkFrame(self.networks_tab); add_frame.pack(pady=10, padx=10, fill="x")
        self.new_network_entry = ctk.CTkEntry(add_frame, placeholder_text="New Network Name"); self.new_network_entry.pack(side="left", padx=(0, 10), fill="x", expand=True)
        ctk.CTkButton(add_frame, text="Add", command=lambda: self.add_item("networks", self.new_network_entry, self.populate_networks_tab)).pack(side="left")
    def populate_wallets_tab(self):
        for widget in self.wallets_tab.winfo_children(): widget.destroy()
        list_frame = ctk.CTkScrollableFrame(self.wallets_tab, label_text="Existing Wallets"); list_frame.pack(pady=10, padx=10, fill="both", expand=True)
        c = self.db_conn.cursor(); c.execute("SELECT id, name, address FROM wallets ORDER BY name");
        for wal_id, wal_name, wal_address in c.fetchall():
            item_frame = ctk.CTkFrame(list_frame, fg_color="transparent"); item_frame.pack(fill="x", pady=2); item_frame.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(item_frame, text=f"{wal_name} ({wal_address})").grid(row=0, column=0, sticky="w")
            ctk.CTkButton(item_frame, text="Delete", width=60, fg_color="#D32F2F", hover_color="#B71C1C", command=partial(self.delete_item, "wallets", wal_id, self.populate_wallets_tab)).grid(row=0, column=1)
        add_frame = ctk.CTkFrame(self.wallets_tab); add_frame.pack(pady=10, padx=10, fill="x")
        self.new_wallet_name_entry = ctk.CTkEntry(add_frame, placeholder_text="New Wallet Name"); self.new_wallet_name_entry.pack(fill="x", pady=(0, 5))
        self.new_wallet_address_entry = ctk.CTkEntry(add_frame, placeholder_text="New Wallet Address"); self.new_wallet_address_entry.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(add_frame, text="Add", command=self.add_wallet).pack()
    def populate_categories_tab(self):
        for widget in self.categories_tab.winfo_children(): widget.destroy()
        list_frame = ctk.CTkScrollableFrame(self.categories_tab, label_text="Existing Categories"); list_frame.pack(pady=10, padx=10, fill="x")
        c = self.db_conn.cursor(); c.execute("SELECT id, name FROM categories ORDER BY name");
        for cat_id, cat_name in c.fetchall():
            item_frame = ctk.CTkFrame(list_frame, fg_color="transparent"); item_frame.pack(fill="x", pady=2); item_frame.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(item_frame, text=cat_name).grid(row=0, column=0, sticky="w")
            ctk.CTkButton(item_frame, text="Delete", width=60, fg_color="#D32F2F", hover_color="#B71C1C", command=partial(self.delete_item, "categories", cat_id, self.populate_categories_tab)).grid(row=0, column=1)
        add_frame = ctk.CTkFrame(self.categories_tab); add_frame.pack(pady=10, padx=10, fill="x")
        self.new_category_entry = ctk.CTkEntry(add_frame, placeholder_text="New Category Name"); self.new_category_entry.pack(side="left", padx=(0, 10), fill="x", expand=True)
        ctk.CTkButton(add_frame, text="Add", command=lambda: self.add_item("categories", self.new_category_entry, self.populate_categories_tab)).pack(side="left")
    def add_item(self, table_name, entry_widget, refresh_func):
        name = entry_widget.get().strip()
        if not name: return messagebox.showerror("Error", "Name cannot be empty.", parent=self)
        try: c = self.db_conn.cursor(); c.execute(f"INSERT INTO {table_name} (name) VALUES (?)", (name,)); self.db_conn.commit(); entry_widget.delete(0, 'end'); refresh_func()
        except sqlite3.IntegrityError: messagebox.showerror("Error", f"'{name}' already exists.", parent=self)
    def add_wallet(self):
        name = self.new_wallet_name_entry.get().strip(); address = self.new_wallet_address_entry.get().strip()
        if not name or not address: return messagebox.showerror("Error", "Wallet name and address are required.", parent=self)
        try: c = self.db_conn.cursor(); c.execute("INSERT INTO wallets (name, address) VALUES (?, ?)", (name, address)); self.db_conn.commit(); self.new_wallet_name_entry.delete(0, 'end'); self.new_wallet_address_entry.delete(0, 'end'); self.populate_wallets_tab()
        except sqlite3.IntegrityError: messagebox.showerror("Error", "A wallet with this name or address already exists.", parent=self)
    def delete_item(self, table_name, item_id, refresh_func):
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete this item from {table_name}?", parent=self): c = self.db_conn.cursor(); c.execute(f"DELETE FROM {table_name} WHERE id = ?", (item_id,)); self.db_conn.commit(); refresh_func()
    def on_close(self): self.master_app.refresh_config_combos(); self.destroy()

class UserManagementWindow(ctk.CTkToplevel):
    def __init__(self, master_app, current_username):
        super().__init__(master_app.root)
        self.master_app = master_app; self.current_username = current_username; self.db_conn = master_app.db_conn
        self.title("User Management"); self.geometry("500x750"); self.transient(master_app.root); self.grab_set()
        self.user_list_frame = ctk.CTkFrame(self, border_width=1); self.user_list_frame.pack(pady=20, padx=20, fill="x")
        ctk.CTkLabel(self.user_list_frame, text="All Users", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10,5))
        self.scrollable_user_list = ctk.CTkScrollableFrame(self.user_list_frame, height=150); self.scrollable_user_list.pack(pady=5, padx=15, fill="x", expand=True)
        self.populate_user_list()
        add_user_frame = ctk.CTkFrame(self, border_width=1); add_user_frame.pack(pady=(0, 20), padx=20, fill="x")
        ctk.CTkLabel(add_user_frame, text="Add New User", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10,5))
        self.new_username_entry = ctk.CTkEntry(add_user_frame, placeholder_text="New Username", width=300); self.new_username_entry.pack(pady=5, padx=20)
        self.new_password_entry = ctk.CTkEntry(add_user_frame, placeholder_text="New Password", show="*", width=300); self.new_password_entry.pack(pady=5, padx=20)
        ctk.CTkButton(add_user_frame, text="Add User", command=self.add_user).pack(pady=10)
        change_username_frame = ctk.CTkFrame(self, border_width=1); change_username_frame.pack(pady=(0, 20), padx=20, fill="x")
        self.change_username_label = ctk.CTkLabel(change_username_frame, text=f"Change Username for '{self.current_username}'", font=ctk.CTkFont(size=16, weight="bold")); self.change_username_label.pack(pady=(10,5))
        self.change_username_entry = ctk.CTkEntry(change_username_frame, placeholder_text="New Username", width=300); self.change_username_entry.pack(pady=5, padx=20)
        ctk.CTkButton(change_username_frame, text="Change Username", command=self.change_username).pack(pady=10)
        change_password_frame = ctk.CTkFrame(self, border_width=1); change_password_frame.pack(pady=(0, 20), padx=20, fill="x")
        self.change_password_label = ctk.CTkLabel(change_password_frame, text=f"Change Password for '{self.current_username}'", font=ctk.CTkFont(size=16, weight="bold")); self.change_password_label.pack(pady=(10,5))
        self.change_pass_entry1 = ctk.CTkEntry(change_password_frame, placeholder_text="New Password", show="*", width=300); self.change_pass_entry1.pack(pady=5, padx=20)
        self.change_pass_entry2 = ctk.CTkEntry(change_password_frame, placeholder_text="Confirm New Password", show="*", width=300); self.change_pass_entry2.pack(pady=5, padx=20)
        ctk.CTkButton(change_password_frame, text="Change Password", command=self.change_password).pack(pady=10)
    def populate_user_list(self):
        for widget in self.scrollable_user_list.winfo_children(): widget.destroy()
        c = self.db_conn.cursor(); c.execute("SELECT id, username FROM users ORDER BY username"); users = c.fetchall()
        for user_id, username in users:
            user_frame = ctk.CTkFrame(self.scrollable_user_list, fg_color="transparent"); user_frame.pack(fill="x", expand=True); user_frame.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(user_frame, text=username).grid(row=0, column=0, padx=5, sticky="w")
            delete_button = ctk.CTkButton(user_frame, text="Delete", width=80, fg_color="#D32F2F", hover_color="#B71C1C", command=partial(self.delete_user, user_id, username)); delete_button.grid(row=0, column=1, padx=5)
            if username == self.current_username: delete_button.configure(state="disabled", fg_color="gray")
    def delete_user(self, user_id, username):
        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to permanently delete the user '{username}'?", parent=self):
            try: c = self.db_conn.cursor(); c.execute("DELETE FROM users WHERE id = ?", (user_id,)); self.db_conn.commit(); messagebox.showinfo("Success", f"User '{username}' deleted.", parent=self); self.populate_user_list()
            except Exception as e: messagebox.showerror("Error", f"An error occurred: {e}", parent=self)
    def add_user(self):
        username = self.new_username_entry.get().strip(); password = self.new_password_entry.get()
        if not username or not password: return messagebox.showerror("Error", "Username and password cannot be empty.", parent=self)
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        try: c = self.db_conn.cursor(); c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed_password)); self.db_conn.commit(); messagebox.showinfo("Success", f"User '{username}' created successfully.", parent=self); self.new_username_entry.delete(0, 'end'); self.new_password_entry.delete(0, 'end'); self.populate_user_list()
        except sqlite3.IntegrityError: messagebox.showerror("Error", f"Username '{username}' already exists.", parent=self)
    def change_username(self):
        new_username = self.change_username_entry.get().strip()
        if not new_username: return messagebox.showerror("Error", "New username cannot be empty.", parent=self)
        if new_username == self.current_username: return messagebox.showinfo("Info", "New username is the same as the current one.", parent=self)
        try: c = self.db_conn.cursor(); c.execute("UPDATE users SET username = ? WHERE username = ?", (new_username, self.current_username)); self.db_conn.commit(); messagebox.showinfo("Success", "Username changed successfully.", parent=self); self.master_app.update_logged_in_user(new_username); self.destroy()
        except sqlite3.IntegrityError: messagebox.showerror("Error", f"Username '{new_username}' already exists.", parent=self)
    def change_password(self):
        pass1 = self.change_pass_entry1.get(); pass2 = self.change_pass_entry2.get()
        if not pass1 or not pass2: return messagebox.showerror("Error", "Password fields cannot be empty.", parent=self)
        if pass1 != pass2: return messagebox.showerror("Error", "Passwords do not match.", parent=self)
        hashed_password = hashlib.sha256(pass1.encode()).hexdigest()
        try: c = self.db_conn.cursor(); c.execute("UPDATE users SET password_hash = ? WHERE username = ?", (hashed_password, self.current_username)); self.db_conn.commit(); messagebox.showinfo("Success", "Password changed successfully.", parent=self); self.change_pass_entry1.delete(0, 'end'); self.change_pass_entry2.delete(0, 'end')
        except Exception as e: messagebox.showerror("Error", f"An error occurred: {e}", parent=self)

if __name__ == "__main__":
    app = LoginWindow()
    app.mainloop()
