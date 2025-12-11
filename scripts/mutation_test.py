import ast
import os
import shutil
import subprocess
import sys
import time

TARGET_FILE = "src/business/services/playback_service.py"
BACKUP_FILE = TARGET_FILE + ".bak"

class MutationVisitor(ast.NodeTransformer):
    def __init__(self):
        self.mutations = []
        self.current_mutation_idx = 0
        self.counter = 0

    def visit_Compare(self, node):
        # Mutate comparisons: < to >=, == to !=, etc.
        self.generic_visit(node)
        op_map = {
            ast.Lt: ast.GtE,
            ast.LtE: ast.Gt,
            ast.Gt: ast.LtE,
            ast.GtE: ast.Lt,
            ast.Eq: ast.NotEq,
            ast.NotEq: ast.Eq,
        }
        
        current_op_type = type(node.ops[0])
        if current_op_type in op_map:
             self.mutations.append((node, op_map[current_op_type]))
             if self.counter == self.current_mutation_idx:
                 print(f"  Mutation {self.counter}: Changing {current_op_type.__name__} to {op_map[current_op_type].__name__} at line {node.lineno}")
                 new_op = op_map[current_op_type]()
                 node.ops = [new_op]
             self.counter += 1
        return node
        
    def visit_BinOp(self, node):
        # Mutate binary ops: + to -, * to /
        self.generic_visit(node)
        op_map = {
             ast.Add: ast.Sub,
             ast.Sub: ast.Add,
             ast.Mult: ast.Div,
             ast.Div: ast.Mult,
        }
        current_op_type = type(node.op)
        if current_op_type in op_map:
             self.mutations.append((node, op_map[current_op_type]))
             if self.counter == self.current_mutation_idx:
                 print(f"  Mutation {self.counter}: Changing {current_op_type.__name__} to {op_map[current_op_type].__name__} at line {node.lineno}")
                 new_op = op_map[current_op_type]()
                 node.op = new_op
             self.counter += 1
        return node

    def visit_Constant(self, node):
        # Mutate numbers
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
             self.mutations.append(node)
             if self.counter == self.current_mutation_idx:
                 original = node.value
                 # Simple mutation: add 1
                 node.value = original + 1
                 print(f"  Mutation {self.counter}: Changing Constant {original} to {node.value} at line {node.lineno}")
             self.counter += 1
        return node

def count_mutations():
    with open(TARGET_FILE, "r") as f:
        tree = ast.parse(f.read())
    visitor = MutationVisitor()
    visitor.current_mutation_idx = -1 # Don't mutate, just count
    visitor.visit(tree)
    return len(visitor.mutations)

def apply_mutation(idx):
    with open(TARGET_FILE, "r") as f:
        tree = ast.parse(f.read())
    visitor = MutationVisitor()
    visitor.current_mutation_idx = idx
    visitor.visit(tree)
    
    # Write back
    with open(TARGET_FILE, "w") as f:
        f.write(ast.unparse(tree))

def run_tests():
    # Run only unit tests for speed, specifically the service one if possible, but let's run all unit tests to be safe
    # If a mutation in service breaks integration test, that counts too.
    cmd = [sys.executable, "-m", "pytest", "tests/unit", "-x", "-q", "--tb=no"]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0

def main():
    if len(sys.argv) < 2:
        print("Usage: python mutation_test.py <target_file>")
        return

    global TARGET_FILE, BACKUP_FILE
    TARGET_FILE = sys.argv[1]
    BACKUP_FILE = TARGET_FILE + ".bak"

    if not os.path.exists(TARGET_FILE):
        print(f"Error: File {TARGET_FILE} not found.")
        return

    print(f"Targeting: {TARGET_FILE}")
    
    # 1. Verify baseline
    print("Verifying baseline (tests should pass)...")
    if not run_tests():
        print("Baseline tests failed! Aborting.")
        return

    # 2. Count mutations
    total_mutations = count_mutations()
    print(f"Found {total_mutations} possible mutations.")
    
    # 3. Backup
    shutil.copy2(TARGET_FILE, BACKUP_FILE)
    
    killed = 0
    survived = 0
    timeout = 0
    
    try:
        for i in range(total_mutations):
            print(f"\n[Mutant {i+1}/{total_mutations}]")
            # Restore
            shutil.copy2(BACKUP_FILE, TARGET_FILE)
            
            # Apply
            apply_mutation(i)
            
            # Test
            start_time = time.time()
            passed = run_tests()
            duration = time.time() - start_time
            
            if passed:
                print(f"[SURVIVED] Mutant SURVIVED! (Tests passed despite mutation)")
                survived += 1
            else:
                print(f"[KILLED] Mutant KILLED! (Tests failed)")
                killed += 1
                
    except KeyboardInterrupt:
        print("\nAborted by user.")
    finally:
        # Restore original
        if os.path.exists(BACKUP_FILE):
            shutil.copy2(BACKUP_FILE, TARGET_FILE)
            os.remove(BACKUP_FILE)
        
        score = (killed / total_mutations) * 100 if total_mutations else 0
        print("\n" + "="*30)
        print("Mutation Testing Results")
        print("="*30)
        print(f"File: {TARGET_FILE}")
        print(f"Total Mutants: {total_mutations}")
        print(f"Killed: {killed}")
        print(f"Survived: {survived}")
        print(f"Mutation Score: {score:.2f}%")

if __name__ == "__main__":
    main()
