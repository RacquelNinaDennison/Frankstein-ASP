% ==========================================
% APPLICATION IDENTIFIER & CORE DATA
% ==========================================
% app_data(RequestedAmount, IndividualLimit, GroupLimit).
% They want $50k. The committee previously authorized $60k for them individually, 
% and $100k for their corporate group.
app_data(50000, 60000, 100000).

% app_data(AppID, Equity, RequestedAmount).
% Used by the Finance Route to calculate the final equity allocation.
app_data(101, 150000, 50000).

% ==========================================
% FINANCIAL DATA (For the Finance Route)
% raw_financials(AppID, Metric, Value).
% ==========================================
raw_financials(101, limit_requested, 50000).
raw_financials(101, npat, 15000).             % $15k Profit (Passes > 0)
raw_financials(101, debtor_days, 45).         % 45 Days (Passes < 60)
raw_financials(101, cash, 10000).             % $10k Cash (Passes > 15% of 50k requested)
raw_financials(101, current_assets, 200000).  % CA: $200k
raw_financials(101, current_liab, 150000).    % CL: $150k (Ratio is 1.33, Passes > 1.1)

% ==========================================
% CREDIT PROFILE (For the Base Route)
% ==========================================
% Delphi Credit Score (Assume >= 50 passes)
credit_scores(65).

% Enquiries: 3-Months and 12-Months (Assume <= 3 and <= 10 passes)
enquiries(1, 4).

% Mandates: Individual and Aggregate (1 = True, 0 = False)
mandates(1, 1).

% Historical Claims: 0 = No historical claims, 1 = Has claims
claims(0).

% Auto Approvals in last 30 days (Assume <= 5 passes)
auto_approvals(2).