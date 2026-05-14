"""Ingest tool outputs into memory automatically."""
import re
from typing import List, Optional

from vcm_os.schemas import (
    ErrorEntry,
    EventRecord,
    MemoryObject,
    MemoryType,
    SourcePointer,
    SourceType,
    Validity,
)


class ToolResultIngestor:
    """Convert tool outputs (pytest, git diff, ripgrep, etc.) into memory objects."""

    def ingest(self, event: EventRecord) -> List[MemoryObject]:
        text = event.payload.get("content", "") if event.payload else ""
        tool_name = event.payload.get("tool_name", "") if event.payload else ""
        if not text:
            return []

        objs = []

        # pytest / test runner
        if tool_name in ("pytest", "npm_test", "jest", "cargo_test", "go_test"):
            objs.extend(self._parse_test_output(event, text, tool_name))

        # git diff
        elif tool_name in ("git_diff", "git"):
            objs.extend(self._parse_git_diff(event, text))

        # ripgrep / grep
        elif tool_name in ("ripgrep", "grep", "rg"):
            objs.extend(self._parse_search_output(event, text))

        # mypy / tsc / eslint / linter
        elif tool_name in ("mypy", "tsc", "eslint", "rustfmt", "clippy", "flake8", "pylint", "black", "prettier"):
            objs.extend(self._parse_linter_output(event, text, tool_name))

        # docker / build logs
        elif tool_name in ("docker", "docker_build", "docker_compose"):
            objs.extend(self._parse_docker_output(event, text, tool_name))

        # terraform / infrastructure
        elif tool_name in ("terraform", "tf_plan", "tf_apply"):
            objs.extend(self._parse_terraform_output(event, text, tool_name))

        # kubectl / kubernetes
        elif tool_name in ("kubectl", "k8s", "helm"):
            objs.extend(self._parse_kubectl_output(event, text, tool_name))

        # package managers
        elif tool_name in ("pip", "npm", "yarn", "pnpm", "cargo", "go_mod"):
            objs.extend(self._parse_package_output(event, text, tool_name))

        # API / curl responses
        elif tool_name in ("curl", "http", "api_call"):
            objs.extend(self._parse_api_output(event, text, tool_name))

        # security scanners
        elif tool_name in ("bandit", "snyk", "trivy", "semgrep"):
            objs.extend(self._parse_security_output(event, text, tool_name))

        # coverage tools
        elif tool_name in ("coverage", "codecov", "cargo_tarpaulin"):
            objs.extend(self._parse_coverage_output(event, text, tool_name))

        # generic tool call — store as fact
        else:
            objs.append(self._make_fact(event, text, tool_name))

        return objs

    def _parse_test_output(self, event: EventRecord, text: str, tool_name: str) -> List[MemoryObject]:
        objs = []

        # Detect pass/fail status
        passed = re.search(r"(\d+)\s+passed", text, re.IGNORECASE)
        failed = re.search(r"(\d+)\s+failed", text, re.IGNORECASE)

        status = "unknown"
        if failed and int(failed.group(1)) > 0:
            status = "failing"
        elif passed and int(passed.group(1)) > 0:
            status = "passing"

        # Store test result as fact
        summary = f"{tool_name}: {status}"
        if passed:
            summary += f", {passed.group(1)} passed"
        if failed:
            summary += f", {failed.group(1)} failed"

        objs.append(MemoryObject(
            project_id=event.project_id,
            session_id=event.session_id,
            memory_type=MemoryType.FACT,
            source_type=SourceType.TOOL_OUTPUT,
            source_pointer=SourcePointer(event_id=event.event_id),
            raw_text=text,
            compressed_summary=summary[:300],
            validity=Validity.ACTIVE,
        ))

        # Extract failing tests as errors
        for m in re.finditer(r"FAILED\s+([\w/_.]+)::?([\w_]+).*?\n(.*?)(?=\nFAILED|\n=+|$)", text, re.DOTALL):
            test_file = m.group(1)
            test_name = m.group(2)
            error_detail = m.group(3).strip()[:200]
            objs.append(MemoryObject(
                project_id=event.project_id,
                session_id=event.session_id,
                memory_type=MemoryType.ERROR,
                source_type=SourceType.TOOL_OUTPUT,
                source_pointer=SourcePointer(event_id=event.event_id),
                raw_text=text,
                compressed_summary=f"Test fail: {test_name} in {test_file}",
                errors_found=[ErrorEntry(
                    kind="test_failure",
                    message=f"{test_name}: {error_detail}"[:400],
                    affected_files=[test_file] if test_file else [],
                )],
                validity=Validity.ACTIVE,
            ))

        return objs

    def _parse_git_diff(self, event: EventRecord, text: str) -> List[MemoryObject]:
        objs = []
        files = re.findall(r"^diff --git a/(.+?) b/", text, re.MULTILINE)
        files = list(dict.fromkeys(files))

        if files:
            objs.append(MemoryObject(
                project_id=event.project_id,
                session_id=event.session_id,
                memory_type=MemoryType.CODE_CHANGE,
                source_type=SourceType.TOOL_OUTPUT,
                source_pointer=SourcePointer(event_id=event.event_id),
                raw_text=text,
                compressed_summary=f"Diff: {', '.join(files[:3])}",
                file_references=files,
                validity=Validity.ACTIVE,
            ))

            # Detect added/removed symbols (simple heuristic)
            added = re.findall(r"^\+.+def\s+(\w+)", text, re.MULTILINE)
            removed = re.findall(r"^-.*def\s+(\w+)", text, re.MULTILINE)
            if added or removed:
                changes = []
                if added:
                    changes.append(f"+{','.join(added[:3])}")
                if removed:
                    changes.append(f"-{','.join(removed[:3])}")
                objs.append(MemoryObject(
                    project_id=event.project_id,
                    session_id=event.session_id,
                    memory_type=MemoryType.FACT,
                    source_type=SourceType.TOOL_OUTPUT,
                    source_pointer=SourcePointer(event_id=event.event_id),
                    raw_text=text,
                    compressed_summary=f"Changes: {' '.join(changes)}",
                    validity=Validity.ACTIVE,
                ))

        return objs

    def _parse_search_output(self, event: EventRecord, text: str) -> List[MemoryObject]:
        files = re.findall(r"^([^\n:]+):\d+:", text, re.MULTILINE)
        files = list(dict.fromkeys(files))
        if not files:
            return []

        return [MemoryObject(
            project_id=event.project_id,
            session_id=event.session_id,
            memory_type=MemoryType.FACT,
            source_type=SourceType.TOOL_OUTPUT,
            source_pointer=SourcePointer(event_id=event.event_id),
            raw_text=text,
            compressed_summary=f"Search found: {', '.join(files[:3])}",
            file_references=files[:5],
            validity=Validity.ACTIVE,
        )]

    def _parse_linter_output(self, event: EventRecord, text: str, tool_name: str) -> List[MemoryObject]:
        objs = []
        errors = []
        for m in re.finditer(r"^([^\n:]+):(\d+):\s*(error|warning)[\s:]*(.+)$", text, re.MULTILINE | re.IGNORECASE):
            file_path = m.group(1)
            line = m.group(2)
            severity = m.group(3).lower()
            msg = m.group(4).strip()
            errors.append(ErrorEntry(
                kind=f"{tool_name}_{severity}",
                message=f"{file_path}:{line}: {msg}"[:400],
                affected_files=[file_path],
            ))

        if errors:
            objs.append(MemoryObject(
                project_id=event.project_id,
                session_id=event.session_id,
                memory_type=MemoryType.ERROR,
                source_type=SourceType.TOOL_OUTPUT,
                source_pointer=SourcePointer(event_id=event.event_id),
                raw_text=text,
                compressed_summary=f"{tool_name}: {len(errors)} issues",
                errors_found=errors,
                validity=Validity.ACTIVE,
            ))
        else:
            objs.append(self._make_fact(event, text, tool_name))

        return objs

    def _parse_docker_output(self, event: EventRecord, text: str, tool_name: str) -> List[MemoryObject]:
        objs = []
        # Detect build errors
        if "error" in text.lower() or "failed" in text.lower():
            objs.append(MemoryObject(
                project_id=event.project_id,
                session_id=event.session_id,
                memory_type=MemoryType.ERROR,
                source_type=SourceType.TOOL_OUTPUT,
                source_pointer=SourcePointer(event_id=event.event_id),
                raw_text=text,
                compressed_summary=f"{tool_name} build failed: {text[:200]}",
                errors_found=[ErrorEntry(kind="docker_error", message=text[:500])],
                validity=Validity.ACTIVE,
            ))
        else:
            objs.append(self._make_fact(event, text, tool_name))
        # Extract image names
        images = re.findall(r"Successfully built\s+([a-f0-9]{12})", text)
        if images:
            objs.append(MemoryObject(
                project_id=event.project_id,
                session_id=event.session_id,
                memory_type=MemoryType.FACT,
                source_type=SourceType.TOOL_OUTPUT,
                source_pointer=SourcePointer(event_id=event.event_id),
                raw_text=text,
                compressed_summary=f"Docker image built: {images[0]}",
                validity=Validity.ACTIVE,
            ))
        return objs

    def _parse_terraform_output(self, event: EventRecord, text: str, tool_name: str) -> List[MemoryObject]:
        objs = []
        # Count resources to add/change/destroy
        add_match = re.search(r"(\d+) to add", text)
        change_match = re.search(r"(\d+) to change", text)
        destroy_match = re.search(r"(\d+) to destroy", text)
        summary_parts = []
        if add_match:
            summary_parts.append(f"+{add_match.group(1)}")
        if change_match:
            summary_parts.append(f"~{change_match.group(1)}")
        if destroy_match:
            summary_parts.append(f"-{destroy_match.group(1)}")
        if summary_parts:
            objs.append(MemoryObject(
                project_id=event.project_id,
                session_id=event.session_id,
                memory_type=MemoryType.FACT,
                source_type=SourceType.TOOL_OUTPUT,
                source_pointer=SourcePointer(event_id=event.event_id),
                raw_text=text,
                compressed_summary=f"Terraform plan: {' '.join(summary_parts)}",
                validity=Validity.ACTIVE,
            ))
        else:
            objs.append(self._make_fact(event, text, tool_name))
        # Detect errors
        if "error" in text.lower():
            objs.append(MemoryObject(
                project_id=event.project_id,
                session_id=event.session_id,
                memory_type=MemoryType.ERROR,
                source_type=SourceType.TOOL_OUTPUT,
                source_pointer=SourcePointer(event_id=event.event_id),
                raw_text=text,
                compressed_summary=f"Terraform error: {text[:200]}",
                errors_found=[ErrorEntry(kind="terraform_error", message=text[:500])],
                validity=Validity.ACTIVE,
            ))
        return objs

    def _parse_kubectl_output(self, event: EventRecord, text: str, tool_name: str) -> List[MemoryObject]:
        objs = []
        # Extract pod/deployment status
        status_items = re.findall(r"^(\S+)\s+\d+/\d+\s+(\w+)", text, re.MULTILINE)
        if status_items:
            statuses = [f"{name}:{status}" for name, status in status_items[:3]]
            objs.append(MemoryObject(
                project_id=event.project_id,
                session_id=event.session_id,
                memory_type=MemoryType.FACT,
                source_type=SourceType.TOOL_OUTPUT,
                source_pointer=SourcePointer(event_id=event.event_id),
                raw_text=text,
                compressed_summary=f"K8s status: {' '.join(statuses)}",
                validity=Validity.ACTIVE,
            ))
        else:
            objs.append(self._make_fact(event, text, tool_name))
        # Detect CrashLoopBackOff or errors
        if any(k in text for k in ["CrashLoopBackOff", "Error", "Failed", "OOMKilled"]):
            objs.append(MemoryObject(
                project_id=event.project_id,
                session_id=event.session_id,
                memory_type=MemoryType.ERROR,
                source_type=SourceType.TOOL_OUTPUT,
                source_pointer=SourcePointer(event_id=event.event_id),
                raw_text=text,
                compressed_summary=f"K8s pod error detected",
                errors_found=[ErrorEntry(kind="k8s_error", message=text[:500])],
                validity=Validity.ACTIVE,
            ))
        return objs

    def _parse_package_output(self, event: EventRecord, text: str, tool_name: str) -> List[MemoryObject]:
        objs = []
        # Detect installed packages
        if tool_name in ("pip", "npm", "yarn", "pnpm"):
            pkgs = re.findall(r"Successfully installed\s+(.+)", text)
            if pkgs:
                objs.append(MemoryObject(
                    project_id=event.project_id,
                    session_id=event.session_id,
                    memory_type=MemoryType.FACT,
                    source_type=SourceType.TOOL_OUTPUT,
                    source_pointer=SourcePointer(event_id=event.event_id),
                    raw_text=text,
                    compressed_summary=f"Installed: {pkgs[0][:100]}",
                    validity=Validity.ACTIVE,
                ))
        # Detect vulnerabilities
        vuln_match = re.search(r"(\d+)\s+(?:vulnerabilities?|high|critical)", text, re.IGNORECASE)
        if vuln_match:
            objs.append(MemoryObject(
                project_id=event.project_id,
                session_id=event.session_id,
                memory_type=MemoryType.ERROR,
                source_type=SourceType.TOOL_OUTPUT,
                source_pointer=SourcePointer(event_id=event.event_id),
                raw_text=text,
                compressed_summary=f"Package vulnerabilities found: {vuln_match.group(1)}",
                errors_found=[ErrorEntry(kind="package_vulnerability", message=text[:500])],
                validity=Validity.ACTIVE,
            ))
        if not objs:
            objs.append(self._make_fact(event, text, tool_name))
        return objs

    def _parse_api_output(self, event: EventRecord, text: str, tool_name: str) -> List[MemoryObject]:
        objs = []
        status_match = re.search(r"HTTP/(\d\.\d)\s+(\d{3})", text)
        if status_match:
            code = int(status_match.group(2))
            status = "success" if code < 400 else "error"
            objs.append(MemoryObject(
                project_id=event.project_id,
                session_id=event.session_id,
                memory_type=MemoryType.FACT,
                source_type=SourceType.TOOL_OUTPUT,
                source_pointer=SourcePointer(event_id=event.event_id),
                raw_text=text,
                compressed_summary=f"API {status}: HTTP {code}",
                validity=Validity.ACTIVE,
            ))
            if code >= 400:
                objs.append(MemoryObject(
                    project_id=event.project_id,
                    session_id=event.session_id,
                    memory_type=MemoryType.ERROR,
                    source_type=SourceType.TOOL_OUTPUT,
                    source_pointer=SourcePointer(event_id=event.event_id),
                    raw_text=text,
                    compressed_summary=f"API error: HTTP {code}",
                    errors_found=[ErrorEntry(kind="api_error", message=text[:500])],
                    validity=Validity.ACTIVE,
                ))
        else:
            objs.append(self._make_fact(event, text, tool_name))
        return objs

    def _parse_security_output(self, event: EventRecord, text: str, tool_name: str) -> List[MemoryObject]:
        objs = []
        issues = re.findall(r"(high|critical|medium|low)\s+severity", text, re.IGNORECASE)
        if issues:
            counts = {}
            for sev in issues:
                counts[sev.lower()] = counts.get(sev.lower(), 0) + 1
            summary = ", ".join(f"{k}:{v}" for k, v in sorted(counts.items()))
            objs.append(MemoryObject(
                project_id=event.project_id,
                session_id=event.session_id,
                memory_type=MemoryType.ERROR,
                source_type=SourceType.TOOL_OUTPUT,
                source_pointer=SourcePointer(event_id=event.event_id),
                raw_text=text,
                compressed_summary=f"{tool_name} security: {summary}",
                errors_found=[ErrorEntry(kind=f"{tool_name}_issue", message=text[:500])],
                validity=Validity.ACTIVE,
            ))
        else:
            objs.append(self._make_fact(event, text, tool_name))
        return objs

    def _parse_coverage_output(self, event: EventRecord, text: str, tool_name: str) -> List[MemoryObject]:
        objs = []
        coverage_match = re.search(r"(\d+(?:\.\d+)?)%", text)
        if coverage_match:
            pct = float(coverage_match.group(1))
            objs.append(MemoryObject(
                project_id=event.project_id,
                session_id=event.session_id,
                memory_type=MemoryType.FACT,
                source_type=SourceType.TOOL_OUTPUT,
                source_pointer=SourcePointer(event_id=event.event_id),
                raw_text=text,
                compressed_summary=f"Coverage: {pct}%",
                validity=Validity.ACTIVE,
            ))
            if pct < 50:
                objs.append(MemoryObject(
                    project_id=event.project_id,
                    session_id=event.session_id,
                    memory_type=MemoryType.ERROR,
                    source_type=SourceType.TOOL_OUTPUT,
                    source_pointer=SourcePointer(event_id=event.event_id),
                    raw_text=text,
                    compressed_summary=f"Low coverage: {pct}%",
                    errors_found=[ErrorEntry(kind="low_coverage", message=f"Coverage {pct}% below threshold")],
                    validity=Validity.ACTIVE,
                ))
        else:
            objs.append(self._make_fact(event, text, tool_name))
        return objs

    def _make_fact(self, event: EventRecord, text: str, tool_name: str) -> MemoryObject:
        return MemoryObject(
            project_id=event.project_id,
            session_id=event.session_id,
            memory_type=MemoryType.FACT,
            source_type=SourceType.TOOL_OUTPUT,
            source_pointer=SourcePointer(event_id=event.event_id),
            raw_text=text,
            compressed_summary=f"{tool_name}: {text[:200]}",
            validity=Validity.ACTIVE,
        )
