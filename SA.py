
from typing import Dict, List, Set, Tuple, FrozenSet
from collections import defaultdict

# ================ Constants ================
EPSILON = 'ε'
END_MARKER = '$'

# ================ Grammar Input ================
def read_grammar() -> Tuple[Dict[str, List[List[str]]], str]:
    """
    Read grammar rules from user input
    
    Returns:
        Tuple[grammar dict, start symbol]
    """
    grammar = defaultdict(list)
    start = None
    
    print("\n" + "="*60)
    print("Enter grammar rules (format: S -> a B | c)")
    print("Type 'done' to finish")
    print("="*60 + "\n")
    
    while True:
        try:
            line = input("Rule > ").strip()
            
            if line.lower() == "done":
                if not grammar:
                    print("Warning: At least one rule is required!")
                    continue
                break
            
            if not line or "->" not in line:
                print("Invalid format! Use: A -> B C | d")
                continue
            
            # Parse the rule
            left, right = line.split("->", 1)
            left = left.strip()
            
            if not left:
                print("Left side cannot be empty!")
                continue
            
            # Set start symbol
            if start is None:
                start = left
            
            # Parse alternatives
            alternatives = [alt.strip().split() for alt in right.split("|")]
            alternatives = [alt if alt else [EPSILON] for alt in alternatives]
            
            grammar[left].extend(alternatives)
            print(f"✓ Added: {left} -> {' | '.join(' '.join(alt) for alt in alternatives)}")
            
        except KeyboardInterrupt:
            print("\n\nCancelled!")
            return None, None
        except Exception as e:
            print(f"Error: {e}")
    
    return dict(grammar), start


# ================ FIRST Set Computation ================
def compute_first(grammar: Dict[str, List[List[str]]]) -> Dict[str, Set[str]]:
    """
    Compute FIRST sets for all non-terminals
    """
    FIRST = {nt: set() for nt in grammar}
    changed = True
    
    while changed:
        changed = False
        
        for A in grammar:
            for production in grammar[A]:
                for symbol in production:
                    # Terminal or epsilon
                    if symbol not in grammar:
                        if symbol not in FIRST[A]:
                            FIRST[A].add(symbol)
                            changed = True
                        break
                    
                    # Non-terminal
                    old_size = len(FIRST[A])
                    FIRST[A] |= (FIRST[symbol] - {EPSILON})
                    
                    if len(FIRST[A]) != old_size:
                        changed = True
                    
                    # Stop if doesn't derive epsilon
                    if EPSILON not in FIRST[symbol]:
                        break
                else:
                    # All symbols derive epsilon
                    if EPSILON not in FIRST[A]:
                        FIRST[A].add(EPSILON)
                        changed = True
    
    return FIRST


# ================ FOLLOW Set Computation ================
def compute_follow(grammar: Dict[str, List[List[str]]], 
                   FIRST: Dict[str, Set[str]], 
                   start: str) -> Dict[str, Set[str]]:
    """
    Compute FOLLOW sets for all non-terminals
    """
    FOLLOW = {nt: set() for nt in grammar}
    FOLLOW[start].add(END_MARKER)
    changed = True
    
    while changed:
        changed = False
        
        for A in grammar:
            for production in grammar[A]:
                for i, B in enumerate(production):
                    # Skip terminals
                    if B not in grammar:
                        continue
                    
                    # Get beta (rest of production after B)
                    beta = production[i+1:]
                    first_beta = compute_first_of_sequence(beta, FIRST, grammar)
                    
                    old_size = len(FOLLOW[B])
                    FOLLOW[B] |= (first_beta - {EPSILON})
                    
                    # If beta derives epsilon or is empty, add FOLLOW(A)
                    if EPSILON in first_beta or not beta:
                        FOLLOW[B] |= FOLLOW[A]
                    
                    if len(FOLLOW[B]) != old_size:
                        changed = True
    
    return FOLLOW


def compute_first_of_sequence(sequence: List[str], 
                              FIRST: Dict[str, Set[str]], 
                              grammar: Dict[str, List[List[str]]]) -> Set[str]:
    """
    Compute FIRST set of a sequence of symbols
    """
    result = set()
    
    for symbol in sequence:
        if symbol not in grammar:
            # Terminal
            result.add(symbol)
            return result
        
        # Non-terminal
        result |= (FIRST[symbol] - {EPSILON})
        
        if EPSILON not in FIRST[symbol]:
            return result
    
    # All symbols derive epsilon
    result.add(EPSILON)
    return result


