// Uncomment lines 163, 165, 336 and 338 to print cluster information
use super::{ConstraintStorage, EncodingIterator, SEncoded, Simplifier, A, C, S};
use crate::SignalMap;
use circom_algebra::num_bigint::BigInt;
use constraint_writers::json_writer::SubstitutionJSON;
use std::collections::{HashMap, HashSet, LinkedList, BTreeSet};
use std::sync::Arc;

fn log_substitutions(substitutions: &LinkedList<S>, writer: &mut Option<SubstitutionJSON>) {
    use super::json_porting::port_substitution;
    if let Some(w) = writer {
        for s in substitutions {
            let (from, to) = port_substitution(s);
            w.write_substitution(&from, &to).unwrap();
        }
    }
}

#[derive(Default, Clone)]
struct Cluster {
    constraints: LinkedList<C>,
    num_signals: usize
}
impl Cluster {
    pub fn new(constraint: C, num_signals: usize) -> Cluster {
        let mut new = Cluster::default();
        LinkedList::push_back(&mut new.constraints, constraint);
        new.num_signals = num_signals;
        new
    }

    pub fn merge(mut c0: Cluster, mut c1: Cluster) -> Cluster {
        let mut result = Cluster::default();
        LinkedList::append(&mut result.constraints, &mut c0.constraints);
        LinkedList::append(&mut result.constraints, &mut c1.constraints);
        result.num_signals = c0.num_signals + c1.num_signals - 1;
        result
    }

    pub fn size(&self) -> usize {
        LinkedList::len(&self.constraints)
    }
}

fn build_clusters(linear: LinkedList<C>, no_vars: usize) -> Vec<Cluster> {
    type ClusterArena = Vec<Option<Cluster>>;
    type ClusterPath = Vec<usize>;
    fn shrink_jumps_and_find(c_to_c: &mut ClusterPath, org: usize) -> usize {
        let mut current = org;
        let mut jumps = Vec::new();
        while current != c_to_c[current] {
            Vec::push(&mut jumps, current);
            current = c_to_c[current];
        }
        while let Some(redirect) = Vec::pop(&mut jumps) {
            c_to_c[redirect] = current;
        }
        current
    }

    fn arena_merge(arena: &mut ClusterArena, c_to_c: &mut ClusterPath, src: usize, dest: usize) {
        let current_dest = shrink_jumps_and_find(c_to_c, dest);
        let current_src = shrink_jumps_and_find(c_to_c, src);
        let c0 = std::mem::replace(&mut arena[current_dest], None).unwrap_or_default();
        let c1 = std::mem::replace(&mut arena[current_src], None).unwrap_or_default();
        let merged = Cluster::merge(c0, c1);
        arena[current_dest] = Some(merged);
        c_to_c[current_src] = current_dest;
    }

    let no_linear = LinkedList::len(&linear);
    let mut arena = ClusterArena::with_capacity(no_linear);
    let mut cluster_to_current = ClusterPath::with_capacity(no_linear);
    let mut signal_to_cluster = vec![no_linear; no_vars];
    for constraint in linear {
        if !constraint.is_empty(){
            let signals = C::take_cloned_signals(&constraint);
            let dest = ClusterArena::len(&arena);
            ClusterArena::push(&mut arena, Some(Cluster::new(constraint, signals.len())));
            Vec::push(&mut cluster_to_current, dest);
            for signal in signals {
                let prev = signal_to_cluster[signal];
                signal_to_cluster[signal] = dest;
                if prev < no_linear {
                    arena_merge(&mut arena, &mut cluster_to_current, prev, dest);
                }
            }
        }
    }
    let mut clusters = Vec::new();
    for cluster in arena {
        if let Some(cluster) = cluster {
            if Cluster::size(&cluster) != 0 {
                Vec::push(&mut clusters, cluster);
            }
        }
    }
    clusters
}

fn rebuild_witness(
    max_signal: usize,
    deleted: &mut HashSet<usize>,
    forbidden: &HashSet<usize>,
    non_linear_map: SignalToConstraints,
    remove_unused: bool,
) -> SignalMap {
    let mut map = SignalMap::with_capacity(max_signal);
    let mut free = LinkedList::new();
    for signal in 0..max_signal {
        if deleted.contains(&signal) {
            free.push_back(signal);
        } else if remove_unused && !forbidden.contains(&signal) && !non_linear_map.contains_key(&signal){
            deleted.insert(signal);
            free.push_back(signal);
        } else if let Some(new_pos) = free.pop_front() {
            map.insert(signal, new_pos);
            free.push_back(signal);
        } else {
            map.insert(signal, signal);
        }
    }
    map
}

