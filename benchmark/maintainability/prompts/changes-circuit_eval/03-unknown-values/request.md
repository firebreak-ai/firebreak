# Change request: unknown (`X`) values inside circuit files

Today a circuit file cannot contain the unknown value `X`. It is a `CircParseError`. `X` can only arrive as an input value, under `eval --mode 3val`. Users want to write circuits where some constant bits are unknown, and to see what every command makes of them.

After this change `X` is a legal constant in `.circ` and `.json` circuit files, and every command has a defined result for such a circuit.

Below, an **X circuit** is a circuit file that contains at least one literal with an `X` bit, anywhere in the file, used by an output or not. A circuit file with no such literal behaves exactly as it does today in every command.

## Literals

These forms are accepted wherever a literal is accepted today, in `.circ` files and in the `rhs` strings of `.json` files:

| Form | Example | Width | Bits (left is the most significant) |
|---|---|---|---|
| Scalar | `X` | 1 | X |
| Unsized binary | `0b1X0` | 3 | 1, X, 0 |
| Sized binary | `4'b1X0X` | 4 | 1, X, 0, X |

- The scalar form is the single uppercase letter `X` standing alone as an expression. It is always the literal, never a signal. A lowercase `x` standing alone is a signal name, as today.
- Inside binary digits `X` and `x` both mean an unknown bit: `0b1x0` equals `0b1X0`.
- Underscores are ignored as today: `0b1_X0` equals `0b1X0`.
- An `X` literal has the width shown and obeys every width rule as any other literal does. `y = 0b1X` for a 4-bit `y` is a `WidthMismatchError`.
- Hex and decimal literals cannot hold `X`. `0x1X`, `8'hXf` and `4'd1X` stay a `CircParseError`, in `.json` files too.

Not covered by this request, and left as they are: declaring a signal named `X`; a sized binary literal whose digit count differs from its size; `.bench` files, which have no literals.

## What an X bit evaluates to

Every operator treats an `X` bit by the 3-valued rules the product already has for `eval --mode 3val`: the tables for `NOT`, `BUF`, `AND`, `OR`, `XOR`, and the rules for `MUX`/`ITE`, `EQ` and the three reductions. `NAND`, `NOR` and `XNOR` are `NOT` of `AND`, `OR` and `XOR`. Indexing, slicing and concatenation carry each bit through unchanged, known or unknown.

This holds in every command that computes values, whichever mode was asked for. A result that depends on an `X` bit shows `X`. A result that does not, shows `0` or `1`: `AND(a, X)` is `0` when `a` is `0`.

Values that can hold `X` are written the way `eval --mode 3val` writes them today: a 1-bit value as `0`, `1` or `X`; a wider value as `0b` followed by exactly one digit per bit from `0`, `1`, `X`. `X` is always uppercase in output.

## Commands

The examples use this file, `demo.circ`:

```text
input a b[1:0]
output k y z[3:0]
wire t[1:0]
t = AND(b, 0b1x)
y = OR(a, X)
z = {t, 2'b0X}
k = 0
```

### `check`, `stats`, `dot`

They accept X circuits. An `X` literal counts as any other literal: it adds no dependency, it is category `BUF` when it is a whole right-hand side, and an assignment of only a literal has depth 1. So `stats` and `dot` give the same result for an X circuit as for the same file with every `X` bit replaced by `0`.

### `eval`

In `--mode 2val` (the default), input values are still only `0` and `1`; `--set a=X` is still an `InputValueParseError`. Outputs can now show `X`. The `mode` field of the JSON result stays `"2val"`.

```bash
$ circopt eval demo.circ --set a=0 --set b=0b11
k=0
y=X
z=0b1X0X
$ circopt eval demo.circ --set a=1 --set b=0b01 --json
{"ok":true,"command":"eval","mode":"2val","radix":"bin","outputs":[{"name":"k","msb":0,"lsb":0,"value":"0"},{"name":"y","msb":0,"lsb":0,"value":"1"},{"name":"z","msb":3,"lsb":0,"value":"0b0X0X"}]}
```

In `--mode 3val`, `X` literals and `X` input values combine by the same rules.

```bash
$ circopt eval demo.circ --mode 3val --set a=X --set b=0b1X
k=0
y=X
z=0b1X0X
```

**Radix.** Hex and decimal cannot show an unknown bit. For an X circuit, `eval` accepts only `--radix bin`, in both modes. `--radix hex` or `--radix dec` gives `RadixNotAllowedIn3ValError`, exit code 1. This depends only on the file being an X circuit, never on the input values or on whether the outputs of that run happen to be fully known.

