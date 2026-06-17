"""
All check definitions for EU AI Act Article 14 (Human Oversight) compliance checker.
"""

CHECKS = [
    # ── Section A ─────────────────────────────────────────────────────────────
    # A1 — Human-Machine Interface (Art. 14(1))
    {
        "id": "A1.1",
        "section": "A",
        "subsection": "A1",
        "title": "Human-Machine Interface",
        "requirement": (
            "The system includes human-machine interface (HMI) tools that allow "
            "a natural person to observe system behaviour in real time."
        ),
        "article": "Art. 14(1)",
        "evidence": (
            "HMI design specification, screenshot/demo of oversight interface, "
            "section in instructions of use referencing oversight tooling."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    {
        "id": "A1.2",
        "section": "A",
        "subsection": "A1",
        "title": "Human-Machine Interface",
        "requirement": (
            "The HMI presents outputs in a form that is interpretable without "
            "specialist ML knowledge."
        ),
        "article": "Art. 14(1)",
        "evidence": (
            "HMI design specification, screenshot/demo of oversight interface, "
            "section in instructions of use referencing oversight tooling."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    {
        "id": "A1.3",
        "section": "A",
        "subsection": "A1",
        "title": "Human-Machine Interface",
        "requirement": (
            "The HMI is documented in the instructions of use (Art. 13) delivered "
            "to deployers."
        ),
        "article": "Art. 14(1)",
        "evidence": (
            "HMI design specification, screenshot/demo of oversight interface, "
            "section in instructions of use referencing oversight tooling."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    # A2 — Pre-Market Oversight Measures Identification (Art. 14(3))
    {
        "id": "A2.1",
        "section": "A",
        "subsection": "A2",
        "title": "Pre-Market Oversight Measures Identification",
        "requirement": (
            "Oversight measures were formally identified and documented before "
            "the system was placed on the market or put into service."
        ),
        "article": "Art. 14(3)",
        "evidence": (
            "Oversight measures register, pre-market risk assessment, "
            "instructions of use (deployer section)."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    {
        "id": "A2.2",
        "section": "A",
        "subsection": "A2",
        "title": "Pre-Market Oversight Measures Identification",
        "requirement": (
            "For each identified measure: it has been assessed whether it can be "
            "embedded technically (Art. 14(3)(a)) or must be implemented by the "
            "deployer (Art. 14(3)(b))."
        ),
        "article": "Art. 14(3)",
        "evidence": (
            "Oversight measures register, pre-market risk assessment, "
            "instructions of use (deployer section)."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    {
        "id": "A2.3",
        "section": "A",
        "subsection": "A2",
        "title": "Pre-Market Oversight Measures Identification",
        "requirement": (
            "All deployer-assigned measures are described explicitly in the "
            "instructions of use."
        ),
        "article": "Art. 14(3)",
        "evidence": (
            "Oversight measures register, pre-market risk assessment, "
            "instructions of use (deployer section)."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    {
        "id": "A2.4",
        "section": "A",
        "subsection": "A2",
        "title": "Pre-Market Oversight Measures Identification",
        "requirement": (
            "The proportionality of measures to the system's risk level, autonomy "
            "level, and deployment context is documented."
        ),
        "article": "Art. 14(3)",
        "evidence": (
            "Oversight measures register, pre-market risk assessment, "
            "instructions of use (deployer section)."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    # A3a — Understand Capabilities and Limitations (Art. 14(4)(a))
    {
        "id": "A3a.1",
        "section": "A",
        "subsection": "A3a",
        "title": "Understand Capabilities and Limitations",
        "requirement": (
            "The system surfaces its own confidence scores, uncertainty estimates, "
            "or reliability indicators to oversight personnel."
        ),
        "article": "Art. 14(4)(a)",
        "evidence": (
            "Confidence/uncertainty display in UI, system logs, anomaly alert "
            "configuration, limitations documentation."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    {
        "id": "A3a.2",
        "section": "A",
        "subsection": "A3a",
        "title": "Understand Capabilities and Limitations",
        "requirement": (
            "Known limitations (accuracy bounds, out-of-distribution behaviour, "
            "failure modes) are documented and accessible to oversight personnel "
            "during operation."
        ),
        "article": "Art. 14(4)(a)",
        "evidence": (
            "Confidence/uncertainty display in UI, system logs, anomaly alert "
            "configuration, limitations documentation."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    {
        "id": "A3a.3",
        "section": "A",
        "subsection": "A3a",
        "title": "Understand Capabilities and Limitations",
        "requirement": (
            "The system generates alerts or flags when it detects anomalous inputs, "
            "unexpected outputs, or performance degradation."
        ),
        "article": "Art. 14(4)(a)",
        "evidence": (
            "Confidence/uncertainty display in UI, system logs, anomaly alert "
            "configuration, limitations documentation."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    {
        "id": "A3a.4",
        "section": "A",
        "subsection": "A3a",
        "title": "Understand Capabilities and Limitations",
        "requirement": (
            "Logs of system decisions and outputs are retained in a form that "
            "oversight personnel can audit (see also Art. 12)."
        ),
        "article": "Art. 14(4)(a)",
        "evidence": (
            "Confidence/uncertainty display in UI, system logs, anomaly alert "
            "configuration, limitations documentation."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    # A3b — Counter Automation Bias (Art. 14(4)(b))
    {
        "id": "A3b.1",
        "section": "A",
        "subsection": "A3b",
        "title": "Counter Automation Bias",
        "requirement": (
            "The system does not present AI output as a final decision — outputs "
            "are labelled as recommendations, suggestions, or AI-generated assessments."
        ),
        "article": "Art. 14(4)(b)",
        "evidence": (
            "UI screenshots showing output labelling, confirmation-step design, "
            "instructions of use section on automation bias."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    {
        "id": "A3b.2",
        "section": "A",
        "subsection": "A3b",
        "title": "Counter Automation Bias",
        "requirement": (
            "The interface does not pre-populate or auto-commit actions based on "
            "AI output without explicit human confirmation."
        ),
        "article": "Art. 14(4)(b)",
        "evidence": (
            "UI screenshots showing output labelling, confirmation-step design, "
            "instructions of use section on automation bias."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    {
        "id": "A3b.3",
        "section": "A",
        "subsection": "A3b",
        "title": "Counter Automation Bias",
        "requirement": (
            "Instructions of use explicitly warn oversight personnel of automation "
            "bias risk and its implications."
        ),
        "article": "Art. 14(4)(b)",
        "evidence": (
            "UI screenshots showing output labelling, confirmation-step design, "
            "instructions of use section on automation bias."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    {
        "id": "A3b.4",
        "section": "A",
        "subsection": "A3b",
        "title": "Counter Automation Bias",
        "requirement": (
            "Training materials for oversight personnel include automation bias awareness."
        ),
        "article": "Art. 14(4)(b)",
        "evidence": (
            "UI screenshots showing output labelling, confirmation-step design, "
            "instructions of use section on automation bias."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    # A3c — Interpret Outputs (Art. 14(4)(c))
    {
        "id": "A3c.1",
        "section": "A",
        "subsection": "A3c",
        "title": "Interpret Outputs",
        "requirement": (
            "The system provides explanation or rationale for its outputs (e.g., "
            "feature attribution, decision factors, natural language justification)."
        ),
        "article": "Art. 14(4)(c)",
        "evidence": (
            "Explainability feature documentation, UI walkthrough, "
            "output format specification."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    {
        "id": "A3c.2",
        "section": "A",
        "subsection": "A3c",
        "title": "Interpret Outputs",
        "requirement": (
            "Interpretation tools are accessible within the operational interface — "
            "not only in separate technical documentation."
        ),
        "article": "Art. 14(4)(c)",
        "evidence": (
            "Explainability feature documentation, UI walkthrough, "
            "output format specification."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    {
        "id": "A3c.3",
        "section": "A",
        "subsection": "A3c",
        "title": "Interpret Outputs",
        "requirement": (
            "Output formats use language and scales appropriate to the oversight "
            "personnel's domain (not raw model scores only)."
        ),
        "article": "Art. 14(4)(c)",
        "evidence": (
            "Explainability feature documentation, UI walkthrough, "
            "output format specification."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    # A3d — Override / Disregard Output (Art. 14(4)(d))
    {
        "id": "A3d.1",
        "section": "A",
        "subsection": "A3d",
        "title": "Override / Disregard Output",
        "requirement": (
            "Oversight personnel can reject, disregard, or reverse any AI output "
            "before it takes effect — without requiring technical access or "
            "administrator privileges."
        ),
        "article": "Art. 14(4)(d)",
        "evidence": (
            "Override workflow documentation, override log schema, UI demonstration."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    {
        "id": "A3d.2",
        "section": "A",
        "subsection": "A3d",
        "title": "Override / Disregard Output",
        "requirement": (
            "The override mechanism is prominent and accessible within the standard "
            "operational workflow."
        ),
        "article": "Art. 14(4)(d)",
        "evidence": (
            "Override workflow documentation, override log schema, UI demonstration."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    {
        "id": "A3d.3",
        "section": "A",
        "subsection": "A3d",
        "title": "Override / Disregard Output",
        "requirement": (
            "Overrides are logged (who overrode, when, and if captured, the reason)."
        ),
        "article": "Art. 14(4)(d)",
        "evidence": (
            "Override workflow documentation, override log schema, UI demonstration."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    {
        "id": "A3d.4",
        "section": "A",
        "subsection": "A3d",
        "title": "Override / Disregard Output",
        "requirement": (
            "Overriding the AI output does not automatically trigger a re-run or "
            "escalation that bypasses the override."
        ),
        "article": "Art. 14(4)(d)",
        "evidence": (
            "Override workflow documentation, override log schema, UI demonstration."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    # A3e — Stop / Interrupt the System (Art. 14(4)(e))
    {
        "id": "A3e.1",
        "section": "A",
        "subsection": "A3e",
        "title": "Stop / Interrupt the System",
        "requirement": (
            "A clearly labelled stop or interrupt mechanism exists within the "
            "operational interface."
        ),
        "article": "Art. 14(4)(e)",
        "evidence": (
            "Stop-button UI specification, test records, "
            "instructions of use section on interruption."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    {
        "id": "A3e.2",
        "section": "A",
        "subsection": "A3e",
        "title": "Stop / Interrupt the System",
        "requirement": (
            "The stop function halts the system's active processing — it does not "
            "only pause new inputs while ongoing decisions complete."
        ),
        "article": "Art. 14(4)(e)",
        "evidence": (
            "Stop-button UI specification, test records, "
            "instructions of use section on interruption."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    {
        "id": "A3e.3",
        "section": "A",
        "subsection": "A3e",
        "title": "Stop / Interrupt the System",
        "requirement": (
            "Activating the stop function does not require escalation to a third "
            "party or vendor support."
        ),
        "article": "Art. 14(4)(e)",
        "evidence": (
            "Stop-button UI specification, test records, "
            "instructions of use section on interruption."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    {
        "id": "A3e.4",
        "section": "A",
        "subsection": "A3e",
        "title": "Stop / Interrupt the System",
        "requirement": (
            "The stop procedure and its effects are documented in the instructions "
            "of use."
        ),
        "article": "Art. 14(4)(e)",
        "evidence": (
            "Stop-button UI specification, test records, "
            "instructions of use section on interruption."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },
    {
        "id": "A3e.5",
        "section": "A",
        "subsection": "A3e",
        "title": "Stop / Interrupt the System",
        "requirement": (
            "The stop function has been tested and its behaviour verified under "
            "realistic load conditions."
        ),
        "article": "Art. 14(4)(e)",
        "evidence": (
            "Stop-button UI specification, test records, "
            "instructions of use section on interruption."
        ),
        "roles": ["provider"],
        "biometric_only": False,
    },

    # ── Section B ─────────────────────────────────────────────────────────────
    # B1 — Implementation of Provider-Assigned Measures (Art. 14(3)(b))
    {
        "id": "B1.1",
        "section": "B",
        "subsection": "B1",
        "title": "Implementation of Provider-Assigned Measures",
        "requirement": (
            "You have received and reviewed the provider's instructions of use, "
            "specifically the oversight measures section."
        ),
        "article": "Art. 14(3)(b)",
        "evidence": (
            "Signed receipt of instructions of use, implementation register, "
            "any gap notifications to provider."
        ),
        "roles": ["deployer"],
        "biometric_only": False,
    },
    {
        "id": "B1.2",
        "section": "B",
        "subsection": "B1",
        "title": "Implementation of Provider-Assigned Measures",
        "requirement": (
            "All deployer-assigned oversight measures listed by the provider have "
            "been operationally implemented."
        ),
        "article": "Art. 14(3)(b)",
        "evidence": (
            "Signed receipt of instructions of use, implementation register, "
            "any gap notifications to provider."
        ),
        "roles": ["deployer"],
        "biometric_only": False,
    },
    {
        "id": "B1.3",
        "section": "B",
        "subsection": "B1",
        "title": "Implementation of Provider-Assigned Measures",
        "requirement": (
            "You have documented which measures are implemented, how, and by whom."
        ),
        "article": "Art. 14(3)(b)",
        "evidence": (
            "Signed receipt of instructions of use, implementation register, "
            "any gap notifications to provider."
        ),
        "roles": ["deployer"],
        "biometric_only": False,
    },
    {
        "id": "B1.4",
        "section": "B",
        "subsection": "B1",
        "title": "Implementation of Provider-Assigned Measures",
        "requirement": (
            "You have identified any provider-assigned measure you cannot implement, "
            "and have notified the provider and/or your national market surveillance "
            "authority as appropriate."
        ),
        "article": "Art. 14(3)(b)",
        "evidence": (
            "Signed receipt of instructions of use, implementation register, "
            "any gap notifications to provider."
        ),
        "roles": ["deployer"],
        "biometric_only": False,
    },
    # B2 — Assignment of Qualified Oversight Personnel (Art. 26(2))
    {
        "id": "B2.1",
        "section": "B",
        "subsection": "B2",
        "title": "Assignment of Qualified Oversight Personnel",
        "requirement": (
            "Natural persons have been formally assigned to human oversight of "
            "this system."
        ),
        "article": "Art. 26(2)",
        "evidence": (
            "Oversight personnel assignment records, training completion certificates, "
            "competence assessments, authority delegation documents."
        ),
        "roles": ["deployer"],
        "biometric_only": False,
    },
    {
        "id": "B2.2",
        "section": "B",
        "subsection": "B2",
        "title": "Assignment of Qualified Oversight Personnel",
        "requirement": (
            "Assigned personnel have documented competence relevant to the system's "
            "domain and outputs."
        ),
        "article": "Art. 26(2)",
        "evidence": (
            "Oversight personnel assignment records, training completion certificates, "
            "competence assessments, authority delegation documents."
        ),
        "roles": ["deployer"],
        "biometric_only": False,
    },
    {
        "id": "B2.3",
        "section": "B",
        "subsection": "B2",
        "title": "Assignment of Qualified Oversight Personnel",
        "requirement": (
            "Assigned personnel have received training on the system's capabilities, "
            "limitations, and the five Art. 14(4) competencies."
        ),
        "article": "Art. 26(2)",
        "evidence": (
            "Oversight personnel assignment records, training completion certificates, "
            "competence assessments, authority delegation documents."
        ),
        "roles": ["deployer"],
        "biometric_only": False,
    },
    {
        "id": "B2.4",
        "section": "B",
        "subsection": "B2",
        "title": "Assignment of Qualified Oversight Personnel",
        "requirement": (
            "Assigned personnel have the organisational authority to exercise override "
            "(Art. 14(4)(d)) and stop (Art. 14(4)(e)) without requiring approval "
            "from a superior."
        ),
        "article": "Art. 26(2)",
        "evidence": (
            "Oversight personnel assignment records, training completion certificates, "
            "competence assessments, authority delegation documents."
        ),
        "roles": ["deployer"],
        "biometric_only": False,
    },
    {
        "id": "B2.5",
        "section": "B",
        "subsection": "B2",
        "title": "Assignment of Qualified Oversight Personnel",
        "requirement": (
            "A named backup or coverage procedure exists for when primary oversight "
            "personnel are unavailable."
        ),
        "article": "Art. 26(2)",
        "evidence": (
            "Oversight personnel assignment records, training completion certificates, "
            "competence assessments, authority delegation documents."
        ),
        "roles": ["deployer"],
        "biometric_only": False,
    },
    {
        "id": "B2.6",
        "section": "B",
        "subsection": "B2",
        "title": "Assignment of Qualified Oversight Personnel",
        "requirement": (
            "Training records and competence assessments are retained and refreshed "
            "on a defined schedule."
        ),
        "article": "Art. 26(2)",
        "evidence": (
            "Oversight personnel assignment records, training completion certificates, "
            "competence assessments, authority delegation documents."
        ),
        "roles": ["deployer"],
        "biometric_only": False,
    },
    # B3 — Operational Monitoring and Review
    {
        "id": "B3.1",
        "section": "B",
        "subsection": "B3",
        "title": "Operational Monitoring and Review",
        "requirement": (
            "A process exists for oversight personnel to report anomalies, unexpected "
            "outputs, or performance concerns."
        ),
        "article": "Art. 26(2)",
        "evidence": (
            "Anomaly reporting procedure, review meeting records, performance "
            "monitoring logs, change management records."
        ),
        "roles": ["deployer"],
        "biometric_only": False,
    },
    {
        "id": "B3.2",
        "section": "B",
        "subsection": "B3",
        "title": "Operational Monitoring and Review",
        "requirement": (
            "Anomaly reports are reviewed on a defined cadence by a responsible "
            "person with authority to escalate or halt the system."
        ),
        "article": "Art. 26(2)",
        "evidence": (
            "Anomaly reporting procedure, review meeting records, performance "
            "monitoring logs, change management records."
        ),
        "roles": ["deployer"],
        "biometric_only": False,
    },
    {
        "id": "B3.3",
        "section": "B",
        "subsection": "B3",
        "title": "Operational Monitoring and Review",
        "requirement": (
            "The system's performance against its stated accuracy and reliability "
            "specifications is reviewed at defined intervals."
        ),
        "article": "Art. 26(2)",
        "evidence": (
            "Anomaly reporting procedure, review meeting records, performance "
            "monitoring logs, change management records."
        ),
        "roles": ["deployer"],
        "biometric_only": False,
    },
    {
        "id": "B3.4",
        "section": "B",
        "subsection": "B3",
        "title": "Operational Monitoring and Review",
        "requirement": (
            "If the system is updated or retrained, oversight measures are "
            "re-evaluated before the updated system is re-deployed."
        ),
        "article": "Art. 26(2)",
        "evidence": (
            "Anomaly reporting procedure, review meeting records, performance "
            "monitoring logs, change management records."
        ),
        "roles": ["deployer"],
        "biometric_only": False,
    },

    # ── Section C ─────────────────────────────────────────────────────────────
    # C — Biometric Identification (Art. 14(5))
    {
        "id": "C1",
        "section": "C",
        "subsection": "C",
        "title": "Biometric Identification — Dual Verification",
        "requirement": (
            "No action or decision based on a remote biometric identification result "
            "is taken until that result has been separately verified by a second "
            "natural person."
        ),
        "article": "Art. 14(5)",
        "evidence": (
            "Dual-verification workflow, verification logs, competence records for "
            "both roles, legal basis documentation if exception claimed."
        ),
        "roles": ["provider", "deployer"],
        "biometric_only": True,
    },
    {
        "id": "C2",
        "section": "C",
        "subsection": "C",
        "title": "Biometric Identification — Verifier Competence",
        "requirement": (
            "Both verifying persons have documented competence, training, and "
            "authority relevant to the biometric identification context."
        ),
        "article": "Art. 14(5)",
        "evidence": (
            "Dual-verification workflow, verification logs, competence records for "
            "both roles, legal basis documentation if exception claimed."
        ),
        "roles": ["provider", "deployer"],
        "biometric_only": True,
    },
    {
        "id": "C3",
        "section": "C",
        "subsection": "C",
        "title": "Biometric Identification — Process Enforcement",
        "requirement": (
            "The two-person verification step is enforced by process or system "
            "design — it cannot be bypassed by a single operator."
        ),
        "article": "Art. 14(5)",
        "evidence": (
            "Dual-verification workflow, verification logs, competence records for "
            "both roles, legal basis documentation if exception claimed."
        ),
        "roles": ["provider", "deployer"],
        "biometric_only": True,
    },
    {
        "id": "C4",
        "section": "C",
        "subsection": "C",
        "title": "Biometric Identification — Verification Records",
        "requirement": (
            "Records of dual-person verifications are retained, including the "
            "identity of both verifying persons and the outcome."
        ),
        "article": "Art. 14(5)",
        "evidence": (
            "Dual-verification workflow, verification logs, competence records for "
            "both roles, legal basis documentation if exception claimed."
        ),
        "roles": ["provider", "deployer"],
        "biometric_only": True,
    },
    {
        "id": "C5",
        "section": "C",
        "subsection": "C",
        "title": "Biometric Identification — Exception Documentation",
        "requirement": (
            "If you are relying on the law-enforcement disproportionality exception: "
            "the legal basis (Union or national law provision) is documented and "
            "reviewed by legal counsel."
        ),
        "article": "Art. 14(5)",
        "evidence": (
            "Dual-verification workflow, verification logs, competence records for "
            "both roles, legal basis documentation if exception claimed."
        ),
        "roles": ["provider", "deployer"],
        "biometric_only": True,
    },

    # ── Section D ─────────────────────────────────────────────────────────────
    # D — Documentation and Conformity
    {
        "id": "D1",
        "section": "D",
        "subsection": "D",
        "title": "Documentation and Conformity",
        "requirement": (
            "Technical documentation (Art. 11 / Annex IV) includes a dedicated "
            "section on human oversight measures and how Art. 14(1), (3), and (4) "
            "requirements are met."
        ),
        "article": "Art. 11 / Annex IV",
        "evidence": (
            "Technical documentation, EU AI database registration confirmation, "
            "notified body assessment certificate (if applicable), "
            "self-assessment records."
        ),
        "roles": ["provider", "deployer"],
        "biometric_only": False,
    },
    {
        "id": "D2",
        "section": "D",
        "subsection": "D",
        "title": "Documentation and Conformity",
        "requirement": (
            "The system is registered in the EU AI Act database (Art. 49) if "
            "required for your Annex III category."
        ),
        "article": "Art. 49",
        "evidence": (
            "Technical documentation, EU AI database registration confirmation, "
            "notified body assessment certificate (if applicable), "
            "self-assessment records."
        ),
        "roles": ["provider", "deployer"],
        "biometric_only": False,
    },
    {
        "id": "D3",
        "section": "D",
        "subsection": "D",
        "title": "Documentation and Conformity",
        "requirement": (
            "If a third-party notified body assessment is required (biometrics and "
            "certain Annex III categories): it has been commissioned or completed."
        ),
        "article": "Art. 43",
        "evidence": (
            "Technical documentation, EU AI database registration confirmation, "
            "notified body assessment certificate (if applicable), "
            "self-assessment records."
        ),
        "roles": ["provider", "deployer"],
        "biometric_only": False,
    },
    {
        "id": "D4",
        "section": "D",
        "subsection": "D",
        "title": "Documentation and Conformity",
        "requirement": (
            "Internal self-assessment records against Arts. 9-15 are retained and "
            "available for market surveillance authority inspection."
        ),
        "article": "Arts. 9-15",
        "evidence": (
            "Technical documentation, EU AI database registration confirmation, "
            "notified body assessment certificate (if applicable), "
            "self-assessment records."
        ),
        "roles": ["provider", "deployer"],
        "biometric_only": False,
    },
    {
        "id": "D5",
        "section": "D",
        "subsection": "D",
        "title": "Documentation and Conformity",
        "requirement": (
            "A process exists to update documentation when the system or its "
            "deployment context changes materially."
        ),
        "article": "Art. 11",
        "evidence": (
            "Technical documentation, EU AI database registration confirmation, "
            "notified body assessment certificate (if applicable), "
            "self-assessment records."
        ),
        "roles": ["provider", "deployer"],
        "biometric_only": False,
    },

    # ── Section E ─────────────────────────────────────────────────────────────
    # E — Cross-Cutting Obligations
    {
        "id": "E1",
        "section": "E",
        "subsection": "E",
        "title": "Cross-Cutting Obligations",
        "requirement": (
            "A risk management system is in place and documents residual risks that "
            "human oversight is relied upon to address."
        ),
        "article": "Art. 9",
        "evidence": "Risk management system documentation.",
        "roles": ["provider", "deployer"],
        "biometric_only": False,
    },
    {
        "id": "E2",
        "section": "E",
        "subsection": "E",
        "title": "Cross-Cutting Obligations",
        "requirement": (
            "The system generates automatic logs of its operation sufficient for "
            "post-hoc review of decisions."
        ),
        "article": "Art. 12",
        "evidence": "Log configuration, sample log output.",
        "roles": ["provider", "deployer"],
        "biometric_only": False,
    },
    {
        "id": "E3",
        "section": "E",
        "subsection": "E",
        "title": "Cross-Cutting Obligations",
        "requirement": (
            "Logs are retained for the period required by applicable law and are "
            "protected against tampering."
        ),
        "article": "Art. 12",
        "evidence": "Retention policy, tamper-evidence mechanism.",
        "roles": ["provider", "deployer"],
        "biometric_only": False,
    },
    {
        "id": "E4",
        "section": "E",
        "subsection": "E",
        "title": "Cross-Cutting Obligations",
        "requirement": (
            "Instructions of use have been provided to deployers and cover: system "
            "purpose, performance characteristics, oversight measures, and risks."
        ),
        "article": "Art. 13",
        "evidence": "Instructions of use document.",
        "roles": ["provider", "deployer"],
        "biometric_only": False,
    },
    {
        "id": "E5",
        "section": "E",
        "subsection": "E",
        "title": "Cross-Cutting Obligations",
        "requirement": (
            "Instructions of use identify categories of persons or contexts for "
            "which the system is not suitable."
        ),
        "article": "Art. 13",
        "evidence": "Instructions of use — contraindications section.",
        "roles": ["provider", "deployer"],
        "biometric_only": False,
    },
]

ANNEX_III_SECTORS = [
    "1. Biometrics",
    "2. Critical infrastructure",
    "3. Education and vocational training",
    "4. Employment, workers management, and access to self-employment",
    "5. Access to and enjoyment of essential private services and public services and benefits",
    "6. Law enforcement",
    "7. Migration, asylum, and border control management",
    "8. Administration of justice and democratic processes",
]

SECTION_TITLES = {
    "A": "Section A — Provider Obligations (Art. 14(1), 14(3), 14(4))",
    "B": "Section B — Deployer Obligations (Art. 14(3)(b), Art. 26(2))",
    "C": "Section C — Biometric Identification (Art. 14(5))",
    "D": "Section D — Documentation and Conformity",
    "E": "Section E — Cross-Cutting Obligations",
}

SUBSECTION_TITLES = {
    "A1":  "A1 — Human-Machine Interface (Art. 14(1))",
    "A2":  "A2 — Pre-Market Oversight Measures Identification (Art. 14(3))",
    "A3a": "A3a — Understand Capabilities and Limitations (Art. 14(4)(a))",
    "A3b": "A3b — Counter Automation Bias (Art. 14(4)(b))",
    "A3c": "A3c — Interpret Outputs (Art. 14(4)(c))",
    "A3d": "A3d — Override / Disregard Output (Art. 14(4)(d))",
    "A3e": "A3e — Stop / Interrupt the System (Art. 14(4)(e))",
    "B1":  "B1 — Implementation of Provider-Assigned Measures (Art. 14(3)(b))",
    "B2":  "B2 — Assignment of Qualified Oversight Personnel (Art. 26(2))",
    "B3":  "B3 — Operational Monitoring and Review",
    "C":   "C — Biometric Identification (Art. 14(5))",
    "D":   "D — Documentation and Conformity",
    "E":   "E — Cross-Cutting Obligations",
}
