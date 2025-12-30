from z3 import *

solver = Solver()

if solver.check() == sat:
    print("Satisfiable")
else:
    print("Unsatisfiable")