fn eq_cluster_simplification(
    mut cluster: Cluster,
    forbidden: &HashSet<usize>,
    field: &BigInt,
) -> (LinkedList<S>, LinkedList<C>) {
    if Cluster::size(&cluster) == 1 {
        let mut substitutions = LinkedList::new();
        let mut constraints = LinkedList::new();
        let constraint = LinkedList::pop_back(&mut cluster.constraints).unwrap();
        let signals: Vec<_> = C::take_cloned_signals_ordered(&constraint).iter().cloned().collect();
        let s_0 = signals[0];
        let s_1 = signals[1];
        if HashSet::contains(forbidden, &s_0) && HashSet::contains(forbidden, &s_1) {
            LinkedList::push_back(&mut constraints, constraint);
        } else if HashSet::contains(forbidden, &s_0) {
            LinkedList::push_back(
                &mut substitutions,
                S::new(s_1, A::Signal { symbol: s_0 }).unwrap(),
            );
        } else if HashSet::contains(forbidden, &s_1) {
            LinkedList::push_back(
                &mut substitutions,
                S::new(s_0, A::Signal { symbol: s_1 }).unwrap(),
            );
        } else {
            let (l, r) = if s_0 > s_1 { (s_0, s_1) } else { (s_1, s_0) };
            LinkedList::push_back(&mut substitutions, S::new(l, A::Signal { symbol: r }).unwrap());
        }
        (substitutions, constraints)
    } else {
        let mut cons = LinkedList::new();
        let mut subs = LinkedList::new();
        let (mut remains, mut min_remains) = (BTreeSet::new(), None);
        let (mut remove, mut min_remove) = (HashSet::new(), None);
        for c in cluster.constraints {
            for signal in C::take_cloned_signals_ordered(&c) {
                if HashSet::contains(&forbidden, &signal) {
                    BTreeSet::insert(&mut remains, signal);
                    min_remains = Some(min_remains.map_or(signal, |s| std::cmp::min(s, signal)));
                } else {
                    min_remove = Some(min_remove.map_or(signal, |s| std::cmp::min(s, signal)));
                    HashSet::insert(&mut remove, signal);
                }
            }
        }

        let rh_signal = if let Some(signal) = min_remains {
            BTreeSet::remove(&mut remains, &signal);
            signal
        } else {
            let signal = min_remove.unwrap();
            HashSet::remove(&mut remove, &signal);
            signal
        };

        for signal in remains {
            let l = A::Signal { symbol: signal };
            let r = A::Signal { symbol: rh_signal };
            let expr = A::sub(&l, &r, field);
            let c = A::transform_expression_to_constraint_form(expr, field).unwrap();
            LinkedList::push_back(&mut cons, c);
        }

        for signal in remove {
            let sub = S::new(signal, A::Signal { symbol: rh_signal }).unwrap();
            LinkedList::push_back(&mut subs, sub);
        }

        (subs, cons)
    }
}

