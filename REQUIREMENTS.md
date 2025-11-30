# Midas Finance Bot - Complete Requirements

## Project Overview
**Goal:** Create a Telegram bot that is a FULL CLONE of Spendee app functionality + automatic wallet/bank integration + AI financial analysis

**Quality Standard:** 10/10 - NO BUGS, fully functional, tested autonomously

## Core Requirements

### 1. Spendee Clone Features (MUST HAVE ALL)
- ✅ Add/Edit/Delete transactions
- ✅ Categories management (custom user categories)
- ❌ Labels/Tags management
- ❌ Analytics (charts, reports, spending by category)
- ❌ Wallets management (add/edit/delete/view)
- ❌ Multi-currency support
- ❌ Transaction history with filters
- ❌ Budget tracking
- ❌ Recurring transactions

### 2. Smart Currency Detection
- ✅ Parse amounts with any currency format
- ✅ Support Ukrainian: гривны, гривень, грн, гривна, гривні
- ✅ Support symbols: $, €, £, ¥, ₽, ₴
- ✅ Support codes: USD, EUR, GBP, UAH, etc.
- ✅ Handle formats: "100 usd", "€50", "1,000.50 USD"

### 3. Automatic Wallet Integration

#### Crypto Wallets (via Blockchain API)
**Supported wallets:**
- Trustee Global
- Trust Wallet
- Exodus
- Binance
- Best Wallet

