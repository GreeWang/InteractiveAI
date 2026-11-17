"""Shared resource reminders and reserved opportunities for actor-written finish."""
def report_phase(stats, caps, reserve, elapsed, next_input_bound, already=False):
    reasons = []
    if caps['requests'] - stats['requests'] <= reserve['requests']: reasons.append('request_reserve')
    if caps['tools'] - stats['tools'] <= reserve['requests']: reasons.append('tool_reserve')
    # Two report opportunities, allowing growth for an invalid-report correction.
    needed = max(reserve['input_tokens'], 2 * (next_input_bound + 4096))
    if stats['input_tokens'] + next_input_bound + needed > caps['input_tokens']: reasons.append('input_reserve')
    if caps['output_tokens'] - stats['output_tokens'] - 2048 < reserve['output_tokens']: reasons.append('output_reserve')
    if caps['seconds'] - elapsed <= reserve['seconds'] + 270: reasons.append('time_reserve')
    return already or bool(reasons), reasons, needed


def resource_budget(stats, caps, elapsed, finish_only, reasons):
    return dict(remaining_requests=caps['requests']-stats['requests'],
        remaining_tools=caps['tools']-stats['tools'],
        remaining_edit_batches=caps['edit_batches']-stats['edit_batches'],
        remaining_writes=caps['operations']-stats['operations'],
        remaining_input_tokens=caps['input_tokens']-stats['input_tokens'],
        remaining_output_tokens=caps['output_tokens']-stats['output_tokens'],
        remaining_seconds=round(max(0, caps['seconds']-elapsed), 3),
        finish_only=finish_only, finalization_reasons=reasons,
        accounting='Remaining tokens are before this request; its full input history is charged again.')
