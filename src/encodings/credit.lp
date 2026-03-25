rule(delphi_rule).
rule(months_3_enquiry_rule).
rule(months_12_enquiry_rule).
rule(individual_mandate_rule).
rule(aggregate_mandate_rule).
rule(has_historical_claims_rule).
rule(debtor_auto_approvals_30_days_rule).
l use hypothetical thresholds here.

% python will inject the facts of the application into the encoding 
% Expects: credit_scores(Delphi).
passed(delphi_rule) :- credit_scores(Delphi), Delphi >= 50.

% Expects: enquiries(Enq3M, Enq12M).
passed(months_3_enquiry_rule) :- enquiries(E3, _), E3 <= 3.
passed(months_12_enquiry_rule) :- enquiries(_, E12), E12 <= 10.

% Expects: mandates(IndivHasMandate, AggHasMandate). 1 = True, 0 = False.
passed(individual_mandate_rule) :- mandates(1, _).
passed(aggregate_mandate_rule) :- mandates(_, 1).

% Expects: claims(HasClaimsFlag). True if any claim existed before approval date.
passed(has_historical_claims_rule) :- claims(0). % 0 means NO historical claims

% Expects: auto_approvals(Count).
passed(debtor_auto_approvals_30_days_rule) :- auto_approvals(Count), Count <= 5.

% 3. The Strict Routing Constraint 
route_failed :- rule(R), not passed(R).
route_passed :- not route_failed.

#show route_passed/0.