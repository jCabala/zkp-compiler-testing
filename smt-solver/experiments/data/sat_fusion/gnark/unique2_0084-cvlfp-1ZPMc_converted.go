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
var FIELD_PRIME = big.NewInt(47)

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

type smtlib2_lia struct {
	FVar_scr1_x1 frontend.Variable
	FVar_scr1_x2 frontend.Variable
	FVar_scr2_x1 frontend.Variable
	FVar_scr2_x2 frontend.Variable
	FVar_scr1_x1_scr2_x2_fused frontend.Variable `gnark:",public"`
}

func (circuit *smtlib2_lia) Define(api frontend.API) error {
	CircuitVarIn(circuit.FVar_scr1_x1)
	Label(circuit.FVar_scr1_x1, "scr1_x1")
	CircuitVarIn(circuit.FVar_scr1_x2)
	Label(circuit.FVar_scr1_x2, "scr1_x2")
	CircuitVarIn(circuit.FVar_scr2_x1)
	Label(circuit.FVar_scr2_x1, "scr2_x1")
	CircuitVarIn(circuit.FVar_scr2_x2)
	Label(circuit.FVar_scr2_x2, "scr2_x2")
	CircuitVarOut(circuit.FVar_scr1_x1_scr2_x2_fused)
	Label(circuit.FVar_scr1_x1_scr2_x2_fused, "scr1_x1_scr2_x2_fused")
	api.AssertIsBoolean(circuit.FVar_scr1_x1)
	api.AssertIsBoolean(circuit.FVar_scr1_x2)
	api.AssertIsBoolean(circuit.FVar_scr2_x1)
	api.AssertIsBoolean(circuit.FVar_scr2_x2)
	api.AssertIsBoolean(circuit.FVar_scr1_x1_scr2_x2_fused)
	api.AssertIsEqual(api.And(api.And(api.And(api.IsZero(circuit.FVar_scr1_x1), circuit.FVar_scr1_x2), api.IsZero(circuit.FVar_scr1_x1_scr2_x2_fused)), circuit.FVar_scr2_x1), 1)
	api.Println("scr1_x1_scr2_x2_fused:", circuit.FVar_scr1_x1_scr2_x2_fused)
	return nil // no error
}

// main_template.go
// --- BEGIN GENERATED MAIN TEMPLATE ---
//
// usage:
//   go run <file>.go <outPath>
//
// writes:
//   <outPath>  (sr1cs s-expression)
//
// Notes:
// - Inputs / outputs / labels / extra constraints are assumed
//   to be populated during Define(api) via helper calls.
// - This file must NOT define package/imports/helpers.
//
// --- END GENERATED MAIN TEMPLATE ---

func main() {
	if len(os.Args) != 2 {
		panic("usage: <binary> <outPath>  (writes <outPath>)")
	}
	outPath := os.Args[1]

	// Reset annotation buffers (important if main() is reused)
	extraCnsts = []string{}
	varIns = []string{}
	varOuts = []string{}
	labels = [][2]string{}

	var circuit smtlib2_lia

	f, err := os.Create(outPath)
	if err != nil {
		panic(err)
	}
	defer f.Close()

	// ------------------------------------------------------------
	// Shared: header + annotations
	// ------------------------------------------------------------
	writeHeaderAndAnnotations := func(prime any) {
		fmt.Fprintf(f, "(prime-number %v)\n", prime)

		for _, x := range varIns {
			fmt.Fprintf(f, "(in %v)\n", x)
		}
		for _, x := range varOuts {
			fmt.Fprintf(f, "(out %v)\n", x)
		}
		for _, x := range labels {
			fmt.Fprintf(f, "(label %v %v)\n", x[0], x[1])
		}
		for _, x := range extraCnsts {
			fmt.Fprintf(f, "(extra-constraint %v)\n", x)
		}
	}

	// ------------------------------------------------------------
	// U64 R1CS emission
	// ------------------------------------------------------------
	writeConstraintsU64 := func(r1csCS constraint.R1CS[constraint.U64]) {
		r1csList := r1csCS.GetR1Cs()
		for _, r1c := range r1csList {
			fmt.Fprintf(f, "(constraint ")
			fmt.Fprintf(f, "[")

			for i := 0; i < len(r1c.L); i++ {
				fmt.Fprintf(
					f,
					"(%v %v) ",
					r1csCS.CoeffToString(int(r1c.L[i].CID)),
					r1c.L[i].VID,
				)
			}
			fmt.Fprintf(f, "] [")

			for i := 0; i < len(r1c.R); i++ {
				fmt.Fprintf(
					f,
					"(%v %v) ",
					r1csCS.CoeffToString(int(r1c.R[i].CID)),
					r1c.R[i].VID,
				)
			}
			fmt.Fprintf(f, "] [")

			for i := 0; i < len(r1c.O); i++ {
				fmt.Fprintf(
					f,
					"(%v %v) ",
					r1csCS.CoeffToString(int(r1c.O[i].CID)),
					r1c.O[i].VID,
				)
			}
			fmt.Fprintf(f, "])\n")
		}
	}

	// ------------------------------------------------------------
	// U32 R1CS emission
	// ------------------------------------------------------------
	writeConstraintsU32 := func(r1csCS constraint.R1CS[constraint.U32]) {
		r1csList := r1csCS.GetR1Cs()
		for _, r1c := range r1csList {
			fmt.Fprintf(f, "(constraint ")
			fmt.Fprintf(f, "[")

			for i := 0; i < len(r1c.L); i++ {
				fmt.Fprintf(
					f,
					"(%v %v) ",
					r1csCS.CoeffToString(int(r1c.L[i].CID)),
					r1c.L[i].VID,
				)
			}
			fmt.Fprintf(f, "] [")

			for i := 0; i < len(r1c.R); i++ {
				fmt.Fprintf(
					f,
					"(%v %v) ",
					r1csCS.CoeffToString(int(r1c.R[i].CID)),
					r1c.R[i].VID,
				)
			}
			fmt.Fprintf(f, "] [")

			for i := 0; i < len(r1c.O); i++ {
				fmt.Fprintf(
					f,
					"(%v %v) ",
					r1csCS.CoeffToString(int(r1c.O[i].CID)),
					r1c.O[i].VID,
				)
			}
			fmt.Fprintf(f, "])\n")
		}
	}

	// ------------------------------------------------------------
	// Compile & dump
	// ------------------------------------------------------------
	if FIELD_PRIME.String() == ecc.BN254.ScalarField().String() {
		// ---- U64 path ----
		ccs, err := frontend.Compile(FIELD_PRIME, r1cs.NewBuilder, &circuit)
		if err != nil {
			panic(err)
		}

		r1csCS, ok := ccs.(constraint.R1CS[constraint.U64])
		if !ok {
			panic("compiled constraint system is not R1CS[constraint.U64]")
		}

		writeHeaderAndAnnotations(r1csCS.Field())
		writeConstraintsU64(r1csCS)
		return
	}

	{
		// ---- U32 path ----
		ccs, err := frontend.CompileU32(FIELD_PRIME, r1cs.NewBuilder, &circuit)
		if err != nil {
			panic(err)
		}

		r1csCS, ok := ccs.(constraint.R1CS[constraint.U32])
		if !ok {
			panic("compiled constraint system is not R1CS[constraint.U32]")
		}

		writeHeaderAndAnnotations(r1csCS.Field())
		writeConstraintsU32(r1csCS)
	}
}
