from enum import Enum
from typing import Set, Dict


class PostStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    VALIDATING = "VALIDATING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    READY = "READY"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


# Mapa de transições válidas de estados
VALID_TRANSITIONS: Dict[PostStatus, Set[PostStatus]] = {
    PostStatus.DISCOVERED: {PostStatus.VALIDATING, PostStatus.FAILED},
    PostStatus.VALIDATING: {PostStatus.READY, PostStatus.NEEDS_REVIEW, PostStatus.FAILED},
    PostStatus.NEEDS_REVIEW: {PostStatus.READY, PostStatus.CANCELLED, PostStatus.BLOCKED},
    PostStatus.READY: {PostStatus.APPROVED, PostStatus.NEEDS_REVIEW, PostStatus.CANCELLED},
    PostStatus.APPROVED: {PostStatus.SCHEDULED, PostStatus.NEEDS_REVIEW, PostStatus.CANCELLED},
    PostStatus.SCHEDULED: {PostStatus.UPLOADING, PostStatus.NEEDS_REVIEW, PostStatus.CANCELLED, PostStatus.BLOCKED},
    PostStatus.UPLOADING: {PostStatus.PROCESSING, PostStatus.UNKNOWN, PostStatus.FAILED},
    PostStatus.PROCESSING: {PostStatus.PUBLISHED, PostStatus.FAILED, PostStatus.UNKNOWN},
    PostStatus.UNKNOWN: {PostStatus.PROCESSING, PostStatus.PUBLISHED, PostStatus.FAILED},
    PostStatus.PUBLISHED: set(),  # Estado terminal com sucesso
    PostStatus.FAILED: {PostStatus.READY, PostStatus.NEEDS_REVIEW, PostStatus.CANCELLED},  # Permite reset após correção
    PostStatus.BLOCKED: {PostStatus.READY, PostStatus.NEEDS_REVIEW, PostStatus.CANCELLED},
    PostStatus.CANCELLED: {PostStatus.READY},
}


def can_transition(current: PostStatus, target: PostStatus) -> bool:
    """Verifica se a transição entre dois estados é válida segundo a máquina de estados."""
    if current == target:
        return True
    return target in VALID_TRANSITIONS.get(current, set())
