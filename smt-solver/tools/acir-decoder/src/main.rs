use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process::Command;

use base64::Engine;
use clap::Parser;
use flate2::read::GzDecoder;
use serde::Deserialize;
use serde::Serialize;
use serde_json::Value;

#[derive(Parser, Debug)]
#[command(about = "Decode Noir ACIR artifact into structured JSON")]
struct Args {
    /// Path to the Noir artifact JSON file produced by nargo.
    artifact: PathBuf,

    /// Output path for the decoded JSON. Defaults to <artifact>.decoded.json
    #[arg(short, long)]
    output: Option<PathBuf>,
}

#[derive(Debug, Deserialize)]
struct NoirArtifact {
    noir_version: String,
    hash: String,
    abi: Value,
    bytecode: String,
    #[serde(default)]
    debug_symbols: Option<String>,
    #[serde(default)]
    file_map: Value,
    #[serde(default)]
    expression_width: Value,
}

#[derive(Debug, Serialize)]
struct DecodedArtifact {
    artifact_path: String,
    artifact: ArtifactMetadata,
    summary: InspectorSummary,
    inspector_output: InspectorOutput,
}

#[derive(Debug, Serialize)]
struct ArtifactMetadata {
    noir_version: String,
    hash: String,
    abi: Value,
    file_map: Value,
    expression_width: Value,
    bytecode_base64_len: usize,
    compressed_byte_len: usize,
    uncompressed_byte_len: usize,
    debug_symbols_base64_len: usize,
}

#[derive(Debug, Serialize)]
struct InspectorSummary {
    function_count: usize,
    total_opcode_count: usize,
    opcode_kind_counts: BTreeMap<String, usize>,
}

#[derive(Debug, Serialize)]
struct InspectorOutput {
    raw_text: String,
    functions: Vec<FunctionDump>,
}

#[derive(Debug, Serialize)]
struct FunctionDump {
    name: String,
    func_line: Option<String>,
    private_parameters: Vec<String>,
    public_parameters: Vec<String>,
    return_values: Vec<String>,
    opcode_count: usize,
    opcode_kind_counts: BTreeMap<String, usize>,
    opcodes: Vec<OpcodeDump>,
}

#[derive(Debug, Serialize)]
struct OpcodeDump {
    index: usize,
    kind: String,
    text: String,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();
    let output_path = args
        .output
        .clone()
        .unwrap_or_else(|| default_output_path(&args.artifact));

    let artifact_text = fs::read_to_string(&args.artifact)?;
    let artifact: NoirArtifact = serde_json::from_str(&artifact_text)?;

    let compressed = base64::engine::general_purpose::STANDARD.decode(&artifact.bytecode)?;
    let uncompressed = gunzip(&compressed)?;
    let inspector_text = run_noir_inspector(&args.artifact)?;
    let inspector_output = parse_inspector_output(&inspector_text);
    let summary = summarize_inspector_output(&inspector_output);

    let decoded = DecodedArtifact {
        artifact_path: args.artifact.display().to_string(),
        artifact: ArtifactMetadata {
            noir_version: artifact.noir_version,
            hash: artifact.hash,
            abi: artifact.abi,
            file_map: artifact.file_map,
            expression_width: artifact.expression_width,
            bytecode_base64_len: artifact.bytecode.len(),
            compressed_byte_len: compressed.len(),
            uncompressed_byte_len: uncompressed.len(),
            debug_symbols_base64_len: artifact.debug_symbols.as_ref().map_or(0, |s| s.len()),
        },
        summary,
        inspector_output,
    };

    if let Some(parent) = output_path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(output_path, serde_json::to_string_pretty(&decoded)?)?;
    Ok(())
}

fn default_output_path(artifact: &Path) -> PathBuf {
    match artifact.file_name().and_then(|name| name.to_str()) {
        Some(name) => artifact.with_file_name(format!("{name}.decoded.json")),
        None => artifact.with_extension("decoded.json"),
    }
}

fn gunzip(bytes: &[u8]) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut decoder = GzDecoder::new(bytes);
    let mut out = Vec::new();
    decoder.read_to_end(&mut out)?;
    Ok(out)
}

fn run_noir_inspector(artifact: &Path) -> Result<String, Box<dyn std::error::Error>> {
    let inspector_bin =
        env::var("NOIR_INSPECTOR_BIN").unwrap_or_else(|_| "noir-inspector".to_string());
    let output = Command::new(inspector_bin)
        .arg("print-acir")
        .arg(artifact)
        .output()?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("noir-inspector failed: {stderr}").into());
    }
    Ok(String::from_utf8(output.stdout)?)
}

fn parse_inspector_output(text: &str) -> InspectorOutput {
    let mut functions = Vec::new();
    let mut current: Option<FunctionDump> = None;

    for raw_line in text.lines() {
        let line = raw_line.trim();
        if line.is_empty() {
            continue;
        }

        if let Some(name) = line.strip_prefix("Compiled ACIR for ").and_then(|s| s.strip_suffix(':'))
        {
            if let Some(prev) = current.take() {
                functions.push(prev);
            }
            current = Some(FunctionDump {
                name: name.to_string(),
                func_line: None,
                private_parameters: Vec::new(),
                public_parameters: Vec::new(),
                return_values: Vec::new(),
                opcode_count: 0,
                opcode_kind_counts: BTreeMap::new(),
                opcodes: Vec::new(),
            });
            continue;
        }

        let Some(func) = current.as_mut() else {
            continue;
        };

        if let Some(rest) = line.strip_prefix("func ") {
            func.func_line = Some(format!("func {rest}"));
        } else if let Some(rest) = line.strip_prefix("private parameters: ") {
            func.private_parameters = parse_list(rest);
        } else if let Some(rest) = line.strip_prefix("public parameters: ") {
            func.public_parameters = parse_list(rest);
        } else if let Some(rest) = line.strip_prefix("return values: ") {
            func.return_values = parse_list(rest);
        } else {
            let kind = opcode_kind_from_text(line);
            *func.opcode_kind_counts.entry(kind.clone()).or_insert(0) += 1;
            func.opcodes.push(OpcodeDump {
                index: func.opcodes.len(),
                kind,
                text: line.to_string(),
            });
        }
    }

    if let Some(prev) = current.take() {
        functions.push(prev);
    }

    for func in &mut functions {
        func.opcode_count = func.opcodes.len();
    }

    InspectorOutput { raw_text: text.to_string(), functions }
}

fn parse_list(text: &str) -> Vec<String> {
    let trimmed = text.trim();
    let inner = trimmed
        .strip_prefix('[')
        .and_then(|s| s.strip_suffix(']'))
        .unwrap_or(trimmed)
        .trim();
    if inner.is_empty() {
        Vec::new()
    } else {
        inner.split(',').map(|part| part.trim().to_string()).collect()
    }
}

fn opcode_kind_from_text(line: &str) -> String {
    if let Some((first, _)) = line.split_once(' ') {
        first.to_string()
    } else {
        line.to_string()
    }
}

fn summarize_inspector_output(output: &InspectorOutput) -> InspectorSummary {
    let mut opcode_kind_counts = BTreeMap::new();
    let mut total_opcode_count = 0;
    for func in &output.functions {
        total_opcode_count += func.opcodes.len();
        for (kind, count) in &func.opcode_kind_counts {
            *opcode_kind_counts.entry(kind.clone()).or_insert(0) += count;
        }
    }

    InspectorSummary {
        function_count: output.functions.len(),
        total_opcode_count,
        opcode_kind_counts,
    }
}
