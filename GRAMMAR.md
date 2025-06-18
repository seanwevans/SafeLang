# SafeLang Grammar

This document describes the core grammar of SafeLang using an EBNF-style notation.
It is not a full formal specification but reflects the constructs supported by the
demo parser and examples.

```
program        ::= { statement }

statement      ::= function_decl
                 | call_expr ';'
                 | const_decl ';'
                 | import_stmt ';'

function_decl  ::= [ "@init" ] "function" string_lit "{" function_body "}"

function_body  ::= time_decl newline
                   space_decl newline
                   consume_block newline
                   { inner_statement newline }
                   emit_block

inner_statement ::= assign_expr ';'
                  | if_stmt
                  | loop_stmt
                  | match_stmt

# attributes

time_decl      ::= "@time" integer "ns"
space_decl     ::= "@space" integer "B"

consume_block  ::= "consume" "{" { param_decl newline } "}"
emit_block     ::= "emit" "{" { param_decl newline } "}"

param_decl     ::= type "(" identifier ")" range_comment

range_comment  ::= '#' '[' number ',' number ']'

# statements

if_stmt        ::= "if" expr newline
                     { inner_statement newline }
                   [ "else" newline { inner_statement newline } ]

loop_stmt      ::= "loop" '(' identifier '=' expr '..' expr ')' newline
                    { inner_statement newline }

match_stmt     ::= "match" expr newline
                    { 'case' identifier '=>' { inner_statement newline } }

assign_expr    ::= identifier '=' expr

call_expr      ::= identifier '(' [ expr { ',' expr } ] ')'

const_decl     ::= 'const' identifier '=' literal
import_stmt    ::= 'import' string_lit

expr           ::= literal
                 | identifier
                 | call_expr
                 | expr operator expr

literal        ::= number | string_lit
operator       ::= '+' | '-' | '*' | '/' | '%'

identifier     ::= /[A-Za-z_][A-Za-z0-9_]*/
string_lit     ::= '"' { any_char_no_quote } '"'
number         ::= /[0-9]+(\.[0-9]+)?/
newline        ::= /\n/
```

Comments starting with `!`, `//`, `/* */`, or `#` are ignored by the parser.
The grammar intentionally omits precedence and secondary constructs for
brevity.
