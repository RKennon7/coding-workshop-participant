// shared lookups and helpers for the dashboard cards in this folder: attention flag metadata (label, color, icon),
// the statuses that count as "active", percentage -> status color thresholds and location formatting.
// used by every persona's dashboard (pages/DashboardPage.jsx) and the cards it renders
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

// tickets still being worked on. mirrors ACTIVE in backend/v1/app/routers/analytics.py; used for drill-down filters
export const ACTIVE_STATUSES = ['Open', 'In Progress', 'Blocked'];

/**
 * Share of something that went well (SLA met, tickets kept updated) -> MUI palette key.
 * 90%+ is 'success', 70%+ 'warning', anything lower 'error'. null means there was nothing to
 * measure yet (e.g. no tickets resolved) and gives 'default', which callers render grey.
 */
export function successTone(pct) {
    if (pct == null) return 'default';
    if (pct >= 90) return 'success';
    if (pct >= 70) return 'warning';
    return 'error';
}

/**
 * How full an engineer's queue is (EngineerLoad.load_pct = active / max_open_tickets * 100) -> MUI palette key.
 * The reverse of successTone: higher is worse. 100%+ (at or over capacity) is 'error', 70%+ 'warning'.
 */
export function loadTone(pct) {
    if (pct >= 100) return 'error';
    if (pct >= 70) return 'warning';
    return 'success';
}

/**
 * "North Tower · Floor 3 · NT-3-02", led by the facility when the view spans several campuses.
 * Takes a LocationRef from the API ({facility, building, floor?, seat?}); missing floor/seat are skipped.
 */
export function formatLocation({facility, building, floor, seat}, withFacility = false) {
    return [withFacility && facility, building, floor, seat].filter(Boolean).join(' · ');
}
