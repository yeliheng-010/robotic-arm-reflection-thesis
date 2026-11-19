"""仅收窄已证实的碰撞例外，不额外约束夹爪接触源物体。"""
from guard_policy import forbidden as strict_forbidden


def forbidden(contact, source):
    if set(contact['roots']) == {source, '2f85_base'}:
        return False
    return strict_forbidden(contact, source)
