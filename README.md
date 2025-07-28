
# Airdrop Tracker App (v1.0.0)
> ![Dashboard](https://raw.githubusercontent.com/kuncikayu/airdrop-tracker-app/refs/heads/main/screenshot/image.png)

Oryx Tracker is a desktop application for Windows designed to help airdrop hunters track all their activities neatly and efficiently. Forget messy spreadsheets: manage all your projects, wallets, and tasks in one secure application that runs locally on your computer.

## 🔑 Key Features
- **Multi-Account Management**: Easily manage multiple separate portfolios or identities!
- **Detailed Task Tracking**: Record all essential information, including project name, category (Testnet, Retro, Node), description, website, network, wallet, ticket, and potential rewards.
- **Local & Secure Database**: All your data is stored locally on your computer in an `oryx_tracker_main.db` file. No data is sent to external servers.
- **Login System**: Secure access to your data with a safe user login system (passwords are hashed).
- **Dynamic Configuration**: Add, delete, or manage your own lists of Categories, Wallets, and Networks.
- **Backup & Restore**: Easily secure your data with the database backup and restore feature.
- **Automatic Updates**: Get notifications and update the application to the latest version automatically from within the app.
- **Light & Dark Mode**: Customize the application’s appearance according to your preference.

## 📦 Installation
1. Go to the Releases page.                              
2. Download the `.exe` file from the latest release (e.g., `OryxTracker.exe`).
3. Save the file anywhere on your computer.
4. Run the `.exe` file to start the application. No installation is required!

## 🧪 How to Use
1. **First-Time Login**: When running the application for the first time, use the default login details:
   - **Username**: `admin`
   - **Password**: `admin`
2. **User Management**: It is highly recommended to immediately change the default password or create a new user via the **"Manage Users"** button in the sidebar.
3. **Configuration**: Before you start, open **"Manage Configs"** to add the lists of Wallets, Networks, and Categories you frequently use.
4. **Create an Account**: Create your first tracking account using the “➕ Add Account” button.
5. **Start Tracking**: Select an account, then begin adding your airdrop tasks using the form at the top.

## 🛠 Built With
- Python 3
- CustomTkinter: For the modern user interface.
- SQLite3: For the local database.

## 💛 Contributing
Contributions, issues, and feature requests are welcome! Feel free to create an _issue_ or a _pull request_.
