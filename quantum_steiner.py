# quantum_steiner.py
# Minimal hybrid demo: classical candidate generation for Steiner-like subproblems
# + Grover search (oracle built from the classically-determined best index)


import itertools
import math
import networkx as nx
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

G = nx.Graph()
G.add_weighted_edges_from([
    (0, 1, 2),
    (1, 2, 2),
    (0, 2, 3),
    (2, 3, 1),
    (1, 3, 4)
])
terminals = {0, 3}  

nodes = list(G.nodes())
candidates = []
for r in range(1, len(nodes) + 1):
    for comb in itertools.combinations(nodes, r):
        s = set(comb)
        if terminals.issubset(s):
          
            sub = G.subgraph(s)
            if nx.is_connected(sub):
                tree = nx.minimum_spanning_tree(sub)
                cost = tree.size(weight="weight")
                candidates.append( (tuple(sorted(comb)), cost) )


candidates.sort(key=lambda x: x[1])

if len(candidates) == 0:
    print("No feasible candidates found (increase graph connectivity).")
    exit(0)

print("Candidates (subset, cost):")
for i, (subset, cost) in enumerate(candidates):
    print(f"  {i:2d}: {subset}, cost = {cost}")

best_index = 0  # because we sorted by cost
best_subset, best_cost = candidates[best_index]
print("\nClassical best candidate index:", best_index, "subset:", best_subset, "cost:", best_cost)


def build_grover_circuit(n_qubits, target_index, n_iterations=1):
    """
    n_qubits: number of qubits to represent candidates (2^n_qubits >= N)
    target_index: integer index to mark
    n_iterations: number of Grover iterations to apply (1 is fine for small N)
    """
    
    anc = n_qubits
    qc = QuantumCircuit(n_qubits + 1, n_qubits)  
    qc.h(range(n_qubits))

    qc.x(anc)
    qc.h(anc)

    def apply_oracle():
        
        bitstr = f"{target_index:0{n_qubits}b}"

        for i, b in enumerate(bitstr[::-1]):  
            if b == '0':
                qc.x(i)

        controls = list(range(n_qubits))
        qc.mcx(controls, anc) 

        for i, b in enumerate(bitstr[::-1]):
            if b == '0':
                qc.x(i)
    def diffusion():
        qc.h(range(n_qubits))
        qc.x(range(n_qubits))

    
        qc.x(range(n_qubits))
        qc.mcx(list(range(n_qubits)), anc)
        qc.x(range(n_qubits))

        qc.x(range(n_qubits))
        qc.h(range(n_qubits))

    for _ in range(n_iterations):
        apply_oracle()
        diffusion()

    qc.measure(range(n_qubits), range(n_qubits))
    return qc

N = len(candidates)
n_qubits = math.ceil(math.log2(max(1, N)))
if n_qubits == 0:
    n_qubits = 1

grover_iterations = 1

qc = build_grover_circuit(n_qubits, target_index=best_index, n_iterations=grover_iterations)

print("\nGrover circuit built with", n_qubits, "qubits (can encode up to", 2**n_qubits, "states).")

sim = AerSimulator()

tqc = transpile(qc, sim)

job = sim.run(tqc, shots=1024)
result = job.result()
counts = result.get_counts()

print("\nRaw measurement counts:", counts)

index_counts = {}
for bitstr, c in counts.items():
    
    idx = int(bitstr[::-1], 2)  
    if idx < N:
        index_counts[idx] = index_counts.get(idx, 0) + c

print("\nCounts for valid candidate indices:", index_counts)

if len(index_counts) == 0:
    print("No valid candidate measurements (increase shots or reduce 2^n gap).")
else:
    top_index = max(index_counts, key=index_counts.get)
    print("\nGrover top index:", top_index, "subset:", candidates[top_index][0], "classical cost:", candidates[top_index][1])


print("\nDemo complete. This shows Grover amplifying the (classically known) best candidate among small candidates.")
print("In a full hybrid algorithm you would build oracles that compare costs or mark items under a threshold,")
print("and use Grover/Amplitude Amplification inside the DP recurrence instead of a naive search.")
