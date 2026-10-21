"""Knowledge Centre: plain language explanations of every term used in FinSuite.

Written for readers with no finance background. Each entry has
  group    section heading in the Knowledge Centre
  term     the short name (also used by the Assistant chat to find an answer)
  q        the question shown as the entry title
  a        what it means, in simple words
  example  a small worked example with real numbers
  where    where the term appears in FinSuite

Rules quoted here (score bands, thresholds, tax rates) mirror the formulas in
app/calculators.py, so what you read matches what the tools do.
"""

GLOSSARY: list[dict] = []


def _add(group, term, a, example=None, where=None, q=None, also=()):
    GLOSSARY.append({
        "group": group,
        "term": term,
        "q": q or f"What is {term}?",
        "a": a,
        "example": example,
        "where": where,
        "also": list(also),   # extra words the Assistant chat should recognise
    })


# ---------------------------------------------------------------------------
G = "1. Money basics"
# ---------------------------------------------------------------------------
_add(G, "Income",
     "Money that comes to you: salary, business earnings, rent received, interest and so on.",
     "A monthly salary of ₹80,000 is your income.",
     "Finance Report, AI Assistant, Loan Insights, Credit and Risk, Goals.")
_add(G, "Expenses",
     "Money that goes out: rent, food, travel, bills, EMIs and everything else you spend on.",
     "Rent ₹20,000 + food ₹10,000 + bills ₹5,000 = ₹35,000 of expenses in a month.",
     "Finance Report, AI Assistant, Emergency Fund.")
_add(G, "Savings",
     "Money you have kept aside instead of spending. In FinSuite it means the total amount you have saved up so far.",
     "If you have set aside ₹40,000 over the past few months, your savings are ₹40,000.",
     "Finance Report, AI Assistant, Emergency Fund.")
_add(G, "Assets",
     "Everything you own that has value: cash, bank balance, property, shares, gold, a vehicle.",
     "A flat worth ₹10 lakh plus ₹2 lakh in the bank means assets of ₹12 lakh.",
     "ROA, Debt Ratio, Portfolio Dashboard.")
_add(G, "Liabilities",
     "Everything you owe to others: loans, credit card dues, unpaid bills.",
     "A home loan of ₹4 lakh still to be repaid is a liability of ₹4 lakh.",
     "Debt Ratio.")
_add(G, "Equity (net worth)",
     "What is truly yours after paying off what you owe. Equity = Assets minus Liabilities.",
     "Assets ₹12 lakh and liabilities ₹4 lakh leave equity of ₹8 lakh.",
     "ROE, Finance Report, AI Assistant.")
_add(G, "Debt",
     "Borrowed money that must be paid back, usually with interest. Home loans, car loans and credit card balances are debt.",
     "You borrowed ₹2 lakh for a bike. Until it is repaid, that ₹2 lakh is your debt.",
     "Finance Report, Debt to Equity.")
_add(G, "Interest",
     "The price of using money. You pay interest when you borrow and earn interest when you lend or save. It is usually quoted as a percentage per year.",
     "8% interest on ₹1,00,000 for one year is ₹8,000.")
_add(G, "Revenue",
     "The total money a business brings in from selling its products or services, before any costs are taken out. Also called sales or turnover.",
     "A shop that sells goods worth ₹10 lakh in a year has revenue of ₹10 lakh.",
     "Profit Margin, Revenue Growth, Investment Call, Portfolio Dashboard.")
_add(G, "Net profit (net income)",
     "What is left after all costs are paid. For a person: income minus expenses. For a company: revenue minus all costs, interest and taxes.",
     "Income ₹80,000 minus expenses ₹50,000 leaves a net profit of ₹30,000 for the month.",
     "Finance Report, ROE, ROA.")
_add(G, "Inflation",
     "Prices rising over time, so the same money buys less. It is why ₹100 today is worth more than ₹100 ten years from now.",
     "At 6% inflation a year, something that costs ₹100 today will cost about ₹106 next year and about ₹179 in ten years.",
     "Goals and Retirement.")
