use super::{A, ConstraintList, C, EncodingIterator, SignalMap};
use circom_algebra::modular_arithmetic;
use circom_algebra::num_bigint::BigInt;
use constraint_writers::r1cs_writer::{ConstraintSection, CustomGatesAppliedData, HeaderData, R1CSWriter, SignalSection};
use rand::seq::SliceRandom;
use rand::Rng;
use std::collections::{HashMap, HashSet};
use std::env;
use std::fs;

struct MutableConstraint {
    a: HashMap<usize, BigInt>,
    b: HashMap<usize, BigInt>,
    c: HashMap<usize, BigInt>,
    is_linear: bool,
}

struct ArtificialBugsConfig {
    always_empty_r1cs: bool,
    remove_random_variable_n: usize,
    remove_random_constraint_n: usize,
    add_random_constraint_n: usize,
    change_random_number_n: usize,
    bias_constant_on_nonlinear_n: usize,
}

fn parse_non_negative_usize(value: &json::JsonValue) -> Option<usize> {
    let raw = value.dump();
    raw.parse::<usize>().ok()
}

fn load_artificial_bugs_config() -> ArtificialBugsConfig {
    let cfg_path =
        env::var("CIRCOM_ARTIFICIAL_BUGS_CONFIG").unwrap_or_else(|_| "circom_artificial_bugs.json".to_string());
    let content = match fs::read_to_string(&cfg_path) {
        Ok(c) => c,
        Err(_) => {
            return ArtificialBugsConfig {
                always_empty_r1cs: false,
                remove_random_variable_n: 0,
                remove_random_constraint_n: 0,
                add_random_constraint_n: 0,
                change_random_number_n: 0,
                bias_constant_on_nonlinear_n: 0,
            }
        }
    };
    let parsed = match json::parse(&content) {
        Ok(v) => v,
        Err(_) => {
            return ArtificialBugsConfig {
                always_empty_r1cs: false,
                remove_random_variable_n: 0,
                remove_random_constraint_n: 0,
                add_random_constraint_n: 0,
                change_random_number_n: 0,
                bias_constant_on_nonlinear_n: 0,
            }
        }
    };

    let always_empty_r1cs = parsed["always-empty-r1cs"].as_bool().unwrap_or(false)
        || parsed["always_empty_r1cs"].as_bool().unwrap_or(false);

    let mut remove_random_variable_n = 0usize;
    if let Some(n) = parse_non_negative_usize(&parsed["remove-random-variable"]) {
        remove_random_variable_n = n;
    } else if let Some(n) = parse_non_negative_usize(&parsed["remove_random_variable"]) {
        remove_random_variable_n = n;
    } else if let Some(n) = parse_non_negative_usize(&parsed["remove-random-variable"]["n"]) {
        remove_random_variable_n = n;
    } else if let Some(n) = parse_non_negative_usize(&parsed["remove_random_variable"]["n"]) {
        remove_random_variable_n = n;
    }

    let mut remove_random_constraint_n = 0usize;
    if let Some(n) = parse_non_negative_usize(&parsed["remove-random-constraint"]) {
        remove_random_constraint_n = n;
    } else if let Some(n) = parse_non_negative_usize(&parsed["remove_random_constraint"]) {
        remove_random_constraint_n = n;
    } else if let Some(n) = parse_non_negative_usize(&parsed["remove-random-constraint"]["n"]) {
        remove_random_constraint_n = n;
    } else if let Some(n) = parse_non_negative_usize(&parsed["remove_random_constraint"]["n"]) {
        remove_random_constraint_n = n;
    }

    let mut add_random_constraint_n = 0usize;
    if let Some(n) = parse_non_negative_usize(&parsed["add-random-constraint"]) {
        add_random_constraint_n = n;
    } else if let Some(n) = parse_non_negative_usize(&parsed["add_random_constraint"]) {
        add_random_constraint_n = n;
    } else if let Some(n) = parse_non_negative_usize(&parsed["add-random-constraint"]["n"]) {
        add_random_constraint_n = n;
    } else if let Some(n) = parse_non_negative_usize(&parsed["add_random_constraint"]["n"]) {
        add_random_constraint_n = n;
    }

    let mut change_random_number_n = 0usize;
    if let Some(n) = parse_non_negative_usize(&parsed["change-random-number"]) {
        change_random_number_n = n;
    } else if let Some(n) = parse_non_negative_usize(&parsed["change_random_number"]) {
        change_random_number_n = n;
    } else if let Some(n) = parse_non_negative_usize(&parsed["change-random-number"]["n"]) {
        change_random_number_n = n;
    } else if let Some(n) = parse_non_negative_usize(&parsed["change_random_number"]["n"]) {
        change_random_number_n = n;
    }

    let mut bias_constant_on_nonlinear_n = 0usize;
    if let Some(n) = parse_non_negative_usize(&parsed["bias-constant-on-nonlinear"]) {
        bias_constant_on_nonlinear_n = n;
    } else if let Some(n) = parse_non_negative_usize(&parsed["bias_constant_on_nonlinear"]) {
        bias_constant_on_nonlinear_n = n;
    } else if let Some(n) = parse_non_negative_usize(&parsed["bias-constant-on-nonlinear"]["n"]) {
        bias_constant_on_nonlinear_n = n;
    } else if let Some(n) = parse_non_negative_usize(&parsed["bias_constant_on_nonlinear"]["n"]) {
        bias_constant_on_nonlinear_n = n;
    }

    ArtificialBugsConfig {
        always_empty_r1cs,
        remove_random_variable_n,
        remove_random_constraint_n,
        add_random_constraint_n,
        change_random_number_n,
        bias_constant_on_nonlinear_n,
    }
}

