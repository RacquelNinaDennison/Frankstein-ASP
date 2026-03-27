import clingo
import asyncio
from pathlib import Path
from src.modules.data_loader import to_ceiling_facts, to_credit_facts, to_finance_facts, to_optimization_facts

BASE = Path(__file__).parent
ENCODINGS = BASE / "src" / "encodings"
INSTANCES = BASE / "src" / "data"
CELLING = ENCODINGS / "celling.lp"
CREDIT = ENCODINGS / "credit.lp"
FINANCE = ENCODINGS / "financial.lp"
FINANCIAL_OPTIMISATIONS = ENCODINGS / "finance_optimisation.lp"
OPTIMISED_FACTS = INSTANCES/ "instances.lp"


class Frankenstein:
    def __init__(self):
        self.finance_optimization_file = FINANCIAL_OPTIMISATIONS
        self.base_route_file = CELLING
        self.credit = CREDIT
        self.finance = FINANCE

    def run_optimizations(self, optimization_facts_string):
        """
        Runs the offline optimization batch process to find the perfect weights.
        Accepts a string of ASP facts (not a file path).
        """
        ctl = clingo.Control()
        #ctl.add("base", [], optimization_facts_string)
        ctl.load(str(optimization_facts_string))
        ctl.load(str(self.finance_optimization_file))
        ctl.ground([("base", [])])

        optimal_weights = {}
        ctl.configuration.solve.opt_mode = "opt"
        def on_model(model):
                    # Clingo calls this every time it finds a BETTER weight combination
                    optimal_weights.clear()
                    for atom in model.symbols(shown=True):
                        if atom.name == "passed_weight":
                            rule_name = str(atom.arguments[0])
                            weight_val = atom.arguments[1].number
                            optimal_weights[rule_name] = weight_val
                    
                    # Print the deviation penalty to the console so we can see it working!
                    print(f"  [Optimizer] Found better configuration. Deviation Penalty: {model.cost}")
        print("Running Optimization Solver...")
        ctl.solve(on_model=on_model)

        print(f"Optimization Complete! Best Weights: {optimal_weights}")
        return optimal_weights

    def _run_clingo_sync(self, route_file, app_data_string, optimized_weights=None):
        """
        The actual blocking Clingo solver logic.
        We will push this into a background thread so it doesn't block Python.
        """
        atoms_collected = []
        ctl = clingo.Control()
        ctl.load(str(route_file))
        ctl.add("base", [], app_data_string)
        if optimized_weights:
            ctl.add("base", [], optimized_weights)
        ctl.ground([("base", [])])

        def on_model(model):
            for atom in model.symbols(shown=True):
                if "route_passed" in str(atom):
                    atoms_collected.append(str(atom))
                if "score" in str(atom):
                    atoms_collected.append(str(atom))

        ctl.solve(on_model=on_model)
        return atoms_collected

    async def evaluate_ceiling(self, app_data):
        return await asyncio.to_thread(self._run_clingo_sync, self.base_route_file, app_data)

    async def evaluate_finance(self, app_data, optimized_weights):
        return await asyncio.to_thread(self._run_clingo_sync, self.finance, app_data, optimized_weights)

    async def evaluate_credit(self, app_data):
        return await asyncio.to_thread(self._run_clingo_sync, self.credit, app_data)

    async def pass_applications(self, applications):
        """
        Evaluates parallel routes and applies prioritization logic.
        applications: list of dicts loaded from JSON.
        """
 

        optimal_weights = self.run_optimizations(OPTIMISED_FACTS)

        weight_facts = "\n".join(
            f"passed_weight({rule}, {weight})."
            for rule, weight in optimal_weights.items()
        )

        results = {}
        for idx, app in enumerate(applications, start=1):
            app_id = app["DBC_REFNUM"]
            print(f"Evaluating App {app_id} in parallel...")

            ceiling_facts = to_ceiling_facts(app)
            credit_facts = to_credit_facts(app)
            finance_facts = to_finance_facts(idx, app)

            ceiling_task = self.evaluate_ceiling(ceiling_facts)
            finance_task = self.evaluate_finance(finance_facts, weight_facts)
            credit_task = self.evaluate_credit(credit_facts)

            ceiling_pass, finance_pass, credit_pass = await asyncio.gather(
                ceiling_task, finance_task, credit_task
            )

            print(f"  [Results] Ceiling: {ceiling_pass} | Finance: {finance_pass} | Base: {credit_pass}")

            if ceiling_pass:
                decision = "APPROVED (Ceiling)"
            elif finance_pass:
                for atom in finance_pass:
                    if("route_passed" in atom):
                        decision="APPROVED (Finance)"
            elif credit_pass:
                decision = "APPROVED (Base)"
            else:
                decision = "REJECTED (Refer to Underwriter)"

            results[app_id] = decision
            print(f"  [Final Decision] {decision}\n")

        return results
