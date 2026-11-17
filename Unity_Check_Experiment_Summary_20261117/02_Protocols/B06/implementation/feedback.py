"""Presentation only: every immutable public rule is still evaluated upstream."""
def check_feedback(full):
    rules = full['rules']
    failed = [r for r in rules if not r['passed']]
    return dict(passed=full['passed'], checked_rule_count=len(rules),
                passed_rule_count=len(rules)-len(failed), failed_rule_count=len(failed),
                failures=[{k: r[k] for k in ['rule_id', 'measured', 'expected']} for r in failed])
