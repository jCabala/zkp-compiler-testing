// prefix.go
// --- BEGIN GENERATED PREFIX TEMPLATE ---
//
// This file is a *template fragment* (not compiled standalone).
// The emitter concatenates:
//   prefix.go + <generated circuit> + main_template.go
//
// Place ALL imports here.
//
// --- END GENERATED PREFIX TEMPLATE ---

package main

import (
	"fmt"
	"math/big"
	"os"
	"regexp"
	"strings"

	"github.com/consensys/gnark-crypto/ecc"
	"github.com/consensys/gnark/constraint"
	"github.com/consensys/gnark/frontend"
	"github.com/consensys/gnark/frontend/cs/r1cs"

	// used by generated circuit code (bitwise + comparisons)
	"github.com/consensys/gnark/std/math/bits"
	cmp "github.com/consensys/gnark/std/math/cmp"
)

// Keep these references so imports don't go unused even if a particular circuit
// doesn't touch them (Go is strict about unused imports).
var (
	_ = strings.Builder{}
	_ = big.Int{}
	_ = ecc.BN254

	// safe import keep-alives (avoid composite literals / generics)
	_ = fmt.Sprintf
	_ = regexp.MustCompile
	_ = os.Args

	// used by generated circuit code
	_ = bits.ToBinary
	_ = cmp.IsLess
)

// Field prime (patched by emitter)
var FIELD_PRIME = __FIELD_PRIME__

// -----------------------------------------------------------------------------
// Picus-style globals + helpers (embedded)
// -----------------------------------------------------------------------------

var extraCnsts []string
var varIns []string
var varOuts []string
var labels [][2]string

func AddExtraConstraint(x string) {
	extraCnsts = append(extraCnsts, x)
}

func Extract(x frontend.Variable) string {
	r, _ := regexp.Compile(`^\[{([0-9]+)`)
	return r.FindStringSubmatch(fmt.Sprint(x))[1]
}

func CircuitVarIn(v frontend.Variable) {
	varIns = append(varIns, Extract(v))
}

func CircuitVarOut(v frontend.Variable) {
	varOuts = append(varOuts, Extract(v))
}

func Label(v frontend.Variable, name string) {
	labels = append(labels, [2]string{Extract(v), name})
}
// -----------------------------------------------------------------------------