_add(G, "Compounding",
     "Earning returns on your earlier returns, not just on your original money. Over long periods it makes savings grow much faster.",
     "₹1,00,000 growing at 10% a year becomes ₹1,10,000 after year 1 and ₹1,21,000 after year 2 (not ₹1,20,000), because the second year's 10% is also earned on the first year's gain.",
     "Goals and Retirement, SIP vs Lump Sum.")
_add(G, "GDP (Gross Domestic Product)",
     "The total value of all goods and services a country produces in a period. It is the usual measure of how big and how fast growing an economy is.",
     "If GDP grows from ₹300 lakh crore to ₹318 lakh crore in a year, the economy grew 6%.")

# ---------------------------------------------------------------------------
G = "2. Ratios and financial health"
# ---------------------------------------------------------------------------
_add(G, "ROE (Return on Equity)",
     "How much profit you make for every ₹100 of your own money invested. ROE = Net Profit ÷ Equity × 100. Higher means your own money is working harder.",
     "Net profit ₹1,00,000 on equity ₹5,00,000 gives ROE = 20%.",
     "Ratios, Finance Report, Portfolio Dashboard. FinSuite treats above 15% as strong.")
_add(G, "ROA (Return on Assets)",
     "How much profit you make for every ₹100 of everything you own (not just your own money). ROA = Net Profit ÷ Assets × 100.",
     "Net profit ₹1,00,000 on assets ₹10,00,000 gives ROA = 10%.",
     "Ratios, Investment Call, Portfolio Dashboard. FinSuite treats 10% or more as strong.")
_add(G, "Debt ratio",
     "The share of what you own that is paid for with borrowed money. Debt Ratio = Liabilities ÷ Assets. The higher it is, the more you depend on loans.",
     "Liabilities ₹4,00,000 and assets ₹10,00,000 give a debt ratio of 0.40, meaning 40% of your assets are funded by debt.",
     "Ratios, Portfolio Dashboard.")
_add(G, "Debt to equity ratio",
     "Compares what you owe with what you truly own. Debt to Equity = Debt ÷ Equity. Above 1 means you owe more than you own outright.",
     "Debt ₹2,00,000 and equity ₹5,00,000 give 0.40, which is comfortable. Debt ₹6,00,000 and equity ₹5,00,000 give 1.2, which is high.",
     "Finance Report.")
_add(G, "Leverage",
     "Using borrowed money to do more than your own money alone could. It can boost gains, but it also magnifies losses and the pressure of repayments.",
     "Buying a ₹10 lakh flat with ₹2 lakh of your own money and an ₹8 lakh loan is highly leveraged.")
_add(G, "Profit margin",
     "How much of every ₹100 of sales turns into profit. Profit Margin = Net Profit ÷ Revenue × 100.",
     "Revenue ₹10,00,000 and profit ₹1,50,000 give a margin of 15%.",
     "Investment Call, Portfolio Dashboard. FinSuite treats above 15% as healthy.")
_add(G, "Revenue growth",
     "How much sales increased compared with the earlier period. Revenue Growth = (This period minus Last period) ÷ Last period × 100.",
     "Sales rising from ₹80 lakh to ₹100 lakh is growth of 25%.",
     "Company Performance, Investment Call, Portfolio Dashboard.")
_add(G, "Current ratio (as used in FinSuite)",
     "A simple safety check for individuals: Savings ÷ Monthly Expenses. It tells you how many months you could pay your expenses from savings if income stopped. (Companies use a different, more detailed version of this ratio.)",
     "Savings ₹40,000 and expenses ₹50,000 give 0.8, so savings cover less than one month.",
     "Finance Report.")
_add(G, "Savings ratio",
     "The share of your income that you keep as savings. Savings Ratio = Savings ÷ Income × 100. Below 20% is flagged as thin.",
     "Saving ₹30,000 out of an income of ₹80,000 is a savings ratio of 37.5%.",
     "AI Assistant.")