**Implementation:**
- Use Moralis API (key provided: ***REMOVED_MORALIS_API_KEY***
- Use TronGrid for TRON network
- Monitor wallet addresses:
  - TUAWUDwPxhVUeMBcNZMRNCns9GNjXzi4Hv
  - TDfdioqwoxcWRpKisGLx5nnqJFqgTA9R3A
  - 0xc1964Ea65e5024128f6a732942203D8beAffa30b

**Features:**
- Auto-sync transactions from blockchain
- Detect balance changes
- Track USDT/USDC swaps (card payments detection)
- Get transaction hash, txid, all metadata
- Support both fiat and crypto currencies

#### Card Payment Detection Logic
**Critical logic for Trustee card:**
1. USDT → USDC swap = preparing for card payment
2. USDC balance decrease = card payment (99% confidence)
3. USDC → EUR swap = card payment in local currency
4. Track balance changes every cycle (hourly)
5. Calculate difference: if balance decreased = transaction happened

#### Bank/Payment Services (Future)
- Wise (API key needed)
- Pioneer (API key needed)
- Revolut (skip for now - expensive)
- Monobank (API key needed)

### 4. AI Finance Analysis with DeepSeek

**DeepSeek API Key:** ***REMOVED_DEEPSEEK_API_KEY***

**Requirements:**
- Use DeepSeek latest model with deep thinking
- **PERSISTENT CHAT:** One continuous conversation, NOT new chat each time
- When token limit reached: transfer full context + chronology to new chat
- Self-learning: bot gets smarter over time
- Analyze periods: 1, 3, 7, 14, 30, 60, 90, 180, 363 days + ALL TIME
- Generate detailed 10/10 quality reports
- Analyze by: categories, labels, amount, currency, notes, dates

**Analysis triggers:**
- Manual user request
- Automatic periodic analysis (configurable)

**Report format:**
- Spending patterns
- Category breakdown
- Budget recommendations
- Anomaly detection
- Trends and forecasts

### 5. Merchant Learning & Transaction Categorization

**Automatic categorization:**
1. Check transaction description (merchant name)
2. Search in database for identical merchant/description
3. If found: use same category + label
4. If not found: use AI to analyze + search online
5. If AI uncertain (< 95% confidence): ASK USER

**User confirmation flow:**
When bot is uncertain:
```
🤔 Uncategorized Transaction

Amount: 107 USDC
Date: 2025-11-30
Wallet: Trustee (Ethereum)
Hash: 0x1234...
Description: [merchant name if available]

Please select category:
[Category buttons]

Or provide details:
```

**Learning:**
- Save user's choice to database
- Use for future similar transactions
- Build merchant database over time

### 6. Transfer Detection

**Algorithm:**
1. Monitor all wallets in parallel
2. If wallet A balance decreases
3. Check all other wallets within 1-30 minutes
4. If wallet B receives same amount → TRANSFER
5. If no match → expense or external transfer (ask user)

**Important:**
- Don't count transfers as expenses
- Track both source and destination
- Handle failed/frozen transfers

### 7. Auto-Sync Scheduler

**Implementation:** APScheduler + Redis (if needed)

**Cycle:**
- Check all connected wallets sequentially
- Frequency: Every hour (configurable)
- Can be enabled/disabled per user
- Process new transactions only (track last sync time)

**Process:**
1. Fetch new transactions from each wallet
2. Detect transfers between user's wallets
3. Categorize transactions (AI + learning)
4. Ask user for uncertain transactions
5. Update database
6. Update wallet balances

### 8. User Categories (35 categories provided)

**Income (3):**
- Salary
- Freelance
- Other Income

**Expense (32):**
- Cars: Audi A6, Mercedes w222, Mazda 6, BMW 3 F30
- Food & Dining
- Shopping
- Transport
- Bills & Utilities
- Entertainment
- Health
- Education
- Travel
- Gifts
- [... and more from user's Spendee screenshots]

**Features:**
- View all categories
- See transaction count per category
- See total spent per category
- Edit/delete categories
- Add new categories

### 9. Database & Storage

**Supabase:**
- URL: https://uwsroinzalaauretfutm.supabase.co/
- Service Role Key: ***REMOVED_MORALIS_API_KEY***
- MCP connection available

**Data retention:**
- ❌ NO auto-deletion of transactions
- Keep ALL transaction history forever
- More data = better AI learning
- Scale infrastructure if needed

**Tables:**
- users
- wallets
- categories
- labels
- transactions
- merchant_mappings (for learning)
- ai_analysis_history

### 10. Bot UI/UX Requirements

**Main Menu:**
- 💰 Add Transaction
- 📊 Analytics
- 🏷️ Categories
- 🏦 Wallets
- 🤖 AI Finance Analysis
- ⚙️ Settings

**Transaction Flow:**
1. Select type (Income/Expense/Transfer)
2. Select category
3. Enter amount (smart currency detection)
4. Select date
5. Add note (optional)
6. Confirm → MUST SAVE TO DATABASE

**Analytics:**
- Charts and graphs
- Spending by category
- Period comparison
- Export functionality

**Wallets Management:**
- List all wallets
- Add new wallet (manual or auto-sync)
- Edit wallet details
- View wallet balance
- Enable/disable auto-sync per wallet

**AI Analysis:**
- Button to request analysis
- Select time period
- View analysis report
- Save analysis history
- View past analyses

## Critical Rules

### Development Process
1. **NO DUPLICATES:** Update existing files, don't create new versions
2. **TEST EVERYTHING:** Test autonomously before reporting completion
3. **MAINTAIN CHECKLIST:** Update one checklist, don't abandon and create new
4. **WORK AUTONOMOUSLY:** Fix all bugs independently
5. **QUALITY 10/10:** No bugs, no errors, no shortcuts

### Code Quality
- Comprehensive error logging
- Handle all edge cases
- Graceful error messages to user
- No infinite loading states
- All buttons must work

### Bot Behavior
- Smart and friendly responses
- Clear documentation/help
- Ask user when uncertain
- Never lose data
- Fast response times

## Current Status

### ✅ Working
- Bot starts and responds
- User registration
- Main menu
- Transaction flow (type → category → amount → date → note)
- 35 categories in database
- 2 wallets in database
- Smart currency parser (Ukrainian support)
- Transaction saving to Supabase

### ❌ Broken/Missing
- Labels management
- Analytics (infinite loading)
- Categories view (shows wrong info)
- Wallets management (weak UI, no add/edit)
- AI Finance Analysis button missing
- Back button from AI response (infinite loading)
- AI analysis history not saved
- Auto-sync not implemented
- Blockchain API integration not started
- Merchant learning not implemented
- Transfer detection not implemented
- Uncategorized transactions flow not implemented

## Next Steps (Priority Order)

1. Fix all infinite loading issues
2. Implement proper Categories UI
3. Implement Labels management
4. Implement Analytics
5. Implement Wallets management UI
6. Add AI Finance Analysis button
7. Implement blockchain API integration (Moralis + TronGrid)
8. Implement auto-sync scheduler
9. Implement merchant learning
10. Implement transfer detection
11. Implement uncategorized transactions flow
12. Test everything end-to-end
13. Create GitHub repository
14. Final QA and deployment

## Success Criteria

- [ ] All Spendee features working
- [ ] Smart currency detection (all languages)
- [ ] Auto-sync from crypto wallets
- [ ] AI analysis with persistent chat
- [ ] Merchant learning working
- [ ] Transfer detection accurate
- [ ] No bugs or errors
- [ ] Fast and responsive
- [ ] User-friendly
- [ ] Well documented
- [ ] GitHub repository created
- [ ] 10/10 quality achieved