fn collect_constraint_variables(constraint: &MutableConstraint) -> HashSet<usize> {
    let mut vars = HashSet::new();
    for signal in constraint.a.keys() {
        if *signal != 0 {
            vars.insert(*signal);
        }
    }
    for signal in constraint.b.keys() {
        if *signal != 0 {
            vars.insert(*signal);
        }
    }
    for signal in constraint.c.keys() {
        if *signal != 0 {
            vars.insert(*signal);
        }
    }
    vars
}

fn constraint_touches_any(constraint: &MutableConstraint, removed_variables: &HashSet<usize>) -> bool {
    for signal in constraint.a.keys() {
        if *signal != 0 && removed_variables.contains(signal) {
            return true;
        }
    }
    for signal in constraint.b.keys() {
        if *signal != 0 && removed_variables.contains(signal) {
            return true;
        }
    }
    for signal in constraint.c.keys() {
        if *signal != 0 && removed_variables.contains(signal) {
            return true;
        }
    }
    false
}

pub fn port_r1cs(list: &ConstraintList, output: &str, custom_gates: bool) -> Result<(), ()> {
    use constraint_writers::log_writer::Log;
    let field_size = if list.field.bits() % 64 == 0 {
        list.field.bits() / 8
    } else{
        (list.field.bits() / 64 + 1) * 8
    };
    let mut log = Log::new();
    log.no_labels = ConstraintList::no_labels(list);
    log.no_wires = ConstraintList::no_wires(list);
    log.no_private_inputs = list.no_private_inputs;
    log.no_private_inputs_witness = list.no_private_inputs_witness;
    log.no_public_inputs = list.no_public_inputs;
    log.no_public_outputs = list.no_public_outputs;

    let r1cs = R1CSWriter::new(output.to_string(), field_size, custom_gates)?;
    let mut constraint_section = R1CSWriter::start_constraints_section(r1cs)?;
    let mut written = 0;
    let bugs_config = load_artificial_bugs_config();
    let force_empty_r1cs = bugs_config.always_empty_r1cs;
    let remove_random_variable_n = bugs_config.remove_random_variable_n;
    let remove_random_constraint_n = bugs_config.remove_random_constraint_n;
    let add_random_constraint_n = bugs_config.add_random_constraint_n;
    let change_random_number_n = bugs_config.change_random_number_n;
    let bias_constant_on_nonlinear_n = bugs_config.bias_constant_on_nonlinear_n;

    if force_empty_r1cs {
        eprintln!(
            "[artificial-bugs] enabled bug 'always-empty-r1cs': writing empty constraint section"
        );
    }

    if !force_empty_r1cs {
        let mut mapped_constraints = Vec::new();
        for c_id in list.constraints.get_ids() {
            let c = list.constraints.read_constraint(c_id).unwrap();
            let c = C::apply_correspondence(&c, &list.signal_map);
            mapped_constraints.push(MutableConstraint {
                a: c.a().clone(),
                b: c.b().clone(),
                c: c.c().clone(),
                is_linear: C::is_linear(&c),
            });
        }

        if remove_random_variable_n > 0 {
            let mut candidate_variables = HashSet::new();
            for c in &mapped_constraints {
                candidate_variables.extend(collect_constraint_variables(c));
            }

            if !candidate_variables.is_empty() {
                let mut selected_variables: Vec<usize> = candidate_variables.into_iter().collect();
                selected_variables.shuffle(&mut rand::thread_rng());
                let selected_variables: HashSet<usize> = selected_variables
                    .into_iter()
                    .take(remove_random_variable_n)
                    .collect();

                let before = mapped_constraints.len();
                mapped_constraints.retain(|c| !constraint_touches_any(c, &selected_variables));
                let removed_constraints = before - mapped_constraints.len();
                eprintln!(
                    "[artificial-bugs] enabled bug 'remove-random-variable': selected {} variables, removed {} constraints",
                    selected_variables.len(),
                    removed_constraints
                );
            }
        }

        if remove_random_constraint_n > 0 && !mapped_constraints.is_empty() {
            let mut random_indices: Vec<usize> = (0..mapped_constraints.len()).collect();
            random_indices.shuffle(&mut rand::thread_rng());
            let selected_indices: HashSet<usize> = random_indices
                .into_iter()
                .take(remove_random_constraint_n)
                .collect();

            let before = mapped_constraints.len();
            mapped_constraints = mapped_constraints
                .into_iter()
                .enumerate()
                .filter_map(|(i, c)| {
                    if selected_indices.contains(&i) {
                        None
                    } else {
                        Some(c)
                    }
                })
                .collect();
            let removed_constraints = before - mapped_constraints.len();
            eprintln!(
                "[artificial-bugs] enabled bug 'remove-random-constraint': selected {} constraints, removed {} constraints",
                selected_indices.len(),
                removed_constraints
            );
        }

        if add_random_constraint_n > 0 {
            let candidate_variables: Vec<usize> = (1..ConstraintList::no_wires(list)).collect();
            if candidate_variables.len() >= 2 {
                let mut rng = rand::thread_rng();
                let mut added = 0usize;
                for _ in 0..add_random_constraint_n {
                    let chosen: Vec<&usize> = candidate_variables.choose_multiple(&mut rng, 2).collect();
                    if chosen.len() != 2 {
                        continue;
                    }
                    let x = *chosen[0];
                    let y = *chosen[1];
                    let num = BigInt::from(rng.gen::<u64>());
                    let x_expr = A::Signal { symbol: x };
                    let y_expr = A::Signal { symbol: y };
                    let num_expr = A::Number { value: num };
                    let mul_expr = A::mul(&x_expr, &y_expr, &list.field);
                    let eq_zero_expr = A::sub(&mul_expr, &num_expr, &list.field);
                    if let Some(new_constraint) =
                        A::transform_expression_to_constraint_form(eq_zero_expr, &list.field)
                    {
                        mapped_constraints.push(MutableConstraint {
                            a: new_constraint.a().clone(),
                            b: new_constraint.b().clone(),
                            c: new_constraint.c().clone(),
                            is_linear: C::is_linear(&new_constraint),
                        });
                        added += 1;
                    }
                }
                eprintln!(
                    "[artificial-bugs] enabled bug 'add-random-constraint': requested {}, added {} constraints",
                    add_random_constraint_n,
                    added
                );
            }
        }

        if change_random_number_n > 0 && !mapped_constraints.is_empty() {
            let mut candidates = Vec::new();
            for (ci, c) in mapped_constraints.iter().enumerate() {
                for key in c.a.keys() {
                    candidates.push((ci, 0usize, *key));
                }
                for key in c.b.keys() {
                    candidates.push((ci, 1usize, *key));
                }
                for key in c.c.keys() {
                    candidates.push((ci, 2usize, *key));
                }
            }
            if !candidates.is_empty() {
                candidates.shuffle(&mut rand::thread_rng());
                let mut rng = rand::thread_rng();
                let mut changed = 0usize;
                for (ci, part, key) in candidates.into_iter().take(change_random_number_n) {
                    let new_value = BigInt::from(rng.gen::<u64>());
                    let value_ref = match part {
                        0 => mapped_constraints[ci].a.get_mut(&key),
                        1 => mapped_constraints[ci].b.get_mut(&key),
                        _ => mapped_constraints[ci].c.get_mut(&key),
                    };
                    if let Some(v) = value_ref {
                        *v = new_value;
                        changed += 1;
                    }
                }
                eprintln!(
                    "[artificial-bugs] enabled bug 'change-random-number': requested {}, changed {} numbers",
                    change_random_number_n,
                    changed
                );
            }
        }

        if bias_constant_on_nonlinear_n > 0 && !mapped_constraints.is_empty() {
            let mut nonlinear_indices = Vec::new();
            for (i, c) in mapped_constraints.iter().enumerate() {
                if !c.is_linear {
                    nonlinear_indices.push(i);
                }
            }
            if !nonlinear_indices.is_empty() {
                nonlinear_indices.shuffle(&mut rand::thread_rng());
                let mut rng = rand::thread_rng();
                let mut changed = 0usize;
                for idx in nonlinear_indices.into_iter().take(bias_constant_on_nonlinear_n) {
                    // Tiny delta in {-3,-2,-1,1,2,3}
                    let mag = rng.gen_range(1u64..=3u64);
                    let sign: i64 = if rng.gen_bool(0.5) { 1 } else { -1 };
                    let delta = BigInt::from(sign) * BigInt::from(mag);
                    let constant_key = 0usize;
                    let current = mapped_constraints[idx]
                        .c
                        .get(&constant_key)
                        .cloned()
                        .unwrap_or_else(|| BigInt::from(0));
                    let next = modular_arithmetic::add(&current, &delta, &list.field);
                    mapped_constraints[idx].c.insert(constant_key, next);
                    changed += 1;
                }
                eprintln!(
                    "[artificial-bugs] enabled bug 'bias-constant-on-nonlinear': requested {}, changed {} nonlinear constraints",
                    bias_constant_on_nonlinear_n,
                    changed
                );
            }
        }

        for c in mapped_constraints {
            ConstraintSection::write_constraint_usize(&mut constraint_section, &c.a, &c.b, &c.c)?;
            if c.is_linear {
                log.no_linear += 1;
            } else {
                log.no_non_linear += 1;
            }
            written += 1;
        }
    }

    let r1cs = constraint_section.end_section()?;
    let mut header_section = R1CSWriter::start_header_section(r1cs)?;
    let header_data = HeaderData {
        field: list.field.clone(),
        public_outputs: list.no_public_outputs,
        public_inputs: list.no_public_inputs,
        private_inputs: list.no_private_inputs,
        total_wires: ConstraintList::no_wires(list),
        number_of_labels: ConstraintList::no_labels(list),
        number_of_constraints: written,
    };
    header_section.write_section(header_data)?;
    let r1cs = header_section.end_section()?;
    let mut signal_section = R1CSWriter::start_signal_section(r1cs)?;

    for id in list.get_witness_as_vec() {
        SignalSection::write_signal_usize(&mut signal_section, id)?;
    }
    let r1cs = signal_section.end_section()?;
    if !custom_gates {
	R1CSWriter::finish_writing(r1cs)?;
    } else {
        let mut custom_gates_used_section = R1CSWriter::start_custom_gates_used_section(r1cs)?;
        let (usage_data, occurring_order) = {
            let mut usage_data = vec![];
            let mut occurring_order = vec![];
            for node in &list.dag_encoding.nodes {
                if node.is_custom_gate {
                    let mut name = node.name.clone();
                    occurring_order.push(name.clone());
                    while name.pop() != Some('(') {};
                    usage_data.push((name, node.parameters.clone()));
                }
            }
            (usage_data, occurring_order)
        };
        custom_gates_used_section.write_custom_gates_usages(usage_data)?;
        let r1cs = custom_gates_used_section.end_section()?;

        let mut custom_gates_applied_section = R1CSWriter::start_custom_gates_applied_section(r1cs)?;
        let application_data = {
            fn find_indexes(
                occurring_order: Vec<String>,
                application_data: Vec<(String, Vec<usize>)>
            ) -> CustomGatesAppliedData {
                let mut new_application_data = vec![];
                for (custom_gate_name, signals) in application_data {
                    let mut index = 0;
                    while occurring_order[index] != custom_gate_name {
                        index += 1;
                    }
                    new_application_data.push((index, signals));
                }
                new_application_data
            }

            fn iterate(
                iterator: EncodingIterator,
                map: &SignalMap,
                application_data: &mut Vec<(String, Vec<usize>)>
            ) {
                let node = &iterator.encoding.nodes[iterator.node_id];
                if node.is_custom_gate {
                    let mut signals = vec![];
                    for signal in &node.ordered_signals {
                        let new_signal = signal + iterator.offset;
                        let signal_numbering = map.get(&new_signal).unwrap();
                        signals.push(*signal_numbering);
                    }
                    application_data.push((node.name.clone(), signals));
                } else {
                    for edge in EncodingIterator::edges(&iterator) {
                        let next = EncodingIterator::next(&iterator, edge);
                        iterate(next, map, application_data);
                    }
                }
            }

            let mut application_data = vec![];
            let iterator = EncodingIterator::new(&list.dag_encoding);
            iterate(iterator, &list.signal_map, &mut application_data);
            find_indexes(occurring_order, application_data)
        };
        custom_gates_applied_section.write_custom_gates_applications(application_data)?;
        let r1cs = custom_gates_applied_section.end_section()?;
	R1CSWriter::finish_writing(r1cs)?;
    }
    Log::print(&log);
    Ok(())
}