_add(G, "Borrowed to owned ratio",
     "Borrowed money divided by owned money. Above 1 means you owe more than you own.",
     "Borrowed ₹1,00,000 and owned ₹3,00,000 give 0.33, which is low.",
     "AI Assistant.")
_add(G, "Financial health (Excellent, Good, Weak)",
     "A quick label based on ROE. Above 20% is Excellent, 10% to 20% is Good, and below 10% is Weak.",
     "An ROE of 18% shows as Good.",
     "Ratios, Portfolio Dashboard.")

# ---------------------------------------------------------------------------
G = "3. Loans and credit"
# ---------------------------------------------------------------------------
_add(G, "Credit score",
     "A number between 300 and 900 that shows how reliably you have repaid loans and credit card bills in the past. Lenders use it to decide whether to lend to you and at what interest rate. In India it comes from credit bureaus such as CIBIL.",
     "A score of 780 is very good. A score of 580 means banks may refuse or charge more.",
     "Credit and Risk, Loan Insights.")
_add(G, "Credit score categories",
     "300 to 549 is Poor, 550 to 649 is Fair, 650 to 749 is Good, 750 to 799 is Very Good, and 800 to 900 is Excellent.",
     "A score of 750 moves you from Good to Very Good.",
     "Credit and Risk.")
_add(G, "EMI (Equated Monthly Installment)",
     "The fixed amount you pay every month to repay a loan. Each EMI covers a part of the loan itself and the interest on it.",
     "A loan of ₹5,00,000 repaid with an EMI of ₹12,000 a month means you pay ₹12,000 every month until the loan ends.",
     "Loan Insights, Credit and Risk.")
_add(G, "EMI to income ratio",
     "The share of your monthly income that goes into EMIs. EMI ÷ Monthly Income. Above about 40% is a heavy burden, so FinSuite raises the risk level by one step.",
     "EMI ₹22,000 on an income of ₹50,000 is 44%, which is heavy.",
     "Credit and Risk.")
_add(G, "Credit risk level",
     "How risky it is to lend to someone, from Very High Risk to Very Low Risk. It starts from the credit score (below 550 Very High, 550 to 649 High, 650 to 749 Medium, 750 to 799 Low, 800 and above Very Low) and moves up one step if the EMI burden is above 40% of income.",
     "A score of 700 is Medium Risk. With an EMI of 44% of income it becomes High Risk.",
     "Credit and Risk.")
_add(G, "Loan screening insight",
     "For each customer in the Loan Insights table, FinSuite writes a short comment on the credit profile and a recommendation, for example whether they look like a strong candidate or should reduce their EMI burden first.",
     "A customer with a score of 810 gets 'Excellent credit profile' and 'Strong candidate for premium loan products'.",
     "Loan Insights.")

# ---------------------------------------------------------------------------
G = "4. The stock market"
# ---------------------------------------------------------------------------
_add(G, "Stock (share)",
     "A small piece of ownership in a company. If the company does well, the price of its shares tends to rise, and if it does badly, the price tends to fall.",
     "Buying 10 shares of a company priced at ₹2,500 each costs ₹25,000.",
     "Stock Market, Growth and Target, Watchlist.", also=("stock", "stocks", "shares", "equity share"))
_add(G, "Ticker symbol",
     "A short code that identifies a stock. Indian stocks end with .NS (traded on NSE) or .BO (traded on BSE). US stocks have no ending. Indexes start with ^.",
     "RELIANCE.NS is Reliance on NSE, TCS.NS is Tata Consultancy Services, AAPL is Apple, and ^NSEI is the NIFTY 50 index.",
     "Stock Market, Watchlist, ML Prediction. You can also just search by company name.", also=("ticker", "symbol"))
_add(G, "NSE and BSE",
     "The two main stock exchanges in India, which are marketplaces where shares are bought and sold. NSE is the National Stock Exchange and BSE is the Bombay Stock Exchange.",
     "The same company, such as TCS, can be traded on both, with almost the same price.")
