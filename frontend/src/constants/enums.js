// mirrors the enums in backend/v1/app/models (incident.py, user.py)

export const INCIDENT_STATUSES = ['Open', 'In Progress', 'Blocked', 'Resolved', 'Closed'];
export const INCIDENT_PRIORITIES = ['Low', 'Medium', 'High', 'Critical'];
export const INCIDENT_CATEGORIES = [
    'HVAC',
    'Electrical',
    'Plumbing',
    'Furniture',
    'Cleaning',
    'Security / Access',
    'Network / Wi-Fi',
    'Hardware',
    'AV Equipment',
    'Other',
];
export const USER_ROLES = ['Facility Admin', 'Engineer', 'Employee'];

// MUI Chip colors for each value
export const STATUS_COLORS = {
    'Open': 'info',
    'In Progress': 'primary',
    'Blocked': 'error',
    'Resolved': 'success',
    'Closed': 'default',
};
export const PRIORITY_COLORS = {
    Low: 'default',
    Medium: 'info',
    High: 'warning',
    Critical: 'error',
};

// plain string list -> select options
export const toOptions = (values) => values.map((value) => ({value, label: value}));
