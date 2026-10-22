// helpers for turning filter UI state into API query params (used by pages/IncidentsPage.jsx)

// filter object -> query params, leaving out anything that isn't set (empty lists, null, false)
export function toListParams(filters) {
    return Object.fromEntries(
        Object.entries(filters).filter(([, value]) => (Array.isArray(value) ? value.length > 0 : value != null && value !== false))
    );
}
