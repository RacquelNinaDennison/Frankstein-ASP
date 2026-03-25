import clingo
import asyncio

class Frankenstein:
    def __init__(self):
        self.finance_optimization_file = "finance_optimization.lp"
        self.base_route_file = "base_route.lp"
        self.ceiling_route_file = "ceiling_route.lp"

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


    def _run_clingo_sync(self, route_file, app_data_string):
        """
        The actual blocking Clingo solver logic. 
        We will push this into a background thread so it doesn't block Python.
        """
        ctl = clingo.Control()
        # In a real setup, you would load the route file and inject the facts string here:
        # ctl.load(route_file)
        # ctl.add("base", [], app_data_string)
        # ctl.ground([("base", [])])
        
        passed = False
        def on_model(model):
            nonlocal passed
            if "route_passed" in [str(atom) for atom in model.symbols(shown=True)]:
                passed = True
                
        # ctl.solve(on_model=on_model)
        
        # MOCK RETURN FOR TESTING PURPOSES:
        if "ceiling" in route_file: return False # Let's pretend it failed Ceiling
        if "finance" in route_file: return True  # Let's pretend it passed Finance
        return True

    # ---------------------------------------------------------
    # THE ASYNC WRAPPERS
    # ---------------------------------------------------------
    async def evaluate_ceiling(self, app_data):
        return await asyncio.to_thread(self._run_clingo_sync, self.ceiling_route_file, app_data)

    async def evaluate_finance(self, app_data, optimized_weights):
        # We would inject the weights into the app_data string here before solving
        return await asyncio.to_thread(self._run_clingo_sync(self.finance_route_file, app_data))

    async def evaluate_base(self, app_data):
        return await asyncio.to_thread(self._run_clingo_sync, self.base_route_file, app_data)

    # ---------------------------------------------------------
    # THE MAIN EXECUTION ENGINE
    # ---------------------------------------------------------
    async def pass_applications(self, list_of_application_data, optimized_weights):
        """
        Evaluates parallel routes and applies prioritization logic.
        """
        results = {}
        
        for app_id, app_data in list_of_application_data.items():
            print(f"Evaluating App {app_id} in parallel...")
            
            # 1. FIRE THEM OFF AT THE SAME TIME
            # We create tasks for all three routes to start simultaneously
            ceiling_task = self.evaluate_ceiling(app_data)
            finance_task = self.evaluate_finance(app_data, optimized_weights)
            base_task = self.evaluate_base(app_data)
            
            # 2. WAIT FOR ALL TO FINISH & GATHER RESULTS
            # Python pauses here until all three Clingo solvers are done crunching
            ceiling_pass, finance_pass, base_pass = await asyncio.gather(
                ceiling_task, finance_task, base_task
            )
            
            print(f"  [Scores] Ceiling: {ceiling_pass} | Finance: {finance_pass} | Base: {base_pass}")
            
            # 3. APPLY PRIORITIZATION LOGIC 
            # (Ceiling -> Finance -> Base -> Refer to UW)
            if ceiling_pass:
                decision = "APPROVED (Ceiling)"
            elif finance_pass:
                decision = "APPROVED (Finance)"
            elif base_pass:
                decision = "APPROVED (Base)"
            else:
                decision = "REJECTED (Refer to Underwriter)"
                
            results[app_id] = decision
            print(f"  [Final Decision] {decision}\n")
            
        return results


# --- Test Drive ---
if __name__ == "__main__":
    engine = Frankenstein()
    
    # Assuming you have your mock data saved in 'historical_data.lp'
    # weights = engine.run_optimizations("historical_data.lp")