_add(G, "Stock index",
     "A single number that tracks how a group of big companies is doing, so you can see how the market as a whole is moving. NIFTY 50 covers 50 large companies on NSE, SENSEX covers 30 large companies on BSE, and the S&P 500 covers 500 large US companies.",
     "If NIFTY 50 rises 1% in a day, large Indian companies on average went up about 1%.",
     "Stock Market, ML Prediction.", also=("index", "nifty", "nifty 50", "sensex", "s&p 500"))
_add(G, "Live quote and previous close",
     "The quote is the latest traded price of a stock. The previous close is the price at the end of the last trading day. The change shown is the difference between the two, also as a percentage.",
     "Previous close ₹1,215 and latest price ₹1,211.20 means a change of minus ₹3.80, which is minus 0.31%.",
     "Stock Market, Watchlist.")
_add(G, "Open, High, Low, Close and Volume",
     "The five numbers recorded for each trading day. Open is the first price of the day, High is the highest price, Low is the lowest, Close is the last price (the official price for the day), and Volume is how many shares changed hands.",
     "Open ₹1,212, High ₹1,215, Low ₹1,193, Close ₹1,211 and a volume of 1.7 crore shares.",
     "Stock Market daily history table.")
_add(G, "Why is the price not moving?",
     "Stock markets are open only on weekdays for a few hours (Indian markets trade roughly 9:15 am to 3:30 pm). Outside those hours and on holidays the price stays at the last trade. FinSuite shows the time of the last trade so you can tell.",
     "On a Sunday you will see Friday's closing price.",
     "Stock Market, Watchlist.")
_add(G, "Watchlist",
     "A personal list of stocks you want to keep an eye on, so you can see all their prices in one place without searching each time.",
     "Add TCS, Infosys and Reliance, then press Refresh to see all three prices together.",
     "Watchlist and Alerts.")
_add(G, "Price alert",
     "A reminder that triggers when a stock's price crosses a level you choose, either rising above it or falling below it. FinSuite checks alerts each time the watchlist refreshes while the page is open.",
     "Set an alert for 'rises above ₹2,900' and it shows 'Alert triggered' once the price goes above that.",
     "Watchlist and Alerts.")
_add(G, "52 week high and low",
     "The highest and lowest prices a stock has touched in the last year. Where today's price sits between them tells you whether it is near its yearly peak or its bottom. 0% means at the 52 week low and 100% means at the 52 week high.",
     "Price ₹2,650, low ₹2,200, high ₹3,100: the price is 50% of the way up the range.",
     "Portfolio and Tax tools.")
_add(G, "Target price and stop loss",
     "A target price is where you plan to sell to take your profit. A stop loss is a lower price where you plan to sell to limit your loss if things go wrong. Setting both before you buy helps you avoid emotional decisions.",
     "Buy at ₹2,500 with a 15% target (₹2,875) and an 8% stop loss (₹2,300).",
     "Growth and Target planner.")
_add(G, "Risk reward ratio",
     "How much you could gain for every ₹1 you could lose. Risk Reward = Potential Gain ÷ Potential Loss. 2 or more is a favourable setup, 1 to 2 is modest, and below 1 is weak.",
     "Gain ₹3,750 against a loss of ₹2,000 gives 1.88, a workable but modest setup.",
     "Growth and Target planner.")
_add(G, "What if and CAGR",
     "The What If tool shows what your money would be worth today had you invested at an earlier price. CAGR (Compound Annual Growth Rate) is the steady yearly growth rate that would give the same result. It is shown when the holding period is about a month or longer.",
     "₹10,000 invested at ₹2,500 per share is 4 shares. At ₹2,800 they are worth ₹11,200, a gain of ₹1,200 or 12%. Over exactly one year, CAGR is 12%.",
     "Growth and Target planner.")
_add(G, "SIP (Systematic Investment Plan)",
     "Investing a fixed amount every month instead of all at once. It spreads your buying over time, so you buy more shares when prices are low and fewer when they are high.",
     "₹5,000 a month for 12 months invests ₹60,000 in total.",
     "Goals and Retirement, SIP vs Lump Sum.")
