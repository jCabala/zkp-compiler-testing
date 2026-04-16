use circ::cfg::{cfg, CircOpt};
use circ::front::zsharp::{self, ZSharpFE};
use circ::front::{FrontEnd, Mode};
use circ::ir::opt::{opt, Opt};
use circ::target::r1cs::opt::reduce_linearities;
use circ::target::r1cs::trans::to_r1cs;
use clap::Parser;
use serde::Serialize;
use std::collections::HashSet;
use std::fs::File;
use std::path::PathBuf;

#[derive(Debug, Parser)]
#[command(name = "circ_exporter")]
struct Options {
    #[arg(name = "PATH")]
    path: PathBuf,

    #[arg(long, short = 'o')]
    output: PathBuf,

    #[command(flatten)]
    circ: CircOpt,
}

#[derive(Serialize)]
struct Exported<'a> {
    r1cs: &'a circ::target::r1cs::R1csFinal,
    input_names: Vec<String>,
    public_input_names: HashSet<String>,
}

fn main() {
    env_logger::Builder::from_default_env()
        .format_level(false)
        .format_timestamp(None)
        .init();

    let options = Options::parse();
    circ::cfg::set(&options.circ);

    let inputs = zsharp::Inputs {
        file: options.path,
        mode: Mode::Proof,
    };
    let cs = ZSharpFE::gen(inputs);
    let input_names = cs.get("main").metadata.ordered_input_names();
    let public_input_names: HashSet<String> =
        cs.get("main").metadata.public_input_names_set().into_iter().collect();

    let cs = opt(
        cs,
        vec![
            Opt::ScalarizeVars,
            Opt::Flatten,
            Opt::Sha,
            Opt::ConstantFold(Box::new([])),
            Opt::Flatten,
            Opt::Inline,
            Opt::Tuple,
            Opt::ConstantFold(Box::new([])),
            Opt::Obliv,
            Opt::Tuple,
            Opt::LinearScan,
            Opt::Tuple,
            Opt::Flatten,
            Opt::ConstantFold(Box::new([])),
            Opt::Inline,
        ],
    );

    let r1cs = reduce_linearities(to_r1cs(cs.get("main"), cfg()), cfg());
    let (pd, _vd) = r1cs.finalize(cs.get("main"));
    let exported = Exported {
        r1cs: &pd.r1cs,
        input_names,
        public_input_names,
    };

    let output = File::create(options.output).expect("create output");
    serde_json::to_writer_pretty(output, &exported).expect("serialize export");
}