fn eq_simplification(
    equalities: LinkedList<C>,
    forbidden: Arc<HashSet<usize>>,
    no_vars: usize,
    field: &BigInt,
    substitution_log: &mut Option<SubstitutionJSON>,
) -> (LinkedList<S>, LinkedList<C>) {
    use std::sync::mpsc;
    use threadpool::ThreadPool;
    let field = Arc::new(field.clone());
    let mut constraints = LinkedList::new();
    let mut substitutions = LinkedList::new();
    let clusters = build_clusters(equalities, no_vars);
    let (cluster_tx, simplified_rx) = mpsc::channel();
    let pool = ThreadPool::new(num_cpus::get());
    let no_clusters = Vec::len(&clusters);
    // println!("Clusters: {}", no_clusters);
    let mut single_clusters = 0;
    let mut id = 0;
    let mut aux_constraints = vec![LinkedList::new(); clusters.len()];
    for cluster in clusters {
        if Cluster::size(&cluster) == 1 {
            let (mut subs, cons) = eq_cluster_simplification(cluster, &forbidden, &field);
            aux_constraints[id] = cons;
            LinkedList::append(&mut substitutions, &mut subs);
            single_clusters += 1;
        } else {
            let cluster_tx = cluster_tx.clone();
            let forbidden = Arc::clone(&forbidden);
            let field = Arc::clone(&field);
            let job = move || {
                //println!("Cluster: {}", id);
                let result = eq_cluster_simplification(cluster, &forbidden, &field);
                //println!("End of cluster: {}", id);
                cluster_tx.send((id, result)).unwrap();
            };
            ThreadPool::execute(&pool, job);
        }
        let _ = id;
        id += 1;
    }
    // println!("{} clusters were of size 1", single_clusters);
    ThreadPool::join(&pool);
    for _ in 0..(no_clusters - single_clusters) {
        let (id, (mut subs, cons)) = simplified_rx.recv().unwrap();
        aux_constraints[id] = cons;
        LinkedList::append(&mut substitutions, &mut subs);
    }
    for id in 0..no_clusters {
        LinkedList::append(&mut constraints, &mut aux_constraints[id]);
    }
    log_substitutions(&substitutions, substitution_log);
    (substitutions, constraints)
}

fn constant_eq_simplification(
    c_eq: LinkedList<C>,
    forbidden: &HashSet<usize>,
    field: &BigInt,
    substitution_log: &mut Option<SubstitutionJSON>,
) -> (LinkedList<S>, LinkedList<C>) {
    let mut cons = LinkedList::new();
    let mut subs = LinkedList::new();
    for constraint in c_eq {
        let mut signals: Vec<_> = C::take_cloned_signals_ordered(&constraint).iter().cloned().collect();
        let signal = signals.pop().unwrap();
        if HashSet::contains(&forbidden, &signal) {
            LinkedList::push_back(&mut cons, constraint);
        } else {
            let sub = C::clear_signal_from_linear(constraint, &signal, field);
            LinkedList::push_back(&mut subs, sub);
        }
    }
    log_substitutions(&subs, substitution_log);
    (subs, cons)
}

fn linear_simplification(
    log: &mut Option<SubstitutionJSON>,
    linear: LinkedList<C>,
    forbidden: Arc<HashSet<usize>>,
    no_labels: usize,
    field: &BigInt,
    use_old_heuristics: bool,
) -> (LinkedList<S>, LinkedList<C>) {
    use circom_algebra::simplification_utils::full_simplification;
    use circom_algebra::simplification_utils::Config;
    use std::sync::mpsc;
    use threadpool::ThreadPool;

    // println!("Cluster simplification");
    let mut cons = LinkedList::new();
    let mut substitutions = LinkedList::new();
    let clusters = build_clusters(linear, no_labels);
    let (cluster_tx, simplified_rx) = mpsc::channel();
    let pool = ThreadPool::new(num_cpus::get());
    let no_clusters = Vec::len(&clusters);
    // println!("Clusters: {}", no_clusters);
    let mut id = 0;
    for cluster in clusters {
        let cluster_tx = cluster_tx.clone();
        let config = Config {
            field: field.clone(),
            constraints: cluster.constraints,
            forbidden: Arc::clone(&forbidden),
            num_signals: cluster.num_signals,
            use_old_heuristics,
        };
        let job = move || {
            // println!("cluster: {}", id);
            let result = full_simplification(config);
            // println!("End of cluster: {}", id);
            cluster_tx.send(result).unwrap();
        };
        ThreadPool::execute(&pool, job);
        let _ = id;
        id += 1;
    }
    ThreadPool::join(&pool);

    for _ in 0..no_clusters {
        let mut result = simplified_rx.recv().unwrap();
        log_substitutions(&result.substitutions, log);
        LinkedList::append(&mut cons, &mut result.constraints);
        LinkedList::append(&mut substitutions, &mut result.substitutions);
    }
    (substitutions, cons)
}

type SignalToConstraints = HashMap<usize, LinkedList<usize>>;
fn build_non_linear_signal_map(non_linear: &ConstraintStorage) -> SignalToConstraints {
    let mut map = SignalToConstraints::new();
    for c_id in non_linear.get_ids() {
        let constraint = non_linear.read_constraint(c_id).unwrap();
        for signal in C::take_cloned_signals(&constraint) {
            if let Some(list) = map.get_mut(&signal) {
                list.push_back(c_id);
            } else {
                let mut new = LinkedList::new();
                new.push_back(c_id);
                map.insert(signal, new);
            }
        }
    }
    map
}

