// display formatting for dates and durations, shared by the grids and dashboard cards.
// all output uses the browser's locale and time zone (the API sends ISO timestamps)

// "Oct 21, 2026, 3:04 PM" in the user's locale, or "" for missing values
export function formatDateTime(value) {
    if (!value) {
        return '';
    }
    return new Date(value).toLocaleString(undefined, {dateStyle: 'medium', timeStyle: 'short'});
}

// "Oct 21, 2026" in the user's locale, or "" for missing values
export function formatDate(value) {
    if (!value) {
        return '';
    }
    return new Date(value).toLocaleDateString(undefined, {dateStyle: 'medium'});
}

// compact duration for stat tiles: "45m", "5.2h", "3.1d". takes hours (the analytics API reports
// durations as *_hours), "–" for null/undefined e.g. when no tickets reached that milestone yet
export function formatDuration(hours) {
    if (hours == null) {
        return '–';
    }
    if (hours < 1) {
        return `${Math.max(1, Math.round(hours * 60))}m`;
    }
    if (hours < 48) {
        // a decimal only where it matters: "1.8h" but "37h"
        return `${trimZero(hours.toFixed(hours < 10 ? 1 : 0))}h`;
    }
    return `${trimZero((hours / 24).toFixed(1))}d`;
}

// "just now", "5h ago", "3d ago"
export function formatAgo(value) {
    if (!value) {
        return '';
    }
    const hours = (Date.now() - new Date(value).getTime()) / 3_600_000;
    return hours < 1 / 60 ? 'just now' : `${formatDuration(hours)} ago`;
}

// "Oct 21"
export function formatShortDate(value) {
    return new Date(value).toLocaleDateString(undefined, {month: 'short', day: 'numeric'});
}

// "2.0" -> "2" (defined last but only called later, once the module has loaded)
const trimZero = (text) => text.replace(/\.0$/, '');
