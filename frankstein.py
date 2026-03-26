import clingo
import asyncio
from pathlib import Path 

BASE = Path(__file__).parent
ENCODINGS = BASE/"src"/"encodings"
INSTANCES = BASE/"src"/"data" 
CELLING = ENCODINGS/"celling.lp"
CREDIT = ENCODINGS/"credit.lp"
FINANCE = ENCODINGS/"financial.lp"
FINANCIAL_OPTMISATIONS = ENCODINGS/"finance_optimisations.lp"

# DATA 

TRAINING = INSTANCES/"training.lp"


class Frankenstein:
    def __init__(self):
        self.finance_optimization_file = FINANCIAL_OPTMISATIONS
        self.base_route_file = CELLING
        self.credit = CREDIT
        self.finance = FINANCE

    def run_optimizations(self, historical_data_file):
        """
        Runs the offline optimization batch process to find the perfect weights.
        """
        ctl = clingo.Control()
        ctl.load(historical_data_file)
        ctl.load(self.finance_optimization_file)
        ctl.ground([("base", [])])
        
        optimal_weights = {}

        def on_model(model):
            optimal_weights.clear() 
            for atom in model.symbols(shown=True):
                if atom.name == "passed_weight":
                    rule_name = str(atom.arguments[0])
                    weight_val = atom.arguments[1].number
                    optimal_weights[rule_name] = weight_val

        print("Running Optimization Solver...")
        ctl.solve(on_model=on_model)
        
        print(f"Optimization Complete! Best Weights: {optimal_weights}")
        return optimal_weights


    def _run_clingo_sync(self, route_file, app_data_string, optimized_weights = None):
        """
        The actual blocking Clingo solver logic. 
        We will push this into a background thread so it doesn't block Python.
        """
      

        atoms_collected= []
        ctl = clingo.Control()
        ctl.load(route_file)
        ctl.add("base", [], app_data_string)
        if optimized_weights:
            ctl.add("base", [], optimized_weights)
        ctl.ground([("base", [])])

        def on_model(model):
            for atom in model.symbols(showm=True):
                if "route_passed" in str(atom):
                    atoms_collected.append(atom)
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


    async def pass_applications(self, list_of_application_data, optimized_weights):
        """
        Evaluates parallel routes and applies prioritization logic.
        """
        results = {}
        optimized_weights = self.run_optimizations(INSTANCES)
        for app_id, app_data in list_of_application_data.items():
            print(f"Evaluating App {app_id} in parallel...")
            
            ceiling_task = self.evaluate_ceiling(app_data)
            finance_task = self.evaluate_finance(app_data, optimized_weights)
            base_task = self.evaluate_credit(app_data)
            

            ceiling_pass, finance_pass, base_pass = await asyncio.gather(
                ceiling_task, finance_task, base_task
            )
            
            print(f"[Scores] Ceiling: {ceiling_pass[0]} | Finance: {finance_pass[0]} | Base: {base_pass[0]}")
            

            if ceiling_pass:
                decision = "APPROVED (Ceiling)"
            elif finance_pass:
                decision = "APPROVED (Finance)"
            elif base_pass:
                decision = "APPROVED (Base)"
            else:
                decision = "REJECTED (Refer to Underwriter)"
                
            results[app_id] = decision
            print(f" Final Decision] {decision}\n")
            
        return results



if __name__ == "__main__":
    engine = Frankenstein()
    