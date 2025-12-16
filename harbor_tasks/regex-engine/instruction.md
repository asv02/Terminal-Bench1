Implement a full-featured regular expression engine with advanced matching capabilities.

Create an executable at /app/regex that matches patterns against text.

Usage: /app/regex <pattern> <text>
       /app/regex -a <pattern> <text>    (find all matches, print each on new line)
       /app/regex -r <pattern> <replacement> <text>  (replace matches)

=== BASIC PATTERNS ===
.           : Match any single character (except newline)
\d          : Match digit [0-9]
\D          : Non-digit
\w          : Word character [a-zA-Z0-9_]
\W          : Non-word character
\s          : Whitespace [ \t\n\r\f]
\S          : Non-whitespace
\n, \t, \r  : Literal newline, tab, carriage return
\\          : Literal backslash
\.  \*  etc : Escaped metacharacters

=== CHARACTER CLASSES ===
[abc]       : Match a, b, or c
[^abc]      : Match anything except a, b, c
[a-z]       : Range (a through z)
[a-zA-Z0-9] : Multiple ranges
[]]         : Literal ] (must be first)
[-a]        : Literal - (must be first or last)

=== QUANTIFIERS ===
*           : Zero or more (greedy)
+           : One or more (greedy)
?           : Zero or one (greedy)
{n}         : Exactly n times
{n,}        : n or more times
{n,m}       : Between n and m times (inclusive)

=== ANCHORS ===
^           : Start of string (or line in multiline mode)
$           : End of string (or line in multiline mode)
\b          : Word boundary
\B          : Non-word boundary
\A          : Start of string only
\Z          : End of string only

=== GROUPS AND CAPTURING ===
(expr)      : Capturing group
(?:expr)    : Non-capturing group
(?P<name>expr) : Named capturing group
\1, \2      : Backreference to group 1, 2, etc.
(?P=name)   : Backreference to named group

=== ALTERNATION ===
a|b         : Match a or b
(ab|cd)     : Match ab or cd

=== LOOKAHEAD AND LOOKBEHIND ===
(?=expr)    : Positive lookahead (matches if expr matches ahead)
(?!expr)    : Negative lookahead (matches if expr does NOT match ahead)
(?<=expr)   : Positive lookbehind (matches if expr matches behind)
(?<!expr)   : Negative lookbehind (matches if expr does NOT match behind)

=== OUTPUT FORMAT ===
Default mode: Print "MATCH" if pattern matches anywhere in text, "NO MATCH" otherwise
              Exit code 0 for match, 1 for no match

-a mode: Print each match on a separate line (the matched text itself)
         If groups are present, print: match\tgroup1\tgroup2\t...

-r mode: Print the text with all matches replaced
         Use \1, \2 in replacement for backreferences

=== ERROR HANDLING ===
Print "REGEX ERROR: <message>" and exit with code 2 for:
  - Invalid pattern syntax
  - Unbalanced parentheses
  - Invalid backreference
  - Invalid quantifier

=== EXAMPLES ===
$ /app/regex "hello" "hello world"
MATCH

$ /app/regex "^[a-z]+$" "hello"
MATCH

$ /app/regex "\d{3}-\d{4}" "Call 555-1234"
MATCH

$ /app/regex -a "\w+" "hello world"
hello
world

$ /app/regex -a "(\w+)@(\w+)" "a@b c@d"
a@b	a	b
c@d	c	d

$ /app/regex "(\w+) \1" "hello hello"
MATCH

$ /app/regex "(?<=@)\w+" "@user"
MATCH

$ /app/regex -r "(\w+)" "[\1]" "hello world"
[hello] [world]

=== REQUIREMENTS ===
1. Implement backtracking regex engine (NFA or recursive backtracking)
2. Support all features listed above
3. Handle greedy quantifiers correctly
4. Implement proper lookahead and lookbehind
5. Support backreferences in both pattern and replacement
6. Handle edge cases: empty patterns, empty text, overlapping matches