```bash
$ circopt eval demo.circ --set a=1 --set b=0b01 --radix hex --json
{"ok":false,"command":"eval","exit_code":1,"error":{"type":"RadixNotAllowedIn3ValError","message":"...","file":null,"line":null,"col":null}}
# exit 1
```

### `truth-table`

Rows are the same as today: every combination of `0` and `1` on the inputs. Output columns can show `X`. `--mode 3val` is still an `UnsupportedFeatureError`. The radix rule is the same as for `eval`: for an X circuit, `--radix hex` or `--radix dec` gives `RadixNotAllowedIn3ValError`, exit code 1, and nothing is written.

```bash
$ circopt truth-table demo.circ --max-input-bits 8
a,b,k,y,z
0,0b00,0,X,0b000X
0,0b01,0,X,0b0X0X
0,0b10,0,X,0b100X
0,0b11,0,X,0b1X0X
1,0b00,0,1,0b000X
1,0b01,0,1,0b0X0X
1,0b10,0,1,0b100X
1,0b11,0,1,0b1X0X
```

The `-o` file and the `--json` result show the same values.

### `equiv`

Inputs still range over `0` and `1` only, exhaustively or at random as today. Two outputs are identical for an input assignment when they agree bit for bit, where an `X` bit agrees only with an `X` bit. `X` against `0` or `1` is a difference. Either or both files may be X circuits.

The counterexample shows output values in the form above, so they can hold `X`. Exit codes, `method` and `comparisons` mean what they mean today.

`dup.circ`:
```text
input a
output y
wire t
t = AND(a, X)
y = XOR(t, t)
```

`zero.circ`:
```text
input a
output y
y = 0
```

```bash
$ circopt equiv dup.circ zero.circ --max-input-bits 8 --json
{"ok":true,"command":"equiv","equivalent":false,"method":"exhaustive","comparisons":2,"counterexample":{"inputs":[{"name":"a","msb":0,"lsb":0,"value":"1"}],"outputs_compared":["y"],"a_outputs":[{"name":"y","msb":0,"lsb":0,"value":"X"}],"b_outputs":[{"name":"y","msb":0,"lsb":0,"value":"0"}]}}
# exit 10
```

With `a=1`, `t` is `X` and `XOR(X, X)` is `X`, not `0`.

### `lint`

No new warning types. The constant output check evaluates as described above. An output is constant when it has the same value, bit for bit with `X` bits included, for every input combination. The warning's `value` is written in the form above. `UnusedInputWarning` and the skipped-check warning are decided as today.

For `demo.circ`, only `k` is constant: `y` is `X` when `a` is `0` and `1` when `a` is `1`.

```bash
$ circopt lint demo.circ --json
{"ok":true,"command":"lint","warnings":[{"type":"ConstantOutputWarning","name":"k","message":"output 'k' is constant","value":"0"}]}
```

A file with `input a`, `output y`, `y = XOR(a, X)` gives one warning: `ConstantOutputWarning` for `y` with value `"X"`. Input `a` is used.

### `cone`

`cone` accepts X circuits and writes `X` literals in the canonical form: a 1-bit literal as `0`, `1` or `X`; a wider literal as `0b` followed by exactly one digit per bit, `X` uppercase. This applies to `.circ` and `.json` output. All other writing rules are as today. The file it writes passes `check`.

```bash
$ circopt cone demo.circ -o part.circ --outputs z
```

`part.circ`:
```text
input b[1:0]
output z[3:0]
wire t[1:0]

t = AND(0b1X, b)
z = {t, 0b0X}
```

### `opt`

`opt` does not support X circuits. Its rewrites rest on 2-valued identities that are false for an unknown bit, as the `equiv` example shows for `XOR(t, t)`. For an X circuit, `opt` gives `UnsupportedFeatureError`, exit code 1, whatever its other flags, and writes no output file and no report file.

```bash
$ circopt opt demo.circ -o out.circ --json
{"ok":false,"command":"opt","exit_code":1,"error":{"type":"UnsupportedFeatureError","message":"...","file":null,"line":null,"col":null}}
# exit 1
```

A circuit written by `cone` that no longer contains an `X` literal is an ordinary circuit, and `opt` accepts it.

## Scope

- Each error case above has one fault. Which error is reported when a run has several faults is not covered.
- Error messages are free text unless the specification already fixes them.
- Keep the existing tests passing and up to date with the code. Tests that assert the old prohibition must be updated.