fn apply_substitution_to_map(
    storage: &mut ConstraintStorage,
    map: &mut SignalToConstraints,
    substitutions: &LinkedList<S>,
    field: &BigInt,
) -> LinkedList<C> {
    fn constraint_processing(
        storage: &mut ConstraintStorage,
        map: &mut SignalToConstraints,
        c_ids: &LinkedList<usize>,
        substitution: &S,
        field: &BigInt,
    ) -> LinkedList<usize> {
        let mut linear = LinkedList::new();
        let signals: LinkedList<_> = substitution.to().keys().cloned().collect();
        for c_id in c_ids {
            let c_id = *c_id;
            let mut constraint = storage.read_constraint(c_id).unwrap();
            C::apply_substitution(&mut constraint, substitution, field);
            C::fix_constraint(&mut constraint, field);
            if C::is_linear(&constraint) {
                linear.push_back(c_id);
            }
            storage.replace(c_id, constraint);
            for signal in &signals {
                if let Some(list) = map.get_mut(&signal) {
                    list.push_back(c_id);
                } else {
                    let mut new = LinkedList::new();
                    new.push_back(c_id);
                    map.insert(*signal, new);
                }
            }
        }
        linear
    }

    let mut linear_id = LinkedList::new();
    for substitution in substitutions {
        if let Some(c_ids) = map.get(substitution.from()).cloned() {
            let mut new_linear = constraint_processing(storage, map, &c_ids, substitution, field);
            linear_id.append(&mut new_linear);
        }
    }
    let mut linear = LinkedList::new();
    for c_id in linear_id {
        let constraint = storage.read_constraint(c_id).unwrap();
        linear.push_back(constraint);
        storage.replace(c_id, C::empty());
    }
    linear
}

fn build_relevant_set(
    mut iter: EncodingIterator,
    relevant: &mut HashSet<usize>,
    renames: &SEncoded,
    deletes: &SEncoded,
) {
    fn unwrapped_signal(map: &SEncoded, signal: usize) -> Option<usize> {
        let f = |e: &A| {
            if let A::Signal { symbol } = e {
                Some(*symbol)
            } else {
                None
            }
        };
        SEncoded::get(map, &signal).map_or(None, f)
    }

    let (_, non_linear) = EncodingIterator::take(&mut iter);
    for c in non_linear {
        for signal in C::take_cloned_signals(&c) {
            let signal = unwrapped_signal(renames, signal).unwrap_or(signal);
            if !SEncoded::contains_key(deletes, &signal) {
                HashSet::insert(relevant, signal);
            }
        }
    }

    for edge in EncodingIterator::edges(&iter) {
        let next = EncodingIterator::next(&iter, edge);
        build_relevant_set(next, relevant, renames, deletes)
    }
}

fn remove_not_relevant(substitutions: &mut SEncoded, relevant: &HashSet<usize>) {
    let signals: Vec<_> = substitutions.keys().cloned().collect();
    for signal in signals {
        if !HashSet::contains(&relevant, &signal) {
            SEncoded::remove(substitutions, &signal);
        }
    }
}

/// Count constraints by type: (linear, quadratic, constant, empty)
fn classify_constraints_in_storage(storage: &ConstraintStorage) -> (usize, usize, usize, usize) {
    let mut linear = 0;
    let mut quadratic = 0;
    let mut constant = 0;
    let mut empty = 0;
    for c_id in storage.get_ids() {
        let c = storage.read_constraint(c_id).unwrap();
        if C::is_empty(&c) {
            empty += 1;
        } else if C::is_linear(&c) {
            linear += 1;
        } else {
            quadratic += 1;
        }
    }
    (linear, quadratic, constant, empty)
}

