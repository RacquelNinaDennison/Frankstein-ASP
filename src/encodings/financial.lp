% ==========================================
% FINANCIAL RULE EVALUATION LOGIC
% ==========================================

% Rule 1: NPAT > 0
app_passed_finance(App, npat_positive) :- 
    raw_financials(App, npat, NPAT), 
    NPAT > 0.

% Rule 2: Debtor Collection Period < 60 days
app_passed_finance(App, debtor_collection_under_60) :- 
    raw_financials(App, debtor_days, Days), 
    Days < 60.

% Rule 3: Cash > 15% of Limit Requested
% Math trick for ASP: Cash * 100 > Limit * 15
app_passed_finance(App, cash_15_percent_limit) :- 
    raw_financials(App, cash, Cash),
    raw_financials(App, limit_requested, Limit),
    (Cash * 100) > (Limit * 15).

% Rule 4: Current Ratio > 1.1
% Current Ratio is (Current Assets / Current Liabilities).
% Math trick for ASP: Current Assets * 10 > Current Liabilities * 11
app_passed_finance(App, current_ratio_over_1_1) :- 
    raw_financials(App, current_assets, CA),
    raw_financials(App, current_liab, CL),
    (CA * 10) > (CL * 11).


% Calculate the cumulative score for each application
score(App, TotalScore) :-
    app(App),
    TotalScore = #sum { Weight, Rule : app_passed_finance(App, Rule), passed_weight(Rule, Weight) }.

% Equity allocation based on score thresholds
equity_allocation(App, 0)  :- score(App, S), S < 50.
equity_allocation(App, 25) :- score(App, S), S >= 50, S <= 75.
equity_allocation(App, 50) :- score(App, S), S >= 76, S <= 100.
equity_allocation(App, 75) :- score(App, S), S > 100.

% Allowed limit = (Equity * Allocation%) / 100
allowed_limit(App, Limit) :-
    app_data(App, Equity, _),
    equity_allocation(App, Percentage),
    Limit = (Equity * Percentage) / 100.

% Route passes if requested amount <= allowed limit
route_passed(App) :-
    app_data(App, _, Requested),
    allowed_limit(App, Limit),
    Requested <= Limit.

#show route_passed/1.
#show score/2.