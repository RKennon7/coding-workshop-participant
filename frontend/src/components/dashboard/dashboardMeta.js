import TimerOffIcon from '@mui/icons-material/TimerOff';
import BlockIcon from '@mui/icons-material/Block';
import FlagIcon from '@mui/icons-material/Flag';
import PersonOffIcon from '@mui/icons-material/PersonOff';
import NotificationsPausedIcon from '@mui/icons-material/NotificationsPaused';
import TaskAltIcon from '@mui/icons-material/TaskAlt';

// mirrors AttentionKind in backend/v1/app/schemas/analytics.py, in the backend's urgency order.
// color is an MUI palette key; every flag shows its icon + label, never color alone
export const FLAG_META = {
    sla_breached: {label: 'SLA breached', color: 'error', icon: TimerOffIcon},
    blocked: {label: 'Blocked', color: 'error', icon: BlockIcon},
    escalated: {label: 'Escalated', color: 'warning', icon: FlagIcon},
    unassigned: {label: 'Unassigned', color: 'warning', icon: PersonOffIcon},
    awaiting_reporter: {label: 'Awaiting your confirmation', color: 'success', icon: TaskAltIcon},
    silent: {label: 'No recent update', color: 'info', icon: NotificationsPausedIcon},
};

export const ACTIVE_STATUSES = ['Open', 'In Progress', 'Blocked'];

// share of something that went well (SLA met, tickets kept updated) -> status color
export function successTone(pct) {
    if (pct == null) return 'default';
    if (pct >= 90) return 'success';
    if (pct >= 70) return 'warning';
    return 'error';
}

// how full an engineer's queue is -> status color
export function loadTone(pct) {
    if (pct >= 100) return 'error';
    if (pct >= 70) return 'warning';
    return 'success';
}

// "North Tower · Floor 3 · NT-3-02"
export function formatLocation({building, floor, seat}) {
    return [building, floor, seat].filter(Boolean).join(' · ');
}
