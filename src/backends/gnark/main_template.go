// main_template.go
// --- BEGIN GENERATED MAIN TEMPLATE ---
//
// usage:
//   go run <file>.go <outPath>
//
// writes:
//   <outPath>
//
// Notes:
// - In this gnark version, R1C sides are of type constraint.LinearExpression.
// - constraint.Term stores coefficients via coefficient IDs (CID).
//   This template emits coefficients as "c<CID>" strings.
//

func main() {
	_ = strings.Builder{}
	_ = big.Int{}
	_ = cmp.IsLess
	_ = ecc.BN254

	if len(os.Args) != 2 {
		panic("usage: <binary> <outPath>  (writes <outPath>)")
	}
	outPath := os.Args[1]

	var circuit smtlib2_lia

	// JSON schema
	type Term struct {
		Var   int    `json:"var"`
		Coeff string `json:"coeff"`
	}
	type Constraint struct {
		ID int    `json:"id"`
		L  []Term `json:"L"`
		R  []Term `json:"R"`
		O  []Term `json:"O"`
	}
	type Dump struct {
		Field       string       `json:"field"`
		System      string       `json:"system"`
		Constraints []Constraint `json:"constraints"`
	}

	// shared file write
	writeDump := func(dump Dump) {
		f, err := os.Create(outPath)
		if err != nil {
			panic(err)
		}
		defer f.Close()

		enc := json.NewEncoder(f)
		enc.SetIndent("", "  ")
		if err := enc.Encode(dump); err != nil {
			panic(err)
		}
	}

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
		r1csList := r1csCS.GetR1Cs()

		termsFromSlice := func(ts []constraint.Term) []Term {
			out := make([]Term, 0, len(ts))
			for _, t := range ts {
				out = append(out, Term{
					Var:   int(t.VID),
					Coeff: r1csCS.CoeffToString(int(t.CID)),
				})
			}
			return out
		}

		linToTerms := func(lin any) []Term {
			switch v := lin.(type) {
			case constraint.LinearExpression:
				return termsFromSlice([]constraint.Term(v))
			case []constraint.Term:
				return termsFromSlice(v)
			default:
				panic(fmt.Sprintf("unknown linear expression type: %T", lin))
			}
		}

		dump := Dump{
			Field:       "BN254",
			System:      "R1CS",
			Constraints: make([]Constraint, 0, len(r1csList)),
		}
		for i := range r1csList {
			c := r1csList[i]
			dump.Constraints = append(dump.Constraints, Constraint{
				ID: i,
				L:  linToTerms(c.L),
				R:  linToTerms(c.R),
				O:  linToTerms(c.O),
			})
		}

		writeDump(dump)
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
		r1csList := r1csCS.GetR1Cs()

		// NOTE: depending on your gnark version, Term/LinearExpression may be U32-typed here.
		// If this block fails to compile, paste the new error and I’ll adjust the types.
		termsFromSlice := func(ts []constraint.Term) []Term {
			out := make([]Term, 0, len(ts))
			for _, t := range ts {
				out = append(out, Term{
					Var:   int(t.VID),
					Coeff: r1csCS.CoeffToString(int(t.CID)),
				})
			}
			return out
		}

		linToTerms := func(lin any) []Term {
			switch v := lin.(type) {
			case constraint.LinearExpression:
				return termsFromSlice([]constraint.Term(v))
			case []constraint.Term:
				return termsFromSlice(v)
			default:
				panic(fmt.Sprintf("unknown linear expression type: %T", lin))
			}
		}

		dump := Dump{
			Field:       FIELD_PRIME.String(),
			System:      "R1CS",
			Constraints: make([]Constraint, 0, len(r1csList)),
		}
		for i := range r1csList {
			c := r1csList[i]
			dump.Constraints = append(dump.Constraints, Constraint{
				ID: i,
				L:  linToTerms(c.L),
				R:  linToTerms(c.R),
				O:  linToTerms(c.O),
			})
		}

		writeDump(dump)
	}
}
