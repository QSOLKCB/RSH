//! Deterministic Rust implementation of the RSH tissue contract.
//!
//! The Python implementation remains the readable tissue reference. This crate
//! ports the same bounded cell graph, tick order, functional Q_f metric, and
//! chained receipt policy for native and WebAssembly conformance. Q_f is a
//! functional simulation metric only; it is not evidence of life, consciousness,
//! subjective awareness, or qualia.

use rsh_core::{build_and_verify, kappa_max, psi, ModelConfig, MODEL_NAME, MODEL_VERSION};
use serde::Serialize;
use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::f64::consts::{PI, TAU};

pub const TISSUE_CONTRACT_VERSION: &str = "1.0.0";
pub const TISSUE_SCHEMA: &str = "RSH-TISSUE-REPORT-V1";
pub const TICK_SCHEMA: &str = "RSH-TISSUE-TICK-V1";
pub const CONSTITUTION_SCHEMA: &str = "RSH-CONSTITUTION-V1";
pub const CONSTITUTION_VERSION: &str = "1.0.0";
pub const EXPECTED_CONSTITUTION_HASH: &str =
    "090416435f8ae2adc7555dab356eafef7aadfeabdb99c68e7c381ddf3bf9e544";
pub const TISSUE_RECEIPT_DOMAIN: &[u8] = b"RSH-TISSUE-EVIDENCE-V1\0";
pub const TICK_RECEIPT_DOMAIN: &[u8] = b"RSH-TISSUE-TICK-V1\0";
pub const CONSTITUTION_DOMAIN: &[u8] = b"RSH-CONSTITUTION-V1\0";
pub const MAX_TISSUE_WORK: usize = 5_000_000;
pub const MAX_TISSUE_CELLS: usize = 4096;
pub const MAX_TISSUE_TICKS: usize = 100_000;
pub const MAX_GEOMETRY_SAMPLES: usize = 262_145;
pub const OBSERVABLE_TOLERANCE: f64 = 1.0e-12;
pub const PYTHON_REFERENCE_FIRST_Q_F: f64 = 0.2623914043443579;
pub const PYTHON_REFERENCE_FINAL_Q_F: f64 = 0.37926532158281384;
pub const PYTHON_REFERENCE_MIN_Q_F: f64 = 0.2623914043443579;
pub const PYTHON_REFERENCE_MAX_Q_F: f64 = 0.37926532158281384;
pub const PYTHON_REFERENCE_FINAL_DISSOCIATION: f64 = 0.00005863114611954213;
pub const PYTHON_REFERENCE_REPORT_RECEIPT: &str =
    "732fc6ccc5af543881528da7f9ec7717817af97c07e7f7973512685ab67e2622";
const CANONICAL_FLOAT_PRECISION: usize = 12;
const ROLES: [&str; 3] = ["R", "W", "P"];

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum SidecarBackend {
    None,
    Webgpu,
    Cuda,
    Npu,
}