_add(G, "Lump sum",
     "Investing the whole amount at one time, on day one.",
     "Putting all ₹60,000 into a stock today.",
     "SIP vs Lump Sum.")
_add(G, "SIP vs lump sum",
     "Compares the two ways of investing the same total amount using actual monthly prices. Neither always wins: lump sum tends to win when prices mostly rise, while SIP can do better when prices dip and recover.",
     "With prices rising from ₹2,500 to ₹2,800, investing ₹60,000 at once gives ₹67,200, while a monthly SIP gives slightly less.",
     "Portfolio and Tax tools.")
_add(G, "Capital gains tax",
     "Tax on the profit you make when you sell a share for more than you paid. In FinSuite's India model: if you sell within 1 year of buying (short term, STCG) the profit is taxed at 20%. If you hold for more than 1 year (long term, LTCG) the profit is taxed at 12.5%, but the first ₹1,25,000 of long term gains in a year is exempt. A 4% cess is then added on the tax. Losses are not taxed.",
     "Buy at ₹100 and sell at ₹200 (10 shares) within 6 months: profit ₹1,000, tax 20% = ₹200, plus 4% cess = ₹208. Tax rules change, so please confirm with a tax professional.",
     "Portfolio and Tax tools.", also=("stcg", "ltcg", "capital gains", "short term capital gains", "long term capital gains"))
_add(G, "Cess",
     "A small extra charge added on top of a tax. Health and education cess in India is 4% of the tax amount.",
     "Tax of ₹200 plus 4% cess is ₹208.",
     "Portfolio and Tax tools.")
_add(G, "Investment call (BUY, HOLD, AVOID)",
     "A quick rule based verdict on a company. It earns 1 point each for: revenue growth of 15% or more, profit margin of 15% or more, ROA of 10% or more, and ROE of 15% or more. Score 3 or 4 is BUY, score 2 is HOLD, and below 2 is AVOID. It is a learning tool, not advice.",
     "Growth 20%, margin 18%, ROA 12% and ROE 16% pass all four checks, so the call is BUY (4 out of 4).",
     "Investment Call.")
_add(G, "Portfolio and diversification",
     "A portfolio is your whole collection of investments. Diversification means spreading money across many companies or sectors so that one bad performer does not hurt you much.",
     "Holding five different companies is safer than putting everything in one.",
     "Portfolio Dashboard.")
_add(G, "Portfolio score, BUY, HOLD and SELL",
     "The Portfolio Dashboard scores each company out of 100: ROE above 15% earns 30 points, ROA above 10% earns 25, revenue growth above 10% earns 25, and profit margin above 15% earns 20. A score of 75 or more is BUY (Low risk), 50 to 74 is HOLD (Medium risk), and below 50 is SELL (High risk). If some figures are missing, the score is worked out from the ones provided.",
     "A company that passes all four tests scores 100 and shows BUY.",
     "Portfolio Dashboard.")
_add(G, "Customer satisfaction and employee retention",
     "Customer satisfaction is the percentage of customers who are happy with a company. Employee retention is the percentage of employees who stay instead of leaving. Both are signs of a well run business.",
     "Retention of 90% means 9 out of 10 employees stayed over the year.",
     "Company Performance.")
_add(G, "Company performance score",
     "A score out of 100 built from three checks: revenue growth above 15% (34 points), customer satisfaction above 80% (33 points) and employee retention above 85% (33 points). 85 or more is Excellent, 60 to 84 is Good, and below 60 is Needs Improvement.",
     "Growth 20%, satisfaction 85% and retention 90% pass all three, scoring 100 (Excellent).",
     "Company Performance.")

# ---------------------------------------------------------------------------
G = "5. Planning your goals"
# ---------------------------------------------------------------------------
_add(G, "Goal planning",
     "Works out how much you must invest every month to reach a future target. Because of inflation, a target in today's money needs a bigger amount in the future, and FinSuite includes that.",
     "A goal of ₹50 lakh in today's money, 15 years away at 6% inflation, needs about ₹1.2 crore at that time. The tool then shows the monthly SIP needed to build it.",
     "Goals and Retirement.")
