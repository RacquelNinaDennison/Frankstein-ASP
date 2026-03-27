% these are the rules we are hopping to optimise 
rule(npat_positive).
rule(debtor_collection_under_60).
rule(cash_15_percent_limit).
rule(current_ratio_over_1_1).


% required to be multiples of 5
multiplier(0..20).

% for every rule defined, we want to assign some weight to it 
1 { passed_weight(R, M * 5) : multiplier(M) } 1 :- rule(R).


% Calculate total score per application using the #sum aggregate
% the score is based on the weighting assigned. 
% for these applications which passed the previous rules, if we were to adjust the rules, what would their score be?
% also question for Vince- what classifies as a passed rule? 
score(App, TotalScore) :- 
    app(App), 
    TotalScore = #sum { Weight, Rule : app_passed_rule(App, Rule), passed_weight(Rule, Weight) }.

% Define the Finance route passing criteria. 
equity_allocation(App, 0)  :- score(App, S), S < 50.
equity_allocation(App, 25) :- score(App, S), S >= 50, S <= 75.
equity_allocation(App, 50) :- score(App, S), S >= 76, S <= 100.
equity_allocation(App, 75) :- score(App, S), S > 100.

% 2. Calculate the Allowed Limit (Equity * Allocation %) / 100
% allowed amount is based on their equity and their weighted score 
allowed_limit(App, Limit) :-
    app_data(App, Equity, _),
    equity_allocation(App, Percentage),
    Limit = (Equity * Percentage) / 100.

% The route passes ONLY if the requested limit is less than or equal to the allowed limit
route_passed(App) :-
    app_data(App, _, Requested),
    allowed_limit(App, Limit),
    Requested <= Limit.


% 1. Aggregate the totals for APPROVED applications only
total_approvals(A) :- A = #count { App : route_passed(App) }.
total_premium(P)   :- P = #sum { Req, App : route_passed(App), app_data(App, _, Req) }.
total_claims(C)    :- C = #sum { Claim, App : route_passed(App), app_financials(App, Claim, _) }.
total_apps(T)      :- T = #count { App : app(App) }.

% 2. Calculate the Scaled Ratio: (100 * Approvals * Premium) / (Total Apps * Claims)
numerator(N)   :- total_approvals(A), total_premium(P), N = 100 * A * P.
denominator(D) :- total_apps(T), total_claims(C), D = T * C.

% Calculate the ratio (safeguarding against division by zero)
ratio(R) :- numerator(N), denominator(D), D > 0, R = N / D.
ratio(9999) :- denominator(0). % Heavy penalty if no claims exist in the portfolio

% 3. Calculate the absolute deviation from the target of 175
deviation(Dev) :- ratio(R), R >= 175, Dev = R - 175.
deviation(Dev) :- ratio(R), R < 175, Dev = 175 - R.

% 4. Instruct the solver to find the weights that minimize this deviation
#minimize { Dev : deviation(Dev)}.

#show passed_weight/2.

