# 💰 Midas Finance Bot

**AI-Powered Personal Finance Management Telegram Bot**

Midas is a comprehensive financial management bot that helps you track expenses, manage multiple wallets (fiat & crypto), analyze spending patterns with AI, and automatically sync transactions from blockchain wallets.

## ✨ Features

### 📊 Core Features
- **Multi-Wallet Support** - Manage unlimited fiat and crypto wallets
- **Smart Transaction Tracking** - Manual entry with intelligent currency parsing
- **Category Management** - Organize transactions with custom categories and icons
- **Labels & Tags** - Add multiple labels to transactions for better organization
- **Analytics Dashboard** - Visual spending insights and trends

### 🤖 AI-Powered Features
- **AI Finance Analysis** - Get personalized financial insights using DeepSeek AI
- **Smart Categorization** - AI automatically categorizes transactions
- **Merchant Learning** - Bot learns from your corrections and improves over time
- **Spending Pattern Analysis** - Identify trends and get budget recommendations

### ⛓️ Blockchain Integration
- **Auto-Sync Crypto Wallets** - Automatically import transactions from Ethereum, TRON, BSC
- **Multi-Network Support** - ERC20, TRC20, and native token support
- **Transfer Detection** - Automatically detect transfers between your own wallets
- **Card Payment Detection** - Track crypto card payments (USDT→USDC swaps)

### 🔄 Automation
- **Scheduled Auto-Sync** - Hourly automatic wallet synchronization
- **Smart Notifications** - Get notified about uncategorized transactions
- **Merchant Mapping** - Automatic merchant-to-category mapping

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Moralis API Key (for blockchain features)
- DeepSeek API Key (for AI features)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/midas-finance-bot.git
cd midas-finance-bot
```

2. **Create virtual environment**
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys
```

Required environment variables:
```env
BOT_TOKEN=your_telegram_bot_token
DEEPSEEK_API_KEY=your_deepseek_api_key
MORALIS_API_KEY=your_moralis_api_key
```

5. **Run the bot**
```bash
python3.11 -m src.main
```

## 📖 Usage

### Basic Commands
- `/start` - Initialize the bot and create your profile
- `/help` - Show help and available commands
- `/sync` - Manually sync crypto wallets
- `/pending` - View uncategorized transactions

### Adding Transactions
1. Click "➕ Add Transaction"
2. Select type (Expense/Income/Transfer)
3. Choose category
4. Enter amount (supports multiple formats):
   - `100 USD`
   - `1.234,56 EUR`
   - `500 грн` (Ukrainian)
   - `50.5` (default currency)
5. Add optional note
6. Confirm

### Managing Wallets
1. Go to "💼 Wallets"
2. Click "➕ Add Wallet"
3. Choose type:
   - **Manual Wallet** - For cash, bank accounts, cards
   - **Crypto Wallet** - For Ethereum, TRON, BSC addresses
4. For crypto wallets, enable auto-sync to import transactions automatically

### AI Finance Analysis
1. Click "🤖 AI Finance"
2. Choose analysis type:
   - **Smart Insights** - Overall financial health
   - **Spending Patterns** - Where your money goes
   - **Budget Tips** - Personalized recommendations
   - **Savings Goals** - How to save more

## 🏗️ Architecture

### Project Structure
```
midas-finance-bot/
├── src/
│   ├── app/
│   │   ├── bot/
│   │   │   ├── handlers/       # Telegram bot handlers
│   │   │   ├── keyboards/      # Inline keyboards
│   │   │   └── states/         # FSM states
│   │   ├── services/           # Business logic
│   │   │   ├── blockchain_service.py
│   │   │   ├── deepseek_service.py
│   │   │   ├── sync_service.py
│   │   │   └── ...
│   │   ├── scheduler/          # Background jobs
│   │   └── utils/              # Utilities
│   ├── domain/                 # Domain models
│   ├── infrastructure/         # Data layer
│   │   ├── repositories/       # Database repositories
│   │   ├── database.py         # SQLite wrapper
│   │   └── logging_config.py
│   └── main.py                 # Entry point
├── data/                       # SQLite database
├── requirements.txt
├── .env
└── README.md
```

### Technology Stack
- **Bot Framework**: aiogram 3.x
- **Database**: SQLite (with option for Supabase)
- **AI**: DeepSeek API
- **Blockchain**: Moralis API, TronGrid API
- **Scheduler**: APScheduler
- **Language**: Python 3.11+

## 🔧 Configuration

### Currency Support
The bot automatically detects currencies from text:
- **USD**: $, USD, dollars, bucks
- **EUR**: €, EUR, euros
- **UAH**: ₴, грн, гривны, гривень
- **And many more...**

### Number Formats
Supports multiple number formats:
- US: `1,234.56`
- European: `1.234,56`
- Simple: `1234.56`

### Auto-Sync Settings
Configure in `/sync` command:
- **Interval**: 1 hour (default)
- **Enable/Disable**: Per user
- **Manual Trigger**: Sync anytime

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [aiogram](https://github.com/aiogram/aiogram) - Telegram Bot framework
- [DeepSeek](https://www.deepseek.com/) - AI API for financial analysis
- [Moralis](https://moralis.io/) - Blockchain API
- [TronGrid](https://www.trongrid.io/) - TRON blockchain API

## 📧 Support

For support, email support@example.com or open an issue on GitHub.

## 🗺️ Roadmap

- [x] **Balance-based Detection**
- [x] **Production-Ready Security**
- [x] **Unit of Work Pattern**
- [x] **Comprehensive Error Handling**
- [ ] Multi-language support (English, Ukrainian, Russian)
- [ ] Export to CSV/Excel
- [ ] Budget planning and alerts
- [ ] Recurring transactions
- [ ] Split transactions
- [ ] Receipt scanning (OCR)
- [ ] Web dashboard
- [ ] Mobile app

## 📊 Status

**Version**: 2.0.0  
**Status**: Active Development  
**Last Updated**: November 2025

---

Made with ❤️ by the Midas Team
