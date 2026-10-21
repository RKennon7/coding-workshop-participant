// "Oct 21, 2026, 3:04 PM" in the user's locale, or "" for missing values
export function formatDateTime(value) {
    if (!value) {
        return '';
    }
    return new Date(value).toLocaleString(undefined, {dateStyle: 'medium', timeStyle: 'short'});
}
