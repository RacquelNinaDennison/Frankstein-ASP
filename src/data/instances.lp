% app(ID).
app(1). app(2). app(3).

% app_passed_rule(AppID, RuleName).
% Which specific rules did each application successfully meet based on its data?
app_passed_rule(1, npat_positive).
app_passed_rule(1, debtor_collection_under_60).
app_passed_rule(2, npat_positive).
app_passed_rule(3, current_ratio_over_1_1).

% app_financials(AppID, ClaimAmount, PremiumAmount).
app_financials(1, 0, 5000).
app_financials(2, 15000, 4000).
app_financials(3, 0, 6000).


% app_data(AppID, TotalEquity, RequestedLimit).
app_data(1, 100000, 40000). 
app_data(2, 50000, 10000).
app_data(3, 200000, 100000).