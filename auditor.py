"""Offline, deterministic checks for JSON agent traces. No model/API required."""
import argparse
import json
from pathlib import Path


def audit(trace):
    """Return evidence-linked findings; never execute a trace's tool calls."""
    if not isinstance(trace, dict) or not isinstance(trace.get('steps'), list):
        raise ValueError('Trace must be an object with a steps array')
    policy = trace.get('policy', {})
    allowed = set(policy.get('allowed_tools', []))
    required = policy.get('required_arguments', {})
    results, seen, findings = {}, set(), []

    def flag(code, step, detail):
        findings.append(dict(code=code, step=step, detail=detail))

    for index, step in enumerate(trace['steps']):
        if not isinstance(step, dict):
            raise ValueError(f'Step {index} must be an object')
        sid = step.get('id')
        if not isinstance(sid, str) or not sid or sid in seen:
            raise ValueError(f'Step {index} needs a unique nonempty string id')
        seen.add(sid)
        kind = step.get('type')
        if kind == 'tool_call':
            tool = step.get('tool')
            if tool not in allowed:
                flag('UNAPPROVED_TOOL', sid, f'Tool {tool!r} is outside the allowlist')
            arguments = step.get('arguments', {})
            if not isinstance(arguments, dict):
                raise ValueError(f'{sid}: arguments must be an object')
            for name in required.get(tool, []):
                if name not in arguments or arguments[name] is None or arguments[name] == '':
                    flag('MISSING_ARGUMENT', sid, f'Required argument {name!r} missing')
            results[sid] = None
        elif kind == 'tool_result':
            call = step.get('call_id')
            status = step.get('status')
            if status not in ('success', 'error'):
                raise ValueError(f'{sid}: status must be success or error')
            if call not in results:
                flag('ORPHAN_RESULT', sid, 'Result has no preceding tool call')
            elif results[call] is not None:
                flag('DUPLICATE_RESULT', sid, f'Call {call!r} already has a result')
            else:
                results[call] = status
        elif kind == 'final':
            evidence = step.get('evidence', [])
            if not isinstance(evidence, list) or any(not isinstance(x, str) for x in evidence):
                raise ValueError(f'{sid}: evidence must be a list of call ids')
            if step.get('claims_completion') and not evidence:
                flag('UNSUPPORTED_COMPLETION', sid, 'Completion claim has no cited tool evidence')
            for call in evidence:
                if results.get(call) != 'success':
                    flag('INVALID_EVIDENCE', sid, f'{call!r} has no preceding successful result')
        else:
            raise ValueError(f'{sid}: unsupported step type {kind!r}')
    for call, status in results.items():
        if status is None:
            flag('MISSING_RESULT', call, 'Tool call has no result')
    return dict(trace_id=trace.get('trace_id'), checks_passed=not findings,
                finding_count=len(findings), findings=findings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        report = audit(json.loads(args.trace.read_text()))
    except (ValueError, OSError) as exc:
        parser.exit(2, f'Invalid input: {exc}\n')
    text = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end='')
    return 0 if report['checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