_add(G, "Expected return",
     "The yearly growth rate you assume your investments will earn. It is only an assumption, so real results can be higher or lower. Using a cautious number is safer.",
     "An expected return of 12% a year is common for equity funds over long periods, but it is never guaranteed.",
     "Goals and Retirement.")
_add(G, "Corpus",
     "The total pile of money built up for a goal, such as retirement.",
     "Reaching a corpus of ₹1.2 crore by age 60.",
     "Goals and Retirement.")
_add(G, "Emergency fund",
     "Cash kept aside for essential expenses if income suddenly stops, for example job loss or illness. The usual target is 6 months of expenses. FinSuite shows 6 months or more as well protected, 3 to 6 months as building, and under 3 months as critical.",
     "Expenses of ₹40,000 a month means a target of ₹2,40,000. Savings of ₹1,50,000 cover 3.75 months, so the status is Building.",
     "Goals and Retirement.")

# ---------------------------------------------------------------------------
G = "6. Machine learning prediction"
# ---------------------------------------------------------------------------
_add(G, "Machine learning",
     "Teaching a computer to find patterns in past data and use them to make a guess about the future. It does not know the future; it only learns from history.",
     "Looking at two years of price history to estimate tomorrow's closing price.",
     "ML Prediction.")
_add(G, "Linear Regression",
     "A simple model that draws the best straight line relationship between today's information (price, averages, volatility) and tomorrow's price, then uses that line to predict.",
     "If prices usually move close to their recent average, the model will lean on that.",
     "ML Prediction.")
_add(G, "Random Forest",
     "A model made of many small decision trees that each vote on the answer; the average of their votes is the prediction. It can capture more complex patterns than a straight line.",
     "Like asking 200 people to guess and taking the average.",
     "ML Prediction.")
_add(G, "Training and test data",
     "The older 80% of the history is used to train the models. The latest 20% is kept hidden and used to test them, to see how well they predict days they have never seen. Testing on unseen days is what makes the accuracy figures honest.",
     "With about 470 usable days, around 374 are used to train and 93 to test.",
     "ML Prediction.")
_add(G, "MAE, RMSE and MAPE",
     "Three ways to measure prediction error on the test days. MAE is the average miss in price. RMSE is similar but punishes big misses more. MAPE is the average miss as a percentage of the price. Lower is better for all three.",
     "An MAE of ₹13 on a ₹1,200 stock means predictions were off by about ₹13 on average, roughly 1%.",
     "ML Prediction.")
_add(G, "Naive baseline",
     "The simplest possible guess: tomorrow's price will equal today's price. A model is only useful if it beats this guess. FinSuite shows the baseline next to both models, and tells you honestly when they do not beat it.",
     "If the naive guess is off by ₹13 on average and a model is off by ₹14, the model added nothing.",
     "ML Prediction.")
_add(G, "Moving average (7 day and 30 day)",
     "The average closing price over the last 7 (or 30) trading days. It smooths out daily ups and downs so you can see the trend. The models use both as inputs.",
     "If the last 7 closes are 100, 102, 101, 103, 104, 102 and 105, the 7 day average is about 102.4.",
     "ML Prediction.")
_add(G, "Daily return",
     "How much the price changed from the previous day, as a percentage.",
     "Closing at ₹102 after ₹100 the day before is a daily return of 2%.",
     "ML Prediction.")
_add(G, "Volatility",
     "How much a price jumps around. A stock with big daily swings is volatile and riskier, while a steady one has low volatility. FinSuite measures it as the spread of daily returns over the last 21 days.",
     "A stock that moves 3% up and down most days is more volatile than one that moves 0.5%.",
     "ML Prediction.")
_add(G, "Why a prediction can be wrong",
     "Share prices react to news, results, global events and human mood, none of which are in the past price data alone. Short term movements are very hard to predict even for professionals. Treat the forecast as a learning exercise, never as a reason to buy or sell.",
     "A sudden company announcement can move the price far more than any model expected.",
     "ML Prediction.")
