Implement a Prolog-like logic programming engine with unification and backtracking.

Create an executable at /app/logic that interprets a logic program and answers queries.

Usage: /app/logic <program.pl>
       /app/logic -q <query> <program.pl>   (run single query)

=== SYNTAX ===

Terms:
  atom          : Lowercase identifiers (foo, bar, nil)
  Variable      : Uppercase identifiers or _ (X, Y, _Temp, _)
  123           : Integer literal
  "hello"       : String literal
  [1, 2, 3]     : List literal
  [H|T]         : List with head H and tail T (cons pattern)
  []            : Empty list
  f(X, Y)       : Compound term (functor with arguments)
  (A, B)        : Tuple/pair

Facts:
  parent(tom, bob).     : tom is parent of bob
  likes(mary, pizza).   : mary likes pizza

Rules:
  grandparent(X, Z) :- parent(X, Y), parent(Y, Z).
  ancestor(X, Y) :- parent(X, Y).
  ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).

Queries (in REPL or with -q):
  ?- parent(tom, X).    : Find X where tom is parent of X
  ?- likes(Who, What).  : Find all who likes what

=== BUILT-IN PREDICATES ===

Unification:
  X = Y         : Unify X with Y
  X \= Y        : X and Y do not unify (succeeds if unification fails)

Comparison (built-in, for ground numeric terms):
  X < Y         : Less than
  X > Y         : Greater than  
  X =< Y        : Less than or equal
  X >= Y        : Greater than or equal

List operations:
  length(List, N)        : N is length of List
  append(L1, L2, L3)     : L3 is L1 appended with L2
  member(X, List)        : X is a member of List

Control:
  true          : Always succeeds
  false / fail  : Always fails
  !             : Cut (commit to current choice, prune backtracking)
  not(Goal)     : Negation as failure
  \+ Goal       : Same as not(Goal) (must implement both)
  (A ; B)       : Disjunction (A or B)

I/O:
  write(X)      : Write X to stdout (no newline)
  writeln(X)    : Write X with newline

Meta:
  ground(X)                  : Succeeds if X is fully instantiated
  var(X)                     : Succeeds if X is unbound variable
  nonvar(X)                  : Succeeds if X is not an unbound variable
  atom(X)                    : Succeeds if X is an atom
  number(X)                  : Succeeds if X is a number

Findall:
  findall(Template, Goal, List) : Collect all solutions

=== OUTPUT FORMAT ===

For each solution found, print variable bindings with spaces around equals:
  X = value, Y = value.
  (correct: "X = 1", incorrect: "X=1" or "X= 1")

Lists must be formatted with spaces after commas:
  [1, 2, 3] (correct)
  [1,2,3]   (incorrect)

If no more solutions, print:
  false.

For ground queries (no variables), print:
  true.
or
  false.

For -q mode with single query, print all solutions then "false." when done.

=== ERROR HANDLING ===
Print "ERROR: <message>" (case-insensitive) and exit with code 1 for:
  - Undefined predicate (when called)

=== EXAMPLES ===

Program (family.pl):
```
parent(tom, bob).
parent(tom, liz).
parent(bob, ann).

grandparent(X, Z) :- parent(X, Y), parent(Y, Z).
```

$ /app/logic -q "grandparent(tom, Who)" family.pl
Who = ann.
false.

$ /app/logic -q "parent(tom, X)" family.pl
X = bob.
X = liz.
false.

=== REQUIREMENTS ===
1. Implement proper unification with occurs check
2. Implement backtracking via choice points
3. Handle cut (!) correctly - prunes choice points
4. Support negation as failure
5. Implement all listed built-in predicates
6. Handle infinite/circular terms correctly (occurs check)
7. Parse and execute multi-clause predicates

