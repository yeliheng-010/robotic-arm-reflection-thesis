def execution_mode(*, folder_exists, completed):
    if not folder_exists:
        assert not completed
        return 'execute_new'
    assert completed, 'Incomplete consumed case must be investigated, never rerun automatically'
    return 'audit_existing'


def audit_disposition(contact_counts):
    assert contact_counts and all(type(n) is int and n >= 0 for n in contact_counts)
    return 'quarantine' if any(contact_counts) else 'audit'