impl SidecarBackend {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::Webgpu => "webgpu",
            Self::Cuda => "cuda",
            Self::Npu => "npu",
        }
    }

    pub fn from_name(value: &str) -> Result<Self, String> {
        match value {
            "none" => Ok(Self::None),
            "webgpu" => Ok(Self::Webgpu),
            "cuda" => Ok(Self::Cuda),
            "npu" => Ok(Self::Npu),
            _ => Err("sidecar_backend must be one of none, webgpu, cuda, npu".into()),
        }
    }

    pub fn from_code(value: u32) -> Result<Self, String> {
        match value {
            0 => Ok(Self::None),
            1 => Ok(Self::Webgpu),
            2 => Ok(Self::Cuda),
            3 => Ok(Self::Npu),
            _ => Err("sidecar backend code must be in [0, 3]".into()),
        }
    }

    pub const fn code(self) -> u32 {
        match self {
            Self::None => 0,
            Self::Webgpu => 1,
            Self::Cuda => 2,
            Self::Npu => 3,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct TissueConfig {
    pub cells: usize,
    pub ticks: usize,
    pub geometry_samples: usize,
    pub ds: f64,
    pub phase_coupling: f64,
    pub binding_diffusion: f64,
    pub sidecar_backend: SidecarBackend,
    pub sidecar_residual: f64,
    pub residual_gate: f64,
    pub qf_floor: f64,
}

impl Default for TissueConfig {
    fn default() -> Self {
        Self {
            cells: 8,
            ticks: 20,
            geometry_samples: 129,
            ds: 0.05,
            phase_coupling: 0.25,
            binding_diffusion: 0.15,
            sidecar_backend: SidecarBackend::None,
            sidecar_residual: 0.0,
            residual_gate: 1.0e-4,
            qf_floor: 0.0,
        }
    }
}

impl TissueConfig {
    pub fn validate(self) -> Result<Self, String> {
        if !(3..=MAX_TISSUE_CELLS).contains(&self.cells) {
            return Err(format!("cells must be in [3, {MAX_TISSUE_CELLS}]"));
        }
        if !(1..=MAX_TISSUE_TICKS).contains(&self.ticks) {
            return Err(format!("ticks must be in [1, {MAX_TISSUE_TICKS}]"));
        }
        let work = self
            .cells
            .checked_mul(self.ticks)
            .ok_or_else(|| "cells × ticks overflowed the bounded work counter".to_string())?;
        if work > MAX_TISSUE_WORK {
            return Err("cells × ticks exceeds the bounded tissue work limit".into());
        }
        if self.geometry_samples < self.cells
            || self.geometry_samples < 3
            || self.geometry_samples > MAX_GEOMETRY_SAMPLES
            || self.geometry_samples.is_multiple_of(2)
        {
            return Err(format!(
                "geometry_samples must be odd, at least cells, and no more than {MAX_GEOMETRY_SAMPLES}"
            ));
        }
        for (name, value) in [
            ("ds", self.ds),
            ("phase_coupling", self.phase_coupling),
            ("binding_diffusion", self.binding_diffusion),
            ("sidecar_residual", self.sidecar_residual),
            ("residual_gate", self.residual_gate),
            ("qf_floor", self.qf_floor),
        ] {
            if !value.is_finite() {
                return Err(format!("{name} must be finite"));
            }
        }
        if !(0.0 < self.ds && self.ds <= 1.0) {
            return Err("ds must be in (0, 1]".into());
        }
        if !(0.0..=1.0).contains(&self.phase_coupling) {
            return Err("phase_coupling must be in [0, 1]".into());
        }
        if !(0.0..=1.0).contains(&self.binding_diffusion) {
            return Err("binding_diffusion must be in [0, 1]".into());
        }
        if self.sidecar_residual < 0.0 {
            return Err("sidecar_residual must be non-negative".into());
        }
        if self.residual_gate <= 0.0 {
            return Err("residual_gate must be positive".into());
        }
        if !(0.0..=1.0).contains(&self.qf_floor) {
            return Err("qf_floor must be in [0, 1]".into());
        }
        if self.sidecar_backend == SidecarBackend::None && self.sidecar_residual != 0.0 {
            return Err("sidecar_residual must be zero when no sidecar is requested".into());
        }
        Ok(self)
    }
}

#[derive(Clone, Debug, PartialEq)]
struct CellState {
    id: String,
    x: f64,
    y: f64,
    z: f64,
    kappa: f64,
    tau: f64,
    phase: f64,
    role: String,
    binding: f64,
    prediction_error: f64,
}

impl CellState {
    fn project_bounds(&mut self) -> bool {
        let before = (self.kappa, self.tau);
        self.kappa = clamp(self.kappa, 0.0, kappa_max());
        self.tau = clamp(self.tau, 1.0e-12, 1.0 - 1.0e-12);
        before != (self.kappa, self.tau)
    }
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct CellSnapshot {
    pub id: String,
    pub x: f64,
    pub y: f64,
    pub z: f64,
    pub kappa: f64,
    pub tau: f64,
    pub phase: f64,
    pub role: String,
    pub binding: f64,
    pub prediction_error: f64,
}

#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct TissueMetrics {
    pub phase_coherence: f64,
    pub binding_cohesion: f64,
    pub predictive_stability: f64,
    pub edge_continuity: f64,
    pub role_coverage: f64,
    pub dissociation: f64,
    pub q_f: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct TissueTick {
    pub schema: String,
    pub index: usize,
    pub previous_receipt: String,
    pub centre_shift: [f64; 3],
    pub centre_error: f64,
    pub bound_fixes: usize,
    pub sidecar_accepted: bool,
    pub fallback_used: bool,
    pub metrics: TissueMetrics,
    pub receipt: String,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct TissueReport {
    pub schema: String,
    pub tissue_contract: String,
    pub geometry_model: String,
    pub geometry_model_contract: String,
    pub constitution_version: String,
    pub constitution_hash: String,
    pub config: TissueConfig,
    pub seed_geometry_receipt: String,
    pub edges: Vec<[usize; 2]>,
    pub roles: Vec<String>,
    pub ticks: Vec<TissueTick>,
    pub final_cells: Vec<CellSnapshot>,
    pub final_q_f: f64,
    pub min_q_f: f64,
    pub max_q_f: f64,
    pub sidecar_accepted: bool,
    pub fallback_used: bool,
    pub pass_constitution: bool,
    pub pass_bounds: bool,
    pub pass_centre: bool,
    pub pass_qf_floor: bool,
    pub audit_chain_valid: bool,
    pub pass_all: bool,
    pub receipt: String,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct TissueConformanceResult {
    pub schema: String,
    pub pass: bool,
    pub observable_absolute_tolerance: f64,
    pub first_q_f_error: f64,
    pub final_q_f_error: f64,
    pub minimum_q_f_error: f64,
    pub maximum_q_f_error: f64,
    pub final_dissociation_error: f64,
    pub constitution_hash_matches: bool,
    pub python_reference_report_receipt: String,
    pub rust_report_receipt: String,
    pub cross_runtime_receipt_identity_required: bool,
    pub cross_runtime_receipt_identical: bool,
}

fn clamp(value: f64, lower: f64, upper: f64) -> f64 {
    value.max(lower).min(upper)
}

fn angle_delta(target: f64, current: f64) -> f64 {
    (target - current + PI).rem_euclid(TAU) - PI
}

fn python_scientific(value: f64) -> Result<String, String> {
    if !value.is_finite() {
        return Err("non-finite tissue evidence value".into());
    }
    let raw = format!("{:.*e}", CANONICAL_FLOAT_PRECISION, value);
    let (mantissa, exponent) = raw
        .split_once('e')
        .ok_or_else(|| "failed to encode canonical tissue float".to_string())?;
    let exponent: i32 = exponent
        .parse()
        .map_err(|_| "failed to parse canonical tissue exponent".to_string())?;
    Ok(format!("{mantissa}e{exponent:+03}"))
}

fn canonicalize(value: Value) -> Result<Value, String> {
    match value {
        Value::Number(number) if number.is_f64() => {
            let value = number
                .as_f64()
                .ok_or_else(|| "failed to decode canonical tissue float".to_string())?;
            Ok(Value::String(python_scientific(value)?))
        }
        Value::Array(values) => Ok(Value::Array(
            values
                .into_iter()
                .map(canonicalize)
                .collect::<Result<Vec<_>, _>>()?,
        )),
        Value::Object(values) => {
            let mut sorted = BTreeMap::new();
            for (key, value) in values {
                sorted.insert(key, canonicalize(value)?);
            }
            let mut output = Map::new();
            for (key, value) in sorted {
                output.insert(key, value);
            }
            Ok(Value::Object(output))
        }
        other => Ok(other),
    }
}

fn digest_value(domain: &[u8], payload: Value) -> Result<String, String> {
    let canonical = canonicalize(payload)?;
    let encoded = serde_json::to_vec(&canonical).map_err(|error| error.to_string())?;
    let mut hasher = Sha256::new();
    hasher.update(domain);
    hasher.update(encoded);
    Ok(format!("{:x}", hasher.finalize()))
}

fn receipt_without_field<T: Serialize>(domain: &[u8], payload: &T) -> Result<String, String> {
    let mut value = serde_json::to_value(payload).map_err(|error| error.to_string())?;
    let object = value
        .as_object_mut()
        .ok_or_else(|| "receipted tissue value must be an object".to_string())?;
    object.remove("receipt");
    digest_value(domain, value)
}

pub fn constitution_hash() -> Result<String, String> {
    let payload = json!({
        "schema": CONSTITUTION_SCHEMA,
        "version": CONSTITUTION_VERSION,
        "geometry_model": MODEL_NAME,
        "geometry_model_contract": MODEL_VERSION,
        "invariants": {
            "psi": psi(),
            "kappa_interval": [0.0, kappa_max()],
            "tau_interval": {
                "lower": 0.0,
                "upper": 1.0,
                "open": true
            },
            "geometry_centring": "discrete-midpoint-to-origin",
            "tissue_centring": "shared-centroid-to-origin",
            "oracle_authority": ["f64-cpu", "f64-wasm"],
            "accelerator_authority": "residual-sidecar-only",
            "geometry_receipt_domain": "RSH-GEOMETRY-EVIDENCE-V2"
        },
        "ordered_objectives": [
            "invariant_integrity",
            "oracle_fidelity",
            "tissue_cohesion_qf",
            "resource_cost",
            "role_coverage"
        ],
        "governance": {
            "non_escalating_refinement": "dry-run-and-seal",
            "contract_escalation": "explicit-human-ack-required",
            "human_veto": "authoritative"
        },
        "refusals": [
            "silent-bound-violation",
            "accelerator-as-oracle",
            "audit-chain-deletion",
            "subjective-awareness-or-qualia-claim"
        ],
        "terminology": {
            "operational_awareness": "state observation, prediction, audit and reporting only",
            "bound_safe_asymptotic_refinement": "iterated accepted proposals under a fixed constitution; not unbounded autonomous takeoff"
        }
    });
    digest_value(CONSTITUTION_DOMAIN, payload)
}

fn sample_indices(samples: usize, cells: usize) -> Vec<usize> {
    (0..cells)
        .map(|index| index * (samples - 1) / (cells - 1))
        .collect()
}

fn snapshot(cell: &CellState) -> CellSnapshot {
    CellSnapshot {
        id: cell.id.clone(),
        x: cell.x,
        y: cell.y,
        z: cell.z,
        kappa: cell.kappa,
        tau: cell.tau,
        phase: cell.phase,
        role: cell.role.clone(),
        binding: cell.binding,
        prediction_error: cell.prediction_error,
    }
}

fn initial_state(
    config: TissueConfig,
) -> Result<(Vec<CellState>, Vec<[usize; 2]>, String), String> {
    let model = ModelConfig {
        samples: config.geometry_samples,
        ..ModelConfig::default()
    }
    .validate()?;
    let (rows, geometry_report) = build_and_verify(model)?;
    let indices = sample_indices(rows.len(), config.cells);

    let mut cells = Vec::with_capacity(config.cells);
    for (index, sample_index) in indices.into_iter().enumerate() {
        let sample = rows[sample_index];
        cells.push(CellState {
            id: format!("C{index}"),
            x: sample.x,
            y: sample.y,
            z: sample.z,
            kappa: sample.kappa,
            tau: sample.tau,
            phase: sample.ty.atan2(sample.tx).rem_euclid(TAU),
            role: ROLES[index % ROLES.len()].to_string(),
            binding: (index + 1) as f64 / (config.cells + 1) as f64,
            prediction_error: 0.0,
        });
    }

    let mut edges = BTreeSet::new();
    for index in 0..config.cells {
        edges.insert((index, (index + 1) % config.cells));
    }
    if config.cells >= 4 {
        let half = config.cells / 2;
        for index in (0..config.cells).step_by(2) {
            let other = (index + half) % config.cells;
            let edge = if index <= other {
                (index, other)
            } else {
                (other, index)
            };
            if edge.0 != edge.1 {
                edges.insert(edge);
            }
        }
    }

    Ok((
        cells,
        edges
            .into_iter()
            .map(|(left, right)| [left, right])
            .collect(),
        geometry_report.receipt,
    ))
}

fn neighbours(count: usize, edges: &[[usize; 2]]) -> Vec<Vec<usize>> {
    let mut result = vec![Vec::new(); count];
    for [left, right] in edges.iter().copied() {
        result[left].push(right);
        result[right].push(left);
    }
    result
}

fn shared_centre(cells: &mut [CellState]) -> [f64; 3] {
    let count = cells.len() as f64;
    let centre = [
        cells.iter().map(|cell| cell.x).sum::<f64>() / count,
        cells.iter().map(|cell| cell.y).sum::<f64>() / count,
        cells.iter().map(|cell| cell.z).sum::<f64>() / count,
    ];
    for cell in cells {
        cell.x -= centre[0];
        cell.y -= centre[1];
        cell.z -= centre[2];
    }
    centre
}

fn centre_error(cells: &[CellState]) -> f64 {
    let count = cells.len() as f64;
    let x = cells.iter().map(|cell| cell.x).sum::<f64>() / count;
    let y = cells.iter().map(|cell| cell.y).sum::<f64>() / count;
    let z = cells.iter().map(|cell| cell.z).sum::<f64>() / count;
    x.hypot(y).hypot(z)
}

fn phase_lock(cells: &mut [CellState], amount: f64) {
    let sine = cells.iter().map(|cell| cell.phase.sin()).sum::<f64>();
    let cosine = cells.iter().map(|cell| cell.phase.cos()).sum::<f64>();
    let target = sine.atan2(cosine);
    for cell in cells {
        cell.phase = (cell.phase + amount * angle_delta(target, cell.phase)).rem_euclid(TAU);
    }
}

fn binding_diffuse(cells: &mut [CellState], adjacent: &[Vec<usize>], amount: f64) {
    let mut values = Vec::with_capacity(cells.len());
    for (index, cell) in cells.iter().enumerate() {
        if adjacent[index].is_empty() {
            values.push(cell.binding);
            continue;
        }
        let mean = adjacent[index]
            .iter()
            .map(|item| cells[*item].binding)
            .sum::<f64>()
            / adjacent[index].len() as f64;
        let curvature_pressure = 0.002 * (cell.kappa / kappa_max());
        values.push(
            (cell.binding + amount * (mean - cell.binding) - curvature_pressure).max(1.0e-12),
        );
    }
    for (cell, value) in cells.iter_mut().zip(values) {
        cell.binding = value;
    }
}

fn prediction_errors(cells: &mut [CellState], adjacent: &[Vec<usize>]) {
    let phases = cells.iter().map(|cell| cell.phase).collect::<Vec<_>>();
    let taus = cells.iter().map(|cell| cell.tau).collect::<Vec<_>>();
    for (index, cell) in cells.iter_mut().enumerate() {
        if adjacent[index].is_empty() {
            cell.prediction_error = 0.0;
            continue;
        }
        let sine = adjacent[index]
            .iter()
            .map(|item| phases[*item].sin())
            .sum::<f64>();
        let cosine = adjacent[index]
            .iter()
            .map(|item| phases[*item].cos())
            .sum::<f64>();
        let target = sine.atan2(cosine);
        let phase_error = angle_delta(target, phases[index]).abs() / PI;
        let tau_error = adjacent[index]
            .iter()
            .map(|item| (taus[index] - taus[*item]).abs())
            .sum::<f64>()
            / adjacent[index].len() as f64;
        cell.prediction_error = 0.75 * phase_error + 0.25 * tau_error;
    }
}

fn edge_lengths(cells: &[CellState], edges: &[[usize; 2]]) -> Vec<f64> {
    edges
        .iter()
        .map(|[left, right]| {
            let dx = cells[*left].x - cells[*right].x;
            let dy = cells[*left].y - cells[*right].y;
            let dz = cells[*left].z - cells[*right].z;
            dx.hypot(dy).hypot(dz)
        })
        .collect()
}

fn metrics(
    cells: &[CellState],
    edges: &[[usize; 2]],
    bound_fixes: usize,
    sidecar_pressure: f64,
) -> TissueMetrics {
    let count = cells.len() as f64;
    let cosine = cells.iter().map(|cell| cell.phase.cos()).sum::<f64>();
    let sine = cells.iter().map(|cell| cell.phase.sin()).sum::<f64>();
    let phase_coherence = clamp(cosine.hypot(sine) / count, 0.0, 1.0);

    let binding_mean = cells.iter().map(|cell| cell.binding).sum::<f64>() / count;
    let binding_cohesion = if binding_mean <= 1.0e-15 {
        0.0
    } else {
        let variance = cells
            .iter()
            .map(|cell| (cell.binding - binding_mean).powi(2))
            .sum::<f64>()
            / count;
        1.0 / (1.0 + variance.sqrt() / binding_mean)
    };

    let predictive_stability =
        (-cells.iter().map(|cell| cell.prediction_error).sum::<f64>() / count).exp();

    let lengths = edge_lengths(cells, edges);
    let edge_continuity = if lengths.is_empty() {
        1.0
    } else {
        let mean = lengths.iter().sum::<f64>() / lengths.len() as f64;
        let variance = lengths
            .iter()
            .map(|value| (*value - mean).powi(2))
            .sum::<f64>()
            / lengths.len() as f64;
        (-variance.sqrt() / (mean + 1.0e-15)).exp()
    };

    let mut roles = BTreeSet::new();
    for cell in cells {
        roles.insert(cell.role.as_str());
    }
    let role_coverage = roles.len() as f64 / ROLES.len() as f64;
    let fix_pressure = (bound_fixes as f64 / (2 * edges.len()).max(1) as f64).min(1.0);
    let dissociation = clamp(
        0.55 * (1.0 - phase_coherence) + 0.25 * fix_pressure + 0.20 * sidecar_pressure,
        0.0,
        1.0,
    );
    let q_f = clamp(
        phase_coherence
            * binding_cohesion
            * predictive_stability
            * edge_continuity
            * role_coverage
            * (1.0 - dissociation),
        0.0,
        1.0,
    );

    TissueMetrics {
        phase_coherence,
        binding_cohesion,
        predictive_stability,
        edge_continuity,
        role_coverage,
        dissociation,
        q_f,
    }
}

fn tick_receipt(tick: &TissueTick) -> Result<String, String> {
    receipt_without_field(TICK_RECEIPT_DOMAIN, tick)
}

fn report_receipt(report: &TissueReport) -> Result<String, String> {
    receipt_without_field(TISSUE_RECEIPT_DOMAIN, report)
}

pub fn validate_audit_chain(
    ticks: &[TissueTick],
    seed_receipt: &str,
    expected_ticks: usize,
    terminal_receipt: Option<&str>,
) -> bool {
    if expected_ticks < 1 || ticks.len() != expected_ticks || seed_receipt.is_empty() {
        return false;
    }
    let mut previous = seed_receipt.to_string();
    for (offset, tick) in ticks.iter().enumerate() {
        if tick.schema != TICK_SCHEMA || tick.index != offset + 1 {
            return false;
        }
        if tick.previous_receipt != previous {
            return false;
        }
        let expected = match tick_receipt(tick) {
            Ok(receipt) => receipt,
            Err(_) => return false,
        };
        if tick.receipt != expected {
            return false;
        }
        previous = tick.receipt.clone();
    }
    terminal_receipt.is_none_or(|terminal| terminal == previous)
}

pub fn simulate_tissue(config: TissueConfig) -> Result<TissueReport, String> {
    let config = config.validate()?;
    let (mut cells, edges, seed_receipt) = initial_state(config)?;
    let adjacent = neighbours(cells.len(), &edges);
    let mut ticks = Vec::with_capacity(config.ticks);
    let mut previous_receipt = seed_receipt.clone();

    let sidecar_requested = config.sidecar_backend != SidecarBackend::None;
    let sidecar_accepted = sidecar_requested && config.sidecar_residual <= config.residual_gate;
    let fallback_used = sidecar_requested && !sidecar_accepted;
    let sidecar_pressure = if sidecar_requested {
        (config.sidecar_residual / config.residual_gate).min(1.0)
    } else {
        0.0
    };

    for tick_index in 1..=config.ticks {
        let mut bound_fixes = 0_usize;
        for cell in &mut cells {
            bound_fixes += usize::from(cell.project_bounds());
            cell.phase = (cell.phase + cell.tau * config.ds * psi()).rem_euclid(TAU);
            let speed = (1.0 - 0.35 * (cell.kappa / kappa_max())).max(0.05);
            cell.x += config.ds * cell.phase.cos() * speed;
            cell.y += config.ds * cell.phase.sin() * speed;
            cell.z += config.ds * cell.tau * 0.1;
            bound_fixes += usize::from(cell.project_bounds());
        }

        phase_lock(&mut cells, config.phase_coupling);
        binding_diffuse(&mut cells, &adjacent, config.binding_diffusion);
        prediction_errors(&mut cells, &adjacent);
        let centre_shift = shared_centre(&mut cells);
        let centre_error = centre_error(&cells);
        let metrics = metrics(&cells, &edges, bound_fixes, sidecar_pressure);

        let mut tick = TissueTick {
            schema: TICK_SCHEMA.to_string(),
            index: tick_index,
            previous_receipt,
            centre_shift,
            centre_error,
            bound_fixes,
            sidecar_accepted,
            fallback_used,
            metrics,
            receipt: String::new(),
        };
        tick.receipt = tick_receipt(&tick)?;
        previous_receipt = tick.receipt.clone();
        ticks.push(tick);
    }

    let final_cells = cells.iter().map(snapshot).collect::<Vec<_>>();
    let q_values = ticks
        .iter()
        .map(|tick| tick.metrics.q_f)
        .collect::<Vec<_>>();
    let computed_constitution_hash = constitution_hash()?;
    let pass_constitution = computed_constitution_hash == EXPECTED_CONSTITUTION_HASH;
    let pass_bounds = final_cells.iter().all(|cell| {
        0.0 <= cell.kappa && cell.kappa <= kappa_max() && 0.0 < cell.tau && cell.tau < 1.0
    });
    let pass_centre = ticks
        .iter()
        .map(|tick| tick.centre_error)
        .fold(0.0_f64, f64::max)
        <= OBSERVABLE_TOLERANCE;
    let pass_qf_floor = q_values[q_values.len() - 1] >= config.qf_floor;
    let audit_chain_valid = validate_audit_chain(&ticks, &seed_receipt, config.ticks, None);
    let pass_all =
        pass_constitution && pass_bounds && pass_centre && pass_qf_floor && audit_chain_valid;

    let mut report = TissueReport {
        schema: TISSUE_SCHEMA.to_string(),
        tissue_contract: TISSUE_CONTRACT_VERSION.to_string(),
        geometry_model: MODEL_NAME.to_string(),
        geometry_model_contract: MODEL_VERSION.to_string(),
        constitution_version: CONSTITUTION_VERSION.to_string(),
        constitution_hash: computed_constitution_hash,
        config,
        seed_geometry_receipt: seed_receipt,
        edges,
        roles: final_cells.iter().map(|cell| cell.role.clone()).collect(),
        ticks,
        final_cells,
        final_q_f: q_values[q_values.len() - 1],
        min_q_f: q_values.iter().copied().fold(f64::INFINITY, f64::min),
        max_q_f: q_values.iter().copied().fold(f64::NEG_INFINITY, f64::max),
        sidecar_accepted,
        fallback_used,
        pass_constitution,
        pass_bounds,
        pass_centre,
        pass_qf_floor,
        audit_chain_valid,
        pass_all,
        receipt: String::new(),
    };
    report.receipt = report_receipt(&report)?;
    Ok(report)
}

pub fn tissue_report_json(report: &TissueReport) -> Result<String, String> {
    serde_json::to_string_pretty(report)
        .map(|text| format!("{text}\n"))
        .map_err(|error| error.to_string())
}

pub fn tissue_trace_csv(report: &TissueReport) -> String {
    let mut output = String::from(
        "tick,centre_error,bound_fixes,phase_coherence,binding_cohesion,predictive_stability,edge_continuity,role_coverage,dissociation,q_f,sidecar_accepted,fallback_used,receipt\n",
    );
    for tick in &report.ticks {
        output.push_str(&format!(
            "{},{:.17e},{},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{},{},{}\n",
            tick.index,
            tick.centre_error,
            tick.bound_fixes,
            tick.metrics.phase_coherence,
            tick.metrics.binding_cohesion,
            tick.metrics.predictive_stability,
            tick.metrics.edge_continuity,
            tick.metrics.role_coverage,
            tick.metrics.dissociation,
            tick.metrics.q_f,
            tick.sidecar_accepted,
            tick.fallback_used,
            tick.receipt,
        ));
    }
    output
}

pub fn check_python_conformance() -> Result<TissueConformanceResult, String> {
    let report = simulate_tissue(TissueConfig::default())?;
    let first_q_f_error = (report.ticks[0].metrics.q_f - PYTHON_REFERENCE_FIRST_Q_F).abs();
    let final_q_f_error = (report.final_q_f - PYTHON_REFERENCE_FINAL_Q_F).abs();
    let minimum_q_f_error = (report.min_q_f - PYTHON_REFERENCE_MIN_Q_F).abs();
    let maximum_q_f_error = (report.max_q_f - PYTHON_REFERENCE_MAX_Q_F).abs();
    let final_dissociation_error = (report.ticks[report.ticks.len() - 1].metrics.dissociation
        - PYTHON_REFERENCE_FINAL_DISSOCIATION)
        .abs();
    let constitution_hash_matches = report.constitution_hash == EXPECTED_CONSTITUTION_HASH;
    let pass = report.pass_all
        && constitution_hash_matches
        && first_q_f_error <= OBSERVABLE_TOLERANCE
        && final_q_f_error <= OBSERVABLE_TOLERANCE
        && minimum_q_f_error <= OBSERVABLE_TOLERANCE
        && maximum_q_f_error <= OBSERVABLE_TOLERANCE
        && final_dissociation_error <= OBSERVABLE_TOLERANCE;
    Ok(TissueConformanceResult {
        schema: "RSH-TISSUE-RUST-CONFORMANCE-V1".into(),
        pass,
        observable_absolute_tolerance: OBSERVABLE_TOLERANCE,
        first_q_f_error,
        final_q_f_error,
        minimum_q_f_error,
        maximum_q_f_error,
        final_dissociation_error,
        constitution_hash_matches,
        python_reference_report_receipt: PYTHON_REFERENCE_REPORT_RECEIPT.into(),
        rust_report_receipt: report.receipt.clone(),
        cross_runtime_receipt_identity_required: false,
        cross_runtime_receipt_identical: report.receipt == PYTHON_REFERENCE_REPORT_RECEIPT,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_profile_conforms_to_python_observables() {
        let result = check_python_conformance().expect("default tissue conformance");
        assert!(result.pass, "{result:?}");
    }

    #[test]
    fn same_runtime_replay_is_receipt_identical() {
        let first = simulate_tissue(TissueConfig::default()).expect("first tissue run");
        let second = simulate_tissue(TissueConfig::default()).expect("second tissue run");
        assert_eq!(first, second);
        assert_eq!(first.receipt, second.receipt);
    }

    #[test]
    fn audit_chain_rejects_truncation_and_wrong_terminal() {
        let report = simulate_tissue(TissueConfig::default()).expect("tissue report");
        assert!(!validate_audit_chain(
            &report.ticks[..report.ticks.len() - 1],
            &report.seed_geometry_receipt,
            report.config.ticks,
            None,
        ));
        assert!(!validate_audit_chain(
            &report.ticks,
            &report.seed_geometry_receipt,
            report.config.ticks,
            Some("not-the-terminal-receipt"),
        ));
    }

    #[test]
    fn rejected_sidecar_records_cpu_fallback() {
        let report = simulate_tissue(TissueConfig {
            sidecar_backend: SidecarBackend::Webgpu,
            sidecar_residual: 2.0e-4,
            residual_gate: 1.0e-4,
            ticks: 3,
            ..TissueConfig::default()
        })
        .expect("fallback tissue report");
        assert!(!report.sidecar_accepted);
        assert!(report.fallback_used);
        assert!(report.pass_all);
    }

    #[test]
    fn invalid_work_and_even_geometry_are_rejected() {
        assert!(TissueConfig {
            cells: 4096,
            ticks: 100_000,
            ..TissueConfig::default()
        }
        .validate()
        .is_err());
        assert!(TissueConfig {
            geometry_samples: 128,
            ..TissueConfig::default()
        }
        .validate()
        .is_err());
    }
}