# ================ LL(1) Parsing Table ================
def build_ll1_table(grammar: Dict[str, List[List[str]]], 
                    FIRST: Dict[str, Set[str]], 
                    FOLLOW: Dict[str, Set[str]]) -> Dict[str, Dict[str, List[str]]]:
    """
    Build LL(1) parsing table
    """
    table = {nt: {} for nt in grammar}
    conflicts = []
    
    for A in grammar:
        for production in grammar[A]:
            first_set = compute_first_of_sequence(production, FIRST, grammar)
            
            # Add entries for terminals in FIRST
            for terminal in (first_set - {EPSILON}):
                if terminal in table[A]:
                    conflicts.append(f"Conflict at [{A}, {terminal}]")
                table[A][terminal] = production
            
            # If epsilon in FIRST, add entries for FOLLOW
            if EPSILON in first_set:
                for terminal in FOLLOW[A]:
                    if terminal in table[A]:
                        conflicts.append(f"Conflict at [{A}, {terminal}]")
                    table[A][terminal] = production
    
    if conflicts:
        print("\n⚠️  WARNING: Grammar is not LL(1)!")
        for conflict in conflicts:
            print(f"   {conflict}")
    
    return table


def print_ll1_table(table: Dict[str, Dict[str, List[str]]]):
    """
    Print LL(1) parsing table in formatted output
    """
    print("\n" + "="*80)
    print("LL(1) PARSING TABLE")
    print("="*80)
    
    # Get all terminals
    terminals = sorted({t for nt in table for t in table[nt]})
    
    # Header
    header = f"{'NT':^12s} | " + " | ".join(f"{t:^15s}" for t in terminals)
    print(header)
    print("-" * len(header))
    
    # Rows
    for nt in sorted(table.keys()):
        row = [f"{nt:^12s}"]
        for t in terminals:
            if t in table[nt]:
                prod = " ".join(table[nt][t])
                row.append(f"{prod:^15s}")
            else:
                row.append(f"{'':^15s}")
        print(" | ".join(row))
    
    print("="*80 + "\n")


# ================ SLR(1) Parser ================
def build_slr_parser(grammar: Dict[str, List[List[str]]], 
                     FIRST: Dict[str, Set[str]], 
                     FOLLOW: Dict[str, Set[str]], 
                     start: str) -> Tuple[Dict, Dict, List, List[str]]:
    """
    Build SLR(1) parsing tables
    """
    # Augment grammar
    aug_start = start + "'"
    grammar = dict(grammar)
    grammar[aug_start] = [[start]]
    FOLLOW[aug_start] = set()
    
    def closure(items: Set[Tuple]) -> FrozenSet:
        """Compute closure of item set"""
        new_items = set(items)
        changed = True
        
        while changed:
            changed = False
            for (A, production, dot) in list(new_items):
                if dot < len(production):
                    B = production[dot]
                    if B in grammar:
                        for rule in grammar[B]:
                            item = (B, tuple(rule), 0)
                            if item not in new_items:
                                new_items.add(item)
                                changed = True
        
        return frozenset(new_items)
    
    def goto(items: FrozenSet, symbol: str) -> FrozenSet:
        """Compute goto(items, symbol)"""
        moved = {
            (A, production, dot+1) 
            for (A, production, dot) in items 
            if dot < len(production) and production[dot] == symbol
        }
        return closure(moved) if moved else frozenset()
    
    # Build canonical collection
    start_item = closure({(aug_start, tuple(grammar[aug_start][0]), 0)})
    states = [start_item]
    transitions = {}
    
    while True:
        added = False
        for i, state in enumerate(states):
            symbols = {
                production[dot] 
                for (A, production, dot) in state 
                if dot < len(production)
            }
            
            for symbol in symbols:
                next_state = goto(state, symbol)
                if next_state and next_state not in states:
                    states.append(next_state)
                    added = True
                if next_state:
                    transitions[(i, symbol)] = states.index(next_state)
        
        if not added:
            break
    
    # Build ACTION and GOTO tables
    terminals = {
        s for nt in grammar for prod in grammar[nt] 
        for s in prod if s not in grammar and s != EPSILON
    }
    terminals.add(END_MARKER)
    
    ACTION = {i: {} for i in range(len(states))}
    GOTO = {i: {} for i in range(len(states))}
    conflicts = []
    
    for i, state in enumerate(states):
        for (A, production, dot) in state:
            if dot < len(production):
                # Shift or goto
                symbol = production[dot]
                next_state = transitions.get((i, symbol))
                
                if symbol in terminals:
                    action = f"s{next_state}"
                    if symbol in ACTION[i] and ACTION[i][symbol] != action:
                        conflicts.append(f"Shift-Reduce conflict in state {i} on '{symbol}'")
                    ACTION[i][symbol] = action
                else:
                    GOTO[i][symbol] = next_state
            else:
                # Reduce or accept
                if A == aug_start:
                    ACTION[i][END_MARKER] = 'acc'
                else:
                    prod_str = " ".join(production) if production else EPSILON
                    action = f"r({A} → {prod_str})"
                    
                    for terminal in FOLLOW[A]:
                        if terminal in ACTION[i] and ACTION[i][terminal] != action:
                            conflicts.append(f"Reduce-Reduce conflict in state {i} on '{terminal}'")
                        ACTION[i][terminal] = action
    
    if conflicts:
        print("\n⚠️  WARNING: Grammar is not SLR(1)!")
        for conflict in conflicts:
            print(f"   {conflict}")
    
    return ACTION, GOTO, states, sorted(terminals)


