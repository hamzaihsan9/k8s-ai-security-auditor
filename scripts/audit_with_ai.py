#!/usr/bin/env python3
"""
Automated AI-Driven Kubernetes Vulnerability & Compliance Auditing Pipeline
Demonstrates end-to-end local DevSecOps workflow:
1. Ingests deterministic scanner outputs (Trivy & Kubescape)
2. Uses local AI (Ollama / llama3.2:1b) for root-cause threat modeling
3. Evaluates security score improvements post-hardening
"""

import json
import urllib.request
import os

EVIDENCE_DIR = "/home/kali/k8s-ai-security-poc/evidence"

def get_trivy_summary():
    with open(f"{EVIDENCE_DIR}/trivy_scan_report.json") as f:
        data = json.load(f)
    results = data.get("Results", [])
    misconfigs = []
    for r in results:
        for m in r.get("Misconfigurations", []):
            misconfigs.append({
                "id": m.get("ID"),
                "title": m.get("Title"),
                "severity": m.get("Severity"),
                "resolution": m.get("Resolution")
            })
    return misconfigs

def get_kubescape_summary():
    with open(f"{EVIDENCE_DIR}/kubescape_scan_report.json") as f:
        data = json.load(f)
    summary = data.get("summaryDetails", {})
    score = summary.get("complianceScore", 0)
    failed_controls = []
    for r in data.get("results", []):
        for c in r.get("controls", []):
            if c.get("status") == "failed":
                failed_controls.append(c.get("name"))
    return score, list(set(failed_controls))

def generate_ai_analysis(misconfigs):
    high_crit = [m for m in misconfigs if m["severity"] in ["HIGH", "CRITICAL"]]
    prompt = f"""You are a Principal DevSecOps Engineer.
Analyze the following Kubernetes security vulnerabilities detected in a production deployment manifest:
{json.dumps(high_crit[:4], indent=2)}

Provide:
1. Threat Vector & Exploit Chain (Explain the blast radius of privileged mode, hostPath, and hostPID).
2. Attack Scenario: How an adversary can break out of this container to the host node.
3. 3-step hardening mandate to remediate these issues before deploying to production.
Keep your response concise, technical, and authoritative.
"""
    data = json.dumps({
        "model": "llama3.2:1b",
        "prompt": prompt,
        "stream": False
    }).encode("utf-8")
    
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read().decode("utf-8"))["response"]

def main():
    print("[*] Ingesting Trivy misconfigurations...")
    misconfigs = get_trivy_summary()
    print(f"    Found {len(misconfigs)} misconfigurations.")

    print("[*] Ingesting Kubescape compliance report...")
    k_score, k_failed = get_kubescape_summary()
    print(f"    Pre-Hardening Kubescape Compliance Score: {k_score:.1f}%")
    print(f"    Failed Controls count: {len(k_failed)}")

    print("[*] Invoking Local AI (llama3.2:1b via Ollama) for Threat Analysis...")
    ai_report = generate_ai_analysis(misconfigs)
    
    with open(f"{EVIDENCE_DIR}/ai_threat_analysis.txt", "w") as f:
        f.write(ai_report)
    print("[+] AI Analysis successfully generated and saved.")

if __name__ == "__main__":
    main()
