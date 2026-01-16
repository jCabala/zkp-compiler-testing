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
	// Dummy use of strings to avoid import errors if not used elsewhere
	_ = strings.Builder{}

	if len(os.Args) != 2 {
		panic("usage: <binary> <outPath>  (writes <outPath>)")
	}
	outPath := os.Args[1]

	var circuit __CIRCUIT_NAME__
	ccs, err := frontend.Compile(ecc.BN254.ScalarField(), r1cs.NewBuilder, &circuit)
	if err != nil {
		panic(err)
	}

	// Extract R1CS constraints
	r1csCS, ok := ccs.(constraint.R1CS[constraint.U64])
	if !ok {
		panic("compiled constraint system is not R1CS[constraint.U64]")
	}
	r1csList := r1csCS.GetR1Cs()

	// JSON schema
	type Term struct {
		Var   int    `json:"var"`
		Coeff string `json:"coeff"` // coefficient id: "c<CID>"
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

	termsFromSlice := func(ts []constraint.Term) []Term {
		out := make([]Term, 0, len(ts))
		for _, t := range ts {
			out = append(out, Term{
				Var:   int(t.VID),
				// dump actual field element (often "0", "1", "-1", or big ints)
				Coeff: r1csCS.CoeffToString(int(t.CID)),
			})
		}
		return out
	}

	// Helper: linear expression -> []Term
	linToTerms := func(lin any) []Term {
		switch v := lin.(type) {
		case constraint.LinearExpression:
			// LinearExpression is (in this gnark) a named slice type, typically []constraint.Term
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

// --- END GENERATED MAIN TEMPLATE ---
