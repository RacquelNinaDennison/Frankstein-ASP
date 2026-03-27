rule(delphi_rule).
rule(months_3_enquiry_rule).
rule(months_12_enquiry_rule).
rule(has_historical_claims_rule).

% Expects: credit_scores(Delphi).
passed(delphi_rule) :- credit_scores(Delphi), Delphi >= 50.

% Expects: enquiries(Enq3M, Enq12M).
passed(months_3_enquiry_rule) :- enquiries(E3, _), E3 <= 3.
passed(months_12_enquiry_rule) :- enquiries(_, E12), E12 <= 10.

% Expects: claims(HasClaimsFlag). 0 = No historical claims, 1 = Has claims.
passed(has_historical_claims_rule) :- claims(0).

% The Strict Routing Constraint
route_failed :- rule(R), not passed(R).
route_passed :- not route_failed.

#show route_passed/0.