def print_slr_tables(ACTION: Dict, GOTO: Dict, terminals: List[str]):
    """
    Print SLR(1) ACTION and GOTO tables
    """
    print("\n" + "="*80)
    print("SLR(1) ACTION TABLE")
    print("="*80)
    
    # ACTION table
    header = f"{'State':^8s} | " + " | ".join(f"{t:^12s}" for t in terminals)
    print(header)
    print("-" * len(header))
    
    for state in sorted(ACTION.keys()):
        row = [f"{state:^8d}"]
        for t in terminals:
            row.append(f"{ACTION[state].get(t, ''):^12s}")
        print(" | ".join(row))
    
    # GOTO table
    non_terminals = sorted({nt for state in GOTO for nt in GOTO[state]})
    
    if non_terminals:
        print("\n" + "="*80)
        print("SLR(1) GOTO TABLE")
        print("="*80)
        
        header = f"{'State':^8s} | " + " | ".join(f"{nt:^12s}" for nt in non_terminals)
        print(header)
        print("-" * len(header))
        
        for state in sorted(GOTO.keys()):
            row = [f"{state:^8d}"]
            for nt in non_terminals:
                val = GOTO[state].get(nt, '')
                row.append(f"{val:^12s}")
            print(" | ".join(row))
    
    print("="*80 + "\n")


# ================ Main Program ================
def print_sets(FIRST: Dict[str, Set[str]], FOLLOW: Dict[str, Set[str]]):
    """Print FIRST and FOLLOW sets"""
    print("\n" + "="*60)
    print("FIRST SETS")
    print("="*60)
    for nt in sorted(FIRST.keys()):
        print(f"FIRST({nt}) = {{{', '.join(sorted(FIRST[nt]))}}}")
    
    print("\n" + "="*60)
    print("FOLLOW SETS")
    print("="*60)
    for nt in sorted(FOLLOW.keys()):
        print(f"FOLLOW({nt}) = {{{', '.join(sorted(FOLLOW[nt]))}}}")
    print()


def main():
    """Main program"""
    print("\n" + "="*60)
    print("PARSER GENERATOR - LL(1) & SLR(1)")
    print("="*60)
    
    # Choose algorithm
    while True:
        algo = input("\nChoose algorithm (LL1 or SLR1): ").strip().upper()
        if algo in ["LL1", "SLR1", "LL(1)", "SLR(1)"]:
            algo = algo.replace("(", "").replace(")", "")
            break
        print("Invalid choice! Enter LL1 or SLR1")
    
    # Read grammar
    grammar, start = read_grammar()
    if grammar is None:
        return
    
    # Compute FIRST and FOLLOW
    FIRST = compute_first(grammar)
    FOLLOW = compute_follow(grammar, FIRST, start)
    
    # Display sets
    print_sets(FIRST, FOLLOW)
    
    # Build and display parsing table
    if algo == "LL1":
        table = build_ll1_table(grammar, FIRST, FOLLOW)
        print_ll1_table(table)
    else:
        ACTION, GOTO, states, terminals = build_slr_parser(grammar, FIRST, FOLLOW, start)
        print_slr_tables(ACTION, GOTO, terminals)
        print(f"\nTotal states: {len(states)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProgram terminated by user.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()