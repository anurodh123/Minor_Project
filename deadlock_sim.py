class BankersAlgorithm:
    def __init__(self, num_processes, num_resources, available, max_matrix, allocation):
        self.num_processes = num_processes
        self.num_resources = num_resources
        
        # Core Matrices / Arrays
        self.available = list(available)
        self.max_matrix = [list(row) for row in max_matrix]
        self.allocation = [list(row) for row in allocation]
        
        # Dynamically calculate the Need Matrix
        self.need = []
        self.calculate_need_matrix()

    def calculate_need_matrix(self):
        self.need = []
        for i in range(self.num_processes):
            row = []
            for j in range(self.num_resources):
                row.append(self.max_matrix[i][j] - self.allocation[i][j])
            self.need.append(row)

    def check_safety_state(self):
        # Step 1: Initialize Work and Finish arrays
        work = list(self.available)
        finish = [False] * self.num_processes
        safe_sequence = []

        # Loop until we find a sequence or get stuck
        while len(safe_sequence) < self.num_processes:
            found_executable_process = False
            
            # Step 2: Find an unfinished process whose needs can be met by 'work'
            for i in range(self.num_processes):
                if not finish[i]:
                    can_execute = True
                    for j in range(self.num_resources):
                        if self.need[i][j] > work[j]:
                            can_execute = False
                            break
                    
                    # Step 3: If it can run, simulate its completion and reclaim resources
                    if can_execute:
                        for j in range(self.num_resources):
                            work[j] += self.allocation[i][j]
                        
                        finish[i] = True
                        safe_sequence.append(f"P{i}")
                        found_executable_process = True
                        break  # Restart the scan loop from P0
            
            # If we scanned everything and found nothing executable -> Deadlock condition
            if not found_executable_process:
                return False, []

        # Step 4: If all finished, system is safe
        return True, safe_sequence

    def request_resources(self, proc_id, request_array):
        # Check 1: Request vs Need
        for j in range(self.num_resources):
            if request_array[j] > self.need[proc_id][j]:
                return False, f"Error: Process P{proc_id} requested more than its declared maximum need!"

        # Check 2: Request vs Available
        for j in range(self.num_resources):
            if request_array[j] > self.available[j]:
                return False, f"Status: Process P{proc_id} must wait. Not enough resources available right now."

        # Check 3: "What-If" Allocation (Tentative changes)
        for j in range(self.num_resources):
            self.available[j] -= request_array[j]
            self.allocation[proc_id][j] += request_array[j]
            self.need[proc_id][j] -= request_array[j]

        # Check 4: Evaluate safety of tentative state
        is_safe, seq = self.check_safety_state()

        if is_safe:
            return True, f"Success: Request granted safely! Safe Sequence: {' -> '.join(seq)}"
        else:
            # Rollback if it triggers an unsafe state
            for j in range(self.num_resources):
                self.available[j] += request_array[j]
                self.allocation[proc_id][j] -= request_array[j]
                self.need[proc_id][j] += request_array[j]
            return False, "Denied: Request rejected because it leads to an Unsafe State (Potential Deadlock)."


if __name__ == "__main__":
    print("=== Initializing Banker's Algorithm Test ===")
    
    # Mock data setup
    p_count = 5
    r_count = 3
    init_avail = [3, 3, 2]
    
    max_demand = [
        [7, 5, 3],  # P0
        [3, 2, 2],  # P1
        [9, 0, 2],  # P2
        [2, 2, 2],  # P3
        [4, 3, 3]   # P4
    ]
    
    current_alloc = [
        [0, 1, 0],  # P0
        [2, 0, 0],  # P1
        [3, 0, 2],  # P2
        [2, 1, 1],  # P3
        [0, 0, 2]   # P4
    ]

    # Instantiate the engine
    sim = BankersAlgorithm(p_count, r_count, init_avail, max_demand, current_alloc)
    
    # 1. Test Initial Safety
    safe, sequence = sim.check_safety_state()
    print(f"Initial State Safe? {safe}")
    if safe:
        print(f"Initial Safe Sequence: {sequence}")
        
    # 2. Test a Safe Request (P1 requests [1, 0, 2])
    print("\n--- Simulating Request: P1 requests [1, 0, 2] ---")
    success, message = sim.request_resources(1, [1, 0, 2])
    print(message)
    
    # 3. Test an Unsafe Request (P4 requests [3, 3, 0])
    print("\n--- Simulating Request: P4 requests [3, 3, 0] ---")
    success, message = sim.request_resources(4, [3, 3, 0])
    print(message)