// returns the constraints, the assignment of the witness and the number of inputs in the witness
pub fn simplification(smp: &mut Simplifier) -> (ConstraintStorage, SignalMap, usize) {
    use super::non_linear_utils::obtain_and_simplify_non_linear;
    use circom_algebra::simplification_utils::build_encoded_fast_substitutions;
    use circom_algebra::simplification_utils::fast_encoded_constraint_substitution;
    use std::time::SystemTime;

    let mut substitution_log =
        if smp.port_substitution {
            Some(SubstitutionJSON::new(&smp.json_substitutions).unwrap())
        } else {
             None
        };
    let apply_linear = !smp.flag_s;
    let use_old_heuristics = smp.flag_old_heuristics;
    let field = smp.field.clone();
    let forbidden = Arc::new(std::mem::replace(&mut smp.forbidden, HashSet::with_capacity(0)));
    let no_labels = Simplifier::no_labels(smp);
    let equalities = std::mem::replace(&mut smp.equalities, LinkedList::new());
    let max_signal = smp.max_signal;
    let mut cons_equalities = std::mem::replace(&mut smp.cons_equalities, LinkedList::new());
    let mut linear = std::mem::replace(&mut smp.linear, LinkedList::new());
    let mut deleted = HashSet::new();
    let mut lconst = LinkedList::new();
    let mut no_rounds = smp.no_rounds;
    let remove_unused = true;

    // === PROFILING: initial constraint counts ===
    let prof_initial_equalities = equalities.len();
    let prof_initial_cons_equalities = cons_equalities.len();
    let prof_initial_linear = linear.len();
    let prof_total_time = SystemTime::now();

    eprintln!("{{\"event\":\"profiling_start\",\"initial_equalities\":{},\"initial_cons_equalities\":{},\"initial_linear\":{},\"max_signal\":{},\"no_rounds_config\":{},\"apply_linear\":{},\"use_old_heuristics\":{},\"forbidden_count\":{}}}",
        prof_initial_equalities, prof_initial_cons_equalities, prof_initial_linear,
        max_signal, smp.no_rounds, apply_linear, use_old_heuristics, forbidden.len());

    let relevant_signals = {
        let now = SystemTime::now();
        let mut relevant = HashSet::new();
        let iter = EncodingIterator::new(&smp.dag_encoding);
        let s_sub = HashMap::with_capacity(0);
        let c_sub = HashMap::with_capacity(0);
        build_relevant_set(iter, &mut relevant, &s_sub, &c_sub);
        let _dur = now.elapsed().unwrap().as_millis();
        relevant
    };

    let single_substitutions = {
        let now = SystemTime::now();
        let eq_input_count = equalities.len();
        let (subs, mut cons) = eq_simplification(
            equalities,
            Arc::clone(&forbidden),
            no_labels,
            &field,
            &mut substitution_log,
        );

        let eq_subs_count = subs.len();
        let eq_remaining_cons = cons.len();

        LinkedList::append(&mut lconst, &mut cons);
        let mut substitutions = build_encoded_fast_substitutions(subs);
        for constraint in &mut linear {
            if fast_encoded_constraint_substitution(constraint, &substitutions, &field){
                C::fix_constraint(constraint, &field);
            }
        }
        for constraint in &mut cons_equalities {
            if fast_encoded_constraint_substitution(constraint, &substitutions, &field){
                C::fix_constraint(constraint, &field);
            }
        }
        for signal in substitutions.keys().cloned() {
            deleted.insert(signal);
        }
        remove_not_relevant(&mut substitutions, &relevant_signals);
        let dur = now.elapsed().unwrap().as_millis();

        // === PROFILING: eq_simplification results ===
        eprintln!("{{\"event\":\"eq_simplification\",\"input_constraints\":{},\"substitutions_produced\":{},\"remaining_constraints\":{},\"duration_ms\":{}}}",
            eq_input_count, eq_subs_count, eq_remaining_cons, dur);

        substitutions
    };

    let cons_substitutions = {
        let now = SystemTime::now();
        let ceq_input_count = cons_equalities.len();
        let (subs, mut cons) =
            constant_eq_simplification(cons_equalities, &forbidden, &field, &mut substitution_log);
        let ceq_subs_count = subs.len();
        let ceq_remaining_cons = cons.len();

        LinkedList::append(&mut lconst, &mut cons);
        let substitutions = build_encoded_fast_substitutions(subs);
        for constraint in &mut linear {
            if fast_encoded_constraint_substitution(constraint, &substitutions, &field){
                C::fix_constraint(constraint, &field);
            }
        }
        for signal in substitutions.keys().cloned() {
            deleted.insert(signal);
        }
        let dur = now.elapsed().unwrap().as_millis();

        // === PROFILING: constant_eq_simplification results ===
        eprintln!("{{\"event\":\"constant_eq_simplification\",\"input_constraints\":{},\"substitutions_produced\":{},\"remaining_constraints\":{},\"duration_ms\":{}}}",
            ceq_input_count, ceq_subs_count, ceq_remaining_cons, dur);

        substitutions
    };

    let relevant_signals = {
        let now = SystemTime::now();
        let mut relevant = HashSet::new();
        let iter = EncodingIterator::new(&smp.dag_encoding);
        build_relevant_set(iter, &mut relevant, &single_substitutions, &cons_substitutions);
        let _dur = now.elapsed().unwrap().as_millis();
        relevant
    };

    let linear_substitutions = if apply_linear {
        let now = SystemTime::now();
        let lin_input_count = linear.len();
        let (subs, mut cons) = linear_simplification(
            &mut substitution_log,
            linear,
            Arc::clone(&forbidden),
            no_labels,
            &field,
            use_old_heuristics,
        );
        let lin_subs_count = subs.len();
        let lin_remaining_cons = cons.len();

        let now0 = SystemTime::now();
        let mut only_relevant = LinkedList::new();
        for substitution in subs {
            deleted.insert(*substitution.from());
            if relevant_signals.contains(substitution.from()) {
                only_relevant.push_back(substitution);
            }
        }
        let substitutions = build_encoded_fast_substitutions(only_relevant);
        let _dur0 = now0.elapsed().unwrap().as_millis();
        let dur = now.elapsed().unwrap().as_millis();

        // === PROFILING: linear_simplification results ===
        eprintln!("{{\"event\":\"linear_simplification\",\"input_constraints\":{},\"substitutions_produced\":{},\"remaining_constraints\":{},\"duration_ms\":{}}}",
            lin_input_count, lin_subs_count, lin_remaining_cons, dur);

        LinkedList::append(&mut lconst, &mut cons);
        for constraint in &mut lconst {
            if fast_encoded_constraint_substitution(constraint, &substitutions, &field){
                C::fix_constraint(constraint, &field);
            }
        }
        substitutions
    } else {
        eprintln!("{{\"event\":\"linear_simplification\",\"skipped\":true}}");
        LinkedList::append(&mut lconst, &mut linear);
        HashMap::with_capacity(0)
    };

    let (with_linear, mut constraint_storage) = {
        let now = SystemTime::now();
        let mut frames = LinkedList::new();
        LinkedList::push_back(&mut frames, single_substitutions);
        LinkedList::push_back(&mut frames, cons_substitutions);
        LinkedList::push_back(&mut frames, linear_substitutions);
        let iter = EncodingIterator::new(&smp.dag_encoding);
        let mut storage = ConstraintStorage::new();
        let with_linear = obtain_and_simplify_non_linear(iter, &mut storage, &frames, &field);
        crate::state_utils::empty_encoding_constraints(&mut smp.dag_encoding);
        let dur = now.elapsed().unwrap().as_millis();

        // === PROFILING: non-linear simplification + constraint classification ===
        let (nl_linear, nl_quadratic, nl_constant, nl_empty) = classify_constraints_in_storage(&storage);
        eprintln!("{{\"event\":\"non_linear_simplification\",\"linearized_from_nonlinear\":{},\"storage_linear\":{},\"storage_quadratic\":{},\"storage_constant\":{},\"storage_empty\":{},\"duration_ms\":{}}}",
            with_linear.len(), nl_linear, nl_quadratic, nl_constant, nl_empty, dur);

        if no_rounds > 0{
            no_rounds -= 1;
        }
        (with_linear, storage)
    };

    let mut round_id = 0;
    let _ = round_id;
    let mut linear = with_linear;
    let mut apply_round = apply_linear && no_rounds > 0 && !linear.is_empty();
    let mut non_linear_map = if apply_round || remove_unused {
        let now = SystemTime::now();
        let non_linear_map = build_non_linear_signal_map(&constraint_storage);
        let _dur = now.elapsed().unwrap().as_millis();
        non_linear_map
    } else {
        SignalToConstraints::with_capacity(0)
    };

    // === PROFILING: track iterative rounds ===
    let mut total_round_subs: usize = 0;
    while apply_round {
        let now = SystemTime::now();
        let round_linear_in = linear.len();
        let (substitutions, mut constants) = linear_simplification(
            &mut substitution_log,
            linear,
            Arc::clone(&forbidden),
            no_labels,
            &field,
            use_old_heuristics,
        );

        let round_subs = substitutions.len();
        total_round_subs += round_subs;

        for sub in &substitutions {
            deleted.insert(*sub.from());
        }
        lconst.append(&mut constants);
        for constraint in &mut lconst {
            for substitution in &substitutions {
                C::apply_substitution(constraint, substitution, &field);
            }
            C::fix_constraint(constraint, &field);
        }
        linear = apply_substitution_to_map(
            &mut constraint_storage,
            &mut non_linear_map,
            &substitutions,
            &field,
        );
        round_id += 1;
        no_rounds -= 1;
        apply_round = !linear.is_empty() && no_rounds > 0;
        let dur = now.elapsed().unwrap().as_millis();

        // === PROFILING: per-round stats ===
        eprintln!("{{\"event\":\"optimization_round\",\"round\":{},\"linear_in\":{},\"substitutions_produced\":{},\"new_linear_from_nonlinear\":{},\"continues\":{},\"duration_ms\":{}}}",
            round_id, round_linear_in, round_subs, linear.len(), apply_round, dur);
    }

    for constraint in linear {
        if remove_unused {
            let signals =  C::take_cloned_signals(&constraint);
            let c_id = constraint_storage.add_constraint(constraint);
            for signal in signals {
                if let Some(list) = non_linear_map.get_mut(&signal) {
                    list.push_back(c_id);
                } else {
                    let mut new = LinkedList::new();
                    new.push_back(c_id);
                    non_linear_map.insert(signal, new);
                }
            }
        }
        else{
            constraint_storage.add_constraint(constraint);
        }
    }
    for mut constraint in lconst {
        if remove_unused{
            C::fix_constraint(&mut constraint, &field);
            let signals =  C::take_cloned_signals(&constraint);
            let c_id = constraint_storage.add_constraint(constraint);
            for signal in signals {
                if let Some(list) = non_linear_map.get_mut(&signal) {
                    list.push_back(c_id);
                } else {
                    let mut new = LinkedList::new();
                    new.push_back(c_id);
                    non_linear_map.insert(signal, new);
                }
            }
        }
        else{
            C::fix_constraint(&mut constraint, &field);
            constraint_storage.add_constraint(constraint);
        }
    }

    let erased = crate::non_linear_simplification::simplify(
        &mut constraint_storage,
        &forbidden,
        &field
    );

    for signal in erased {
        deleted.insert(signal);
    }

    let _trash = constraint_storage.extract_with(&|c| C::is_empty(c));

    // === PROFILING: final constraint classification ===
    let (final_linear, final_quadratic, final_constant, final_empty) = classify_constraints_in_storage(&constraint_storage);

    let signal_map = {
        let now = SystemTime::now();
        let signal_map= rebuild_witness(
            max_signal,
            &mut deleted,
            &forbidden,
            non_linear_map,
            remove_unused
        );
        let _dur = now.elapsed().unwrap().as_millis();
       signal_map
    };

    // count the number of deleted inputs
    let max_value_input = smp.no_public_outputs + smp.no_public_inputs + smp.no_private_inputs;
    let mut deleted_inputs = 0;
    for signal in &deleted{
        if signal >= &(smp.no_public_outputs + 1) && signal <= &max_value_input{
            deleted_inputs += 1;
        }
    }


    if let Some(w) = substitution_log {
        w.end().unwrap();
    }

    let total_dur = prof_total_time.elapsed().unwrap().as_millis();

    // === PROFILING: operator usage counts ===
    circom_algebra::algebra::print_operator_profiling();

    // === PROFILING: summary ===
    eprintln!("{{\"event\":\"profiling_end\",\"total_rounds\":{},\"total_round_substitutions\":{},\"final_constraints_linear\":{},\"final_constraints_quadratic\":{},\"final_constraints_constant\":{},\"final_constraints_empty\":{},\"final_constraints_total\":{},\"signals_deleted\":{},\"signals_remaining\":{},\"total_duration_ms\":{}}}",
        round_id, total_round_subs, final_linear, final_quadratic, final_constant, final_empty,
        final_linear + final_quadratic + final_constant,
        deleted.len(), signal_map.len(), total_dur);

    (constraint_storage, signal_map, smp.no_private_inputs - deleted_inputs)
}
