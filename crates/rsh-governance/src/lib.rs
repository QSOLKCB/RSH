//! RSH v4 epistemic and conformance governance.
//!
//! This crate does not redefine RSH geometry. It provides machine-readable
//! evidence classification, fail-closed claim promotion, explicit runtime
//! identity, and deterministic SHA-256 conformance receipts.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;

pub const RSH_EPISTEMIC_V1: &str = "RSH-EPISTEMIC-V1";
pub const RSH_CONFORMANCE_V1: &str = "RSH-CONFORMANCE-V1";
pub const CONFORMANCE_RECEIPT_DOMAIN: &[u8] = b"RSH-CONFORMANCE-V1\0";
pub const CONFORMANCE_LEDGER_DOMAIN: &[u8] = b"RSH-CONFORMANCE-LEDGER-V1\0";

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum EpistemicState {
    Known,
    Retrieved,
    Inferred,
    Unknown,
    Conflict,
    Fiction,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum EvidenceClass {
    ModelProposal,
    ToolReceipt,
    Measurement,
    FormalSyntax,
    ProofReceipt,
    Rejected,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ClaimTier {
    Proposal,
    Hypothesis,
    EvidenceBacked,
    Verified,
    Blocked,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClaimDecision {
    pub allowed: bool,
    pub tier: ClaimTier,
    pub epistemic_state: EpistemicState,
    pub evidence_class: EvidenceClass,
    pub reason: String,
}

fn tier_rank(tier: ClaimTier) -> i8 {
    match tier {
        ClaimTier::Blocked => -1,
        ClaimTier::Proposal => 0,
        ClaimTier::Hypothesis => 1,
        ClaimTier::EvidenceBacked => 2,
        ClaimTier::Verified => 3,
    }
}

fn cap_tier(tier: ClaimTier, cap: ClaimTier) -> ClaimTier {
    if tier == ClaimTier::Blocked || tier_rank(tier) <= tier_rank(cap) {
        tier
    } else {
        cap
    }
}

pub fn adjudicate_claim(
    epistemic_state: EpistemicState,
    evidence_class: EvidenceClass,
    receipt_present: bool,
    proof_checked: bool,
    measurement_identified: bool,
) -> ClaimDecision {
    let (mut tier, mut reason) = match evidence_class {
        EvidenceClass::Rejected => (ClaimTier::Blocked, "evidence-rejected".to_owned()),
        EvidenceClass::ProofReceipt if !receipt_present || !proof_checked => {
            (ClaimTier::Blocked, "proof-receipt-incomplete".to_owned())
        }
        EvidenceClass::ProofReceipt => (ClaimTier::Verified, "proof-receipt-verified".to_owned()),
        EvidenceClass::Measurement if !receipt_present || !measurement_identified => (
            ClaimTier::Blocked,
            "measurement-evidence-incomplete".to_owned(),
        ),
        EvidenceClass::Measurement => (
            ClaimTier::EvidenceBacked,
            "measurement-evidence-backed".to_owned(),
        ),
        EvidenceClass::ToolReceipt if !receipt_present => {
            (ClaimTier::Blocked, "tool-receipt-missing".to_owned())
        }
        EvidenceClass::ToolReceipt => (
            ClaimTier::EvidenceBacked,
            "tool-execution-evidence".to_owned(),
        ),
        EvidenceClass::FormalSyntax => (
            ClaimTier::Hypothesis,
            "formal-syntax-is-not-proof".to_owned(),
        ),
        EvidenceClass::ModelProposal => {
            (ClaimTier::Proposal, "model-output-is-proposal".to_owned())
        }
    };

    match epistemic_state {
        EpistemicState::Conflict => {
            tier = ClaimTier::Blocked;
            reason = "material-conflict-unresolved".to_owned();
        }
        EpistemicState::Fiction => {
            tier = cap_tier(tier, ClaimTier::Proposal);
            reason = "fiction-is-non-literal".to_owned();
        }
        EpistemicState::Unknown => {
            tier = cap_tier(tier, ClaimTier::Hypothesis);
            reason.push_str(";unknown-is-not-false");
        }
        EpistemicState::Inferred => {
            tier = cap_tier(tier, ClaimTier::EvidenceBacked);
            reason.push_str(";inference-not-known-without-support");
        }
        EpistemicState::Known | EpistemicState::Retrieved => {}
    }

    ClaimDecision {
        allowed: tier != ClaimTier::Blocked,
        tier,
        epistemic_state,
        evidence_class,
        reason,
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeIdentity {
    pub backend: String,
    pub implementation: String,
    pub implementation_version: String,
    pub source_revision: String,
    pub fallback_used: bool,
    pub fallback_from: Option<String>,
}

impl RuntimeIdentity {
    pub fn validate(&self) -> Result<(), String> {
        for (label, value) in [
            ("backend", self.backend.as_str()),
            ("implementation", self.implementation.as_str()),
            (
                "implementation_version",
                self.implementation_version.as_str(),
            ),
            ("source_revision", self.source_revision.as_str()),
        ] {
            validate_canonical_text(value, &format!("runtime.{label}"))?;
        }

        if self.fallback_used {
            let fallback_from = self
                .fallback_from
                .as_deref()
                .ok_or_else(|| "fallback_used=true requires runtime.fallback_from".to_owned())?;
            validate_canonical_text(fallback_from, "runtime.fallback_from")?;
            if fallback_from == self.backend {
                return Err("fallback_from must name a different requested backend".to_owned());
            }
        } else if self.fallback_from.is_some() {
            return Err("fallback_from must be null when fallback_used=false".to_owned());
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExperimentEnvelope {
    pub contract: String,
    pub experiment: String,
    pub input_sha256: String,
    pub runtime: RuntimeIdentity,
    pub parameters: BTreeMap<String, String>,
    pub seed: u64,
    pub observables: BTreeMap<String, String>,
}

fn is_sha256_hex(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

fn validate_canonical_text(value: &str, label: &str) -> Result<(), String> {
    if value.is_empty() {
        return Err(format!("{label} must be a non-empty string"));
    }
    if value
        .bytes()
        .any(|byte| !(0x20..=0x7e).contains(&byte) || byte == b'"' || byte == b'\\')
    {
        return Err(format!(
            "{label} must use printable ASCII excluding quote and backslash"
        ));
    }
    Ok(())
}

fn validate_string_map(value: &BTreeMap<String, String>, label: &str) -> Result<(), String> {
    for (key, item) in value {
        validate_canonical_text(key, &format!("{label} key"))?;
        validate_canonical_text(item, &format!("{label}.{key}"))?;
    }
    Ok(())
}

impl ExperimentEnvelope {
    pub fn validate(&self) -> Result<(), String> {
        if self.contract != RSH_CONFORMANCE_V1 {
            return Err(format!("contract must be {RSH_CONFORMANCE_V1}"));
        }
        validate_canonical_text(&self.experiment, "experiment")?;
        if !is_sha256_hex(&self.input_sha256) {
            return Err("input_sha256 must be canonical lower-case SHA-256 hex".to_owned());
        }
        self.runtime.validate()?;
        validate_string_map(&self.parameters, "parameters")?;
        validate_string_map(&self.observables, "observables")?;
        Ok(())
    }
}

pub fn canonical_experiment_json(envelope: &ExperimentEnvelope) -> Result<String, String> {
    envelope.validate()?;
    serde_json::to_string(envelope).map_err(|error| error.to_string())
}

pub fn experiment_receipt(envelope: &ExperimentEnvelope) -> Result<String, String> {
    let payload = canonical_experiment_json(envelope)?;
    let mut hasher = Sha256::new();
    hasher.update(CONFORMANCE_RECEIPT_DOMAIN);
    hasher.update(payload.as_bytes());
    Ok(format!("{:x}", hasher.finalize()))
}

pub fn require_backend(
    envelope: &ExperimentEnvelope,
    expected_backend: &str,
    allow_declared_fallback: bool,
) -> Result<(), String> {
    envelope.validate()?;
    if envelope.runtime.backend != expected_backend {
        return Err(format!(
            "backend mismatch: expected {expected_backend:?}, observed {:?}",
            envelope.runtime.backend
        ));
    }
    if envelope.runtime.fallback_used && !allow_declared_fallback {
        return Err(format!(
            "declared fallback from {:?} is not accepted",
            envelope.runtime.fallback_from
        ));
    }
    Ok(())
}

pub fn compare_observables(a: &ExperimentEnvelope, b: &ExperimentEnvelope) -> Result<bool, String> {
    a.validate()?;
    b.validate()?;
    Ok(a.contract == b.contract
        && a.experiment == b.experiment
        && a.input_sha256 == b.input_sha256
        && a.parameters == b.parameters
        && a.seed == b.seed
        && a.observables == b.observables)
}

#[derive(Serialize)]
struct LedgerPayload<'a> {
    contract: &'static str,
    receipts: &'a [String],
}

pub fn ledger_digest(receipts: &[String]) -> Result<String, String> {
    if receipts.is_empty() {
        return Err("ledger must contain at least one receipt".to_owned());
    }
    if receipts.iter().any(|receipt| !is_sha256_hex(receipt)) {
        return Err("ledger receipts must be canonical lower-case SHA-256 hex".to_owned());
    }
    let payload = serde_json::to_string(&LedgerPayload {
        contract: RSH_CONFORMANCE_V1,
        receipts,
    })
    .map_err(|error| error.to_string())?;
    let mut hasher = Sha256::new();
    hasher.update(CONFORMANCE_LEDGER_DOMAIN);
    hasher.update(payload.as_bytes());
    Ok(format!("{:x}", hasher.finalize()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde::Deserialize;
    use serde_json::Value;

    #[derive(Debug, Deserialize)]
    struct ClaimVector {
        name: String,
        epistemic_state: EpistemicState,
        evidence_class: EvidenceClass,
        receipt_present: bool,
        proof_checked: bool,
        measurement_identified: bool,
        expected_tier: ClaimTier,
    }

    #[test]
    fn sealed_cross_runtime_vector_matches() {
        let vector: Value = serde_json::from_str(include_str!(
            "../../../conformance/rsh_v4_governance_vector_v1.json"
        ))
        .expect("vector must parse");
        let envelope: ExperimentEnvelope =
            serde_json::from_value(vector["envelope"].clone()).expect("envelope must parse");
        let expected = vector["expected_receipt"]
            .as_str()
            .expect("receipt must be string");
        assert_eq!(experiment_receipt(&envelope).unwrap(), expected);

        let ledger: Vec<String> =
            serde_json::from_value(vector["ledger_receipts"].clone()).unwrap();
        let expected_ledger = vector["expected_ledger_digest"].as_str().unwrap();
        assert_eq!(ledger_digest(&ledger).unwrap(), expected_ledger);

        let claim_vectors: Vec<ClaimVector> =
            serde_json::from_value(vector["claim_vectors"].clone())
                .expect("claim vectors must parse");
        assert!(!claim_vectors.is_empty(), "sealed claim vectors must not be empty");
        for claim in claim_vectors {
            let decision = adjudicate_claim(
                claim.epistemic_state,
                claim.evidence_class,
                claim.receipt_present,
                claim.proof_checked,
                claim.measurement_identified,
            );
            assert_eq!(
                decision.tier, claim.expected_tier,
                "sealed claim vector {:?} diverged",
                claim.name
            );
        }
    }

    #[test]
    fn formal_syntax_never_becomes_proof() {
        let decision = adjudicate_claim(
            EpistemicState::Known,
            EvidenceClass::FormalSyntax,
            true,
            true,
            false,
        );
        assert_eq!(decision.tier, ClaimTier::Hypothesis);
    }

    #[test]
    fn incomplete_proof_receipt_fails_closed() {
        let decision = adjudicate_claim(
            EpistemicState::Known,
            EvidenceClass::ProofReceipt,
            true,
            false,
            false,
        );
        assert_eq!(decision.tier, ClaimTier::Blocked);
        assert!(!decision.allowed);
    }

    #[test]
    fn silent_fallback_is_rejected() {
        let mut parameters = BTreeMap::new();
        parameters.insert("samples".to_owned(), "129".to_owned());
        let mut observables = BTreeMap::new();
        observables.insert("result".to_owned(), "pass".to_owned());
        let envelope = ExperimentEnvelope {
            contract: RSH_CONFORMANCE_V1.to_owned(),
            experiment: "fallback-test".to_owned(),
            input_sha256: "0".repeat(64),
            runtime: RuntimeIdentity {
                backend: "python-reference".to_owned(),
                implementation: "rsh-geometry".to_owned(),
                implementation_version: "4.0.0".to_owned(),
                source_revision: "fixture".to_owned(),
                fallback_used: true,
                fallback_from: Some("cuda".to_owned()),
            },
            parameters,
            seed: 0,
            observables,
        };
        assert!(require_backend(&envelope, "python-reference", false).is_err());
        assert!(require_backend(&envelope, "python-reference", true).is_ok());
    }
}
