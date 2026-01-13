#!/usr/bin/env python3
import os
import subprocess

SAT_DIR = os.path.join(os.path.dirname(__file__), '../benchmarks/SAT-benchmarks')

sat_count = 0
unsat_count = 0
error_count = 0
total = 0

for fname in os.listdir(SAT_DIR):
	if not fname.endswith('.cnf'):
		continue
	fpath = os.path.join(SAT_DIR, fname)
	try:
		result = subprocess.run(['minisat', fpath], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
		total += 1
		if result.returncode == 10:
			sat_count += 1
		elif result.returncode == 20:
			unsat_count += 1
		else:
			error_count += 1
			print(f"[ERROR] {fname}: minisat returned {result.returncode}")
	except Exception as e:
		error_count += 1
		print(f"[EXCEPTION] {fname}: {e}")

print(f"Total: {total}")
print(f"SAT: {sat_count}")
print(f"UNSAT: {unsat_count}")
print(f"ERRORS: {error_count}")
