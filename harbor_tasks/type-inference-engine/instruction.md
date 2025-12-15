Implement a Hindley-Milner type inference engine for a functional programming language.

Create an executable at /app/infer that reads an expression file and outputs its inferred type.

Usage: /app/infer <program.ml>

=== SYNTAX ===
The language supports:

Literals:
  42                    : integer literal
  3.14                  : float literal  
  true / false          : boolean literals
  "hello"               : string literal
  ()                    : unit value

Variables:
  x, foo, myVar         : identifiers (alphanumeric, starting with lowercase)

Functions:
  fn x -> expr          : lambda (anonymous function)
  fn x y z -> expr      : multi-param lambda (curried)

Application:
  f x                   : function application
  f x y                 : multi-arg application (left-associative)

Let bindings:
  let x = e1 in e2      : local binding (with let-polymorphism)
  let rec f = e1 in e2  : recursive binding

Conditionals:
  if e1 then e2 else e3

Binary operators (infix, standard precedence):
  +, -, *, /            : arithmetic (int -> int -> int) or (float -> float -> float)
  ==, !=, <, >, <=, >=  : comparison (returns bool)
  &&, ||                : logical (bool -> bool -> bool)
  ^                     : string concatenation (string -> string -> string)

Tuples:
  (e1, e2)              : pair
  (e1, e2, e3)          : triple (and larger)
  fst, snd              : built-in pair accessors

Lists:
  []                    : empty list (polymorphic)
  [e1, e2, e3]          : list literal
  e1 :: e2              : cons (prepend to list)
  hd, tl                : built-in list head/tail

=== TYPE SYNTAX ===
int, float, bool, string, unit       : base types
'a, 'b, 'c                           : type variables
t1 -> t2                             : function type
t1 * t2                              : tuple type
t list                               : list type
(t)                                  : parenthesized type

=== OUTPUT FORMAT ===
Print the inferred type on a single line. For polymorphic types, use 'a, 'b, etc.
Generalize let-bound variables (let-polymorphism).

Examples:
  Input: 42
  Output: int

  Input: fn x -> x
  Output: 'a -> 'a

  Input: fn x -> x + 1
  Output: int -> int

  Input: let id = fn x -> x in (id 1, id true)
  Output: int * bool

  Input: fn f -> fn x -> f (f x)
  Output: ('a -> 'a) -> 'a -> 'a

  Input: []
  Output: 'a list

  Input: fn x -> [x]
  Output: 'a -> 'a list

=== ERROR HANDLING ===
Print "TYPE ERROR: <message>" and exit with code 1 for:
  - Unification failure (e.g., int vs bool)
  - Occurs check failure (infinite types)
  - Unbound variable
  - Arity mismatch

Print "PARSE ERROR: <message>" and exit with code 1 for syntax errors.

=== REQUIREMENTS ===
1. Implement Algorithm W (or equivalent) for type inference
2. Support let-polymorphism (generalize at let bindings)
3. Handle recursive functions with proper typing
4. Implement unification with occurs check
5. Normalize type variable names in output ('a, 'b, 'c in order of first occurrence)

