% rules that need to be passed on the ceiling route
rule(individual_ceiling_limit).
rule(group_ceiling_limit).

% if a req <= indiv, then the individual ceiling limit is passed
passed(individual_ceiling_limit) :- 
    app_data(Req, Indiv, _), 
    Req <= Indiv.

% group celling requirement 
passed(group_ceiling_limit) :- 
    app_data(Req, _, Group), 
    Req <= Group.


route_failed :- rule(R), not passed(R).
route_passed :- not route_failed.

#show route_passed/0.